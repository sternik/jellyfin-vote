"""Results endpoint: items every user agreed to remove."""

from __future__ import annotations

import json
import logging
import os

from flask import jsonify

from .auth import load_users, require_auth
from .config import Config

log = logging.getLogger("jellyfin_vote")


def register_results_routes(app, config: Config) -> None:
    @app.route("/api/results")
    @require_auth
    def results():
        data_dir = os.path.dirname(config.USERS_FILE)
        users = load_users(config)
        total_users = len(users)
        remove_counts: dict[str, int] = {}

        valid_ids: set[str] = set()
        if os.path.exists(config.MEDIA_FILE):
            try:
                with open(config.MEDIA_FILE, encoding="utf-8") as f:
                    for item in json.load(f):
                        valid_ids.add(item["id"])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        if not os.path.isdir(data_dir):
            return jsonify([])

        for fname in os.listdir(data_dir):
            if not (fname.startswith("votes_") and fname.endswith(".json")):
                continue
            try:
                with open(os.path.join(data_dir, fname), encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for item_id in data.get("remove", []):
                        if item_id in valid_ids:
                            remove_counts[item_id] = remove_counts.get(item_id, 0) + 1
            except (json.JSONDecodeError, OSError):
                continue

        agreed = [iid for iid, count in remove_counts.items() if count == total_users]
        return jsonify([{"id": iid} for iid in agreed])
