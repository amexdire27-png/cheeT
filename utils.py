"""Shared Windows helpers: paths, logging, singleton, attributes, console."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    from ctypes import wintypes
else:
    wintypes = None  # type: ignore[misc, assignment]

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\PageMindSingleton_v1"
TRAY_MUTEX_NAME = "Local\\PageMindTray_v1"
SETTINGS_MUTEX_NAME = "Local\\CheeT1Settings_v1"
_SYNCHRONIZE = 0x00100000

_log = logging.getLogger("pagemind")
_mutex_handle: Optional[int] = None
_tray_mutex_handle: Optional[int] = None
_settings_mutex_handle: Optional[int] = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Writable install folder. config.json lives here."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """Bundled files (assets, example config) when frozen; otherwise the repo."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def expand_path(raw: str) -> Path:
    """Expand %ENV% and ~ in a configured path."""
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def hide_path(path: Path) -> None:
    """Mark a file or folder hidden. Does not recurse."""
    if sys.platform != "win32" or not path.exists():
        return
    try:
        attrs = kernel32.GetFileAttributesW(str(path))
        if attrs == 0xFFFFFFFF:
            return
        kernel32.SetFileAttributesW(str(path), attrs | FILE_ATTRIBUTE_HIDDEN)
    except OSError:
        _log.debug("Could not hide path %s", path, exc_info=True)


def ensure_dir(path: Path, hidden: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if hidden:
        hide_path(path)
    return path


def hide_storage_tree(leaf: Path) -> None:
    """Hide the screenshot/log leaf and its syshelper / .cache parents."""
    current = leaf
    for _ in range(3):
        if current.exists():
            hide_path(current)
        if current.name in {".cache", "syshelper", "img", "logs"}:
            hide_path(current)
        current = current.parent


def hide_console() -> None:
    """Detach from any console so the process has no visible window."""
    if sys.platform != "win32":
        return
    if os.environ.get("PAGEMIND_DEBUG") == "1":
        return
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE
    try:
        kernel32.FreeConsole()
    except OSError:
        pass


def set_dpi_aware() -> None:
    """Per-monitor DPI so screenshot coordinates match the real window."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
        return
    except OSError:
        pass
    try:
        user32.SetProcessDPIAware()
    except OSError:
        pass


def bind_app_id(aumid: str) -> None:
    """Stop Windows grouping this process with python.exe on the taskbar."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(aumid)
    except OSError:
        pass


def _acquire_named_mutex(name: str) -> tuple[bool, Optional[int]]:
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return True, None
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False, handle
    return True, handle


def acquire_singleton() -> bool:
    """Return False if another PageMind instance is already running."""
    global _mutex_handle
    ok, handle = _acquire_named_mutex(MUTEX_NAME)
    _mutex_handle = handle
    return ok


def acquire_tray_singleton() -> bool:
    """Return False if the overflow tray process is already running."""
    global _tray_mutex_handle
    ok, handle = _acquire_named_mutex(TRAY_MUTEX_NAME)
    _tray_mutex_handle = handle
    return ok


def _mutex_already_open(name: str) -> bool:
    """True if another process already holds this named mutex."""
    if sys.platform != "win32" or wintypes is None:
        return False
    kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenMutexW.restype = wintypes.HANDLE
    handle = kernel32.OpenMutexW(_SYNCHRONIZE, False, name)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def is_host_running() -> bool:
    return _mutex_already_open(MUTEX_NAME)


def is_tray_running() -> bool:
    return _mutex_already_open(TRAY_MUTEX_NAME)


def acquire_settings_singleton() -> bool:
    """Return False if the cheeT1 settings window is already open."""
    global _settings_mutex_handle
    ok, handle = _acquire_named_mutex(SETTINGS_MUTEX_NAME)
    _settings_mutex_handle = handle
    return ok


def focus_window_by_title(title: str) -> bool:
    """Restore and focus an existing top-level window. Windows only."""
    if sys.platform != "win32":
        return False
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        return False
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True


def pid_path() -> Path:
    return expand_path(r"%LOCALAPPDATA%\.cache\syshelper\host.pid")


def write_pid() -> None:
    path = pid_path()
    ensure_dir(path.parent, hidden=True)
    hide_path(path.parent)
    try:
        if path.exists():
            kernel32.SetFileAttributesW(str(path), 0x80)  # FILE_ATTRIBUTE_NORMAL
        path.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        try:
            path.unlink()
            path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            _log.debug("Could not write pid file %s", path, exc_info=True)
            return
    hide_path(path)


def clear_pid() -> None:
    path = pid_path()
    try:
        if path.exists() and path.read_text(encoding="utf-8").strip() == str(os.getpid()):
            path.unlink()
    except OSError:
        pass


def setup_logging(log_folder: Path) -> Path:
    """Silent rotating log file. Nothing is written to stdout."""
    ensure_dir(log_folder, hidden=True)
    hide_path(log_folder.parent)
    log_path = log_folder / "pagemind.log"

    root = logging.getLogger("pagemind")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.propagate = False

    handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)

    # Keep third-party libraries quiet unless they error.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pynput").setLevel(logging.WARNING)
    return log_path


def redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


class AppError(Exception):
    """Recoverable error that may be shown in a short notification."""

    def __init__(self, message: str, *, user_message: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message


class AbortError(AppError):
    """User cancelled an in-flight capture or Gemini request."""

    def __init__(self, message: str = "Aborted"):
        super().__init__(message, user_message="Aborted")
