from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_audit_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    top = ttk.Frame(root, padding=10)
    top.grid(row=0, column=0, sticky="ew")
    ttk.Button(top, text="Recarregar", command=app.reload_audit).grid(row=0, column=0, sticky="w")

    mid = ttk.Frame(root, padding=(10, 0, 10, 10))
    mid.grid(row=1, column=0, sticky="nsew")
    mid.columnconfigure(0, weight=1)
    mid.rowconfigure(0, weight=1)

    app.audit_tree = ttk.Treeview(
        mid, columns=("at", "actor", "action", "etype", "eid"), show="headings", selectmode="browse"
    )
    for col, w in [("at", 200), ("actor", 140), ("action", 160), ("etype", 100), ("eid", 260)]:
        app.audit_tree.heading(col, text=col)
        app.audit_tree.column(col, width=w, anchor="w")
    app._setup_treeview(app.audit_tree)
    app.audit_tree.grid(row=0, column=0, sticky="nsew")
    app.audit_tree.bind("<<TreeviewSelect>>", lambda _e: app.on_audit_select())

    vsb = ttk.Scrollbar(mid, orient="vertical", command=app.audit_tree.yview)
    app.audit_tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=0, column=1, sticky="ns")

    app.audit_details = tk.Text(root, height=10, wrap="word")
    app.audit_details.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

    app.reload_audit()
