"""Tests for alternate Spotify query generation."""

from music_sync.classes import Song
from music_sync.spotify.utils import clean_string, generate_alternate_queries


def test_clean_string_lowercases_and_strips():
    assert clean_string("  Caruso  ") == "caruso"


def test_feat_in_title_produces_a_query_without_the_collaborator():
    song = Song(
        name="All Eyez On Me (feat. Big Syke)", artist="2Pac", album="All Eyez On Me"
    )

    names = {attempt.name for attempt in generate_alternate_queries(song)}

    assert "All Eyez On Me" in names


def test_remastered_in_title_produces_a_query_without_the_suffix():
    song = Song(
        name="Let It Be (Remastered 2009)", artist="The Beatles", album="Let It Be"
    )

    names = {attempt.name for attempt in generate_alternate_queries(song)}

    assert "Let It Be" in names


def test_ampersand_artist_produces_first_artist_and_comma_variants():
    song = Song(
        name="Spinning Away", artist="Brian Eno & John Cale", album="Wrong Way Up"
    )

    artists = {attempt.artist for attempt in generate_alternate_queries(song)}

    assert "Brian Eno" in artists
    assert "Brian Eno, John Cale" in artists


def test_plain_song_generates_no_alternates():
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")

    assert generate_alternate_queries(song) == []


def test_every_alternate_has_an_album_free_variant():
    """Album names like '<song> - Single' often prevent a match."""
    song = Song(
        name="All Eyez On Me (feat. Big Syke)", artist="2Pac", album="All Eyez On Me"
    )

    attempts = generate_alternate_queries(song)

    assert any(attempt.album == "" for attempt in attempts)
