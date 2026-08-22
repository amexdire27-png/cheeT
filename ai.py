"""Gemini Flash client — classify the page, then answer."""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests
from PIL import Image

from config import Config
from utils import AbortError, AppError, redact

_log = logging.getLogger("pagemind.ai")

CLIPBOARD_TYPES = frozenset({"short_answer", "code"})
KNOWN_TYPES = frozenset({"short_answer", "code", "true_false", "other"})

TYPE_ALIASES = {
    "short": "short_answer",
    "shortanswer": "short_answer",
    "short-answer": "short_answer",
    "fill_in": "short_answer",
    "fill-in": "short_answer",
    "numeric": "short_answer",
    "write_code": "code",
    "coding": "code",
    "program": "code",
    "programming": "code",
    "snippet": "code",
    "truefalse": "true_false",
    "true-false": "true_false",
    "true/false": "true_false",
    "boolean": "true_false",
    "yes_no": "true_false",
    "yes/no": "true_false",
    "tf": "true_false",
    "mixed": "short_answer",  # also injects code below
    "multiple_choice": "other",
    "mcq": "other",
}

OUTPUT_CONTRACT = """
Classify the question on the page, then answer it.

Return JSON only (no markdown, no extra keys):
{"types": ["..."], "answer": "..."}

types — include every label that applies:
- "true_false": True/False, Yes/No, T/F, Correct/Incorrect.
- "code": write a program, function, class, SQL, HTML/CSS, algorithm, or complete a snippet.
- "short_answer": fill-in-the-blank, one word/phrase/number/formula the user would TYPE or PASTE into a box.
- "other": multiple choice, matching, explain, article, error, docs, or anything meant to be read rather than pasted.
If the task is BOTH a short typed answer AND writing code, set types to ["short_answer", "code"].

answer:
- true_false: only True or False (Yes or No if the question uses that wording).
- short_answer: only the paste-ready value. No sentence wrapper.
- code: only the paste-ready source. No markdown fences, no explanation.
- short_answer + code: paste-ready payload (short value then the code, or the full solution they would submit).
- other: glanceable toast text — option letter first for MCQ, else 1–3 short sentences.
"""

SCREENSHOT_HINT = (
    "This is a screenshot of the user's active window (often a browser). "
    "Classify the question type, then answer it."
)

OCR_IMAGE_HINT = (
    "Read the text in this screenshot (OCR), then classify the question "
    "type and answer it. Ignore chrome/toolbars unless they are the subject."
)

OCR_TEXT_HINT = (
    "The following text was extracted from the user's active window. "
    "It may be noisy. Classify the question type, then answer it."
)


@dataclass(frozen=True)
class Analysis:
    types: tuple[str, ...]
    answer: str

    @property
    def copy_to_clipboard(self) -> bool:
        return bool(CLIPBOARD_TYPES.intersection(self.types))

_MAX_INLINE_BYTES = 1_200_000
_MAX_EDGE = 1280


def _prepare_image(image_bytes: bytes) -> tuple[str, str]:
    """Return (mime_type, base64). Prefer already-compact JPEG from capture."""
    if image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg", base64.b64encode(image_bytes).decode("ascii")

    if len(image_bytes) <= _MAX_INLINE_BYTES and image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", base64.b64encode(image_bytes).decode("ascii")

    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")

    width, height = image.size
    scale = min(1.0, _MAX_EDGE / max(width, height))
    if scale < 1.0:
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.BILINEAR,
        )

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=72, subsampling=2)
    jpeg = buffer.getvalue()
    _log.info("Compressed screenshot %s -> %s bytes for API", len(image_bytes), len(jpeg))
    return "image/jpeg", base64.b64encode(jpeg).decode("ascii")


def _extract_text(payload: dict[str, Any]) -> str:
    prompt_feedback = payload.get("promptFeedback") or {}
    block = prompt_feedback.get("blockReason")
    if block:
        raise AppError(
            f"Gemini blocked the prompt ({block})",
            user_message="Gemini declined this screen",
        )

    candidates = payload.get("candidates") or []
    if not candidates:
        raise AppError(
            "Gemini returned no candidates",
            user_message="Gemini returned an empty answer",
        )

    finish = (candidates[0] or {}).get("finishReason")
    if finish in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
        raise AppError(
            f"Gemini stopped ({finish})",
            user_message="Gemini declined this screen",
        )

    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise AppError(
            "Gemini returned empty text",
            user_message="Gemini returned an empty answer",
        )
    return text


