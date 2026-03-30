from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_users_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    top = ttk.Frame(root, padding=10)
    top.grid(row=0, column=0, sticky="ew")
    ttk.Label(top, text="Usuários (admin)").grid(row=0, column=0, sticky="w")

    mid = ttk.Frame(root, padding=(10, 0, 10, 10))
    mid.grid(row=1, column=0, sticky="nsew")
    mid.columnconfigure(0, weight=1)
    mid.rowconfigure(0, weight=1)

    app.users_tree = ttk.Treeview(mid, columns=("user", "role", "active"), show="headings", selectmode="browse")
    app.users_tree.heading("user", text="Usuário")
    app.users_tree.column("user", width=220, anchor="w")
    app.users_tree.heading("role", text="Role")
    app.users_tree.column("role", width=100, anchor="w")
    app.users_tree.heading("active", text="Ativo")
    app.users_tree.column("active", width=80, anchor="center")
    app._setup_treeview(app.users_tree)
    app.users_tree.grid(row=0, column=0, sticky="nsew")
    app.users_tree.bind("<<TreeviewSelect>>", lambda _e: app.on_user_select())

    vsb = ttk.Scrollbar(mid, orient="vertical", command=app.users_tree.yview)
    app.users_tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=0, column=1, sticky="ns")

    form = ttk.Frame(root, padding=(10, 0, 10, 10))
    form.grid(row=2, column=0, sticky="ew")
    form.columnconfigure(1, weight=1)

    app.user_id_var = tk.StringVar(value="")
    app.user_username_var = tk.StringVar(value="")
    app.user_role_var = tk.StringVar(value="viewer")
    app.user_active_var = tk.BooleanVar(value=True)
    app.user_pw_var = tk.StringVar(value="")
    app.user_pw2_var = tk.StringVar(value="")

    ttk.Label(form, text="Usuário:").grid(row=0, column=0, sticky="w")
    ttk.Entry(form, textvariable=app.user_username_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    ttk.Label(form, text="Role:").grid(row=0, column=2, sticky="e", padx=(16, 0))
    ttk.Combobox(form, textvariable=app.user_role_var, state="readonly", values=["admin", "editor", "viewer"]).grid(
        row=0, column=3, sticky="w", padx=(8, 0)
    )
    ttk.Checkbutton(form, text="Ativo", variable=app.user_active_var).grid(row=0, column=4, sticky="w", padx=(16, 0))

    ttk.Label(form, text="Senha:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(form, textvariable=app.user_pw_var, show="*").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
    ttk.Label(form, text="Confirmar:").grid(row=1, column=2, sticky="e", padx=(16, 0), pady=(8, 0))
    ttk.Entry(form, textvariable=app.user_pw2_var, show="*").grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(8, 0))

    ttk.Button(form, text="Salvar usuário", command=app.on_user_save).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
    ttk.Button(form, text="Novo", command=app.on_user_new).grid(row=2, column=2, sticky="e", pady=(10, 0))

    app.reload_users()
