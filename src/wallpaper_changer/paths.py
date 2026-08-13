from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "AutoWallpaperChanger"


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    cache: Path
    images: Path
    thumbnails: Path
    logs: Path
    temp: Path
    config: Path
    database: Path
    index_cache: Path
    index_metadata: Path
    diagnostics: Path
    exports: Path

    def ensure(self) -> AppPaths:
        for directory in (
            self.root,
            self.cache,
            self.images,
            self.thumbnails,
            self.logs,
            self.temp,
            self.diagnostics,
            self.exports,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self


def get_app_paths(root: Path | None = None) -> AppPaths:
    if root is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        root = base / APP_NAME

    pictures = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Pictures" / "Wallwidgy"
    return AppPaths(
        root=root,
        cache=root / "cache",
        images=root / "cache" / "images",
        thumbnails=root / "cache" / "thumbnails",
        logs=root / "logs",
        temp=root / "temp",
        config=root / "settings.json",
        database=root / "wallpapers.sqlite3",
        index_cache=root / "cache" / "index.json",
        index_metadata=root / "cache" / "index.meta.json",
        diagnostics=root / "diagnostics",
        exports=pictures,
    )
