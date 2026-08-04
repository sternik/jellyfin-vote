"""Authentication: login, logout, /me, session helpers."""

from __future__ import annotations

import logging
import re
from functools import wraps

from flask import jsonify, request, session

from .config import Config

log = logging.getLogger("jellyfin_vote")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def is_valid_username(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name or ""))


def require_auth(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if "user" not in session:
            return "", 401
        return f(*args, **kwargs)

    return inner


def register_auth_routes(app, config: Config, limiter=None, client=None) -> None:
    @app.route("/api/login", methods=["POST"])
    @limiter.limit("5/minute")
    def login():
        data = request.json or {}
        username = data.get("username", "")
        password = data.get("password", "")
        if not username:
            return jsonify({"error": "Invalid"}), 401
        # Authenticate against Jellyfin server.
        result = client.authenticate_user(username, password)
        if result:
            session.clear()
            session.permanent = True
            session["user"] = result["user"]
            session["jellyfin_user_id"] = result.get("user_id")
            return jsonify({"user": result["user"]})
        return jsonify({"error": "Invalid"}), 401

    @app.route("/api/logout")
    def logout():
        session.clear()
        return "", 200

    @app.route("/api/me")
    @require_auth
    def me():
        return jsonify({"user": session["user"]})
