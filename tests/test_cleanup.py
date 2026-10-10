from __future__ import annotations

import json
import os

import pytest


class FakeArrClient:
    """In-memory *arr client recording delete calls."""

    movies: dict[str, int] = {}
    series: dict[str, int] = {}
    deleted: list[tuple[str, int]] = []

    def __init__(self, base_url, api_key):
        self.base_url = base_url

    def list_movies(self):
        return dict(type(self).movies)

    def list_series(self):
        return dict(type(self).series)

    def delete_movie(self, movie_id):
        type(self).deleted.append(("movie", movie_id))

    def delete_series(self, series_id):
        type(self).deleted.append(("series", series_id))


@pytest.fixture()
def arr_env(arr_overrides):
    """Enable both *arr integrations."""
    arr_overrides.update(
        {
            "RADARR_URL": "https://radarr.test",
            "RADARR_API_KEY": "r-key",
            "SONARR_URL": "https://sonarr.test",
            "SONARR_API_KEY": "s-key",
        }
    )


@pytest.fixture()
def sonarr_only_env(arr_overrides):
    arr_overrides.update({"SONARR_URL": "https://sonarr.test", "SONARR_API_KEY": "s-key"})


@pytest.fixture()
def fake_arr(monkeypatch):
    FakeArrClient.movies = {"tt0000001": 11}
    FakeArrClient.series = {"tt0000002": 22}
    FakeArrClient.deleted = []
    monkeypatch.setattr("jellyfin_vote.cleanup.ArrClient", FakeArrClient)
    return FakeArrClient


def _agree_remove(client, other_client, item_id):
    for c, user in ((client, "alice"), (other_client, "bob")):
        r = c.post(
            f"/api/votes/{user}",
            data=json.dumps({"keep": [], "remove": [item_id]}),
            content_type="application/json",
        )
        assert r.status_code == 200


def test_status_disabled_without_config(authed_client):
    r = authed_client.get("/api/cleanup/status")
    assert r.status_code == 200
    assert r.get_json() == {"radarr": False, "sonarr": False}


def test_status_enabled(arr_env, authed_client):
    r = authed_client.get("/api/cleanup/status")
    assert r.get_json() == {"radarr": True, "sonarr": True}


def test_cleanup_requires_auth(client):
    assert client.post("/api/cleanup", json={"item_id": "item1"}).status_code == 401


def test_cleanup_requires_agreed_item(arr_env, fake_arr, populated_media, authed_client_b):
    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})
    assert r.status_code == 409
    assert r.get_json()["status"] == "not_agreed"
    assert fake_arr.deleted == []


def test_cleanup_no_imdb(arr_env, fake_arr, populated_media, authed_client_b):
    _agree_remove(populated_media, authed_client_b, "item2")
    r = populated_media.post("/api/cleanup", json={"item_id": "item2"})
    assert r.status_code == 422
    assert r.get_json()["status"] == "no_imdb"
    assert fake_arr.deleted == []


def test_cleanup_not_found_in_arr(arr_env, fake_arr, populated_media, authed_client_b):
    fake_arr.movies = {}
    _agree_remove(populated_media, authed_client_b, "item1")
    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})
    assert r.status_code == 404
    body = r.get_json()
    assert body["status"] == "not_found"
    assert body["imdb"] == "tt0000001"
    assert body["service"] == "Radarr"
    assert fake_arr.deleted == []


def test_cleanup_unavailable_when_not_configured(
    sonarr_only_env, fake_arr, populated_media, authed_client_b
):
    _agree_remove(populated_media, authed_client_b, "item1")
    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})
    assert r.status_code == 501
    assert r.get_json()["status"] == "unavailable"


def test_cleanup_deletes_movie(arr_env, fake_arr, populated_media, authed_client_b):
    _agree_remove(populated_media, authed_client_b, "item1")
    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})
    assert r.status_code == 200
    assert r.get_json() == {"status": "deleted", "name": "Test Movie", "local": True}
    assert fake_arr.deleted == [("movie", 11)]


def test_cleanup_deletes_series(arr_env, fake_arr, populated_media, authed_client_b):
    _agree_remove(populated_media, authed_client_b, "s1")
    r = populated_media.post("/api/cleanup", json={"item_id": "s1"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "deleted"
    assert fake_arr.deleted == [("series", 22)]


def test_cleanup_missing_item_id(arr_env, fake_arr, populated_media):
    r = populated_media.post("/api/cleanup", json={})
    assert r.status_code == 400


def test_cleanup_forgets_item_everywhere(arr_env, fake_arr, app, populated_media, authed_client_b):
    _agree_remove(populated_media, authed_client_b, "item1")
    assert "item1" in [m["id"] for m in populated_media.get("/api/media").get_json()]

    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})
    assert r.status_code == 200

    # Gone from media.json, votes, results — and tombstoned for future refreshes.
    ids = [m["id"] for m in populated_media.get("/api/media").get_json()]
    assert "item1" not in ids
    assert populated_media.get("/api/results").get_json() == []

    config = app.config["APP_CONFIG"]
    votes_path = os.path.join(os.path.dirname(config.USERS_FILE), "votes_alice.json")
    with open(votes_path, encoding="utf-8") as f:
        votes = json.load(f)
    assert votes == {"keep": [], "remove": []}

    removed_path = os.path.join(os.path.dirname(config.USERS_FILE), "removed.json")
    with open(removed_path, encoding="utf-8") as f:
        assert json.load(f) == ["item1"]


def test_cleanup_still_reports_deleted_when_local_forget_fails(
    arr_env, fake_arr, populated_media, authed_client_b, monkeypatch
):
    _agree_remove(populated_media, authed_client_b, "item1")

    def _boom(config, item_id):
        raise RuntimeError("media.json unreadable — aborting local forget")

    monkeypatch.setattr("jellyfin_vote.cleanup.remove_item_everywhere", _boom)
    r = populated_media.post("/api/cleanup", json={"item_id": "item1"})

    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "deleted"
    assert body["local"] is False
    assert "unreadable" in body["error"]
    assert fake_arr.deleted == [("movie", 11)]
