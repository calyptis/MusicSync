"""Data models for songs, similarity scores, and song matches."""

from typing import TypedDict

from pydantic import BaseModel, ConfigDict


class Song(BaseModel):
    """Song information."""

    # Frozen so instances are hashable and can be used in sets/dict keys.
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    artist: str | None = None
    album: str | None = None
    track_id: str | int | None = None

    def as_search_query(self) -> str:
        """Render the song as a free-text query for the Spotify search endpoint."""
        return f"{self.name} {self.artist} {self.album}".strip()

    def __repr__(self):
        return self.as_search_query()


class Similarity(BaseModel):
    """Song similarity scores."""

    total_similarity: float | None = None
    song_similarity: float | None = None
    artist_similarity: float | None = None
    album_similarity: float | None = None


class SongMatch(BaseModel):
    """Spotify match for Apple Music song."""

    apple_info: Song
    spotify_info: Song
    similarity: Similarity


class SongsToSync(TypedDict):
    to_search: list[Song]
    to_assign: list[str]
