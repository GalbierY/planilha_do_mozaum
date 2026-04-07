from __future__ import annotations

import colorsys
import hashlib
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core.auth import hash_password, verify_password
from .core.backup import create_backup, restore_backup
from .core.config import AppConfig
from .core.files import store_attachment
from .i18n import I18N, normalize_language
from .core.reports import build_reports, export_csv, export_pdf
from .core.store import JsonStore
from .core.updater import check_for_update, pull_ff_only
from .core.util import br_date_to_iso, iso_to_br_date
from .core.stats import compute_stats
from .core.runtime import ensure_user_files, get_data_root, get_resource_root
from .dialogs import AttendanceDialog, ExportFormatDialog, LoginDialog, MergeDialog, SetupAdminDialog
from .tabs import (
    build_audit_tab,
    build_backup_tab,
    build_cadastros_tab,
    build_history_tab,
    build_reports_tab,
    build_stats_tab,
    build_users_tab,
    build_workflow_tab,
)


class App(tk.Tk):
    def __init__(self, app_root: Path, data_root: Path):
        super().__init__()

        self.app_root = app_root
        self.data_root = data_root
        self.cfg = AppConfig.load(self.data_root)
        self.cfg.ui_language = normalize_language(self.cfg.ui_language)
        self.i18n = I18N(self.cfg.ui_language)
        self.store = JsonStore(self.data_root / self.cfg.db_path)
        self.current_user: dict | None = None
        self._i18n_tab_sources: dict[tuple[str, str], str] = {}
        self._i18n_heading_sources: dict[tuple[str, str], str] = {}
        self._install_messagebox_i18n()

        self.title(self.cfg.app_name)
        self.geometry("1200x720")
        self._try_set_icon()

        self.selected_id: str | None = None
        self.selected_attendance_id: str | None = None
        self.cache: list[dict] = []
        self._update_check_running = False
        self._update_available = False

        try:
            self._setup_styles()
        except Exception:
            self.option_add("*Font", ("Segoe UI", 10))
            self.configure(bg="#F4F7FB")

        # Login / setup
        self.withdraw()
        self.current_user = self._login_flow()
        if self.current_user is None:
            self.destroy()
            return
        self.deiconify()

        self._build_ui()
        self._bind_shortcuts()
        self._apply_permissions()
        self._refresh_action_bar_state()
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self._start_auto_update_checks()

    def _t(self, text: str) -> str:
        return self.i18n.tr(text)

    def _install_messagebox_i18n(self) -> None:
        def wrap(fn):
            def _wrapped(title=None, message=None, *args, **kwargs):
                app = getattr(messagebox, "_sas_i18n_app", None)
                if app is not None:
                    if isinstance(title, str):
                        title = app._t(title)
                    if isinstance(message, str):
                        message = app._t(message)
                    detail = kwargs.get("detail")
                    if isinstance(detail, str):
                        kwargs["detail"] = app._t(detail)
                return fn(title, message, *args, **kwargs)

            return _wrapped

        if not getattr(messagebox, "_sas_i18n_wrapped", False):
            messagebox.showinfo = wrap(messagebox.showinfo)
            messagebox.showwarning = wrap(messagebox.showwarning)
            messagebox.showerror = wrap(messagebox.showerror)
            messagebox.askyesno = wrap(messagebox.askyesno)
            messagebox._sas_i18n_wrapped = True
        messagebox._sas_i18n_app = self

    def _save_config(self) -> None:
        self.cfg.save(self.data_root)

    def _translate_window_title(self, win: tk.Misc) -> None:
        if not hasattr(win, "title"):
            return
        try:
            source = getattr(win, "_i18n_source_title", None)
            if source is None:
                source = str(win.title() or "")
                setattr(win, "_i18n_source_title", source)
            if source:
                win.title(self._t(source))
        except Exception:
            return

    def _translate_widget_tree(self, widget: tk.Misc) -> None:
        try:
            keys = set(widget.keys()) if hasattr(widget, "keys") else set()
            if "text" in keys:
                text = str(widget.cget("text") or "")
                source_text = getattr(widget, "_i18n_source_text", None)
                if source_text is None and text:
                    source_text = text
                    setattr(widget, "_i18n_source_text", source_text)
                if source_text:
                    widget.configure(text=self._t(source_text))
        except Exception:
            pass

        if isinstance(widget, ttk.Notebook):
            for tab_id in widget.tabs():
                try:
                    key = (str(widget), str(tab_id))
                    source_tab = self._i18n_tab_sources.get(key)
                    if source_tab is None:
                        source_tab = str(widget.tab(tab_id, "text") or "")
                        self._i18n_tab_sources[key] = source_tab
                    widget.tab(tab_id, text=self._t(source_tab))
                except Exception:
                    continue

        if isinstance(widget, ttk.Treeview):
            try:
                cols = list(widget["columns"] or [])
            except Exception:
                cols = []
            for col in cols:
                try:
                    key = (str(widget), str(col))
                    source_heading = self._i18n_heading_sources.get(key)
                    if source_heading is None:
                        source_heading = str((widget.heading(col) or {}).get("text") or "")
                        self._i18n_heading_sources[key] = source_heading
                    if source_heading:
                        widget.heading(col, text=self._t(source_heading))
                except Exception:
                    continue

        for child in widget.winfo_children():
            self._translate_widget_tree(child)

    def _apply_language_to_window(self, win: tk.Misc) -> None:
        self._translate_window_title(win)
        self._translate_widget_tree(win)

    def _apply_language(self) -> None:
        self._apply_language_to_window(self)
        if hasattr(self, "filter_tag_none_label"):
            prev_none = self.filter_tag_none_label
            self.filter_tag_none_label = self._t("(Sem tag)")
            if hasattr(self, "filter_tag_var") and (self.filter_tag_var.get() or "").strip() == prev_none:
                self.filter_tag_var.set(self.filter_tag_none_label)
            self._refresh_tag_controls()
        if hasattr(self, "user_label_var"):
            self.user_label_var.set(self._user_label())

    def _set_language(self, lang: str) -> None:
        new_lang = normalize_language(lang)
        if new_lang == self.i18n.language:
            return
        self.i18n.set_language(new_lang)
        self.cfg.ui_language = new_lang
        try:
            self._save_config()
        except Exception:
            messagebox.showwarning("Idioma", "Não foi possível salvar o idioma no config.")
        self._apply_language()
        self.set_status("Idioma atualizado.")

    def on_toggle_language(self) -> None:
        target = "en" if self.i18n.language != "en" else "pt-BR"
        if target == "en":
            question = "Deseja trocar o idioma para inglês?"
        else:
            question = "Deseja trocar o idioma para português (Brasil)?"
        if not messagebox.askyesno("Idioma", question):
            return
        self._set_language(target)

    def _try_set_icon(self) -> None:
        candidates = [
            self.app_root / "icon.ico",
            self.app_root / "icon.png",
            self.app_root / "app.ico",
            self.app_root / "app.png",
            self.app_root / "assets" / "icon.ico",
            self.app_root / "assets" / "icon.png",
        ]
        icon_path = next((p for p in candidates if p.exists()), None)
        if icon_path is None:
            return
        try:
            if icon_path.suffix.lower() == ".ico":
                self.iconbitmap(str(icon_path))
            else:
                self._icon_img = tk.PhotoImage(file=str(icon_path))  # keep reference
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        def sconf(style_name: str, **kwargs) -> None:
            try:
                style.configure(style_name, **kwargs)
            except Exception:
                for key, value in kwargs.items():
                    try:
                        style.configure(style_name, **{key: value})
                    except Exception:
                        pass

        def smap(style_name: str, **kwargs) -> None:
            try:
                style.map(style_name, **kwargs)
            except Exception:
                pass

        self.colors = {
            "bg": "#F4F7FB",
            "panel": "#FFFFFF",
            "panel_soft": "#EEF3FB",
            "line": "#D5DEED",
            "text": "#1E2A3A",
            "muted": "#5E6B7F",
            "primary": "#1D5FBF",
            "primary_hover": "#174E9C",
            "header": "#0E2A47",
            "header_button": "#1A3D61",
            "header_button_hover": "#245078",
            "warning_bg": "#FFF3CD",
            "warning_fg": "#664D03",
            "invalid_bg": "#FFE6EB",
            "status_bg": "#E9EFF9",
        }

        self.option_add("*Font", ("Segoe UI", 10))

        try:
            self.configure(bg=self.colors["bg"])
        except Exception:
            pass

        sconf(".", background=self.colors["bg"], foreground=self.colors["text"])

        sconf("Root.TFrame", background=self.colors["bg"])
        sconf("Header.TFrame", background=self.colors["header"])
        sconf("HeaderTitle.TLabel", background=self.colors["header"], foreground="#F4F7FF", font=("Segoe UI Semibold", 15))
        sconf("HeaderSubtitle.TLabel", background=self.colors["header"], foreground="#C8D5EB", font=("Segoe UI", 9))
        sconf("HeaderMeta.TLabel", background=self.colors["header"], foreground="#E6EEFA", font=("Segoe UI Semibold", 9))
        sconf("Muted.TLabel", foreground=self.colors["muted"], background=self.colors["bg"])
        sconf("Status.TLabel", foreground=self.colors["text"], background=self.colors["status_bg"], padding=(10, 6))
        sconf("MetricLabel.TLabel", foreground=self.colors["muted"], background=self.colors["panel"])
        sconf("MetricValue.TLabel", foreground=self.colors["text"], background=self.colors["panel"], font=("Segoe UI Semibold", 14))

        sconf(
            "Card.TLabelframe",
            background=self.colors["panel"],
            bordercolor=self.colors["line"],
            relief="solid",
            borderwidth=1,
        )
        sconf(
            "Card.TLabelframe.Label",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            font=("Segoe UI Semibold", 10),
        )

        sconf(
            "TButton",
            background=self.colors["panel_soft"],
            foreground=self.colors["text"],
            borderwidth=1,
            focusthickness=1,
            focuscolor=self.colors["line"],
            padding=(10, 6),
        )
        smap("TButton", background=[("active", "#E2EAF8"), ("pressed", "#D6E2F6")])

        sconf("Primary.TButton", background=self.colors["primary"], foreground="#FFFFFF", borderwidth=0, padding=(12, 7))
        smap(
            "Primary.TButton",
            background=[
                ("disabled", "#AFC2E4"),
                ("pressed", self.colors["primary_hover"]),
                ("active", self.colors["primary_hover"]),
            ],
            foreground=[("disabled", "#F4F7FF")],
        )
        sconf("Secondary.TButton", background=self.colors["panel_soft"], foreground=self.colors["text"], padding=(10, 6))
        smap("Secondary.TButton", background=[("active", "#DFE8F8"), ("pressed", "#D4E1F7")])

        sconf("Header.TButton", background=self.colors["header_button"], foreground="#EDF3FF", borderwidth=0, padding=(10, 5))
        smap("Header.TButton", background=[("active", self.colors["header_button_hover"]), ("pressed", self.colors["header_button_hover"])])

        sconf(
            "TEntry",
            fieldbackground=self.colors["panel"],
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            borderwidth=1,
            padding=4,
        )
        sconf(
            "TCombobox",
            fieldbackground=self.colors["panel"],
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            borderwidth=1,
            padding=3,
        )
        sconf("Invalid.TEntry", fieldbackground=self.colors["invalid_bg"])
        sconf("Invalid.TCombobox", fieldbackground=self.colors["invalid_bg"])

        sconf("TNotebook", background=self.colors["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        sconf("TNotebook.Tab", padding=(16, 8), background=self.colors["panel_soft"], foreground=self.colors["muted"])
        smap("TNotebook.Tab", background=[("selected", self.colors["panel"])], foreground=[("selected", self.colors["text"])])

        sconf(
            "Treeview",
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            rowheight=26,
            borderwidth=0,
            relief="flat",
        )
        smap("Treeview", background=[("selected", "#D9E8FF")], foreground=[("selected", self.colors["text"])])
        sconf(
            "Treeview.Heading",
            font=("Segoe UI Semibold", 10),
            background=self.colors["panel_soft"],
            foreground=self.colors["text"],
            relief="flat",
            borderwidth=0,
        )
    def _build_ui(self) -> None:
        self.banner_frame = tk.Frame(self, bg=self.colors["warning_bg"], bd=1, relief="solid")
        self.banner_frame.pack(fill="x")
        self.banner_message = tk.StringVar(value="")
        tk.Label(
            self.banner_frame,
            textvariable=self.banner_message,
            bg=self.colors["warning_bg"],
            fg=self.colors["warning_fg"],
            anchor="w",
            padx=10,
            pady=6,
        ).pack(side="left", fill="x", expand=True)
        self.banner_update_btn = ttk.Button(self.banner_frame, text="Atualizar", command=self.on_update_now, style="Secondary.TButton")
        self.banner_update_btn.pack(side="right", padx=(0, 10), pady=6)
        ttk.Button(self.banner_frame, text="Fechar", command=self.hide_update_banner, style="Secondary.TButton").pack(
            side="right", padx=(0, 8), pady=6
        )
        self.banner_frame.pack_forget()

        self.header_frame = ttk.Frame(self, style="Header.TFrame", padding=(14, 12))
        self.header_frame.pack(fill="x", padx=10, pady=(10, 8))
        self.header_frame.columnconfigure(0, weight=1)

        ttk.Label(self.header_frame, text=self.cfg.app_name, style="HeaderTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self.header_frame,
            text="Fluxo simplificado: busque, selecione, atualize e acompanhe o historico em uma tela unica.",
            style="HeaderSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        header_actions = ttk.Frame(self.header_frame, style="Header.TFrame")
        header_actions.grid(row=0, column=1, rowspan=2, sticky="e")

        self.user_label_var = tk.StringVar(value=self._user_label())
        ttk.Label(header_actions, textvariable=self.user_label_var, style="HeaderMeta.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="e", pady=(0, 6)
        )
        ttk.Button(header_actions, text="Atalhos (F1)", command=self.on_show_shortcuts, style="Header.TButton").grid(
            row=1, column=0, padx=(0, 8)
        )
        ttk.Button(header_actions, text="Trocar usuario", command=self.on_switch_user, style="Header.TButton").grid(
            row=1, column=1
        )
        ttk.Button(header_actions, text="Idioma", command=self.on_toggle_language, style="Header.TButton").grid(
            row=1, column=2, padx=(8, 0)
        )

        self.notebook = ttk.Notebook(self)
        self.tab_cadastros = ttk.Frame(self.notebook)
        self.tab_stats = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_reports = ttk.Frame(self.notebook)
        self.tab_backup = ttk.Frame(self.notebook)
        self.tab_audit = ttk.Frame(self.notebook)
        self.tab_workflow = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cadastros, text="Cadastros")
        self.notebook.add(self.tab_stats, text="Estatisticas")
        self.notebook.add(self.tab_history, text="Historico")
        self.notebook.add(self.tab_reports, text="Relatorios")
        self.notebook.add(self.tab_backup, text="Backup")
        self.notebook.add(self.tab_audit, text="Auditoria")
        self.notebook.add(self.tab_workflow, text="Workflow")
        if self._is_admin():
            self.tab_users = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_users, text="Usuarios")
        self.notebook.pack(fill="both", expand=True, padx=10)

        build_cadastros_tab(self, self.tab_cadastros)
        self._build_stats_ui(self.tab_stats)
        self._build_history_ui(self.tab_history)
        self._build_reports_ui(self.tab_reports)
        self._build_backup_ui(self.tab_backup)
        self._build_audit_ui(self.tab_audit)
        self._build_workflow_ui(self.tab_workflow)
        if self._is_admin() and hasattr(self, "tab_users"):
            self._build_users_ui(self.tab_users)

        self.action_bar = ttk.Frame(self, style="Root.TFrame", padding=(12, 8))
        self.action_bar.pack(fill="x", side="bottom", padx=10, pady=(8, 10))
        self.action_bar.columnconfigure(30, weight=1)

        self.btn_new_form = ttk.Button(self.action_bar, text="Novo formulario", command=self.on_new_child_form, style="Secondary.TButton")
        self.btn_new_form.grid(row=0, column=0, sticky="w")
        self.btn_add_child = ttk.Button(self.action_bar, text="+ Crianca", command=self.on_add, style="Primary.TButton")
        self.btn_add_child.grid(row=0, column=1, padx=(8, 0))
        self.btn_save_child = ttk.Button(self.action_bar, text="Salvar cadastro", command=self.on_save, style="Primary.TButton")
        self.btn_save_child.grid(row=0, column=2, padx=(8, 0))
        self.btn_new_att = ttk.Button(self.action_bar, text="+ Atendimento", command=self.on_new_attendance, state="disabled", style="Secondary.TButton")
        self.btn_new_att.grid(row=0, column=3, padx=(12, 0))
        self.btn_edit_att = ttk.Button(
            self.action_bar,
            text="Editar atendimento",
            command=self.on_edit_attendance,
            state="disabled",
            style="Secondary.TButton",
        )
        self.btn_edit_att.grid(row=0, column=4, padx=(8, 0))
        self.btn_attach = ttk.Button(self.action_bar, text="Anexar arquivo", command=self.on_attachment_add, state="disabled", style="Secondary.TButton")
        self.btn_attach.grid(row=0, column=5, padx=(8, 0))
        self.btn_backup_quick = ttk.Button(self.action_bar, text="Backup rapido", command=self.on_backup_create, style="Secondary.TButton")
        self.btn_backup_quick.grid(row=0, column=6, padx=(12, 0))

        ttk.Label(
            self.action_bar,
            text="Atalhos: Ctrl+F busca | Ctrl+N novo | Ctrl+S salvar | Ctrl+Enter atendimento",
            style="Muted.TLabel",
        ).grid(row=0, column=30, sticky="e")

        ttk.Separator(self.action_bar, orient="horizontal").grid(row=1, column=0, columnspan=31, sticky="ew", pady=(8, 0))

        self.status_var = tk.StringVar(value=self._t("Pronto."))
        ttk.Label(self.action_bar, textvariable=self.status_var, style="Status.TLabel").grid(
            row=2, column=0, columnspan=31, sticky="ew", pady=(6, 0)
        )

        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._refresh_action_bar_state())
        self._apply_language()

    def on_show_shortcuts(self) -> None:
        messagebox.showinfo(
            "Atalhos disponiveis",
            "Ctrl+F: focar busca\n"
            "Ctrl+N: novo formulario\n"
            "Ctrl+S: salvar cadastro\n"
            "Ctrl+Enter: novo atendimento\n"
            "Ctrl+E: editar atendimento\n"
            "Alt+1..7: trocar abas",
        )

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
        bind("<Alt-7>", lambda: self.notebook.select(self.tab_workflow))
        if hasattr(self, "tab_users"):
            bind("<Alt-8>", lambda: self.notebook.select(self.tab_users))
        bind("<F1>", self.on_show_shortcuts)

    def _current_tab_text(self) -> str:
        try:
            tab_id = self.notebook.select()
            return str(self.notebook.tab(tab_id, "text") or "")
        except Exception:
            return ""

    def _set_widget_state(self, widget: tk.Widget | None, enabled: bool) -> None:
        if widget is None:
            return
        try:
            widget.configure(state="normal" if enabled else "disabled")
        except Exception:
            pass

    def _refresh_action_bar_state(self) -> None:
        can_edit = self._can_edit()
        current_tab = ""
        try:
            current_tab = str(self.notebook.select())
        except Exception:
            current_tab = ""
        in_cadastros = bool(hasattr(self, "tab_cadastros") and current_tab == str(self.tab_cadastros))
        in_workflow = bool(hasattr(self, "tab_workflow") and current_tab == str(self.tab_workflow))

        self._set_widget_state(getattr(self, "btn_import", None), can_edit and (in_cadastros or in_workflow))
        self._set_widget_state(getattr(self, "btn_new_form", None), can_edit)
        self._set_widget_state(getattr(self, "btn_add_child", None), can_edit)
        self._set_widget_state(getattr(self, "btn_save_child", None), can_edit and in_cadastros)
        self._set_widget_state(getattr(self, "btn_save_inline", None), can_edit and in_cadastros)
        self._set_widget_state(getattr(self, "btn_new_att", None), can_edit and bool(self.selected_id))
        self._set_widget_state(getattr(self, "btn_edit_att", None), can_edit and bool(self.selected_attendance_id))
        self._set_widget_state(getattr(self, "btn_attach", None), can_edit and bool(self.selected_attendance_id))
        self._set_widget_state(getattr(self, "btn_backup_quick", None), can_edit)
        self._set_widget_state(getattr(self, "btn_merge", None), can_edit)
        self._set_widget_state(getattr(self, "btn_add_tag", None), can_edit)
        if hasattr(self, "tags_chip_wrap"):
            self._render_tag_chips()
        self._set_widget_state(getattr(self, "btn_history_edit", None), can_edit and bool(self.selected_attendance_id))

    def on_export_selected(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        
        # Obter IDs selecionados
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Exportar", "Selecione crianças para exportar.")
            return
            
        # Coletar dados das crianças selecionadas
        selected_children = []
        for item_id in selected_items:
            child = next((c for c in self.cache if c.get("id") == item_id), None)
            if child:
                selected_children.append(child)
        
        if not selected_children:
            messagebox.showwarning("Exportar", "Nenhuma criança encontrada para exportar.")
            return
        
        # Perguntar formato de exportação
        format_dialog = ExportFormatDialog(self)
        self.wait_window(format_dialog)
        if format_dialog.result is None:
            return
            
        format_type = format_dialog.result["format"]
        
        # Exportar dados
        try:
            from .core.reports import export_selected_children
            
            default_name = f"exportacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if format_type == "csv":
                path = filedialog.asksaveasfilename(
                    title="Salvar exportação CSV",
                    defaultextension=".csv",
                    initialdir=str(self.data_root / self.cfg.exports_dir),
                    initialfile=default_name + ".csv",
                    filetypes=[("CSV", "*.csv")],
                )
                if not path:
                    return
                export_selected_children(selected_children, Path(path), format_type="csv")
                self.set_status(f"Exportação CSV concluída: {path}")
                
            elif format_type == "json":
                path = filedialog.asksaveasfilename(
                    title="Salvar exportação JSON",
                    defaultextension=".json",
                    initialdir=str(self.data_root / self.cfg.exports_dir),
                    initialfile=default_name + ".json",
                    filetypes=[("JSON", "*.json")],
                )
                if not path:
                    return
                export_selected_children(selected_children, Path(path), format_type="json")
                self.set_status(f"Exportação JSON concluída: {path}")
                
            elif format_type == "xlsx":
                path = filedialog.asksaveasfilename(
                    title="Salvar exportação Excel",
                    defaultextension=".xlsx",
                    initialdir=str(self.data_root / self.cfg.exports_dir),
                    initialfile=default_name + ".xlsx",
                    filetypes=[("Excel", "*.xlsx")],
                )
                if not path:
                    return
                export_selected_children(selected_children, Path(path), format_type="xlsx")
                self.set_status(f"Exportação Excel concluída: {path}")
                
        except Exception as e:
            messagebox.showerror("Exportar", f"Erro ao exportar: {str(e)}")
            self.set_status("Erro ao exportar")

    def on_generate_report(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        
        # Abrir aba de relatórios
        try:
            self.notebook.select(self.tab_reports)
        except Exception:
            pass
            
        # Configurar filtros atuais como parâmetros do relatório
        workflow_status = (getattr(self, "filter_workflow_var", tk.StringVar(value="")).get() or "").strip().lower()
        
        # Definir tipo de relatório baseado no filtro
        if workflow_status == "pendente":
            self.report_key_var.set("Pendencias de atendimento")
        elif workflow_status == "concluido":
            self.report_key_var.set("Detalhamento de atendimentos")
        else:
            self.report_key_var.set("Resumo por escola")
            
        # Aplicar filtros de período
        start = (getattr(self, "filter_start_var", tk.StringVar(value="")).get() or "").strip()
        end = (getattr(self, "filter_end_var", tk.StringVar(value="")).get() or "").strip()
        self.report_start_var.set(start)
        self.report_end_var.set(end)
        
        # Gerar relatório
        self.on_report_generate()
        self.set_status("Relatorio gerado com base nos filtros atuais")

    def _build_stats_ui(self, root: ttk.Frame) -> None:
        build_stats_tab(self, root)

    def _build_reports_ui(self, root: ttk.Frame) -> None:
        build_reports_tab(self, root)

    def _build_backup_ui(self, root: ttk.Frame) -> None:
        build_backup_tab(self, root)

    def _build_users_ui(self, root: ttk.Frame) -> None:
        build_users_tab(self, root)

    def _build_audit_ui(self, root: ttk.Frame) -> None:
        build_audit_tab(self, root)

    def _build_workflow_ui(self, root: ttk.Frame) -> None:
        build_workflow_tab(self, root)

    def reload_workflow(self) -> None:
        if not hasattr(self, "workflow_tree"):
            return
        for iid in self.workflow_tree.get_children():
            self.workflow_tree.delete(iid)

        # Exibir nomes da planilha padrão com seus status
        try:
            from .core.xlsx_reader import read_xlsx_table  # lazy import
            
            xlsx_path = self.data_root / self.cfg.xlsx_default_path
            if xlsx_path.exists():
                # Resolver nome real da aba antes de ler
                resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

                # Ler a planilha padrão
                rows = read_xlsx_table(xlsx_path, sheet_name=resolved_sheet)

                # Obter nomes únicos da coluna "Crianças" ou colunas alternativas
                colunas_possiveis = ["Crianças", "Nome", "Aluno", "Estudante", "Criança"]
                nomes_planilha = set()
                
                for row in rows:
                    for col in colunas_possiveis:
                        nome = row.get(col, "").strip()
                        if nome:
                            nomes_planilha.add(nome)
                            break
                
                # Verificar status de cada nome na planilha
                for nome_str in sorted(nomes_planilha):
                    if not nome_str:
                        continue
                        
                    # Verificar se já foi importado (existe no cache)
                    child = next((c for c in self.cache if c.get("nome") == nome_str), None)
                    status = child.get("workflow_status", False) if child else False
                    status_text = "Concluído" if status else "Pendente"
                    tag = "completed" if status else "pending"
                    
                    iid = self.workflow_tree.insert(
                        "", "end", values=(nome_str, status_text), tags=(tag,)
                    )
            else:
                # Planilha não encontrada
                iid = self.workflow_tree.insert(
                    "", "end", values=("Planilha não encontrada", ""), tags=("pending",)
                )
        except Exception as e:
            # Erro ao ler a planilha
            iid = self.workflow_tree.insert(
                "", "end", values=(f"Erro ao ler planilha: {str(e)}", ""), tags=("pending",)
            )
        
        self._apply_zebra(self.workflow_tree)

    def on_workflow_select(self) -> None:
        sel = self.workflow_tree.selection() if hasattr(self, "workflow_tree") else []
        if not sel:
            return
        file_path = sel[0]
        self.workflow_file_var.set(file_path)
        self.workflow_status_var.set("Arquivo selecionado")
        self.workflow_last_import_var.set("")
        self.btn_workflow_import.configure(state="normal")
        self.btn_workflow_clear.configure(state="normal")

    def on_workflow_import(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        file_path = self.workflow_file_var.get()
        if not file_path:
            messagebox.showwarning("Workflow", "Selecione um arquivo na lista.")
            return
        try:
            from .core.importer import import_from_xlsx  # lazy import (tk startup faster)

            xlsx_path = Path(file_path)
            resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

            res = import_from_xlsx(
                store=self.store,
                xlsx_path=xlsx_path,
                sheet_name=resolved_sheet,
            )

            self.reload_cache()
            self.apply_filter()
            self.refresh_stats()
            self.set_status(
                f"Importação OK: {res.inserted} novos, {res.updated} atualizados, {res.skipped} pulados (total {res.total})"
            )
            self.reload_workflow()
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            self.set_status("Erro ao importar")
        finally:
            self.refresh_stats()
            self.reload_history()
            self.reload_audit()

    def on_workflow_select_file(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        try:
            from .core.importer import import_from_xlsx  # lazy import (tk startup faster)

            xlsx_path_str = filedialog.askopenfilename(
                title="Selecionar planilha",
                initialdir=str(self.data_root),
                filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
            )
            if not xlsx_path_str:
                return

            xlsx_path = Path(xlsx_path_str)

            # Save the selected path for future imports (absoluto ou relativo)
            try:
                rel = xlsx_path.relative_to(self.data_root)
                self.cfg.xlsx_default_path = str(rel)
            except ValueError:
                self.cfg.xlsx_default_path = str(xlsx_path)
            self.cfg.save(self.data_root)

            resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

            # Atualizar label da planilha no workflow e na aba de cadastros
            if hasattr(self, "sheet_label_var"):
                sheet_info = self.cfg.xlsx_default_path or ""
                if getattr(self.cfg, "xlsx_default_sheet", ""):
                    sheet_info += f" | Aba: {self.cfg.xlsx_default_sheet}"
                self.sheet_label_var.set("Planilha: " + sheet_info)

            res = import_from_xlsx(
                store=self.store,
                xlsx_path=xlsx_path,
                sheet_name=resolved_sheet,
            )
            self.reload_cache()
            self.apply_filter()
            self.refresh_stats()
            self.set_status(
                f"Importação OK: {res.inserted} novos, {res.updated} atualizados, {res.skipped} pulados (total {res.total})"
            )
            self.reload_workflow()
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            self.set_status("Erro ao importar")
        finally:
            self.refresh_stats()
            self.reload_history()
            self.reload_audit()

    def on_workflow_clear(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        if not self.workflow_file_var.get():
            messagebox.showwarning("Workflow", "Selecione um arquivo na lista.")
            return
        if not messagebox.askyesno("Workflow", "Limpar histórico deste arquivo?"):
            return
        db = self.store.load()
        imports = list(db.get("import_log") or [])
        imports = [x for x in imports if x.get("file") != self.workflow_file_var.get()]
        db["import_log"] = imports
        self.store.save(db, actor=self._actor())
        self.reload_workflow()
        self.set_status("Histórico limpo")
        self.reload_audit()

    def on_workflow_item_click(self, event) -> None:
        """Manipula clique em itens da tabela de workflow para alternar cores."""
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        
        # Identificar o item clicado
        item = self.workflow_tree.identify_row(event.y)
        if not item:
            return
            
        # Obter o nome da criança (primeira coluna)
        values = self.workflow_tree.item(item, "values")
        if not values or len(values) < 1:
            return
            
        child_name = values[0]
        
        # Encontrar a criança no cache e alternar o status (busca case-insensitive)
        child = None
        for c in self.cache:
            if (c.get("nome") or "").strip().lower() == child_name.strip().lower():
                child = c
                break
        
        if not child:
            self.set_status(f"Criança '{child_name}' não encontrada no banco de dados")
            return
            
        # Alternar o status
        current_status = child.get("workflow_status", False)
        new_status = not current_status
        
        # Atualizar no banco de dados
        actor = self._actor()
        action, saved = self.store.upsert_child(
            {
                **child,
                "workflow_status": new_status,
            },
            actor=actor,
        )
        
        # Atualizar a exibição
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        
        # Atualizar a cor na tabela
        tag = "completed" if new_status else "pending"
        status_text = "Concluído" if new_status else "Pendente"
        self.workflow_tree.item(item, tags=(tag,), values=(child_name, status_text))
        
        self.set_status(f"Status alterado para {child_name}: {status_text}")
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

        if hasattr(self, "stats_tree_tags"):
            for iid in self.stats_tree_tags.get_children():
                self.stats_tree_tags.delete(iid)
            for tag, count in stats.by_tag:
                self.stats_tree_tags.insert("", "end", values=(tag, str(count)))
            self._apply_zebra(self.stats_tree_tags)

    def set_status(self, msg: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"[{stamp}] {self._t(msg)}")

    def _actor(self) -> str:
        return ((self.current_user or {}).get("username") or "").strip()

    def _role(self) -> str:
        return ((self.current_user or {}).get("role") or "").strip().lower()

    def _user_label(self) -> str:
        u = (self.current_user or {}).get("username") or ""
        r = (self.current_user or {}).get("role") or ""
        return f"{self._t('Usuario: ')}{u} ({r})"

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

    def _selected_tags_from_form(self) -> list[str]:
        return list(getattr(self, "_form_tags", []))

    def _set_selected_tags(self, tags: list[str]) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for raw in (tags or []):
            t = str(raw or "").strip()
            if not t:
                continue
            k = t.casefold()
            if k in seen:
                continue
            seen.add(k)
            unique.append(t)
        self._form_tags = unique
        self._render_tag_chips()

    def _tag_chip_colors(self, tag: str) -> tuple[str, str]:
        key = (tag or "").strip().encode("utf-8")
        digest = hashlib.sha1(key).digest() if key else b"\x00" * 20
        hue = int.from_bytes(digest[:2], "big") % 360
        sat = 0.52 + (digest[2] / 255.0) * 0.12
        bg_light = 0.90 + (digest[3] / 255.0) * 0.05
        fg_light = 0.26 + (digest[4] / 255.0) * 0.12

        br, bg, bb = colorsys.hls_to_rgb(hue / 360.0, min(bg_light, 0.95), min(sat, 0.70))
        fr, fg, fb = colorsys.hls_to_rgb(hue / 360.0, min(fg_light, 0.42), min(sat + 0.10, 0.80))

        bg_hex = f"#{int(br * 255):02X}{int(bg * 255):02X}{int(bb * 255):02X}"
        fg_hex = f"#{int(fr * 255):02X}{int(fg * 255):02X}{int(fb * 255):02X}"
        return bg_hex, fg_hex

    def _render_tag_chips(self) -> None:
        if not hasattr(self, "tags_chip_wrap"):
            return
        for child in self.tags_chip_wrap.winfo_children():
            child.destroy()

        tags = list(getattr(self, "_form_tags", []))
        if not tags:
            tk.Label(
                self.tags_chip_wrap,
                text=self._t("(Sem tag)"),
                bg=self.colors.get("panel", "#FFFFFF"),
                fg=self.colors.get("muted", "#5E6B7F"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        can_edit = self._can_edit()
        col = 0
        row = 0
        for tag in tags:
            bg, fg = self._tag_chip_colors(tag)
            chip = tk.Frame(self.tags_chip_wrap, bg=bg, bd=1, relief="solid")
            chip.grid(row=row, column=col, sticky="w", padx=(0, 6), pady=(0, 6))
            tk.Label(
                chip,
                text=tag,
                bg=bg,
                fg=fg,
                font=("Segoe UI Semibold", 9),
                padx=8,
                pady=2,
            ).pack(side="left")
            tk.Button(
                chip,
                text="x",
                command=lambda t=tag: self.on_remove_tag_from_form(t),
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                borderwidth=0,
                padx=4,
                pady=0,
                state=("normal" if can_edit else "disabled"),
            ).pack(side="left")
            col += 1
            if col >= 4:
                row += 1
                col = 0

    def _refresh_tag_controls(self) -> None:
        if not hasattr(self, "tag_pick_cb"):
            return
        tags = list(self.store.list_tags())
        current_tag_input = (self.tag_pick_var.get() or "").strip() if hasattr(self, "tag_pick_var") else ""
        self.tag_pick_cb.configure(values=tags)
        if current_tag_input:
            self.tag_pick_var.set(current_tag_input)

        if hasattr(self, "filter_tag_cb"):
            current = (self.filter_tag_var.get() or "").strip()
            values = ["", self.filter_tag_none_label, *tags]
            self.filter_tag_cb.configure(values=values)
            if current and current in values:
                self.filter_tag_var.set(current)
            elif current:
                self.filter_tag_var.set("")

        self._render_tag_chips()

    def on_add_new_tag(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        raw = (self.tag_pick_var.get() or "").strip()
        if not raw:
            messagebox.showwarning("Validação", "Selecione ou digite uma tag.")
            return

        selected_before = self._selected_tags_from_form()
        created, tag_name = self.store.add_tag(raw, actor=self._actor())
        self._refresh_tag_controls()
        self.tag_pick_var.set("")
        if not tag_name:
            return

        already = {t.casefold() for t in selected_before}
        if tag_name.casefold() in already:
            self.set_status("Tag já no cadastro")
            return

        self._set_selected_tags(selected_before + [tag_name])
        if created:
            self.set_status("Tag criada e adicionada")
        else:
            self.set_status("Tag adicionada")

    def on_remove_tag_from_form(self, tag: str) -> None:
        if not self._can_edit():
            return
        current = [t for t in self._selected_tags_from_form() if t.casefold() != (tag or "").casefold()]
        self._set_selected_tags(current)
        self.set_status("Tag removida")

    def _tree_tag_color_name(self, tag: str) -> str:
        key = (tag or "").strip().encode("utf-8")
        digest = hashlib.sha1(key).hexdigest()[:12] if key else "000000000000"
        return f"tagc_{digest}"

    def _ensure_tree_tag_color(self, tree: ttk.Treeview, tag: str) -> str:
        tag_name = self._tree_tag_color_name(tag)
        cache = getattr(self, "_tree_color_tag_cache", set())
        cache_key = (id(tree), tag_name)
        if cache_key not in cache:
            _bg, fg = self._tag_chip_colors(tag)
            try:
                tree.tag_configure(tag_name, foreground=fg)
            except Exception:
                pass
            cache.add(cache_key)
            self._tree_color_tag_cache = cache
        return tag_name

    def _setup_treeview(self, tree: ttk.Treeview, *, numeric_cols: set[str] | None = None) -> None:
        numeric_cols = set(numeric_cols or set())
        tree.tag_configure("even", background=self.colors.get("panel", "#FFFFFF"))
        tree.tag_configure("odd", background=self.colors.get("panel_soft", "#EEF3FB"))


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
            existing = list(tree.item(iid, "tags") or [])
            extra = [t for t in existing if t not in {"even", "odd"}]
            base = "even" if idx % 2 == 0 else "odd"
            tree.item(iid, tags=tuple([base, *extra]))

    def _on_cadastros_right_mousewheel(self, event) -> str:
        if not hasattr(self, "cadastros_right_canvas"):
            return "break"
        delta = int(-1 * (event.delta / 120)) if getattr(event, "delta", 0) else 0
        if delta:
            self.cadastros_right_canvas.yview_scroll(delta, "units")
        return "break"

    def reload_cache(self) -> None:
        selected_form_tags = self._selected_tags_from_form() if hasattr(self, "tag_pick_cb") else []
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
        self._refresh_tag_controls()
        if selected_form_tags:
            self._set_selected_tags(selected_form_tags)

        # Atualizar label da planilha na interface de cadastros, se existir
        if hasattr(self, "sheet_label_var"):
            sheet_info = self.cfg.xlsx_default_path or ""
            if getattr(self.cfg, "xlsx_default_sheet", ""):
                sheet_info += f" | Aba: {self.cfg.xlsx_default_sheet}"
            self.sheet_label_var.set("Planilha: " + sheet_info)


    def _on_nasc_var_change(self, *_args) -> None:
        if getattr(self, "_nasc_mask_lock", False):
            return
        raw = self.nasc_var.get() or ""
        digits = "".join(ch for ch in raw if ch.isdigit())[:8]
        if len(digits) <= 2:
            masked = digits
        elif len(digits) <= 4:
            masked = f"{digits[:2]}/{digits[2:]}"
        else:
            masked = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"

        if masked == raw:
            return

        self._nasc_mask_lock = True
        try:
            self.nasc_var.set(masked)
        finally:
            self._nasc_mask_lock = False

    def on_clear_filters(self) -> None:
        for attr, value in [
            ("search_var", ""),
            ("filter_school_var", ""),
            ("filter_age_min_var", ""),
            ("filter_age_max_var", ""),
            ("filter_start_var", ""),
            ("filter_end_var", ""),
            ("filter_workflow_var", ""),
            ("filter_tag_var", ""),
        ]:
            var = getattr(self, attr, None)
            if var is not None:
                var.set(value)
        if hasattr(self, "filter_has_att_var"):
            self.filter_has_att_var.set(False)
        if hasattr(self, "filter_has_vd_var"):
            self.filter_has_vd_var.set(False)
        self.apply_filter()
        self.set_status("Filtros limpos.")
        self.focus_search()

    def apply_filter(self) -> None:
        query = (self.search_var.get() or "").strip().lower()
        school = (getattr(self, "filter_school_var", tk.StringVar(value="")).get() or "").strip().lower()
        has_att = bool(getattr(self, "filter_has_att_var", tk.BooleanVar(value=False)).get())
        has_vd = bool(getattr(self, "filter_has_vd_var", tk.BooleanVar(value=False)).get())
        workflow_status = (getattr(self, "filter_workflow_var", tk.StringVar(value="")).get() or "").strip().lower()
        tag_filter_raw = (getattr(self, "filter_tag_var", tk.StringVar(value="")).get() or "").strip()
        tag_filter = tag_filter_raw.casefold()
        none_tag_label = getattr(self, "filter_tag_none_label", "(Sem tag)").casefold()

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

        def match_workflow_status(child: dict) -> bool:
            if not workflow_status:
                return True
            if workflow_status == "pendente":
                return not child.get("workflow_status", False)
            elif workflow_status == "concluido":
                return child.get("workflow_status", False)
            return True

        items = []
        for c in self.cache:
            cid = c.get("id") or ""
            tags = [str(t).strip() for t in (c.get("tags") or []) if str(t).strip()]
            tags_lower = {t.casefold() for t in tags}
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
            if not match_workflow_status(c):
                continue
            if tag_filter:
                if tag_filter == none_tag_label:
                    if tags:
                        continue
                elif tag_filter not in tags_lower:
                    continue

            if query:
                qok = query in (c.get("nome") or "").lower() or query in (c.get("escola") or "").lower()
                if not qok:
                    qok = query in (self._fulltext_by_child.get(cid) or "")
                if not qok and tags:
                    qok = query in " ".join(tags).lower()
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
            tags = [str(t).strip() for t in (c.get("tags") or []) if str(t).strip()]
            tag_principal = tags[0] if tags else ""
            item_tags: tuple[str, ...] = ()
            if tag_principal:
                item_tags = (self._ensure_tree_tag_color(self.tree, tag_principal),)
            self.tree.insert("", "end", iid=iid, values=(nome, idade, escola, tag_principal), tags=item_tags)

        self._apply_zebra(self.tree)

        filtered = bool(
            query
            or school
            or has_att
            or has_vd
            or workflow_status
            or tag_filter
            or (age_min is not None)
            or (age_max is not None)
            or bool(start_dt)
            or bool(end_dt)
        )
        msg = f"{len(items)} cadastro(s) exibido(s)" + (" com filtros ativos" if filtered else "")
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
        if hasattr(self, "contato_var"):
            self.contato_var.set("")
        if hasattr(self, "endereco_var"):
            self.endereco_var.set("")
        if hasattr(self, "tag_pick_var"):
            self.tag_pick_var.set("")
        self._set_selected_tags([])
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
        if hasattr(self, "contato_var"):
            self.contato_var.set(child.get("contato") or "")
        if hasattr(self, "endereco_var"):
            self.endereco_var.set(child.get("endereco") or "")
        self._set_selected_tags(child.get("tags") or [])

        self.meta_var.set(f"created_at={child.get('created_at')} | updated_at={child.get('updated_at')}")
        self._sync_history_selection()
        self._refresh_action_bar_state()

    def _child_from_form(self, *, use_selected_id: bool) -> dict:
        birth_iso = br_date_to_iso(self.nasc_var.get() or "")
        contato = self.contato_var.get() if hasattr(self, "contato_var") else ""
        endereco = self.endereco_var.get() if hasattr(self, "endereco_var") else ""
        return self.store.new_child_from_form(
            child_id=self.selected_id if use_selected_id else None,
            nome=self.nome_var.get() or "",
            idade=self.idade_var.get() or "",
            escola=self.escola_var.get() or "",
            data_nascimento_iso=birth_iso,
            contato=contato,
            endereco=endereco,
            tags=self._selected_tags_from_form(),
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

        is_new = not bool(self.selected_id)
        if is_new and hasattr(self, "tab_cadastros"):
            self.notebook.select(self.tab_cadastros)

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
        child = self._child_from_form(use_selected_id=(not is_new))
        if not self._validate_child_age(child):
            return
        action, saved = self.store.upsert_child(child, actor=actor)
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.fill_form(saved)
        if is_new:
            self.set_status(f"Cadastro criado ({action})")
        else:
            self.set_status(f"Cadastro salvo ({action})")
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

    def _resolve_and_save_sheet_name(self, xlsx_path: Path) -> str:
        """Resolve o nome real da aba e atualiza a config se for diferente.

        Isso evita quebrar quando a aba muda de "Base2025" para
        "Base2025-2026", por exemplo.
        """
        from .importer import _resolve_sheet_name

        resolved = _resolve_sheet_name(xlsx_path, self.cfg.xlsx_default_sheet)
        if resolved.strip() and resolved.strip() != self.cfg.xlsx_default_sheet.strip():
            self.cfg.xlsx_default_sheet = resolved
            # Salvar config para que o próximo uso já venha certo
            try:
                self.cfg.save(self.data_root)
            except Exception:
                pass
        return resolved

    def on_import(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        try:
            from .core.importer import import_from_xlsx  # lazy import (tk startup faster)

            xlsx_path = self.data_root / self.cfg.xlsx_default_path
            resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

            res = import_from_xlsx(
                store=self.store,
                xlsx_path=xlsx_path,
                sheet_name=resolved_sheet,
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

    def on_import_cadastros(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        try:
            from .core.importer import import_from_xlsx  # lazy import (tk startup faster)

            xlsx_path = self.data_root / self.cfg.xlsx_default_path
            resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

            res = import_from_xlsx(
                store=self.store,
                xlsx_path=xlsx_path,
                sheet_name=resolved_sheet,
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

    def on_select_spreadsheet(self) -> None:
        if not self._can_edit():
            messagebox.showwarning("Permissão", "Seu perfil é somente leitura.")
            return
        try:
            from .core.importer import import_from_xlsx  # lazy import (tk startup faster)

            xlsx_path_str = filedialog.askopenfilename(
                title="Selecionar planilha",
                initialdir=str(self.data_root),
                filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
            )
            if not xlsx_path_str:
                return

            xlsx_path = Path(xlsx_path_str)

            # Se o arquivo estiver fora da pasta de dados, guarda caminho absoluto;
            # caso contrário, guarda relativo à pasta de dados.
            try:
                rel = xlsx_path.relative_to(self.data_root)
                self.cfg.xlsx_default_path = str(rel)
            except ValueError:
                self.cfg.xlsx_default_path = str(xlsx_path)

                        # Resolver e salvar o nome real da aba antes de importar
            resolved_sheet = self._resolve_and_save_sheet_name(xlsx_path)

            # Atualizar label da planilha
            if hasattr(self, "sheet_label_var"):
                sheet_info = self.cfg.xlsx_default_path or ""
                if getattr(self.cfg, "xlsx_default_sheet", ""):
                    sheet_info += f" | Aba: {self.cfg.xlsx_default_sheet}"
                self.sheet_label_var.set("Planilha: " + sheet_info)

            res = import_from_xlsx(

                store=self.store,
                xlsx_path=xlsx_path,
                sheet_name=resolved_sheet,
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
        label = (self.report_key_var.get() or "").strip()
        key = (getattr(self, "report_labels", {}).get(label) or label or "pending").strip()
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
        label = (self.report_key_var.get() or "").strip()
        key = (getattr(self, "report_labels", {}).get(label) or label or "report").strip()
        key = key.replace(" ", "_")
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
            initialdir=str(self.data_root / self.cfg.exports_dir),
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
            initialdir=str(self.data_root / self.cfg.exports_dir),
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
            db_path=self.data_root / self.cfg.db_path,
            attachments_dir=self.data_root / self.cfg.attachments_dir,
            backups_dir=self.data_root / self.cfg.backups_dir,
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
            initialdir=str(self.data_root / self.cfg.backups_dir),
            filetypes=[("Backup zip", "*.zip")],
        )
        if not zip_path:
            return
        if not messagebox.askyesno("Restaurar", "Isso substituirá o banco e anexos atuais. Continuar?"):
            return
        restore_backup(
            backup_zip=Path(zip_path),
            db_path=self.data_root / self.cfg.db_path,
            attachments_dir=self.data_root / self.cfg.attachments_dir,
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
        build_history_tab(self, root)

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
            attachments_dir=self.data_root / self.cfg.attachments_dir,
            attendance_id=self.selected_attendance_id,
        )
        rel = str(dest.relative_to(self.data_root))
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
        p = self.data_root / (a.get("path") or "")
        if (not p.exists()) and (self.app_root != self.data_root):
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
            p = self.data_root / (a.get("path") or "")
            if (not p.exists()) and (self.app_root != self.data_root):
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
                # Get current version from config or default
                current_version = getattr(self.cfg, 'app_version', '0.0.0')
                result = check_for_update(self.app_root, fetch=True, current_version=current_version)
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
                self._last_update_result = result
                self._apply_update_check(result)

            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update_check(self, result) -> None:
        if not result.ok:
            self._update_available = False
            self.hide_update_banner()
            return

        # Handle GitHub-based updates (for non-git installations)
        if result.has_github_update:
            self._update_available = True
            version_info = f"v{result.current_version} → v{result.latest_version}"
            self.banner_message.set(
                f"Nova versão disponível ({version_info}). Clique em Atualizar para baixar o instalador."
            )
            self.banner_update_btn.configure(state="normal")
            self.show_update_banner()
            return

        # Handle git-based updates
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
        
        # Check if this is a GitHub update (non-git installation)
        if hasattr(self, '_last_update_result') and self._last_update_result and self._last_update_result.has_github_update:
            self._handle_github_update()
        else:
            self._handle_git_update()
    
    def _handle_github_update(self) -> None:
        """Handle GitHub-based update (download installer)."""
        result = self._last_update_result
        if not result or not result.installer_url:
            self.banner_message.set("URL do instalador não disponível.")
            self.banner_update_btn.configure(state="normal")
            return
        
        self.banner_message.set("Baixando instalador...")
        
        def worker() -> None:
            try:
                from .core.github_updater import download_installer
                import tempfile
                
                # Create temp file for installer
                with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                
                # Download installer
                success = download_installer(result.installer_url, tmp_path)
                
                def apply() -> None:
                    if not success:
                        self.banner_message.set("Falha ao baixar o instalador.")
                        self.banner_update_btn.configure(state="normal")
                        return
                    
                    self.banner_message.set("Instalador baixado. Abrindo...")
                    self.hide_update_banner()
                    
                    # Open the installer
                    try:
                        os.startfile(str(tmp_path))
                        messagebox.showinfo(
                            "Atualização",
                            f"O instalador da versão {result.latest_version} foi aberto.\n"
                            "Feche o aplicativo e execute o instalador para atualizar."
                        )
                    except Exception as e:
                        messagebox.showerror("Erro", f"Não foi possível abrir o instalador: {e}")
                
                self.after(0, apply)
            except Exception as e:
                self.after(
                    0,
                    lambda e=e: (
                        self.banner_message.set(f"Erro ao baixar: {str(e)}"),
                        self.banner_update_btn.configure(state="normal")
                        ))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _handle_git_update(self) -> None:
        """Handle git-based update (git pull)."""
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


def run() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    app_root = get_resource_root()
    data_root = get_data_root(app_root)
    ensure_user_files(app_root, data_root)
    App(app_root, data_root).mainloop()
