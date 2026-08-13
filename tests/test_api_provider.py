from __future__ import annotations

import json

import pytest

from wallpaper_changer.api.errors import ProviderError
from wallpaper_changer.api.wallwidgy_api import WallwidgyApiProvider


class FakeResponse:
    def __init__(self, payload, *, status=200, content_type="application/json"):
        self._payload = payload
        self.status_code = status
        self.headers = {"Content-Type": content_type}
        self.content = json.dumps(payload).encode()

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get(self, *_args, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def test_api_provider_uses_new_contract():
    session = FakeSession(
        FakeResponse(
            {
                "wallpapers": ["https://raw.githubusercontent.com/not-ayan/storage/main/main/forest.png"],
                "count": 1,
            }
        )
    )
    provider = WallwidgyApiProvider("https://wallwidgy.vercel.app/api/wallpapers", session=session)
    wallpapers = provider.fetch(count=30, orientation="desktop", category="#nature", color="blue")
    assert len(wallpapers) == 1
    assert session.last_kwargs["params"] == {
        "count": 10,
        "type": "desktop",
        "category": "nature",
        "color": "blue",
    }
    assert session.last_kwargs["timeout"] == (5, 30)


@pytest.mark.parametrize(
    ("payload", "content_type"),
    [([], "application/json"), ({"wallpapers": []}, "text/html")],
)
def test_api_provider_rejects_legacy_or_html_responses(payload, content_type):
    provider = WallwidgyApiProvider(
        "https://wallwidgy.vercel.app/api/wallpapers",
        session=FakeSession(FakeResponse(payload, content_type=content_type)),
    )
    with pytest.raises(ProviderError):
        provider.fetch()
