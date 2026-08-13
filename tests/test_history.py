from pathlib import Path

from wallpaper_changer.models import Wallpaper
from wallpaper_changer.services.history import HistoryRepository


def test_history_favorites_block_and_trim(tmp_path):
    repository = HistoryRepository(tmp_path / "history.sqlite3")
    wallpaper = Wallpaper.from_url("https://raw.githubusercontent.com/test/repo/main/one.png")
    image = tmp_path / "one.png"
    image.write_bytes(b"image")
    repository.record(wallpaper, local_path=image, previous_path=tmp_path / "old.png", success=True)
    assert wallpaper.id in repository.used_ids()
    assert repository.last_successful().local_path == str(image)
    assert repository.toggle_favorite(wallpaper) is True
    assert repository.is_favorite(wallpaper.id)
    assert repository.toggle_favorite(wallpaper) is False
    repository.block(wallpaper.id)
    assert wallpaper.id in repository.blocked_ids()
    repository.trim(20)
    assert Path(repository.last_successful().local_path) == image
