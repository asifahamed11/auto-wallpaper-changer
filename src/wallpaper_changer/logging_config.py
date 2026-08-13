from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from wallpaper_changer.paths import AppPaths


def configure_logging(paths: AppPaths, verbose: bool = False) -> logging.Logger:
    paths.ensure()
    logger = logging.getLogger("wallpaper_changer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        paths.logs / "wallpaper_changer.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    return logger
