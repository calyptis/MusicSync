def get_entry(song) -> dict:
    """
    Parses an XML song tag

    Parameters
    ----------
    song

    Returns
    -------
    """
    return {song[i].text: song[i + 1].text for i in range(0, len(song) - 1, 2)}
