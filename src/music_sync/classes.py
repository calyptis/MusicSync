"""Define match."""
from pydantic import BaseModel, Field
from typing import Optional


class Song(BaseModel):
    """Song information."""

    name: str
    artist: str
    album: str
    track_id: Optional[str] = None

    class Config:
        # Make the instance hashable
        frozen = True


class Similarity(BaseModel):
    """Song similarity scores."""

    total_similarity: float
    song_name_similarity: float
    artist_name_similarity: float
    album_name_similarity: Optional[float]


class SongMatch(BaseModel):
    """Spotify match for Apple Music song."""

    apple_info: Song
    spotify_info: Song
    similarity: Optional[Similarity]
