import json
import time
import spotipy.exceptions

from src.config import CREDENTIALS_PATH


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
        yield original_list[i:i + n]


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
            return_obj = api_call
            if return_obj:
                return return_obj
            else:
                pass
        except TimeoutError:
            time.sleep(0.8 * count)
    return None
