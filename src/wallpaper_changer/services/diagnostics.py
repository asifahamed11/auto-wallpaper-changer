from __future__ import annotations

import json
import platform
import sys
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from wallpaper_changer import __version__
from wallpaper_changer.config import SettingsStore
from wallpaper_changer.paths import AppPaths


def export_diagnostics(paths: AppPaths, settings_store: SettingsStore) -> Path:
    paths.diagnostics.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destination = paths.diagnostics / f"wallwidgy-diagnostics-{timestamp}.zip"
    system_info = {
        "app_version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    settings = asdict(settings_store.settings)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("system.json", json.dumps(system_info, indent=2))
        archive.writestr("settings.json", json.dumps(settings, indent=2, ensure_ascii=False))
        for log_file in sorted(paths.logs.glob("wallpaper_changer.log*")):
            if log_file.is_file():
                archive.write(log_file, f"logs/{log_file.name}")
    return destination
