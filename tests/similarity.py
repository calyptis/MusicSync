from music_sync.classes import Song
from music_sync.spotify.similarity import measure_query_similarity


if __name__ == "__main__":
    song = Song(
        name="All Eyez On Me (feat. Big Syke)", artist="2Pac", album="All Eyez On Me"
    )
    match = Song(name="All Eyez On Me", artist="2Pac", album="All Eyez On Me")
    similarity = measure_query_similarity(song_to_match=song, match=match)
    print(similarity)
