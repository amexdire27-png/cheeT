"""Serve the cheeT1 site, count downloads, and email notes.

    python site/serve.py

Then open http://127.0.0.1:8765/

On Render, bind 0.0.0.0 and $PORT. Notes go to MAIL_TO via Resend
(RESEND_API_KEY), then SMTP if set, otherwise Formsubmit.
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("COMMUNITY_PATH") or (ROOT / "data" / "community.json"))
LOCK = threading.Lock()
MAIL_TO = "amexdire27@gmail.com"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, _, value = text.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()


def _mail_ready() -> bool:
    return bool((os.environ.get("RESEND_API_KEY") or "").strip())


def public_state(data: dict, mail_ok: bool | None = None) -> dict:
    out = {
        "downloads": int(data.get("downloads") or 0),
        "rating_sum": int(data.get("rating_sum") or 0),
        "rating_count": int(data.get("rating_count") or 0),
        "mail_ready": _mail_ready(),
    }
    if mail_ok is not None:
        out["mail_ok"] = mail_ok
    return out
    return {"downloads": 0, "rating_sum": 0, "rating_count": 0}


def load() -> dict:
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
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
    return {
        "downloads": int(downloads) if isinstance(downloads, int) and downloads >= 0 else 0,
        "rating_sum": max(0, rating_sum),
        "rating_count": max(0, rating_count),
    }


def save(data: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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
    import html as html_lib

    import resend

    stars = _stars(rating)
    subject = f"cheeT1 note: {stars} from {name}"
    body = f"Name: {name}\nScore: {stars} ({rating} / 5)\n\n{note}\n"
    safe_note = html_lib.escape(note).replace("\n", "<br>")
    safe_name = html_lib.escape(name)
    resend_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if not resend_key:
        raise OSError("RESEND_API_KEY is not set")

    resend.api_key = resend_key
    params = {
        "from": (os.environ.get("RESEND_FROM") or "onboarding@resend.dev").strip(),
        "to": [MAIL_TO],
        "subject": subject,
        "html": (
            f"<p><strong>Name:</strong> {safe_name}</p>"
            f"<p><strong>Score:</strong> {stars} ({rating} / 5)</p>"
            f"<p>{safe_note}</p>"
        ),
    }
    result = resend.Emails.send(params)
    email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
    if not email_id:
        raise OSError(f"Mail failed: {result}")
    print(f"Resend sent {email_id}", flush=True)


def apply(msg: dict) -> dict:
    data = load()
    op = str(msg.get("op") or "")
    if op == "download":
        data["downloads"] = int(data.get("downloads") or 0) + 1
        save(data)
        return public_state(data)
    if op == "review":
        name = _clean_name(msg.get("name")) or "Anonymous"
        note = _clean_note(msg.get("note"))
        rating = _clean_rating(msg.get("rating"))
        if rating is None:
            raise ValueError("Invalid note")
        if msg.get("company"):
            raise ValueError("Rejected")
        data["rating_sum"] = int(data.get("rating_sum") or 0) + rating
        data["rating_count"] = int(data.get("rating_count") or 0) + 1
        save(data)
        try:
            send_note_email(name, rating, note or "(no note)")
            return public_state(data, True)
        except Exception as exc:
            print(f"Mail failed: {exc}", flush=True)
            return public_state(data, False)
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
                body = json.dumps(public_state(load())).encode("utf-8")
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
    if (os.environ.get("RESEND_API_KEY") or "").strip():
        print("Mail: Resend ready", flush=True)
    else:
        print("Mail: RESEND_API_KEY missing — notes will not appear in Resend", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
