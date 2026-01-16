"""CLI for processing Apple Music library and playlists."""
import click

from music_sync.apple_music.parse_library import (
    save_apple_music_library,
    prepare_playlists_for_syncing,
)
from music_sync.config import config


@click.command()
@click.option(
    "--xml-library-file",
    default=config.apple_music.library_file,
    type=str,
    show_default=True,
    help="Path to the Apple Music library XML file.",
)
@click.option(
    "--playlists-file",
    default=config.apple_music.raw_playlist_file,
    type=str,
    show_default=True,
    help="Path to save the raw playlist data in JSON format.",
)
@click.option(
    "--songs-file",
    default=config.apple_music.song_file,
    type=str,
    show_default=True,
    help="Path to save the song data in CSV format.",
)
@click.option(
    "--prepared-playlists-file",
    default=config.apple_music.prepared_playlist_file,
    type=str,
    show_default=True,
    help="Path to save the processed playlist data in JSON format.",
)
def main(
    xml_library_file: str,
    playlists_file: str,
    songs_file: str,
    prepared_playlists_file: str,
):
    """
    Main function for processing an Apple Music library and preparing playlists for syncing.

    This function performs two operations:
    1. Parse and save the Apple Music library into separate files for songs and playlists.
    2. Prepare playlists by filtering and transforming raw playlist data based on song metadata.

    Parameters
    ----------
    xml_library_file : str
        Path to the Apple Music library XML file. Defaults to `APPLE_MUSIC_LIBRARY_FILE`.
    playlists_file : str
        Path to save the raw playlist data in JSON format. Defaults to `RAW_PLAYLIST_FILE`.
    songs_file : str
        Path to save the song data in CSV format. Defaults to `SONG_FILE`.
    prepared_playlists_file : str
        Path to save the processed playlist data in JSON format. Defaults to `PREPARED_PLAYLIST_FILE`.
    """

    save_apple_music_library(xml_library_file, playlists_file, songs_file)
    prepare_playlists_for_syncing(songs_file, playlists_file, prepared_playlists_file)


if __name__ == "__main__":
    main()
