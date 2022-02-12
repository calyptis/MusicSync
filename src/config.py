import os
import pathlib


MAIN_DIR = os.path.split(pathlib.Path(__file__).parent.resolve())[0]

DATA_DIR = os.path.join(MAIN_DIR, "data")

LOG_DIR = os.path.join(DATA_DIR, "sync_logs")

APPLE_MUSIC_DIR = os.path.join(DATA_DIR, "apple_music")

CREDENTIALS_PATH = os.path.join(*[MAIN_DIR, "credentials", "credentials.json"])

ALLOWED_EXTENSIONS = {'xml'}

SCOPES_LIST = [
    "user-library-modify",
    "user-library-read",
    "playlist-modify-private",
    "playlist-read-private",
    "playlist-modify-public"
]

SCOPES = " ".join(SCOPES_LIST)
