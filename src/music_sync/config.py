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

# Threshold for similarity metric
# Any spotify match below this value will not be synced with a given playlist
SYNCING_THRESHOLD = 0.86

# Mapping between class `` and the columns in the log file
# TODO: Do this programmatically
COLUMN_MAPPING = {
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
