# Contributing

Thanks for considering a contribution to Jellyfin Vote!

## Development setup

```bash
# Recommended (uv)
uv venv
uv sync --extra dev

# Or with plain pip
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Create a `.env` from the example and fill in Jellyfin settings:

```bash
cp .env.example .env
```

Seed `data/users.json` with the accounts you want to be able to log in:

```json
{"alice": "pw1", "bob": "pw2"}
```

## Running the app

```bash
python app.py
# open http://127.0.0.1:8000
```

## Pre-commit

Install hooks once:

```bash
pre-commit install
```

This runs `ruff` and `black` on staged files. To run manually:

```bash
ruff check .
black .
pytest
```

## Pull requests

- Fork the repo, create a feature branch from `main`.
- Keep the change focused; one concern per PR.
- Add or update tests under `tests/` for any change to backend behavior.
- Make sure `ruff check`, `black --check .`, and `pytest` all pass.
- Write a clear commit message; the project follows
  [Conventional Commits](https://www.conventionalcommits.org/) prefixes
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## Project layout

```
src/jellyfin_vote/   backend modules
templates/           Jinja-style HTML pages (currently static HTMLs)
static/css|js|img/   frontend assets
data/                runtime data (users, votes, media cache)
tests/               pytest suite with fixtures
```

## Disclaimer

Jellyfin Vote is NOT affiliated with Jellyfin. "Jellyfin" is a trademark of
its respective owners. This project is an independent tool that talks to your
self-hosted Jellyfin server via its public API.