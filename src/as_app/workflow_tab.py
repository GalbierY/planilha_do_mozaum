from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_workflow_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    top = ttk.Frame(root, padding=10)
    top.grid(row=0, column=0, sticky="ew")
    ttk.Label(top, text="Workflow de Importação").grid(row=0, column=0, sticky="w")

    mid = ttk.Frame(root, padding=(10, 0, 10, 10))
    mid.grid(row=1, column=0, sticky="nsew")
    mid.columnconfigure(0, weight=1)
    mid.rowconfigure(0, weight=1)

    app.workflow_tree = ttk.Treeview(
        mid, columns=("nome", "status"), show="headings", selectmode="browse"
    )
    app.workflow_tree.heading("nome", text="Criança")
    app.workflow_tree.column("nome", width=400, anchor="w")
    app.workflow_tree.heading("status", text="Status")
    app.workflow_tree.column("status", width=120, anchor="center")
    app._setup_treeview(app.workflow_tree)

    app.workflow_tree.tag_configure("pending", background="#FFF3F8", foreground="#7A5D6A")
    app.workflow_tree.tag_configure("completed", background="#EEF8F2", foreground="#4E6D5B")

    app.workflow_tree.grid(row=0, column=0, sticky="nsew")
    app.workflow_tree.bind("<<TreeviewSelect>>", lambda _e: app.on_workflow_select())
    app.workflow_tree.bind("<Button-1>", app.on_workflow_item_click)

    vsb = ttk.Scrollbar(mid, orient="vertical", command=app.workflow_tree.yview)
    app.workflow_tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=0, column=1, sticky="ns")

    bottom = ttk.Frame(root, padding=(10, 0, 10, 10))
    bottom.grid(row=2, column=0, sticky="ew")
    bottom.columnconfigure(1, weight=1)

    ttk.Label(bottom, text="Arquivo:").grid(row=0, column=0, sticky="w")
    app.workflow_file_var = tk.StringVar(value="")
    ttk.Entry(bottom, textvariable=app.workflow_file_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 0))

    ttk.Label(bottom, text="Status:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    app.workflow_status_var = tk.StringVar(value="")
    ttk.Label(bottom, textvariable=app.workflow_status_var).grid(row=1, column=1, sticky="w", pady=(8, 0))

    ttk.Label(bottom, text="Última importação:").grid(row=2, column=0, sticky="w", pady=(8, 0))
    app.workflow_last_import_var = tk.StringVar(value="")
    ttk.Label(bottom, textvariable=app.workflow_last_import_var).grid(row=2, column=1, sticky="w", pady=(8, 0))

    btns = ttk.Frame(bottom)
    btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
    app.btn_workflow_import = ttk.Button(btns, text="Importar", command=app.on_workflow_import, state="disabled")
    app.btn_workflow_import.grid(row=0, column=0, padx=(0, 8))
    app.btn_workflow_select = ttk.Button(btns, text="Selecionar Arquivo", command=app.on_workflow_select_file)
    app.btn_workflow_select.grid(row=0, column=1, padx=(0, 8))
    app.btn_workflow_clear = ttk.Button(btns, text="Limpar Histórico", command=app.on_workflow_clear, state="disabled")
    app.btn_workflow_clear.grid(row=0, column=2)

    app.reload_workflow()
