"""Client for Sonarr / Radarr APIs."""

from __future__ import annotations

import logging

import httpx2

log = logging.getLogger("jellyfin_vote")


class ArrClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.url = base_url.rstrip("/")
        self._http = httpx2.Client(
            timeout=20,
            headers={
                "User-Agent": "jellyfin-vote/1.0",
                "X-Api-Key": api_key,
            },
        )

    def _list(self, endpoint: str) -> dict[str, int]:
        resp = self._http.get(f"{self.url}/api/v3/{endpoint}")
        if resp.status_code != 200:
            log.error("Arr %s failed: %s %s", endpoint, resp.status_code, resp.text[:200])
            raise RuntimeError(f"Arr {endpoint} returned {resp.status_code}")
        mapping: dict[str, int] = {}
        for entry in resp.json():
            imdb = (entry.get("imdbId") or "").strip()
            if imdb:
                mapping[imdb] = entry["id"]
        return mapping

    def list_movies(self) -> dict[str, int]:
        return self._list("movie")

    def list_series(self) -> dict[str, int]:
        return self._list("series")

    def delete_movie(self, movie_id: int) -> None:
        self._delete("movie", movie_id, "addImportExclusion")

    def delete_series(self, series_id: int) -> None:
        self._delete("series", series_id, "addImportListExclusion")

    def _delete(self, endpoint: str, item_id: int, exclusion_param: str) -> None:
        resp = self._http.delete(
            f"{self.url}/api/v3/{endpoint}/{item_id}",
            params={
                "deleteFiles": "true",
                exclusion_param: "true",
            },
        )
        if resp.status_code not in (200, 202):
            log.error(
                "Arr delete %s/%s failed: %s %s",
                endpoint,
                item_id,
                resp.status_code,
                resp.text[:200],
            )
            raise RuntimeError(f"Arr delete returned {resp.status_code}")
        log.info("Arr deleted %s %s", endpoint, item_id)
