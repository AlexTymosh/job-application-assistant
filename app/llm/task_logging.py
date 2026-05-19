from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.storage.app_dirs import resolve_app_data_paths

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
KEY_RE = re.compile(r"sk-[A-Za-z0-9_-]+")


def ai_debug_raw_logging_enabled() -> bool:
    return os.getenv("AI_DEBUG_LOG_RAW_RESPONSES", "false").lower() == "true"


def redact_sensitive_text(value: str) -> str:
    value = EMAIL_RE.sub("[redacted_email]", value)
    value = PHONE_RE.sub("[redacted_phone]", value)
    return KEY_RE.sub("[redacted_key]", value)


class AiTaskLogger:
    def __init__(self) -> None:
        paths = resolve_app_data_paths()
        self.log_dir = paths.logs_dir / "ai-tasks"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, record: dict[str, Any]) -> Path:
        record = dict(record)
        record.setdefault("timestamp", datetime.now(UTC).isoformat())
        if not ai_debug_raw_logging_enabled():
            record.pop("raw_response", None)
            record.pop("safe_payload", None)
        serialised = redact_sensitive_text(json.dumps(record, ensure_ascii=False))
        target = self.log_dir / f"ai-tasks-{datetime.now(UTC).date().isoformat()}.jsonl"
        with target.open("a", encoding="utf-8") as fh:
            fh.write(serialised + "\n")
        return target
