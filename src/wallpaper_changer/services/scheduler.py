from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROTATION_TASK = "AutoWallpaperChanger-Rotation"


class SchedulerError(RuntimeError):
    pass


class WindowsTaskScheduler:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or Path(sys.executable)

    def build_run_command(self) -> str:
        command, arguments = self.command_and_arguments()
        return f'"{command}" {arguments}'

    def command_and_arguments(self) -> tuple[str, str]:
        executable = str(self.executable.resolve())
        if getattr(sys, "frozen", False):
            return executable, "--change-now --scheduled"
        pythonw = self.executable.with_name("pythonw.exe")
        launcher = pythonw if pythonw.exists() else self.executable
        return str(launcher.resolve()), "-m wallpaper_changer --change-now --scheduled"

    def enable(self, interval_minutes: int, *, run_on_battery: bool = True) -> None:
        self._require_windows()
        minutes = min(max(int(interval_minutes), 15), 43_200)
        executable, arguments = self.command_and_arguments()
        start_boundary = (
            (datetime.now().astimezone() + timedelta(minutes=2)).replace(microsecond=0).isoformat()
        )
        disallow_battery = "false" if run_on_battery else "true"
        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Periodically changes the desktop wallpaper using Wallwidgy.</Description></RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition><Interval>PT{minutes}M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
      <StartBoundary>{escape(start_boundary)}</StartBoundary><Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>{disallow_battery}</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle><WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit><Priority>7</Priority>
  </Settings>
  <Actions Context="Author"><Exec><Command>{escape(executable)}</Command><Arguments>{escape(arguments)}</Arguments></Exec></Actions>
</Task>
"""
        xml_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-16", suffix=".xml", delete=False
            ) as task_file:
                task_file.write(xml)
                xml_path = Path(task_file.name)
            self._run(["schtasks.exe", "/Create", "/TN", ROTATION_TASK, "/XML", str(xml_path), "/F"])
        finally:
            if xml_path:
                xml_path.unlink(missing_ok=True)

    def disable(self) -> None:
        self._require_windows()
        result = subprocess.run(
            ["schtasks.exe", "/Delete", "/TN", ROTATION_TASK, "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode not in {0, 1}:
            raise SchedulerError(
                result.stderr.strip() or result.stdout.strip() or "Could not remove scheduled task"
            )

    def is_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        result = subprocess.run(
            ["schtasks.exe", "/Query", "/TN", ROTATION_TASK],
            capture_output=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode == 0

    @staticmethod
    def _require_windows() -> None:
        if sys.platform != "win32":
            raise SchedulerError("Windows Task Scheduler is available only on Windows")

    @staticmethod
    def _run(command: list[str]) -> None:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise SchedulerError(
                result.stderr.strip() or result.stdout.strip() or "Could not configure scheduled task"
            )
