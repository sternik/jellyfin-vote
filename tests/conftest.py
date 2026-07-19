"""Tests shared fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jellyfin_vote import create_app

FIXTURES = Path(__file__).parent / "fixtures"


class FakeJellyfinClient:
    """In-memory Jellyfin client pulling from fixture JSON."""

    def __init__(self, items_path: Path | None = None) -> None:
        if items_path is None:
            items_path = FIXTURES / "jellyfin_items.json"
        with open(items_path, encoding="utf-8") as f:
            self._items = json.load(f)["Items"].copy()

    def list_items(self):
        return [dict(item) for item in self._items]

    def fetch_image(self, item_id):
        return None

    @staticmethod
    def normalize(item, base_url):
        from jellyfin_vote.jellyfin import JellyfinClient

        return JellyfinClient.normalize(item, base_url)


@pytest.fixture()
def app(tmp_path, monkeypatch):  # noqa: C901
    """Flask app with isolated data dir and mocked Jellyfin API via requests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "cache").mkdir()

    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JELLYFIN_URL", "https://jellyfin.example.com/jellyfin")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("USER_ID", "test-user-id")
    monkeypatch.setenv("MEDIA_FILE", str(data_dir / "media.json"))
    monkeypatch.setenv("USERS_FILE", str(data_dir / "users.json"))
    monkeypatch.setenv("CACHE_DIR", str(data_dir / "cache"))

    with open(data_dir / "users.json", "w", encoding="utf-8") as f:
        json.dump({"alice": "pw1", "bob": "pw2"}, f)

    # Mock requests.get used by JellyfinClient.
    items_path = FIXTURES / "jellyfin_items.json"
    with open(items_path, encoding="utf-8") as f:
        items_payload = json.load(f)

    class _Response:
        def __init__(self, status_code, payload, headers=None):
            self.status_code = status_code
            self._payload = payload
            self.headers = headers or {}
            self.ok = 200 <= status_code < 300

        def json(self):
            return self._payload

        @property
        def content(self):
            return b"fake-image-bytes"

        @property
        def text(self):
            return ""

    def fake_get(url, params=None, timeout=None, stream=None):
        if "/Items/" in url and "/Images/Primary" in url:
            return _Response(404, None)
        return _Response(200, items_payload)

    monkeypatch.setattr("jellyfin_vote.jellyfin.requests.get", fake_get)
    app = create_app()
    app.testing = True
    yield app


def _login(app, username, password):
    c = app.test_client()
    r = c.post(
        "/api/login",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert r.status_code == 200, r.get_json()
    return c


@pytest.fixture()
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture()
def authed_client(app):
    """Independent session as alice (own test_client so cookies are not shared)."""
    return _login(app, "alice", "pw1")


@pytest.fixture()
def authed_client_b(app):
    """Independent session as bob (own test_client)."""
    return _login(app, "bob", "pw2")


@pytest.fixture()
def populated_media(app, authed_client):
    """Populate media.json via separate refresh session; return alice session."""
    refresher = _login(app, "alice", "pw1")
    r = refresher.post("/api/media/refresh")
    assert r.status_code == 200
    return authed_client
