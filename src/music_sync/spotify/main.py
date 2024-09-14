import argparse
import json

from music_sync.apple_music.config import PREPARED_PLAYLIST_FILE
from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance


def main(playlist_name: str):
    playlists = json.load(open(PREPARED_PLAYLIST_FILE, "r"))
    sp_instance = get_spotipy_instance()
    if playlist_name in playlists:
        sync_playlist(sp_instance, playlist_name, playlists[playlist_name])
    else:
        raise Exception("Specified playlist does not exist. Perhaps there's a typo?")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # noinspection PyTypeChecker
    parser.add_argument("--name", type=str, nargs=None)
    args = parser.parse_args()
    chosen_playlist_name = args.name
    main(chosen_playlist_name)
