from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from wallpaper_changer.bootstrap import AppServices, build_services  # noqa: E402
from wallpaper_changer.i18n import Translator  # noqa: E402
from wallpaper_changer.models import ChangeResult, Wallpaper  # noqa: E402
from wallpaper_changer.paths import get_app_paths  # noqa: E402
from wallpaper_changer.services.updates import UpdateInfo  # noqa: E402
from wallpaper_changer.ui import settings_window as settings_window_module  # noqa: E402
from wallpaper_changer.ui import tray as tray_module  # noqa: E402
from wallpaper_changer.ui.settings_window import SettingsWindow  # noqa: E402
from wallpaper_changer.ui.tray import TrayController  # noqa: E402


class InlineThreadPool:
    def start(self, worker) -> None:
        worker.run()


class FakeIntegration:
    def __init__(self):
        self.enabled: list[tuple[tuple, dict]] = []
        self.disabled = 0

    def enable(self, *args, **kwargs):
        self.enabled.append((args, kwargs))

    def disable(self):
        self.disabled += 1


@pytest.fixture
def ui(tmp_path):
    application = QApplication.instance() or QApplication([])
    services = build_services(get_app_paths(tmp_path / "appdata"))
    services.scheduler = FakeIntegration()
    services.startup = FakeIntegration()
    window = SettingsWindow(services, Translator("en"))
    window.thread_pool = InlineThreadPool()
    yield application, services, window
    window._catalog_timer.stop()
    window.hide()
    window.deleteLater()
    application.processEvents()


def _seed_history(services, tmp_path: Path) -> Wallpaper:
    wallpaper = Wallpaper(
        id="wallpaper-one",
        url="https://example.test/wallpaper.jpg",
        thumbnail_url="https://example.test/thumb.jpg",
        title="Quiet Mountain",
        category="nature",
        width=1920,
        height=1080,
        resolution="1920x1080",
    )
    current = tmp_path / "current.jpg"
    previous = tmp_path / "previous.jpg"
    current.write_bytes(b"not-an-image")
    previous.write_bytes(b"not-an-image")
    services.history.record(
        wallpaper,
        local_path=current,
        previous_path=previous,
        success=True,
    )
    services.settings_store.save(last_wallpaper_path=str(current))
    return wallpaper


def test_home_and_discover_buttons_call_their_actions(ui, tmp_path, monkeypatch):
    _application, services, window = ui
    wallpaper = _seed_history(services, tmp_path)
    calls: list[tuple[str, object]] = []

    def change_now(*, wallpaper=None, progress=None, **_kwargs):
        calls.append(("change", wallpaper))
        if progress:
            progress("Downloading")
        return ChangeResult(True, "Changed", wallpaper=wallpaper)

    monkeypatch.setattr(services.wallpaper, "change_now", change_now)
    monkeypatch.setattr(
        services.wallpaper,
        "undo",
        lambda: calls.append(("undo", None)) or ChangeResult(True, "Restored"),
    )
    monkeypatch.setattr(
        services.wallpaper,
        "toggle_current_favorite",
        lambda: calls.append(("favorite-current", None)) or True,
    )
    monkeypatch.setattr(
        services.wallpaper,
        "block_current",
        lambda: calls.append(("block-current", None)) or True,
    )
    monkeypatch.setattr(services.wallpaper, "catalog", lambda **_kwargs: [wallpaper])
    monkeypatch.setattr(services.downloader, "thumbnail", lambda _wallpaper: tmp_path / "missing.jpg")

    window.refresh_home()
    window.change_button.click()
    window.undo_button.click()
    window.favorite_button.click()
    window.block_button.click()
    window.automation_shortcut.click()

    assert window.pages.currentIndex() == 2
    assert ("change", None) in calls
    assert ("undo", None) in calls
    assert ("favorite-current", None) in calls
    assert ("block-current", None) in calls

    window.set_page(1)
    window.catalog_refresh.click()
    assert window.catalog.count() == 1
    window.catalog.setCurrentRow(0)
    assert window.apply_selected_button.isEnabled()
    window.favorite_selected_button.click()
    assert services.history.is_favorite(wallpaper.id)
    window.apply_selected_button.click()
    assert ("change", wallpaper) in calls


