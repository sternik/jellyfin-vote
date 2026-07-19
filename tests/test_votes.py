from __future__ import annotations

import json


def test_get_own_votes_empty(authed_client):
    r = authed_client.get("/api/votes/alice")
    assert r.status_code == 200
    assert r.get_json() == {"keep": [], "remove": []}


def test_get_other_user_votes_forbidden(authed_client):
    r = authed_client.get("/api/votes/bob")
    assert r.status_code == 403


def test_save_to_other_user_forbidden(authed_client):
    r = authed_client.post(
        "/api/votes/bob",
        data=json.dumps({"keep": [], "remove": []}),
        content_type="application/json",
    )
    assert r.status_code == 403


def test_save_votes_invalid_payload_missing_keys(authed_client):
    r = authed_client.post(
        "/api/votes/alice",
        data=json.dumps({"keep": []}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_save_votes_invalid_payload_wrong_type(authed_client):
    r = authed_client.post(
        "/api/votes/alice",
        data=json.dumps({"keep": "x", "remove": []}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_save_votes_valid(authed_client):
    payload = {"keep": ["item1"], "remove": ["item2"]}
    r = authed_client.post(
        "/api/votes/alice",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 200

    r2 = authed_client.get("/api/votes/alice")
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["keep"] == ["item1"]
    assert data["remove"] == ["item2"]


def test_save_votes_filters_non_string_ids(authed_client):
    payload = {"keep": [123, "valid"], "remove": [None, "x"]}
    r = authed_client.post(
        "/api/votes/alice",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = authed_client.get("/api/votes/alice").get_json()
    assert data["keep"] == ["123", "valid"]
    assert data["remove"] == ["x"]
