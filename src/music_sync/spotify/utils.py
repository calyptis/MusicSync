"""Utility functions for Spotify API access, string cleaning, retries, and query generation."""

import time
from requests.exceptions import ReadTimeout
import re

from loguru import logger
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from spotipy.exceptions import SpotifyException

from music_sync.classes import Song
from music_sync.config import config


def clean_string(x: str | None) -> str:
    """
    Strip space and transform string into lowercase letters.

    Parameters
    ----------
    x : str | None
        String to be cleaned. A missing value is treated as an empty string.

    Returns
    -------
    Cleaned string
    """
    if x is None:
        return ""
    return x.lower().strip()


def retry_on_timeout(api_call, n_retries: int = 5, backoff_factor: float = 0.8):
    """
    Retry an API call multiple times to handle transient timeouts or network errors.

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
            logger.warning(f"Timeout on attempt {attempt}/{n_retries}: {e}")
            time.sleep(backoff_factor * attempt)
        except Exception as e:
            logger.error(f"Non-timeout exception during API call: {e}")
            break
    logger.error("API call failed after maximum retries.")
    return None


def generate_alternate_queries(song: Song) -> list[Song]:
    """
    Generate alternative query attempts for better Spotify matching.

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
    attempts: list[Song] = []

    # Song fields are optional; a missing one is an empty string here.
    name = song.name or ""
    artist = song.artist or ""
    album = song.album or ""

    def add_attempts(s_name: str, a_name: str, alb_name: str) -> None:
        """Helper to add standard + no-album versions of a query."""
        attempts.append(
            Song(name=s_name.strip(), artist=a_name.strip(), album=alb_name.strip())
        )
        attempts.append(Song(name=s_name.strip(), artist=a_name.strip(), album=""))

    # Sometimes there is no match if song includes "feat." or "ft."
    if "feat." in name.lower() or "ft." in name.lower():
        cleaned_name = re.sub(
            r"\s*\(?\b(?:feat\.|ft\.)\b.*", "", name, flags=re.IGNORECASE
        ).strip()
        no_feat_name = name.replace("feat. ", " ").replace("ft. ", " ")
        song_name_clean_first_collab = re.split(r"(\s?\(?feat\.)|(\s?\(?ft\.)", name)[
            0
        ].strip()
        add_attempts(song_name_clean_first_collab, artist, album)
        add_attempts(no_feat_name, artist, album)
        add_attempts(cleaned_name, artist, album)

    # Sometimes there is no match if song includes "remastered"
    if "remastered" in name.lower():
        cleaned_name = re.sub(
            r"\s*\(?remastered[^\)]*\)?", "", name, flags=re.IGNORECASE
        ).strip()
        add_attempts(cleaned_name, artist, album)

    # Sometimes there is no match if artist is collaboration and includes "&", like Brian Eno & John Cale
    if "&" in artist:
        # Try only the first artist
        main_artist = artist.split("&")[0]
        add_attempts(name, main_artist, album)
        # Try replacing '&' with a comma
        artist_with_comma = artist.replace(" & ", ", ")
        add_attempts(name, artist_with_comma, album)

    return attempts


def get_spotipy_instance() -> spotipy.Spotify:
    """
    Initiate the spotipy instance to allow API calls.

    Credentials are read from the environment or a `.env` file as
    `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` and `SPOTIFY_REDIRECT_URI`.

    Returns
    -------
    spotipy.Spotify
        An authenticated client.

    Raises
    ------
    RuntimeError
        If no client ID or secret has been configured.
    """
    if not config.spotify.client_id or not config.spotify.client_secret:
        raise RuntimeError(
            "No Spotify credentials found. Create a .env file in the project root "
            "with SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET (see README)."
        )

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=config.spotify.client_id,
            client_secret=config.spotify.client_secret,
            redirect_uri=config.spotify.redirect_uri,
            scope=config.spotify.scopes,
        )
    )
