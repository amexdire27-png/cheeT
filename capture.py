"""Active-window targeting, screenshot capture, and native text extraction."""

from __future__ import annotations

import ctypes
import io
import logging
import os
import re
import threading
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional

import mss
import win32gui
import win32process
from PIL import Image
from mss.exception import ScreenShotError

from utils import AppError, ensure_dir, hide_path

_log = logging.getLogger("pagemind.capture")

_API_EDGE = 1280
_JPEG_QUALITY = 72

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi

dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_uint,
]
dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

# DWMWA_EXTENDED_FRAME_BOUNDS — true visible rect, no drop shadow.
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
GA_ROOT = 2

BROWSER_PROCESSES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
    "arc.exe",
    "iexplore.exe",
    "browser.exe",
    "waterfox.exe",
    "librewolf.exe",
}

# Skip IME / overlay popups that steal foreground without being the real app.
SKIP_CLASSES = {
    "IME",
    "MSCTFIME UI",
    "tooltips_class32",
    "Windows.UI.Core.CoreWindow",
}


def _dwm_rect(hwnd: int) -> Optional[tuple[int, int, int, int]]:
    rect = wintypes.RECT()
    try:
        result = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        )
    except OSError:
        return None
    if result != 0:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def _is_cloaked(hwnd: int) -> bool:
    cloaked = wintypes.DWORD(0)
    try:
        result = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_CLOAKED,
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
    except OSError:
        return False
    return result == 0 and cloaked.value != 0


def _process_name(hwnd: int) -> str:
    """Resolve the executable name without needing PROCESS_VM_READ."""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return ""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buf))
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        if not ok:
            return ""
        return Path(buf.value).name.lower()
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _is_browser(hwnd: int) -> bool:
    return _process_name(hwnd) in BROWSER_PROCESSES


def _is_usable(hwnd: int) -> bool:
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
        return False
    if _is_cloaked(hwnd):
        return False
    class_name = win32gui.GetClassName(hwnd) or ""
    if class_name in SKIP_CLASSES:
        return False
    title = win32gui.GetWindowText(hwnd) or ""
    if class_name == "Progman" or title == "Program Manager":
        return False
    return True


def _window_rect(hwnd: int) -> tuple[int, int, int, int]:
    dwm = _dwm_rect(hwnd)
    if dwm:
        left, top, right, bottom = dwm
    else:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width < 32 or height < 32:
        raise AppError(
            f"Window too small to capture ({width}x{height})",
            user_message="Active window is too small to capture",
        )
    return left, top, right, bottom


def _find_topmost_browser() -> Optional[int]:
    found: list[int] = []

    def _enum(hwnd: int, _: int) -> bool:
        if not found and _is_usable(hwnd) and _is_browser(hwnd):
            found.append(hwnd)
        return True

    try:
        win32gui.EnumWindows(_enum, 0)
    except Exception:
        _log.debug("EnumWindows failed while searching for a browser", exc_info=True)
    return found[0] if found else None


def get_target_hwnd(*, prefer_browser: bool = True) -> int:
    """Return the window we should capture: foreground, preferring a browser."""
    raw = win32gui.GetForegroundWindow()
    hwnd = win32gui.GetAncestor(raw, GA_ROOT) if raw else 0
    if not hwnd:
        hwnd = raw

    if _is_usable(hwnd):
        if prefer_browser and not _is_browser(hwnd):
            browser = _find_topmost_browser()
            # Only switch if the current foreground is a tiny overlay / our toast.
            try:
                left, top, right, bottom = _window_rect(hwnd)
                tiny = (right - left) < 280 or (bottom - top) < 160
            except AppError:
                tiny = True
            class_name = win32gui.GetClassName(hwnd) or ""
            if browser and (tiny or class_name == "PageMindToast"):
                _log.info("Foreground is an overlay; using browser hwnd=%s", browser)
                return browser
        return hwnd

    if prefer_browser:
        browser = _find_topmost_browser()
        if browser:
            _log.info("Foreground unusable; falling back to browser hwnd=%s", browser)
            return browser

    raise AppError("No active window", user_message="No active window to capture")


