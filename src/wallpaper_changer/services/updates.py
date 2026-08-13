from __future__ import annotations

from dataclasses import dataclass

import requests

from wallpaper_changer import __version__
from wallpaper_changer.services.http import DEFAULT_TIMEOUT, build_http_session

LATEST_RELEASE_API = "https://api.github.com/repos/asifahamed11/auto-wallpaper-changer/releases/latest"


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str
    release_url: str
    notes: str = ""


class UpdateService:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or build_http_session()

    def check(self) -> UpdateInfo:
        response = self.session.get(LATEST_RELEASE_API, timeout=DEFAULT_TIMEOUT)
        if response.status_code == 404:
            return UpdateInfo(False, __version__, __version__, "")
        response.raise_for_status()
        payload = response.json()
        latest = str(payload.get("tag_name") or __version__).lstrip("v")
        return UpdateInfo(
            available=self._version_tuple(latest) > self._version_tuple(__version__),
            current_version=__version__,
            latest_version=latest,
            release_url=str(payload.get("html_url") or ""),
            notes=str(payload.get("body") or "")[:2000],
        )

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        result: list[int] = []
        for part in value.split("."):
            digits = "".join(character for character in part if character.isdigit())
            result.append(int(digits or 0))
        return tuple(result)
