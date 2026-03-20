from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .util import now_iso, stable_key, write_json_atomic


@dataclass
class ImportResult:
    batch_id: str
    inserted: int
    updated: int
    skipped: int
    total: int


class JsonStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _empty_db(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "generated_at": now_iso(),
            "alunos": [],
            "import_batches": [],
        }

    def load(self) -> dict[str, Any]:
        if not self.db_path.exists():
            db = self._empty_db()
            write_json_atomic(self.db_path, db)
            return db
        text = self.db_path.read_text(encoding="utf-8")
        if not text.strip():
            db = self._empty_db()
            write_json_atomic(self.db_path, db)
            return db
        return json.loads(text)

    def save(self, db: dict[str, Any]) -> None:
        db["generated_at"] = now_iso()
        write_json_atomic(self.db_path, db)

    def list_children(self) -> list[dict[str, Any]]:
        db = self.load()
        alunos = list(db.get("alunos") or [])
        alunos.sort(key=lambda a: (a.get("nome") or "").lower())
        return alunos

    def upsert_child(self, child: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        db = self.load()
        alunos: list[dict[str, Any]] = list(db.get("alunos") or [])

        existing = None
        child_id = (child.get("id") or "").strip()
        if child_id:
            existing = next((a for a in alunos if a.get("id") == child_id), None)
        if existing is None:
            ext = (child.get("external_key") or "").strip()
            if ext:
                existing = next((a for a in alunos if a.get("external_key") == ext), None)

        if existing is None:
            new_id = str(uuid.uuid4())
            created = now_iso()
            child = {**child}
            child["id"] = new_id
            child["created_at"] = created
            child["updated_at"] = created
            child.setdefault("source", {"type": "manual"})
            alunos.append(child)
            db["alunos"] = alunos
            self.save(db)
            return "inserted", child

        incoming_source_type = ((child.get("source") or {}).get("type") or "").strip()
        existing_source_type = ((existing.get("source") or {}).get("type") or "").strip()
        skip = {"id", "created_at"}
        if incoming_source_type == "manual" and existing_source_type == "xlsx":
            skip |= {"source", "imported_at"}

        for k, v in child.items():
            if k in skip:
                continue
            existing[k] = v
        existing["updated_at"] = now_iso()

        db["alunos"] = alunos
        self.save(db)
        return "updated", existing

    def new_child_from_form(
        self,
        *,
        child_id: str | None,
        nome: str,
        idade: str,
        escola: str,
        data_nascimento_iso: str | None,
        atendimento: str,
        vd: str,
    ) -> dict[str, Any]:
        age = None
        idade = (idade or "").strip()
        if idade:
            try:
                age = int(idade)
            except ValueError:
                age = None

        nome = (nome or "").strip()
        escola = (escola or "").strip()
        birth = (data_nascimento_iso or "").strip()
        seed = f"{nome}|{birth}|{escola}".lower()
        ext = stable_key(seed) if seed.replace("|", "").strip() else None

        return {
            "id": (child_id or "").strip() or None,
            "external_key": ext,
            "nome": nome,
            "idade": age,
            "escola": escola,
            "data_nascimento": birth or None,
            "atendimento_realizado": atendimento or "",
            "vd": vd or "",
            "source": {"type": "manual"},
        }


def build_external_key(nome: str, birth_iso: str | None, escola: str) -> str:
    seed = f"{(nome or '').strip()}|{(birth_iso or '').strip()}|{(escola or '').strip()}".lower()
    return stable_key(seed)
