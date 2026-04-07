from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .store import ImportResult, JsonStore, build_external_key
from .util import br_date_to_iso, now_iso, stable_key
from .xlsx_reader import read_xlsx_table, list_sheet_names



def _parse_int(text: Any) -> int | None:
    s = ("" if text is None else str(text)).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _resolve_sheet_name(xlsx_path: Path, preferred_sheet: str) -> str:
    """Tenta encontrar uma aba adequada, mesmo se o nome exato tiver mudado.

    Estratégia:
    - Se `preferred_sheet` existir, usa ela.
    - Senão, procura uma aba que comece com o mesmo prefixo (ex.: "Base").
    - Se ainda não achar, usa a primeira aba disponível.
    """
    available = list_sheet_names(xlsx_path)
    if not available:
        raise ValueError("Nenhuma aba encontrada no XLSX.")

    # Se a preferida ainda existe, usa
    for name in available:
        if name.strip().lower() == (preferred_sheet or "").strip().lower():
            return name

    # Tentar casar por prefixo (ex.: Base2025, Base2025-2026)
    base_pref = (preferred_sheet or "").strip()
    base_pref_lower = base_pref.lower()

    # Se começa com letras (ex.: "Base"), usar esse prefixo
    prefix = ""  # exemplo: "base"
    for ch in base_pref_lower:
        if ch.isalpha():
            prefix += ch
        else:
            break
    prefix = prefix.strip()

    if prefix:
        for name in available:
            if name.strip().lower().startswith(prefix):
                return name

    # Fallback: primeira aba
    return available[0]


def import_from_xlsx(*, store: JsonStore, xlsx_path: Path, sheet_name: str, validate_workflow: bool = False) -> ImportResult:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"XLSX não encontrado: {xlsx_path}")

    # Resolver nome real da aba caso tenha mudado (ex.: Base2025 -> Base2025-2026)
    resolved_sheet_name = _resolve_sheet_name(xlsx_path, sheet_name)

    # Validação de workflow
    if validate_workflow:
        db = store.load()
        children = list(db.get("children") or [])
        pending_children = [c for c in children if not c.get("workflow_status", False)]
        if pending_children:
            raise ValueError(
                f"Existem {len(pending_children)} crianças pendentes no workflow:\n" +
                "\n".join([f"  - {c['nome']} ({c['escola']})" for c in pending_children])
            )

    rows = read_xlsx_table(xlsx_path, resolved_sheet_name)
    batch_id = str(uuid.uuid4())
    imported_at = now_iso()

    db = store.load()
    children: list[dict[str, Any]] = list(db.get("children") or [])
    attendances: list[dict[str, Any]] = list(db.get("attendances") or [])

    by_child_key = {a.get("external_key"): a for a in children if a.get("external_key")}
    by_att_key = {a.get("external_key"): a for a in attendances if a.get("external_key")}

    inserted = updated = skipped = 0
    for r in rows:
        nome = (r.get("Aluno") or "").strip()
        if not nome:
            skipped += 1
            continue

        escola = (r.get("Escola") or "").strip()
        birth_iso = br_date_to_iso((r.get("Data de nascimento") or "").strip())
        ext_key = build_external_key(nome, birth_iso, escola)

        source = {
            "type": "xlsx",
            "file": xlsx_path.name,
            "sheet": resolved_sheet_name,
            "row": int(r.get("__row") or 0),
            "batch": batch_id,
        }

        child_fields = {
            "external_key": ext_key,
            "nome": nome,
            "idade": _parse_int(r.get("Idade")),
            "escola": escola,
            "data_nascimento": birth_iso,
            "imported_at": imported_at,
            "source": source,
            "workflow_status": False,  # Novo campo: False = vermelho (pendente), True = verde (concluído)
        }

        existing_child = by_child_key.get(ext_key)
        if existing_child is None:
            created = now_iso()
            new_child = dict(child_fields)
            new_child["id"] = str(uuid.uuid4())
            new_child["created_at"] = created
            new_child["updated_at"] = created
            children.append(new_child)
            by_child_key[ext_key] = new_child
            inserted += 1
            child_id = new_child["id"]
        else:
            for k, v in child_fields.items():
                if k in {"created_at", "id"}:
                    continue
                existing_child[k] = v
            existing_child["updated_at"] = now_iso()
            updated += 1
            child_id = existing_child.get("id")

        atendimento_text = (r.get("Atendimento realizado") or "").strip()
        vd_text = (r.get("VD") or "").strip()
        if atendimento_text or vd_text:
            att_ext = stable_key(f"xlsx|{xlsx_path.name}|{resolved_sheet_name}|{source['row']}|{ext_key}")
            attendance_fields = {
                "external_key": att_ext,
                "child_id": child_id,
                "occurred_at": imported_at,
                "tipo": "importado",
                "profissional": "",
                "registrado_por": "import",
                "resultado": "",
                "atendimento_text": atendimento_text,
                "vd_text": vd_text,
                "source": source,
            }

            existing_att = by_att_key.get(att_ext)
            if existing_att is None:
                created = now_iso()
                new_att = dict(attendance_fields)
                new_att["id"] = str(uuid.uuid4())
                new_att["created_at"] = created
                new_att["updated_at"] = created
                attendances.append(new_att)
                by_att_key[att_ext] = new_att
            else:
                for k, v in attendance_fields.items():
                    if k in {"id", "created_at"}:
                        continue
                    existing_att[k] = v
                existing_att["updated_at"] = now_iso()

    db["children"] = children
    db["attendances"] = attendances
    db.setdefault("import_batches", []).append(
        {
            "id": batch_id,
            "imported_at": imported_at,
            "file": xlsx_path.name,
            "sheet": resolved_sheet_name,
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
