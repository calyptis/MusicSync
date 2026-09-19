"""Functions for matching Apple Music songs to Spotify tracks using similarity metrics."""

import re
import requests

import spotipy

from music_sync.classes import Song, SongMatch, Similarity
from music_sync.spotify.similarity import measure_similarity
from music_sync.spotify.utils import generate_alternate_queries, retry_on_timeout


def search_best_match(sp: spotipy.Spotify, song: Song) -> SongMatch:
    """
    Return the best Spotify song match for a given Apple Music song, if available.

    Parameters
    ----------
    sp
        Spotipy instance
    song: Song:
        Song instance to match.

    Returns
    -------
    best_match : SongMatch
        Information on best match, including string similarity with original query information
        All of this information will be written to the CSV log file after a playlist was successfully synced.
    """

    attempts = [song]

    # Sometimes there is no match if album name is included, e.g.
    # bloody valentine	Machine Gun Kelly	bloody valentine - Single
    attempts += [
        Song(name=song.name, artist=song.artist, album="", track_id=song.track_id)
    ]
    attempts += generate_alternate_queries(song)

    attempts_best_matches = []
    for attempt in attempts:
        query = attempt.as_search_query()
        query = re.sub(r"\s+", " ", query).strip()
        try:
            tracks = retry_on_timeout(lambda: sp.search(query, limit=15).get("tracks"))
        except (spotipy.exceptions.SpotifyException, requests.exceptions.ReadTimeout):
            tracks = None
        if tracks is not None and len(tracks.get("items")) > 0:
            items = tracks.get("items")
            attempts_best_matches += [select_best_match(items, attempt)]

    if attempts_best_matches:
        # Find best match across all the attempts
        best_match = max(
            attempts_best_matches, key=lambda m: m.similarity.total_similarity or 0.0
        )
        # Overwrite apple info => original (not modified song info)
        best_match.apple_info = song
        return best_match
    else:
        # No valid match
        return SongMatch(apple_info=song, spotify_info=Song(), similarity=Similarity())


def select_best_match(tracks: list, song: Song) -> SongMatch:
    """
    Identify the best matching track from a list of tracks based on string similarity.

    This function takes the search results (tracks) returned by the Spotify API
    and compares them with the provided song information. It calculates similarity
    metrics for each track and returns the best match.

    Parameters
    ----------
    tracks : list:
        A list of tracks returned from the Spotify search API, where each track
        is represented by a dictionary containing track details.
    song : Song
        A Song instance representing the query song to match with the tracks.

    Returns
    -------
    SongMatch
        A SongMatch object containing the original Apple Music song,
        the best-matching Spotify track, and the similarity metrics.
    """
    scored_tracks = score_tracks(tracks, song)
    if not scored_tracks:
        return SongMatch(apple_info=song, spotify_info=Song(), similarity=Similarity())

    best_match_item, match_similarity = max(
        scored_tracks, key=lambda pair: pair[1].total_similarity or 0.0
    )

    spotify_info = Song(
        name=best_match_item.get("name"),
        artist=" ".join(
            i.get("name", "") for i in best_match_item.get("artists") or []
        ),
        album=(best_match_item.get("album") or {}).get("name"),
        track_id=best_match_item.get("id"),
    )

    return SongMatch(
        apple_info=song,
        spotify_info=spotify_info,
        similarity=match_similarity,
    )


def score_tracks(tracks: list, song: Song) -> list[tuple[dict, Similarity]]:
    """
    Score every track returned by the API against the original query.

    Parameters
    ----------
    tracks: list :
        All results from the API search request
    song: Song:
        Apple Music song instance to match.

    Returns
    -------
    list[tuple[dict, Similarity]] :
        Each track paired with its similarity metrics. Tracks are paired with
        their own score so that callers cannot mix up indices.
    """
    scored_tracks = []
    for item in tracks:
        if item is None:
            continue
        match = Song(
            name=str(item.get("name", "")),
            artist=" ".join(
                str(i.get("name", "")) for i in item.get("artists") or []
            ).strip(),
            album=str((item.get("album") or {}).get("name", "")),
        )
        scored_tracks.append(
            (item, measure_similarity(song_to_match=song, match=match))
        )

    return scored_tracks
