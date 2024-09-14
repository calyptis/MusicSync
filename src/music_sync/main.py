import os
import logging
import json

from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance
from music_sync.apple_music.config import PREPARED_PLAYLIST_FILE, EXCLUDE_PLAYLIST_FILE
from music_sync.apple_music.main import main as prepare_library


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def main():
    logging.info("Parsing Apple Music library\n==============")
    prepare_library()

    logging.info("Sync to Spotify\n==============")
    # Sync to Spotify
    sp = get_spotipy_instance()
    apple_playlists = json.load(open(PREPARED_PLAYLIST_FILE, "rb"))
    playlists_to_exclude = []
    if os.path.exists(EXCLUDE_PLAYLIST_FILE):
        with open(EXCLUDE_PLAYLIST_FILE, "r", encoding="utf-8") as f:
            playlists_to_exclude = f.read().split("\n")

    subset_apple_playlists = {
        k: v for k, v in apple_playlists.items() if k not in playlists_to_exclude
    }
    subset_apple_playlists = dict(
        sorted(subset_apple_playlists.items(), key=lambda item: len(item[-1]))
    )

    for playlist_name, playlist_tracks in subset_apple_playlists.items():
        sync_playlist(sp, playlist_name, playlist_tracks)


if __name__ == "__main__":
    main()
