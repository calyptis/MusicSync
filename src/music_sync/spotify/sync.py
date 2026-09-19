"""Functions for syncing Apple Music playlists to Spotify and managing sync logs."""

import json
import pathlib
import os
from itertools import batched

from loguru import logger
import pandas as pd
import spotipy
from tqdm import tqdm

from music_sync.classes import Song, SongMatch, SongsToSync
from music_sync.config import config
from music_sync.spotify.matching import search_best_match


PLAYLIST_FETCH_LIMIT = 50
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


def get_existing_playlists(sp: spotipy.Spotify, user_id: str) -> dict[str, str]:
    """
    Obtain all playlists owned by a user, paging through the API.

    Parameters
    ----------
    sp :
        Spotipy instance.
    user_id :
        Spotify user whose playlists should be listed.

    Returns
    -------
    dict[str, str]
        Mapping of playlist name to playlist ID.
    """
    playlists: dict[str, str] = {}
    offset = 0
    while True:
        page = sp.user_playlists(user_id, limit=PLAYLIST_FETCH_LIMIT, offset=offset)[
            "items"
        ]
        if not page:
            break
        playlists.update({v["name"]: v["id"] for v in page})
        offset += PLAYLIST_FETCH_LIMIT
    return playlists


def load_sync_log(filepath: pathlib.Path) -> list[dict]:
    """
    Read the sync log, returning a single empty entry when no log exists yet.

    Parameters
    ----------
    filepath :
        Path to the JSON sync log.

    Returns
    -------
    list[dict]
        Log entries, one per previously synced song.
    """
    if not os.path.exists(filepath):
        return [{}]
    with open(filepath, "r") as f:
        return json.load(f)


def build_match_log(
    matched_songs: list[SongMatch],
    playlist_name: str,
    existing_track_ids: set[str],
    log_data: list[dict],
) -> pd.DataFrame:
    """
    Turn matches into log rows, keeping only good matches that are not already synced.

    Parameters
    ----------
    matched_songs :
        Matches produced by `search_best_match`, one per Apple Music song.
    playlist_name :
        Playlist these matches belong to.
    existing_track_ids :
        Spotify track IDs already present in the playlist; these are dropped so
        a track is not added twice (e.g. when two near-identical Apple songs
        resolve to the same Spotify track).
    log_data :
        Existing log entries, used to verify the column names still line up.

    Returns
    -------
    pd.DataFrame
        Rows ready to append to the sync log.

    Raises
    ------
    ValueError
        If the columns derived from `SongMatch` do not match the existing log.
    """
    df_matches = pd.concat(
        [pd.json_normalize(i.model_dump()) for i in matched_songs], ignore_index=True
    )
    # Make sure columns correspond to original names
    df_matches = df_matches.rename(columns=config.sync.column_mapping)
    df_matches["apple_playlist"] = [[playlist_name]] * len(df_matches)

    if log_data and set(df_matches.columns) != set(log_data[0].keys()):
        mismatch = set(df_matches.columns) ^ set(log_data[0].keys())
        logger.error(f"Matched songs have the wrong column names. Mismatch: {mismatch}")
        raise ValueError(
            "Dataframe resulting from SongMatch class has wrong column names"
        )

    n_initial_matches = len(df_matches)
    df_good_matches = df_matches.query(
        f"total_similarity >= {config.sync.similarity_threshold}"
    )
    df_good_matches = df_good_matches.loc[
        ~df_good_matches["spotify_track_id"].isin(existing_track_ids)
    ].copy()
    logger.info(
        f"{len(df_good_matches)} songs out of {n_initial_matches} are good matches"
    )
    return df_good_matches


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

    songs = [Song(**i) for i in playlist_songs]
    log_data = load_sync_log(filepath)

    synced_before = any(
        playlist_name in (entry.get("apple_playlist") or []) for entry in log_data
    )
    logger.info(f"Has the playlist been synced before? {synced_before}")

    updated_log_data, songs_to_sync = select_songs_to_sync(
        log_data, songs, playlist_name
    )

    n_items = len(songs_to_sync["to_search"]) + len(songs_to_sync["to_assign"])
    logger.info(f"Need to sync {n_items:,} songs")

    user_id = sp.current_user()["id"]
    existing_playlists = get_existing_playlists(sp, user_id)

    # If playlist does not already exist on Spotify, create it
    if playlist_name not in existing_playlists:
        logger.info("Spotify playlist was newly created")
        info = sp.user_playlist_create(user_id, playlist_name, public=False)
        tracks = []
        playlist_id = info["id"]
    else:
        playlist_id = existing_playlists[playlist_name]
        tracks = get_playlist_tracks(sp, playlist_id)
        # noinspection PyTypeChecker
        logger.info(f"Spotify playlist already exists and contains {len(tracks)} songs")

    track_ids = {track[0] for track in tracks}

    to_match = songs_to_sync["to_search"]
    logger.info(f"Finding matching Spotify songs for {len(to_match):,} Apple songs.")
    # For above songs, search for availability in Spotify's catalogue
    matched_songs: list = []
    for song in tqdm(to_match, desc="Matching songs"):
        matched_songs.append(search_best_match(sp, song))

    to_sync: list[str] = []

    if matched_songs:
        df_good_matches = build_match_log(
            matched_songs, playlist_name, track_ids, updated_log_data
        )
        updated_log_data += df_good_matches.to_dict("records")
        to_sync += df_good_matches["spotify_track_id"].values.tolist()

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


def select_songs_to_sync(
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

    songs_to_sync: SongsToSync = {
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
