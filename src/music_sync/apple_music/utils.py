from xml.etree.ElementTree import Element


def get_entry(song: Element) -> dict[str, str]:
    """
    Parse an XML song tag into a dictionary.

    This function processes an XML representation of a song and extracts key-value pairs
    by iterating over the song's elements in steps of two. The first element in each pair
    is used as the key, and the second element is used as the corresponding value.

    Parameters
    ----------
    song : list
        A list of XML elements representing a song, where alternating elements represent keys and values.

    Returns
    -------
    dict
        A dictionary where the keys and values are extracted from the XML song tag.
    """
    return {song[i].text: song[i + 1].text for i in range(0, len(song) - 1, 2)}
