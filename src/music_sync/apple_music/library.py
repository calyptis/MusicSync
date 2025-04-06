import json
import logging

import pandas as pd
import xml.etree.ElementTree as ElTr

from music_sync.apple_music.config import (
    APPLE_MUSIC_LIBRARY_FILE,
    SONG_FILE,
    RAW_PLAYLIST_FILE,
    PREPARED_PLAYLIST_FILE,
)
from music_sync.apple_music.utils import get_entry


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def parse_apple_music_library(
    filename: str = APPLE_MUSIC_LIBRARY_FILE,
) -> tuple[pd.DataFrame, dict]:
    """
    Parses Apple Music library, which is exported using File -> Library -> Export Library...
    It creates two objects, a dataframe containing all relevant information of all the songs in the library
    and a dictionary containing the track IDs for each playlist.

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
    songs = song_list.findall("dict")
    # Load songs into a dataframe
    df_songs = pd.DataFrame(list(map(get_entry, songs)))
    # Get correct dtypes
    tags = {}
    for s in songs:
        for i in range(0, len(s) - 1, 2):
            e = s[i].text
            t = s[i + 1].tag
            if e not in tags:
                tags[e] = t
    # Transform columns to have correct type
    for col in df_songs.columns:
        if tags[col] == "integer":
            df_songs[col] = pd.to_numeric(df_songs[col])
        if tags[col] == "date":
            df_songs[col] = pd.to_datetime(df_songs[col], yearfirst=True)

    # /// PLAYLISTS \\\
    playlists_data = library.findall("array")[-1].findall("dict")
    dict_playlist = {}
    for p in playlists_data:
        p_name = p.find("string").text
        tmp_track_list = p.findall("array")
        track_list = None
        if tmp_track_list:
            try:
                tmp_track_list = tmp_track_list[-1].findall("dict")
                if tmp_track_list:
                    track_list = [int(i.find("integer").text) for i in tmp_track_list]
            except KeyError:
                pass
        dict_playlist[p_name] = track_list

    return df_songs, dict_playlist


def write_apple_music_library(
    in_file: str = APPLE_MUSIC_LIBRARY_FILE,
    out_playlist_file: str = RAW_PLAYLIST_FILE,
    out_song_file: str = SONG_FILE,
):
    """
    Parses Apply Music Library file and writes output to disk.

    Returns
    -------
        Writes output to file.
    """
    songs, playlists = parse_apple_music_library(in_file)
    songs.to_csv(out_song_file, index=False)
    json.dump(playlists, open(out_playlist_file, "w"))


def prepare_playlists(
    in_song_file: str = SONG_FILE,
    in_playlist_file: str = RAW_PLAYLIST_FILE,
    out_playlist_file: str = PREPARED_PLAYLIST_FILE,
):
    """
    Transforms the raw playlist file into a playlist file that contains
    a song's name, artist and album.
    This information is then used to create a query to Spotify's API when syncing playlists.

    Returns
    -------
    """
    apple_music_songs = pd.read_csv(
        in_song_file, usecols=[0, 1, 2, 3, 4, 5, 6]
    ).set_index("Track ID")
    apple_music_playlists = json.load(open(in_playlist_file, "rb"))

    # Check for invalid Track IDs
    mask_valid = (
        apple_music_songs.index.to_series().astype(str).apply(lambda x: x.isdigit())
    )
    mask_invalid = ~mask_valid
    apple_music_songs = apple_music_songs.loc[mask_valid]
    logging.info(f"Number of invalid track IDs: {mask_invalid.sum():,}")
    valid_songs = set(apple_music_songs.index.tolist())

    apple_music_songs.columns = apple_music_songs.columns.str.lower()

    # Convert Track IDs in playlist file to tuples of Name, Artist, Album
    # Since we can sync only based on that information
    parsed_playlists = {
        k: list(
            apple_music_songs.loc[
                # Intersection makes sure we only index valid songs
                # in case some songs are in playlists but not in the library
                # Perhaps for Apple Music managed playlists.
                list(set(v).intersection(valid_songs)), ["name", "artist", "album"]
            ].to_dict(orient="records")
        )
        for k, v in apple_music_playlists.items()
    }

    json.dump(parsed_playlists, open(out_playlist_file, "w"))
