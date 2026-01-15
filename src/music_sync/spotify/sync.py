"""Functions for syncing Apple Music playlists to Spotify and managing sync logs."""

import json
import pathlib
import os
from itertools import batched

from loguru import logger
import pandas as pd
import spotipy
from tqdm import tqdm
from pandas import DataFrame

from music_sync.classes import Song, SongsToSync
from music_sync.config import config
from music_sync.spotify.matching import get_best_match


PLAYLIST_FETCH_LIMIT = 50
UPDATE_FREQUENCY = 50
CHUNK_SIZE = 100


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list:
    """
    Obtain all track IDs of the songs included in a specified playlist.

    Parameters
    ----------
    sp :
        Spotipy instance.
    playlist_id :
        Playlist ID for which all tracks should be obtained.

    Returns
    -------
    playlist_tracks : list
        Track IDs that are contained in the playlist
    """
    playlist_tracks = []
    offset = 0
    while True:
        response = sp.playlist_items(
            playlist_id,
            offset=offset,
            fields="items.track.id,items.track.artists.id",
            additional_types=["track"],
        )
        if not response.get("items"):
            break
        offset += len(response["items"])
        current_track_extract = []
        for i in response["items"]:
            try:
                current_track_extract += [
                    (i["track"]["id"], [j["id"] for j in i["track"]["artists"]])
                ]
            except TypeError:
                pass
        playlist_tracks += current_track_extract
    return playlist_tracks


def sync_playlist(
    sp: spotipy.Spotify,
    playlist_name: str,
    playlist_songs: list[dict[str, str]],
    filepath: pathlib.Path = config.sync.log_file,
):
    """
    Sync a given playlist.

    If it does not yet exist, such a playlist will be created.
    Otherwise, existing songs will be compared to the provided playlist songs and only new ones will be synced.
    Information on each song synced is written to the log directory, where a CSV with the playlist name is created.
    This file contains info on how well a given song was matched (string similarity) and identifies songs that
    were not matched.

    Parameters
    ----------
    sp
    playlist_name
        The name of the playlist to be created/synced on Spotify
    playlist_songs
        The songs that should be in this playlist in the form of [(song name, artist name, album name), ...]
    filepath: str :
        File logger synced songs.

    Returns
    -------

    """
    logger.info(f"Working with playlist: {playlist_name}")

    playlist_songs = [Song(**i) for i in playlist_songs]
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            log_data = json.load(f)
    else:
        log_data = [{}]

    synced_playlists = [
        i.get("apple_playlist") for i in log_data if i.get("apple_playlist") is not None
    ]
    synced_playlists = set([x for xs in synced_playlists for x in xs])

    flag_synced_before = playlist_name in synced_playlists
    logger.info(f"Has the playlist been synced before? {flag_synced_before}")

    updated_log_data, songs_to_sync = get_songs_to_sync(
        log_data, playlist_songs, playlist_name
    )

    n_items = sum([len(v) for v in songs_to_sync.values()])
    logger.info(f"Need to sync {n_items:,} songs")

    user_id = sp.current_user()["id"]
    offset = 0
    d_existing_playlists = {}
    while True:
        list_playlists = sp.user_playlists(
            user_id, limit=PLAYLIST_FETCH_LIMIT, offset=offset
        )["items"]
        d_playlists = {v["name"]: v["id"] for v in list_playlists}
        if not d_playlists:
            break
        d_existing_playlists = {**d_existing_playlists, **d_playlists}
        offset += PLAYLIST_FETCH_LIMIT

    # If playlist does not already exist on Spotify, create it
    if playlist_name not in d_existing_playlists:
        logger.info("Spotify playlist was newly created")
        info = sp.user_playlist_create(user_id, playlist_name, public=False)
        tracks = []
        playlist_id = info["id"]
    else:
        playlist_id = d_existing_playlists[playlist_name]
        tracks = get_playlist_tracks(sp, playlist_id)
        # noinspection PyTypeChecker
        logger.info(f"Spotify playlist already exists and contains {len(tracks)} songs")

    track_ids = {track[0] for track in tracks}

    to_match = songs_to_sync["to_search"]
    logger.info(f"Finding matching Spotify songs for {len(to_match):,} Apple songs.")
    # For above songs, search for availability in Spotify's catalogue
    count = 0
    matched_songs: list = []
    for song in tqdm(to_match, desc="Matching songs"):
        count += 1
        matched_songs.append(get_best_match(sp, song))

    to_sync = []

    matched_songs = [pd.json_normalize(i.model_dump()) for i in matched_songs]
    # Filter out empty DataFrames before concatenation
    matched_songs = [
        df for df in matched_songs if not df.empty or ~df.isnull().all().all()
    ]
    if matched_songs:
        df_matched_songs: pd.DataFrame = pd.concat(matched_songs, ignore_index=True)
        # Make sure columns correspond to original names
        df_matched_songs.rename(columns=config.sync.column_mapping, inplace=True)
        # Add column for playlist
        df_matched_songs["apple_playlist"] = [[playlist_name]] * len(df_matched_songs)
        n_initial_matches = len(df_matched_songs)
        if len(updated_log_data) > 0 and not set(df_matched_songs.columns) == set(
            updated_log_data[0].keys()
        ):
            logger.error("Matched songs have the wrong column names")
            logger.error(
                f"Mismatch: {set(df_matched_songs.columns) - set(updated_log_data[0].keys())}"
            )
            raise Exception(
                "Dataframe resulting from SongMatch class has wrong column names"
            )
        # Filter out poor matches
        df_matched_songs = df_matched_songs.query(
            f"total_similarity >= {config.sync.similarity_threshold}"
        ).copy()
        # Filter out songs that are already in the playlist
        # Perhaps because the given song was the best match to a highly similar Apple song in the same playlist
        df_matched_songs = df_matched_songs.loc[
            ~df_matched_songs["spotify_track_id"].isin(track_ids)
        ].copy()
        # Provide some info
        n_songs_actually_added = len(df_matched_songs)
        msg = "{0} songs out of {1} are good matches".format(
            n_songs_actually_added, n_initial_matches
        )
        logger.info(msg)
        # Add matched songs to log data
        updated_log_data += df_matched_songs.to_dict("records")
        to_sync += df_matched_songs["spotify_track_id"].values.tolist()
        # Break songs to be added into chunks so as not to cause timeout

    # Songs that have been synced before (for a different playlist) and simply need to be assigned
    # to this playlist as well
    logger.info(
        f"Songs to add that have already been matched before for another playlist: {len(songs_to_sync['to_assign']):,}"
    )
    to_sync += songs_to_sync["to_assign"]

    if to_sync:
        for chunk in batched(to_sync, CHUNK_SIZE):
            # Add matched songs to Spotify playlist
            sp.playlist_add_items(playlist_id, chunk)

        # Save updated log data
        with open(filepath, "w") as f:
            # noinspection PyTypeChecker
            json.dump(updated_log_data, f)

    logger.info(f"Done with playlist {playlist_name}.\n")


