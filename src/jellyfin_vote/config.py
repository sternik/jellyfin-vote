"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

_PLACEHOLDER_KEYS = frozenset({"", "dev-secret-key-change-me", "change-me", "changeme"})


@dataclass(frozen=True)
class Config:
    SECRET_KEY: str
    JELLYFIN_URL: str
    API_KEY: str
    USER_ID: str
    MEDIA_FILE: str
    USERS_FILE: str
    CACHE_DIR: str

    @staticmethod
    def from_env() -> Config:
        required = ("SECRET_KEY", "JELLYFIN_URL", "API_KEY", "USER_ID")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill in your Jellyfin details."
            )
        secret = os.environ["SECRET_KEY"]
        if secret.lower().strip() in _PLACEHOLDER_KEYS:
            raise RuntimeError(
                "SECRET_KEY is set to a placeholder value. "
                'Generate a real key: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data")
        return Config(
            SECRET_KEY=secret,
            JELLYFIN_URL=os.environ["JELLYFIN_URL"].rstrip("/"),
            API_KEY=os.environ["API_KEY"],
            USER_ID=os.environ["USER_ID"],
            MEDIA_FILE=os.environ.get("MEDIA_FILE", os.path.join(data_dir, "media.json")),
            USERS_FILE=os.environ.get("USERS_FILE", os.path.join(data_dir, "users.json")),
            CACHE_DIR=os.environ.get("CACHE_DIR", os.path.join(data_dir, "cache")),
        )
