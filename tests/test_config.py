from __future__ import annotations

import pytest

from jellyfin_vote.config import Config


def test_config_requires_env(monkeypatch):
    for name in ("SECRET_KEY", "JELLYFIN_URL", "API_KEY", "USER_ID"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        Config.from_env()


def test_config_partial_env_fails(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x")
    monkeypatch.setenv("JELLYFIN_URL", "https://example.com")
    # API_KEY and USER_ID missing
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("USER_ID", raising=False)
    with pytest.raises(RuntimeError):
        Config.from_env()


def test_config_full_env_succeeds(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "k")
    monkeypatch.setenv("JELLYFIN_URL", "https://example.com/jellyfin/")
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.setenv("USER_ID", "uid")
    cfg = Config.from_env()
    assert cfg.SECRET_KEY == "k"
    # Trailing slash stripped from JELLYFIN_URL.
    assert cfg.JELLYFIN_URL == "https://example.com/jellyfin"


def test_config_users_file_default(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "k")
    monkeypatch.setenv("JELLYFIN_URL", "https://example.com")
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.setenv("USER_ID", "uid")
    custom = tmp_path / "users.json"
    custom.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("USERS_FILE", str(custom))
    cfg = Config.from_env()
    assert cfg.USERS_FILE == str(custom)
