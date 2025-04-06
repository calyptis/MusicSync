from music_sync.classes import Song
from music_sync.spotify.utils import generate_alternate_queries


if __name__ == "__main__":
    song = Song(
        name="All Eyez On Me (feat. Big Syke)", artist="2Pac", album="All Eyez On Me"
    )
    alternatives = generate_alternate_queries(song)
    print(alternatives)
