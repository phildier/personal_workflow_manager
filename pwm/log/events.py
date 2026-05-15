from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


LOG_DIR = Path.home() / ".config" / "pwm"
LOG_FILE = LOG_DIR / "log.jsonl"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

TRIM_KEYS = {
    "body",
    "description",
    "message",
}

REDACT_KEYS = {
    "token",
    "api_key",
    "authorization",
    "password",
    "secret",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _normalize_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_value(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(v, key) for v in value]

    if isinstance(value, str):
        lower_key = (key or "").lower()
        if any(sensitive in lower_key for sensitive in REDACT_KEYS):
            return "<redacted>"
        if lower_key in TRIM_KEYS and len(value) > 120:
            return f"{value[:120]}..."
        if len(value) > 500:
            return f"{value[:500]}..."
        return value

    return value


def _rotate_if_needed(max_bytes: int) -> None:
    if not LOG_FILE.exists():
        return
    if LOG_FILE.stat().st_size < max_bytes:
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    rotated = LOG_DIR / f"log-{ts}.jsonl"
    LOG_FILE.rename(rotated)


def append_event(
    command: str,
    args: dict,
    details: dict | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> None:
    """Append a command event to ~/.config/pwm/log.jsonl.

    This function is best-effort and never raises.
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(max_bytes)

        row = {
            "timestamp": _now_iso(),
            "command": command,
            "args": _normalize_value(args),
            "details": _normalize_value(details or {}),
        }

        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")))
            f.write("\n")
    except Exception:
        return
