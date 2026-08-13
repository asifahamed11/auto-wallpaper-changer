from __future__ import annotations

import io

import pytest
from PIL import Image

from wallpaper_changer.api.errors import DownloadError
from wallpaper_changer.models import Wallpaper
from wallpaper_changer.services.downloader import ImageDownloader


class FakeResponse:
    def __init__(self, content: bytes, content_type: str = "image/png"):
        self.content = content
        self.status_code = 200
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}

    def iter_content(self, _size):
        yield self.content


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


def png_bytes(size=(800, 450)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (20, 80, 120)).save(output, "PNG")
    return output.getvalue()


def test_downloader_validates_and_atomically_saves_image(tmp_path):
    downloader = ImageDownloader(
        tmp_path / "images",
        tmp_path / "thumbs",
        session=FakeSession(FakeResponse(png_bytes())),
    )
    wallpaper = Wallpaper.from_url("https://raw.githubusercontent.com/test/repo/main/image.png")
    result = downloader.download(wallpaper)
    assert result.path.is_file()
    assert result.width == 800
    assert result.height == 450
    assert not list((tmp_path / "images").glob("*.part"))


def test_downloader_rejects_html_and_untrusted_hosts(tmp_path):
    downloader = ImageDownloader(
        tmp_path / "images",
        tmp_path / "thumbs",
        session=FakeSession(FakeResponse(b"<html>", "text/html")),
    )
    with pytest.raises(DownloadError, match="Untrusted"):
        downloader.download(Wallpaper.from_url("https://malicious.example/image.png"))
    with pytest.raises(DownloadError, match="Expected an image"):
        downloader.download(Wallpaper.from_url("https://raw.githubusercontent.com/test/repo/main/image.png"))
