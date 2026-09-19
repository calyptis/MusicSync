"""Utility functions for parsing Apple Music XML elements."""

from xml.etree.ElementTree import Element


def parse_song_entry(song: Element) -> dict[str, str | None]:
    """
    Parse an XML song tag into a dictionary.

    This function processes an XML representation of a song and extracts key-value pairs
    by iterating over the song's elements in steps of two. The first element in each pair
    is used as the key, and the second element is used as the corresponding value.

    A value may be `None` when the XML tag is empty; callers are expected to fill
    those in (see `prepare_playlists_for_syncing`). Pairs whose *key* tag is empty
    are skipped, since such a field cannot be addressed by name.

    Parameters
    ----------
    song : Element:
        The `<dict>` element for one song, whose children alternate between
        key tags and value tags.

    Returns
    -------
    dict[str, str | None]
        A dictionary where the keys and values are extracted from the XML song tag.
    """
    entry = {}
    for i in range(0, len(song) - 1, 2):
        key = song[i].text
        if key is None:
            continue
        entry[key] = song[i + 1].text
    return entry
