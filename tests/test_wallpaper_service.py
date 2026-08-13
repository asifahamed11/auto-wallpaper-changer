from __future__ import annotations

from pathlib import Path

from PIL import Image

from wallpaper_changer.config import SettingsStore
from wallpaper_changer.models import DownloadedWallpaper, Monitor, Wallpaper
from wallpaper_changer.services.history import HistoryRepository
from wallpaper_changer.services.wallpaper_service import WallpaperService


class FakeApi:
    def __init__(self, wallpaper):
        self.wallpaper = wallpaper

    def fetch(self, **_kwargs):
        return [self.wallpaper]

    def test_connection(self):
        return True


class FakeIndex:
    def search(self, **_kwargs):
        return []


class FakeDownloader:
    def __init__(self, path):
        self.path = path
        self.cleaned = False

    def download(self, wallpaper):
        return DownloadedWallpaper(
            wallpaper=wallpaper,
            path=self.path,
            content_type="image/png",
            size_bytes=self.path.stat().st_size,
            sha256="abc",
            width=1920,
            height=1080,
        )

    def dominant_color(self, _path):
        return "#123456"

    def cleanup(self, *_args, **_kwargs):
        self.cleaned = True
        return 0


class FakePlatform:
    def __init__(self, previous):
        self.current = previous
        self.applied = []

    def get_current(self, _monitor_id=None):
        return self.current

    def set_wallpaper(self, path, *, monitor_id=None, position="fill"):
        self.applied.append((Path(path), monitor_id, position))
        self.current = Path(path)

    def monitors(self):
        return [Monitor("display-1", "Display 1", 0, 0, 1920, 1080)]


def test_change_and_undo_are_recorded(tmp_path):
    previous = tmp_path / "previous.png"
    selected = tmp_path / "selected.png"
    Image.new("RGB", (640, 360), "blue").save(previous)
    Image.new("RGB", (640, 360), "green").save(selected)
    wallpaper = Wallpaper.from_url("https://raw.githubusercontent.com/test/repo/main/selected.png")
    store = SettingsStore(tmp_path / "settings.json")
    history = HistoryRepository(tmp_path / "history.sqlite3")
    downloader = FakeDownloader(selected)
    platform = FakePlatform(previous)
    service = WallpaperService(
        store,
        FakeApi(wallpaper),
        FakeIndex(),
        downloader,
        history,
        platform,
    )

    result = service.change_now()
    assert result.success
    assert platform.applied[-1][0] == selected
    assert history.last_successful().previous_path == str(previous)
    assert store.settings.accent_color == "#123456"
    assert downloader.cleaned

    undo = service.undo()
    assert undo.success
    assert platform.applied[-1][0] == previous
