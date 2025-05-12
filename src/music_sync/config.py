import os
import pathlib


MAIN_DIR = pathlib.Path(
    os.path.split(pathlib.Path(__file__).parent.parent.resolve())[0]
)
DATA_DIR = MAIN_DIR / "data"
LOG_DIR = DATA_DIR / "sync_logs"
LOG_FILE = LOG_DIR / "database.json"
APPLE_MUSIC_DIR = DATA_DIR / "apple_music"
CREDENTIALS_PATH = MAIN_DIR / "credentials" / "credentials.json"
ALLOWED_EXTENSIONS = {"xml"}
SCOPES_LIST = [
    "user-library-modify",
    "user-library-read",
    "playlist-modify-private",
    "playlist-read-private",
    "playlist-modify-public",
]
SCOPES = " ".join(SCOPES_LIST)

# Mapping between class `` and the columns in the sync log CSV files
COLUMN_MAPPING = {
    "apple_info.name": "Apple Song Name",
    "apple_info.artist": "Apple Artist",
    "apple_info.album": "Apple Album",
    "spotify_info.name": "Spotify Song Name",
    "spotify_info.artist": "Spotify Artist",
    "spotify_info.album": "Spotify Album",
    "spotify_info.track_id": "Spotify Track ID",
    "similarity.total_similarity": "Match Score",
    "similarity.song_name_similarity": "Song Match Score",
    "similarity.artist_name_similarity": "Artist Match Score",
    "similarity.album_name_similarity": "Album Match Score",
}
