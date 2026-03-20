from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store import ImportResult, JsonStore, build_external_key
from .util import br_date_to_iso, now_iso
from .xlsx_reader import read_xlsx_table


def _parse_int(text: Any) -> int | None:
    s = ("" if text is None else str(text)).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def import_from_xlsx(*, store: JsonStore, xlsx_path: Path, sheet_name: str) -> ImportResult:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"XLSX não encontrado: {xlsx_path}")

    rows = read_xlsx_table(xlsx_path, sheet_name)
    batch_id = str(uuid.uuid4())
    imported_at = now_iso()

    db = store.load()
    alunos: list[dict[str, Any]] = list(db.get("alunos") or [])

    by_key = {a.get("external_key"): a for a in alunos if a.get("external_key")}

    inserted = updated = skipped = 0
    for r in rows:
        nome = (r.get("Aluno") or "").strip()
        if not nome:
            skipped += 1
            continue

        escola = (r.get("Escola") or "").strip()
        birth_iso = br_date_to_iso((r.get("Data de nascimento") or "").strip())
        ext_key = build_external_key(nome, birth_iso, escola)

        child = {
            "external_key": ext_key,
            "nome": nome,
            "idade": _parse_int(r.get("Idade")),
            "escola": escola,
            "data_nascimento": birth_iso,
            "atendimento_realizado": r.get("Atendimento realizado") or "",
            "vd": r.get("VD") or "",
            "imported_at": imported_at,
            "source": {
                "type": "xlsx",
                "file": xlsx_path.name,
                "sheet": sheet_name,
                "row": int(r.get("__row") or 0),
                "batch": batch_id,
            },
        }

        existing = by_key.get(ext_key)
        if existing is None:
            created = now_iso()
            child["id"] = str(uuid.uuid4())
            child["created_at"] = created
            child["updated_at"] = created
            alunos.append(child)
            by_key[ext_key] = child
            inserted += 1
            continue

        for k, v in child.items():
            if k in {"id", "created_at"}:
                continue
            existing[k] = v
        existing["updated_at"] = now_iso()
        updated += 1

    db["alunos"] = alunos
    db.setdefault("import_batches", []).append(
        {
            "id": batch_id,
            "imported_at": imported_at,
            "file": xlsx_path.name,
            "sheet": sheet_name,
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }
    )
    store.save(db)

    return ImportResult(
        batch_id=batch_id,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        total=len(rows),
    )
