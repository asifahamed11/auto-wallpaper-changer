from __future__ import annotations

import logging
import webbrowser
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from wallpaper_changer import __version__
from wallpaper_changer.bootstrap import AppServices
from wallpaper_changer.config import AppSettings
from wallpaper_changer.i18n import Translator
from wallpaper_changer.models import ChangeResult, Wallpaper
from wallpaper_changer.platform.windows_wallpaper import open_path
from wallpaper_changer.resources import asset_path
from wallpaper_changer.services.scheduler import SchedulerError
from wallpaper_changer.services.startup import StartupError
from wallpaper_changer.ui.styles import stylesheet
from wallpaper_changer.ui.widgets import FadeStackedWidget
from wallpaper_changer.ui.workers import FunctionWorker

LOGGER = logging.getLogger("wallpaper_changer.ui")
CATEGORIES = ["all", "abstract", "anime", "architecture", "art", "cars", "minimal", "nature", "tech"]
COLORS = ["all", "blue", "red", "green", "purple", "pink", "orange", "yellow", "black", "white"]


class SettingsWindow(QMainWindow):
    wallpaper_result = Signal(object)
    settings_saved = Signal(object)

    def __init__(self, services: AppServices, translator: Translator):
        super().__init__()
        self.services = services
        self.translator = translator
        self.ui_language = translator.language
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(6)
        self.thread_pool.setExpiryTimeout(15_000)
        self._active_workers: set[FunctionWorker] = set()
        self._busy_reasons: set[str] = set()
        self._catalog_generation = 0
        self._preview_pixmap = QPixmap()
        self._preview_path: Path | None = None
        self._first_show = True
        self._window_animation: QPropertyAnimation | None = None

        self._catalog_timer = QTimer(self)
        self._catalog_timer.setSingleShot(True)
        self._catalog_timer.setInterval(380)
        self._catalog_timer.timeout.connect(self.load_catalog)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(90)
        self._preview_timer.timeout.connect(self._render_preview)

        self._build_ui()
        self._load_settings()
        self._apply_style()
        self.refresh_home()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_next_change)
        self._clock_timer.start(30_000)

    def _build_ui(self) -> None:
        self.setWindowTitle(self.translator("app_name"))
        self.setMinimumSize(900, 640)
        self.resize(1080, 760)

        root = QWidget(objectName="AppRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 10)
        root_layout.setSpacing(20)

        navigation = QFrame(objectName="NavRail")
        navigation.setFixedWidth(194)
        nav_layout = QVBoxLayout(navigation)
        nav_layout.setContentsMargins(14, 18, 14, 14)
        nav_layout.setSpacing(7)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand_icon = QLabel(objectName="BrandMark")
        brand_icon.setFixedSize(38, 38)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QPixmap(str(asset_path("icon.svg")))
        if not icon.isNull():
            brand_icon.setPixmap(icon.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(QLabel("Wallwidgy", objectName="BrandTitle"))
        brand_subtitle = QLabel(self.translator("app_tagline"), objectName="Muted")
        brand_subtitle.setWordWrap(True)
        brand_text.addWidget(brand_subtitle)
        brand.addWidget(brand_icon)
        brand.addLayout(brand_text, 1)
        nav_layout.addLayout(brand)
        nav_layout.addSpacing(18)

        self.nav_buttons: list[QPushButton] = []
        for index, key in enumerate(("home", "discover", "automation", "settings")):
            button = QPushButton(self.translator(key), objectName="NavButton")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("pageIndex", index)
            button.setAccessibleName(self.translator(key))
            button.clicked.connect(lambda _checked=False, page=index: self.set_page(page))
            self.nav_buttons.append(button)
            nav_layout.addWidget(button)
        nav_layout.addStretch()
        self.nav_status = QLabel(objectName="StatusPill")
        self.nav_status.setWordWrap(True)
        nav_layout.addWidget(self.nav_status)
        nav_layout.addWidget(QLabel(f"v{__version__}  •  Windows", objectName="Muted"))
        root_layout.addWidget(navigation)

        content = QWidget(objectName="ContentSurface")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 5, 6, 0)
        content_layout.setSpacing(10)
        self.page_title = QLabel(objectName="PageTitle")
        self.page_subtitle = QLabel(objectName="PageSubtitle")
        self.page_subtitle.setWordWrap(True)
        content_layout.addWidget(self.page_title)
        content_layout.addWidget(self.page_subtitle)

        self.busy_bar = QProgressBar(objectName="BusyBar")
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setTextVisible(False)
        self.busy_bar.setFixedHeight(4)
        self.busy_bar.hide()
        content_layout.addWidget(self.busy_bar)

        self.pages = FadeStackedWidget()
        self.home_tab = self._build_home_tab()
        self.discover_tab = self._build_discover_tab()
        self.automation_tab = self._build_automation_tab()
        self.general_tab = self._build_general_tab()
        for page in (self.home_tab, self.discover_tab, self.automation_tab, self.general_tab):
            self.pages.addWidget(page)
        self.tabs = self.pages  # Compatibility for integrations that used the former tab widget.
        content_layout.addWidget(self.pages, 1)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.status.showMessage(self.translator("status_ready"))
        self.setStatusBar(self.status)
        self.set_page(0, animate=False)

    def _build_home_tab(self) -> QWidget:
        page = QWidget(objectName="Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)

        preview_card, preview_layout = self._card(self.translator("current_wallpaper"))
        self.preview = QLabel("WALLWIDGY", objectName="Preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(300)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.preview, 1)

        details = QHBoxLayout()
        details.setSpacing(12)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        self.current_title = QLabel("—", objectName="HeroTitle")
        self.current_title.setWordWrap(True)
        self.current_meta = QLabel("", objectName="Muted")
        title_column.addWidget(self.current_title)
        title_column.addWidget(self.current_meta)
        details.addLayout(title_column, 1)
        self.change_button = self._button(self.translator("change_now"), "Primary", "Ctrl+N")
        details.addWidget(self.change_button)
        preview_layout.addLayout(details)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.undo_button = self._button(self.translator("undo"), shortcut="Ctrl+Z")
        self.favorite_button = self._button(self.translator("favorite"))
        self.block_button = self._button(self.translator("never_show"), "Danger")
        for button in (self.undo_button, self.favorite_button, self.block_button):
            actions.addWidget(button)
        actions.addStretch()
        preview_layout.addLayout(actions)
        layout.addWidget(preview_card, 1)

        schedule_card, schedule_layout = self._card(self.translator("next_change"))
        schedule_row = QHBoxLayout()
        schedule_text = QVBoxLayout()
        schedule_text.setSpacing(2)
        self.next_change_label = QLabel("—", objectName="SectionTitle")
        self.rotation_status = QLabel("", objectName="Muted")
        schedule_text.addWidget(self.next_change_label)
        schedule_text.addWidget(self.rotation_status)
        schedule_row.addLayout(schedule_text, 1)
        self.automation_shortcut = self._button(self.translator("open_automation"), "Quiet")
        schedule_row.addWidget(self.automation_shortcut)
        schedule_layout.addLayout(schedule_row)
        layout.addWidget(schedule_card)

        self.change_button.clicked.connect(lambda _checked=False: self.change_now())
        self.undo_button.clicked.connect(self.undo)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        self.block_button.clicked.connect(self.block_current)
        self.automation_shortcut.clicked.connect(lambda: self.set_page(2))
        return page

    def _build_discover_tab(self) -> QWidget:
        page = QWidget(objectName="Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        filter_card, filter_layout = self._card(self.translator("discover"))
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.translator("search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName(self.translator("search"))
        self.catalog_refresh = self._button(self.translator("refresh"))
        self.catalog_refresh.setToolTip(self.translator("filter_hint"))
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.catalog_refresh)
        filter_layout.addLayout(search_row)

        filters = QHBoxLayout()
        self.category_combo = self._combo(CATEGORIES)
        self.color_combo = self._combo(COLORS)
        self.orientation_combo = self._combo(["desktop", "mobile", "all"])
        self.category_combo.setAccessibleName(self.translator("category"))
        self.color_combo.setAccessibleName(self.translator("color"))
        self.orientation_combo.setAccessibleName(self.translator("orientation"))
        self.category_combo.setToolTip(self.translator("category"))
        self.color_combo.setToolTip(self.translator("color"))
        self.orientation_combo.setToolTip(self.translator("orientation"))
        filters.addWidget(self.category_combo)
        filters.addWidget(self.color_combo)
        filters.addWidget(self.orientation_combo)
        filters.addStretch()
        filter_layout.addLayout(filters)
        layout.addWidget(filter_card)

        self.catalog = QListWidget()
        self.catalog.setViewMode(QListWidget.ViewMode.IconMode)
        self.catalog.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.catalog.setMovement(QListWidget.Movement.Static)
        self.catalog.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.catalog.setIconSize(QSize(210, 128))
        self.catalog.setGridSize(QSize(238, 184))
        self.catalog.setWordWrap(True)
        self.catalog.setUniformItemSizes(True)
        self.catalog.setMouseTracking(True)
        self.catalog.setAccessibleName("Wallpaper gallery")
        layout.addWidget(self.catalog, 1)

        actions = QHBoxLayout()
        self.selection_hint = QLabel(self.translator("select_wallpaper"), objectName="Muted")
        self.apply_selected_button = self._button(self.translator("change_now"), "Primary")
        self.favorite_selected_button = self._button(self.translator("favorite"))
        self.apply_selected_button.setEnabled(False)
        self.favorite_selected_button.setEnabled(False)
        actions.addWidget(self.selection_hint, 1)
        actions.addWidget(self.favorite_selected_button)
        actions.addWidget(self.apply_selected_button)
        layout.addLayout(actions)

        self.catalog_refresh.clicked.connect(lambda: self.load_catalog(force=True))
        self.search_input.textChanged.connect(self._schedule_catalog_load)
        self.search_input.returnPressed.connect(self._load_catalog_immediately)
        self.category_combo.currentIndexChanged.connect(self._schedule_catalog_load)
        self.color_combo.currentIndexChanged.connect(self._schedule_catalog_load)
        self.orientation_combo.currentIndexChanged.connect(self._schedule_catalog_load)
        self.catalog.currentItemChanged.connect(self._catalog_selection_changed)
        self.catalog.itemDoubleClicked.connect(lambda _item: self.apply_selected())
        self.apply_selected_button.clicked.connect(self.apply_selected)
        self.favorite_selected_button.clicked.connect(self.favorite_selected)
        return page

    def _build_automation_tab(self) -> QWidget:
        page = QWidget(objectName="Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)
        rotation_card, rotation_layout = self._card(self.translator("rotation"))
        hint = QLabel(self.translator("automation_hint"), objectName="Muted")
        hint.setWordWrap(True)
        rotation_layout.addWidget(hint)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(28)
        form.setVerticalSpacing(12)
        self.rotation_enabled = QCheckBox(self.translator("rotation"))
        self.interval_combo = QComboBox()
        for label, minutes in (
            ("15 minutes", 15),
            ("30 minutes", 30),
            ("1 hour", 60),
            ("3 hours", 180),
            ("6 hours", 360),
            ("12 hours", 720),
            ("1 day", 1440),
        ):
            self.interval_combo.addItem(label, minutes)
        self.rotation_mode_combo = self._combo(["random", "category", "color", "favorites"])
        self.rotation_category_combo = self._combo(CATEGORIES)
        self.rotation_color_combo = self._combo(COLORS)
        self.target_mode_combo = self._combo(["all", "specific", "different"])
        self.monitor_combo = QComboBox()
        self.position_combo = self._combo(["fill", "fit", "stretch", "center", "tile", "span"])
        self.startup_enabled = QCheckBox(self.translator("start_windows"))
        self.change_at_startup = QCheckBox(self.translator("change_at_startup"))
        self.run_on_battery = QCheckBox(self.translator("run_on_battery"))
        form.addRow(self.translator("rotation"), self.rotation_enabled)
        form.addRow(self.translator("interval"), self.interval_combo)
        form.addRow(self.translator("rotation_mode"), self.rotation_mode_combo)
        form.addRow(self.translator("category"), self.rotation_category_combo)
        form.addRow(self.translator("color"), self.rotation_color_combo)
        form.addRow(self.translator("target_monitor"), self.target_mode_combo)
        form.addRow(self.translator("display"), self.monitor_combo)
        form.addRow(self.translator("display_position"), self.position_combo)
        form.addRow(self.translator("start_windows"), self.startup_enabled)
        form.addRow(self.translator("change_at_startup"), self.change_at_startup)
        form.addRow(self.translator("run_on_battery"), self.run_on_battery)
        rotation_layout.addLayout(form)

        pause_row = QHBoxLayout()
        self.pause_hour_button = self._button(self.translator("pause_1h"))
        self.pause_today_button = self._button(self.translator("pause_today"))
        self.resume_button = self._button(self.translator("resume"), "Quiet")
        pause_row.addWidget(self.pause_hour_button)
        pause_row.addWidget(self.pause_today_button)
        pause_row.addWidget(self.resume_button)
        pause_row.addStretch()
        rotation_layout.addLayout(pause_row)
        layout.addWidget(rotation_card)
        layout.addStretch()

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.automation_save_button = self._button(self.translator("save_automation"), "Primary")
        save_row.addWidget(self.automation_save_button)
        layout.addLayout(save_row)

        self.rotation_enabled.toggled.connect(self._sync_automation_controls)
        self.rotation_mode_combo.currentIndexChanged.connect(self._sync_automation_controls)
        self.target_mode_combo.currentIndexChanged.connect(self._sync_automation_controls)
        self.pause_hour_button.clicked.connect(lambda: self.pause_rotation(hours=1))
        self.pause_today_button.clicked.connect(self.pause_until_tomorrow)
        self.resume_button.clicked.connect(self.resume_rotation)
        self.automation_save_button.clicked.connect(self.save_settings)
        return page

    def _build_general_tab(self) -> QWidget:
        page = QWidget(objectName="Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)
        preferences_card, preferences_layout = self._card(self.translator("settings"))
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(28)
        form.setVerticalSpacing(11)
        self.theme_combo = self._combo(["system", "dark", "light"])
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("বাংলা", "bn")
        self.notifications_enabled = QCheckBox(self.translator("notifications"))
        self.derive_accent = QCheckBox(self.translator("dynamic_accent"))
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(64, 10_240)
        self.cache_spin.setSuffix(" MB")
        self.download_spin = QSpinBox()
        self.download_spin.setRange(5, 500)
        self.download_spin.setSuffix(" MB")
        self.history_spin = QSpinBox()
        self.history_spin.setRange(20, 10_000)
        self.update_checks = QCheckBox(self.translator("automatic_updates"))
        self.source_mode_combo = self._combo(["hybrid", "api", "index"])
        form.addRow(self.translator("theme"), self.theme_combo)
        form.addRow(self.translator("language"), self.language_combo)
        form.addRow(self.translator("notifications"), self.notifications_enabled)
        form.addRow(self.translator("dynamic_accent"), self.derive_accent)
        form.addRow(self.translator("cache_size"), self.cache_spin)
        form.addRow(self.translator("download_limit"), self.download_spin)
        form.addRow(self.translator("history_limit"), self.history_spin)
        form.addRow(self.translator("check_updates"), self.update_checks)
        form.addRow(self.translator("source_mode"), self.source_mode_combo)
        preferences_layout.addLayout(form)
        layout.addWidget(preferences_card)

        tools_card, tools_layout = self._card(self.translator("support_diagnostics"))
        tools = QGridLayout()
        tools.setHorizontalSpacing(8)
        tools.setVerticalSpacing(8)
        self.connection_button = self._button(self.translator("connection_test"))
        self.open_folder_button = self._button(self.translator("open_folder"))
        self.open_logs_button = self._button(self.translator("open_logs"))
        self.diagnostics_button = self._button(self.translator("diagnostics"))
        self.update_button = self._button(self.translator("check_updates"))
        for index, button in enumerate(
            (
                self.connection_button,
                self.open_folder_button,
                self.open_logs_button,
                self.diagnostics_button,
                self.update_button,
            )
        ):
            tools.addWidget(button, index // 3, index % 3)
        tools.setColumnStretch(2, 1)
        tools_layout.addLayout(tools)
        layout.addWidget(tools_card)
        layout.addStretch()

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_button = self._button(self.translator("save"), "Primary", "Ctrl+S")
        save_row.addWidget(self.save_button)
        layout.addLayout(save_row)

        self.save_button.clicked.connect(self.save_settings)
        self.connection_button.clicked.connect(self.test_connection)
        self.open_folder_button.clicked.connect(self.open_wallpaper_folder)
        self.open_logs_button.clicked.connect(self.open_log_folder)
        self.diagnostics_button.clicked.connect(self.export_diagnostics)
        self.update_button.clicked.connect(self.check_updates)
        self.theme_combo.currentIndexChanged.connect(self._preview_theme)
        return page

    def set_page(self, index: int, *, animate: bool = True) -> None:
        if not 0 <= index < self.pages.count():
            return
        titles = ("home", "discover", "automation", "settings")
        subtitles = ("home_subtitle", "discover_subtitle", "automation_subtitle", "settings_subtitle")
        self.page_title.setText(self.translator(titles[index]))
        self.page_subtitle.setText(self.translator(subtitles[index]))
        self.nav_buttons[index].setChecked(True)
        if animate:
            self.pages.fade_to(index)
        else:
            self.pages.setCurrentIndex(index)
        if index == 1 and self.catalog.count() == 0:
            self._catalog_timer.start(80)

    def _load_settings(self) -> None:
        settings = self.services.settings_store.settings
        self._set_combo(self.category_combo, settings.category)
        self._set_combo(self.color_combo, settings.color)
        self._set_combo(self.orientation_combo, settings.orientation)
        self._set_combo(self.rotation_mode_combo, settings.rotation_mode)
        self._set_combo(self.rotation_category_combo, settings.category)
        self._set_combo(self.rotation_color_combo, settings.color)
        self._set_combo(self.target_mode_combo, settings.target_mode)
        self._set_combo(self.position_combo, settings.wallpaper_position)
        self._set_combo(self.theme_combo, settings.theme)
        self._set_combo(self.source_mode_combo, settings.source_mode)
        self._set_combo_data(self.language_combo, settings.language)
        self.rotation_enabled.setChecked(settings.rotation_enabled)
        self.startup_enabled.setChecked(settings.startup_enabled)
        self.change_at_startup.setChecked(settings.change_at_startup)
        self.run_on_battery.setChecked(settings.run_on_battery)
        self.notifications_enabled.setChecked(settings.notifications_enabled)
        self.derive_accent.setChecked(settings.derive_accent_from_wallpaper)
        self.cache_spin.setValue(settings.max_cache_mb)
        self.download_spin.setValue(settings.max_download_mb)
        self.history_spin.setValue(settings.max_history_items)
        self.update_checks.setChecked(settings.check_updates)
        self._set_combo_data(self.interval_combo, settings.interval_minutes)
        self.monitor_combo.clear()
        self.monitor_combo.addItem("All displays", "")
        for monitor in self.services.wallpaper.platform.monitors():
            label = f"{monitor.label}  {monitor.width}×{monitor.height}" if monitor.width else monitor.label
            self.monitor_combo.addItem(label, monitor.id)
        self._set_combo_data(self.monitor_combo, settings.monitor_id)
        self._sync_automation_controls()

    def save_settings(self) -> None:
        current = self.services.settings_store.settings
        updated = replace(current)
        updated.language = str(self.language_combo.currentData())
        updated.theme = str(self.theme_combo.currentData())
        updated.category = str(self.rotation_category_combo.currentData())
        updated.color = str(self.rotation_color_combo.currentData())
        updated.orientation = str(self.orientation_combo.currentData())
        updated.rotation_mode = str(self.rotation_mode_combo.currentData())
        updated.interval_minutes = int(self.interval_combo.currentData())
        updated.rotation_enabled = self.rotation_enabled.isChecked()
        updated.startup_enabled = self.startup_enabled.isChecked()
        updated.change_at_startup = self.change_at_startup.isChecked()
        updated.run_on_battery = self.run_on_battery.isChecked()
        updated.notifications_enabled = self.notifications_enabled.isChecked()
        updated.derive_accent_from_wallpaper = self.derive_accent.isChecked()
        updated.target_mode = str(self.target_mode_combo.currentData())
        updated.monitor_id = str(self.monitor_combo.currentData() or "")
        updated.wallpaper_position = str(self.position_combo.currentData())
        updated.max_cache_mb = self.cache_spin.value()
        updated.max_download_mb = self.download_spin.value()
        updated.max_history_items = self.history_spin.value()
        updated.check_updates = self.update_checks.isChecked()
        updated.source_mode = str(self.source_mode_combo.currentData())
        saved = self.services.settings_store.save(updated)
        self.services.downloader.max_bytes = saved.max_download_mb * 1024 * 1024
        self.translator.set_language(saved.language)
        self._apply_style()
        self._update_next_change()
        self.settings_saved.emit(saved)
        self._set_save_busy(True)
        worker = FunctionWorker(self._apply_system_integrations, saved)
        worker.signals.finished.connect(self._settings_integrations_finished)
        worker.signals.failed.connect(self._settings_integrations_failed)
        self._start_worker(worker)

    def _apply_system_integrations(self, settings: AppSettings) -> list[str]:
        errors: list[str] = []
        try:
            if settings.rotation_enabled:
                self.services.scheduler.enable(
                    settings.interval_minutes,
                    run_on_battery=settings.run_on_battery,
                )
            else:
                self.services.scheduler.disable()
        except SchedulerError as exc:
            errors.append(str(exc))
        try:
            if settings.startup_enabled:
                self.services.startup.enable()
            else:
                self.services.startup.disable()
        except StartupError as exc:
            errors.append(str(exc))
        return errors

    def _settings_integrations_finished(self, errors: list[str]) -> None:
        self._set_save_busy(False)
        if errors:
            QMessageBox.warning(self, self.translator("app_name"), "\n".join(errors))
        else:
            self.status.showMessage(self.translator("saved"), 5000)

    def _settings_integrations_failed(self, message: str) -> None:
        self._set_save_busy(False)
        self.status.showMessage(message, 8000)

    def _set_save_busy(self, busy: bool) -> None:
        self.save_button.setEnabled(not busy)
        self.automation_save_button.setEnabled(not busy)
        self._set_progress("settings", busy, self.translator("saved") if not busy else "")

    def change_now(self, wallpaper: Wallpaper | None = None) -> None:
        self._set_wallpaper_busy(True, self.translator("loading"))
        worker = FunctionWorker(self.services.wallpaper.change_now, wallpaper=wallpaper, with_progress=True)
        worker.signals.progress.connect(self.status.showMessage)
        worker.signals.finished.connect(self._change_finished)
        worker.signals.failed.connect(self._worker_failed)
        self._start_worker(worker)

    def undo(self) -> None:
        self._set_wallpaper_busy(True, self.translator("restoring"))
        worker = FunctionWorker(self.services.wallpaper.undo)
        worker.signals.finished.connect(self._change_finished)
        worker.signals.failed.connect(self._worker_failed)
        self._start_worker(worker)

    def _change_finished(self, result: ChangeResult) -> None:
        self._set_wallpaper_busy(False, result.message)
        self.refresh_home()
        self.wallpaper_result.emit(result)

    def _worker_failed(self, message: str) -> None:
        self._set_wallpaper_busy(False, message)
        self.wallpaper_result.emit(ChangeResult(False, message, error_code="worker_failed"))

    def toggle_favorite(self) -> None:
        value = self.services.wallpaper.toggle_current_favorite()
        if value is None:
            self.status.showMessage(self.translator("no_applied"), 5000)
            return
        self.favorite_button.setText(self.translator("unfavorite") if value else self.translator("favorite"))
        self.status.showMessage(
            self.translator("added_favorite") if value else self.translator("removed_favorite"),
            5000,
        )

    def block_current(self) -> None:
        if self.services.wallpaper.block_current():
            self.status.showMessage(self.translator("blocked"), 5000)
            self.refresh_home()

    def favorite_selected(self) -> None:
        wallpaper = self._selected_wallpaper()
        if wallpaper is None:
            self.status.showMessage(self.translator("select_wallpaper"), 4000)
            return
        favorite = self.services.history.toggle_favorite(wallpaper)
        self.favorite_selected_button.setText(
            self.translator("unfavorite") if favorite else self.translator("favorite")
        )
        self.status.showMessage(
            self.translator("added_favorite") if favorite else self.translator("removed_favorite"),
            5000,
        )

    def apply_selected(self) -> None:
        wallpaper = self._selected_wallpaper()
        if wallpaper is None:
            self.status.showMessage(self.translator("select_wallpaper"), 4000)
            return
        self.change_now(wallpaper)

    def load_catalog(self, force: bool = False) -> None:
        self._catalog_timer.stop()
        self._catalog_generation += 1
        generation = self._catalog_generation
        self.catalog.clear()
        placeholder = QListWidgetItem(self.translator("loading"))
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.catalog.addItem(placeholder)
        self.catalog_refresh.setEnabled(False)
        self._catalog_selection_changed()
        self._set_progress("catalog", True, self.translator("loading"))
        worker = FunctionWorker(
            self.services.wallpaper.catalog,
            query=self.search_input.text().strip(),
            category=str(self.category_combo.currentData()),
            color=str(self.color_combo.currentData()),
            orientation=str(self.orientation_combo.currentData()),
            force_refresh=force,
        )
        worker.signals.finished.connect(lambda items: self._catalog_loaded(generation, items))
        worker.signals.failed.connect(lambda message: self._catalog_failed(generation, message))
        self._start_worker(worker)

    def _catalog_loaded(self, generation: int, wallpapers: list[Wallpaper]) -> None:
        if generation != self._catalog_generation:
            return
        self.catalog.clear()
        self.catalog_refresh.setEnabled(True)
        self._set_progress("catalog", False)
        if not wallpapers:
            item = QListWidgetItem(self.translator("no_matches"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.catalog.addItem(item)
            self.status.showMessage(self.translator("no_matches"), 5000)
            return
        for wallpaper in wallpapers:
            label = f"{wallpaper.title}\n{wallpaper.category.title()}  {wallpaper.resolution}".strip()
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, wallpaper)
            item.setToolTip(
                f"{wallpaper.title}\n{wallpaper.width}×{wallpaper.height}\n{', '.join(wallpaper.colors)}"
            )
            self.catalog.addItem(item)
            thumb_worker = FunctionWorker(self.services.downloader.thumbnail, wallpaper)
            thumb_worker.signals.finished.connect(
                lambda path, expected=item, current=generation: self._thumbnail_loaded(current, expected, path)
            )
            self._start_worker(thumb_worker)
        self.status.showMessage(self.translator("loaded_count", count=len(wallpapers)), 5000)

    def _catalog_failed(self, generation: int, message: str) -> None:
        if generation != self._catalog_generation:
            return
        self.catalog.clear()
        self.catalog_refresh.setEnabled(True)
        self._set_progress("catalog", False)
        item = QListWidgetItem(f"{self.translator('gallery_failed')}\n{message}")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.catalog.addItem(item)
        self.status.showMessage(message, 8000)

    def _thumbnail_loaded(self, generation: int, item: QListWidgetItem, path: Path) -> None:
        if generation == self._catalog_generation and item.listWidget() is self.catalog:
            item.setIcon(QIcon(str(path)))

    def _schedule_catalog_load(self, *_args: object) -> None:
        if self.pages.currentIndex() == 1:
            self._catalog_timer.start()

    def _load_catalog_immediately(self) -> None:
        self._catalog_timer.stop()
        self.load_catalog()

    def _catalog_selection_changed(self, *_args: object) -> None:
        wallpaper = self._selected_wallpaper()
        enabled = wallpaper is not None and "wallpaper" not in self._busy_reasons
        self.apply_selected_button.setEnabled(enabled)
        self.favorite_selected_button.setEnabled(enabled)
        if wallpaper is None:
            self.selection_hint.setText(self.translator("select_wallpaper"))
            self.favorite_selected_button.setText(self.translator("favorite"))
            return
        self.selection_hint.setText(f"{wallpaper.title}  •  {wallpaper.resolution or wallpaper.category.title()}")
        is_favorite = self.services.history.is_favorite(wallpaper.id)
        self.favorite_selected_button.setText(
            self.translator("unfavorite") if is_favorite else self.translator("favorite")
        )

    def refresh_home(self) -> None:
        latest = self.services.history.last_successful()
        path: Path | None = None
        if latest and latest.local_path:
            path = Path(latest.local_path)
            self.current_title.setText(latest.title or "Wallwidgy wallpaper")
            self.current_meta.setText(f"{latest.category.title()}  •  {latest.applied_at[:16].replace('T', ' ')}")
            favorite = self.services.history.is_favorite(latest.wallpaper_id)
            self.favorite_button.setText(
                self.translator("unfavorite") if favorite else self.translator("favorite")
            )
        else:
            settings_path = self.services.settings_store.settings.last_wallpaper_path
            path = Path(settings_path) if settings_path else None
            self.current_title.setText(self.translator("no_wallpaper"))
            self.current_meta.setText(self.translator("choose_start"))
            self.favorite_button.setText(self.translator("favorite"))
        has_history = latest is not None
        self.favorite_button.setEnabled(has_history)
        self.block_button.setEnabled(has_history)
        self.undo_button.setEnabled(bool(latest and latest.previous_path and Path(latest.previous_path).is_file()))
        self._load_preview(path)
        self._update_next_change()

    def _load_preview(self, path: Path | None) -> None:
        if path == self._preview_path and not self._preview_pixmap.isNull():
            self._render_preview()
            return
        self._preview_path = path
        self._preview_pixmap = QPixmap(str(path)) if path and path.is_file() else QPixmap()
        if self._preview_pixmap.isNull():
            self.preview.clear()
            self.preview.setText("WALLWIDGY")
        else:
            self._render_preview()

    def _render_preview(self) -> None:
        if self._preview_pixmap.isNull() or not hasattr(self, "preview"):
            return
        target = self.preview.size() - QSize(4, 4)
        if target.width() <= 0 or target.height() <= 0:
            return
        self.preview.setPixmap(
            self._preview_pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_next_change(self) -> None:
        settings = self.services.settings_store.settings
        if not settings.rotation_enabled:
            self.next_change_label.setText(self.translator("automatic_off"))
            self.rotation_status.setText(self.translator("enable_automation"))
            self.nav_status.setText(self.translator("rotation_off"))
            return
        self.nav_status.setText(self.translator("rotation_on"))
        if settings.is_paused:
            self.next_change_label.setText(self.translator("status_paused"))
            self.rotation_status.setText(f"Until {settings.pause_until}")
            return
        if not settings.last_changed_at:
            self.next_change_label.setText(self.translator("next_scheduled"))
            self.rotation_status.setText(self.translator("every_minutes", minutes=settings.interval_minutes))
            return
        try:
            last = datetime.fromisoformat(settings.last_changed_at)
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            remaining = last + timedelta(minutes=settings.interval_minutes) - datetime.now(UTC)
            minutes = max(0, int(remaining.total_seconds() // 60))
            if self.translator.language == "bn":
                remaining_text = f"{minutes // 60} ঘণ্টা {minutes % 60} মিনিট" if minutes >= 60 else f"{minutes} মিনিট"
            else:
                remaining_text = f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes} minutes"
            self.next_change_label.setText(remaining_text)
            self.rotation_status.setText(self.translator("every_minutes", minutes=settings.interval_minutes))
        except ValueError:
            self.next_change_label.setText(self.translator("next_scheduled"))

    def _sync_automation_controls(self, *_args: object) -> None:
        mode = str(self.rotation_mode_combo.currentData())
        target = str(self.target_mode_combo.currentData())
        self.rotation_category_combo.setEnabled(mode == "category")
        self.rotation_color_combo.setEnabled(mode == "color")
        self.monitor_combo.setEnabled(target == "specific")

    def pause_rotation(self, *, hours: int) -> None:
        until = datetime.now(UTC) + timedelta(hours=hours)
        self.services.settings_store.save(pause_until=until.isoformat())
        self._update_next_change()
        self.status.showMessage(self.translator("status_paused"), 5000)

    def pause_until_tomorrow(self) -> None:
        now = datetime.now(UTC)
        tomorrow = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        self.services.settings_store.save(pause_until=tomorrow.isoformat())
        self._update_next_change()
        self.status.showMessage(self.translator("status_paused"), 5000)

    def resume_rotation(self) -> None:
        self.services.settings_store.save(pause_until=None)
        self._update_next_change()
        self.status.showMessage(self.translator("resume"), 5000)

    def test_connection(self) -> None:
        self.connection_button.setEnabled(False)
        self._set_progress("connection", True, self.translator("testing"))
        worker = FunctionWorker(self.services.wallpaper.test_connection)
        worker.signals.finished.connect(self._connection_finished)
        worker.signals.failed.connect(lambda _message: self._connection_finished(False))
        self._start_worker(worker)

    def _connection_finished(self, result: bool) -> None:
        self.connection_button.setEnabled(True)
        self._set_progress("connection", False)
        self.status.showMessage(
            self.translator("connection_ok") if result else self.translator("connection_failed"),
            7000,
        )

    def open_wallpaper_folder(self) -> None:
        open_path(self.services.paths.images)

    def open_log_folder(self) -> None:
        open_path(self.services.paths.logs)

    def export_diagnostics(self) -> None:
        try:
            destination = self.services.export_diagnostics()
            self.status.showMessage(f"Diagnostics saved to {destination}", 8000)
            open_path(destination.parent)
        except OSError as exc:
            QMessageBox.warning(self, self.translator("app_name"), str(exc))

    def check_updates(self) -> None:
        self.update_button.setEnabled(False)
        self._set_progress("updates", True, self.translator("checking_updates"))
        worker = FunctionWorker(self.services.updates.check)
        worker.signals.finished.connect(self._update_checked)
        worker.signals.failed.connect(self._update_failed)
        self._start_worker(worker)

    def _update_checked(self, update) -> None:
        self.update_button.setEnabled(True)
        self._set_progress("updates", False)
        if update.available:
            choice = QMessageBox.question(
                self,
                self.translator("update_available"),
                self.translator("version_available", version=update.latest_version),
            )
            if choice == QMessageBox.StandardButton.Yes and update.release_url:
                webbrowser.open(update.release_url)
        else:
            self.status.showMessage(self.translator("up_to_date"), 7000)

    def _update_failed(self, message: str) -> None:
        self.update_button.setEnabled(True)
        self._set_progress("updates", False)
        self.status.showMessage(message, 8000)

    def _selected_wallpaper(self) -> Wallpaper | None:
        item = self.catalog.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, Wallpaper) else None

    def _set_wallpaper_busy(self, busy: bool, message: str) -> None:
        self.change_button.setEnabled(not busy)
        self._set_progress("wallpaper", busy, message)
        self._catalog_selection_changed()

    def _set_progress(self, reason: str, busy: bool, message: str = "") -> None:
        if busy:
            self._busy_reasons.add(reason)
        else:
            self._busy_reasons.discard(reason)
        self.busy_bar.setVisible(bool(self._busy_reasons))
        if message:
            self.status.showMessage(message)

    def _start_worker(self, worker: FunctionWorker) -> None:
        self._active_workers.add(worker)
        worker.signals.finished.connect(lambda _result, current=worker: self._active_workers.discard(current))
        worker.signals.failed.connect(lambda _message, current=worker: self._active_workers.discard(current))
        self.thread_pool.start(worker)

    def _apply_style(self) -> None:
        settings = self.services.settings_store.settings
        theme = str(self.theme_combo.currentData()) if hasattr(self, "theme_combo") else settings.theme
        if theme == "system":
            scheme = QGuiApplication.styleHints().colorScheme()
            theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        self.setStyleSheet(stylesheet(theme, settings.accent_color))

    def _preview_theme(self, *_args: object) -> None:
        self._apply_style()

    @staticmethod
    def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(objectName="Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)
        layout.addWidget(QLabel(title, objectName="SectionTitle"))
        return frame, layout

    @staticmethod
    def _button(text: str, object_name: str = "", shortcut: str = "") -> QPushButton:
        button = QPushButton(text)
        if object_name:
            button.setObjectName(object_name)
        if shortcut:
            button.setShortcut(shortcut)
        button.setAccessibleName(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _combo(self, values: list[str]) -> QComboBox:
        combo = QComboBox()
        for value in values:
            translated = self.translator(value)
            combo.addItem(translated.title() if translated == value else translated, value)
        return combo

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index < 0:
            index = combo.findText(value, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._preview_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_home()
        if self._first_show:
            self._first_show = False
            self.setWindowOpacity(0.0)
            animation = QPropertyAnimation(self, b"windowOpacity", self)
            animation.setDuration(180)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._window_animation = animation
            animation.start()
        else:
            self.setWindowOpacity(1.0)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
