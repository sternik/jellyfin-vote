"""Jellyfin Vote application factory."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask

from .config import Config


def create_app() -> Flask:
    load_dotenv()
    config = Config.from_env()

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=86400 * 7,
    )
    app.config.from_mapping({"APP_CONFIG": config})

    from .auth import register_auth_routes
    from .jellyfin import JellyfinClient
    from .media import register_media_routes
    from .results import register_results_routes
    from .routes_static import register_static_routes
    from .votes import register_votes_routes

    client = app.config.get("JELLYFIN_CLIENT") or JellyfinClient(config)
    register_auth_routes(app, config)
    register_media_routes(app, config, client)
    register_votes_routes(app, config)
    register_results_routes(app, config)
    register_static_routes(app, config)

    return app
