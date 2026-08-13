from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from wallpaper_changer.api.errors import ProviderError
from wallpaper_changer.models import Wallpaper
from wallpaper_changer.services.http import build_http_session

MAX_INDEX_BYTES = 20 * 1024 * 1024


class WallwidgyIndexProvider:
    def __init__(
        self,
        index_url: str,
        base_url: str,
        cache_path: Path,
        metadata_path: Path,
        session: requests.Session | None = None,
    ):
        self.index_url = index_url
        self.base_url = base_url
        self.cache_path = cache_path
        self.metadata_path = metadata_path
        self.session = session or build_http_session()

    def load(self, *, force_refresh: bool = False) -> list[Wallpaper]:
        if not force_refresh and self._cache_is_fresh():
            try:
                return self._parse_file(self.cache_path)
            except (OSError, ValueError, json.JSONDecodeError):
                pass

        try:
            self._refresh()
        except ProviderError:
            if self.cache_path.exists():
                return self._parse_file(self.cache_path)
            raise
        return self._parse_file(self.cache_path)

    def search(
        self,
        *,
        query: str = "",
        category: str = "all",
        color: str = "all",
        orientation: str = "desktop",
        limit: int = 60,
        force_refresh: bool = False,
    ) -> list[Wallpaper]:
        query_tokens = [token.lower() for token in query.split() if token]
        clean_category = category.lower().lstrip("#")
        clean_color = color.lower()
        results: list[Wallpaper] = []
        for wallpaper in self.load(force_refresh=force_refresh):
            if orientation != "all" and wallpaper.orientation.lower() != orientation:
                continue
            if clean_category != "all" and wallpaper.category.lower() != clean_category:
                continue
            if clean_color != "all" and clean_color not in wallpaper.colors:
                continue
            haystack = " ".join(
                [wallpaper.title, wallpaper.category, wallpaper.resolution, *wallpaper.colors]
            ).lower()
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            results.append(wallpaper)
            if len(results) >= max(1, limit):
                break
        return results

    def categories(self) -> list[str]:
        return sorted({item.category for item in self.load() if item.category and item.category != "all"})

    def colors(self) -> list[str]:
        return sorted({color for item in self.load() for color in item.colors})

    def _refresh(self) -> None:
        metadata = self._read_metadata()
        headers: dict[str, str] = {"Accept": "application/json"}
        if metadata.get("etag"):
            headers["If-None-Match"] = str(metadata["etag"])
        if metadata.get("last_modified"):
            headers["If-Modified-Since"] = str(metadata["last_modified"])
        try:
            response = self.session.get(
                self.index_url,
                headers=headers,
                timeout=(8, 60),
                stream=True,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Wallwidgy index request failed: {exc}") from exc

        if response.status_code == 304 and self.cache_path.exists():
            metadata["checked_at"] = datetime.now(UTC).isoformat()
            self._write_metadata(metadata)
            return
        if response.status_code != 200:
            raise ProviderError(f"Wallwidgy index returned HTTP {response.status_code}")

        content_length = int(response.headers.get("Content-Length") or 0)
        if content_length > MAX_INDEX_BYTES:
            raise ProviderError("Wallwidgy index exceeded the 20 MB safety limit")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(".part")
        received = 0
        try:
            with temporary.open("wb") as output:
                for chunk in response.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > MAX_INDEX_BYTES:
                        raise ProviderError("Wallwidgy index exceeded the 20 MB safety limit")
                    output.write(chunk)
            self._parse_file(temporary)
            os.replace(temporary, self.cache_path)
        finally:
            temporary.unlink(missing_ok=True)

        self._write_metadata(
            {
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "checked_at": datetime.now(UTC).isoformat(),
            }
        )

    def _parse_file(self, path: Path) -> list[Wallpaper]:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ProviderError("Wallwidgy index root must be an array")
        wallpapers: list[Wallpaper] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                wallpapers.append(Wallpaper.from_index(item, self.base_url))
            except (TypeError, ValueError):
                continue
        if not wallpapers:
            raise ProviderError("Wallwidgy index contained no usable wallpapers")
        return wallpapers

    def _cache_is_fresh(self) -> bool:
        if not self.cache_path.exists():
            return False
        checked_at = self._read_metadata().get("checked_at")
        if not checked_at:
            return False
        try:
            checked = datetime.fromisoformat(str(checked_at))
            if checked.tzinfo is None:
                checked = checked.replace(tzinfo=UTC)
            return datetime.now(UTC) - checked < timedelta(hours=24)
        except ValueError:
            return False

    def _read_metadata(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError, json.JSONDecodeError):
            return {}

    def _write_metadata(self, metadata: dict[str, Any]) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        os.replace(temporary, self.metadata_path)
