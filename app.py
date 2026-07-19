"""Entry point for development: `python app.py`.

For production, run via gunicorn:

    gunicorn "jellyfin_vote:create_app()"
"""

from jellyfin_vote import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
