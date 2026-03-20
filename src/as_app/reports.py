from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


FALTA_RE = re.compile(r"\bfalta\b", re.IGNORECASE)


@dataclass(frozen=True)
class Report:
    title: str
    headers: list[str]
    rows: list[list[str]]


def _dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def build_reports(db: dict[str, Any], *, start: str | None = None, end: str | None = None) -> dict[str, Report]:
    children = list(db.get("children") or [])
    attendances = list(db.get("attendances") or [])
    child_by_id = {c.get("id"): c for c in children if c.get("id")}

    start_dt = _dt(start)
    end_dt = _dt(end)

    def in_period(att: dict[str, Any]) -> bool:
        if start_dt is None and end_dt is None:
            return True
        d = _dt(att.get("occurred_at"))
        if d is None:
            return False
        if start_dt and d < start_dt:
            return False
        if end_dt and d > end_dt:
            return False
        return True

    # Pendências: crianças sem atendimentos
    has_any = {a.get("child_id") for a in attendances if a.get("child_id")}
    pending = [c for c in children if c.get("id") and c.get("id") not in has_any]
    pending.sort(key=lambda c: (c.get("nome") or "").lower())

    # Faltas: atendimentos com palavra "falta"
    faltas_rows: list[list[str]] = []
    for a in attendances:
        if not in_period(a):
            continue
        txt = f"{a.get('atendimento_text') or ''}\n{a.get('vd_text') or ''}"
        if not FALTA_RE.search(txt):
            continue
        c = child_by_id.get(a.get("child_id"))
        faltas_rows.append(
            [
                (c.get("nome") if c else "") or "",
                (c.get("escola") if c else "") or "",
                a.get("occurred_at") or "",
                a.get("tipo") or "",
                a.get("profissional") or "",
            ]
        )
    faltas_rows.sort(key=lambda r: r[2], reverse=True)

    # Por escola (contagem)
    by_school = Counter(((c.get("escola") or "").strip() or "(Sem escola)") for c in children)
    school_rows = [[k, str(v)] for k, v in sorted(by_school.items(), key=lambda kv: (-kv[1], kv[0].lower()))]

    # Atendimentos por mês
    by_month: Counter[str] = Counter()
    for a in attendances:
        if not in_period(a):
            continue
        d = _dt(a.get("occurred_at"))
        if not d:
            continue
        by_month[d.strftime("%Y-%m")] += 1
    month_rows = [[k, str(v)] for k, v in sorted(by_month.items(), key=lambda kv: kv[0], reverse=True)]

    # Atendimentos detalhado (no período)
    att_rows: list[list[str]] = []
    for a in attendances:
        if not in_period(a):
            continue
        c = child_by_id.get(a.get("child_id"))
        att_rows.append(
            [
                a.get("occurred_at") or "",
                (c.get("nome") if c else "") or "",
                (c.get("escola") if c else "") or "",
                a.get("tipo") or "",
                a.get("profissional") or "",
                (a.get("resultado") or ""),
            ]
        )
    att_rows.sort(key=lambda r: r[0], reverse=True)

    return {
        "pending": Report(
            title="Pendências (sem atendimento)",
            headers=["Criança", "Escola", "Idade"],
            rows=[
                [c.get("nome") or "", c.get("escola") or "", "" if c.get("idade") is None else str(c.get("idade"))]
                for c in pending
            ],
        ),
        "faltas": Report(
            title="Faltas (texto contém 'falta')",
            headers=["Criança", "Escola", "Quando", "Tipo", "Profissional"],
            rows=faltas_rows,
        ),
        "by_school": Report(
            title="Crianças por escola",
            headers=["Escola", "Qtd"],
            rows=school_rows,
        ),
        "att_by_month": Report(
            title="Atendimentos por mês",
            headers=["Ano-Mês", "Qtd"],
            rows=month_rows,
        ),
        "att_detail": Report(
            title="Atendimentos (detalhado)",
            headers=["Quando", "Criança", "Escola", "Tipo", "Profissional", "Resultado"],
            rows=att_rows,
        ),
    }


def export_csv(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(report.headers)
        w.writerows(report.rows)


def export_pdf(report: Report, path: Path) -> None:
    try:
        from fpdf import FPDF  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Dependência PDF não instalada. Rode o bootstrap para instalar o requirements.") from e

    path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, report.title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", size=9)
    pdf.multi_cell(0, 5, " | ".join(report.headers))
    pdf.set_x(pdf.l_margin)
    pdf.ln(1)
    pdf.set_font("Helvetica", size=8)

    for row in report.rows:
        line = " | ".join((c or "") for c in row).replace("\t", " ")
        pdf.multi_cell(0, 4, line)
        pdf.set_x(pdf.l_margin)

    pdf.output(str(path))
