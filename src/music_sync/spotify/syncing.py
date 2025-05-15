import logging
import json
import pathlib
import os

import pandas as pd
import spotipy

from music_sync.spotify.utils import (
    get_chunks,
    get_songs_to_sync,
)
from music_sync.classes import Song
from music_sync.config import COLUMN_MAPPING, LOG_FILE, SYNCING_THRESHOLD
from music_sync.spotify.matching import get_best_match


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


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
    filepath: pathlib.Path = LOG_FILE,
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
        File logging synced songs.

    Returns
    -------

    """
    logging.info(f"Working with playlist: {playlist_name}")

    playlist_songs = [Song(**i) for i in playlist_songs]
    log_data = json.load(open(filepath, "r")) if os.path.exists(filepath) else [{}]

    synced_playlists = [i.get("apple_playlist") for i in log_data]
    synced_playlists = set([x for xs in synced_playlists for x in xs])

    flag_synced_before = playlist_name in synced_playlists
    logging.info(f"Has playlist been synced before? {flag_synced_before}")

    updated_log_data, songs_to_sync = get_songs_to_sync(
        log_data, playlist_songs, playlist_name
    )

    n_items = sum([len(v) for v in songs_to_sync.values()])
    logging.info(f"Need to sync {n_items:,} songs")

    user_id = sp.current_user()["id"]
    offset = 0
    limit = 50
    d_existing_playlists = {}
    while True:
        list_playlists = sp.user_playlists(user_id, limit=limit, offset=offset)["items"]
        d_playlists = {v["name"]: v["id"] for v in list_playlists}
        if len(d_playlists) == 0 or d_playlists is None:
            break
        d_existing_playlists = {**d_existing_playlists, **d_playlists}
        offset += limit

    # If playlist does not already exist on Spotify, create it
    if playlist_name not in d_existing_playlists:
        logging.info("Spotify playlist was newly created")
        info = sp.user_playlist_create(user_id, playlist_name, public=False)
        tracks = []
        playlist_id = info["id"]
    else:
        playlist_id = d_existing_playlists[playlist_name]
        tracks = get_playlist_tracks(sp, playlist_id)
        # noinspection PyTypeChecker
        logging.info(
            f"Spotify playlist already exists and contains {len(tracks)} songs"
        )

    to_match = songs_to_sync["to_search"]
    logging.info(f"Finding matching Spotify songs for {len(to_match):,} Apple songs.")
    # For above songs, search for availability in Spotify's catalogue
    update_frequency = 50
    count = 0
    matched_songs = []
    for song in to_match:
        count += 1
        matched_songs += [get_best_match(sp, song)]
        if count % update_frequency == 0:
            logging.info(f"Matched {count} out of {len(to_match):,} songs")

    to_sync = []

    if matched_songs:
        matched_songs = [pd.json_normalize(i.model_dump()) for i in matched_songs]
        matched_songs = pd.concat(matched_songs)
        # Make sure columns correspond to original names
        matched_songs.rename(columns=COLUMN_MAPPING, inplace=True)
        # Add column for playlist
        matched_songs["apple_playlist"] = [[playlist_name]] * len(matched_songs)
        n_initial_matches = len(matched_songs)
        # Check
        check = set(matched_songs.columns) == set(updated_log_data[0].keys())
        if not check:
            logging.error("Matched songs have the wrong column names")
            logging.error(
                f"Mismatch: {set(matched_songs.columns) - set(updated_log_data[0].keys())}"
            )
            raise Exception(
                "Dataframe resulting from SongMatch class has wrong column names"
            )
        # Filter out poor matches
        matched_songs = matched_songs.query(
            f"total_similarity >= {SYNCING_THRESHOLD}"
        ).copy()
        # Filter out songs that are already in the playlist
        # Perhaps because the given song was the best match to a highly similar Apple song in the same playlist
        matched_songs = matched_songs.loc[
            lambda x: ~x["spotify_track_id"].isin(tracks)
        ].copy()
        # Provide some info
        n_songs_actually_added = len(matched_songs)
        msg = "{0} of {1} are good matches".format(
            n_songs_actually_added, n_initial_matches
        )
        logging.info(msg)
        # Add matched songs to log data
        updated_log_data += matched_songs.to_dict("records")
        to_sync += matched_songs["spotify_track_id"].values.tolist()
        # Break songs to be added into chunks so as not to cause timeout

    # Songs that have been synced before (for a different playlist) and simply need to be assigned
    # to this playlist as well
    logging.info(
        f"Songs without need to match but to add: {len(songs_to_sync['to_assign']):,}"
    )
    to_sync += songs_to_sync["to_assign"]

    if to_sync:
        chunks = get_chunks(to_sync, 100)
        for chunk in chunks:
            # Add matched songs to Spotify playlist
            sp.playlist_add_items(playlist_id, chunk)

        # Save updated log data
        with open(filepath, "w") as f:
            # noinspection PyTypeChecker
            json.dump(updated_log_data, f)

    logging.info(f"Done with playlist {playlist_name}.\n")
