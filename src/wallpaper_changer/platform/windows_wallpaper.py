from __future__ import annotations

import ctypes
import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from wallpaper_changer.models import Monitor

LOGGER = logging.getLogger("wallpaper_changer.windows")
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02
POSITIONS = {"center": 0, "tile": 1, "stretch": 2, "fit": 3, "fill": 4, "span": 5}


class WallpaperPlatformError(RuntimeError):
    pass


class WindowsWallpaperService:
    def set_wallpaper(
        self,
        path: Path,
        *,
        monitor_id: str | None = None,
        position: str = "fill",
    ) -> None:
        if sys.platform != "win32":
            raise WallpaperPlatformError("Wallpaper changes are supported only on Windows")
        resolved = path.resolve()
        if not resolved.is_file():
            raise WallpaperPlatformError(f"Wallpaper file does not exist: {resolved}")

        try:
            with self._desktop_interface() as desktop:
                desktop.SetPosition(POSITIONS.get(position, POSITIONS["fill"]))
                desktop.SetWallpaper(monitor_id or None, str(resolved))
            return
        except Exception as exc:  # COM may be unavailable on stripped-down Windows editions.
            if monitor_id:
                raise WallpaperPlatformError(
                    f"Could not set wallpaper on the selected monitor: {exc}"
                ) from exc
            LOGGER.warning("IDesktopWallpaper unavailable, using SystemParametersInfoW: %s", exc)

        self._set_position_registry(position)
        ctypes.set_last_error(0)
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            str(resolved),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        if not result:
            error = ctypes.get_last_error()
            raise WallpaperPlatformError(f"Windows rejected the wallpaper change (error {error})")

    def get_current(self, monitor_id: str | None = None) -> Path | None:
        if sys.platform != "win32":
            return None
        try:
            with self._desktop_interface() as desktop:
                value = desktop.GetWallpaper(monitor_id or None)
            return Path(value) if value else None
        except Exception:
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                    value, _ = winreg.QueryValueEx(key, "WallPaper")
                return Path(value) if value else None
            except OSError:
                return None

    def monitors(self) -> list[Monitor]:
        if sys.platform != "win32":
            return []
        try:
            with self._desktop_interface() as desktop:
                count = int(desktop.GetMonitorDevicePathCount())
                monitors: list[Monitor] = []
                for index in range(count):
                    monitor_id = str(desktop.GetMonitorDevicePathAt(index))
                    rect = desktop.GetMonitorRECT(monitor_id)
                    monitors.append(
                        Monitor(
                            id=monitor_id,
                            label=f"Display {index + 1}",
                            left=int(rect.left),
                            top=int(rect.top),
                            right=int(rect.right),
                            bottom=int(rect.bottom),
                        )
                    )
            return monitors
        except Exception as exc:
            LOGGER.warning("Could not enumerate monitors: %s", exc)
            return [Monitor(id="", label="All displays")]

    @contextmanager
    def _desktop_interface(self):
        if sys.platform != "win32":
            raise WallpaperPlatformError("IDesktopWallpaper is available only on Windows")

        from ctypes import POINTER, Structure, c_int, c_uint, c_ulong, c_wchar_p

        import comtypes
        from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
        from comtypes.client import CreateObject

        class RECT(Structure):
            _fields_ = [("left", c_int), ("top", c_int), ("right", c_int), ("bottom", c_int)]

        class IDesktopWallpaper(IUnknown):
            _iid_ = GUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")
            _methods_ = [
                COMMETHOD(
                    [],
                    HRESULT,
                    "SetWallpaper",
                    (["in"], c_wchar_p, "monitorID"),
                    (["in"], c_wchar_p, "wallpaper"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetWallpaper",
                    (["in"], c_wchar_p, "monitorID"),
                    (["out"], POINTER(c_wchar_p), "wallpaper"),
                ),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetMonitorDevicePathAt",
                    (["in"], c_uint, "monitorIndex"),
                    (["out"], POINTER(c_wchar_p), "monitorID"),
                ),
                COMMETHOD([], HRESULT, "GetMonitorDevicePathCount", (["out"], POINTER(c_uint), "count")),
                COMMETHOD(
                    [],
                    HRESULT,
                    "GetMonitorRECT",
                    (["in"], c_wchar_p, "monitorID"),
                    (["out"], POINTER(RECT), "displayRect"),
                ),
                COMMETHOD([], HRESULT, "SetBackgroundColor", (["in"], c_ulong, "color")),
                COMMETHOD([], HRESULT, "GetBackgroundColor", (["out"], POINTER(c_ulong), "color")),
                COMMETHOD([], HRESULT, "SetPosition", (["in"], c_int, "position")),
                COMMETHOD([], HRESULT, "GetPosition", (["out"], POINTER(c_int), "position")),
            ]

        clsid = GUID("{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}")
        comtypes.CoInitialize()
        desktop = None
        try:
            desktop = CreateObject(clsid, interface=IDesktopWallpaper)
            yield desktop
        finally:
            if desktop is not None:
                del desktop
            comtypes.CoUninitialize()

    @staticmethod
    def _set_position_registry(position: str) -> None:
        import winreg

        style = {
            "center": ("0", "0"),
            "tile": ("0", "1"),
            "stretch": ("2", "0"),
            "fit": ("6", "0"),
            "fill": ("10", "0"),
            "span": ("22", "0"),
        }.get(position, ("10", "0"))
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, style[0])
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, style[1])


def open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True) if not path.suffix else None
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        raise WallpaperPlatformError("Opening paths is supported only on Windows")
