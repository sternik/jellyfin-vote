from __future__ import annotations

import json
import os

import pytest


def test_media_requires_auth(client):
    r = client.get("/api/media")
    assert r.status_code == 401


def test_media_refresh_requires_auth(client):
    r = client.post("/api/media/refresh")
    assert r.status_code == 401


def test_media_refresh_populates_file(populated_media):
    r = populated_media.get("/api/media")
    assert r.status_code == 200
    items = r.get_json()
    assert len(items) == 5

    ids = [item["id"] for item in items]
    assert "item1" in ids
    assert "s1" in ids


def test_media_normalizes_items(populated_media):
    items = populated_media.get("/api/media").get_json()
    by_id = {item["id"]: item for item in items}
    item1 = by_id["item1"]
    assert item1["type"] == "Movie"
    assert item1["year"] == 2020
    assert item1["imdb"] == "tt0000001"
    assert item1["link"].startswith("https://jellyfin.example.com/jellyfin/web")
    series = by_id["s1"]
    assert series["type"] == "Series"


def test_img_endpoint_returns_404_on_missing(populated_media):
    # FakeJellyfinClient.fetch_image returns None -> 404.
    r = populated_media.get("/api/img/nonexistent-id")
    assert r.status_code == 404


def test_refresh_prunes_stale_votes(app, authed_client):
    config = app.config["APP_CONFIG"]

    # Vote referencing an item that is not in the fixture library.
    r = authed_client.post(
        "/api/votes/alice",
        data=json.dumps({"keep": ["ghost-id"], "remove": ["item1", "ghost-id"]}),
        content_type="application/json",
    )
    assert r.status_code == 200

    assert authed_client.post("/api/media/refresh").status_code == 200

    votes_path = os.path.join(os.path.dirname(config.USERS_FILE), "votes_alice.json")
    with open(votes_path, encoding="utf-8") as f:
        votes = json.load(f)
    assert votes == {"keep": [], "remove": ["item1"]}


def test_refresh_hides_tombstoned_items(app, authed_client):
    config = app.config["APP_CONFIG"]
    data_dir = os.path.dirname(config.USERS_FILE)

    # item3 exists in Jellyfin; ghost never does.
    with open(os.path.join(data_dir, "removed.json"), "w", encoding="utf-8") as f:
        json.dump(["item3", "ghost"], f)

    assert authed_client.post("/api/media/refresh").status_code == 200

    ids = [m["id"] for m in authed_client.get("/api/media").get_json()]
    assert "item3" not in ids
    assert "item1" in ids

    # Tombstone for an item Jellyfin no longer has is forgotten.
    with open(os.path.join(data_dir, "removed.json"), encoding="utf-8") as f:
        assert json.load(f) == ["item3"]


def test_refresh_refuses_empty_library(app, populated_media, monkeypatch):
    """A 0-item answer from Jellyfin must never wipe media.json or votes."""
    config = app.config["APP_CONFIG"]
    data_dir = os.path.dirname(config.USERS_FILE)

    r = populated_media.post(
        "/api/votes/alice",
        data=json.dumps({"keep": ["item2"], "remove": ["item1"]}),
        content_type="application/json",
    )
    assert r.status_code == 200

    before_media = open(config.MEDIA_FILE, encoding="utf-8").read()
    before_votes = open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read()

    from jellyfin_vote.jellyfin import JellyfinClient

    monkeypatch.setattr(JellyfinClient, "list_items", lambda self: [])
    r = populated_media.post("/api/media/refresh")
    assert r.status_code == 502
    assert "0 items" in r.get_json()["error"]

    assert open(config.MEDIA_FILE, encoding="utf-8").read() == before_media
    assert open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read() == (
        before_votes
    )


def test_refresh_failure_leaves_data_untouched(app, populated_media, monkeypatch):
    config = app.config["APP_CONFIG"]
    data_dir = os.path.dirname(config.USERS_FILE)

    populated_media.post(
        "/api/votes/alice",
        data=json.dumps({"keep": [], "remove": ["item1"]}),
        content_type="application/json",
    )
    before_media = open(config.MEDIA_FILE, encoding="utf-8").read()
    before_votes = open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read()

    from jellyfin_vote.jellyfin import JellyfinClient

    def _boom(self):
        raise RuntimeError("Jellyfin list_items returned 401")

    monkeypatch.setattr(JellyfinClient, "list_items", _boom)
    r = populated_media.post("/api/media/refresh")
    assert r.status_code == 502

    assert open(config.MEDIA_FILE, encoding="utf-8").read() == before_media
    assert open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read() == (
        before_votes
    )


def test_remove_item_aborts_on_unreadable_media(app, populated_media):
    """Corrupt media.json must not turn into an all-votes wipe."""
    from jellyfin_vote.media import remove_item_everywhere

    config = app.config["APP_CONFIG"]
    data_dir = os.path.dirname(config.USERS_FILE)

    populated_media.post(
        "/api/votes/alice",
        data=json.dumps({"keep": [], "remove": ["item1"]}),
        content_type="application/json",
    )
    before_votes = open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read()
    with open(config.MEDIA_FILE, "w", encoding="utf-8") as f:
        f.write("{ not json")

    with pytest.raises(RuntimeError):
        remove_item_everywhere(config, "item1")

    assert open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read() == (
        before_votes
    )
    assert not os.path.exists(os.path.join(data_dir, "removed.json"))
    assert open(config.MEDIA_FILE, encoding="utf-8").read() == "{ not json"


def test_prune_refuses_empty_valid_set(app, populated_media):
    from jellyfin_vote.media import prune_stale_votes

    config = app.config["APP_CONFIG"]
    data_dir = os.path.dirname(config.USERS_FILE)

    populated_media.post(
        "/api/votes/alice",
        data=json.dumps({"keep": ["item2"], "remove": ["item1"]}),
        content_type="application/json",
    )
    before = open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read()

    prune_stale_votes(config, set())

    assert open(os.path.join(data_dir, "votes_alice.json"), encoding="utf-8").read() == before


def test_static_assets_served(client):
    for path in ("/css/styles.css", "/js/auth.js"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.data


def test_html_pages_served(client):
    for path in ("/", "/login", "/myvotes", "/results"):
        r = client.get(path)
        assert r.status_code == 200
        assert b"<html" in r.data.lower()
