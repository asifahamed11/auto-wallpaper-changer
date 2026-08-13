from __future__ import annotations

import json

from wallpaper_changer.config import AppSettings, SettingsStore


def test_settings_are_sanitized_and_saved_atomically(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    saved = store.save(
        AppSettings(
            language="invalid",
            interval_minutes=1,
            max_cache_mb=1,
            category="#nature",
            accent_color="broken",
        )
    )
    assert saved.language == "en"
    assert saved.interval_minutes == 15
    assert saved.max_cache_mb == 64
    assert saved.category == "nature"
    assert saved.accent_color == "#F7F06D"
    assert json.loads(store.path.read_text(encoding="utf-8"))["category"] == "nature"
    assert not store.path.with_suffix(".tmp").exists()


def test_corrupt_settings_are_recovered(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    store = SettingsStore(path)
    assert store.settings == AppSettings()
    assert path.with_suffix(".corrupt.json").exists()
