import re
import requests

import spotipy
import numpy as np

from music_sync.classes import Song, SongMatch, Similarity
from music_sync.spotify.similarity import measure_similarity
from music_sync.spotify.utils import generate_alternate_queries, timeout_wrapper


def get_best_match(sp: spotipy.Spotify, song: Song) -> SongMatch:
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
    attempts += generate_alternate_queries(song)

    attempts_best_matches = []
    for attempt in attempts:
        query = " ".join([i.__repr__() for i in attempt])
        query = re.sub(r"\s+", " ", query).strip()
        try:
            tracks = timeout_wrapper(lambda: sp.search(query, limit=15).get("tracks"))
        except (spotipy.exceptions.SpotifyException, requests.exceptions.ReadTimeout):
            tracks = None
        if tracks is not None and len(tracks.get("items")) > 0:
            items = tracks.get("items")
            attempts_best_matches += [find_best_match(items, attempt)]

    if attempts_best_matches:
        # Find best match across all the attempts
        scores = [i.similarity.total_similarity for i in attempts_best_matches]
        optimal = np.argmax(scores)
        return attempts_best_matches[optimal]
    else:
        # No valid match
        return SongMatch(apple_info=song, spotify_info=Song(), similarity=Similarity())


def find_best_match(tracks: list, song: Song) -> SongMatch:
    """
    Returns the best match according to string similarities amongst the API results.

    Parameters
    ----------
    tracks
        All results from the API search request
    song: Song :
        Song to match.

    Returns
    -------
    best_match
    """
    matched_items = evaluate_matches(tracks, song)
    best_match_idx = np.argmax([i.total_similarity for i in matched_items])
    best_match_item = tracks[best_match_idx]

    spotify_info = Song(
        name=best_match_item.get("name"),
        artist=" ".join([i.get("name") for i in best_match_item.get("artists")]),
        album=best_match_item.get("album").get("name"),
        track_id=best_match_item.get("id"),
    )

    match_similarity = matched_items[best_match_idx]

    return SongMatch(
        apple_info=song,
        spotify_info=spotify_info,
        similarity=match_similarity,
    )


def evaluate_matches(tracks: list, song: Song) -> list[Similarity]:
    """
    Calculates similarities between the original query and all returned matches.
    These similarities are at a later stage used to identify the best match.

    Parameters
    ----------
    tracks
        All results from the API search request
    song:
        Apple Music song instance to match.

    Returns
    -------
    matched_items
        List of tuples containing similarity metrics as returned by query_similarity
    """
    matched_items = [
        measure_similarity(
            song_to_match=song,
            match=Song(
                name=str(item.get("name", "")),
                artist=" ".join([str(i.get("name", "")) for i in item.get("artists")]),
                album=str(item.get("album").get("name", "")),
            ),
        )
        for item in tracks
        if item is not None
    ]
    return matched_items
