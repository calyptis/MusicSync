import numpy as np
import pandas as pd
from music_sync.spotify.utils import (
    get_chunks,
    clean_string,
    timeout_wrapper,
    generate_additional_attempts,
    get_songs_to_sync,
)
from music_sync.config import LOG_DIR
import difflib
import re
import spotipy
import logging
import requests
import pathlib


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


# TODO: Create one main database that contains all synced songs.
#       Whenever a new playlist needs to be synced, look up any songs that are already
#       in this database. This will save some API calls.


def measure_query_similarity(query: tuple, match: tuple) -> tuple:
    """
    Calculates string similarity matches between the original query and a match returned by the API.
    Final similarity is based on individual similarities of song, artist and album (if available).
    Song similarity has a larger weight.

    Parameters
    ----------
    query
        Tuple of (song_name, artist_name, album_name) of original song
    match
        Tuple of (song_name, artist_name, album_name) of matched Spotify song
    Returns
    -------
    similarities
        Tuple of similarities for (aggregate, song, artist, album)
    """
    song_name_similarity = difflib.SequenceMatcher(
        None, query[0], clean_string(match[0])
    ).ratio()
    artist_name_similarity = difflib.SequenceMatcher(
        None, query[1], clean_string(match[1])
    ).ratio()
    album_name_similarity = difflib.SequenceMatcher(
        None, query[2], clean_string(match[2])
    ).ratio()
    if query[2] == "":
        album_name_similarity = None
    similarities = np.array(
        [song_name_similarity, artist_name_similarity, album_name_similarity]
    )
    # Getting the song right is slightly more important
    w = np.array([0.4, 0.3, 0.3])
    ww = np.array(
        [0.6, 0.5]
    )  # In case no album was provided, exclude it from aggregate similarity
    if query[2] == "":
        total_similarity = sum(similarities[:-1] * ww)
    else:
        total_similarity = sum(similarities * w)
    similarities = (
        total_similarity,
        song_name_similarity,
        artist_name_similarity,
        album_name_similarity,
    )
    return similarities


def evaluate_matches(
    tracks: list, song_name: str, artist_name: str, album_name: str
) -> list:
    """
    Calculates similarities between the original query and all returned matches.
    These similarities are at a later stage used to identify the best match.

    Parameters
    ----------
    tracks
        All results from the API search request
    song_name
        Original song name
    artist_name
        Original artist name
    album_name
        Original album name

    Returns
    -------
    matched_items
        List of tuples containing similarity metrics as returned by query_similarity
    """
    matched_items = [
        measure_query_similarity(
            (song_name, artist_name, album_name),
            (
                str(item.get("name", "")),
                " ".join([str(i.get("name", "")) for i in item.get("artists")]),
                str(item.get("album").get("name", "")),
            ),
        )
        for item in tracks
        if item is not None
    ]
    return matched_items


def return_best_match(
    tracks: list,
    best_match_template: dict,
    song_name: str,
    artist_name: str,
    album_name: str,
) -> dict:
    """
    Returns the best match according to string similarities amongst the API results.

    Parameters
    ----------
    tracks
        All results from the API search request
    best_match_template
        Template of the structure of the best_match object
        Contains all the information that will be written to disk in the form of the CSV log file
        after a playlist was successfully synced.
    song_name
        Original song name
    artist_name
        Original artist name
    album_name
        Original album name

    Returns
    -------
    best_match
    """
    best_match = best_match_template.copy()
    matched_items = evaluate_matches(tracks, song_name, artist_name, album_name)
    best_match_idx = np.argmax([i[0] for i in matched_items])
    best_match_item = tracks[best_match_idx]
    best_match["Spotify Song Name"] = best_match_item.get("name")
    best_match["Spotify Artist"] = " ".join(
        [i.get("name") for i in best_match_item.get("artists")]
    )
    best_match["Spotify Album"] = best_match_item.get("album").get("name")
    best_match["Spotify Track ID"] = best_match_item.get("id")
    best_match["Match Score"] = matched_items[best_match_idx][0]
    best_match["Song Match Score"] = matched_items[best_match_idx][1]
    best_match["Artist Match Score"] = matched_items[best_match_idx][2]
    best_match["Album Match Score"] = matched_items[best_match_idx][-1]
    return best_match


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


def get_best_match(
    sp: spotipy.Spotify, song_name: str, artist_name: str, album_name: str
) -> dict:
    """
    Returns the best Spotify song match for a given Apple Music song, if available.

    Parameters
    ----------
    sp
        Spotipy instance
    song_name
        Name of song to be looked up in Spotify
    artist_name
        Name of artist(s) of song to be looked up in Spotify
    album_name
        Name of album of song to be looked up in Spotify


    Returns
    -------
    best_match : dict
        Information on best match, including string similarity with original query information
        All of this information will be written to the CSV log file after a playlist was successfully synced.
    """

    attempts = [(song_name, artist_name, album_name)]

    # Sometimes there is no match if album name is included, e.g.
    # bloody valentine	Machine Gun Kelly	bloody valentine - Single
    attempts += [(song_name, artist_name, "")]
    attempts += generate_additional_attempts(song_name, artist_name, album_name)

    best_match_template = {
        "Apple Song Name": song_name,
        "Apple Artist": artist_name,
        "Apple Album": album_name,
        "Spotify Song Name": None,
        "Spotify Artist": None,
        "Spotify Track ID": None,
        "Match Score": None,
        "Song Match Score": None,
        "Artist Match Score": None,
        "Album Match Score": None,
    }

    attempts_best_matches = []
    for attempt in attempts:
        query = " ".join([str(i) for i in attempt])
        query = re.sub(r"\s+", " ", query).strip()
        try:
            tracks = timeout_wrapper(sp.search(query, limit=15)).get("tracks")
        # except spotipy.exceptions.SpotifyException or requests.exceptions.ReadTimeout:
        except requests.exceptions.ReadTimeout:
            tracks = None
        if tracks is not None and len(tracks.get("items")) > 0:
            items = tracks.get("items")
            attempts_best_matches += [
                return_best_match(items, best_match_template.copy(), *attempt)
            ]

    if attempts_best_matches:
        # Find best match across all the attempts
        scores = [i["Match Score"] for i in attempts_best_matches]
        optimal = np.argmax(scores)
        return attempts_best_matches[optimal]
    else:
        return best_match_template


def sync_playlist(
    sp: spotipy.Spotify,
    playlist_name: str,
    playlist_songs: list[tuple],
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

    songs_to_sync, flag_already_synced = get_songs_to_sync(filepath, playlist_songs)

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
    for song_name, song_artist, album_name in songs_to_sync:
        count += 1
        matched_songs += [get_best_match(sp, song_name, song_artist, album_name)]
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
