"""Authentication: login, logout, /me, session helpers."""

from __future__ import annotations

import json
import logging
import os
import re
from functools import wraps

from flask import jsonify, request, session

from .config import Config

log = logging.getLogger("jellyfin_vote")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def load_users(config: Config) -> dict[str, str]:
    if not os.path.exists(config.USERS_FILE):
        return {}
    try:
        with open(config.USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        log.warning("users file unreadable: %s", config.USERS_FILE)
        return {}


def is_valid_username(name: str) -> bool:
    return bool(USERNAME_RE.fullmatch(name or ""))


def require_auth(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if "user" not in session:
            return "", 401
        return f(*args, **kwargs)

    return inner


def register_auth_routes(app, config: Config) -> None:
    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.json or {}
        username = data.get("username", "")
        password = data.get("password", "")
        users = load_users(config)
        if username in users and users[username] == password:
            session.permanent = True
            session["user"] = username
            return jsonify({"user": username})
        return jsonify({"error": "Invalid"}), 401

    @app.route("/api/logout")
    def logout():
        session.clear()
        return "", 200

    @app.route("/api/me")
    @require_auth
    def me():
        return jsonify({"user": session["user"]})
