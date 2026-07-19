"""Thin client around the Jellyfin server API."""

from __future__ import annotations

import logging
from typing import Any

import requests

from .config import Config

log = logging.getLogger("jellyfin_vote")


class JellyfinClient:
    def __init__(self, config: Config) -> None:
        self.url = config.JELLYFIN_URL
        self.api_key = config.API_KEY
        self.user_id = config.USER_ID

    def list_items(self) -> list[dict[str, Any]]:
        endpoint = f"{self.url}/Users/{self.user_id}/Items"
        params = {
            "api_key": self.api_key,
            "Recursive": "true",
            "IncludeItemTypes": "Movie,Series",
            "Fields": "Path,PrimaryImageAspectRatio,Type,Overview,ProviderIds,ProductionYear",
        }
        resp = requests.get(endpoint, params=params, timeout=20)
        if resp.status_code != 200:
            log.error("Jellyfin list_items failed: %s %s", resp.status_code, resp.text[:200])
            return []
        return resp.json().get("Items", [])

    def fetch_image(self, item_id: str) -> tuple[bytes, str] | None:
        resp = requests.get(
            f"{self.url}/Items/{item_id}/Images/Primary",
            params={"fillHeight": 400, "api_key": self.api_key},
            timeout=20,
        )
        if not resp.ok:
            return None
        return resp.content, resp.headers.get("Content-Type", "image/jpeg")

    @staticmethod
    def normalize(item: dict[str, Any], base_url: str) -> dict[str, Any]:
        provider_ids = item.get("ProviderIds", {}) or {}
        imdb_id = provider_ids.get("IMDb")
        return {
            "id": item.get("Id"),
            "name": item.get("Name"),
            "type": item.get("Type"),
            "year": item.get("ProductionYear"),
            "overview": item.get("Overview"),
            "imdb": f"https://www.imdb.com/title/{imdb_id}" if imdb_id else None,
            "poster": f"/api/img/{item.get('Id')}",
            "link": f"{base_url}/web/index.html#!/details?id={item.get('Id')}",
        }
