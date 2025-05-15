import numpy as np
from rapidfuzz import fuzz

from music_sync.spotify.utils import clean_string
from music_sync.classes import Song, Similarity


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
    Calculates string similarity matches between the original query and a match returned by the API.
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
    similarities
        Tuple of similarities for (aggregate, song, artist, album)
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
    # Setting the weight of each similarity
    # (song, artist, album)
    # Getting the song right is slightly more important
    w = np.array([0.4, 0.3, 0.3])
    # In case no album was provided, exclude it from aggregate similarity
    ww = np.array([0.6, 0.4])
    # If no album name => ignore its similarity
    if song_to_match.album == "":
        total_similarity = sum(similarities[:-1] * ww)
    else:
        total_similarity = sum(similarities * w)

    return Similarity(
        total_similarity=total_similarity,
        song_similarity=song_similarity,
        artist_similarity=artist_similarity,
        album_similarity=album_similarity,
    )
