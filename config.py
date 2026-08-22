"""Load and validate PageMind configuration."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils import app_dir, expand_path

_log = logging.getLogger("pagemind.config")

DEFAULT_PROMPT = (
    "You are PageMind. Answer the actual question on the user's screen in "
    "1–3 short, precise sentences. No preamble."
)


@dataclass(frozen=True)
class Hotkeys:
    screenshot: str
    ocr: str
    dismiss: str
    start: str
    restart: str


@dataclass(frozen=True)
class Config:
    api_key: str
    backup_api_key: str
    model: str
    fallback_models: tuple[str, ...]
    api_base: str
    request_timeout_seconds: int
    hotkeys: Hotkeys
    system_prompt: str
    notification_duration_seconds: int
    clipboard_threshold: int
    screenshot_folder: Path
    log_folder: Path
    source_path: Path


def _as_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 120) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _normalize_hotkey(raw: str, fallback: str) -> str:
    """Accept both '<ctrl>+<shift>+s' and 'ctrl+shift+s'."""
    text = (raw or "").strip().lower()
    if not text:
        return fallback
    if "<" in text:
        return text
    parts = [p.strip() for p in text.replace("-", "+").split("+") if p.strip()]
    if not parts:
        return fallback
    mapped = []
    for part in parts:
        if part in {"ctrl", "control"}:
            mapped.append("<ctrl>")
        elif part in {"shift"}:
            mapped.append("<shift>")
        elif part in {"alt", "option"}:
            mapped.append("<alt>")
        elif part in {"win", "windows", "cmd", "super"}:
            mapped.append("<cmd>")
        else:
            mapped.append(part)
    return "+".join(mapped)


def config_path() -> Path:
    return app_dir() / "config.json"


def example_path() -> Path:
    return app_dir() / "config.example.json"


def ensure_config_file() -> Path:
    """Create config.json from the example on first run."""
    path = config_path()
    if path.exists():
        return path
    src = example_path()
    if src.exists():
        shutil.copyfile(src, path)
    else:
        path.write_text("{}", encoding="utf-8")
    return path


def load_config() -> Config:
    path = ensure_config_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"config.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("config.json must contain a JSON object")

    example: dict[str, Any] = {}
    if example_path().exists():
        try:
            parsed = json.loads(example_path().read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                example = parsed
        except json.JSONDecodeError:
            _log.warning("config.example.json is invalid; using built-in defaults")

    merged = {**example, **data}
    hot = merged.get("hotkeys") or {}
    if not isinstance(hot, dict):
        hot = {}

    api_key = str(merged.get("api_key") or "").strip()
    env_key = os.environ.get("PAGEMIND_API_KEY", "").strip()
    if env_key:
        api_key = env_key
    if api_key.upper().startswith("YOUR_"):
        api_key = ""

    backup_api_key = str(merged.get("backup_api_key") or "").strip()
    env_backup = os.environ.get("PAGEMIND_BACKUP_API_KEY", "").strip()
    if env_backup:
        backup_api_key = env_backup
    if backup_api_key.upper().startswith("YOUR_"):
        backup_api_key = ""
    if backup_api_key and backup_api_key == api_key:
        backup_api_key = ""

    screenshot = _normalize_hotkey(
        str(hot.get("screenshot") or ""),
        "<ctrl>+<alt>+p",
    )
    ocr = _normalize_hotkey(str(hot.get("ocr") or ""), "<ctrl>+<alt>+t")
    dismiss = _normalize_hotkey(str(hot.get("dismiss") or ""), "<ctrl>+<alt>+x")
    start = _normalize_hotkey(str(hot.get("start") or ""), "<ctrl>+<alt>+<shift>+g")
    restart = _normalize_hotkey(str(hot.get("restart") or ""), "<ctrl>+<alt>+r")

    fallbacks_raw = merged.get("fallback_models")
    fallbacks: list[str] = []
    if isinstance(fallbacks_raw, list):
        for item in fallbacks_raw:
            name = str(item).strip()
            if name and name not in fallbacks:
                fallbacks.append(name)
    if not fallbacks:
        fallbacks = [
            "gemini-flash-lite-latest",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
        ]

    cfg = Config(
        api_key=api_key,
        backup_api_key=backup_api_key,
        model=str(merged.get("model") or "gemini-flash-lite-latest").strip(),
        fallback_models=tuple(fallbacks),
        api_base=str(
            merged.get("api_base")
            or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/"),
        request_timeout_seconds=_as_int(
            merged.get("request_timeout_seconds"), 25, minimum=8, maximum=60
        ),
        hotkeys=Hotkeys(
            screenshot=screenshot,
            ocr=ocr,
            dismiss=dismiss,
            start=start,
            restart=restart,
        ),
        system_prompt=str(merged.get("system_prompt") or DEFAULT_PROMPT).strip(),
        notification_duration_seconds=_as_int(
            merged.get("notification_duration_seconds"), 5, minimum=2, maximum=30
        ),
        clipboard_threshold=_as_int(
            merged.get("clipboard_threshold"), 180, minimum=40, maximum=5000
        ),
        screenshot_folder=expand_path(
            str(
                merged.get("screenshot_folder")
                or r"%LOCALAPPDATA%\.cache\syshelper\img"
            )
        ),
        log_folder=expand_path(
            str(merged.get("log_folder") or r"%LOCALAPPDATA%\.cache\syshelper\logs")
        ),
        source_path=path,
    )
    return cfg
