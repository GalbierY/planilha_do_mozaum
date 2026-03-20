from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def create_backup(*, db_path: Path, attachments_dir: Path, backups_dir: Path) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = backups_dir / f"backup_{ts}.zip"

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if db_path.exists():
            z.write(db_path, arcname="as_db.json")
        if attachments_dir.exists():
            for p in attachments_dir.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=str(Path("attachments") / p.relative_to(attachments_dir)))
    return out


def restore_backup(*, backup_zip: Path, db_path: Path, attachments_dir: Path) -> None:
    if not backup_zip.exists():
        raise FileNotFoundError(str(backup_zip))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with zipfile.ZipFile(backup_zip, "r") as z:
            z.extractall(tmp)

        new_db = tmp / "as_db.json"
        new_attachments = tmp / "attachments"
        if not new_db.exists():
            raise ValueError("Backup inválido: as_db.json não encontrado.")

        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(new_db, db_path)

        if attachments_dir.exists():
            shutil.rmtree(attachments_dir)
        if new_attachments.exists():
            shutil.copytree(new_attachments, attachments_dir)
