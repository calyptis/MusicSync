import logging
import json
import time
from typing import Generator
from requests.exceptions import ReadTimeout
import re
import os

import pandas as pd
import numpy as np
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from spotipy.exceptions import SpotifyException

from music_sync.classes import Song
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


def get_chunks(original_list: list, n: int) -> Generator[list, None, None]:
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


def timeout_wrapper(api_call, n_retries: int = 5, backoff_factor: float = 0.8):
    """
    Retries an API call multiple times to handle transient timeouts or network errors.

    Parameters
    ----------
    api_call : Callable
        A lambda or function reference that makes an API call.
    n_retries : int
        Maximum number of retries before giving up.
    backoff_factor : float
        Time (in seconds) to wait between retries, multiplied by attempt count.

    Returns
    -------
    Any
        Result of the API call if successful, else None.
    """
    for attempt in range(1, n_retries + 1):
        try:
            return api_call()
        except (TimeoutError, ReadTimeout, SpotifyException) as e:
            logging.warning(f"Timeout on attempt {attempt}/{n_retries}: {e}")
            time.sleep(backoff_factor * attempt)
        except Exception as e:
            logging.error(f"Non-timeout exception during API call: {e}")
            break
    logging.error("API call failed after maximum retries.")
    return None


def generate_alternate_queries(song: Song) -> list[Song]:
    """
    Generates alternative query attempts for better Spotify matching.

    Handles cases like:
    - "feat." or "ft." in song titles
    - "remastered" in song titles
    - Collaboration names with "&"

    Parameters
    ----------
    song: Song :
        Song instance for which alternative variations should be generated.

    Returns
    -------
    attempts: list[Song] :
        Alternative song variations.
    """
    attempts = []

    def add_attempts(s_name, a_name, alb_name):
        """Helper to add standard + no-album versions of a query."""
        attempts.append(
            Song(name=s_name.strip(), artist=a_name.strip(), album=alb_name.strip())
        )
        attempts.append(Song(name=s_name.strip(), artist=a_name.strip(), album=""))

    # Sometimes there is no match if song includes "feat." or "ft."
    if "feat." in song.name.lower() or "ft." in song.name.lower():
        cleaned_name = re.sub(
            r"\s*\(?\b(?:feat\.|ft\.)\b.*", "", song.name, flags=re.IGNORECASE
        ).strip()
        no_feat_name = song.name.replace("feat. ", " ").replace("ft. ", " ")
        song_name_clean_first_collab = re.split(
            r"(\s?\(?feat\.)|(\s?\(?ft\.)", song.name
        )[0].strip()
        add_attempts(song_name_clean_first_collab, song.artist, song.album)
        add_attempts(no_feat_name, song.artist, song.album)
        add_attempts(cleaned_name, song.artist, song.album)

    # Sometimes there is no match if song includes "remastered"
    if "remastered" in song.name.lower():
        cleaned_name = re.sub(
            r"\s*\(?remastered[^\)]*\)?", "", song.name, flags=re.IGNORECASE
        ).strip()
        add_attempts(cleaned_name, song.artist, song.album)

    # Sometimes there is no match if artist is collaboration and includes "&", like Brian Eno & John Cale
    if "&" in song.artist:
        # Try only the first artist
        main_artist = song.artist.split("&")[0]
        add_attempts(song.name, main_artist, song.album)
        # Try replacing '&' with a comma
        artist_with_comma = song.artist.replace(" & ", ", ")
        add_attempts(song.name, artist_with_comma, song.album)

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
    filepath: str, playlist_songs: list[Song]
) -> tuple[list[Song], bool]:
    """
    Compares the songs in a playlist with a synced log file to identify songs that need syncing.

    Parameters
    ----------
    filepath : str
        Path to the log file containing songs already synced.
    playlist_songs : list[Song]
        List of Song objects representing the songs currently in the playlist.

    Returns
    -------
    tuple[list[Song], bool]
        A tuple containing:
        - List of Song objects that need to be synced.
        - Boolean indicating whether the playlist has already been synced prior.
    """
    flag_already_synced = os.path.exists(filepath)
    songs_to_sync = playlist_songs

    if flag_already_synced:
        logging.info("Playlist was already synced once before")
        df_logs = pd.read_csv(filepath)
        tracks_already_synced = df_logs[
            ["Apple Song Name", "Apple Artist", "Apple Album"]
        ]
        # Rename columns to easily create Song instance
        tracks_already_synced.columns = ["name", "artist", "album"]
        tracks_already_synced = tracks_already_synced.replace(
            [np.nan, pd.NA], None
        ).to_dict(orient="records")
        # Create song instances
        tracks_already_synced = [Song(**i) for i in tracks_already_synced]
        # Identify songs not yet synced
        songs_to_sync = list(set(songs_to_sync) - set(tracks_already_synced))

    return songs_to_sync, flag_already_synced
