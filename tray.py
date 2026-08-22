"""Bland tray control — looks like a normal host utility in the overflow icons."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from utils import app_dir

_log = logging.getLogger("pagemind.tray")

DISPLAY_NAME = "Sync Host"
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000
_icon = None


def _system_icon():
    """Use a real Windows imageres icon so it blends with other tray apps."""
    try:
        import win32con
        import win32gui
        import win32ui
        from PIL import Image

        dll = str(Path(r"C:\Windows\System32\imageres.dll"))
        # 15 = generic computer — common on OEM utilities.
        large, small = win32gui.ExtractIconEx(dll, 15)
        handles = (small or []) + (large or [])
        if not handles:
            return None
        hicon = handles[0]
        size = 16
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, size, size)
        mem = hdc.CreateCompatibleDC()
        mem.SelectObject(hbmp)
        win32gui.DrawIconEx(
            mem.GetHandleOutput(), 0, 0, hicon, size, size, 0, 0, win32con.DI_NORMAL
        )
        bits = hbmp.GetBitmapBits(True)
        image = Image.frombuffer("RGB", (size, size), bits, "raw", "BGRX", 0, 1)
        for handle in handles:
            try:
                win32gui.DestroyIcon(handle)
            except Exception:
                pass
        return image.convert("RGBA")
    except Exception:
        _log.debug("Could not extract system tray icon", exc_info=True)
        return None


def _fallback_icon():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 2, 14, 12), radius=2, fill=(120, 124, 128, 255))
    draw.rectangle((3, 4, 12, 9), fill=(70, 74, 78, 255))
    draw.rectangle((6, 12, 9, 14), fill=(120, 124, 128, 255))
    return image


def _run_vbs(name: str) -> None:
    """Launch a helper and detach so killing the host cannot kill this tray."""
    script = app_dir() / name
    try:
        os.startfile(str(script))
        return
    except OSError:
        _log.debug("os.startfile failed for %s", name, exc_info=True)
    try:
        subprocess.Popen(
            [
                "cmd.exe",
                "/c",
                "start",
                "",
                "/b",
                "wscript.exe",
                "//B",
                "//Nologo",
                str(script),
            ],
            cwd=str(app_dir()),
            close_fds=True,
            creationflags=(
                _DETACHED_PROCESS
                | _CREATE_NEW_PROCESS_GROUP
                | _CREATE_BREAKAWAY_FROM_JOB
            ),
        )
    except Exception:
        _log.exception("Helper %s failed", name)


def _start_host(_icon=None, _item=None) -> None:
    _run_vbs("run_hidden.vbs")


def _restart(_icon=None, _item=None) -> None:
    _run_vbs("restart_host.vbs")


def _make_icon():
    from pystray import Icon, Menu, MenuItem

    image = _system_icon() or _fallback_icon()
    menu = Menu(
        MenuItem("Start", _start_host, default=True),
        MenuItem("Restart", _restart),
    )
    return Icon("SyncHost", image, DISPLAY_NAME, menu)


def run_forever() -> None:
    """Block on the overflow icon. Used by the always-on tray process."""
    global _icon
    try:
        _icon = _make_icon()
    except Exception:
        _log.warning("pystray is not installed — no tray icon")
        return
    _log.info("Tray icon started as %s", DISPLAY_NAME)
    try:
        _icon.run()
    finally:
        _icon = None


def start() -> None:
    """Show the overflow icon without blocking. Kept for compatibility."""
    global _icon
    try:
        _icon = _make_icon()
    except Exception:
        _log.warning("pystray is not installed — no tray icon")
        return
    try:
        _icon.run_detached()
        _log.info("Tray icon started as %s", DISPLAY_NAME)
    except Exception:
        _log.exception("Tray icon failed")
        _icon = None


def stop() -> None:
    global _icon
    if _icon is None:
        return
    try:
        _icon.stop()
    except Exception:
        pass
    _icon = None
