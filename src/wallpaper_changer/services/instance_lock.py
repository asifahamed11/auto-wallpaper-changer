from __future__ import annotations

import ctypes
import sys

ERROR_ALREADY_EXISTS = 183


class NamedMutex:
    def __init__(self, name: str):
        self.name = name
        self._handle = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        self._handle = kernel32.CreateMutexW(None, False, f"Local\\{self.name}")
        if not self._handle:
            return False
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(self._handle)
            self._handle = None
            return False
        return True

    def release(self) -> None:
        if self._handle and sys.platform == "win32":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> NamedMutex:
        if not self.acquire():
            raise RuntimeError("Another wallpaper change is already running")
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()
