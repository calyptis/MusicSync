import re
import requests

import spotipy
import numpy as np

from music_sync.classes import Song
from music_sync.spotify.similarity import measure_query_similarity
from music_sync.spotify.utils import timeout_wrapper, generate_additional_attempts


def get_best_match(sp: spotipy.Spotify, song: Song) -> dict:
    """
    Returns the best Spotify song match for a given Apple Music song, if available.

    Parameters
    ----------
    sp
        Spotipy instance
    song: Song:
        Song instance to match.

    Returns
    -------
    best_match : dict
        Information on best match, including string similarity with original query information
        All of this information will be written to the CSV log file after a playlist was successfully synced.
    """

    attempts = [song]

    # Sometimes there is no match if album name is included, e.g.
    # bloody valentine	Machine Gun Kelly	bloody valentine - Single
    attempts += [Song(name=song.name, artist=song.artist, album="")]
    attempts += generate_additional_attempts(song)

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


def return_best_match(
    tracks: list,
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
    matched_items = evaluate_matches(tracks, song_name, artist_name, album_name)
    best_match_idx = np.argmax([i[0] for i in matched_items])
    best_match_item = tracks[best_match_idx]

    spotify_info = Song(
        name=best_match_item.get("name"),
        artist=" ".join([i.get("name") for i in best_match_item.get("artists")]),
        album=best_match_item.get("album").get("name"),
        track_id=best_match_item.get("id"),
    )

    best_match["Match Score"] = matched_items[best_match_idx][0]
    best_match["Song Match Score"] = matched_items[best_match_idx][1]
    best_match["Artist Match Score"] = matched_items[best_match_idx][2]
    best_match["Album Match Score"] = matched_items[best_match_idx][-1]
    return best_match


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
