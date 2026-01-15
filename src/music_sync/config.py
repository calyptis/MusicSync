"""Global configuration constants, directory paths, and settings for MusicSync."""

import pathlib
from typing import ClassVar

import numpy as np
from pydantic import BaseModel, Field

# Base directories
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
APPLE_MUSIC_DIR = DATA_DIR / "apple_music"
LOG_DIR = DATA_DIR / "sync_logs"
CREDENTIALS_DIR = ROOT_DIR / "credentials"


class PathsConfig(BaseModel):
    """Directory and file path configuration."""

    main_dir: pathlib.Path = ROOT_DIR
    data_dir: pathlib.Path = DATA_DIR
    log_dir: pathlib.Path = LOG_DIR
    apple_music_dir: pathlib.Path = APPLE_MUSIC_DIR


class SpotifyConfig(BaseModel):
    """Spotify API configuration."""

    scopes_list: ClassVar[list[str]] = [
        "user-library-modify",
        "user-library-read",
        "playlist-modify-private",
        "playlist-read-private",
        "playlist-modify-public",
    ]
    scopes: str = " ".join(scopes_list)

    credentials_file: pathlib.Path = CREDENTIALS_DIR / "credentials.json"


class AppleMusicConfig(BaseModel):
    """Apple Music-specific configuration."""

    library_file: pathlib.Path = APPLE_MUSIC_DIR / "Library.xml"
    song_file: pathlib.Path = APPLE_MUSIC_DIR / "songs.csv"
    raw_playlist_file: pathlib.Path = APPLE_MUSIC_DIR / "playlists.json"
    prepared_playlist_file: pathlib.Path = APPLE_MUSIC_DIR / "parsed_playlists.json"
    exclude_playlist_file: pathlib.Path = APPLE_MUSIC_DIR / "exclude_playlists.txt"


class SyncConfig(BaseModel):
    """Music synchronization configuration."""

    # Threshold for similarity metric
    # Any spotify match below this value will not be synced with a given playlist
    similarity_threshold: float = Field(default=0.86, ge=0.0, le=1.0)

    allowed_extensions: set[str] = Field(default={"xml"})

    # Mapping between class attributes and the columns in the log file
    # TODO: Do this programmatically
    column_mapping: ClassVar[dict[str, str]] = {
        "apple_info.name": "apple_song_name",
        "apple_info.artist": "apple_artist",
        "apple_info.album": "apple_album",
        "spotify_info.name": "spotify_song_name",
        "spotify_info.artist": "spotify_artist",
        "spotify_info.album": "spotify_album",
        "spotify_info.track_id": "spotify_track_id",
        "similarity.total_similarity": "total_similarity",
        "similarity.song_similarity": "song_similarity",
        "similarity.artist_similarity": "artist_similarity",
        "similarity.album_similarity": "album_similarity",
        "apple_info.track_id": "apple_track_id",
    }

    log_file: pathlib.Path = LOG_DIR / "database.json"

    # Setting the weight of each similarity
    # (song, artist, album)
    # Getting the song right is slightly more important
    weights_song_artist_album: ClassVar[np.ndarray] = np.array([0.4, 0.3, 0.3])

    # In case no album was provided, exclude it from aggregate similarity
    weights_song_artist: ClassVar[np.ndarray] = np.array([0.6, 0.4])


class Config(BaseModel):
    """Main configuration container for MusicSync."""

    paths: PathsConfig = Field(default_factory=PathsConfig)
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    apple_music: AppleMusicConfig = Field(default_factory=AppleMusicConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)


# Global config instance
config = Config()
