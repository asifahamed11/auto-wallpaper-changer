from __future__ import annotations

from datetime import UTC, datetime, timedelta

from PySide6.QtCore import QObject, QThreadPool, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from wallpaper_changer.bootstrap import AppServices
from wallpaper_changer.i18n import Translator
from wallpaper_changer.models import ChangeResult
from wallpaper_changer.platform.windows_wallpaper import open_path
from wallpaper_changer.resources import asset_path
from wallpaper_changer.ui.settings_window import SettingsWindow
from wallpaper_changer.ui.workers import FunctionWorker


class TrayController(QObject):
    def __init__(self, application: QApplication, services: AppServices):
        super().__init__()
        self.application = application
        self.services = services
        self.translator = Translator(services.settings_store.settings.language)
        self.icon = QIcon(str(asset_path("icon.svg")))
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip(self.translator("app_name"))
        self.window: SettingsWindow | None = None
        self.tray.activated.connect(self._activated)
        self._active_workers: set[FunctionWorker] = set()
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(2)
        self.thread_pool.setExpiryTimeout(15_000)
        self.actions: dict[str, QAction] = {}
        self._build_menu()

    def start(self, *, show_window: bool) -> None:
        self.tray.show()
        if show_window or not QSystemTrayIcon.isSystemTrayAvailable():
            self.show_settings()
        if self.services.settings_store.settings.change_at_startup:
            QTimer.singleShot(1500, self.change_now)
        if self.services.settings_store.settings.check_updates:
            QTimer.singleShot(5000, self._background_update_check)

    def _build_menu(self) -> None:
        menu = QMenu()
        change_action = QAction(self.translator("change_now"), menu)
        change_action.triggered.connect(self.change_now)
        undo_action = QAction(self.translator("undo"), menu)
        undo_action.triggered.connect(self.undo)
        favorite_action = QAction(self.translator("favorite"), menu)
        favorite_action.triggered.connect(self.toggle_favorite)
        block_action = QAction(self.translator("never_show"), menu)
        block_action.triggered.connect(self.block_current)
        menu.addAction(change_action)
        menu.addAction(undo_action)
        menu.addAction(favorite_action)
        menu.addAction(block_action)
        menu.addSeparator()

        pause_menu = menu.addMenu(self.translator("pause_rotation"))
        pause_hour = QAction(self.translator("pause_1h"), pause_menu)
        pause_hour.triggered.connect(lambda: self.pause(hours=1))
        pause_day = QAction(self.translator("pause_today"), pause_menu)
        pause_day.triggered.connect(lambda: self.pause(hours=24))
        resume = QAction(self.translator("resume"), pause_menu)
        resume.triggered.connect(self.resume)
        pause_menu.addActions([pause_hour, pause_day, resume])
        menu.addSeparator()

        settings_action = QAction(self.translator("open_settings"), menu)
        settings_action.triggered.connect(self.show_settings)
        folder_action = QAction(self.translator("open_folder"), menu)
        folder_action.triggered.connect(lambda: open_path(self.services.paths.images))
        logs_action = QAction(self.translator("open_logs"), menu)
        logs_action.triggered.connect(lambda: open_path(self.services.paths.logs))
        quit_action = QAction(self.translator("quit"), menu)
        quit_action.triggered.connect(self.application.quit)
        menu.addAction(settings_action)
        menu.addAction(folder_action)
        menu.addAction(logs_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.actions = {
            "change": change_action,
            "undo": undo_action,
            "favorite": favorite_action,
            "block": block_action,
            "pause_hour": pause_hour,
            "pause_day": pause_day,
            "resume": resume,
            "settings": settings_action,
            "folder": folder_action,
            "logs": logs_action,
            "quit": quit_action,
        }
        self.tray.setContextMenu(menu)

    def show_settings(self) -> None:
        window = self._ensure_window()
        window.show()
        window.showNormal()
        window.raise_()
        window.activateWindow()

    def _ensure_window(self) -> SettingsWindow:
        if self.window is None:
            self.window = SettingsWindow(self.services, self.translator)
            self.window.wallpaper_result.connect(self._show_result)
            self.window.settings_saved.connect(self._settings_saved)
        return self.window

    def change_now(self) -> None:
        self.tray.setToolTip(self.translator("loading"))
        worker = FunctionWorker(self.services.wallpaper.change_now, with_progress=True)
        worker.signals.progress.connect(self.tray.setToolTip)
        worker.signals.finished.connect(self._show_result)
        worker.signals.failed.connect(lambda message: self._show_result(ChangeResult(False, message)))
        self._start_worker(worker)

    def undo(self) -> None:
        worker = FunctionWorker(self.services.wallpaper.undo)
        worker.signals.finished.connect(self._show_result)
        worker.signals.failed.connect(lambda message: self._show_result(ChangeResult(False, message)))
        self._start_worker(worker)

    def toggle_favorite(self) -> None:
        state = self.services.wallpaper.toggle_current_favorite()
        if state is not None:
            self._notify(
                self.translator("favorites"),
                self.translator("added_favorite") if state else self.translator("removed_favorite"),
            )

    def block_current(self) -> None:
        if self.services.wallpaper.block_current():
            self._notify(self.translator("app_name"), self.translator("blocked"))

    def pause(self, *, hours: int) -> None:
        until = datetime.now(UTC) + timedelta(hours=hours)
        self.services.settings_store.save(pause_until=until.isoformat())
        self._notify(self.translator("app_name"), self.translator("status_paused"))
        if self.window is not None:
            self.window.refresh_home()

    def resume(self) -> None:
        self.services.settings_store.save(pause_until=None)
        self._notify(self.translator("app_name"), self.translator("resume"))
        if self.window is not None:
            self.window.refresh_home()

    def _show_result(self, result: ChangeResult) -> None:
        self.tray.setToolTip(self.translator("app_name"))
        title = self.translator("changed") if result.success else self.translator("change_failed")
        self._notify(title, result.message, success=result.success)
        if self.window is not None:
            self.window.refresh_home()

    def _notify(self, title: str, message: str, *, success: bool = True) -> None:
        if not self.services.settings_store.settings.notifications_enabled:
            return
        icon = QSystemTrayIcon.MessageIcon.Information if success else QSystemTrayIcon.MessageIcon.Warning
        self.tray.showMessage(title, message, icon, 7000)

    def _settings_saved(self, settings) -> None:
        language_changed = self.window is not None and self.window.ui_language != settings.language
        self.translator.set_language(settings.language)
        self.tray.setToolTip(self.translator("app_name"))
        self._build_menu()
        if language_changed:
            QTimer.singleShot(120, self._rebuild_window_for_language)

    def _rebuild_window_for_language(self) -> None:
        if self.window is None:
            return
        old_window = self.window
        was_visible = old_window.isVisible()
        geometry = old_window.saveGeometry()
        page_index = old_window.pages.currentIndex()
        old_window.hide()
        self.window = SettingsWindow(self.services, self.translator)
        self.window.restoreGeometry(geometry)
        self.window.set_page(page_index, animate=False)
        self.window.wallpaper_result.connect(self._show_result)
        self.window.settings_saved.connect(self._settings_saved)
        old_window.deleteLater()
        if was_visible:
            self.show_settings()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.show_settings()

    def _background_update_check(self) -> None:
        worker = FunctionWorker(self.services.updates.check)
        worker.signals.finished.connect(
            lambda update: self._notify(
                self.translator("update_available"),
                f"Version {update.latest_version} is available.",
            )
            if update.available
            else None
        )
        self._start_worker(worker)

    def _start_worker(self, worker: FunctionWorker) -> None:
        self._active_workers.add(worker)
        worker.signals.finished.connect(lambda _result, current=worker: self._active_workers.discard(current))
        worker.signals.failed.connect(lambda _message, current=worker: self._active_workers.discard(current))
        self.thread_pool.start(worker)
