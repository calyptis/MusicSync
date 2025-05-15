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
    Parse Apple Music library, which is exported using File -> Library -> Export Library...

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


def save_apple_music_library(
    xml_library_file: str = APPLE_MUSIC_LIBRARY_FILE,
    playlists_file: str = RAW_PLAYLIST_FILE,
    songs_file: str = SONG_FILE,
):
    """
    Write Apple Music Library Data to Specified Files

    This function parses an Apple Music library XML file and outputs playlists and songs to
    separate files. Songs are stored in CSV format, while playlists are serialized into JSON format.

    Parameters
    ----------
    xml_library_file : str
        The file path of the Apple Music library in XML format. Defaults to the
        constant `APPLE_MUSIC_LIBRARY_FILE`.
    playlists_file : str
        The target file path for saving playlists in JSON format. Defaults to
        the constant `RAW_PLAYLIST_FILE`.
    songs_file : str
        The target file path for saving songs in CSV format. Defaults to the
        constant `SONG_FILE`.

    """
    songs, playlists = parse_apple_music_library(xml_library_file)
    logging.info(f"Number of songs: {len(songs):,}")
    logging.info(f"Number of playlists: {len(playlists):,}")
    songs.to_csv(songs_file, index=False)
    with open(playlists_file, "w") as f:
        # noinspection PyTypeChecker
        json.dump(playlists, f)


def prepare_playlists_for_syncing(
    songs_file: str = SONG_FILE,
    raw_playlists_file: str = RAW_PLAYLIST_FILE,
    parsed_playlists_file: str = PREPARED_PLAYLIST_FILE,
):
    """
    Prepare playlists by parsing raw playlist data and mapping it to metadata from available songs.

    The function reads in a file with song metadata and a file containing raw playlist data.
    It filters out invalid songs based on their Track IDs, matches playlist data with valid
    songs, and converts playlist entries into tuples of song name, artist, and album.
    The processed playlists are then saved to a new file.

    Parameters
    ----------
    songs_file : str
        Path to the CSV file containing information about available songs. The file
        must have the following columns: Track ID, Name, Artist, Album, and others.

    raw_playlists_file : str
        Path to the JSON file containing raw playlist data. The file contains a
        mapping from playlist names to lists of song Track IDs.

    parsed_playlists_file : str
        Path where the processed playlists should be saved as a JSON file. The file
        will contain a mapping from playlist names to lists of dictionaries. Each
        dictionary represents a song with its name, artist, and album fields.

    """
    apple_music_songs = pd.read_csv(songs_file, usecols=[0, 1, 2, 3, 4, 5, 6])
    apple_music_songs.columns = apple_music_songs.columns.str.lower().str.replace(
        " ", "_"
    )
    apple_music_songs.set_index("track_id", inplace=True)
    apple_music_playlists = json.load(open(raw_playlists_file, "rb"))

    # Check for invalid Track IDs
    mask_valid = (
        apple_music_songs.index.to_series().astype(str).apply(lambda x: x.isdigit())
    )
    mask_invalid = ~mask_valid
    apple_music_songs = apple_music_songs.loc[mask_valid]
    logging.info(f"Number of invalid track IDs: {mask_invalid.sum():,}")
    valid_songs = set(apple_music_songs.index.tolist())

    # Convert Track IDs in playlist file to tuples of Name, Artist, Album
    # Since we can sync only based on that information
    parsed_playlists = {
        k: list(
            apple_music_songs.loc[
                # Intersection makes sure we only index valid songs
                # in case some songs are in playlists but not in the library
                # Perhaps for Apple Music managed playlists.
                list(set(v).intersection(valid_songs)), ["name", "artist", "album"]
            ]
            # Keep track ID
            .reset_index()
            # Save as dictionaries to easily create Song instances
            .to_dict(orient="records")
        )
        for k, v in apple_music_playlists.items()
    }

    json.dump(parsed_playlists, open(parsed_playlists_file, "w"))
