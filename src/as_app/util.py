from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def br_date_to_iso(date_text: str) -> str | None:
    text = (date_text or "").strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


def iso_to_br_date(iso_date: str | None) -> str:
    text = (iso_date or "").strip()
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).date().strftime("%d/%m/%Y")
    except ValueError:
        return text


def stable_key(text: str) -> str:
    normalized = (text or "").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
