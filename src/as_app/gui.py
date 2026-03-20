from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .auth import hash_password, verify_password
from .backup import create_backup, restore_backup
from .config import AppConfig
from .files import store_attachment
from .reports import build_reports, export_csv, export_pdf
from .store import JsonStore
from .updater import check_for_update, pull_ff_only
from .util import br_date_to_iso, iso_to_br_date, now_iso
from .stats import compute_stats


class App(tk.Tk):
    def __init__(self, app_root: Path):
        super().__init__()

        self.app_root = app_root
        self.cfg = AppConfig.load(app_root)
        self.store = JsonStore(app_root / self.cfg.db_path)
        self.current_user: dict | None = None

        self.title(self.cfg.app_name)
        self.geometry("1200x720")

        self.selected_id: str | None = None
        self.selected_attendance_id: str | None = None
        self.cache: list[dict] = []
        self._update_check_running = False
        self._update_available = False

        # Login / setup
        self.withdraw()
        self.current_user = self._login_flow()
        if self.current_user is None:
            self.destroy()
            return
        self.deiconify()

        self._setup_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._apply_permissions()
        self._refresh_action_bar_state()
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self._start_auto_update_checks()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.option_add("*Font", ("Segoe UI", 10))
        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Invalid.TEntry", fieldbackground="#fff1f2")
        style.configure("Invalid.TCombobox", fieldbackground="#fff1f2")

    def _build_ui(self) -> None:
        self.banner_frame = tk.Frame(self, bg="#fff3cd", bd=1, relief="solid")
        self.banner_frame.pack(fill="x")
        self.banner_message = tk.StringVar(value="")
        tk.Label(
            self.banner_frame,
            textvariable=self.banner_message,
            bg="#fff3cd",
            fg="#664d03",
            anchor="w",
            padx=10,
            pady=6,
        ).pack(side="left", fill="x", expand=True)
        self.banner_update_btn = ttk.Button(self.banner_frame, text="Atualizar", command=self.on_update_now)
        self.banner_update_btn.pack(side="right", padx=(0, 10), pady=6)
        ttk.Button(self.banner_frame, text="Fechar", command=self.hide_update_banner).pack(
            side="right", padx=(0, 8), pady=6
        )
        self.banner_frame.pack_forget()

        self.notebook = ttk.Notebook(self)
        self.tab_cadastros = ttk.Frame(self.notebook)
        self.tab_stats = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_backup = ttk.Frame(self.notebook)
        self.tab_audit = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cadastros, text="Cadastros")
        self.notebook.add(self.tab_stats, text="Estatísticas")
        self.notebook.add(self.tab_history, text="Histórico")
        self.notebook.add(self.tab_reports, text="Relatórios")
        self.notebook.add(self.tab_backup, text="Backup")
        self.notebook.add(self.tab_audit, text="Auditoria")
        if self._is_admin():
            self.tab_users = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_users, text="Usuários")
        self.notebook.pack(fill="both", expand=True)

        self._build_cadastros_ui(self.tab_cadastros)
        self._build_stats_ui(self.tab_stats)
        self._build_history_ui(self.tab_history)
        self._build_reports_ui(self.tab_reports)
        self._build_backup_ui(self.tab_backup)
        self._build_audit_ui(self.tab_audit)
        if self._is_admin() and hasattr(self, "tab_users"):
            self._build_users_ui(self.tab_users)

        self.action_bar = ttk.Frame(self, padding=(10, 8))
        self.action_bar.pack(fill="x", side="bottom")
        self.action_bar.columnconfigure(20, weight=1)

        self.btn_import = ttk.Button(self.action_bar, text="Importar", command=self.on_import)
        self.btn_import.grid(row=0, column=0, sticky="w")
        self.btn_new_form = ttk.Button(self.action_bar, text="Novo", command=self.on_new_child_form)
        self.btn_new_form.grid(row=0, column=1, padx=(8, 0))
        self.btn_add_child = ttk.Button(self.action_bar, text="+ Criança", command=self.on_add)
        self.btn_add_child.grid(row=0, column=2, padx=(8, 0))
        self.btn_save_child = ttk.Button(self.action_bar, text="Salvar", command=self.on_save)
        self.btn_save_child.grid(row=0, column=3, padx=(8, 0))
        self.btn_new_att = ttk.Button(self.action_bar, text="+ Atendimento", command=self.on_new_attendance, state="disabled")
        self.btn_new_att.grid(row=0, column=4, padx=(12, 0))
        self.btn_edit_att = ttk.Button(self.action_bar, text="Editar atendimento", command=self.on_edit_attendance, state="disabled")
        self.btn_edit_att.grid(row=0, column=5, padx=(8, 0))
        self.btn_attach = ttk.Button(self.action_bar, text="Anexar", command=self.on_attachment_add, state="disabled")
        self.btn_attach.grid(row=0, column=6, padx=(8, 0))
        self.btn_backup_quick = ttk.Button(self.action_bar, text="Backup", command=self.on_backup_create)
        self.btn_backup_quick.grid(row=0, column=7, padx=(12, 0))

        ttk.Separator(self.action_bar, orient="horizontal").grid(row=1, column=0, columnspan=21, sticky="ew", pady=(8, 0))

        self.status_var = tk.StringVar(value="")
        ttk.Label(self.action_bar, textvariable=self.status_var, foreground="gray").grid(
            row=2, column=0, columnspan=21, sticky="w", pady=(6, 0)
        )

        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_action_bar_state())

    def _bind_shortcuts(self) -> None:
        def bind(seq: str, fn) -> None:
            self.bind_all(seq, lambda _e: (fn(), "break"))

        bind("<Control-f>", self.focus_search)
        bind("<Control-n>", self.on_new_child_form)
        bind("<Control-s>", self.on_save)
        bind("<Control-i>", self.on_import)
        bind("<Control-Return>", self.on_new_attendance)
        bind("<Control-e>", self.on_edit_attendance)
        bind("<Alt-1>", lambda: self.notebook.select(self.tab_cadastros))
        bind("<Alt-2>", lambda: self.notebook.select(self.tab_stats))
        bind("<Alt-3>", lambda: self.notebook.select(self.tab_history))
        bind("<Alt-4>", lambda: self.notebook.select(self.tab_reports))
        bind("<Alt-5>", lambda: self.notebook.select(self.tab_backup))
        bind("<Alt-6>", lambda: self.notebook.select(self.tab_audit))

    def _current_tab_text(self) -> str:
        try:
            tab_id = self.notebook.select()
            return str(self.notebook.tab(tab_id, "text") or "")
        except Exception:
            return ""

    def _refresh_action_bar_state(self) -> None:
        can_edit = self._can_edit()
        in_cadastros = self._current_tab_text().strip().lower().startswith("cadastros")

        if hasattr(self, "btn_import"):
            self.btn_import.configure(state=("normal" if (can_edit and in_cadastros) else "disabled"))
        if hasattr(self, "btn_new_form"):
            self.btn_new_form.configure(state=("normal" if can_edit else "disabled"))
        if hasattr(self, "btn_add_child"):
            self.btn_add_child.configure(state=("normal" if can_edit else "disabled"))
        if hasattr(self, "btn_save_child"):
            state = "normal" if (can_edit and in_cadastros and bool(self.selected_id)) else "disabled"
            self.btn_save_child.configure(state=state)
        if hasattr(self, "btn_new_att"):
            state = "normal" if (can_edit and bool(self.selected_id)) else "disabled"
            self.btn_new_att.configure(state=state)
        if hasattr(self, "btn_edit_att"):
            state = "normal" if (can_edit and bool(self.selected_attendance_id)) else "disabled"
            self.btn_edit_att.configure(state=state)
        if hasattr(self, "btn_attach"):
            state = "normal" if (can_edit and bool(self.selected_attendance_id)) else "disabled"
            self.btn_attach.configure(state=state)
        if hasattr(self, "btn_backup_quick"):
            self.btn_backup_quick.configure(state=("normal" if can_edit else "disabled"))
        if hasattr(self, "btn_merge"):
            self.btn_merge.configure(state=("normal" if can_edit else "disabled"))
        if hasattr(self, "btn_history_edit"):
            state = "normal" if (can_edit and bool(self.selected_attendance_id)) else "disabled"
            self.btn_history_edit.configure(state=state)

    def _build_cadastros_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=2)
        root.columnconfigure(1, weight=3)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Buscar:").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.apply_filter())

        self.user_label_var = tk.StringVar(value=self._user_label())
        ttk.Label(top, textvariable=self.user_label_var).grid(row=0, column=2, sticky="e", padx=(16, 8))
        ttk.Button(top, text="Trocar", command=self.on_switch_user).grid(row=0, column=3, sticky="e")

        # Filtros
        ttk.Separator(top).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 8))
        filter_row = ttk.Frame(top)
        filter_row.grid(row=2, column=0, columnspan=4, sticky="ew")
        for c in range(12):
            filter_row.columnconfigure(c, weight=0)
        filter_row.columnconfigure(11, weight=1)

        self.filter_school_var = tk.StringVar(value="")
        self.filter_age_min_var = tk.StringVar(value="")
        self.filter_age_max_var = tk.StringVar(value="")
        self.filter_has_att_var = tk.BooleanVar(value=False)
        self.filter_has_vd_var = tk.BooleanVar(value=False)
        self.filter_start_var = tk.StringVar(value="")
        self.filter_end_var = tk.StringVar(value="")

        ttk.Label(filter_row, text="Escola:").grid(row=0, column=0, sticky="w")
        self.filter_school_cb = ttk.Combobox(filter_row, textvariable=self.filter_school_var, state="normal", width=22, values=[])
        self.filter_school_cb.grid(row=0, column=1, sticky="w", padx=(6, 16))
        self.filter_school_cb.bind("<<ComboboxSelected>>", lambda _e: self.apply_filter())
        self.filter_school_cb.bind("<KeyRelease>", lambda _e: self.apply_filter())

        ttk.Label(filter_row, text="Idade:").grid(row=0, column=2, sticky="w")
        age_min = ttk.Entry(filter_row, textvariable=self.filter_age_min_var, width=5)
        age_min.grid(row=0, column=3, sticky="w", padx=(6, 4))
        ttk.Label(filter_row, text="até").grid(row=0, column=4, sticky="w")
        age_max = ttk.Entry(filter_row, textvariable=self.filter_age_max_var, width=5)
        age_max.grid(row=0, column=5, sticky="w", padx=(6, 16))
        age_min.bind("<KeyRelease>", lambda _e: self.apply_filter())
        age_max.bind("<KeyRelease>", lambda _e: self.apply_filter())

        ttk.Checkbutton(filter_row, text="Tem atendimento", variable=self.filter_has_att_var, command=self.apply_filter).grid(
            row=0, column=6, sticky="w", padx=(0, 12)
        )
        ttk.Checkbutton(filter_row, text="Tem VD", variable=self.filter_has_vd_var, command=self.apply_filter).grid(
            row=0, column=7, sticky="w", padx=(0, 16)
        )

        ttk.Label(filter_row, text="Período (ISO):").grid(row=0, column=8, sticky="w")
        start_e = ttk.Entry(filter_row, textvariable=self.filter_start_var, width=18)
        start_e.grid(row=0, column=9, sticky="w", padx=(6, 6))
        end_e = ttk.Entry(filter_row, textvariable=self.filter_end_var, width=18)
        end_e.grid(row=0, column=10, sticky="w")
        start_e.bind("<KeyRelease>", lambda _e: self.apply_filter())
        end_e.bind("<KeyRelease>", lambda _e: self.apply_filter())

        main_left = ttk.Frame(root, padding=(10, 0, 10, 10))
        main_left.grid(row=1, column=0, sticky="nsew")
        main_left.rowconfigure(1, weight=1)
        main_left.columnconfigure(0, weight=1)

        self.results_var = tk.StringVar(value="Resultados: 0")
        ttk.Label(main_left, textvariable=self.results_var, foreground="gray").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )

        self.tree = ttk.Treeview(
            main_left,
            columns=("nome", "idade", "escola"),
            show="headings",
            selectmode="browse",
        )
        self.tree["displaycolumns"] = ("nome", "idade", "escola")

        self.tree.heading("nome", text="Criança")
        self.tree.column("nome", width=320, anchor="w")
        self.tree.heading("idade", text="Idade")
        self.tree.column("idade", width=80, anchor="center")
        self.tree.heading("escola", text="Escola")
        self.tree.column("escola", width=200, anchor="w")

        self._setup_treeview(self.tree, numeric_cols={"idade"})

        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select())
        self.tree.bind("<Return>", lambda _e: getattr(self, "nome_entry", self.tree).focus_set())

        vsb = ttk.Scrollbar(main_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=1, column=1, sticky="ns")

        main_right = ttk.Frame(root, padding=(0, 0, 10, 10))
        main_right.grid(row=1, column=1, sticky="nsew")
        main_right.columnconfigure(1, weight=1)

        r = 0
        ttk.Label(main_right, text="ID:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.id_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.id_var, state="readonly").grid(
            row=r, column=1, sticky="ew", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Criança:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.nome_var = tk.StringVar()
        self.nome_entry = ttk.Entry(main_right, textvariable=self.nome_var)
        self.nome_entry.grid(row=r, column=1, sticky="ew", pady=(0, 6))
        self.nome_entry.bind("<KeyRelease>", lambda _e: self._clear_invalid(self.nome_entry))

        r += 1
        ttk.Label(main_right, text="Idade:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.idade_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.idade_var, width=10).grid(
            row=r, column=1, sticky="w", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Escola:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.escola_var = tk.StringVar()
        self.escola_cb = ttk.Combobox(main_right, textvariable=self.escola_var, state="normal", values=[])
        self.escola_cb.grid(row=r, column=1, sticky="ew", pady=(0, 6))
        self.escola_cb.bind("<KeyRelease>", lambda _e: self._clear_invalid(self.escola_cb))
        self.escola_cb.bind("<<ComboboxSelected>>", lambda _e: self._clear_invalid(self.escola_cb))

        r += 1
        ttk.Label(main_right, text="Nascimento (dd/mm/aaaa):").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.nasc_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.nasc_var, width=16).grid(
            row=r, column=1, sticky="w", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Atendimentos:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        ttk.Label(main_right, text="Use a aba 'Histórico' para registrar e ver atendimentos.").grid(
            row=r, column=1, sticky="w", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Criado/Atualizado:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.meta_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.meta_var, state="readonly").grid(
            row=r, column=1, sticky="ew", pady=(0, 6)
        )

        self.btn_merge = ttk.Button(main_right, text="Mesclar duplicados…", command=self.on_merge_children)
        self.btn_merge.grid(row=r + 1, column=1, sticky="w", pady=(10, 0))

    def _build_stats_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        for c in range(7):
            top.columnconfigure(c, weight=1)

        ttk.Button(top, text="Recarregar", command=self.refresh_stats).grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.stats_total_var = tk.StringVar(value="0")
        self.stats_atend_var = tk.StringVar(value="0")
        self.stats_vd_var = tk.StringVar(value="0")
        self.stats_source_var = tk.StringVar(value="")
        self.stats_last_import_var = tk.StringVar(value="")

        ttk.Label(top, text="Total:").grid(row=0, column=1, sticky="e")
        ttk.Label(top, textvariable=self.stats_total_var).grid(row=0, column=2, sticky="w", padx=(6, 18))
        ttk.Label(top, text="Com atendimento:").grid(row=0, column=3, sticky="e")
        ttk.Label(top, textvariable=self.stats_atend_var).grid(row=0, column=4, sticky="w", padx=(6, 18))
        ttk.Label(top, text="Com VD:").grid(row=0, column=5, sticky="e")
        ttk.Label(top, textvariable=self.stats_vd_var).grid(row=0, column=6, sticky="w", padx=(6, 0))

        ttk.Label(top, text="Fontes:").grid(row=1, column=1, sticky="e", pady=(8, 0))
        ttk.Label(top, textvariable=self.stats_source_var).grid(row=1, column=2, columnspan=5, sticky="w", pady=(8, 0))
        ttk.Label(top, text="Última importação:").grid(row=2, column=1, sticky="e", pady=(8, 0))
        ttk.Label(top, textvariable=self.stats_last_import_var).grid(row=2, column=2, columnspan=5, sticky="w", pady=(8, 0))

        left = ttk.Frame(root, padding=(10, 0, 10, 10))
        left.grid(row=1, column=0, sticky="nsew")
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Por escola").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.stats_tree_school = ttk.Treeview(left, columns=("escola", "qtd"), show="headings", selectmode="none")
        self.stats_tree_school.heading("escola", text="Escola")
        self.stats_tree_school.column("escola", width=340, anchor="w")
        self.stats_tree_school.heading("qtd", text="Qtd")
        self.stats_tree_school.column("qtd", width=80, anchor="center")
        self._setup_treeview(self.stats_tree_school, numeric_cols={"qtd"})
        self.stats_tree_school.grid(row=1, column=0, sticky="nsew")

        vsb1 = ttk.Scrollbar(left, orient="vertical", command=self.stats_tree_school.yview)
        self.stats_tree_school.configure(yscrollcommand=vsb1.set)
        vsb1.grid(row=1, column=1, sticky="ns")

        right = ttk.Frame(root, padding=(0, 0, 10, 10))
        right.grid(row=1, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Por idade").grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.stats_tree_age = ttk.Treeview(right, columns=("idade", "qtd"), show="headings", selectmode="none")
        self.stats_tree_age.heading("idade", text="Idade")
        self.stats_tree_age.column("idade", width=120, anchor="w")
        self.stats_tree_age.heading("qtd", text="Qtd")
        self.stats_tree_age.column("qtd", width=80, anchor="center")
        self._setup_treeview(self.stats_tree_age, numeric_cols={"idade", "qtd"})
        self.stats_tree_age.grid(row=1, column=0, sticky="nsew")

        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.stats_tree_age.yview)
        self.stats_tree_age.configure(yscrollcommand=vsb2.set)
        vsb2.grid(row=1, column=1, sticky="ns")

    def _build_reports_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Relatório:").grid(row=0, column=0, sticky="w")
        self.report_key_var = tk.StringVar(value="pending")
        self.report_key_cb = ttk.Combobox(
            top,
            textvariable=self.report_key_var,
            state="readonly",
            values=["pending", "faltas", "by_school", "att_by_month", "att_detail"],
        )
        self.report_key_cb.grid(row=0, column=1, sticky="w", padx=(8, 16))

        ttk.Label(top, text="Início (ISO):").grid(row=0, column=2, sticky="e")
        self.report_start_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.report_start_var, width=22).grid(row=0, column=3, sticky="w", padx=(8, 16))

        ttk.Label(top, text="Fim (ISO):").grid(row=0, column=4, sticky="e")
        self.report_end_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.report_end_var, width=22).grid(row=0, column=5, sticky="w", padx=(8, 0))

        btns = ttk.Frame(top)
        btns.grid(row=1, column=0, columnspan=6, sticky="w", pady=(10, 0))
        ttk.Button(btns, text="Gerar", command=self.on_report_generate).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Exportar CSV", command=self.on_report_export_csv).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Exportar PDF", command=self.on_report_export_pdf).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(btns, text="Imprimir PDF", command=self.on_report_print_pdf).grid(row=0, column=3)

        self.report_preview = tk.Text(root, wrap="none")
        self.report_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self._last_report = None
        self._last_pdf_path: Path | None = None

    def _build_backup_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        box = ttk.Frame(root, padding=10)
        box.grid(row=0, column=0, sticky="ew")
        ttk.Button(box, text="Fazer backup", command=self.on_backup_create).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(box, text="Restaurar", command=self.on_backup_restore).grid(row=0, column=1)
        self.backup_status_var = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.backup_status_var, foreground="gray").grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_users_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Usuários (admin)").grid(row=0, column=0, sticky="w")

        mid = ttk.Frame(root, padding=(10, 0, 10, 10))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        self.users_tree = ttk.Treeview(mid, columns=("user", "role", "active"), show="headings", selectmode="browse")
        self.users_tree.heading("user", text="Usuário")
        self.users_tree.column("user", width=220, anchor="w")
        self.users_tree.heading("role", text="Role")
        self.users_tree.column("role", width=100, anchor="w")
        self.users_tree.heading("active", text="Ativo")
        self.users_tree.column("active", width=80, anchor="center")
        self._setup_treeview(self.users_tree)
        self.users_tree.grid(row=0, column=0, sticky="nsew")
        self.users_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_user_select())

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        form = ttk.Frame(root, padding=(10, 0, 10, 10))
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        self.user_id_var = tk.StringVar(value="")
        self.user_username_var = tk.StringVar(value="")
        self.user_role_var = tk.StringVar(value="viewer")
        self.user_active_var = tk.BooleanVar(value=True)
        self.user_pw_var = tk.StringVar(value="")
        self.user_pw2_var = tk.StringVar(value="")

        ttk.Label(form, text="Usuário:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.user_username_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(form, text="Role:").grid(row=0, column=2, sticky="e", padx=(16, 0))
        ttk.Combobox(form, textvariable=self.user_role_var, state="readonly", values=["admin", "editor", "viewer"]).grid(
            row=0, column=3, sticky="w", padx=(8, 0)
        )
        ttk.Checkbutton(form, text="Ativo", variable=self.user_active_var).grid(row=0, column=4, sticky="w", padx=(16, 0))

        ttk.Label(form, text="Senha:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.user_pw_var, show="*").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Label(form, text="Confirmar:").grid(row=1, column=2, sticky="e", padx=(16, 0), pady=(8, 0))
        ttk.Entry(form, textvariable=self.user_pw2_var, show="*").grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Button(form, text="Salvar usuário", command=self.on_user_save).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(form, text="Novo", command=self.on_user_new).grid(row=2, column=2, sticky="e", pady=(10, 0))

        self.reload_users()

    def _build_audit_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="Recarregar", command=self.reload_audit).grid(row=0, column=0, sticky="w")

        mid = ttk.Frame(root, padding=(10, 0, 10, 10))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        self.audit_tree = ttk.Treeview(
            mid, columns=("at", "actor", "action", "etype", "eid"), show="headings", selectmode="browse"
        )
        for col, w in [("at", 200), ("actor", 140), ("action", 160), ("etype", 100), ("eid", 260)]:
            self.audit_tree.heading(col, text=col)
            self.audit_tree.column(col, width=w, anchor="w")
        self._setup_treeview(self.audit_tree)
        self.audit_tree.grid(row=0, column=0, sticky="nsew")
        self.audit_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_audit_select())

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        self.audit_details = tk.Text(root, height=10, wrap="word")
        self.audit_details.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.reload_audit()

    def refresh_stats(self) -> None:
        db = self.store.load()
        stats = compute_stats(db)

        self.stats_total_var.set(str(stats.total))
        self.stats_atend_var.set(str(stats.with_atendimento))
        self.stats_vd_var.set(str(stats.with_vd))

        sources = ", ".join([f"{k}={v}" for k, v in stats.by_source])
        self.stats_source_var.set(sources)

        if stats.last_import:
            li = stats.last_import
            self.stats_last_import_var.set(
                f"{li.get('imported_at')} | file={li.get('file')} | inserted={li.get('inserted')} | updated={li.get('updated')}"
            )
        else:
            self.stats_last_import_var.set("(nenhuma)")

        for iid in self.stats_tree_school.get_children():
            self.stats_tree_school.delete(iid)
        for school, count in stats.by_school:
            self.stats_tree_school.insert("", "end", values=(school, str(count)))
        self._apply_zebra(self.stats_tree_school)

        for iid in self.stats_tree_age.get_children():
            self.stats_tree_age.delete(iid)
        for age, count in stats.by_age:
            self.stats_tree_age.insert("", "end", values=(age, str(count)))
        self._apply_zebra(self.stats_tree_age)

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _actor(self) -> str:
        return ((self.current_user or {}).get("username") or "").strip()

    def _role(self) -> str:
        return ((self.current_user or {}).get("role") or "").strip().lower()

    def _user_label(self) -> str:
        u = (self.current_user or {}).get("username") or ""
        r = (self.current_user or {}).get("role") or ""
        return f"Usuário: {u} ({r})"

    def _can_edit(self) -> bool:
        return self._role() in {"admin", "editor"}

    def _is_admin(self) -> bool:
        return self._role() == "admin"

    def _apply_permissions(self) -> None:
        self._refresh_action_bar_state()

    def _validate_child_age(self, child: dict) -> bool:
        age = child.get("idade")
        birth = child.get("data_nascimento")
        if age is None or not birth:
            return True
        try:
            b = datetime.fromisoformat(birth).date()
            today = datetime.now().date()
            calc = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
        except Exception:
            return True
        if abs(int(age) - int(calc)) <= 1:
            return True
        return messagebox.askyesno(
            "Validação",
            f"Idade ({age}) parece não bater com nascimento ({birth}). Idade calculada ~ {calc}. Salvar mesmo assim?",
        )

    def _set_invalid(self, widget) -> None:
        try:
            if isinstance(widget, ttk.Entry):
                widget.configure(style="Invalid.TEntry")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style="Invalid.TCombobox")
        except Exception:
            pass

    def _clear_invalid(self, widget) -> None:
        try:
            if isinstance(widget, ttk.Entry):
                widget.configure(style="TEntry")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(style="TCombobox")
        except Exception:
            pass

    def _clear_child_form_validation(self) -> None:
        if hasattr(self, "nome_entry"):
            self._clear_invalid(self.nome_entry)
        if hasattr(self, "escola_cb"):
            self._clear_invalid(self.escola_cb)

    def _setup_treeview(self, tree: ttk.Treeview, *, numeric_cols: set[str] | None = None) -> None:
        numeric_cols = set(numeric_cols or set())
        tree.tag_configure("even", background="#ffffff")
        tree.tag_configure("odd", background="#f7f7f7")

        for col in tree["columns"]:
            tree.heading(col, command=lambda c=col: self._tree_sort(tree, c, numeric=(c in numeric_cols)))

    def _tree_sort(self, tree: ttk.Treeview, col: str, *, numeric: bool) -> None:
        state = getattr(self, "_tree_sort_state", None)
        if state is None:
            state = {}
            self._tree_sort_state = state
        per_tree = state.setdefault(id(tree), {})
        descending = bool(per_tree.get(col, False))

        def key_for(v: str):
            t = (v or "").strip()
            if numeric:
                try:
                    return (0, float(t))
                except Exception:
                    return (1, 0.0)
            return (0, t.casefold())

        rows = [(key_for(tree.set(iid, col)), iid) for iid in tree.get_children("")]
        rows.sort(key=lambda x: x[0], reverse=descending)
        for idx, (_k, iid) in enumerate(rows):
            tree.move(iid, "", idx)

        per_tree[col] = not descending
        self._apply_zebra(tree)

    def _apply_zebra(self, tree: ttk.Treeview) -> None:
        for idx, iid in enumerate(tree.get_children("")):
            tree.item(iid, tags=("even" if idx % 2 == 0 else "odd",))

    def reload_cache(self) -> None:
        db = self.store.load()
        children = list(db.get("children") or [])
        children.sort(key=lambda a: (a.get("nome") or "").lower())
        self.cache = children

        attendances = list(db.get("attendances") or [])
        self._atts_by_child: dict[str, list[dict]] = {}
        self._fulltext_by_child: dict[str, str] = {}
        self._has_att: set[str] = set()
        self._has_vd: set[str] = set()
        self._att_dates_by_child: dict[str, list[datetime]] = {}

        for a in attendances:
            cid = a.get("child_id")
            if not cid:
                continue
            self._atts_by_child.setdefault(cid, []).append(a)
            txt = f"{a.get('atendimento_text') or ''}\n{a.get('vd_text') or ''}\n{a.get('resultado') or ''}"
            if txt.strip():
                self._fulltext_by_child[cid] = (self._fulltext_by_child.get(cid, "") + "\n" + txt).lower()
            if (a.get("atendimento_text") or "").strip():
                self._has_att.add(cid)
            if (a.get("vd_text") or "").strip():
                self._has_vd.add(cid)
            try:
                d = datetime.fromisoformat(a.get("occurred_at") or "")
            except Exception:
                d = None
            if d is not None:
                self._att_dates_by_child.setdefault(cid, []).append(d)

        schools = sorted({(c.get("escola") or "").strip() for c in children if (c.get("escola") or "").strip()}, key=str.lower)
        if hasattr(self, "escola_cb"):
            self.escola_cb.configure(values=schools)
        if hasattr(self, "filter_school_cb"):
            self.filter_school_cb.configure(values=[""] + schools)

    def apply_filter(self) -> None:
        query = (self.search_var.get() or "").strip().lower()
        school = (getattr(self, "filter_school_var", tk.StringVar(value="")).get() or "").strip().lower()
        has_att = bool(getattr(self, "filter_has_att_var", tk.BooleanVar(value=False)).get())
        has_vd = bool(getattr(self, "filter_has_vd_var", tk.BooleanVar(value=False)).get())

        def to_int(s: str) -> int | None:
            t = (s or "").strip()
            if not t:
                return None
            try:
                return int(t)
            except ValueError:
                return None

        age_min = to_int(getattr(self, "filter_age_min_var", tk.StringVar(value="")).get())
        age_max = to_int(getattr(self, "filter_age_max_var", tk.StringVar(value="")).get())

        start = (getattr(self, "filter_start_var", tk.StringVar(value="")).get() or "").strip()
        end = (getattr(self, "filter_end_var", tk.StringVar(value="")).get() or "").strip()
        start_dt = None
        end_dt = None
        try:
            if start:
                start_dt = datetime.fromisoformat(start)
        except Exception:
            start_dt = None
        try:
            if end:
                end_dt = datetime.fromisoformat(end)
        except Exception:
            end_dt = None

        def in_period(cid: str) -> bool:
            if start_dt is None and end_dt is None:
                return True
            dates = self._att_dates_by_child.get(cid, [])
            for d in dates:
                if start_dt and d < start_dt:
                    continue
                if end_dt and d > end_dt:
                    continue
                return True
            return False

        items = []
        for c in self.cache:
            cid = c.get("id") or ""
            if school and school not in (c.get("escola") or "").lower():
                continue
            if age_min is not None:
                if c.get("idade") is None or int(c.get("idade")) < age_min:
                    continue
            if age_max is not None:
                if c.get("idade") is None or int(c.get("idade")) > age_max:
                    continue
            if has_att and cid not in self._has_att:
                continue
            if has_vd and cid not in self._has_vd:
                continue
            if not in_period(cid):
                continue

            if query:
                qok = query in (c.get("nome") or "").lower() or query in (c.get("escola") or "").lower()
                if not qok:
                    qok = query in (self._fulltext_by_child.get(cid) or "")
                if not qok:
                    continue
            items.append(c)

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for c in items:
            iid = c.get("id") or ""
            nome = c.get("nome") or ""
            idade = "" if c.get("idade") is None else str(c.get("idade"))
            escola = c.get("escola") or ""
            self.tree.insert("", "end", iid=iid, values=(nome, idade, escola))

        self._apply_zebra(self.tree)

        filtered = bool(
            query
            or school
            or has_att
            or has_vd
            or (age_min is not None)
            or (age_max is not None)
            or bool(start_dt)
            or bool(end_dt)
        )
        msg = f"Resultados: {len(items)}" + (" (filtrado)" if filtered else "")
        if hasattr(self, "results_var"):
            self.results_var.set(msg)
        self.set_status(msg)

    def focus_search(self) -> None:
        if hasattr(self, "tab_cadastros"):
            self.notebook.select(self.tab_cadastros)
        if hasattr(self, "search_entry"):
            self.search_entry.focus_set()
            self.search_entry.selection_range(0, "end")

    def on_new_child_form(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if hasattr(self, "tab_cadastros"):
            self.notebook.select(self.tab_cadastros)
        self.clear_form()
        if hasattr(self, "nome_entry"):
            self.nome_entry.focus_set()

    def on_select(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        child = next((c for c in self.cache if c.get("id") == iid), None)
        if child is None:
            return
        self.fill_form(child)

    def clear_form(self) -> None:
        self.selected_id = None
        self.id_var.set("")
        self.nome_var.set("")
        self.idade_var.set("")
        self.escola_var.set("")
        self.nasc_var.set("")
        self.meta_var.set("")
        self._clear_child_form_validation()
        self._sync_history_selection()
        self._refresh_action_bar_state()

    def fill_form(self, child: dict) -> None:
        self.selected_id = child.get("id")
        self.id_var.set(child.get("id") or "")
        self.nome_var.set(child.get("nome") or "")
        self.idade_var.set("" if child.get("idade") is None else str(child.get("idade")))
        self.escola_var.set(child.get("escola") or "")
        self.nasc_var.set(iso_to_br_date(child.get("data_nascimento")))

        self.meta_var.set(f"created_at={child.get('created_at')} | updated_at={child.get('updated_at')}")
        self._sync_history_selection()
        self._refresh_action_bar_state()

    def _child_from_form(self, *, use_selected_id: bool) -> dict:
        birth_iso = br_date_to_iso(self.nasc_var.get() or "")
        return self.store.new_child_from_form(
            child_id=self.selected_id if use_selected_id else None,
            nome=self.nome_var.get() or "",
            idade=self.idade_var.get() or "",
            escola=self.escola_var.get() or "",
            data_nascimento_iso=birth_iso,
        )

    def on_add(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        self._clear_child_form_validation()
        nome = (self.nome_var.get() or "").strip()
        if not nome:
            self.set_status("Preencha o nome da criança.")
            if hasattr(self, "nome_entry"):
                self._set_invalid(self.nome_entry)
                self.nome_entry.focus_set()
            return
        escola = (self.escola_var.get() or "").strip()
        if not escola:
            self.set_status("Preencha a escola.")
            if hasattr(self, "escola_cb"):
                self._set_invalid(self.escola_cb)
                self.escola_cb.focus_set()
            return
        actor = self._actor()
        child = self._child_from_form(use_selected_id=False)
        if not self._validate_child_age(child):
            return
        action, saved = self.store.upsert_child(child, actor=actor)
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.fill_form(saved)
        self.set_status(f"Adicionado ({action})")
        self.reload_audit()

    def on_save(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if not self.selected_id:
            self.set_status("Selecione uma criança na lista para salvar (ou use '+ Criança').")
            if hasattr(self, "tab_cadastros"):
                self.notebook.select(self.tab_cadastros)
            return
        self._clear_child_form_validation()
        nome = (self.nome_var.get() or "").strip()
        if not nome:
            self.set_status("Preencha o nome da criança.")
            if hasattr(self, "nome_entry"):
                self._set_invalid(self.nome_entry)
                self.nome_entry.focus_set()
            return
        escola = (self.escola_var.get() or "").strip()
        if not escola:
            self.set_status("Preencha a escola.")
            if hasattr(self, "escola_cb"):
                self._set_invalid(self.escola_cb)
                self.escola_cb.focus_set()
            return
        actor = self._actor()
        child = self._child_from_form(use_selected_id=True)
        if not self._validate_child_age(child):
            return
        action, saved = self.store.upsert_child(child, actor=actor)
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.fill_form(saved)
        self.set_status(f"Salvo ({action})")
        self.reload_audit()

    def on_merge_children(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        dlg = MergeDialog(self, children=self.cache)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        ok = self.store.merge_children(
            keep_id=dlg.result["keep_id"],
            merge_id=dlg.result["merge_id"],
            actor=self._actor(),
        )
        if not ok:
            messagebox.showerror("Mesclar", "Não foi possível mesclar.")
            return
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.clear_form()
        self.set_status("Mesclado")
        self.reload_audit()

    def on_import(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        try:
            from .importer import import_from_xlsx  # lazy import (tk startup faster)

            res = import_from_xlsx(
                store=self.store,
                xlsx_path=self.app_root / self.cfg.xlsx_default_path,
                sheet_name=self.cfg.xlsx_default_sheet,
            )
            self.reload_cache()
            self.apply_filter()
            self.refresh_stats()
            self.set_status(
                f"Importação OK: {res.inserted} novos, {res.updated} atualizados, {res.skipped} pulados (total {res.total})"
            )
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            self.set_status("Erro ao importar")
        finally:
            self.refresh_stats()
            self.reload_history()
            self.reload_audit()

    def on_report_generate(self) -> None:
        db = self.store.load()
        start = (self.report_start_var.get() or "").strip() or None
        end = (self.report_end_var.get() or "").strip() or None
        reports = build_reports(db, start=start, end=end)
        key = (self.report_key_var.get() or "").strip()
        rep = reports.get(key)
        if not rep:
            messagebox.showerror("Relatório", "Relatório inválido.")
            return
        self._last_report = rep
        self.report_preview.delete("1.0", "end")
        self.report_preview.insert("1.0", f"{rep.title}\n\n")
        self.report_preview.insert("end", " | ".join(rep.headers) + "\n")
        self.report_preview.insert("end", "-" * 80 + "\n")
        for row in rep.rows[:200]:
            self.report_preview.insert("end", " | ".join(row) + "\n")
        if len(rep.rows) > 200:
            self.report_preview.insert("end", f"\n... ({len(rep.rows)} linhas)\n")

    def _default_export_name(self, ext: str) -> str:
        key = (self.report_key_var.get() or "report").strip()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{key}_{ts}.{ext}"

    def on_report_export_csv(self) -> None:
        if self._last_report is None:
            self.on_report_generate()
            if self._last_report is None:
                return
        default = self._default_export_name("csv")
        path = filedialog.asksaveasfilename(
            title="Salvar CSV",
            defaultextension=".csv",
            initialdir=str(self.app_root / self.cfg.exports_dir),
            initialfile=default,
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        export_csv(self._last_report, Path(path))
        self.set_status(f"CSV exportado: {path}")

    def on_report_export_pdf(self) -> None:
        if self._last_report is None:
            self.on_report_generate()
            if self._last_report is None:
                return
        default = self._default_export_name("pdf")
        path = filedialog.asksaveasfilename(
            title="Salvar PDF",
            defaultextension=".pdf",
            initialdir=str(self.app_root / self.cfg.exports_dir),
            initialfile=default,
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        export_pdf(self._last_report, Path(path))
        self._last_pdf_path = Path(path)
        self.set_status(f"PDF exportado: {path}")

    def on_report_print_pdf(self) -> None:
        if self._last_pdf_path is None or not self._last_pdf_path.exists():
            self.on_report_export_pdf()
        if self._last_pdf_path is None or not self._last_pdf_path.exists():
            return
        try:
            os.startfile(str(self._last_pdf_path), "print")  # type: ignore[attr-defined]
        except Exception:
            os.startfile(str(self._last_pdf_path))  # type: ignore[attr-defined]

    def on_backup_create(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        out = create_backup(
            db_path=self.app_root / self.cfg.db_path,
            attachments_dir=self.app_root / self.cfg.attachments_dir,
            backups_dir=self.app_root / self.cfg.backups_dir,
        )
        self.backup_status_var.set(f"Backup criado: {out}")
        self.store.log_event(actor=self._actor(), action="backup.create", details={"path": str(out)})
        self.reload_audit()

    def on_backup_restore(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        zip_path = filedialog.askopenfilename(
            title="Selecionar backup (.zip)",
            initialdir=str(self.app_root / self.cfg.backups_dir),
            filetypes=[("Backup zip", "*.zip")],
        )
        if not zip_path:
            return
        if not messagebox.askyesno("Restaurar", "Isso substituirá o banco e anexos atuais. Continuar?"):
            return
        restore_backup(
            backup_zip=Path(zip_path),
            db_path=self.app_root / self.cfg.db_path,
            attachments_dir=self.app_root / self.cfg.attachments_dir,
        )
        self.store.log_event(actor=self._actor(), action="backup.restore", details={"path": zip_path})
        self.reload_audit()
        messagebox.showinfo("Restaurar", "Restaurado. O sistema vai reiniciar.")
        self.restart_app()

    def reload_users(self) -> None:
        if not hasattr(self, "users_tree"):
            return
        for iid in self.users_tree.get_children():
            self.users_tree.delete(iid)
        for u in self.store.list_users():
            iid = u.get("id") or ""
            self.users_tree.insert(
                "", "end", iid=iid, values=(u.get("username") or "", u.get("role") or "", "sim" if u.get("active", True) else "não")
            )
        self._apply_zebra(self.users_tree)

    def on_user_new(self) -> None:
        self.user_id_var.set("")
        self.user_username_var.set("")
        self.user_role_var.set("viewer")
        self.user_active_var.set(True)
        self.user_pw_var.set("")
        self.user_pw2_var.set("")

    def on_user_select(self) -> None:
        sel = self.users_tree.selection() if hasattr(self, "users_tree") else []
        if not sel:
            return
        uid = sel[0]
        u = next((x for x in self.store.list_users() if x.get("id") == uid), None)
        if not u:
            return
        self.user_id_var.set(u.get("id") or "")
        self.user_username_var.set(u.get("username") or "")
        self.user_role_var.set(u.get("role") or "viewer")
        self.user_active_var.set(bool(u.get("active", True)))
        self.user_pw_var.set("")
        self.user_pw2_var.set("")

    def on_user_save(self) -> None:
        if not self._is_admin():
            messagebox.showwarning("Permissão", "Somente admin.")
            return
        username = (self.user_username_var.get() or "").strip()
        role = (self.user_role_var.get() or "").strip()
        active = bool(self.user_active_var.get())
        if not username:
            messagebox.showwarning("Validação", "Informe o usuário.")
            return
        pw = self.user_pw_var.get() or ""
        pw2 = self.user_pw2_var.get() or ""
        user = {
            "id": (self.user_id_var.get() or "").strip() or None,
            "username": username,
            "role": role,
            "active": active,
        }
        if pw or pw2:
            if pw != pw2:
                messagebox.showwarning("Validação", "As senhas não conferem.")
                return
            if len(pw) < 4:
                messagebox.showwarning("Validação", "Senha muito curta (mínimo 4).")
                return
            ph = hash_password(pw)
            user["salt_hex"] = ph.salt_hex
            user["hash_hex"] = ph.hash_hex
        self.store.upsert_user(user, actor=self._actor())
        self.reload_users()
        self.on_user_new()
        self.set_status("Usuário salvo")
        self.reload_audit()

    def reload_audit(self) -> None:
        if not hasattr(self, "audit_tree"):
            return
        for iid in self.audit_tree.get_children():
            self.audit_tree.delete(iid)
        db = self.store.load()
        entries = list(db.get("audit_log") or [])
        entries.sort(key=lambda e: (e.get("at") or ""), reverse=True)
        for e in entries[:500]:
            iid = e.get("id") or ""
            self.audit_tree.insert(
                "", "end", iid=iid, values=(e.get("at") or "", e.get("actor") or "", e.get("action") or "", e.get("entity_type") or "", e.get("entity_id") or "")
            )
        self._apply_zebra(self.audit_tree)
        self.audit_details.delete("1.0", "end")

    def on_audit_select(self) -> None:
        sel = self.audit_tree.selection() if hasattr(self, "audit_tree") else []
        if not sel:
            return
        eid = sel[0]
        db = self.store.load()
        e = next((x for x in (db.get("audit_log") or []) if x.get("id") == eid), None)
        if not e:
            return
        import json

        self.audit_details.delete("1.0", "end")
        self.audit_details.insert("1.0", json.dumps(e.get("details") or {}, ensure_ascii=False, indent=2))

    def _build_history_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Criança:").grid(row=0, column=0, sticky="w")
        self.history_child_var = tk.StringVar(value="(nenhuma selecionada)")
        ttk.Label(top, textvariable=self.history_child_var).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(top, text="+ Atendimento", command=self.on_new_attendance).grid(row=0, column=2, padx=(8, 0))
        self.btn_history_edit = ttk.Button(top, text="Editar", command=self.on_edit_attendance, state="disabled")
        self.btn_history_edit.grid(row=0, column=3, padx=(8, 0))

        mid = ttk.Frame(root, padding=(10, 0, 10, 10))
        mid.grid(row=1, column=0, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            mid,
            columns=("quando", "tipo", "prof", "resultado", "registrado", "tem_atend", "tem_vd"),
            show="headings",
            selectmode="browse",
        )
        self.history_tree.heading("quando", text="Quando")
        self.history_tree.column("quando", width=180, anchor="w")
        self.history_tree.heading("tipo", text="Tipo")
        self.history_tree.column("tipo", width=120, anchor="w")
        self.history_tree.heading("prof", text="Profissional")
        self.history_tree.column("prof", width=180, anchor="w")
        self.history_tree.heading("resultado", text="Resultado")
        self.history_tree.column("resultado", width=160, anchor="w")
        self.history_tree.heading("registrado", text="Registrado por")
        self.history_tree.column("registrado", width=140, anchor="w")
        self.history_tree.heading("tem_atend", text="Atendimento")
        self.history_tree.column("tem_atend", width=100, anchor="center")
        self.history_tree.heading("tem_vd", text="VD")
        self.history_tree.column("tem_vd", width=80, anchor="center")
        self._setup_treeview(self.history_tree)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        self.history_tree.bind("<<TreeviewSelect>>", lambda _e: self.on_history_select())
        self.history_tree.bind("<Double-1>", lambda _e: self.on_edit_attendance())

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        bottom = ttk.Frame(root, padding=(10, 0, 10, 10))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(1, weight=1)
        bottom.columnconfigure(3, weight=1)
        bottom.columnconfigure(0, weight=0)
        bottom.columnconfigure(2, weight=0)

        ttk.Label(bottom, text="Atendimento:").grid(row=0, column=0, sticky="nw", pady=(0, 6))
        self.history_txt_atend = tk.Text(bottom, height=8, wrap="word")
        self.history_txt_atend.grid(row=0, column=1, sticky="nsew", pady=(0, 6), padx=(8, 24))

        ttk.Label(bottom, text="VD:").grid(row=0, column=2, sticky="nw", pady=(0, 6))
        self.history_txt_vd = tk.Text(bottom, height=8, wrap="word")
        self.history_txt_vd.grid(row=0, column=3, sticky="nsew", pady=(0, 6), padx=(8, 0))

        self.history_txt_atend.configure(state="disabled")
        self.history_txt_vd.configure(state="disabled")

        attach = ttk.Frame(root, padding=(10, 0, 10, 10))
        attach.grid(row=3, column=0, sticky="nsew")
        attach.columnconfigure(0, weight=1)
        attach.rowconfigure(1, weight=1)

        ttk.Label(attach, text="Anexos:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        btns = ttk.Frame(attach)
        btns.grid(row=0, column=1, sticky="e")
        ttk.Button(btns, text="Adicionar", command=self.on_attachment_add).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Abrir", command=self.on_attachment_open).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Remover", command=self.on_attachment_remove).grid(row=0, column=2)

        self.attach_tree = ttk.Treeview(attach, columns=("nome", "quando", "por"), show="headings", selectmode="browse")
        self.attach_tree.heading("nome", text="Arquivo")
        self.attach_tree.column("nome", width=420, anchor="w")
        self.attach_tree.heading("quando", text="Adicionado em")
        self.attach_tree.column("quando", width=180, anchor="w")
        self.attach_tree.heading("por", text="Por")
        self.attach_tree.column("por", width=160, anchor="w")
        self._setup_treeview(self.attach_tree)
        self.attach_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")

        vsb3 = ttk.Scrollbar(attach, orient="vertical", command=self.attach_tree.yview)
        self.attach_tree.configure(yscrollcommand=vsb3.set)
        vsb3.grid(row=1, column=2, sticky="ns")

    def _sync_history_selection(self) -> None:
        if not self.selected_id:
            self.history_child_var.set("(nenhuma selecionada)")
            self.reload_history()
            return
        name = (self.nome_var.get() or "").strip()
        self.history_child_var.set(name or self.selected_id)
        self.reload_history()
        self._refresh_action_bar_state()

    def reload_history(self) -> None:
        for iid in self.history_tree.get_children():
            self.history_tree.delete(iid)

        self.selected_attendance_id = None
        self._set_history_texts("", "")
        self._reload_attachments()
        self._refresh_action_bar_state()
        if not self.selected_id:
            return

        items = self.store.list_attendances(self.selected_id)
        for att in items:
            iid = att.get("id") or ""
            when = att.get("occurred_at") or ""
            tipo = att.get("tipo") or ""
            prof = att.get("profissional") or ""
            res = att.get("resultado") or ""
            reg = att.get("registrado_por") or ""
            tem_atend = "sim" if (att.get("atendimento_text") or "").strip() else ""
            tem_vd = "sim" if (att.get("vd_text") or "").strip() else ""
            self.history_tree.insert("", "end", iid=iid, values=(when, tipo, prof, res, reg, tem_atend, tem_vd))
        self._apply_zebra(self.history_tree)

    def _set_history_texts(self, atendimento: str, vd: str) -> None:
        self.history_txt_atend.configure(state="normal")
        self.history_txt_vd.configure(state="normal")
        self.history_txt_atend.delete("1.0", "end")
        self.history_txt_vd.delete("1.0", "end")
        self.history_txt_atend.insert("1.0", atendimento or "")
        self.history_txt_vd.insert("1.0", vd or "")
        self.history_txt_atend.configure(state="disabled")
        self.history_txt_vd.configure(state="disabled")

    def on_history_select(self) -> None:
        sel = self.history_tree.selection()
        if not sel:
            return
        att_id = sel[0]
        self.selected_attendance_id = att_id
        items = self.store.list_attendances(self.selected_id or "")
        att = next((a for a in items if a.get("id") == att_id), None)
        if not att:
            return
        self._set_history_texts(att.get("atendimento_text") or "", att.get("vd_text") or "")
        self._reload_attachments()
        self._refresh_action_bar_state()

    def _reload_attachments(self) -> None:
        if not hasattr(self, "attach_tree"):
            return
        for iid in self.attach_tree.get_children():
            self.attach_tree.delete(iid)
        if not self.selected_attendance_id:
            return
        items = self.store.list_attachments(self.selected_attendance_id)
        for a in items:
            iid = a.get("id") or ""
            self.attach_tree.insert(
                "",
                "end",
                iid=iid,
                values=(a.get("original_name") or "", a.get("added_at") or "", a.get("added_by") or ""),
            )
        self._apply_zebra(self.attach_tree)

    def on_attachment_add(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if not self.selected_attendance_id:
            self.set_status("Selecione um atendimento no Histórico para anexar.")
            if hasattr(self, "tab_history"):
                self.notebook.select(self.tab_history)
            return
        src = filedialog.askopenfilename(title="Selecionar anexo")
        if not src:
            return
        actor = self._actor()
        dest = store_attachment(
            src_path=Path(src),
            attachments_dir=self.app_root / self.cfg.attachments_dir,
            attendance_id=self.selected_attendance_id,
        )
        rel = str(dest.relative_to(self.app_root))
        self.store.add_attachment(
            {
                "attendance_id": self.selected_attendance_id,
                "path": rel,
                "original_name": Path(src).name,
                "added_by": actor,
            },
            actor=actor,
        )
        self._reload_attachments()
        self.set_status("Anexo adicionado")
        self.reload_audit()

    def on_attachment_open(self) -> None:
        sel = getattr(self, "attach_tree", None).selection() if hasattr(self, "attach_tree") else []
        if not sel:
            messagebox.showinfo("Anexo", "Selecione um anexo.")
            return
        att_id = sel[0]
        items = self.store.load().get("attachments") or []
        a = next((x for x in items if x.get("id") == att_id), None)
        if not a:
            return
        p = self.app_root / (a.get("path") or "")
        if not p.exists():
            messagebox.showerror("Anexo", f"Arquivo não encontrado: {p}")
            return
        os.startfile(str(p))  # type: ignore[attr-defined]

    def on_attachment_remove(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        sel = getattr(self, "attach_tree", None).selection() if hasattr(self, "attach_tree") else []
        if not sel:
            messagebox.showinfo("Anexo", "Selecione um anexo.")
            return
        attach_id = sel[0]
        if not messagebox.askyesno("Anexo", "Remover este anexo?"):
            return
        db = self.store.load()
        a = next((x for x in (db.get("attachments") or []) if x.get("id") == attach_id), None)
        if a:
            p = self.app_root / (a.get("path") or "")
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        self.store.remove_attachment(attach_id, actor=self._actor())
        self._reload_attachments()
        self.set_status("Anexo removido")
        self.reload_audit()

    def on_new_attendance(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if not self.selected_id:
            messagebox.showinfo("Atendimento", "Selecione uma criança primeiro.")
            return
        actor = self._actor()

        dialog = AttendanceDialog(self, default_prof=actor)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        att = {
            "child_id": self.selected_id,
            "occurred_at": dialog.result["occurred_at"],
            "tipo": dialog.result["tipo"],
            "profissional": dialog.result["profissional"],
            "resultado": dialog.result.get("resultado") or "",
            "atendimento_text": dialog.result["atendimento_text"],
            "vd_text": dialog.result["vd_text"],
            "source": {"type": "manual"},
        }
        saved = self.store.add_attendance(att, actor=actor)
        self.reload_cache()
        self.apply_filter()
        self.reload_history()
        self.refresh_stats()
        self.set_status("Atendimento registrado")
        try:
            self.notebook.select(self.tab_history)
            if saved.get("id"):
                self.history_tree.selection_set(saved["id"])
                self.history_tree.see(saved["id"])
        except Exception:
            pass
        self.reload_audit()

    def on_edit_attendance(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if not self.selected_id:
            self.set_status("Selecione uma criança primeiro.")
            try:
                self.notebook.select(self.tab_cadastros)
            except Exception:
                pass
            return
        if not self.selected_attendance_id:
            self.set_status("Selecione um atendimento no Histórico para editar.")
            try:
                self.notebook.select(self.tab_history)
            except Exception:
                pass
            return

        actor = self._actor()
        items = self.store.list_attendances(self.selected_id)
        att = next((a for a in items if (a.get("id") or "") == (self.selected_attendance_id or "")), None)
        if not att:
            self.set_status("Atendimento não encontrado.")
            return

        dialog = AttendanceDialog(self, default_prof=(att.get("profissional") or actor), attendance=att)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        updated = self.store.update_attendance(
            self.selected_attendance_id,
            {
                "occurred_at": dialog.result["occurred_at"],
                "tipo": dialog.result["tipo"],
                "profissional": dialog.result["profissional"],
                "resultado": dialog.result.get("resultado") or "",
                "atendimento_text": dialog.result["atendimento_text"],
                "vd_text": dialog.result["vd_text"],
            },
            actor=actor,
        )
        if updated is None:
            messagebox.showerror("Editar", "Não consegui salvar as alterações.")
            return

        self.reload_cache()
        self.apply_filter()
        self.reload_history()
        self.refresh_stats()
        self.set_status("Atendimento atualizado")
        self.reload_audit()

    def _login_flow(self) -> dict | None:
        users = self.store.list_users()
        if not users:
            setup = SetupAdminDialog(self)
            self.wait_window(setup)
            if setup.result is None:
                return None
            ph = hash_password(setup.result["password"])
            self.store.upsert_user(
                {
                    "username": setup.result["username"],
                    "role": "admin",
                    "salt_hex": ph.salt_hex,
                    "hash_hex": ph.hash_hex,
                    "active": True,
                },
                actor=setup.result["username"],
            )
            users = self.store.list_users()

        # login loop
        for _ in range(3):
            dlg = LoginDialog(self, usernames=[u.get("username") or "" for u in users])
            self.wait_window(dlg)
            if dlg.result is None:
                return None

            username = dlg.result["username"]
            password = dlg.result["password"]
            user = next(
                (u for u in users if (u.get("username") or "").strip().lower() == username.strip().lower()),
                None,
            )
            if not user or not user.get("active", True):
                messagebox.showerror("Login", "Usuário inválido ou inativo.")
                continue
            if not verify_password(password, salt_hex=user.get("salt_hex", ""), hash_hex=user.get("hash_hex", "")):
                messagebox.showerror("Login", "Senha inválida.")
                continue
            return {"username": user.get("username"), "role": user.get("role")}

        messagebox.showerror("Login", "Muitas tentativas. Fechando.")
        return None

    def on_switch_user(self) -> None:
        self.withdraw()
        user = self._login_flow()
        if user is None:
            self.destroy()
            return
        self.current_user = user
        self.deiconify()
        if hasattr(self, "user_label_var"):
            self.user_label_var.set(self._user_label())
        self._apply_permissions()
        self.set_status("Usuário trocado")

    def _start_auto_update_checks(self) -> None:
        if not self.cfg.auto_update_enabled:
            return
        self.after(1200, self._schedule_update_check)

    def _schedule_update_check(self) -> None:
        self._run_update_check()
        self.after(int(self.cfg.update_check_minutes) * 60 * 1000, self._schedule_update_check)

    def _run_update_check(self) -> None:
        if self._update_check_running:
            return

        self._update_check_running = True

        def worker() -> None:
            try:
                result = check_for_update(self.app_root, fetch=True)
            except Exception as exc:
                result = None
                err = str(exc)
            else:
                err = ""

            def apply() -> None:
                self._update_check_running = False
                if result is None:
                    self.set_status(f"Auto-update: erro ao checar: {err}")
                    return
                self._apply_update_check(result)

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update_check(self, result) -> None:
        if not result.ok:
            self._update_available = False
            self.hide_update_banner()
            return

        behind = int(result.behind or 0)
        ahead = int(result.ahead or 0)

        if behind <= 0:
            self._update_available = False
            self.hide_update_banner()
            return

        self._update_available = True
        if ahead > 0:
            self.banner_message.set(
                f"Atualização disponível, mas há commits locais (ahead={ahead}). Atualize manualmente para evitar conflitos."
            )
            self.banner_update_btn.configure(state="disabled")
        else:
            self.banner_message.set(f"Atualização disponível ({behind} commits). Clique em Atualizar para baixar.")
            self.banner_update_btn.configure(state="normal")
        self.show_update_banner()

    def show_update_banner(self) -> None:
        if not self.banner_frame.winfo_ismapped():
            self.banner_frame.pack(fill="x", before=self.notebook)

    def hide_update_banner(self) -> None:
        if self.banner_frame.winfo_ismapped():
            self.banner_frame.pack_forget()

    def on_update_now(self) -> None:
        if self._update_check_running:
            return
        self.banner_update_btn.configure(state="disabled")
        self.banner_message.set("Baixando atualização (git pull)...")

        def worker() -> None:
            ok, msg = pull_ff_only(self.app_root)

            def apply() -> None:
                if not ok:
                    self.banner_update_btn.configure(state="normal")
                    self.banner_message.set(f"Falha ao atualizar: {msg}")
                    return

                self.banner_message.set("Atualizado. Reiniciar o sistema agora?")
                if messagebox.askyesno("Atualização", "Atualizado com sucesso. Deseja reiniciar agora?"):
                    self.restart_app()
                else:
                    self.hide_update_banner()
                    self._run_update_check()

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def restart_app(self) -> None:
        try:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            messagebox.showerror("Reinício", f"Não consegui reiniciar automaticamente: {e}")


class AttendanceDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, *, default_prof: str, attendance: dict | None = None):
        super().__init__(parent)
        is_edit = attendance is not None
        self.title("Editar atendimento" if is_edit else "Novo atendimento")
        self.resizable(True, True)
        self.result: dict | None = None

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Data/hora (ISO):").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.when_var = tk.StringVar(value=(attendance.get("occurred_at") if attendance else now_iso()))
        ttk.Entry(self, textvariable=self.when_var).grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 6))

        ttk.Label(self, text="Tipo:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        self.tipo_var = tk.StringVar(value=((attendance.get("tipo") if attendance else "") or "atendimento"))
        ttk.Combobox(self, textvariable=self.tipo_var, values=["atendimento", "vd", "outro"], state="readonly").grid(
            row=1, column=1, sticky="w", padx=10, pady=(0, 6)
        )

        ttk.Label(self, text="Profissional:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        self.prof_var = tk.StringVar(value=((attendance.get("profissional") if attendance else "") or default_prof))
        ttk.Entry(self, textvariable=self.prof_var).grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Resultado:").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 6))
        self.res_var = tk.StringVar(value=((attendance.get("resultado") if attendance else "") or ""))
        ttk.Entry(self, textvariable=self.res_var).grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Atendimento:").grid(row=4, column=0, sticky="nw", padx=10, pady=(0, 6))
        self.txt_at = tk.Text(self, height=8, wrap="word")
        self.txt_at.grid(row=4, column=1, sticky="nsew", padx=10, pady=(0, 6))
        if attendance:
            self.txt_at.insert("1.0", attendance.get("atendimento_text") or "")

        ttk.Label(self, text="VD:").grid(row=5, column=0, sticky="nw", padx=10, pady=(0, 6))
        self.txt_vd = tk.Text(self, height=8, wrap="word")
        self.txt_vd.grid(row=5, column=1, sticky="nsew", padx=10, pady=(0, 6))
        if attendance:
            self.txt_vd.insert("1.0", attendance.get("vd_text") or "")

        btns = ttk.Frame(self)
        btns.grid(row=6, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Salvar", command=self._save).grid(row=0, column=1)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-Return>", lambda _e: self._save())

    def _save(self) -> None:
        when = (self.when_var.get() or "").strip()
        prof = (self.prof_var.get() or "").strip()
        if not when:
            messagebox.showwarning("Validação", "Preencha a data/hora.")
            return
        if not prof:
            messagebox.showwarning("Validação", "Preencha o profissional.")
            return
        atendimento_text = self.txt_at.get("1.0", "end").rstrip("\n")
        vd_text = self.txt_vd.get("1.0", "end").rstrip("\n")
        resultado = (self.res_var.get() or "").strip()
        if not (resultado or atendimento_text.strip() or vd_text.strip()):
            messagebox.showwarning("Validação", "Informe pelo menos Resultado, Atendimento ou VD.")
            return
        self.result = {
            "occurred_at": when,
            "tipo": (self.tipo_var.get() or "").strip(),
            "profissional": prof,
            "resultado": resultado,
            "atendimento_text": atendimento_text,
            "vd_text": vd_text,
        }
        self.destroy()


class SetupAdminDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Primeiro acesso - Criar admin")
        self.resizable(False, False)
        self.result: dict | None = None

        ttk.Label(self, text="Usuário admin:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.user_var = tk.StringVar(value="admin")
        ttk.Entry(self, textvariable=self.user_var).grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 6))

        ttk.Label(self, text="Senha:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        self.pw_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw_var, show="*").grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Confirmar:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))
        self.pw2_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw2_var, show="*").grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 10))

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Criar", command=self._create).grid(row=0, column=1)

        self.columnconfigure(1, weight=1)

    def _create(self) -> None:
        u = (self.user_var.get() or "").strip()
        pw = self.pw_var.get() or ""
        pw2 = self.pw2_var.get() or ""
        if not u:
            messagebox.showwarning("Validação", "Informe o usuário.")
            return
        if len(pw) < 4:
            messagebox.showwarning("Validação", "Senha muito curta (mínimo 4).")
            return
        if pw != pw2:
            messagebox.showwarning("Validação", "As senhas não conferem.")
            return
        self.result = {"username": u, "password": pw}
        self.destroy()


class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, *, usernames: list[str]):
        super().__init__(parent)
        self.title("Login")
        self.resizable(False, False)
        self.result: dict | None = None

        ttk.Label(self, text="Usuário:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.user_var = tk.StringVar(value=(usernames[0] if usernames else ""))
        ttk.Combobox(self, textvariable=self.user_var, values=usernames, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=10, pady=(10, 6)
        )

        ttk.Label(self, text="Senha:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        self.pw_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw_var, show="*").grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Entrar", command=self._login).grid(row=0, column=1)

        self.columnconfigure(1, weight=1)
        self.bind("<Return>", lambda _e: self._login())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _login(self) -> None:
        u = (self.user_var.get() or "").strip()
        pw = self.pw_var.get() or ""
        if not u or not pw:
            messagebox.showwarning("Validação", "Informe usuário e senha.")
            return
        self.result = {"username": u, "password": pw}
        self.destroy()


class MergeDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, *, children: list[dict]):
        super().__init__(parent)
        self.title("Mesclar crianças (duplicados)")
        self.resizable(False, False)
        self.result: dict | None = None

        options = []
        self._id_by_label: dict[str, str] = {}
        for c in children:
            cid = c.get("id") or ""
            label = f"{c.get('nome') or ''} | {c.get('escola') or ''} | {cid}"
            options.append(label)
            self._id_by_label[label] = cid
        options.sort(key=str.lower)

        ttk.Label(self, text="Manter:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.keep_var = tk.StringVar(value=(options[0] if options else ""))
        ttk.Combobox(self, textvariable=self.keep_var, values=options, state="readonly", width=70).grid(
            row=0, column=1, sticky="ew", padx=10, pady=(10, 6)
        )

        ttk.Label(self, text="Mesclar:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        self.merge_var = tk.StringVar(value=(options[1] if len(options) > 1 else ""))
        ttk.Combobox(self, textvariable=self.merge_var, values=options, state="readonly", width=70).grid(
            row=1, column=1, sticky="ew", padx=10, pady=(0, 10)
        )

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Mesclar", command=self._merge).grid(row=0, column=1)

    def _merge(self) -> None:
        keep = self._id_by_label.get(self.keep_var.get() or "", "")
        merge = self._id_by_label.get(self.merge_var.get() or "", "")
        if not keep or not merge or keep == merge:
            messagebox.showwarning("Validação", "Selecione dois registros diferentes.")
            return
        if not messagebox.askyesno("Mesclar", "Confirmar mesclagem? Isso não pode ser desfeito facilmente."):
            return
        self.result = {"keep_id": keep, "merge_id": merge}
        self.destroy()


def run() -> None:
    app_root = Path(__file__).resolve().parents[2]
    App(app_root).mainloop()
