"""Single entry for cheeT1.exe and for pythonw launch.py --host / --tray / …"""

from __future__ import annotations

import sys


def main() -> int:
    argv = sys.argv[1:]
    mode = argv[0] if argv and argv[0].startswith("--") else "--settings"
    rest = argv[1:] if argv and argv[0].startswith("--") else argv

    if mode == "--host":
        import main as host

        return host.main()
    if mode == "--tray":
        import tray_host

        return tray_host.main()
    if mode == "--stop":
        import runtime

        runtime.stop_host(quiet=False)
        return 0
    if mode == "--stop-quiet":
        import runtime

        runtime.stop_host(quiet=True)
        return 0
    if mode == "--restart":
        import runtime

        runtime.restart_host()
        return 0
    if mode == "--status":
        import status_toast

        sys.argv = [sys.argv[0], *(rest or ["Started"])]
        return status_toast.main()
    if mode == "--install":
        import runtime

        runtime.ensure_installed()
        return 0
    if mode == "--uninstall":
        import runtime

        runtime.uninstall()
        return 0

    import runtime
    from utils import bind_app_id, is_frozen

    bind_app_id("cheeT1.Settings")
    if is_frozen():
        runtime.ensure_installed()
    import app

    return app.main()


if __name__ == "__main__":
    sys.exit(main())
