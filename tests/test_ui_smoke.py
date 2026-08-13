from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from wallpaper_changer.bootstrap import build_services  # noqa: E402
from wallpaper_changer.i18n import Translator  # noqa: E402
from wallpaper_changer.paths import get_app_paths  # noqa: E402
from wallpaper_changer.ui.settings_window import SettingsWindow  # noqa: E402


class FakeIntegration:
    def enable(self, *_args, **_kwargs):
        return None

    def disable(self):
        return None


def test_settings_window_preserves_combo_data(tmp_path):
    app = QApplication.instance() or QApplication([])
    services = build_services(get_app_paths(tmp_path / "appdata"))
    services.scheduler = FakeIntegration()
    services.startup = FakeIntegration()
    window = SettingsWindow(services, Translator("en"))
    SettingsWindow._set_combo(window.orientation_combo, "mobile")
    SettingsWindow._set_combo(window.rotation_mode_combo, "color")
    SettingsWindow._set_combo(window.target_mode_combo, "different")
    SettingsWindow._set_combo(window.position_combo, "fit")
    SettingsWindow._set_combo(window.theme_combo, "dark")
    window.save_settings()
    saved = services.settings_store.settings
    assert saved.orientation == "mobile"
    assert saved.rotation_mode == "color"
    assert saved.target_mode == "different"
    assert saved.wallpaper_position == "fit"
    assert saved.theme == "dark"
    window.hide()
    window.deleteLater()
    app.processEvents()
