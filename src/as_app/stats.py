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
    alunos = list(db.get("alunos") or [])

    def norm(s: Any, fallback: str) -> str:
        text = ("" if s is None else str(s)).strip()
        return text if text else fallback

    by_school = Counter(norm(a.get("escola"), "(Sem escola)") for a in alunos)
    by_age = Counter(norm(a.get("idade"), "(Sem idade)") for a in alunos)
    by_source = Counter(norm((a.get("source") or {}).get("type"), "(Sem fonte)") for a in alunos)

    with_atendimento = sum(1 for a in alunos if (a.get("atendimento_realizado") or "").strip())
    with_vd = sum(1 for a in alunos if (a.get("vd") or "").strip())

    batches = list(db.get("import_batches") or [])
    last_import = None
    if batches:
        last_import = max(batches, key=lambda b: (b.get("imported_at") or ""))

    return Stats(
        total=len(alunos),
        with_atendimento=with_atendimento,
        with_vd=with_vd,
        by_school=sorted(by_school.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        by_age=sorted(by_age.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        by_source=sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0].lower())),
        last_import=last_import,
    )
