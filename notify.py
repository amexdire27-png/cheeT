"""Windows 11-style toasts with exact durations (WinRT cannot expire at 2s)."""

from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes
from typing import TYPE_CHECKING, Optional

import pyperclip

from utils import AppError

if TYPE_CHECKING:
    from ai import Analysis

_log = logging.getLogger("pagemind.notify")

DISPLAY_NAME = "Sync Host"
AUMID = "SyncHost.Notify"
CLIPBOARD_TITLE = "Copied to clipboard"
CLIPBOARD_BODY = "Press Ctrl+V to paste."
STATUS_SENT = "Sent"
STATUS_WORKING = "Analyzing…"
STATUS_FAILED = "Failed"
STATUS_SECONDS = 2
ANSWER_SECONDS = 5
_TOAST_LIMIT = 180

_LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
dwmapi = ctypes.windll.dwmapi

user32.DefWindowProcW.restype = _LRESULT
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.RegisterClassW.restype = wintypes.ATOM
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t

WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_LBUTTONUP = 0x0202
WM_CLOSE = 0x0010
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
DT_SINGLELINE = 0x0020
DT_VCENTER = 0x0004
DT_WORDBREAK = 0x0010
DT_NOPREFIX = 0x0800
DT_END_ELLIPSIS = 0x8000
DT_CALCRECT = 0x00000400
TRANSPARENT = 1
LWA_ALPHA = 0x2
SPI_GETWORKAREA = 0x0030
IDC_ARROW = 32512
CLASS_NAME = "SyncHostToast"
TIMER_ID = 1
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", ctypes.c_long),
        ("lfWidth", ctypes.c_long),
        ("lfEscapement", ctypes.c_long),
        ("lfOrientation", ctypes.c_long),
        ("lfWeight", ctypes.c_long),
        ("lfItalic", ctypes.c_byte),
        ("lfUnderline", ctypes.c_byte),
        ("lfStrikeOut", ctypes.c_byte),
        ("lfCharSet", ctypes.c_byte),
        ("lfOutPrecision", ctypes.c_byte),
        ("lfClipPrecision", ctypes.c_byte),
        ("lfQuality", ctypes.c_byte),
        ("lfPitchAndFamily", ctypes.c_byte),
        ("lfFaceName", ctypes.c_wchar * 32),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class _ToastState:
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body
        self.font_app = 0
        self.font_title = 0
        self.font_body = 0
        self.brush = 0
        self.hicon = 0


_lock = threading.Lock()
_run_lock = threading.Lock()
_state: Optional[_ToastState] = None
_hwnd = 0
_class_atom = 0
_wndproc_ref = None


def bind_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
    except OSError:
        pass


def _rgb(r: int, g: int, b: int) -> int:
    return r | (g << 8) | (b << 16)


def _make_font(height: int, weight: int = 400) -> int:
    lf = LOGFONTW()
    lf.lfHeight = -height
    lf.lfWeight = weight
    lf.lfQuality = 5
    lf.lfFaceName = "Segoe UI"
    return gdi32.CreateFontIndirectW(ctypes.byref(lf))


def _work_area() -> wintypes.RECT:
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect


def _load_icon() -> int:
    # ExtractIconW lives in shell32, not user32.
    try:
        shell32.ExtractIconW.restype = wintypes.HICON
        shell32.ExtractIconW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            ctypes.c_uint,
        ]
        handle = shell32.ExtractIconW(
            kernel32.GetModuleHandleW(None),
            r"C:\Windows\System32\imageres.dll",
            15,
        )
        return int(handle) if handle else 0
    except Exception:
        return 0


def _copy(text: str) -> bool:
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        _log.exception("Clipboard copy failed")
        return False


def _clip_body(text: str) -> str:
    body = (text or "").strip() or "No answer"
    if len(body) <= _TOAST_LIMIT:
        return body
    return body[: _TOAST_LIMIT - 1].rstrip() + "…"


