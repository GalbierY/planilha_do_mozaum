from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_stats_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(2, weight=1)
    root.rowconfigure(3, weight=1)

    top = ttk.LabelFrame(root, text="Visao geral", style="Card.TLabelframe", padding=(12, 10))
    top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 8))
    top.columnconfigure(4, weight=1)

    ttk.Button(top, text="Atualizar indicadores", command=app.refresh_stats, style="Primary.TButton").grid(
        row=0, column=0, sticky="w", padx=(0, 16)
    )

    app.stats_total_var = tk.StringVar(value="0")
    app.stats_atend_var = tk.StringVar(value="0")
    app.stats_vd_var = tk.StringVar(value="0")
    app.stats_source_var = tk.StringVar(value="")
    app.stats_last_import_var = tk.StringVar(value="")

    metric_total = ttk.LabelFrame(top, text="Total de criancas", style="Card.TLabelframe", padding=(10, 6))
    metric_total.grid(row=0, column=1, sticky="w", padx=(0, 8))
    ttk.Label(metric_total, textvariable=app.stats_total_var, style="MetricValue.TLabel").grid(row=0, column=0, sticky="w")

    metric_att = ttk.LabelFrame(top, text="Com atendimento", style="Card.TLabelframe", padding=(10, 6))
    metric_att.grid(row=0, column=2, sticky="w", padx=(0, 8))
    ttk.Label(metric_att, textvariable=app.stats_atend_var, style="MetricValue.TLabel").grid(row=0, column=0, sticky="w")

    metric_vd = ttk.LabelFrame(top, text="Com VD", style="Card.TLabelframe", padding=(10, 6))
    metric_vd.grid(row=0, column=3, sticky="w", padx=(0, 8))
    ttk.Label(metric_vd, textvariable=app.stats_vd_var, style="MetricValue.TLabel").grid(row=0, column=0, sticky="w")

    ttk.Label(top, text="Fontes:", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Label(top, textvariable=app.stats_source_var, style="Muted.TLabel").grid(row=1, column=1, columnspan=4, sticky="w", pady=(8, 0))
    ttk.Label(top, text="Ultima importacao:", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
    ttk.Label(top, textvariable=app.stats_last_import_var, style="Muted.TLabel").grid(
        row=2, column=1, columnspan=4, sticky="w", pady=(4, 0)
    )

    left = ttk.LabelFrame(root, text="Distribuicao por escola", style="Card.TLabelframe", padding=(10, 8))
    left.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
    left.rowconfigure(0, weight=1)
    left.columnconfigure(0, weight=1)

    app.stats_tree_school = ttk.Treeview(left, columns=("escola", "qtd"), show="headings", selectmode="none")
    app.stats_tree_school.heading("escola", text="Escola")
    app.stats_tree_school.column("escola", width=340, anchor="w")
    app.stats_tree_school.heading("qtd", text="Qtd")
    app.stats_tree_school.column("qtd", width=80, anchor="center")
    app._setup_treeview(app.stats_tree_school, numeric_cols={"qtd"})
    app.stats_tree_school.grid(row=0, column=0, sticky="nsew")

    vsb1 = ttk.Scrollbar(left, orient="vertical", command=app.stats_tree_school.yview)
    app.stats_tree_school.configure(yscrollcommand=vsb1.set)
    vsb1.grid(row=0, column=1, sticky="ns")

    right = ttk.LabelFrame(root, text="Distribuicao por idade", style="Card.TLabelframe", padding=(10, 8))
    right.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
    right.rowconfigure(0, weight=1)
    right.columnconfigure(0, weight=1)

    app.stats_tree_age = ttk.Treeview(right, columns=("idade", "qtd"), show="headings", selectmode="none")
    app.stats_tree_age.heading("idade", text="Idade")
    app.stats_tree_age.column("idade", width=120, anchor="w")
    app.stats_tree_age.heading("qtd", text="Qtd")
    app.stats_tree_age.column("qtd", width=80, anchor="center")
    app._setup_treeview(app.stats_tree_age, numeric_cols={"idade", "qtd"})
    app.stats_tree_age.grid(row=0, column=0, sticky="nsew")

    vsb2 = ttk.Scrollbar(right, orient="vertical", command=app.stats_tree_age.yview)
    app.stats_tree_age.configure(yscrollcommand=vsb2.set)
    vsb2.grid(row=0, column=1, sticky="ns")

    bottom = ttk.LabelFrame(root, text="Distribuicao por tags", style="Card.TLabelframe", padding=(10, 8))
    bottom.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
    bottom.rowconfigure(0, weight=1)
    bottom.columnconfigure(0, weight=1)

    app.stats_tree_tags = ttk.Treeview(bottom, columns=("tag", "qtd"), show="headings", selectmode="none")
    app.stats_tree_tags.heading("tag", text="Tag")
    app.stats_tree_tags.column("tag", width=460, anchor="w")
    app.stats_tree_tags.heading("qtd", text="Qtd")
    app.stats_tree_tags.column("qtd", width=80, anchor="center")
    app._setup_treeview(app.stats_tree_tags, numeric_cols={"qtd"})
    app.stats_tree_tags.grid(row=0, column=0, sticky="nsew")

    vsb3 = ttk.Scrollbar(bottom, orient="vertical", command=app.stats_tree_tags.yview)
    app.stats_tree_tags.configure(yscrollcommand=vsb3.set)
    vsb3.grid(row=0, column=1, sticky="ns")
