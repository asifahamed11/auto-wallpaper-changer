from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from wallpaper_changer.api.errors import DownloadError, ProviderError
from wallpaper_changer.api.wallwidgy_api import WallwidgyApiProvider
from wallpaper_changer.api.wallwidgy_index import WallwidgyIndexProvider
from wallpaper_changer.config import AppSettings, SettingsStore
from wallpaper_changer.models import ChangeResult, Wallpaper
from wallpaper_changer.platform.windows_wallpaper import WallpaperPlatformError, WindowsWallpaperService
from wallpaper_changer.services.downloader import ImageDownloader
from wallpaper_changer.services.history import HistoryRepository
from wallpaper_changer.services.instance_lock import NamedMutex
from wallpaper_changer.services.power import is_running_on_battery

LOGGER = logging.getLogger("wallpaper_changer.service")
ProgressCallback = Callable[[str], None]


class WallpaperService:
    def __init__(
        self,
        settings_store: SettingsStore,
        api_provider: WallwidgyApiProvider,
        index_provider: WallwidgyIndexProvider,
        downloader: ImageDownloader,
        history: HistoryRepository,
        platform_service: WindowsWallpaperService,
    ):
        self.settings_store = settings_store
        self.api_provider = api_provider
        self.index_provider = index_provider
        self.downloader = downloader
        self.history = history
        self.platform = platform_service
        self._lock = threading.Lock()

    def change_now(
        self,
        *,
        scheduled: bool = False,
        wallpaper: Wallpaper | None = None,
        progress: ProgressCallback | None = None,
    ) -> ChangeResult:
        settings = self.settings_store.settings
        if scheduled and (not settings.rotation_enabled or settings.is_paused):
            return ChangeResult(False, "Automatic rotation is disabled or paused", error_code="paused")
        if scheduled and not settings.run_on_battery and is_running_on_battery():
            return ChangeResult(
                False, "Scheduled change skipped while running on battery", error_code="battery"
            )
        if not self._lock.acquire(blocking=False):
            return ChangeResult(False, "A wallpaper change is already running", error_code="busy")

        mutex = NamedMutex("AutoWallpaperChanger.Change")
        if not mutex.acquire():
            self._lock.release()
            return ChangeResult(False, "A wallpaper change is already running", error_code="busy")
        try:
            if settings.target_mode == "different" and wallpaper is None:
                return self._change_different(settings, progress)
            selected = wallpaper or self._select_wallpaper(settings, progress)
            if selected is None:
                return self._offline_fallback(settings, progress)
            return self._apply(selected, settings, progress)
        except (ProviderError, DownloadError, WallpaperPlatformError, OSError, RuntimeError) as exc:
            LOGGER.exception("Wallpaper change failed")
            return ChangeResult(False, str(exc), wallpaper=wallpaper, error_code="change_failed")
        finally:
            mutex.release()
            self._lock.release()

    def _change_different(
        self,
        settings: AppSettings,
        progress: ProgressCallback | None,
    ) -> ChangeResult:
        monitors = [
            monitor for monitor in self.platform.monitors() if monitor.id and monitor.width and monitor.height
        ]
        if len(monitors) < 2:
            selected = self._select_wallpaper(settings, progress)
            if selected is None:
                return self._offline_fallback(settings, progress)
            return self._apply(selected, replace(settings, target_mode="all", monitor_id=""), progress)

        candidates = self.index_provider.search(
            category=settings.category if settings.rotation_mode in {"category", "random"} else "all",
            color=settings.color if settings.rotation_mode in {"color", "random"} else "all",
            orientation="desktop",
            limit=max(settings.catalog_limit, len(monitors) * 10),
        )
        blocked = self.history.blocked_ids()
        used = self.history.used_ids(settings.max_history_items)
        pool = [item for item in candidates if item.id not in blocked and item.id not in used]
        if len(pool) < len(monitors):
            pool = [item for item in candidates if item.id not in blocked]
        if not pool:
            return self._offline_fallback(settings, progress)
        random.shuffle(pool)
        results: list[ChangeResult] = []
        for monitor in monitors:
            monitor_settings = replace(settings, target_mode="specific", monitor_id=monitor.id)
            wallpaper = self._best_fit(pool, monitor_settings)
            pool = [item for item in pool if item.id != wallpaper.id] or pool
            self._progress(progress, f"Updating {monitor.label}")
            results.append(self._apply(wallpaper, monitor_settings, progress))
        last = results[-1]
        return ChangeResult(
            True,
            f"Updated {len(results)} displays",
            wallpaper=last.wallpaper,
            path=last.path,
            previous_path=last.previous_path,
        )

    def _select_wallpaper(
        self,
        settings: AppSettings,
        progress: ProgressCallback | None,
    ) -> Wallpaper | None:
        self._progress(progress, "Fetching wallpaper choices")
        if settings.rotation_mode == "favorites":
            candidates = self.history.favorites()
            return random.choice(candidates) if candidates else None

        candidates: list[Wallpaper] = []
        api_error: Exception | None = None
        if settings.source_mode in {"api", "hybrid"}:
            try:
                candidates = self.api_provider.fetch(
                    count=10,
                    orientation=settings.orientation,
                    category=settings.category if settings.rotation_mode in {"category", "random"} else "all",
                    color=settings.color if settings.rotation_mode in {"color", "random"} else "all",
                )
            except ProviderError as exc:
                api_error = exc
                LOGGER.warning("REST provider failed: %s", exc)

        if not candidates and settings.source_mode in {"index", "hybrid"}:
            candidates = self.index_provider.search(
                category=settings.category if settings.rotation_mode in {"category", "random"} else "all",
                color=settings.color if settings.rotation_mode in {"color", "random"} else "all",
                orientation=settings.orientation,
                limit=max(settings.catalog_limit, 100),
            )
        if not candidates and api_error:
            raise ProviderError(str(api_error))
        if not candidates:
            return None

        blocked = self.history.blocked_ids()
        used = self.history.used_ids(settings.max_history_items)
        fresh = [item for item in candidates if item.id not in blocked and item.id not in used]
        pool = fresh or [item for item in candidates if item.id not in blocked]
        if not pool:
            return None
        return self._best_fit(pool, settings)

    def _best_fit(self, candidates: list[Wallpaper], settings: AppSettings) -> Wallpaper:
        monitors = self.platform.monitors()
        target = None
        if settings.monitor_id:
            target = next((monitor for monitor in monitors if monitor.id == settings.monitor_id), None)
        target = target or next((monitor for monitor in monitors if monitor.width and monitor.height), None)
        if target is None or not target.width or not target.height:
            return random.choice(candidates)
        target_ratio = target.width / target.height
        scored = [
            (abs((item.width / item.height) - target_ratio), random.random(), item)
            for item in candidates
            if item.width and item.height
        ]
        if not scored:
            return random.choice(candidates)
        scored.sort(key=lambda row: (row[0], row[1]))
        return random.choice([row[2] for row in scored[: min(8, len(scored))]])

    def _apply(
        self,
        wallpaper: Wallpaper,
        settings: AppSettings,
        progress: ProgressCallback | None,
    ) -> ChangeResult:
        self._progress(progress, "Downloading and validating image")
        downloaded = self.downloader.download(wallpaper)
        monitor_id = settings.monitor_id if settings.target_mode == "specific" else None
        previous = self.platform.get_current(monitor_id)
        self._progress(progress, "Applying wallpaper")
        try:
            self.platform.set_wallpaper(
                downloaded.path,
                monitor_id=monitor_id,
                position=settings.wallpaper_position,
            )
        except WallpaperPlatformError as exc:
            self.history.record(
                wallpaper,
                local_path=downloaded.path,
                previous_path=previous,
                success=False,
                monitor_id=monitor_id or "",
                error=str(exc),
            )
            raise

        self.history.record(
            wallpaper,
            local_path=downloaded.path,
            previous_path=previous,
            success=True,
            monitor_id=monitor_id or "",
        )
        changes: dict[str, object] = {
            "last_changed_at": datetime.now(UTC).isoformat(),
            "last_wallpaper_id": wallpaper.id,
            "last_wallpaper_path": str(downloaded.path),
        }
        if settings.derive_accent_from_wallpaper:
            changes["accent_color"] = self.downloader.dominant_color(downloaded.path)
        self.settings_store.save(**changes)
        self.history.trim(settings.max_history_items)
        self.downloader.cleanup(settings.max_cache_mb, self.history.protected_paths())
        self._progress(progress, "Wallpaper changed")
        return ChangeResult(
            True,
            "Wallpaper changed successfully",
            wallpaper=wallpaper,
            path=downloaded.path,
            previous_path=previous,
        )

    def _offline_fallback(
        self,
        settings: AppSettings,
        progress: ProgressCallback | None,
    ) -> ChangeResult:
        self._progress(progress, "Using an offline wallpaper")
        for item in self.history.recent(25, successful_only=True):
            path = Path(item.local_path)
            if not path.is_file():
                continue
            monitor_id = settings.monitor_id if settings.target_mode == "specific" else None
            previous = self.platform.get_current(monitor_id)
            self.platform.set_wallpaper(path, monitor_id=monitor_id, position=settings.wallpaper_position)
            return ChangeResult(
                True,
                "Offline wallpaper applied",
                Wallpaper(
                    id=item.wallpaper_id,
                    url=item.url,
                    title=item.title,
                    category=item.category,
                    source="offline",
                ),
                path,
                previous,
            )
        raise ProviderError("No online or cached wallpaper is available")

    def undo(self) -> ChangeResult:
        latest = self.history.last_successful()
        if not latest or not latest.previous_path:
            return ChangeResult(False, "No previous wallpaper is available", error_code="no_previous")
        previous = Path(latest.previous_path)
        if not previous.is_file():
            return ChangeResult(
                False, "The previous wallpaper file no longer exists", error_code="missing_previous"
            )
        settings = self.settings_store.settings
        monitor_id = settings.monitor_id if settings.target_mode == "specific" else None
        current = self.platform.get_current(monitor_id)
        self.platform.set_wallpaper(previous, monitor_id=monitor_id, position=settings.wallpaper_position)
        wallpaper = Wallpaper.from_url(previous.as_uri(), source="undo")
        self.history.record(wallpaper, local_path=previous, previous_path=current, success=True)
        self.settings_store.save(
            last_changed_at=datetime.now(UTC).isoformat(),
            last_wallpaper_id=wallpaper.id,
            last_wallpaper_path=str(previous),
        )
        return ChangeResult(
            True, "Previous wallpaper restored", wallpaper=wallpaper, path=previous, previous_path=current
        )

    def toggle_current_favorite(self) -> bool | None:
        latest = self.history.last_successful()
        if not latest:
            return None
        wallpaper = Wallpaper(
            id=latest.wallpaper_id,
            url=latest.url,
            title=latest.title,
            category=latest.category,
            source="history",
        )
        return self.history.toggle_favorite(wallpaper)

    def block_current(self) -> bool:
        latest = self.history.last_successful()
        if not latest:
            return False
        self.history.block(latest.wallpaper_id)
        return True

    def catalog(
        self,
        *,
        query: str = "",
        category: str = "all",
        color: str = "all",
        orientation: str = "desktop",
        force_refresh: bool = False,
    ) -> list[Wallpaper]:
        return self.index_provider.search(
            query=query,
            category=category,
            color=color,
            orientation=orientation,
            limit=self.settings_store.settings.catalog_limit,
            force_refresh=force_refresh,
        )

    def test_connection(self) -> bool:
        return self.api_provider.test_connection()

    @staticmethod
    def _progress(callback: ProgressCallback | None, message: str) -> None:
        if callback:
            callback(message)
