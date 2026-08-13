from __future__ import annotations

from dataclasses import dataclass

from wallpaper_changer.api import WallwidgyApiProvider, WallwidgyIndexProvider
from wallpaper_changer.config import SettingsStore
from wallpaper_changer.paths import AppPaths, get_app_paths
from wallpaper_changer.platform.windows_wallpaper import WindowsWallpaperService
from wallpaper_changer.services.diagnostics import export_diagnostics
from wallpaper_changer.services.downloader import ImageDownloader
from wallpaper_changer.services.history import HistoryRepository
from wallpaper_changer.services.scheduler import WindowsTaskScheduler
from wallpaper_changer.services.startup import WindowsStartupManager
from wallpaper_changer.services.updates import UpdateService
from wallpaper_changer.services.wallpaper_service import WallpaperService


@dataclass(slots=True)
class AppServices:
    paths: AppPaths
    settings_store: SettingsStore
    history: HistoryRepository
    downloader: ImageDownloader
    wallpaper: WallpaperService
    scheduler: WindowsTaskScheduler
    startup: WindowsStartupManager
    updates: UpdateService

    def export_diagnostics(self):
        return export_diagnostics(self.paths, self.settings_store)


def build_services(paths: AppPaths | None = None) -> AppServices:
    paths = (paths or get_app_paths()).ensure()
    settings_store = SettingsStore(paths.config)
    settings = settings_store.settings
    history = HistoryRepository(paths.database)
    downloader = ImageDownloader(
        paths.images,
        paths.thumbnails,
        max_download_mb=settings.max_download_mb,
    )
    api_provider = WallwidgyApiProvider(settings.api_url)
    index_provider = WallwidgyIndexProvider(
        settings.index_url,
        settings.index_base_url,
        paths.index_cache,
        paths.index_metadata,
    )
    platform_service = WindowsWallpaperService()
    wallpaper = WallpaperService(
        settings_store,
        api_provider,
        index_provider,
        downloader,
        history,
        platform_service,
    )
    return AppServices(
        paths=paths,
        settings_store=settings_store,
        history=history,
        downloader=downloader,
        wallpaper=wallpaper,
        scheduler=WindowsTaskScheduler(),
        startup=WindowsStartupManager(),
        updates=UpdateService(),
    )
