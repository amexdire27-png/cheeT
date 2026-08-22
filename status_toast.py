"""Short-lived helper: show a 2s Sync Host status toast, then exit."""

from __future__ import annotations

import sys

import notify
from utils import hide_console


def main() -> int:
    hide_console()
    notify.bind_app_id()
    title = sys.argv[1].strip() if len(sys.argv) > 1 else "Started"
    notify.present_status_blocking(title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
