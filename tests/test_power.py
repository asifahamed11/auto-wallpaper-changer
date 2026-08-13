import ctypes

from wallpaper_changer.services import power


def test_non_windows_is_not_reported_as_battery(monkeypatch):
    monkeypatch.setattr(power.sys, "platform", "linux")
    assert power.is_running_on_battery() is False


def test_windows_battery_status(monkeypatch):
    class Kernel:
        @staticmethod
        def GetSystemPowerStatus(pointer):
            status = ctypes.cast(pointer, ctypes.POINTER(power.SYSTEM_POWER_STATUS)).contents
            status.ACLineStatus = 0
            return 1

    class Windll:
        kernel32 = Kernel()

    monkeypatch.setattr(power.sys, "platform", "win32")
    monkeypatch.setattr(power.ctypes, "windll", Windll(), raising=False)
    assert power.is_running_on_battery() is True
