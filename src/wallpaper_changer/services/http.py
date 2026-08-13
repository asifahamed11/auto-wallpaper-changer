from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from wallpaper_changer import __version__

DEFAULT_TIMEOUT = (5, 30)


def build_http_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        status=3,
        allowed_methods=frozenset({"GET", "HEAD"}),
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
        backoff_factor=0.6,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": f"AutoWallpaperChanger/{__version__} (+https://github.com/asifahamed11/auto-wallpaper-changer)",
            "Accept": "application/json, image/*;q=0.9, */*;q=0.1",
        }
    )
    session.mount("https://", adapter)
    return session
