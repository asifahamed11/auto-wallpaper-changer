from __future__ import annotations

import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "wallpaper_changer" / "assets" / name
    return Path(__file__).with_name("assets") / name