def _clip_to_virtual_screen(
    left: int, top: int, right: int, bottom: int
) -> tuple[int, int, int, int]:
    vs_left = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vs_top = user32.GetSystemMetrics(77)
    vs_w = user32.GetSystemMetrics(78)
    vs_h = user32.GetSystemMetrics(79)
    vs_right, vs_bottom = vs_left + vs_w, vs_top + vs_h
    left = max(left, vs_left)
    top = max(top, vs_top)
    right = min(right, vs_right)
    bottom = min(bottom, vs_bottom)
    if right - left < 8 or bottom - top < 8:
        raise AppError(
            "Window is off-screen",
            user_message="Active window is off-screen",
        )
    return left, top, right, bottom


def _safe_slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_")
    return (cleaned or "window")[:40]


def _grab_monitor(monitor: dict):
    """Fresh GDI session per shot — reusing mss on Windows hits WinError 183."""
    last: Exception | None = None
    for attempt in range(3):
        try:
            with mss.mss() as sct:
                return sct.grab(monitor)
        except (ScreenShotError, OSError) as exc:
            last = exc
            _log.warning("Screenshot grab failed (attempt %s): %s", attempt + 1, exc)
            time.sleep(0.08 * (attempt + 1))
    raise AppError(
        f"Screenshot failed: {last}",
        user_message="Failed",
    ) from last


def _jpeg_for_api(image: Image.Image) -> bytes:
    """Compact JPEG so the Gemini upload stays small and fast."""
    work = image
    if work.mode != "RGB":
        work = work.convert("RGB")
    width, height = work.size
    longest = max(width, height)
    if longest > _API_EDGE:
        scale = _API_EDGE / longest
        work = work.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.BILINEAR,
        )
    buffer = io.BytesIO()
    work.save(buffer, format="JPEG", quality=_JPEG_QUALITY, subsampling=2)
    return buffer.getvalue()


def capture_window(hwnd: int, folder: Path) -> tuple[Path, bytes]:
    """Grab the window. Archive a PNG in the background; return JPEG for Gemini."""
    ensure_dir(folder, hidden=True)
    hide_path(folder.parent)

    left, top, right, bottom = _clip_to_virtual_screen(*_window_rect(hwnd))
    width, height = right - left, bottom - top
    title = win32gui.GetWindowText(hwnd) or "window"
    proc = _process_name(hwnd) or "app"

    monitor = {"left": left, "top": top, "width": width, "height": height}
    raw = _grab_monitor(monitor)
    image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    api_bytes = _jpeg_for_api(image)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    millis = int(time.time() * 1000) % 1000
    filename = f"{stamp}_{millis:03d}_{os.getpid()}_{_safe_slug(proc)}_{_safe_slug(title)}.png"
    dest = folder / filename
    archive = image.copy()

    def _save() -> None:
        try:
            archive.save(dest, format="PNG")
            _log.info("Saved screenshot %s (%sx%s)", dest.name, width, height)
        except Exception:
            _log.exception("Background PNG save failed for %s", dest)

    threading.Thread(target=_save, name="pagemind-save", daemon=True).start()
    _log.info("Captured %sx%s hwnd=%s api_jpeg=%s bytes", width, height, hwnd, len(api_bytes))
    return dest, api_bytes


def extract_native_text(hwnd: int) -> str:
    """Pull visible Win32 control text. Browsers skip this — vision is faster."""
    if _is_browser(hwnd):
        _log.info("Skipping native OCR for browser hwnd=%s", hwnd)
        return ""

    chunks: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        item = (text or "").strip()
        if len(item) < 2 or item in seen:
            return
        seen.add(item)
        chunks.append(item)

    _add(win32gui.GetWindowText(hwnd))

    def _walk(child: int, _: int) -> bool:
        try:
            if win32gui.IsWindowVisible(child):
                _add(win32gui.GetWindowText(child))
                length = int(user32.SendMessageW(child, 0x0E, 0, 0))
                if 0 < length <= 20000:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.SendMessageW(child, 0x0D, length + 1, ctypes.addressof(buf))
                    _add(buf.value)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(hwnd, _walk, 0)
    except Exception:
        _log.debug("EnumChildWindows failed", exc_info=True)

    text = "\n".join(chunks).strip()
    _log.info("Native text extracted: %s chars from hwnd=%s", len(text), hwnd)
    return text
