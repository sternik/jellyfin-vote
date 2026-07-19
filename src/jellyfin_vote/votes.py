"""Votes endpoints, scoped to the session user."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from flask import jsonify, request, session

from .auth import is_valid_username, require_auth
from .config import Config

log = logging.getLogger("jellyfin_vote")


def votes_file(config: Config, username: str) -> str:
    return os.path.join(os.path.dirname(config.USERS_FILE), f"votes_{username}.json")


def register_votes_routes(app, config: Config) -> None:
    @app.route("/api/votes/<username>", methods=["GET"])
    @require_auth
    def get_votes(username: str):
        if username != session["user"]:
            return "", 403
        if not is_valid_username(username):
            return "", 400
        path = votes_file(config, username)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return jsonify({"keep": [], "remove": []})
        try:
            with open(path, encoding="utf-8") as f:
                return jsonify(json.load(f))
        except (json.JSONDecodeError, OSError):
            return jsonify({"keep": [], "remove": []})

    @app.route("/api/votes/<username>", methods=["POST"])
    @require_auth
    def save_votes(username: str):
        if username != session["user"]:
            return "", 403
        if not is_valid_username(username):
            return "", 400
        data: Any = request.json
        if not isinstance(data, dict) or "keep" not in data or "remove" not in data:
            return "", 400
        if not (isinstance(data["keep"], list) and isinstance(data["remove"], list)):
            return "", 400
        keep = [str(x) for x in data["keep"] if isinstance(x, (str, int))]
        remove = [str(x) for x in data["remove"] if isinstance(x, (str, int))]
        path = votes_file(config, username)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"keep": keep, "remove": remove}, f)
        return "", 200
