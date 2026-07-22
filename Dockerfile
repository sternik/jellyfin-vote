# syntax=docker/dockerfile:1.7

# ---------- Builder ----------
FROM python:3.13-slim AS builder
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY app.py ./
COPY templates ./templates
COPY static ./static
RUN uv sync --frozen --no-dev

# ---------- Runtime ----------
FROM python:3.13-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN useradd --create-home --uid 1000 jellyvote

# Copy installed deps + app source from builder
COPY --from=builder /app /app

# Make sure data dir exists and is writable by the runtime user
RUN mkdir -p /app/data && chown -R jellyvote:jellyvote /app/data

USER jellyvote
EXPOSE 8000

CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "jellyfin_vote:create_app()"]