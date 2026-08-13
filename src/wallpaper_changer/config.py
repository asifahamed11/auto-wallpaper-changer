from __future__ import annotations

import json
import os
import threading
from contextlib import suppress
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "https://wallwidgy.vercel.app/api/wallpapers"
DEFAULT_INDEX_URL = "https://raw.githubusercontent.com/not-ayan/storage/main/index.json"
DEFAULT_INDEX_BASE_URL = "https://raw.githubusercontent.com/not-ayan/storage/main/"


@dataclass(slots=True)
class AppSettings:
    schema_version: int = 1
    language: str = "en"
    theme: str = "system"
    accent_color: str = "#F7F06D"
    derive_accent_from_wallpaper: bool = True
    api_url: str = DEFAULT_API_URL
    index_url: str = DEFAULT_INDEX_URL
    index_base_url: str = DEFAULT_INDEX_BASE_URL
    source_mode: str = "hybrid"
    orientation: str = "desktop"
    category: str = "all"
    color: str = "all"
    rotation_mode: str = "random"
    interval_minutes: int = 60
    rotation_enabled: bool = False
    startup_enabled: bool = False
    change_at_startup: bool = False
    notifications_enabled: bool = True
    pause_until: str | None = None
    target_mode: str = "all"
    monitor_id: str = ""
    wallpaper_position: str = "fill"
    max_cache_mb: int = 512
    max_download_mb: int = 100
    max_history_items: int = 500
    catalog_limit: int = 48
    run_on_battery: bool = True
    last_changed_at: str | None = None
    last_wallpaper_id: str | None = None
    last_wallpaper_path: str | None = None
    check_updates: bool = True

    @property
    def is_paused(self) -> bool:
        if not self.pause_until:
            return False
        try:
            paused_until = datetime.fromisoformat(self.pause_until)
            if paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=UTC)
            return paused_until > datetime.now(UTC)
        except ValueError:
            return False


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._settings = self._load()

    @property
    def settings(self) -> AppSettings:
        with self._lock:
            return AppSettings(**asdict(self._settings))

    def _load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("settings root must be an object")
            allowed = {item.name for item in fields(AppSettings)}
            values = {key: value for key, value in payload.items() if key in allowed}
            return self._sanitize(AppSettings(**values))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            corrupt = self.path.with_suffix(".corrupt.json")
            with suppress(OSError):
                os.replace(self.path, corrupt)
            return AppSettings()

    def save(self, settings: AppSettings | None = None, **changes: Any) -> AppSettings:
        with self._lock:
            current = settings or self._settings
            values = asdict(current)
            values.update(changes)
            updated = self._sanitize(AppSettings(**values))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(asdict(updated), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
            self._settings = updated
            return self.settings

    @staticmethod
    def _sanitize(settings: AppSettings) -> AppSettings:
        settings.language = settings.language if settings.language in {"en", "bn"} else "en"
        settings.theme = settings.theme if settings.theme in {"system", "light", "dark"} else "system"
        settings.source_mode = (
            settings.source_mode if settings.source_mode in {"api", "index", "hybrid"} else "hybrid"
        )
        settings.orientation = (
            settings.orientation if settings.orientation in {"desktop", "mobile", "all"} else "desktop"
        )
        settings.rotation_mode = (
            settings.rotation_mode
            if settings.rotation_mode in {"random", "category", "color", "favorites"}
            else "random"
        )
        settings.target_mode = (
            settings.target_mode if settings.target_mode in {"all", "specific", "different"} else "all"
        )
        settings.wallpaper_position = (
            settings.wallpaper_position
            if settings.wallpaper_position in {"center", "tile", "stretch", "fit", "fill", "span"}
            else "fill"
        )
        settings.interval_minutes = min(max(int(settings.interval_minutes), 15), 43_200)
        settings.max_cache_mb = min(max(int(settings.max_cache_mb), 64), 10_240)
        settings.max_download_mb = min(max(int(settings.max_download_mb), 5), 500)
        settings.max_history_items = min(max(int(settings.max_history_items), 20), 10_000)
        settings.catalog_limit = min(max(int(settings.catalog_limit), 10), 250)
        if not settings.accent_color.startswith("#") or len(settings.accent_color) != 7:
            settings.accent_color = "#F7F06D"
        settings.category = settings.category.strip().lstrip("#") or "all"
        settings.color = settings.color.strip().lower() or "all"
        return settings