def _paint(hwnd: int) -> None:
    assert _state is not None
    ps = PAINTSTRUCT()
    hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
    try:
        rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        user32.FillRect(hdc, ctypes.byref(rect), _state.brush)
        if _state.hicon:
            user32.DrawIconEx(hdc, 16, 18, _state.hicon, 24, 24, 0, None, 0x0003)

        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SetTextColor(hdc, _rgb(160, 160, 160))
        gdi32.SelectObject(hdc, _state.font_app)
        app_rect = wintypes.RECT(52, 12, rect.right - 16, 30)
        user32.DrawTextW(
            hdc,
            DISPLAY_NAME,
            -1,
            ctypes.byref(app_rect),
            DT_SINGLELINE | DT_VCENTER | DT_NOPREFIX | DT_END_ELLIPSIS,
        )

        gdi32.SetTextColor(hdc, _rgb(250, 250, 250))
        gdi32.SelectObject(hdc, _state.font_title)
        title_rect = wintypes.RECT(52, 30, rect.right - 16, 52)
        user32.DrawTextW(
            hdc,
            _state.title,
            -1,
            ctypes.byref(title_rect),
            DT_SINGLELINE | DT_VCENTER | DT_NOPREFIX | DT_END_ELLIPSIS,
        )

        if _state.body:
            gdi32.SetTextColor(hdc, _rgb(200, 200, 200))
            gdi32.SelectObject(hdc, _state.font_body)
            body_rect = wintypes.RECT(52, 54, rect.right - 16, rect.bottom - 14)
            user32.DrawTextW(
                hdc,
                _state.body,
                -1,
                ctypes.byref(body_rect),
                DT_WORDBREAK | DT_NOPREFIX | DT_END_ELLIPSIS,
            )
    finally:
        user32.EndPaint(hwnd, ctypes.byref(ps))


def _cleanup(hwnd: int) -> None:
    global _hwnd
    user32.KillTimer(hwnd, TIMER_ID)
    if _state:
        for attr in ("font_app", "font_title", "font_body", "brush"):
            handle = getattr(_state, attr)
            if handle:
                gdi32.DeleteObject(handle)
                setattr(_state, attr, 0)
        if _state.hicon:
            user32.DestroyIcon(_state.hicon)
            _state.hicon = 0
    _hwnd = 0


@WNDPROC
def _wndproc(hwnd, message, wparam, lparam):
    if message == WM_PAINT:
        _paint(hwnd)
        return 0
    if message == WM_TIMER and wparam == TIMER_ID:
        user32.DestroyWindow(hwnd)
        return 0
    if message in (WM_LBUTTONUP, WM_CLOSE):
        user32.DestroyWindow(hwnd)
        return 0
    if message == WM_DESTROY:
        _cleanup(hwnd)
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, message, wparam, lparam)


def _register_class(instance: int) -> None:
    global _class_atom, _wndproc_ref
    if _class_atom:
        return
    _wndproc_ref = _wndproc
    cls = WNDCLASSW()
    cls.lpfnWndProc = _wndproc_ref
    cls.hInstance = instance
    cls.hCursor = user32.LoadCursorW(None, IDC_ARROW)
    cls.lpszClassName = CLASS_NAME
    atom = user32.RegisterClassW(ctypes.byref(cls))
    if not atom:
        err = kernel32.GetLastError()
        if err not in (0, 1410):
            raise ctypes.WinError(err)
    _class_atom = atom or 1


def _measure(body: str, width: int, font: int) -> int:
    if not body:
        return 72
    hdc = user32.GetDC(0)
    try:
        gdi32.SelectObject(hdc, font)
        rect = wintypes.RECT(0, 0, width - 70, 8)
        user32.DrawTextW(
            hdc, body, -1, ctypes.byref(rect), DT_WORDBREAK | DT_NOPREFIX | DT_CALCRECT
        )
        return max(92, min(220, rect.bottom + 70))
    finally:
        user32.ReleaseDC(0, hdc)


def dismiss() -> None:
    hwnd = _hwnd
    if hwnd:
        user32.ShowWindow(hwnd, SW_HIDE)
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def dismiss_all() -> None:
    """Force-close every Sync Host toast, including helper-process toasts."""
    dismiss()
    found: list[int] = []

    def _enum(hwnd: int, _lparam: int) -> bool:
        buf = ctypes.create_unicode_buffer(64)
        if user32.GetClassNameW(hwnd, buf, 64) and buf.value == CLASS_NAME:
            found.append(hwnd)
        return True

    callback = WNDENUMPROC(_enum)
    user32.EnumWindows(callback, 0)
    for hwnd in found:
        user32.ShowWindow(hwnd, SW_HIDE)
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def dismiss_status() -> None:
    dismiss()