def test_automation_preferences_and_support_buttons(ui, tmp_path, monkeypatch):
    _application, services, window = ui
    opened: list[Path] = []
    diagnostics = tmp_path / "diagnostics.zip"

    monkeypatch.setattr(settings_window_module, "open_path", lambda path: opened.append(Path(path)))
    monkeypatch.setattr(AppServices, "export_diagnostics", lambda _self: diagnostics)
    monkeypatch.setattr(services.wallpaper, "test_connection", lambda: True)
    monkeypatch.setattr(
        services.updates,
        "check",
        lambda: UpdateInfo(False, "2.0.0", "2.0.0", ""),
    )

    window.rotation_enabled.setChecked(True)
    SettingsWindow._set_combo(window.rotation_mode_combo, "category")
    SettingsWindow._set_combo(window.target_mode_combo, "specific")
    assert window.rotation_category_combo.isEnabled()
    assert not window.rotation_color_combo.isEnabled()
    assert window.monitor_combo.isEnabled()

    window.automation_save_button.click()
    assert services.settings_store.settings.rotation_enabled
    assert services.scheduler.enabled
    assert window.automation_save_button.isEnabled()

    window.pause_hour_button.click()
    assert services.settings_store.settings.is_paused
    window.pause_today_button.click()
    assert services.settings_store.settings.is_paused
    window.resume_button.click()
    assert not services.settings_store.settings.is_paused

    window.connection_button.click()
    assert window.connection_button.isEnabled()
    assert "reachable" in window.status.currentMessage()
    window.open_folder_button.click()
    window.open_logs_button.click()
    window.diagnostics_button.click()
    window.update_button.click()
    window.save_button.click()

    assert opened == [services.paths.images, services.paths.logs, diagnostics.parent]
    assert window.update_button.isEnabled()
    assert services.scheduler.enabled


def test_discover_typing_is_debounced_and_selection_is_guarded(ui):
    _application, _services, window = ui
    window.set_page(1)
    window.search_input.setText("mountain")
    assert window._catalog_timer.isActive()
    assert not window.apply_selected_button.isEnabled()
    assert not window.favorite_selected_button.isEnabled()


def test_navigation_and_worker_failures_restore_controls(ui, monkeypatch):
    _application, services, window = ui
    for index, button in enumerate(window.nav_buttons):
        button.click()
        assert window.pages.currentIndex() == index
    window._catalog_timer.stop()

    def fail_change(**_kwargs):
        raise RuntimeError("download failed")

    def fail_catalog(**_kwargs):
        raise RuntimeError("catalog failed")

    monkeypatch.setattr(services.wallpaper, "change_now", fail_change)
    monkeypatch.setattr(services.wallpaper, "catalog", fail_catalog)
    window.change_button.click()
    assert window.change_button.isEnabled()
    assert "download failed" in window.status.currentMessage()
    window.load_catalog()
    assert window.catalog_refresh.isEnabled()
    assert "catalog failed" in window.status.currentMessage()
    assert not window.busy_bar.isVisible()


def test_tray_menu_actions_are_wired(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    services = build_services(get_app_paths(tmp_path / "tray-data"))
    services.settings_store.save(notifications_enabled=False)
    opened: list[Path] = []
    calls: list[str] = []

    def change_now(*, progress=None, **_kwargs):
        calls.append("change")
        if progress:
            progress("Working")
        return ChangeResult(True, "Changed")

    monkeypatch.setattr(services.wallpaper, "change_now", change_now)
    monkeypatch.setattr(
        services.wallpaper,
        "undo",
        lambda: calls.append("undo") or ChangeResult(True, "Restored"),
    )
    monkeypatch.setattr(
        services.wallpaper,
        "toggle_current_favorite",
        lambda: calls.append("favorite") or True,
    )
    monkeypatch.setattr(
        services.wallpaper,
        "block_current",
        lambda: calls.append("block") or True,
    )
    monkeypatch.setattr(tray_module, "open_path", lambda path: opened.append(Path(path)))

    controller = TrayController(application, services)
    controller.thread_pool = InlineThreadPool()
    assert controller.window is None
    quit_triggered: list[bool] = []
    controller.actions["quit"].triggered.connect(lambda: quit_triggered.append(True))

    for name in ("change", "undo", "favorite", "block", "pause_hour", "pause_day", "resume"):
        controller.actions[name].trigger()
    controller.actions["settings"].trigger()
    assert controller.window is not None
    controller.window.thread_pool = InlineThreadPool()
    controller.actions["folder"].trigger()
    controller.actions["logs"].trigger()
    controller.actions["quit"].trigger()

    assert {"change", "undo", "favorite", "block"}.issubset(calls)
    assert not services.settings_store.settings.is_paused
    assert controller.window.isVisible()
    assert opened == [services.paths.images, services.paths.logs]
    assert quit_triggered == [True]

    controller.window._catalog_timer.stop()
    controller.window.hide()
    controller.tray.hide()
    controller.window.deleteLater()
    controller.deleteLater()
    application.processEvents()
