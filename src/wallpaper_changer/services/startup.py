from __future__ import annotations

import sys
from pathlib import Path

RUN_VALUE_NAME = "AutoWallpaperChanger"


class StartupError(RuntimeError):
    pass


class WindowsStartupManager:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or Path(sys.executable)

    def command(self) -> str:
        executable = str(self.executable.resolve())
        if getattr(sys, "frozen", False):
            return f'"{executable}" --minimized'
        pythonw = self.executable.with_name("pythonw.exe")
        launcher = pythonw if pythonw.exists() else self.executable
        return f'"{launcher.resolve()}" -m wallpaper_changer --minimized'

    def enable(self) -> None:
        self._require_windows()
        import winreg

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"
        ) as key:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, self.command())

    def disable(self) -> None:
        self._require_windows()
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            pass

    def is_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"
            ) as key:
                value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return bool(value)
        except FileNotFoundError:
            return False

    @staticmethod
    def _require_windows() -> None:
        if sys.platform != "win32":
            raise StartupError("Startup integration is available only on Windows")