def _run_toast(title: str, body: str, seconds: float) -> None:
    global _state, _hwnd
    with _run_lock:
        instance = kernel32.GetModuleHandleW(None)
        _register_class(instance)
        state = _ToastState(title, body)
        state.font_app = _make_font(12, 400)
        state.font_title = _make_font(15, 600)
        state.font_body = _make_font(13, 400)
        state.brush = gdi32.CreateSolidBrush(_rgb(32, 32, 32))
        try:
            state.hicon = _load_icon()
        except Exception:
            state.hicon = 0
        _state = state

        width = 360
        height = _measure(body, width, state.font_body)
        area = _work_area()
        x = area.right - width - 12
        y = area.bottom - height - 12
        hwnd = user32.CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED,
            CLASS_NAME,
            DISPLAY_NAME,
            WS_POPUP,
            x,
            y,
            width,
            height,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            _cleanup(0)
            raise ctypes.WinError()

        _hwnd = hwnd
        preference = ctypes.c_int(DWMWCP_ROUND)
        try:
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
            dark = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark),
                ctypes.sizeof(dark),
            )
        except OSError:
            pass
        user32.SetLayeredWindowAttributes(hwnd, 0, 245, LWA_ALPHA)
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, x, y, width, height, SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        user32.SetTimer(hwnd, TIMER_ID, max(1, int(seconds * 1000)), None)
        user32.UpdateWindow(hwnd)

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


def show(title: str, body: str = "", *, duration_seconds: float = ANSWER_SECONDS) -> None:
    """Windows 11-styled toast that auto-dismisses after duration_seconds."""
    title = (title or "").strip() or DISPLAY_NAME
    body = _clip_body(body) if (body or "").strip() else ""

    def _worker() -> None:
        try:
            dismiss()
            time.sleep(0.04)
            _run_toast(title, body, duration_seconds)
        except Exception:
            _log.exception("Toast failed")

    with _lock:
        threading.Thread(target=_worker, name="pagemind-toast", daemon=True).start()


def present_analysis(result: "Analysis", *, duration: int) -> None:
    seconds = duration if duration else ANSWER_SECONDS
    text = (result.answer or "").strip() or "No answer"
    if _copy(text):
        _log.info(
            "Copied %s-char %s answer to clipboard",
            len(text),
            ",".join(result.types) or "unknown",
        )
    else:
        _log.warning("Clipboard copy failed")
    if len(text) <= 48:
        show(text, duration_seconds=seconds)
    else:
        show("Answer", text, duration_seconds=seconds)


def present_error(message: str, *, duration: int) -> None:
    show(message, duration_seconds=duration or ANSWER_SECONDS)


def present_status(message: str, *, duration: float = STATUS_SECONDS) -> None:
    show(message, duration_seconds=duration)


def present_status_blocking(message: str, *, duration: float = STATUS_SECONDS) -> None:
    """Show a 2s status toast and wait so a short-lived helper process stays alive."""
    try:
        dismiss()
        time.sleep(0.04)
        _run_toast((message or "").strip() or DISPLAY_NAME, "", duration)
    except Exception:
        _log.exception("Toast failed")


def present_failed(message: str = STATUS_FAILED) -> None:
    show(message or STATUS_FAILED, duration_seconds=STATUS_SECONDS)


def run_with_status(fn, *, timeout: float):
    holder: dict = {}

    def _target() -> None:
        try:
            holder["ok"] = fn()
        except BaseException as exc:
            holder["err"] = exc

    started = time.monotonic()
    deadline = started + max(8.0, float(timeout)) + 5.0
    worker = threading.Thread(target=_target, name="pagemind-gemini", daemon=True)
    worker.start()
    present_status(STATUS_SENT, duration=STATUS_SECONDS)

    analyzing = False
    while worker.is_alive():
        now = time.monotonic()
        if now >= deadline:
            _log.warning("Request unfinished after %.1fs — Failed", timeout)
            raise AppError(
                f"Unfinished after {timeout:.0f}s",
                user_message="Failed",
            )
        if not analyzing and now - started >= STATUS_SECONDS:
            present_status(STATUS_WORKING, duration=STATUS_SECONDS)
            analyzing = True
        worker.join(timeout=0.05)

    if "err" in holder:
        raise holder["err"]
    return holder["ok"]
