from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_ID = "SAS Civitas"
LEGACY_APP_ID = "SAS_Civitas"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_resource_root() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    # repo root: <repo>/src/as_app/runtime.py -> parents[2] == <repo>
    return Path(__file__).resolve().parents[2]


def get_user_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return (Path(base) / APP_ID / "UserData").resolve()
    return (Path.home() / APP_ID / "UserData").resolve()


def get_legacy_user_data_root() -> Path | None:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        return None
    return (Path(base) / LEGACY_APP_ID / "UserData").resolve()


def _copy_tree_missing(src: Path, dst: Path) -> None:
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)


def get_data_root(resource_root: Path) -> Path:
    override = (os.environ.get("SAS_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return get_user_data_root()
    return resource_root


def ensure_user_files(resource_root: Path, data_root: Path) -> None:
    # Migration: older builds used "%LOCALAPPDATA%\\SAS_Civitas\\UserData".
    legacy = get_legacy_user_data_root()
    new_db = data_root / "data" / "metadata" / "as_db.json"
    if (not new_db.exists()) and legacy and legacy.exists():
        _copy_tree_missing(legacy, data_root)

    # Seed config for user-editable settings (installed builds cannot edit inside the EXE).
    src_cfg = resource_root / "config" / "config.json"
    dst_cfg = data_root / "config" / "config.json"
    if src_cfg.exists() and (not dst_cfg.exists()):
        dst_cfg.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_cfg, dst_cfg)

    # Seed the XLSX template (default base sheet).
    src_xlsx = resource_root / "data" / "AssistenteSocial.xlsx"
    dst_xlsx = data_root / "data" / "AssistenteSocial.xlsx"
    if src_xlsx.exists() and (not dst_xlsx.exists()):
        dst_xlsx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_xlsx, dst_xlsx)
