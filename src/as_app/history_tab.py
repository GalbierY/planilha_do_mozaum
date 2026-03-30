from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_history_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    root.rowconfigure(3, weight=1)

    top = ttk.LabelFrame(root, text="Contexto atual", style="Card.TLabelframe", padding=(12, 10))
    top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
    top.columnconfigure(1, weight=1)

    ttk.Label(top, text="Crianca selecionada:").grid(row=0, column=0, sticky="w")
    app.history_child_var = tk.StringVar(value="(nenhuma selecionada)")
    ttk.Label(top, textvariable=app.history_child_var).grid(row=0, column=1, sticky="w", padx=(8, 0))
    ttk.Button(top, text="+ Atendimento", command=app.on_new_attendance, style="Primary.TButton").grid(row=0, column=2, padx=(8, 0))
    app.btn_history_edit = ttk.Button(top, text="Editar", command=app.on_edit_attendance, state="disabled", style="Secondary.TButton")
    app.btn_history_edit.grid(row=0, column=3, padx=(8, 0))

    ttk.Label(top, text="Selecione um item para visualizar o texto do atendimento e os anexos.", style="Muted.TLabel").grid(
        row=1, column=0, columnspan=4, sticky="w", pady=(6, 0)
    )

    mid = ttk.LabelFrame(root, text="Linha do tempo de atendimentos", style="Card.TLabelframe", padding=(10, 8))
    mid.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
    mid.columnconfigure(0, weight=1)
    mid.rowconfigure(0, weight=1)

    app.history_tree = ttk.Treeview(
        mid,
        columns=("quando", "tipo", "prof", "resultado", "registrado", "tem_atend", "tem_vd"),
        show="headings",
        selectmode="browse",
    )
    app.history_tree.heading("quando", text="Quando")
    app.history_tree.column("quando", width=180, anchor="w")
    app.history_tree.heading("tipo", text="Tipo")
    app.history_tree.column("tipo", width=120, anchor="w")
    app.history_tree.heading("prof", text="Profissional")
    app.history_tree.column("prof", width=180, anchor="w")
    app.history_tree.heading("resultado", text="Resultado")
    app.history_tree.column("resultado", width=160, anchor="w")
    app.history_tree.heading("registrado", text="Registrado por")
    app.history_tree.column("registrado", width=140, anchor="w")
    app.history_tree.heading("tem_atend", text="Atendimento")
    app.history_tree.column("tem_atend", width=100, anchor="center")
    app.history_tree.heading("tem_vd", text="VD")
    app.history_tree.column("tem_vd", width=80, anchor="center")
    app._setup_treeview(app.history_tree)
    app.history_tree.grid(row=0, column=0, sticky="nsew")
    app.history_tree.bind("<<TreeviewSelect>>", lambda _e: app.on_history_select())
    app.history_tree.bind("<Double-1>", lambda _e: app.on_edit_attendance())

    vsb = ttk.Scrollbar(mid, orient="vertical", command=app.history_tree.yview)
    app.history_tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=0, column=1, sticky="ns")

    bottom = ttk.LabelFrame(root, text="Detalhes do registro", style="Card.TLabelframe", padding=(10, 8))
    bottom.grid(row=2, column=0, sticky="ew")
    bottom.columnconfigure(1, weight=1)
    bottom.columnconfigure(3, weight=1)
    bottom.columnconfigure(0, weight=0)
    bottom.columnconfigure(2, weight=0)

    ttk.Label(bottom, text="Atendimento:").grid(row=0, column=0, sticky="nw", pady=(0, 6))
    app.history_txt_atend = tk.Text(bottom, height=8, wrap="word")
    app.history_txt_atend.grid(row=0, column=1, sticky="nsew", pady=(0, 6), padx=(8, 24))

    ttk.Label(bottom, text="VD:").grid(row=0, column=2, sticky="nw", pady=(0, 6))
    app.history_txt_vd = tk.Text(bottom, height=8, wrap="word")
    app.history_txt_vd.grid(row=0, column=3, sticky="nsew", pady=(0, 6), padx=(8, 0))

    app.history_txt_atend.configure(state="disabled")
    app.history_txt_vd.configure(state="disabled")

    attach = ttk.LabelFrame(root, text="Anexos do atendimento", style="Card.TLabelframe", padding=(10, 8))
    attach.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
    attach.columnconfigure(0, weight=1)
    attach.rowconfigure(1, weight=1)

    btns = ttk.Frame(attach)
    btns.grid(row=0, column=1, sticky="e")
    ttk.Button(btns, text="Adicionar", command=app.on_attachment_add, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="Abrir", command=app.on_attachment_open, style="Secondary.TButton").grid(row=0, column=1, padx=(0, 8))
    ttk.Button(btns, text="Remover", command=app.on_attachment_remove, style="Secondary.TButton").grid(row=0, column=2)

    app.attach_tree = ttk.Treeview(attach, columns=("nome", "quando", "por"), show="headings", selectmode="browse")
    app.attach_tree.heading("nome", text="Arquivo")
    app.attach_tree.column("nome", width=420, anchor="w")
    app.attach_tree.heading("quando", text="Adicionado em")
    app.attach_tree.column("quando", width=180, anchor="w")
    app.attach_tree.heading("por", text="Por")
    app.attach_tree.column("por", width=160, anchor="w")
    app._setup_treeview(app.attach_tree)
    app.attach_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")

    vsb3 = ttk.Scrollbar(attach, orient="vertical", command=app.attach_tree.yview)
    app.attach_tree.configure(yscrollcommand=vsb3.set)
    vsb3.grid(row=1, column=2, sticky="ns")
