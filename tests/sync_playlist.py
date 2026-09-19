import json

from music_sync.config import config
from music_sync.spotify.sync import sync_playlist
from music_sync.spotify.utils import get_spotipy_instance

if __name__ == "__main__":
    playlists = json.load(open(config.apple_music.prepared_playlist_file, "r"))
    sp_instance = get_spotipy_instance()
    sync_playlist(sp_instance, "Esperanto", playlists["Esperanto"])
