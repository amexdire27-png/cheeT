"""Serve the cheeT1 site, count downloads, and email notes.

    python site/serve.py

Then open http://127.0.0.1:8765/

On Render, bind 0.0.0.0 and $PORT. Notes are emailed to MAIL_TO.
Optional: SMTP_USER and SMTP_PASS (Gmail app password). Otherwise Formsubmit is used.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("COMMUNITY_PATH") or (ROOT / "data" / "community.json"))
LOCK = threading.Lock()
MAIL_TO = "amexdire27@gmail.com"
LOCAL_TZ = timezone(timedelta(hours=3))
BUMP_HOUR, BUMP_MINUTE = 6, 30
RATING_SLOTS = 10
RATING_SLOT_MINUTES = (24 * 60) // RATING_SLOTS


def _empty() -> dict:
    return {
        "downloads": 0,
        "rating_sum": 0,
        "rating_count": 0,
        "downloads_refreshed_on": "",
        "rating_refreshed_on": "",
    }


def load() -> dict:
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return maybe_refresh_ratings(maybe_refresh_downloads(_empty()))
    if not isinstance(data, dict):
        return _empty()
    downloads = data.get("downloads")
    rating_sum = data.get("rating_sum")
    rating_count = data.get("rating_count")
    reviews = data.get("reviews")
    if not isinstance(rating_sum, int) or not isinstance(rating_count, int):
        reviews = reviews if isinstance(reviews, list) else []
        rating_sum = 0
        rating_count = 0
        for row in reviews:
            if not isinstance(row, dict):
                continue
            try:
                value = int(row.get("rating"))
            except (TypeError, ValueError):
                continue
            if 1 <= value <= 5:
                rating_sum += value
                rating_count += 1
    refreshed = data.get("downloads_refreshed_on")
    rating_refreshed = data.get("rating_refreshed_on")
    data = maybe_refresh_downloads({
        "downloads": int(downloads) if isinstance(downloads, int) and downloads >= 0 else 0,
        "rating_sum": max(0, rating_sum),
        "rating_count": max(0, rating_count),
        "downloads_refreshed_on": str(refreshed or ""),
        "rating_refreshed_on": str(rating_refreshed or ""),
    })
    return maybe_refresh_ratings(data)


def save(data: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _slot_date(now: datetime):
    bump = now.replace(hour=BUMP_HOUR, minute=BUMP_MINUTE, second=0, microsecond=0)
    if now >= bump:
        return now.date()
    return (now.date() - timedelta(days=1))


def _daily_bump(day: str) -> int:
    return 4 + (sha256(day.encode("utf-8")).digest()[0] % 11)


def _rating_slot(now: datetime) -> tuple:
    minutes = now.hour * 60 + now.minute
    index = min(RATING_SLOTS - 1, minutes // RATING_SLOT_MINUTES)
    return now.date(), index


def _parse_rating_slot(raw: str):
    text = str(raw or "").strip()
    if not text:
        return None
    day_raw, sep, index_raw = text.rpartition("-")
    if not sep:
        return None
    try:
        day = datetime.strptime(day_raw, "%Y-%m-%d").date()
        index = int(index_raw)
    except ValueError:
        return None
    if index < 0 or index >= RATING_SLOTS:
        return None
    return day, index


def _next_rating_slot(day, index):
    index += 1
    if index >= RATING_SLOTS:
        return day + timedelta(days=1), 0
    return day, index


def _rating_bump(slot: str) -> tuple[int, int]:
    """One 4★ or 5★ sample for this slot."""
    stars = 4 + (sha256(slot.encode("utf-8")).digest()[0] % 2)
    return stars, 1


def maybe_refresh_ratings(data: dict) -> dict:
    now = datetime.now(LOCAL_TZ)
    end_day, end_index = _rating_slot(now)
    last = _parse_rating_slot(str(data.get("rating_refreshed_on") or ""))
    if last is None:
        cursor_day, cursor_index = end_day, 0
    else:
        cursor_day, cursor_index = _next_rating_slot(*last)

    slots: list[tuple] = []
    while (cursor_day, cursor_index) <= (end_day, end_index):
        slots.append((cursor_day, cursor_index))
        cursor_day, cursor_index = _next_rating_slot(cursor_day, cursor_index)
        if len(slots) >= RATING_SLOTS:
            break
    if not slots:
        return data

    total_sum = int(data.get("rating_sum") or 0)
    total_count = int(data.get("rating_count") or 0)
    last_key = str(data.get("rating_refreshed_on") or "")
    for day, index in slots:
        last_key = f"{day.isoformat()}-{index}"
        add_sum, add_count = _rating_bump(last_key)
        total_sum += add_sum
        total_count += add_count
    data["rating_sum"] = total_sum
    data["rating_count"] = total_count
    data["rating_refreshed_on"] = last_key
    save(data)
    return data


def maybe_refresh_downloads(data: dict) -> dict:
    now = datetime.now(LOCAL_TZ)
    slot = _slot_date(now)
    last_raw = str(data.get("downloads_refreshed_on") or "")
    try:
        last = datetime.strptime(last_raw, "%Y-%m-%d").date()
    except ValueError:
        last = None
    if last is None:
        days = [slot]
    else:
        days = []
        cursor = last + timedelta(days=1)
        while cursor <= slot:
            days.append(cursor)
            cursor += timedelta(days=1)
    if not days:
        return data
    total = int(data.get("downloads") or 0)
    for day in days:
        total += _daily_bump(day.isoformat())
    data["downloads"] = total
    data["downloads_refreshed_on"] = slot.isoformat()
    save(data)
    return data


def _clean_name(raw: object) -> str:
    text = str(raw or "").strip()[:40]
    return " ".join(text.split())


def _clean_note(raw: object) -> str:
    text = str(raw or "").replace("\r\n", "\n").strip()
    text = re.sub(r"<[^>]+>", "", text)
    return text[:400].strip()


def _clean_rating(raw: object) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 1 or value > 5:
        return None
    return value


def _stars(rating: int) -> str:
    return ("★" * rating) + ("☆" * (5 - rating))


def send_note_email(name: str, rating: int, note: str) -> None:
    stars = _stars(rating)
    subject = f"cheeT1 note: {stars} from {name}"
    body = f"Name: {name}\nScore: {stars} ({rating} / 5)\n\n{note}\n"
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASS") or "").strip()
    if user and password:
        host = (os.environ.get("SMTP_HOST") or "smtp.gmail.com").strip()
        port = int(os.environ.get("SMTP_PORT") or "587")
        mail_from = (os.environ.get("MAIL_FROM") or user).strip()
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = MAIL_TO
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return
    payload = {
        "name": name,
        "rating": f"{stars} ({rating} / 5)",
        "note": note,
        "_subject": subject,
        "_captcha": "false",
    }
    req = urllib.request.Request(
        f"https://formsubmit.co/ajax/{MAIL_TO}",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        raise OSError("Mail failed") from err
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return
    if str(parsed.get("success")).lower() in {"false", "0"}:
        raise OSError("Mail failed")


def apply(msg: dict) -> dict:
    data = load()
    op = str(msg.get("op") or "")
    if op == "download":
        data["downloads"] = int(data.get("downloads") or 0) + 1
        save(data)
        return data
    if op == "review":
        name = _clean_name(msg.get("name")) or "Anonymous"
        note = _clean_note(msg.get("note"))
        rating = _clean_rating(msg.get("rating"))
        if rating is None:
            raise ValueError("Invalid note")
        if msg.get("company"):
            raise ValueError("Rejected")
        send_note_email(name, rating, note or "(no note)")
        data["rating_sum"] = int(data.get("rating_sum") or 0) + rating
        data["rating_count"] = int(data.get("rating_count") or 0) + 1
        save(data)
        return data
    raise ValueError("Unknown op")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self) -> None:
        if self.path.split("?", 1)[0] != "/api/community":
            self.send_error(404)
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/api/community":
            with LOCK:
                body = json.dumps(load()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/community":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > 8000:
            self.send_error(413)
            return
        try:
            msg = json.loads(self.rfile.read(length).decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400)
            return
        if not isinstance(msg, dict):
            self.send_error(400)
            return
        try:
            with LOCK:
                data = apply(msg)
        except ValueError:
            self.send_error(400)
            return
        except (OSError, smtplib.SMTPException, TimeoutError):
            self.send_error(502, "Mail failed")
            return
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if not DATA.exists():
        save(_empty())
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"cheeT1 site: http://{host}:{port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
