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


def register_media_routes(app, config: Config, client: JellyfinClient) -> None:
    @app.route("/api/media")
    @require_auth
    def api_media():
        if not os.path.exists(config.MEDIA_FILE):
            refresh_media_items()
        try:
            with open(config.MEDIA_FILE, encoding="utf-8") as f:
                items = json.load(f)
        except (json.JSONDecodeError, OSError):
            items = []
        return jsonify(items)

    @app.route("/api/media/refresh", methods=["POST"])
    @require_auth
    def api_media_refresh():
        refreshed = refresh_media_items()
        return jsonify(refreshed)

    def refresh_media_items():
        items = client.list_items()
        media = [client.normalize(item, config.JELLYFIN_URL) for item in items]
        with open(config.MEDIA_FILE, "w", encoding="utf-8") as f:
            json.dump(media, f, ensure_ascii=False, indent=2)
        return media

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
