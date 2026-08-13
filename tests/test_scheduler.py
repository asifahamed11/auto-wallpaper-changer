from wallpaper_changer.services.scheduler import WindowsTaskScheduler
from wallpaper_changer.services.startup import WindowsStartupManager


def test_source_scheduler_command_is_quoted(monkeypatch, tmp_path):
    executable = tmp_path / "Python Folder" / "python.exe"
    scheduler = WindowsTaskScheduler(executable)
    monkeypatch.delattr("sys.frozen", raising=False)
    command = scheduler.build_run_command()
    assert str(executable.resolve()) in command
    assert "-m wallpaper_changer --change-now --scheduled" in command


def test_frozen_scheduler_splits_command_and_arguments(monkeypatch, tmp_path):
    executable = tmp_path / "Auto Wallpaper Changer.exe"
    scheduler = WindowsTaskScheduler(executable)
    monkeypatch.setattr("sys.frozen", True, raising=False)
    command, arguments = scheduler.command_and_arguments()
    assert command == str(executable.resolve())
    assert arguments == "--change-now --scheduled"


def test_scheduler_xml_is_missed_run_and_battery_aware(monkeypatch, tmp_path):
    executable = tmp_path / "AutoWallpaperChanger.exe"
    scheduler = WindowsTaskScheduler(executable)
    captured = {}
    monkeypatch.setattr(scheduler, "_require_windows", lambda: None)

    def capture(command):
        xml_path = command[command.index("/XML") + 1]
        with open(xml_path, encoding="utf-16") as task_file:
            captured["xml"] = task_file.read()

    monkeypatch.setattr(scheduler, "_run", capture)
    scheduler.enable(30, run_on_battery=False)
    assert "<Interval>PT30M</Interval>" in captured["xml"]
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in captured["xml"]
    assert "<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>" in captured["xml"]
    assert "--change-now --scheduled" in captured["xml"]


def test_startup_command_starts_minimized(monkeypatch, tmp_path):
    executable = tmp_path / "Python Folder" / "python.exe"
    manager = WindowsStartupManager(executable)
    monkeypatch.delattr("sys.frozen", raising=False)
    assert "-m wallpaper_changer --minimized" in manager.command()
