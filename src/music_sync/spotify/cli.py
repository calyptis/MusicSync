"""CLI for syncing prepared Apple Music playlists to Spotify."""

import json

import click

from music_sync.config import config
from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance


@click.command()
@click.option(
    "--name",
    "playlist_name",
    required=True,
    type=str,
    help="Name of the playlist to sync.",
)
def main(playlist_name: str):
    """Sync a single, already parsed Apple Music playlist to Spotify."""
    with open(config.apple_music.prepared_playlist_file, "r") as f:
        playlists = json.load(f)

    if playlist_name not in playlists:
        raise click.BadParameter(
            f"No parsed playlist named {playlist_name!r}. "
            f"Available playlists: {', '.join(sorted(playlists))}",
            param_hint="--name",
        )

    sp_instance = get_spotipy_instance()
    sync_playlist(sp_instance, playlist_name, playlists[playlist_name])


if __name__ == "__main__":
    main()
