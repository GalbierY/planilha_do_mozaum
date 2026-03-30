from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_UI_LANGUAGE = "pt-BR"


def normalize_language(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in {"en", "en-us", "en-gb", "english"}:
        return "en"
    return DEFAULT_UI_LANGUAGE


@dataclass
class AppConfig:
    app_name: str
    app_version: str
    db_path: str
    xlsx_default_path: str
    xlsx_default_sheet: str
    auto_update_enabled: bool
    update_check_minutes: int
    attachments_dir: str
    exports_dir: str
    backups_dir: str
    ui_language: str

    @staticmethod
    def _config_path(app_root: Path) -> Path:
        return app_root / "config" / "config.json"

    @staticmethod
    def load(app_root: Path) -> "AppConfig":
        config_path = AppConfig._config_path(app_root)
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
            app_name=get("app_name", "SAS Civitas"),
            app_version=get("app_version", "0.0.0"),
            db_path=get("db_path", "data/metadata/as_db.json"),
            xlsx_default_path=get("xlsx_default_path", "data/AssistenteSocial.xlsx"),
            xlsx_default_sheet=get("xlsx_default_sheet", "Base2025"),
            auto_update_enabled=get_bool("auto_update_enabled", True),
            update_check_minutes=max(1, get_int("update_check_minutes", 5)),
            attachments_dir=get("attachments_dir", "data/attachments"),
            exports_dir=get("exports_dir", "data/exports"),
            backups_dir=get("backups_dir", "data/backups"),
            ui_language=normalize_language(get("ui_language", DEFAULT_UI_LANGUAGE)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "db_path": self.db_path,
            "xlsx_default_path": self.xlsx_default_path,
            "xlsx_default_sheet": self.xlsx_default_sheet,
            "auto_update_enabled": self.auto_update_enabled,
            "update_check_minutes": self.update_check_minutes,
            "attachments_dir": self.attachments_dir,
            "exports_dir": self.exports_dir,
            "backups_dir": self.backups_dir,
            "ui_language": normalize_language(self.ui_language),
        }

    def save(self, app_root: Path) -> None:
        config_path = self._config_path(app_root)
        raw: dict[str, Any] = {}
        if config_path.exists():
            try:
                loaded = json.loads(config_path.read_text(encoding="utf-8") or "{}")
                if isinstance(loaded, dict):
                    raw = loaded
            except Exception:
                raw = {}
        raw.update(self.to_dict())
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
