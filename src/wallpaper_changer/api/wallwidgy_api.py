from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

import requests

from wallpaper_changer.api.errors import ProviderError
from wallpaper_changer.models import Wallpaper
from wallpaper_changer.services.http import DEFAULT_TIMEOUT, build_http_session


class WallwidgyApiProvider:
    def __init__(self, api_url: str, session: requests.Session | None = None):
        self.api_url = api_url
        self.session = session or build_http_session()

    def fetch(
        self,
        *,
        count: int = 10,
        orientation: str = "desktop",
        category: str = "all",
        color: str = "all",
    ) -> list[Wallpaper]:
        count = min(max(int(count), 1), 10)
        params: dict[str, str | int] = {"count": count}
        if orientation in {"desktop", "mobile"}:
            params["type"] = orientation
        if category and category.lower() != "all":
            params["category"] = category.lstrip("#")
        if color and color.lower() != "all":
            params["color"] = color.lower()

        try:
            response = self.session.get(self.api_url, params=params, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise ProviderError(f"Wallwidgy API request failed: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(f"Wallwidgy API returned HTTP {response.status_code}")
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type:
            raise ProviderError(
                f"Wallwidgy API returned unexpected content type: {content_type or 'unknown'}"
            )
        if len(response.content) > 1_000_000:
            raise ProviderError("Wallwidgy API response exceeded the 1 MB safety limit")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("Wallwidgy API returned malformed JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("wallpapers"), list):
            raise ProviderError("Wallwidgy API response schema is not supported")

        wallpapers = [Wallpaper.from_url(url) for url in self._valid_urls(payload["wallpapers"])]
        if not wallpapers:
            raise ProviderError("Wallwidgy API returned no matching wallpapers")
        return wallpapers

    @staticmethod
    def _valid_urls(values: Iterable[object]) -> Iterable[str]:
        for value in values:
            if not isinstance(value, str):
                continue
            parsed = urlparse(value)
            if parsed.scheme == "https" and parsed.hostname:
                yield value

    def test_connection(self) -> bool:
        return bool(self.fetch(count=1, orientation="desktop"))
