from __future__ import annotations

import shutil
import uuid
from pathlib import Path


def store_attachment(*, src_path: Path, attachments_dir: Path, attendance_id: str) -> Path:
    attachments_dir.mkdir(parents=True, exist_ok=True)
    folder = attachments_dir / attendance_id
    folder.mkdir(parents=True, exist_ok=True)

    suffix = src_path.suffix
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = folder / safe_name
    shutil.copy2(src_path, dest)
    return dest
