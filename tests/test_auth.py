from __future__ import annotations

import json


def test_login_missing_credentials(client):
    r = client.post("/api/login", data="{}", content_type="application/json")
    assert r.status_code == 401


def test_login_wrong_password(client):
    r = client.post(
        "/api/login",
        data=json.dumps({"username": "alice", "password": "wrong"}),
        content_type="application/json",
    )
    assert r.status_code == 401


def test_login_success(client):
    r = client.post(
        "/api/login",
        data=json.dumps({"username": "alice", "password": "pw1"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["user"] == "alice"


def test_me_requires_auth(client):
    r = client.get("/api/me")
    assert r.status_code == 401


def test_me_after_login(authed_client):
    r = authed_client.get("/api/me")
    assert r.status_code == 200
    assert r.get_json()["user"] == "alice"


def test_logout(authed_client):
    r = authed_client.get("/api/logout")
    assert r.status_code == 200
    # After logout, /api/me should be unauthorized.
    r2 = authed_client.get("/api/me")
    assert r2.status_code == 401


def test_protected_endpoint_requires_auth(client):
    r = client.get("/api/votes/alice")
    assert r.status_code == 401
