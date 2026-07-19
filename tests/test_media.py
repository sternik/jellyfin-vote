from __future__ import annotations


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
    assert item1["imdb"] == "https://www.imdb.com/title/tt0000001"
    assert item1["link"].startswith("https://jellyfin.example.com/jellyfin/web")
    series = by_id["s1"]
    assert series["type"] == "Series"


def test_img_endpoint_returns_404_on_missing(populated_media):
    # FakeJellyfinClient.fetch_image returns None -> 404.
    r = populated_media.get("/api/img/nonexistent-id")
    assert r.status_code == 404


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
