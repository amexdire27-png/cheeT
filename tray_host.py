"""Always-on overflow tray: Start / Restart. Survives desktop Stop."""

from __future__ import annotations

import logging
import sys

from utils import (
    acquire_tray_singleton,
    expand_path,
    hide_console,
    hide_storage_tree,
    setup_logging,
)

_log = logging.getLogger("pagemind.tray")


def _bind_hotkeys() -> object | None:
    """Start / Restart hotkeys live here so they work even after desktop Stop."""
    try:
        from config import load_config
        from hotkeys import StrictHotKeys
        import tray

        cfg = load_config()
        mapping = {
            cfg.hotkeys.start: tray.start_host,
            cfg.hotkeys.restart: tray.restart_host,
        }
        listener = StrictHotKeys(mapping)
        listener.start()
        _log.info(
            "Tray hotkeys: start=%s restart=%s",
            cfg.hotkeys.start,
            cfg.hotkeys.restart,
        )
        return listener
    except Exception:
        _log.exception("Tray Start/Restart hotkeys failed")
        return None


def main() -> int:
    hide_console()
    if not acquire_tray_singleton():
        return 0

    log_folder = expand_path(r"%LOCALAPPDATA%\.cache\syshelper\logs")
    setup_logging(log_folder)
    hide_storage_tree(log_folder)

    import tray

    listener = _bind_hotkeys()
    _log.info("Tray host running")
    try:
        tray.run_forever()
    finally:
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
