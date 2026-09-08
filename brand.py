"""cheeT1 brand: name, version, palette, logo, window icon."""

from __future__ import annotations

from pathlib import Path

from utils import resource_dir, expand_path

APP_NAME = "cheeT1"
APP_VERSION = "1"
BYLINE = "By DevaBDM and Gray"
WINDOW_TITLE = "cheeT1"
KEY_URL = "https://aistudio.google.com/apikey"

WINDOW_W = 880
WINDOW_H = 640
RAIL_W = 216

# Black, white, gray. No accent color.
CANVAS = "#F2F2F2"
RAIL = "#E6E6E6"
SURFACE = "#FFFFFF"
INK = "#111111"
MUTED = "#5A5A5A"
DIM = "#8A8A8A"
LINE = "#CFCFCF"
WHITE = "#FFFFFF"
SHADOW = "#111111"
SHADOW_SOFT = "#B4B4B4"
DANGER = "#111111"

# Legacy aliases.
BLACK = INK
PANEL = SURFACE
PANEL_2 = "#EFEFEF"
PANEL_3 = "#FFFFFF"
HAIR = LINE
ORANGE = INK
ORANGE_HOT = "#000000"
ORANGE_SOFT = PANEL_2
ORANGE_WASH = PANEL_2
ORANGE_DEEP = INK
OK = MUTED

SANS_FAMILIES = ("Segoe UI Variable Text", "Segoe UI", "Calibri", "Tahoma")
MONO_FAMILIES = ("Segoe UI Variable Text", "Segoe UI", "Tahoma")

MODELS = (
    "gemini-flash-lite-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
)

HOTKEY_ROWS = (
    ("screenshot", "Picture", "Capture the active window and ask"),
    ("ocr", "Text", "Read the window text, or capture it"),
    ("dismiss", "Dismiss", "Close the current notification"),
    ("abort", "Abort", "Cancel a request that is still running"),
    ("start", "Start", "Wake the background service"),
    ("restart", "Restart", "Stop, then start again"),
)

NAV_ITEMS = ("Shortcuts", "API keys", "Answers")


def logo_path() -> Path:
    root = resource_dir()
    png = root / "assets" / "logo.png"
    if png.exists():
        return png
    return root / "assets" / "logo.jpg"


def mark_path() -> Path:
    return resource_dir() / "assets" / "mark.png"


def icon_path() -> Path:
    return resource_dir() / "assets" / "app.ico"


def logo_dark_path() -> Path:
    return resource_dir() / "assets" / "logo_dark.png"


def welcome_marker() -> Path:
    return expand_path(r"%LOCALAPPDATA%\.cache\syshelper\welcome.seen")


def welcome_seen() -> bool:
    return welcome_marker().exists()


def mark_welcome_seen() -> None:
    path = welcome_marker()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("1\n", encoding="utf-8")


def confetti_marker() -> Path:
    return expand_path(r"%LOCALAPPDATA%\.cache\syshelper\confetti.seen")


def confetti_seen() -> bool:
    return confetti_marker().exists()


def mark_confetti_seen() -> None:
    path = confetti_marker()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("1\n", encoding="utf-8")


def _stale(dest: Path, src: Path) -> bool:
    return not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime


def ensure_app_icon() -> Path:
    dest = icon_path()
    src = mark_path() if mark_path().exists() else logo_path()
    if not src.exists() or not _stale(dest, src):
        return dest

    from PIL import Image

    im = Image.open(src).convert("RGBA")
    box = im.getbbox()
    if box:
        im = im.crop(box)
    width, height = im.size
    if width > height * 1.4:
        start = int(width * 0.72)
        im = im.crop((start, 0, width, height))
        width, height = im.size
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - width) // 2, (side - height) // 2), im)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)]
    master = canvas.resize((256, 256), Image.Resampling.LANCZOS)
    master.save(dest, format="ICO", sizes=sizes)
    return dest


def ensure_logo_on_dark() -> Path:
    dest = logo_dark_path()
    if dest.exists():
        return dest
    return logo_path()
