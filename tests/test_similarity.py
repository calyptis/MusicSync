"""Tests for the string similarity metrics."""

import pytest

from music_sync.classes import Song
from music_sync.spotify.similarity import measure_similarity, string_similarity

_ONE = 1.0
_ZERO = 0.0


def test_string_similarity_identical_strings():
    assert string_similarity("caruso", "caruso") == _ONE


def test_string_similarity_disjoint_strings():
    assert string_similarity("abc", "xyz") == _ZERO


def test_measure_similarity_weights_song_artist_and_album():
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")
    match = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")

    similarity = measure_similarity(song_to_match=song, match=match)

    assert similarity.total_similarity == pytest.approx(_ONE)
    assert similarity.album_similarity == _ONE


def test_measure_similarity_ignores_album_when_query_has_none():
    """With no album on the query, album similarity is excluded from the total."""
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="")
    match = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")

    similarity = measure_similarity(song_to_match=song, match=match)

    assert similarity.album_similarity is None
    assert similarity.total_similarity == pytest.approx(_ONE)
