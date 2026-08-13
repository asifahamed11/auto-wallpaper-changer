from __future__ import annotations

import os
from itertools import combinations
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QRect  # noqa: E402
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget  # noqa: E402

from wallpaper_changer.bootstrap import AppServices, build_services  # noqa: E402
from wallpaper_changer.config import AppSettings  # noqa: E402
from wallpaper_changer.i18n import Translator  # noqa: E402
from wallpaper_changer.models import ChangeResult, Wallpaper  # noqa: E402
from wallpaper_changer.paths import get_app_paths  # noqa: E402
from wallpaper_changer.services.updates import UpdateInfo  # noqa: E402
from wallpaper_changer.ui import settings_window as settings_window_module  # noqa: E402
from wallpaper_changer.ui import tray as tray_module  # noqa: E402
from wallpaper_changer.ui.settings_window import SettingsWindow  # noqa: E402
from wallpaper_changer.ui.tray import TrayController  # noqa: E402
from wallpaper_changer.ui.widgets import (  # noqa: E402
    AnimatedButton,
    RoundedComboBox,
    RoundedSpinBox,
)


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


def test_wallpaper_result_reapplies_the_derived_accent(ui):
    _application, services, window = ui
    assert window.change_button.colors is not None
    previous_accent = window.change_button.colors.accent

    services.settings_store.save(accent_color="#336699")
    window._change_finished(ChangeResult(True, "Changed"))

    assert previous_accent != "#336699"
    assert window.change_button.colors is not None
    assert window.change_button.colors.accent == "#336699"
    assert window.preview.colors is not None
    assert window.preview.colors.accent == "#336699"


def test_all_translated_buttons_fit_at_the_minimum_window_size(tmp_path):
    application = QApplication.instance() or QApplication([])
    for language in ("en", "bn"):
        services = build_services(get_app_paths(tmp_path / f"button-fit-{language}"))
        services.settings_store.save(language=language)
        window = SettingsWindow(services, Translator(language))
        window.resize(window.minimumSize())
        window.show()
        application.processEvents()

        for page in range(window.pages.count()):
            window.set_page(page, animate=False)
            window._catalog_timer.stop()
            application.processEvents()
            for button in window.findChildren(AnimatedButton):
                if button.isVisibleTo(window):
                    assert button.width() >= button.minimumSizeHint().width(), button.text()

        window._clock_timer.stop()
        window._catalog_timer.stop()
        window.hide()
        window.deleteLater()
        application.processEvents()


def test_dense_pages_scroll_without_overlapping_controls(ui):
    application, _services, window = ui
    window.resize(window.minimumSize())
    window.show()
    application.processEvents()

    for page in (2, 3):
        window.set_page(page, animate=False)
        application.processEvents()
        scroll = window.pages.currentWidget().findChild(QScrollArea)
        assert scroll is not None
        assert scroll.verticalScrollBar().maximum() > 0
        assert scroll.widget().width() <= scroll.viewport().width()

        content = scroll.widget()
        controls = [
            widget
            for widget in content.findChildren(QWidget)
            if isinstance(widget, (AnimatedButton, RoundedComboBox, RoundedSpinBox))
        ]
        for first, second in combinations(controls, 2):
            first_rect = QRect(first.mapTo(content, QPoint()), first.size())
            second_rect = QRect(second.mapTo(content, QPoint()), second.size())
            assert not first_rect.intersects(second_rect), (first.objectName(), second.objectName())


def test_home_controls_do_not_overlap_while_wallpaper_is_changing(ui):
    application, _services, window = ui
    window.show()
    window.set_page(0, animate=False)

    for width, height in ((1080, 760), (900, 640)):
        window.resize(width, height)
        window._set_wallpaper_busy(True, "Downloading and validating image")
        application.processEvents()
        assert window.busy_bar.isVisible()

        controls = (
            window.preview,
            window.current_title,
            window.current_meta,
            window.change_button,
            window.undo_button,
            window.favorite_button,
            window.block_button,
        )
        rectangles = {
            control: QRect(control.mapTo(window, QPoint()), control.size()) for control in controls
        }
        for first, second in combinations(controls, 2):
            assert not rectangles[first].intersects(rectangles[second]), (
                first.objectName(),
                second.objectName(),
            )

    window._set_wallpaper_busy(False, "Ready")


