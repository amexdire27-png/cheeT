"""Always-on overflow tray: Start / Restart. Survives desktop Stop."""

from __future__ import annotations

import sys

from utils import (
    acquire_tray_singleton,
    expand_path,
    hide_console,
    hide_storage_tree,
    setup_logging,
)


def main() -> int:
    hide_console()
    if not acquire_tray_singleton():
        return 0

    log_folder = expand_path(r"%LOCALAPPDATA%\.cache\syshelper\logs")
    setup_logging(log_folder)
    hide_storage_tree(log_folder)

    import logging
    import tray

    logging.getLogger("pagemind.tray").info("Tray host running")
    tray.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
