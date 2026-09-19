"""Tests for resolving Spotify credentials from settings."""

import pytest

from music_sync.config import config
from music_sync.spotify.utils import get_spotipy_instance


@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [(None, None), (None, "secret"), ("id", None), ("", "secret"), ("id", "")],
)
def test_missing_credentials_raise_a_readable_error(
    monkeypatch, client_id, client_secret
):
    monkeypatch.setattr(config.spotify, "client_id", client_id)
    monkeypatch.setattr(config.spotify, "client_secret", client_secret)

    with pytest.raises(RuntimeError, match="No Spotify credentials found"):
        get_spotipy_instance()


def test_configured_credentials_are_passed_to_the_auth_manager(monkeypatch):
    monkeypatch.setattr(config.spotify, "client_id", "my-id")
    monkeypatch.setattr(config.spotify, "client_secret", "my-secret")
    monkeypatch.setattr(config.spotify, "redirect_uri", "http://localhost:1234/cb/")

    instance = get_spotipy_instance()

    auth_manager = instance.auth_manager
    assert auth_manager.client_id == "my-id"
    assert auth_manager.client_secret == "my-secret"
    assert auth_manager.redirect_uri == "http://localhost:1234/cb/"
    assert auth_manager.scope == config.spotify.scopes
