"""Define match."""
from pydantic import BaseModel
from typing import Optional, Union


class Song(BaseModel):
    """Song information."""

    name: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    track_id: Optional[Union[str, int]] = None

    class Config:
        # Make the instance hashable
        frozen = True

    def __repr__(self):
        return f"{self.name} {self.artist} {self.album}".strip()


class Similarity(BaseModel):
    """Song similarity scores."""

    total_similarity: Optional[float] = None
    song_name_similarity: Optional[float] = None
    artist_name_similarity: Optional[float] = None
    album_name_similarity: Optional[float] = None


class SongMatch(BaseModel):
    """Spotify match for Apple Music song."""

    apple_info: Song
    spotify_info: Song
    similarity: Similarity
