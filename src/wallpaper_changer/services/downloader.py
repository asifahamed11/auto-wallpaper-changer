from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from wallpaper_changer.api.errors import DownloadError
from wallpaper_changer.models import DownloadedWallpaper, Wallpaper
from wallpaper_changer.services.http import DEFAULT_TIMEOUT, build_http_session

LOGGER = logging.getLogger("wallpaper_changer.downloader")
ALLOWED_HOSTS = {
    "raw.githubusercontent.com",
    "wallwidgy.app",
    "www.wallwidgy.app",
    "wallwidgy.vercel.app",
}
ALLOWED_SUFFIXES = (".public.blob.vercel-storage.com",)
MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


class ImageDownloader:
    def __init__(
        self,
        images_dir: Path,
        thumbnails_dir: Path,
        *,
        max_download_mb: int = 100,
        session: requests.Session | None = None,
        extra_allowed_hosts: set[str] | None = None,
    ):
        self.images_dir = images_dir
        self.thumbnails_dir = thumbnails_dir
        self.max_bytes = max_download_mb * 1024 * 1024
        self.session = session or build_http_session()
        self.allowed_hosts = ALLOWED_HOSTS | (extra_allowed_hosts or set())

    def download(self, wallpaper: Wallpaper) -> DownloadedWallpaper:
        self._validate_url(wallpaper.url)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        existing = list(self.images_dir.glob(f"{self._safe_id(wallpaper.id)}.*"))
        for candidate in existing:
            if candidate.suffix != ".part" and candidate.is_file():
                try:
                    width, height = self._verify_image(candidate)
                    return DownloadedWallpaper(
                        wallpaper=wallpaper,
                        path=candidate,
                        content_type=mimetypes.guess_type(candidate.name)[0] or "image/unknown",
                        size_bytes=candidate.stat().st_size,
                        sha256=self._hash_file(candidate),
                        width=width,
                        height=height,
                    )
                except DownloadError:
                    candidate.unlink(missing_ok=True)

        try:
            response = self.session.get(wallpaper.url, stream=True, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise DownloadError(f"Image download failed: {exc}") from exc
        if response.status_code != 200:
            raise DownloadError(f"Image server returned HTTP {response.status_code}")

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise DownloadError(f"Expected an image but received {content_type or 'unknown content'}")
        if content_type not in MIME_EXTENSIONS:
            raise DownloadError(f"Unsupported image type: {content_type}")
        expected_size = int(response.headers.get("Content-Length") or 0)
        if expected_size > self.max_bytes:
            raise DownloadError("Wallpaper exceeds the configured download limit")

        extension = MIME_EXTENSIONS[content_type]
        destination = self.images_dir / f"{self._safe_id(wallpaper.id)}{extension}"
        temporary = destination.with_suffix(destination.suffix + ".part")
        digest = hashlib.sha256()
        received = 0
        try:
            with temporary.open("wb") as output:
                for chunk in response.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > self.max_bytes:
                        raise DownloadError("Wallpaper exceeds the configured download limit")
                    digest.update(chunk)
                    output.write(chunk)
            width, height = self._verify_image(temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

        return DownloadedWallpaper(
            wallpaper=wallpaper,
            path=destination,
            content_type=content_type,
            size_bytes=received,
            sha256=digest.hexdigest(),
            width=width,
            height=height,
        )

    def thumbnail(self, wallpaper: Wallpaper, *, size: tuple[int, int] = (420, 260)) -> Path:
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        destination = self.thumbnails_dir / f"{self._safe_id(wallpaper.id)}.jpg"
        if destination.exists():
            return destination
        source_url = wallpaper.thumbnail_url or wallpaper.url
        preview = Wallpaper.from_url(source_url, source=wallpaper.source)
        preview = Wallpaper(
            id=f"thumb-{wallpaper.id}",
            url=preview.url,
            title=wallpaper.title,
            source=wallpaper.source,
        )
        temporary_downloader = ImageDownloader(
            self.thumbnails_dir / "source",
            self.thumbnails_dir,
            max_download_mb=min(20, max(5, self.max_bytes // (1024 * 1024))),
            session=self.session,
            extra_allowed_hosts=self.allowed_hosts,
        )
        downloaded = temporary_downloader.download(preview)
        temporary = destination.with_suffix(".part")
        try:
            with Image.open(downloaded.path) as image:
                converted = ImageOps.exif_transpose(image).convert("RGB")
                converted.thumbnail(size, Image.Resampling.LANCZOS)
                converted.save(temporary, "JPEG", quality=84, optimize=True)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
            downloaded.path.unlink(missing_ok=True)
        return destination

    def dominant_color(self, path: Path) -> str:
        try:
            with Image.open(path) as image:
                sample = (
                    ImageOps.exif_transpose(image).convert("RGB").resize((1, 1), Image.Resampling.BILINEAR)
                )
                red, green, blue = sample.getpixel((0, 0))
                return f"#{red:02X}{green:02X}{blue:02X}"
        except (OSError, UnidentifiedImageError):
            return "#F7F06D"

    def cleanup(self, max_cache_mb: int, protected_paths: set[Path] | None = None) -> int:
        protected = {path.resolve() for path in (protected_paths or set()) if path.exists()}
        limit = max_cache_mb * 1024 * 1024
        files = [
            path
            for directory in (self.images_dir, self.thumbnails_dir)
            for path in directory.glob("*")
            if path.is_file() and path.suffix != ".part"
        ]
        total = sum(path.stat().st_size for path in files)
        removed = 0
        for path in sorted(files, key=lambda item: item.stat().st_mtime):
            if total <= limit:
                break
            if path.resolve() in protected:
                continue
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            total -= size
            removed += 1
        return removed

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed = hostname in self.allowed_hosts or any(
            hostname.endswith(suffix) for suffix in ALLOWED_SUFFIXES
        )
        if parsed.scheme != "https" or not hostname or not allowed:
            raise DownloadError(f"Untrusted wallpaper URL: {hostname or 'invalid URL'}")

    @staticmethod
    def _verify_image(path: Path) -> tuple[int, int]:
        try:
            with Image.open(path) as image:
                width, height = image.size
                image.verify()
            if width < 320 or height < 200:
                raise DownloadError("Downloaded image is too small to use as wallpaper")
            return width, height
        except (OSError, UnidentifiedImageError) as exc:
            raise DownloadError("Downloaded file is not a valid image") from exc

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _safe_id(value: str) -> str:
        return "".join(character for character in value if character.isalnum() or character in "-_")[:80]
