"""Static page routes — HTML pages and shared assets."""

from __future__ import annotations

import os

from flask import render_template, send_from_directory

from .config import Config


def register_static_routes(app, config: Config) -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    templates_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app.template_folder = templates_dir

    @app.route("/")
    def index():
        return render_template("vote.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/myvotes")
    def myvotes():
        return render_template("myvotes.html")

    @app.route("/results")
    def results_page():
        return render_template("results.html")

    @app.route("/css/<path:path>")
    def css(path: str):
        return send_from_directory(os.path.join(static_dir, "css"), path)

    @app.route("/js/<path:path>")
    def js(path: str):
        return send_from_directory(os.path.join(static_dir, "js"), path)

    @app.route("/img/<path:path>")
    def img(path: str):
        return send_from_directory(os.path.join(static_dir, "img"), path)
