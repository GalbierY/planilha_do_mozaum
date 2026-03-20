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

        return AppConfig(
            app_name=get("app_name", "AS Local (MVP)"),
            db_path=get("db_path", "data/metadata/as_db.json"),
            xlsx_default_path=get("xlsx_default_path", "data/AssistenteSocial.xlsx"),
            xlsx_default_sheet=get("xlsx_default_sheet", "Base2025"),
        )
