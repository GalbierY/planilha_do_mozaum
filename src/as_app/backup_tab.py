from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_backup_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    box = ttk.LabelFrame(root, text="Seguranca dos dados", style="Card.TLabelframe", padding=(12, 10))
    box.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    ttk.Label(
        box,
        text="Crie backups frequentes antes de importacoes ou grandes alteracoes.",
        style="Muted.TLabel",
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    ttk.Button(box, text="Fazer backup agora", command=app.on_backup_create, style="Primary.TButton").grid(
        row=1, column=0, padx=(0, 8), sticky="w"
    )
    ttk.Button(box, text="Restaurar backup", command=app.on_backup_restore, style="Secondary.TButton").grid(
        row=1, column=1, sticky="w"
    )
    app.backup_status_var = tk.StringVar(value="")
    ttk.Label(box, textvariable=app.backup_status_var, style="Muted.TLabel").grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
    )
