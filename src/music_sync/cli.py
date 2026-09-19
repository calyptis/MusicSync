"""Main CLI for end-to-end Apple Music library parsing and Spotify playlist syncing."""

import json

import click
from loguru import logger

from music_sync.apple_music.parse_library import (
    prepare_playlists_for_syncing,
    save_apple_music_library,
)
from music_sync.config import config
from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance


def load_playlists_to_exclude() -> set[str]:
    """Read the names of playlists that should be skipped, if the file exists."""
    exclude_file = config.apple_music.exclude_playlist_file
    if not exclude_file.exists():
        return set()
    return {
        line.strip()
        for line in exclude_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


@click.command()
def main():
    """Parse the Apple Music library and sync every playlist to Spotify."""
    logger.info("Parse Apple Music library")
    save_apple_music_library()
    prepare_playlists_for_syncing()

    logger.info("Sync to Spotify")
    sp = get_spotipy_instance()
    with open(config.apple_music.prepared_playlist_file, "rb") as f:
        apple_playlists = json.load(f)

    playlists_to_exclude = load_playlists_to_exclude()
    playlists_to_sync = {
        name: tracks
        for name, tracks in apple_playlists.items()
        if name not in playlists_to_exclude
    }
    # Sync the shortest playlists first, so failures surface quickly.
    playlists_to_sync = dict(
        sorted(playlists_to_sync.items(), key=lambda item: len(item[-1]))
    )

    for playlist_name, playlist_tracks in playlists_to_sync.items():
        sync_playlist(sp, playlist_name, playlist_tracks)


if __name__ == "__main__":
    main()
