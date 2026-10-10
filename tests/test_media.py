from __future__ import annotations

import json
import os


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
