import re
import logging
import requests
import pathlib

import numpy as np
import pandas as pd
import spotipy

from music_sync.spotify.similarity import measure_query_similarity
from music_sync.spotify.utils import (
    get_chunks,
    timeout_wrapper,
    generate_additional_attempts,
    get_songs_to_sync,
)
from music_sync.classes import Song
from music_sync.config import LOG_DIR


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


# TODO: Create one main database that contains all synced songs.
#       Whenever a new playlist needs to be synced, look up any songs that are already
#       in this database. This will save some API calls.


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list:
    """
    Obtain all track IDs of the songs included in a specified playlist.

    Parameters
    ----------
    sp :
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
        response = timeout_wrapper(
            sp.playlist_items(
                playlist_id,
                offset=offset,
                fields="items.track.id,items.track.artists.id",
                additional_types=["track"],
            )
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
    log_path: pathlib.Path = LOG_DIR,
):
    """
    Syncs a given playlist.
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
    log_path

    Returns
    -------

    """
    logging.info(f"Working with playlist: {playlist_name}")

    # Store information on how well syncing worked
    filename = "".join(e for e in playlist_name if e.isalnum())
    filepath = log_path / f"{filename}.csv"

    playlist_songs = [Song(**i) for i in playlist_songs]
    songs_to_sync, flag_already_synced = get_songs_to_sync(
        str(filepath), playlist_songs
    )

    logging.info("Need to sync {0} new songs".format(len(songs_to_sync)))

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
        logging.info(
            f"Spotify playlist already exists and contained {len(tracks)} songs"
        )

    logging.info(f"Starting to sync {len(songs_to_sync)} songs")
    # For above songs, search for availability in Spotify's catalogue
    update_frequency = 50
    count = 0
    matched_songs = []
    for song in songs_to_sync:
        count += 1
        matched_songs += [get_best_match(sp, song)]
        if count % update_frequency == 0:
            logging.info(f"Synced {count} out of {len(songs_to_sync)} songs")

    if matched_songs:
        matched_songs = pd.DataFrame(list(matched_songs))
        matched_songs.to_csv(
            filepath,
            index=False,
            mode="a" if flag_already_synced else "w",
            header=False if flag_already_synced else True,
        )
        # Subset songs to include only those that are not already present in the Spotify playlist
        unmatched_mask = matched_songs["Spotify Track ID"].isnull()
        mask = (~matched_songs["Spotify Track ID"].isin(tracks)) & (~unmatched_mask)
        songs_to_be_added = matched_songs.loc[mask]

        n_songs_actually_added = len(songs_to_be_added)
        n_songs_supposed_to_be_added = len(matched_songs)
        msg = "{0} songs to be added to Spotify playlist from a total of {1} songs".format(
            n_songs_actually_added, n_songs_supposed_to_be_added
        )
        logging.info(msg)

        # Break songs to be added into chunks so as not to cause timeout
        chunks = get_chunks(songs_to_be_added["Spotify Track ID"].values, 100)
        for chunk in chunks:
            # Add matched songs to Spotify playlist
            sp.playlist_add_items(playlist_id, chunk)

    logging.info(f"Done with playlist {playlist_name}.\n")
