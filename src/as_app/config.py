from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    db_path: str
    xlsx_default_path: str
    xlsx_default_sheet: str
    auto_update_enabled: bool
    update_check_minutes: int
    attachments_dir: str
    exports_dir: str
    backups_dir: str

    @staticmethod
    def load(app_root: Path) -> "AppConfig":
        config_path = app_root / "config" / "config.json"
        raw: dict = {}
        if config_path.exists():
            raw = json.loads(config_path.read_text(encoding="utf-8") or "{}")

        def get(key: str, default: str) -> str:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            return default

        def get_bool(key: str, default: bool) -> bool:
            value = raw.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                v = value.strip().lower()
                if v in {"1", "true", "yes", "y", "sim"}:
                    return True
                if v in {"0", "false", "no", "n", "nao", "não"}:
                    return False
            return default

        def get_int(key: str, default: int) -> int:
            value = raw.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value.strip())
                except ValueError:
                    return default
            return default

        return AppConfig(
            app_name=get("app_name", "AS Local (MVP)"),
            db_path=get("db_path", "data/metadata/as_db.json"),
            xlsx_default_path=get("xlsx_default_path", "data/AssistenteSocial.xlsx"),
            xlsx_default_sheet=get("xlsx_default_sheet", "Base2025"),
            auto_update_enabled=get_bool("auto_update_enabled", True),
            update_check_minutes=max(1, get_int("update_check_minutes", 5)),
            attachments_dir=get("attachments_dir", "data/attachments"),
            exports_dir=get("exports_dir", "data/exports"),
            backups_dir=get("backups_dir", "data/backups"),
        )