def test_every_option_is_saved_filters_are_forwarded_and_reset(ui, monkeypatch):
    _application, services, window = ui
    captured_filters: list[dict] = []
    monkeypatch.setattr(
        services.wallpaper,
        "catalog",
        lambda **kwargs: captured_filters.append(kwargs) or [],
    )
    monkeypatch.setattr(
        settings_window_module.QMessageBox,
        "question",
        lambda *_args, **_kwargs: settings_window_module.QMessageBox.StandardButton.Yes,
    )

    window.set_page(1)
    window._catalog_timer.stop()
    window.search_input.setText("aurora")
    SettingsWindow._set_combo(window.category_combo, "anime")
    SettingsWindow._set_combo(window.color_combo, "purple")
    SettingsWindow._set_combo(window.orientation_combo, "mobile")
    window.load_catalog(force=True)
    assert captured_filters[-1] == {
        "query": "aurora",
        "category": "anime",
        "color": "purple",
        "orientation": "mobile",
        "force_refresh": True,
    }

    SettingsWindow._set_combo(window.rotation_mode_combo, "color")
    SettingsWindow._set_combo(window.rotation_category_combo, "anime")
    SettingsWindow._set_combo(window.rotation_color_combo, "purple")
    SettingsWindow._set_combo_data(window.interval_combo, 180)
    SettingsWindow._set_combo(window.target_mode_combo, "specific")
    window.monitor_combo.addItem("Test display", "DISPLAY-TEST")
    SettingsWindow._set_combo_data(window.monitor_combo, "DISPLAY-TEST")
    SettingsWindow._set_combo(window.position_combo, "fit")
    window.rotation_enabled.setChecked(True)
    window.startup_enabled.setChecked(True)
    window.change_at_startup.setChecked(True)
    window.run_on_battery.setChecked(False)

    SettingsWindow._set_combo(window.theme_combo, "light")
    SettingsWindow._set_combo_data(window.language_combo, "bn")
    window.notifications_enabled.setChecked(False)
    window.derive_accent.setChecked(False)
    window.cache_spin.setValue(1024)
    window.download_spin.setValue(45)
    window.history_spin.setValue(777)
    window.update_checks.setChecked(False)
    SettingsWindow._set_combo(window.source_mode_combo, "index")
    window.save_settings()

    saved = services.settings_store.settings
    assert saved.language == "bn"
    assert saved.theme == "light"
    assert saved.orientation == "mobile"
    assert saved.category == "anime"
    assert saved.color == "purple"
    assert saved.rotation_mode == "color"
    assert saved.interval_minutes == 180
    assert saved.rotation_enabled
    assert saved.startup_enabled
    assert saved.change_at_startup
    assert not saved.run_on_battery
    assert saved.target_mode == "specific"
    assert saved.monitor_id == "DISPLAY-TEST"
    assert saved.wallpaper_position == "fit"
    assert not saved.notifications_enabled
    assert not saved.derive_accent_from_wallpaper
    assert saved.max_cache_mb == 1024
    assert saved.max_download_mb == 45
    assert saved.max_history_items == 777
    assert not saved.check_updates
    assert saved.source_mode == "index"
    assert services.scheduler.enabled[-1] == ((180,), {"run_on_battery": False})
    assert services.startup.enabled

    retained = Wallpaper.from_url("https://example.test/retained.jpg")
    services.history.record(retained, local_path=None, success=True)
    services.history.toggle_favorite(retained)
    window.reset_button.click()
    assert services.settings_store.settings == AppSettings()
    assert services.scheduler.disabled >= 1
    assert services.startup.disabled >= 1
    assert window.translator.language == "en"
    assert window.reset_button.isEnabled()
    assert services.history.last_successful().wallpaper_id == retained.id
    assert services.history.is_favorite(retained.id)


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
