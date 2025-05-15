from music_sync.classes import Song
from music_sync.spotify.matching import get_best_match
from music_sync.spotify.utils import get_spotipy_instance

if __name__ == "__main__":
    song = Song(
        name="All Eyez On Me (feat. Big Syke)", artist="2Pac", album="All Eyez On Me"
    )
    sp = get_spotipy_instance()
    best_match = get_best_match(sp, song)
    print(best_match)
