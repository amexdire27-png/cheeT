"""Start / stop / install helpers shared by the tray, settings, and cheeT1.exe."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from utils import (
    app_dir,
    expand_path,
    is_frozen,
    is_host_running,
    is_tray_running,
    pid_path,
    resource_dir,
)

_log = logging.getLogger("pagemind.runtime")

_DETACHED = 0x00000008
_NEW_GROUP = 0x00000200
_BREAKAWAY = 0x01000000
_NO_WINDOW = 0x08000000
_TASK = "PageMind"


def interpreter() -> str:
    if is_frozen():
        return str(Path(sys.executable).resolve())
    exe = Path(sys.executable).resolve()
    pythonw = exe.with_name("pythonw.exe")
    return str(pythonw if pythonw.exists() else exe)


def _command(mode: str, *extra: str) -> list[str]:
    cmd = [interpreter()]
    if not is_frozen():
        cmd.append(str(app_dir() / "launch.py"))
    cmd.append(mode)
    cmd.extend(extra)
    return cmd


def spawn_mode(mode: str, *extra: str) -> None:
    """Start another cheeT1 role and detach (host / tray / status toast)."""
    flags = _DETACHED | _NEW_GROUP | _BREAKAWAY | _NO_WINDOW
    try:
        subprocess.Popen(
            _command(mode, *extra),
            cwd=str(app_dir()),
            close_fds=True,
            creationflags=flags,
        )
    except Exception:
        _log.exception("Failed to start %s", mode)


def _kill_pid_file() -> None:
    path = pid_path()
    if not path.exists():
        return
    try:
        pid = path.read_text(encoding="utf-8").strip()
        if pid:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", pid],
                capture_output=True,
                creationflags=_NO_WINDOW,
            )
    except OSError:
        pass
    try:
        path.unlink()
    except OSError:
        pass


def _is_host_command(name: str, cmd: str) -> bool:
    name = name.lower()
    cmd = cmd.lower()
    if name == "cheeT1.exe".lower() and "--host" in cmd:
        return True
    if name in {"python.exe", "pythonw.exe"}:
        if "main.py" in cmd:
            return True
        if "launch.py" in cmd and "--host" in cmd:
            return True
    return False


def _is_tray_command(name: str, cmd: str) -> bool:
    name = name.lower()
    cmd = cmd.lower()
    if name == "cheeT1.exe".lower() and "--tray" in cmd:
        return True
    if name in {"python.exe", "pythonw.exe"}:
        if "tray_host.py" in cmd:
            return True
        if "launch.py" in cmd and "--tray" in cmd:
            return True
    return False


def _wmi_kill(match) -> None:
    if sys.platform != "win32":
        return
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        wmi = win32com.client.GetObject("winmgmts:")
        self_pid = os.getpid()
        for proc in wmi.ExecQuery(
            "SELECT ProcessId, Name, CommandLine FROM Win32_Process"
        ):
            pid = int(proc.ProcessId)
            if pid == self_pid:
                continue
            name = str(proc.Name or "")
            cmd = str(proc.CommandLine or "")
            if match(name, cmd):
                try:
                    proc.Terminate()
                except Exception:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True,
                        creationflags=_NO_WINDOW,
                    )
    except Exception:
        _log.debug("WMI process scan failed", exc_info=True)


def kill_host() -> None:
    _kill_pid_file()
    _wmi_kill(_is_host_command)


def wait_host_gone(seconds: float = 6.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not is_host_running():
            time.sleep(0.35)
            return
        time.sleep(0.15)


def start_host() -> None:
    spawn_mode("--host")
    spawn_mode("--status", "Started")


def restart_host() -> None:
    kill_host()
    wait_host_gone()
    spawn_mode("--host")
    spawn_mode("--status", "Restarted")


def stop_host(*, quiet: bool = False) -> None:
    kill_host()
    if not quiet:
        spawn_mode("--status", "Stopped")


def start_tray() -> None:
    if is_tray_running():
        return
    spawn_mode("--tray")


def _shortcut(path: str, target: str, arguments: str, *, icon: str, description: str) -> None:
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    link = shell.CreateShortcut(path)
    link.TargetPath = target
    link.Arguments = arguments
    link.WorkingDirectory = str(Path(target).parent)
    link.WindowStyle = 1
    link.IconLocation = icon
    link.Description = description
    link.Save()


def _install_marker() -> Path:
    return expand_path(r"%LOCALAPPDATA%\.cache\syshelper\installed.v1")


def ensure_installed() -> None:
    """Register logon tray + desktop/Start shortcuts. Frozen builds only."""
    if not is_frozen():
        return
    exe = str(Path(sys.executable).resolve())
    marker = _install_marker()
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == exe:
        start_tray()
        return
    try:
        _write_task(exe)
        _write_shortcuts(exe)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(exe + "\n", encoding="utf-8")
    except Exception:
        _log.exception("Install (shortcuts / logon task) failed")
    start_tray()


def _write_task(exe: str) -> None:
    subprocess.run(
        [
            "schtasks.exe",
            "/Create",
            "/TN",
            _TASK,
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
            "/F",
            "/TR",
            f'"{exe}" --tray',
        ],
        capture_output=True,
        creationflags=_NO_WINDOW,
        check=False,
    )


def _write_shortcuts(exe: str) -> None:
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    start_menu = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
    start_menu.mkdir(parents=True, exist_ok=True)
    ico = str(resource_dir() / "assets" / "app.ico")
    if not Path(ico).exists():
        ico = exe
    bland = r"%SystemRoot%\System32\imageres.dll,15"
    _shortcut(
        str(desktop / "cheeT1.lnk"),
        exe,
        "",
        icon=ico,
        description="cheeT1 — on-screen assistant",
    )
    _shortcut(
        str(start_menu / "cheeT1.lnk"),
        exe,
        "",
        icon=ico,
        description="cheeT1 — on-screen assistant",
    )
    _shortcut(
        str(start_menu / "Chee.lnk"),
        exe,
        "",
        icon=ico,
        description="Chee — on-screen assistant (cheeT1)",
    )
    _shortcut(
        str(desktop / "Sync Host.lnk"),
        exe,
        "--stop",
        icon=bland,
        description="Synchronizes host cache",
    )


def uninstall() -> None:
    subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", _TASK, "/F"],
        capture_output=True,
        creationflags=_NO_WINDOW,
        check=False,
    )
    kill_host()
    _wmi_kill(_is_tray_command)
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    start_menu = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"))
    for folder in (desktop, start_menu):
        for name in ("Sync Host.lnk", "cheeT1.lnk", "Chee.lnk"):
            try:
                (folder / name).unlink()
            except OSError:
                pass
    try:
        _install_marker().unlink()
    except OSError:
        pass
