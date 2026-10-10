"""Cleanup endpoints: delete agreed items from Sonarr / Radarr."""

from __future__ import annotations

import json
import logging
import os

from flask import jsonify, request

from .arr import ArrClient
from .auth import require_auth
from .config import Config
from .jellyfin import JellyfinClient
from .media import remove_item_everywhere
from .results import get_agreed_removals

log = logging.getLogger("jellyfin_vote")


def _load_media_item(config: Config, item_id: str) -> dict | None:
    if not os.path.exists(config.MEDIA_FILE):
        return None
    try:
        with open(config.MEDIA_FILE, encoding="utf-8") as f:
            for item in json.load(f):
                if item.get("id") == item_id:
                    return item
    except (json.JSONDecodeError, OSError):
        pass
    return None


def register_cleanup_routes(app, config: Config, client: JellyfinClient) -> None:
    @app.route("/api/cleanup/status")
    @require_auth
    def cleanup_status():
        return jsonify({"radarr": config.radarr_enabled, "sonarr": config.sonarr_enabled})

    @app.route("/api/cleanup", methods=["POST"])
    @require_auth
    def cleanup():
        data = request.json or {}
        item_id = data.get("item_id", "")
        if not item_id:
            return jsonify({"status": "error", "error": "Missing item_id"}), 400

        if item_id not in set(get_agreed_removals(config)):
            return jsonify({"status": "not_agreed"}), 409

        item = _load_media_item(config, item_id)
        if item is None:
            return jsonify({"status": "not_found"}), 404

        imdb = item.get("imdb")
        if not imdb or imdb.startswith("http"):
            # Raw ID required for *arr matching.
            imdb = None if not imdb else _raw_imdb_id(imdb)
        if not imdb:
            return jsonify({"status": "no_imdb", "name": item.get("name")}), 422

        item_type = item.get("type") or "Movie"
        name = item.get("name")
        service = "Sonarr" if item_type == "Series" else "Radarr"

        try:
            if item_type == "Series":
                if not config.sonarr_enabled:
                    return jsonify({"status": "unavailable", "name": name}), 501
                arr = ArrClient(config.SONARR_URL, config.SONARR_API_KEY)
                arr_map = arr.list_series()
            else:
                if not config.radarr_enabled:
                    return jsonify({"status": "unavailable", "name": name}), 501
                arr = ArrClient(config.RADARR_URL, config.RADARR_API_KEY)
                arr_map = arr.list_movies()

            arr_id = arr_map.get(imdb)
            if arr_id is None:
                log.warning(
                    "Cleanup: %s (%s, %s) not in %s library", name, imdb, item_type, service
                )
                return (
                    jsonify(
                        {"status": "not_found", "name": name, "imdb": imdb, "service": service}
                    ),
                    404,
                )

            if item_type == "Series":
                arr.delete_series(arr_id)
            else:
                arr.delete_movie(arr_id)
        except RuntimeError as exc:
            log.error("Cleanup failed for %s: %s", name, exc)
            return jsonify({"status": "error", "name": name, "error": str(exc)}), 502

        client.refresh_library()
        remove_item_everywhere(config, item_id)
        log.info("Cleanup deleted %s (%s) from *arr", name, item_type)
        return jsonify({"status": "deleted", "name": name})


def _raw_imdb_id(value: str) -> str | None:
    """Extract tt-id from a full IMDb URL if needed."""
    tail = value.rstrip("/").split("/")[-1]
    return tail if tail.startswith("tt") else None
