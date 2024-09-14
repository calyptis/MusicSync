import logging
import json
import time
from requests.exceptions import ReadTimeout
import re
import os

import pandas as pd
from spotipy.oauth2 import SpotifyOAuth
import spotipy

from music_sync.config import CREDENTIALS_PATH, SCOPES


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def clean_string(x: str) -> str:
    """
    Strips space and transforms string into lowercase letters

    Parameters
    ----------
    x : str
        String to be cleaned

    Returns
    -------
    Cleaned string
    """
    return x.lower().strip()


def get_chunks(original_list: list, n: int) -> list:
    """
    Yield successive n-sized chunks from list.

    Parameters
    ----------
    original_list : list
        Original list to be split into chunks
    n : int
        Number of items in chunk

    Returns
    -------
    """
    for i in range(0, len(original_list), n):
        yield original_list[i : i + n]


def get_credentials(credentials_path: str = CREDENTIALS_PATH) -> dict:
    """
    Reads in credentials stored in a file

    Parameters
    ----------
    credentials_path
        Path to the JSON containing Spotify API credentials & configurations

    Returns
    -------

    """
    return json.load(open(credentials_path, "rb"))


def timeout_wrapper(api_call, n_retries: int = 5):
    """
    Retries an API call n times to deal with timeout issues.
    After each retry, a certain amount of time is waited.

    Parameters
    ----------
    api_call
        Function to be called
    n_retries
        How often the API call should be retried

    Returns
    -------
    Return object of API call
    """
    count = 0
    while n_retries > count:
        count += 1
        try:
            return api_call
        except TimeoutError | ReadTimeout:
            time.sleep(0.8 * count)
    return None


def generate_additional_attempts(song_name: str, artist_name: str, album_name: str):
    attempts = []
    # Sometimes there is no match if song includes "feat." or "ft."
    if "feat." in song_name or "ft." in song_name:
        # Replace feat in song name
        song_name_clean = song_name.replace("feat. ", " ").replace("ft. ", " ")
        attempts += [(song_name_clean, artist_name, album_name)]
        attempts += [(song_name_clean, artist_name, "")]
        # Get first part of song name, before feat
        song_name_clean_first_collab = re.split(
            r"(\s?\(?feat\.)|(\s?\(?ft\.)", song_name
        )[0].strip()
        attempts += [(song_name_clean_first_collab, artist_name, album_name)]
        attempts += [(song_name_clean_first_collab, artist_name, "")]
    # Sometimes there is no match if song includes "remastered"
    if "remastered" in song_name:
        song_name_clean = re.sub(r"(\s?remastered\s?)", " ", song_name).strip()
        attempts += [(song_name_clean, artist_name, album_name)]
        attempts += [(song_name_clean, artist_name, "")]
    # Sometimes there is no match if artist is collaboration and includes "&", like Brian Eno & John Cale
    if "&" in artist_name:
        artist_name_clean = artist_name.split("&")[0]
        attempts += [(song_name, artist_name_clean, album_name)]
        attempts += [(song_name, artist_name_clean, "")]
        # Sometimes it helps to replace & with a comma
        attempts += [(song_name, artist_name.replace(" & ", ", "), album_name)]
        attempts += [(song_name, artist_name.replace(" & ", ", "), "")]

    return attempts


def get_spotipy_instance() -> spotipy.Spotify:
    """
    Initiates the spotipy instance to allow API calls.

    Returns
    -------
    spotipy_instance
    """
    spotify_credentials = get_credentials()
    spotipy_instance = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=spotify_credentials["client_id"],
            client_secret=spotify_credentials["client_secret"],
            redirect_uri=spotify_credentials["redirect_uri"],
            scope=SCOPES,
        )
    )
    return spotipy_instance


def get_songs_to_sync(
    filepath: str, playlist_songs: list[tuple]
) -> tuple[list[tuple], bool]:
    flag_already_synced = os.path.exists(filepath)
    songs_to_sync = playlist_songs

    if flag_already_synced:
        logging.info("Playlist was already synced once before")
        df_logs = pd.read_csv(filepath)
        tracks_already_synced = df_logs.apply(
            lambda row: tuple(row[["Apple Song Name", "Apple Artist", "Apple Album"]]),
            axis=1,
        ).tolist()
        songs_to_sync = list(
            set([tuple(i) for i in playlist_songs]) - set(tracks_already_synced)
        )

    return songs_to_sync, flag_already_synced
