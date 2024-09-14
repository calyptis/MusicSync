import os
from music_sync.config import APPLE_MUSIC_DIR

APPLE_MUSIC_LIBRARY_FILE = os.path.join(APPLE_MUSIC_DIR, "Library.xml")
SONG_FILE = os.path.join(APPLE_MUSIC_DIR, "songs.csv")
RAW_PLAYLIST_FILE = os.path.join(APPLE_MUSIC_DIR, "playlists.json")
PREPARED_PLAYLIST_FILE_NAME = "parsed_playlists.json"
PREPARED_PLAYLIST_FILE = os.path.join(APPLE_MUSIC_DIR, PREPARED_PLAYLIST_FILE_NAME)
EXCLUDE_PLAYLIST_FILE = os.path.join(APPLE_MUSIC_DIR, "exclude_playlists.txt")
OUT_DIR = os.path.split(SONG_FILE)[0]
