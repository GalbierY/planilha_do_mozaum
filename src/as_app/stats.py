from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Stats:
    total: int
    with_atendimento: int
    with_vd: int
    by_school: list[tuple[str, int]]
    by_age: list[tuple[str, int]]
    by_source: list[tuple[str, int]]
    last_import: dict[str, Any] | None


def compute_stats(db: dict[str, Any]) -> Stats:
    children = list(db.get("children") or [])
    attendances = list(db.get("attendances") or [])

    def norm(s: Any, fallback: str) -> str:
        text = ("" if s is None else str(s)).strip()
        return text if text else fallback

    by_school = Counter(norm(a.get("escola"), "(Sem escola)") for a in children)
    by_age = Counter(norm(a.get("idade"), "(Sem idade)") for a in children)
    by_source = Counter(norm((a.get("source") or {}).get("type"), "(Sem fonte)") for a in children)

    child_has_atendimento: set[str] = set()
    child_has_vd: set[str] = set()
    for att in attendances:
        cid = att.get("child_id")
        if not cid:
            continue
        if (att.get("atendimento_text") or "").strip():
            child_has_atendimento.add(cid)
        if (att.get("vd_text") or "").strip():
            child_has_vd.add(cid)

    with_atendimento = len(child_has_atendimento)
    with_vd = len(child_has_vd)

    batches = list(db.get("import_batches") or [])
    last_import = None
    if batches:
        last_import = max(batches, key=lambda b: (b.get("imported_at") or ""))

    return Stats(
        total=len(children),
        with_atendimento=with_atendimento,
        with_vd=with_vd,
        by_school=sorted(by_school.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        by_age=sorted(by_age.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        by_source=sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        last_import=last_import,
    )
