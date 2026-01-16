"""Functions for measuring string similarity between Apple Music and Spotify songs."""

import numpy as np
from rapidfuzz import fuzz

from music_sync.spotify.utils import clean_string
from music_sync.classes import Song, Similarity
from music_sync.config import config


def similarity_func(a: str, b: str) -> float:
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
    song_similarity = similarity_func(
        clean_string(song_to_match.name), clean_string(match.name)
    )
    # Artist similarity
    artist_similarity = similarity_func(
        clean_string(song_to_match.artist), clean_string(match.artist)
    )
    # Album similarity
    album_similarity = similarity_func(
        clean_string(song_to_match.album), clean_string(match.album)
    )
    # The three types of similarities
    similarities = np.array([song_similarity, artist_similarity, album_similarity])

    # If no album name => ignore its similarity
    if not song_to_match.album or song_to_match.album == "":
        album_similarity = None
        total_similarity = sum(similarities[:-1] * config.sync.weights_song_artist)
    else:
        total_similarity = sum(similarities * config.sync.weights_song_artist_album)

    return Similarity(
        total_similarity=total_similarity,
        song_similarity=song_similarity,
        artist_similarity=artist_similarity,
        album_similarity=album_similarity,
    )
