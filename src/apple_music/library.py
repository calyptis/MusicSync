import pandas as pd
import xml.etree.ElementTree as ElTr
import json
from src.apple_music.config import APPLE_MUSIC_LIBRARY_FILE, SONG_FILE, RAW_PLAYLIST_FILE, PREPARED_PLAYLIST_FILE


def parse_apple_music_library(filename: str = APPLE_MUSIC_LIBRARY_FILE) -> tuple[pd.DataFrame, dict]:
    """
    Parses Apple Music library, which is exported using File -> Library -> Export Library...
    It creates two objects, a dataframe containing all relevant information of all the songs in the library
    and a dictionary containing track IDs for each playlist.

    Parameters
    ----------
    filename
        XML library file

    Returns
    -------
    songs_df
        Dataframe containing pertinent information about songs in a user's library
    playlists
        Dictionary in the form {playlist_name: [playlist_tracks, ...]}
    """
    tree = ElTr.parse(filename)
    root = tree.getroot()
    # Contains metadata in <key>
    library = root.find("dict")

    # /// SONGS \\\
    # Song list at next dict attribute
    song_list = library.find("dict")
    # Each song has first an ID entry <key> and then its info <dict>
    songs = song_list.findall('dict')
    # Load songs into a dataframe
    songs_df = pd.DataFrame(list(map(_get_entry, songs)))
    # Get correct dtypes
    tags = {}
    for s in songs:
        for i in range(0, len(s) - 1, 2):
            e = s[i].text
            t = s[i + 1].tag
            if e not in tags:
                tags[e] = t
    # Transform columns to have correct type
    for col in songs_df.columns:
        if tags[col] == 'integer':
            songs_df[col] = pd.to_numeric(songs_df[col])
        if tags[col] == 'date':
            songs_df[col] = pd.to_datetime(songs_df[col], yearfirst=True)

    # /// PLAYLISTS \\\
    playlists_data = library.findall("array")[-1].findall("dict")
    playlists = {}
    for p in playlists_data:
        p_name = p.find("string").text
        track_list_ = p.findall("array")
        track_list = None
        if track_list_:
            try:
                track_list_ = track_list_[-1].findall("dict")
                if track_list_:
                    track_list = [int(i.find("integer").text) for i in track_list_]
            except KeyError:
                pass
        playlists[p_name] = track_list

    return songs_df, playlists


def write_apple_music_library():
    """
    Parses Apply Music Library file and stores to information to disk.

    Returns
    -------

    """
    songs, playlists = parse_apple_music_library(APPLE_MUSIC_LIBRARY_FILE)
    songs.to_csv(SONG_FILE, index=False)
    json.dump(playlists, open(RAW_PLAYLIST_FILE, "w"))


def prepare_playlists():
    """
    Transforms the raw playlist file into a playlist file that contains
    a song's name, artist and album.
    This information is then used to create a query to Spotify's API when syncing playlists.

    Returns
    -------
    """
    apple_music_songs = pd.read_csv(SONG_FILE).set_index("Track ID")
    apple_music_playlists = json.load(open(RAW_PLAYLIST_FILE, "rb"))
    parsed_playlists = {
        k: list(apple_music_songs.loc[v, ["Name", "Artist", "Album"]].apply(tuple, axis=1).values)
        for k, v in apple_music_playlists.items()
    }
    json.dump(parsed_playlists, open(PREPARED_PLAYLIST_FILE, "w"))


def _get_entry(song) -> dict:
    """
    Parses an XML song tag

    Parameters
    ----------
    song

    Returns
    -------
    """
    return {song[i].text: song[i+1].text for i in range(0, len(song) - 1, 2)}


if __name__ == '__main__':
    write_apple_music_library()
    prepare_playlists()