def _normalize_type(raw: str) -> str:
    key = re.sub(r"[^a-z/]+", "_", (raw or "").strip().lower()).strip("_")
    key = key.replace("/", "_")
    if key in KNOWN_TYPES:
        return key
    if key in TYPE_ALIASES:
        return TYPE_ALIASES[key]
    compact = key.replace("_", "")
    return TYPE_ALIASES.get(compact, "other")


def _parse_analysis(raw: str) -> Analysis:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    data: Any = None
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        _log.warning("Gemini did not return JSON; treating as other")
        return Analysis(types=("other",), answer=text)

    types_raw = data.get("types") or data.get("type") or data.get("kind") or []
    if isinstance(types_raw, str):
        types_raw = [types_raw]
    if not isinstance(types_raw, list):
        types_raw = []

    types: list[str] = []
    for item in types_raw:
        label = _normalize_type(str(item))
        if label == "short_answer" and str(item).strip().lower() in {"mixed", "both"}:
            types.extend(["short_answer", "code"])
            continue
        if label not in types:
            types.append(label)
    if not types:
        types = ["other"]

    answer = str(data.get("answer") or data.get("text") or "").strip()
    if not answer:
        raise AppError(
            "Gemini JSON had no answer",
            user_message="Gemini returned an empty answer",
        )
    # Code answers sometimes still arrive wrapped in fences.
    if "code" in types:
        answer = re.sub(r"^```(?:\w+)?\s*", "", answer)
        answer = re.sub(r"\s*```$", "", answer).strip()
    return Analysis(types=tuple(types), answer=answer)


def _user_error(status: int, body: str) -> AppError:
    lowered = body.lower()
    if status == 401 or status == 403 or "api key" in lowered or "permission" in lowered:
        return AppError(
            f"Gemini auth error HTTP {status}",
            user_message="Gemini API key was rejected",
        )
    if status == 404:
        return AppError(
            f"Gemini model not found HTTP {status}",
            user_message="Gemini model was not found",
        )
    if status == 429 or "resource_exhausted" in lowered or "quota" in lowered:
        return AppError(
            f"Gemini rate limit HTTP {status}",
            user_message="Gemini is rate-limited — try again shortly",
        )
    if status >= 500:
        return AppError(
            f"Gemini server error HTTP {status}",
            user_message="Gemini is temporarily unavailable",
        )
    return AppError(
        f"Gemini HTTP {status}: {body[:300]}",
        user_message="Gemini request failed",
    )


def _key_exhausted(status: int, body: str) -> bool:
    """True when this key is rejected or out of quota — try the backup."""
    if status in {401, 403, 429}:
        return True
    lowered = body.lower()
    return "resource_exhausted" in lowered or "quota" in lowered


class GeminiClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._active_key = ""
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._session = self._new_session()

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = False
        session.headers.update({"Content-Type": "application/json"})
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=4, pool_maxsize=4, max_retries=0
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def reset_cancel(self) -> None:
        self._cancelled.clear()
        with self._lock:
            try:
                closed = getattr(self._session, "closed", False)
            except Exception:
                closed = True
            if closed:
                self._session = self._new_session()

    def abort(self) -> None:
        """Drop the in-flight HTTP request so Abort can return immediately."""
        self._cancelled.set()
        with self._lock:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = self._new_session()

    @property
    def cancelled(self) -> threading.Event:
        return self._cancelled

    def close(self) -> None:
        with self._lock:
            self._session.close()

    def _raise_if_aborted(self) -> None:
        if self._cancelled.is_set():
            raise AbortError()

    def _keys(self) -> list[str]:
        return list(self.cfg.api_keys)

    def _ordered_keys(self) -> list[str]:
        keys = self._keys()
        if self._active_key in keys:
            return keys[keys.index(self._active_key) :]
        return keys

    def _key_label(self, key: str) -> str:
        try:
            return f"key{self.cfg.api_keys.index(key) + 1}"
        except ValueError:
            return "key"

    def _apply_key(self, key: str) -> None:
        self._session.headers["X-goog-api-key"] = key

    def _models(self) -> list[str]:
        names: list[str] = []
        for name in (self.cfg.model, *self.cfg.fallback_models):
            trimmed = (name or "").strip()
            if trimmed and trimmed not in names:
                names.append(trimmed)
        return names

    def _url(self, model: str) -> str:
        return f"{self.cfg.api_base}/models/{model}:generateContent"

    def _generate(self, parts: list[dict[str, Any]], extra_hint: str) -> Analysis:
        keys = self._ordered_keys()
        if not keys:
            raise AppError(
                "Missing API key",
                user_message="Add your Gemini API key in config.json",
            )

        generation = {
            "temperature": 0.1,
            "topP": 0.8,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        }
        body = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "\n\n".join(
                            [self.cfg.system_prompt, OUTPUT_CONTRACT, extra_hint]
                        )
                    }
                ]
            },
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation,
        }
        timeout = (8.0, float(self.cfg.request_timeout_seconds))
        last_error: Exception | None = None
        dropped_json_mime = False

        for key_index, key in enumerate(keys):
            self._raise_if_aborted()
            self._apply_key(key)
            params = {"key": key}
            label = self._key_label(key)
            has_backup = key_index < len(keys) - 1
            switch_key = False

            for model in self._models():
                self._raise_if_aborted()
                for attempt in range(3):
                    self._raise_if_aborted()
                    _log.info(
                        "Gemini request key=%s model=%s attempt=%s",
                        label,
                        model,
                        attempt + 1,
                    )
                    try:
                        with self._lock:
                            session = self._session
                        response = session.post(
                            self._url(model),
                            params=params,
                            json=body,
                            timeout=timeout,
                        )
                    except requests.Timeout as exc:
                        self._raise_if_aborted()
                        last_error = exc
                        _log.warning("%s timed out (attempt %s)", model, attempt + 1)
                        break
                    except requests.RequestException as exc:
                        self._raise_if_aborted()
                        last_error = exc
                        _log.warning("Network error on %s: %s", model, exc)
                        time.sleep(0.35 * (attempt + 1))
                        continue

                    if response.status_code in {429, 500, 502, 503}:
                        last_error = _user_error(response.status_code, response.text)
                        if has_backup and _key_exhausted(
                            response.status_code, response.text
                        ):
                            _log.warning(
                                "%s HTTP %s on %s — switching to the next key",
                                model,
                                response.status_code,
                                label,
                            )
                            switch_key = True
                            break
                        wait = min(2.0, 0.4 * (2**attempt))
                        _log.warning(
                            "%s HTTP %s — retry in %.1fs",
                            model,
                            response.status_code,
                            wait,
                        )
                        time.sleep(wait)
                        continue

                    if response.status_code == 404:
                        last_error = _user_error(response.status_code, response.text)
                        _log.warning("Model %s not found — trying fallback", model)
                        break

                    if response.status_code == 400:
                        lowered = response.text.lower()
                        retry_same = False
                        if not dropped_json_mime and "mimetype" in lowered:
                            dropped_json_mime = True
                            generation.pop("responseMimeType", None)
                            retry_same = True
                        if "thinking" in lowered or "invalid argument" in lowered:
                            if generation.pop("thinkingConfig", None) is not None:
                                retry_same = True
                        if retry_same:
                            body["generationConfig"] = generation
                            _log.warning(
                                "Adjusted generationConfig after HTTP 400; retrying"
                            )
                            continue

                    if response.status_code >= 400:
                        snippet = redact(response.text[:800], *keys)
                        _log.error("Gemini HTTP %s: %s", response.status_code, snippet)
                        last_error = _user_error(response.status_code, response.text)
                        if has_backup and _key_exhausted(
                            response.status_code, response.text
                        ):
                            _log.warning(
                                "%s rejected (HTTP %s) — switching to the next key",
                                label,
                                response.status_code,
                            )
                            switch_key = True
                            break
                        if response.status_code in {401, 403}:
                            raise last_error
                        break

                    try:
                        payload = response.json()
                    except ValueError as exc:
                        last_error = AppError(
                            "Gemini returned non-JSON",
                            user_message="Failed",
                        )
                        last_error.__cause__ = exc
                        continue

                    analysis = _parse_analysis(_extract_text(payload))
                    self._active_key = key
                    _log.info(
                        "Classified as %s (%s chars) via %s (%s key)",
                        ",".join(analysis.types),
                        len(analysis.answer),
                        model,
                        label,
                    )
                    return analysis
                if switch_key:
                    break
            if switch_key:
                self._active_key = keys[key_index + 1]
                continue

        if isinstance(last_error, AppError):
            last_error.user_message = "Failed"
            raise last_error
        raise AppError(
            f"Gemini failed: {last_error}",
            user_message="Failed",
        )

    def ask_image(self, image_bytes: bytes, *, ocr_mode: bool = False) -> Analysis:
        mime, encoded = _prepare_image(image_bytes)
        hint = OCR_IMAGE_HINT if ocr_mode else SCREENSHOT_HINT
        parts = [
            {"text": hint},
            {"inlineData": {"mimeType": mime, "data": encoded}},
        ]
        return self._generate(parts, hint)

    def ask_text(self, window_text: str) -> Analysis:
        parts = [{"text": f"{OCR_TEXT_HINT}\n\n---\n{window_text}"}]
        return self._generate(parts, OCR_TEXT_HINT)
