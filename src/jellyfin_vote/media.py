"""Media endpoints: list, refresh, image proxy."""

from __future__ import annotations

import json
import logging
import os

from flask import jsonify

from .auth import require_auth
from .config import Config
from .jellyfin import JellyfinClient

log = logging.getLogger("jellyfin_vote")

CACHE_CONTROL_HEADER = "public, max-age=31536000, immutable"


def removed_ids_file(config: Config) -> str:
    return os.path.join(os.path.dirname(config.USERS_FILE), "removed.json")


def load_removed_ids(config: Config) -> set[str]:
    try:
        with open(removed_ids_file(config), encoding="utf-8") as f:
            data = json.load(f)
        return set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, OSError, TypeError):
        return set()


def _save_removed_ids(config: Config, ids: set[str]) -> None:
    with open(removed_ids_file(config), "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


def prune_stale_votes(config: Config, valid_ids: set[str]) -> None:
    """Drop votes referencing items no longer in the media library."""
    data_dir = os.path.dirname(config.USERS_FILE)
    if not os.path.isdir(data_dir):
        return
    for fname in os.listdir(data_dir):
        if not (fname.startswith("votes_") and fname.endswith(".json")):
            continue
        path = os.path.join(data_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                votes = json.load(f)
            keep = [i for i in votes.get("keep", []) if i in valid_ids]
            remove = [i for i in votes.get("remove", []) if i in valid_ids]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            continue
        if keep == votes.get("keep") and remove == votes.get("remove"):
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"keep": keep, "remove": remove}, f)
        log.info("Pruned stale votes from %s", fname)


def refresh_media_items(config: Config, client: JellyfinClient) -> list[dict]:
    items = client.list_items()

    # Forget tombstones for items Jellyfin no longer has.
    fresh_ids = {item.get("Id") for item in items}
    previously_removed = load_removed_ids(config)
    removed = previously_removed & fresh_ids
    if removed != previously_removed:
        _save_removed_ids(config, removed)

    media = [
        client.normalize(item, config.JELLYFIN_URL)
        for item in items
        if item.get("Id") not in removed
    ]
    with open(config.MEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(media, f, ensure_ascii=False, indent=2)
    prune_stale_votes(config, {m["id"] for m in media})
    return media


def remove_item_everywhere(config: Config, item_id: str) -> None:
    """Forget an item: tombstone, media.json, and all votes files."""
    _save_removed_ids(config, load_removed_ids(config) | {item_id})

    try:
        with open(config.MEDIA_FILE, encoding="utf-8") as f:
            media = json.load(f)
    except (json.JSONDecodeError, OSError):
        media = []
    media = [m for m in media if m.get("id") != item_id]
    with open(config.MEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(media, f, ensure_ascii=False, indent=2)

    prune_stale_votes(config, {m.get("id") for m in media})
    log.info("Removed %s from media.json and votes", item_id)


def register_media_routes(app, config: Config, client: JellyfinClient) -> None:
    @app.route("/api/media")
    @require_auth
    def api_media():
        if not os.path.exists(config.MEDIA_FILE):
            refresh_media_items(config, client)
        try:
            with open(config.MEDIA_FILE, encoding="utf-8") as f:
                items = json.load(f)
        except (json.JSONDecodeError, OSError):
            items = []
        return jsonify(items)

    @app.route("/api/media/refresh", methods=["POST"])
    @require_auth
    def api_media_refresh():
        refreshed = refresh_media_items(config, client)
        return jsonify(refreshed)

    @app.route("/api/img/<item_id>")
    @require_auth
    def api_img(item_id):
        if not os.path.exists(config.CACHE_DIR):
            os.makedirs(config.CACHE_DIR)
        cache_path = os.path.join(config.CACHE_DIR, f"{item_id}.jpg")
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return (
                    f.read(),
                    200,
                    {
                        "Content-Type": "image/jpeg",
                        "Cache-Control": CACHE_CONTROL_HEADER,
                    },
                )
        result = client.fetch_image(item_id)
        if result is None:
            return "", 404
        content, content_type = result
        with open(cache_path, "wb") as f:
            f.write(content)
        return (
            content,
            200,
            {
                "Content-Type": content_type,
                "Cache-Control": CACHE_CONTROL_HEADER,
            },
        )
