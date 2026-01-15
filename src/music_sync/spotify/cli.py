"""CLI for syncing prepared Apple Music playlists to Spotify."""

import click
import json

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
    playlists = json.load(open(config.apple_music.prepared_playlist_file, "r"))
    sp_instance = get_spotipy_instance()
    if playlist_name in playlists:
        sync_playlist(sp_instance, playlist_name, playlists[playlist_name])
    else:
        raise Exception("Specified playlist does not exist. Perhaps there's a typo?")


if __name__ == "__main__":
    main()
