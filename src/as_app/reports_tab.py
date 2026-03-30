from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_reports_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    top = ttk.LabelFrame(root, text="Geracao de relatorios", style="Card.TLabelframe", padding=(12, 10))
    top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
    top.columnconfigure(1, weight=1)

    app.report_labels = {
        "Pendencias de atendimento": "pending",
        "Faltas registradas": "faltas",
        "Resumo por escola": "by_school",
        "Atendimentos por mes": "att_by_month",
        "Detalhamento de atendimentos": "att_detail",
    }
    default_report = next(iter(app.report_labels.keys()))

    ttk.Label(top, text="Tipo de relatorio:").grid(row=0, column=0, sticky="w")
    app.report_key_var = tk.StringVar(value=default_report)
    app.report_key_cb = ttk.Combobox(
        top,
        textvariable=app.report_key_var,
        state="readonly",
        width=32,
        values=list(app.report_labels.keys()),
    )
    app.report_key_cb.grid(row=0, column=1, sticky="w", padx=(8, 16))

    ttk.Label(top, text="Inicio (aaaa-mm-dd):").grid(row=0, column=2, sticky="e")
    app.report_start_var = tk.StringVar(value="")
    ttk.Entry(top, textvariable=app.report_start_var, width=18).grid(row=0, column=3, sticky="w", padx=(8, 16))

    ttk.Label(top, text="Fim (aaaa-mm-dd):").grid(row=0, column=4, sticky="e")
    app.report_end_var = tk.StringVar(value="")
    ttk.Entry(top, textvariable=app.report_end_var, width=18).grid(row=0, column=5, sticky="w")

    ttk.Label(
        top,
        text="Use o periodo para limitar resultados. Deixe vazio para considerar todo o historico.",
        style="Muted.TLabel",
    ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

    btns = ttk.Frame(top)
    btns.grid(row=2, column=0, columnspan=6, sticky="w", pady=(10, 0))
    ttk.Button(btns, text="Gerar visualizacao", command=app.on_report_generate, style="Primary.TButton").grid(
        row=0, column=0, padx=(0, 8)
    )
    ttk.Button(btns, text="Exportar CSV", command=app.on_report_export_csv, style="Secondary.TButton").grid(
        row=0, column=1, padx=(0, 8)
    )
    ttk.Button(btns, text="Exportar PDF", command=app.on_report_export_pdf, style="Secondary.TButton").grid(
        row=0, column=2, padx=(0, 8)
    )
    ttk.Button(btns, text="Imprimir PDF", command=app.on_report_print_pdf, style="Secondary.TButton").grid(
        row=0, column=3)

    preview_wrap = ttk.LabelFrame(root, text="Pre-visualizacao", style="Card.TLabelframe", padding=(10, 8))
    preview_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
    preview_wrap.columnconfigure(0, weight=1)
    preview_wrap.rowconfigure(0, weight=1)

    app.report_preview = tk.Text(
        preview_wrap,
        wrap="none",
        background=app.colors.get("panel", "#FFFFFF"),
        foreground=app.colors.get("text", "#1E2A3A"),
        relief="flat",
        padx=8,
        pady=8,
    )
    app.report_preview.grid(row=0, column=0, sticky="nsew")

    report_vsb = ttk.Scrollbar(preview_wrap, orient="vertical", command=app.report_preview.yview)
    app.report_preview.configure(yscrollcommand=report_vsb.set)
    report_vsb.grid(row=0, column=1, sticky="ns")

    app._last_report = None
    app._last_pdf_path = None
