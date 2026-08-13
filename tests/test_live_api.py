import pytest
import requests

from wallpaper_changer.api.errors import ProviderError
from wallpaper_changer.api.wallwidgy_api import WallwidgyApiProvider
from wallpaper_changer.config import DEFAULT_API_URL


@pytest.mark.live
def test_live_wallwidgy_api_contract():
    try:
        wallpapers = WallwidgyApiProvider(DEFAULT_API_URL).fetch(count=1, orientation="desktop")
    except ProviderError as exc:
        if isinstance(exc.__cause__, requests.RequestException):
            pytest.skip(f"Wallwidgy is temporarily unreachable: {exc}")
        raise
    assert len(wallpapers) == 1
    assert wallpapers[0].url.startswith("https://")
