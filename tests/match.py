import json

from music_sync.classes import Song
from music_sync.spotify.matching import get_best_match
from music_sync.spotify.utils import get_spotipy_instance

if __name__ == "__main__":
    songs = [
        Song(
            name="All Eyez On Me (feat. Big Syke)",
            artist="2Pac",
            album="All Eyez On Me",
        ),
        Song(name="Caruso", artist="Fiorella Mannoia", album="A te (Special Edition)"),
    ]
    sp = get_spotipy_instance()
    for song in songs:
        best_match = get_best_match(sp, song)
        print(json.dumps(best_match.model_dump(), indent=4))
