"""Functions for measuring string similarity between Apple Music and Spotify songs."""

import numpy as np
from rapidfuzz import fuzz

from music_sync.spotify.utils import clean_string
from music_sync.classes import Song, Similarity
from music_sync.config import config


def string_similarity(a: str, b: str) -> float:
    """
    Measure the similarity between two strings using rapidfuzz.

    Parameters
    ----------
    a: str:
        String A.
    b: str :
        String B.

    Returns
    -------
    score: float :
        Similarity score [0, 1].
    """
    score = round(fuzz.ratio(a, b) / 100, 2)
    return score


def measure_similarity(song_to_match: Song, match: Song) -> Similarity:
    """
    Calculate string similarity matches between the original query and a match returned by the API.
    Final similarity is based on individual similarities of song, artist and album (if available).
    Song similarity has a larger weight.

    Parameters
    ----------
    song_to_match: Song:
        Song instance of original song to match.
    match: Song:
        Song instance of matched Spotify song.

    Returns
    -------
    similarities: Similarity :
        Similarities for (aggregate, song, artist, album)
    """
    # Song similarity
    song_similarity = string_similarity(
        clean_string(song_to_match.name), clean_string(match.name)
    )
    # Artist similarity
    artist_similarity = string_similarity(
        clean_string(song_to_match.artist), clean_string(match.artist)
    )
    # Album similarity
    album_similarity = string_similarity(
        clean_string(song_to_match.album), clean_string(match.album)
    )
    # If no album name was provided => exclude it from the aggregate
    has_album = bool(song_to_match.album)
    if has_album:
        total_similarity = np.dot(
            [song_similarity, artist_similarity, album_similarity],
            config.sync.weights_song_artist_album,
        )
    else:
        total_similarity = np.dot(
            [song_similarity, artist_similarity],
            config.sync.weights_song_artist,
        )

    return Similarity(
        total_similarity=float(total_similarity),
        song_similarity=song_similarity,
        artist_similarity=artist_similarity,
        album_similarity=album_similarity if has_album else None,
    )
