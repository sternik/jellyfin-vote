from __future__ import annotations

import json


def test_results_empty_without_votes(populated_media):
    r = populated_media.get("/api/results")
    assert r.status_code == 200
    assert r.get_json() == []


def test_results_requires_all_users_agree(populated_media, authed_client_b):
    # populated_media = alice session; authed_client_b = bob session
    # Both must vote remove on the same item for it to appear in results.
    payload = {"keep": [], "remove": ["item1"]}
    assert (
        populated_media.post(
            "/api/votes/alice",
            data=json.dumps(payload),
            content_type="application/json",
        ).status_code
        == 200
    )

    # Only alice voted remove — no agreement yet.
    assert populated_media.get("/api/results").get_json() == []

    # Bob also votes remove on item1 = agreement.
    assert (
        authed_client_b.post(
            "/api/votes/bob",
            data=json.dumps({"keep": [], "remove": ["item1"]}),
            content_type="application/json",
        ).status_code
        == 200
    )

    r = populated_media.get("/api/results")
    ids = [item["id"] for item in r.get_json()]
    assert ids == ["item1"]


def test_results_partial_agreement_does_not_qualify(populated_media, authed_client_b):
    assert (
        populated_media.post(
            "/api/votes/alice",
            data=json.dumps({"keep": [], "remove": ["item2"]}),
            content_type="application/json",
        ).status_code
        == 200
    )
    # Bob keeps item2.
    assert (
        authed_client_b.post(
            "/api/votes/bob",
            data=json.dumps({"keep": ["item2"], "remove": []}),
            content_type="application/json",
        ).status_code
        == 200
    )
    assert populated_media.get("/api/results").get_json() == []


def test_results_filters_to_valid_media_ids(populated_media, authed_client_b):
    # Alice votes remove on item1 AND a stale id not in media.json.
    assert (
        populated_media.post(
            "/api/votes/alice",
            data=json.dumps({"keep": [], "remove": ["item1", "ghost-id"]}),
            content_type="application/json",
        ).status_code
        == 200
    )
    assert (
        authed_client_b.post(
            "/api/votes/bob",
            data=json.dumps({"keep": [], "remove": ["item1", "ghost-id"]}),
            content_type="application/json",
        ).status_code
        == 200
    )
    ids = [i["id"] for i in populated_media.get("/api/results").get_json()]
    # ghost-id not in media.json so it should NOT appear even on unanimous vote.
    assert ids == ["item1"]
