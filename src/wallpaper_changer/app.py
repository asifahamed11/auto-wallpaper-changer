from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from wallpaper_changer import __version__
from wallpaper_changer.bootstrap import build_services
from wallpaper_changer.logging_config import configure_logging
from wallpaper_changer.paths import get_app_paths
from wallpaper_changer.resources import asset_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wallwidgy Auto Wallpaper Changer")
    parser.add_argument("--change-now", action="store_true", help="Change the wallpaper and exit")
    parser.add_argument("--scheduled", action="store_true", help="Treat the change as a scheduled run")
    parser.add_argument("--minimized", action="store_true", help="Start in the system tray")
    parser.add_argument("--diagnostics", action="store_true", help="Export diagnostics and exit")
    parser.add_argument("--verbose", action="store_true", help="Enable console debug logging")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = get_app_paths().ensure()
    logger = configure_logging(paths, verbose=args.verbose)
    services = build_services(paths)

    if args.diagnostics:
        destination = services.export_diagnostics()
        print(destination)
        return 0
    if args.change_now:
        result = services.wallpaper.change_now(scheduled=args.scheduled)
        (logger.info if result.success else logger.error)(result.message)
        if args.verbose:
            print(result.message)
        return 0 if result.success or result.error_code in {"paused", "battery"} else 1

    if sys.platform != "win32":
        logger.error("The graphical app currently supports Windows only")
        print("Auto Wallpaper Changer currently supports Windows only.", file=sys.stderr)
        return 2

    try:
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtGui import QFont, QFontDatabase, QIcon
        from PySide6.QtWidgets import QApplication

        from wallpaper_changer.ui.single_instance import SingleInstance
        from wallpaper_changer.ui.tray import TrayController
    except ImportError as exc:
        logger.exception("GUI dependency is missing")
        print(f"Could not start the graphical interface: {exc}", file=sys.stderr)
        return 2

    QCoreApplication.setOrganizationName("Asif Ahamed")
    QCoreApplication.setApplicationName("Auto Wallpaper Changer")
    QCoreApplication.setApplicationVersion(__version__)
    application = QApplication(sys.argv[:1])
    application.setQuitOnLastWindowClosed(False)
    for font_path in (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\Nirmala.ttc")):
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    application.setFont(QFont("Segoe UI", 10))
    application.setWindowIcon(QIcon(str(asset_path("icon.svg"))))

    controller_holder: dict[str, TrayController] = {}
    instance = SingleInstance(
        "AutoWallpaperChanger-v2",
        lambda: controller_holder.get("controller") and controller_holder["controller"].show_settings(),
    )
    if instance.notify_existing():
        return 0
    instance.listen()

    controller = TrayController(application, services)
    controller_holder["controller"] = controller
    controller.start(show_window=not args.minimized)
    exit_code = application.exec()
    logging.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
