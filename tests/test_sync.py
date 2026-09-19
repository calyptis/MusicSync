"""Tests for sync-log bookkeeping."""

import pandas as pd
import pytest

from music_sync.classes import Similarity, Song, SongMatch
from music_sync.config import config
from music_sync.spotify.sync import build_match_log, load_sync_log, select_songs_to_sync


def test_select_songs_to_sync_splits_new_and_already_matched_songs():
    known = Song(name="Caruso", artist="Fiorella Mannoia", album="A te", track_id=1)
    unknown = Song(name="Roxanne", artist="The Police", album="Reggatta", track_id=2)
    log_data = [
        {
            "apple_track_id": 1,
            "spotify_track_id": "sp1",
            "apple_playlist": ["Other Playlist"],
        }
    ]

    updated_log, songs_to_sync = select_songs_to_sync(
        log_data, [known, unknown], "New Playlist"
    )

    assert songs_to_sync["to_assign"] == ["sp1"]
    assert songs_to_sync["to_search"] == [unknown]
    assert updated_log[0]["apple_playlist"] == ["Other Playlist", "New Playlist"]


def test_select_songs_to_sync_does_not_reassign_current_playlist():
    known = Song(name="Caruso", artist="Fiorella Mannoia", album="A te", track_id=1)
    log_data = [
        {"apple_track_id": 1, "spotify_track_id": "sp1", "apple_playlist": ["Mine"]}
    ]

    _, songs_to_sync = select_songs_to_sync(log_data, [known], "Mine")

    assert songs_to_sync["to_assign"] == []
    assert songs_to_sync["to_search"] == []


def make_match(track_id: str, total_similarity: float) -> SongMatch:
    return SongMatch(
        apple_info=Song(name="n", artist="a", album="al", track_id=1),
        spotify_info=Song(name="n", artist="a", album="al", track_id=track_id),
        similarity=Similarity(
            total_similarity=total_similarity,
            song_similarity=1.0,
            artist_similarity=1.0,
            album_similarity=1.0,
        ),
    )


def test_build_match_log_drops_poor_matches_and_duplicates():
    threshold = config.sync.similarity_threshold
    matches = [
        make_match("good", threshold),
        make_match("poor", threshold - 0.2),
        make_match("already_there", 1.0),
    ]

    df = build_match_log(matches, "My Playlist", {"already_there"}, log_data=[])

    assert df["spotify_track_id"].tolist() == ["good"]
    assert df["apple_playlist"].tolist() == [["My Playlist"]]


def test_build_match_log_rejects_columns_that_do_not_match_the_log():
    with pytest.raises(ValueError, match="wrong column names"):
        build_match_log(
            [make_match("good", 1.0)],
            "My Playlist",
            set(),
            log_data=[{"unexpected_column": 1}],
        )


def test_load_sync_log_returns_placeholder_when_file_is_absent(tmp_path):
    assert load_sync_log(tmp_path / "missing.json") == [{}]


def test_load_sync_log_reads_existing_file(tmp_path):
    log_file = tmp_path / "database.json"
    log_file.write_text('[{"apple_track_id": 1}]')

    assert load_sync_log(log_file) == [{"apple_track_id": 1}]


def test_build_match_log_columns_match_the_configured_mapping():
    """Guards the SongMatch -> log-column contract in config.sync.column_mapping."""
    df = build_match_log([make_match("good", 1.0)], "My Playlist", set(), log_data=[])

    expected = set(config.sync.column_mapping.values()) | {"apple_playlist"}
    assert set(df.columns) == expected
    assert not any("." in c for c in df.columns), "raw nested names leaked through"


def test_build_match_log_is_empty_frame_not_error_when_all_matches_are_poor():
    df = build_match_log([make_match("poor", 0.0)], "My Playlist", set(), log_data=[])

    assert isinstance(df, pd.DataFrame)
    assert df.empty