def get_songs_to_sync(
    log_data: list[dict],
    playlist_songs: list[Song],
    playlist_name: str,
) -> tuple[list[dict], SongsToSync]:
    """
    Compare the songs in a playlist with a synced log file to identify songs that need syncing.

    Parameters
    ----------
    log_data : dict
        JSON data storing log data.
    playlist_songs : list[Song]
        List of Song objects representing the songs currently in the playlist.
    playlist_name : str
        Name of the playlist.

    Returns
    -------
    updated_log_data : list[dict] :
        Updated JSON data storing log data.
        Songs in database that have not yet been assigned to the playlist, will be now.
    songs_to_sync: dict[str, list[Song | str]] :
        Dictionary containing songs to search and those to assign.
    """

    found_track_ids = set()
    updated_log_data = []

    playlist_track_ids = {song.track_id for song in playlist_songs}

    songs_to_sync = {
        # Holds songs not already in the log database and thus have to be searched
        "to_search": [],
        # Holds songs already in the log database, and thus we can simply assign them to the playlist
        "to_assign": [],
    }

    for entry in log_data:
        if "apple_playlist" not in entry:
            logger.info(f"Skipping entry without playlist information: {entry}")
            continue
        track_id = entry["apple_track_id"]
        if track_id in playlist_track_ids:
            found_track_ids.add(track_id)
            if playlist_name not in entry["apple_playlist"]:
                songs_to_sync["to_assign"].append(entry["spotify_track_id"])
                entry["apple_playlist"].append(playlist_name)
        updated_log_data.append(entry)

    songs_to_sync["to_search"] = [
        song for song in playlist_songs if song.track_id not in found_track_ids
    ]

    return updated_log_data, songs_to_sync
