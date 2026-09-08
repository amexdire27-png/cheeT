"""
PageMind — Windows on-screen assistant (cheeT1).

Hotkeys come from config.json (hotkeys.*). Edit that file, then Restart.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

import ai
import hotkeys
import capture
import notify
from config import Config, load_config
from utils import (
    AbortError,
    AppError,
    acquire_singleton,
    clear_pid,
    ensure_dir,
    hide_console,
    hide_storage_tree,
    set_dpi_aware,
    setup_logging,
    write_pid,
)

_log = logging.getLogger("pagemind")

# Ignore accidental double-taps of the same hotkey.
_DEBOUNCE_SECONDS = 0.7
_busy = threading.Lock()
_last_fire = 0.0
_client: ai.GeminiClient | None = None
_cfg: Config | None = None


def _too_soon() -> bool:
    global _last_fire
    now = time.monotonic()
    if now - _last_fire < _DEBOUNCE_SECONDS:
        _log.info("Hotkey ignored (debounce)")
        return True
    _last_fire = now
    return False


def _run_job(kind: str, fn) -> None:
    """Run capture+AI off the hotkey thread so the hook stays responsive."""
    if _too_soon():
        return
    if not _busy.acquire(blocking=False):
        _log.info("Hotkey ignored (already working)")
        notify.present_status("Busy", duration=2)
        return
    if _client:
        _client.reset_cancel()

    def _worker() -> None:
        try:
            fn()
        except AbortError:
            _log.info("%s aborted", kind)
            notify.dismiss_all()
        except AppError as exc:
            _log.warning("%s failed: %s", kind, exc)
            notify.dismiss_status()
            text = (exc.user_message or "Failed").strip() or "Failed"
            notify.present_error(
                text,
                duration=max(3, int(_cfg.notification_duration_seconds) if _cfg else 5),
            )
        except Exception:
            _log.exception("%s crashed", kind)
            notify.dismiss_status()
            notify.present_failed()
        finally:
            _busy.release()

    threading.Thread(target=_worker, name=f"pagemind-{kind}", daemon=True).start()


def _on_screenshot() -> None:
    assert _cfg is not None and _client is not None
    hwnd = capture.get_target_hwnd(prefer_browser=True)
    path, png = capture.capture_window(hwnd, _cfg.screenshot_folder)
    _log.info("Screenshot mode using %s", path.name)
    result = notify.run_with_status(
        lambda: _client.ask_image(png, ocr_mode=False),
        timeout=_cfg.request_timeout_seconds + 20,
        cancelled=_client.cancelled,
    )
    notify.present_analysis(result, duration=_cfg.notification_duration_seconds)


def _on_ocr() -> None:
    assert _cfg is not None and _client is not None
    hwnd = capture.get_target_hwnd(prefer_browser=True)
    native = capture.extract_native_text(hwnd)
    # Browser pages almost never expose their DOM through Win32 text.
    if len(native) >= 80:
        _log.info("OCR mode using native text (%s chars)", len(native))
        result = notify.run_with_status(
            lambda: _client.ask_text(native),
            timeout=_cfg.request_timeout_seconds + 20,
            cancelled=_client.cancelled,
        )
    else:
        path, png = capture.capture_window(hwnd, _cfg.screenshot_folder)
        _log.info("OCR mode falling back to screenshot %s", path.name)
        result = notify.run_with_status(
            lambda: _client.ask_image(png, ocr_mode=True),
            timeout=_cfg.request_timeout_seconds + 20,
            cancelled=_client.cancelled,
        )
    notify.present_analysis(result, duration=_cfg.notification_duration_seconds)


def _on_dismiss() -> None:
    notify.dismiss_all()
    _log.info("Toasts force-dismissed")


def _on_abort() -> None:
    if _client:
        _client.abort()
    notify.dismiss_all()
    _log.info("In-flight work aborted")
    if _busy.locked():
        notify.present_status("Aborted", duration=2)


def main() -> int:
    global _client, _cfg
    set_dpi_aware()
    hide_console()
    notify.bind_app_id()

    if not acquire_singleton():
        return 0
    write_pid()

    try:
        _cfg = load_config()
    except Exception as exc:
        # Logging is not up yet — try to leave a last-resort file.
        try:
            from pathlib import Path
            import os

            fallback = Path(os.path.expandvars(r"%LOCALAPPDATA%\.cache\syshelper\logs"))
            fallback.mkdir(parents=True, exist_ok=True)
            (fallback / "pagemind.log").write_text(
                f"Failed to load config: {exc}\n", encoding="utf-8"
            )
        except Exception:
            pass
        clear_pid()
        return 1

    ensure_dir(_cfg.screenshot_folder, hidden=True)
    hide_storage_tree(_cfg.screenshot_folder)
    log_path = setup_logging(_cfg.log_folder)
    hide_storage_tree(_cfg.log_folder)
    _log.info("PageMind started. log=%s config=%s", log_path, _cfg.source_path)
    shown = _cfg.hotkeys.display()
    _log.info(
        "Hotkeys: screenshot=%s ocr=%s dismiss=%s abort=%s start=%s restart=%s keys=%s model=%s fallbacks=%s timeout=%ss",
        shown["screenshot"],
        shown["ocr"],
        shown["dismiss"],
        shown["abort"],
        shown["start"],
        shown["restart"],
        len(_cfg.api_keys),
        _cfg.model,
        ",".join(_cfg.fallback_models),
        _cfg.request_timeout_seconds,
    )

    if not _cfg.api_keys:
        _log.error("No API key configured")
        notify.present_error(
            "Add Gemini API keys in cheeT1",
            duration=_cfg.notification_duration_seconds,
        )
    else:
        _log.info("Using %s Gemini API key(s)", len(_cfg.api_keys))

    _client = ai.GeminiClient(_cfg)

    mapping = {
        _cfg.hotkeys.screenshot: lambda: _run_job("screenshot", _on_screenshot),
        _cfg.hotkeys.ocr: lambda: _run_job("ocr", _on_ocr),
        _cfg.hotkeys.dismiss: _on_dismiss,
        _cfg.hotkeys.abort: _on_abort,
    }

    try:
        with hotkeys.StrictHotKeys(mapping) as listener:
            listener.join()
    except KeyboardInterrupt:
        _log.info("Stopped by KeyboardInterrupt")
    except Exception:
        _log.exception("Hotkey listener crashed")
        return 1
    finally:
        if _client:
            _client.close()
        notify.dismiss()
        clear_pid()
        _log.info("PageMind stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
