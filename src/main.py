import os
import json
from src.spotify.sync import get_spotipy_instance, sync_playlist
from src.apple_music.config import PREPARED_PLAYLIST_FILE, EXCLUDE_PLAYLIST_FILE
from src.apple_music.library import write_apple_music_library, prepare_playlists
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


if __name__ == '__main__':

    logging.info("Parsing Apple Music library\n==============")
    write_apple_music_library()
    prepare_playlists()

    logging.info("Sync to Spotify\n==============")
    # Sync to Spotify
    sp = get_spotipy_instance()
    apple_playlists = json.load(open(PREPARED_PLAYLIST_FILE, "rb"))
    playlists_to_exclude = []
    if os.path.exists(EXCLUDE_PLAYLIST_FILE):
        with open(EXCLUDE_PLAYLIST_FILE, "r", encoding="utf-8") as f:
            playlists_to_exclude = f.read().split("\n")

    subset_apple_playlists = {k: v for k, v in apple_playlists.items() if k not in playlists_to_exclude}

    for playlist_name, playlist_tracks in apple_playlists.items():
        sync_playlist(sp, playlist_name, playlist_tracks)
