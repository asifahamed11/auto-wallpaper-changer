from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def stable_wallpaper_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class Wallpaper:
    id: str
    url: str
    thumbnail_url: str | None = None
    title: str = "Untitled"
    category: str = "all"
    colors: tuple[str, ...] = field(default_factory=tuple)
    width: int = 0
    height: int = 0
    resolution: str = ""
    orientation: str = "desktop"
    source: str = "wallwidgy-api"

    @classmethod
    def from_url(cls, url: str, *, source: str = "wallwidgy-api") -> Wallpaper:
        parsed = urlparse(url)
        stem = Path(parsed.path).stem or "wallpaper"
        title = stem.replace("-", " ").replace("_", " ").strip().title()
        canonical_asset = f"{(parsed.hostname or '').lower()}{parsed.path}"
        return cls(id=stable_wallpaper_id(canonical_asset), url=url, title=title, source=source)

    @classmethod
    def from_index(cls, item: dict[str, Any], base_url: str) -> Wallpaper:
        file_name = str(item.get("file_name") or "").strip()
        main_name = str(item.get("file_main_name") or item.get("file_name") or "").strip()
        cache_name = str(item.get("file_cache_name") or main_name).strip()
        if not main_name:
            raise ValueError("Index item does not contain a wallpaper filename")

        clean_base = base_url.rstrip("/") + "/"
        metadata = item.get("data") if isinstance(item.get("data"), dict) else {}
        title = str(metadata.get("title") or file_name or Path(main_name).stem)
        category = str(item.get("category") or metadata.get("category") or "all").lstrip("#")
        raw_colors = metadata.get("primary_colors") or []
        colors = tuple(str(color).lower() for color in raw_colors if color)
        orientation = str(item.get("orientation") or "desktop").lower()
        stable_id = file_name or stable_wallpaper_id(clean_base + "main/" + main_name)
        return cls(
            id=stable_id,
            url=clean_base + "main/" + main_name,
            thumbnail_url=clean_base + "cache/" + cache_name,
            title=title,
            category=category,
            colors=colors,
            width=int(item.get("width") or 0),
            height=int(item.get("height") or 0),
            resolution=str(item.get("resolution") or ""),
            orientation=orientation,
            source="wallwidgy-index",
        )


@dataclass(frozen=True, slots=True)
class DownloadedWallpaper:
    wallpaper: Wallpaper
    path: Path
    content_type: str
    size_bytes: int
    sha256: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ChangeResult:
    success: bool
    message: str
    wallpaper: Wallpaper | None = None
    path: Path | None = None
    previous_path: Path | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class Monitor:
    id: str
    label: str
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)
