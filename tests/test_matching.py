"""Tests for track scoring and best-match selection."""

from music_sync.classes import Song
from music_sync.spotify.matching import score_tracks, select_best_match


def make_track(track_id: str, name: str, artist: str, album: str) -> dict:
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": artist}],
        "album": {"name": album},
    }


def test_score_tracks_pairs_each_track_with_its_own_score():
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")
    tracks = [
        make_track("a", "Something Else", "Other Band", "Other Album"),
        make_track("b", "Caruso", "Fiorella Mannoia", "A te"),
    ]

    scored = score_tracks(tracks, song)

    assert [track["id"] for track, _ in scored] == ["a", "b"]
    assert scored[1][1].total_similarity > scored[0][1].total_similarity


def test_score_tracks_skips_none_entries():
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")
    tracks = [None, make_track("b", "Caruso", "Fiorella Mannoia", "A te")]

    scored = score_tracks(tracks, song)

    assert len(scored) == 1
    assert scored[0][0]["id"] == "b"


def test_select_best_match_is_unaffected_by_leading_none_entries():
    """A dropped None must not shift the score/track alignment."""
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")
    exact = make_track("exact", "Caruso", "Fiorella Mannoia", "A te")
    other = make_track("other", "Unrelated", "Nobody", "Nowhere")

    without_none = select_best_match([exact, other], song)
    with_none = select_best_match([None, exact, other], song)

    assert without_none.spotify_info.track_id == "exact"
    assert with_none.spotify_info.track_id == "exact"


def test_select_best_match_returns_empty_match_when_nothing_scorable():
    song = Song(name="Caruso", artist="Fiorella Mannoia", album="A te")

    match = select_best_match([None], song)

    assert match.spotify_info.track_id is None
    assert match.similarity.total_similarity is None
