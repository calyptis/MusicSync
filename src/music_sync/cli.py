"""Main CLI for end-to-end Apple Music library parsing and Spotify playlist syncing."""

import os
import json

from loguru import logger

from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance
from music_sync.config import config
from music_sync.apple_music.cli import main as parse_apple_music_library


def main():
    logger.info("Parse Apple Music library")
    parse_apple_music_library()

    logger.info("Sync to Spotify")
    # Sync to Spotify
    sp = get_spotipy_instance()
    apple_playlists = json.load(open(config.apple_music.prepared_playlist_file, "rb"))
    playlists_to_exclude = []
    if os.path.exists(config.apple_music.exclude_playlist_file):
        with open(config.apple_music.exclude_playlist_file, "r", encoding="utf-8") as f:
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
