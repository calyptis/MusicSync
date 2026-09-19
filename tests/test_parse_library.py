"""Tests for parsing the Apple Music library XML export."""

import pytest

from music_sync.apple_music.parse_library import parse_apple_music_library

LIBRARY_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Major Version</key><integer>1</integer>
    <key>Tracks</key>
    <dict>
        <key>101</key>
        <dict>
            <key>Track ID</key><integer>101</integer>
            <key>Name</key><string>Caruso</string>
            <key>Artist</key><string>Fiorella Mannoia</string>
            <key>Album</key><string>A te</string>
        </dict>
        <key>102</key>
        <dict>
            <key>Track ID</key><integer>102</integer>
            <key>Name</key><string>Roxanne</string>
            <key>Artist</key><string>The Police</string>
            <key>Album</key><string>Reggatta de Blanc</string>
        </dict>
    </dict>
    <key>Playlists</key>
    <array>
{playlists}
    </array>
</dict>
</plist>
"""

PLAYLIST = """        <dict>
            <key>Name</key><string>{name}</string>
            <key>Playlist Items</key>
            <array>
                <dict><key>Track ID</key><integer>101</integer></dict>
                <dict><key>Track ID</key><integer>102</integer></dict>
            </array>
        </dict>"""


def write_library(tmp_path, playlists: str):
    library_file = tmp_path / "Library.xml"
    library_file.write_text(LIBRARY_TEMPLATE.format(playlists=playlists))
    return library_file


def test_parses_songs_and_playlists(tmp_path):
    library_file = write_library(tmp_path, PLAYLIST.format(name="Esperanto"))

    df_songs, playlists = parse_apple_music_library(library_file)

    assert df_songs["Name"].tolist() == ["Caruso", "Roxanne"]
    assert playlists == {"Esperanto": [101, 102]}


def test_integer_columns_are_converted_to_numbers(tmp_path):
    library_file = write_library(tmp_path, PLAYLIST.format(name="Esperanto"))

    df_songs, _ = parse_apple_music_library(library_file)

    assert df_songs["Track ID"].tolist() == [101, 102]


def test_playlist_without_tracks_maps_to_none(tmp_path):
    empty_playlist = """        <dict>
            <key>Name</key><string>Empty</string>
        </dict>"""
    library_file = write_library(tmp_path, empty_playlist)

    _, playlists = parse_apple_music_library(library_file)

    assert playlists == {"Empty": None}


def test_playlist_without_a_name_is_skipped(tmp_path):
    """A nameless playlist cannot be synced, so it is dropped rather than crashing."""
    nameless = """        <dict>
            <key>Playlist Items</key>
            <array>
                <dict><key>Track ID</key><integer>101</integer></dict>
            </array>
        </dict>"""
    library_file = write_library(
        tmp_path, nameless + "\n" + PLAYLIST.format(name="Kept")
    )

    _, playlists = parse_apple_music_library(library_file)

    assert playlists == {"Kept": [101, 102]}


def test_unexpected_xml_shape_raises_a_readable_error(tmp_path):
    library_file = tmp_path / "Library.xml"
    library_file.write_text('<?xml version="1.0"?>\n<plist version="1.0"></plist>\n')

    with pytest.raises(ValueError, match="could not find the library metadata"):
        parse_apple_music_library(library_file)


def test_missing_playlist_array_raises_a_readable_error(tmp_path):
    library_file = tmp_path / "Library.xml"
    library_file.write_text(
        '<?xml version="1.0"?>\n<plist version="1.0"><dict>'
        "<key>Tracks</key><dict></dict>"
        "</dict></plist>\n"
    )

    with pytest.raises(ValueError, match="could not find the playlist array"):
        parse_apple_music_library(library_file)
