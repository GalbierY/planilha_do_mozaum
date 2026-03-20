from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .config import AppConfig
from .store import JsonStore
from .updater import check_for_update, pull_ff_only
from .util import br_date_to_iso, iso_to_br_date
from .stats import compute_stats


class App(tk.Tk):
    def __init__(self, app_root: Path):
        super().__init__()

        self.app_root = app_root
        self.cfg = AppConfig.load(app_root)
        self.store = JsonStore(app_root / self.cfg.db_path)

        self.title(self.cfg.app_name)
        self.geometry("1200x720")

        self.selected_id: str | None = None
        self.cache: list[dict] = []
        self._update_check_running = False
        self._update_available = False

        self._build_ui()
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self._start_auto_update_checks()

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
        self.notebook.add(self.tab_cadastros, text="Cadastros")
        self.notebook.add(self.tab_stats, text="Estatísticas")
        self.notebook.pack(fill="both", expand=True)

        self._build_cadastros_ui(self.tab_cadastros)
        self._build_stats_ui(self.tab_stats)

    def _build_cadastros_ui(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=2)
        root.columnconfigure(1, weight=3)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root, padding=10)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Buscar:").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search = ttk.Entry(top, textvariable=self.search_var)
        search.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        search.bind("<KeyRelease>", lambda _e: self.apply_filter())

        main_left = ttk.Frame(root, padding=(10, 0, 10, 10))
        main_left.grid(row=1, column=0, sticky="nsew")
        main_left.rowconfigure(0, weight=1)
        main_left.columnconfigure(0, weight=1)

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

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select())

        vsb = ttk.Scrollbar(main_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

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
        ttk.Entry(main_right, textvariable=self.nome_var).grid(row=r, column=1, sticky="ew", pady=(0, 6))

        r += 1
        ttk.Label(main_right, text="Idade:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.idade_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.idade_var, width=10).grid(
            row=r, column=1, sticky="w", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Escola:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.escola_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.escola_var).grid(row=r, column=1, sticky="ew", pady=(0, 6))

        r += 1
        ttk.Label(main_right, text="Nascimento (dd/mm/aaaa):").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.nasc_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.nasc_var, width=16).grid(
            row=r, column=1, sticky="w", pady=(0, 6)
        )

        r += 1
        ttk.Label(main_right, text="Atendimento:").grid(row=r, column=0, sticky="nw", pady=(0, 6))
        self.txt_atendimento = tk.Text(main_right, height=8, wrap="word")
        self.txt_atendimento.grid(row=r, column=1, sticky="nsew", pady=(0, 6))

        r += 1
        ttk.Label(main_right, text="VD:").grid(row=r, column=0, sticky="nw", pady=(0, 6))
        self.txt_vd = tk.Text(main_right, height=8, wrap="word")
        self.txt_vd.grid(row=r, column=1, sticky="nsew", pady=(0, 6))

        r += 1
        ttk.Label(main_right, text="Criado/Atualizado:").grid(row=r, column=0, sticky="w", pady=(0, 6))
        self.meta_var = tk.StringVar()
        ttk.Entry(main_right, textvariable=self.meta_var, state="readonly").grid(
            row=r, column=1, sticky="ew", pady=(0, 6)
        )

        bottom = ttk.Frame(root, padding=10)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        ttk.Button(bottom, text="Importar planilha", command=self.on_import).grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="Adicionar criança", command=self.on_add).grid(row=0, column=1, padx=8)
        ttk.Button(bottom, text="Salvar alterações", command=self.on_save).grid(row=0, column=2)

        self.status_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.status_var, foreground="gray").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

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
        self.stats_tree_age.grid(row=1, column=0, sticky="nsew")

        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.stats_tree_age.yview)
        self.stats_tree_age.configure(yscrollcommand=vsb2.set)
        vsb2.grid(row=1, column=1, sticky="ns")

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

        for iid in self.stats_tree_age.get_children():
            self.stats_tree_age.delete(iid)
        for age, count in stats.by_age:
            self.stats_tree_age.insert("", "end", values=(age, str(count)))

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def reload_cache(self) -> None:
        self.cache = self.store.list_children()

    def apply_filter(self) -> None:
        query = (self.search_var.get() or "").strip().lower()
        items = self.cache
        if query:
            items = [
                c
                for c in self.cache
                if query in (c.get("nome") or "").lower() or query in (c.get("escola") or "").lower()
            ]

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for c in items:
            iid = c.get("id") or ""
            nome = c.get("nome") or ""
            idade = "" if c.get("idade") is None else str(c.get("idade"))
            escola = c.get("escola") or ""
            self.tree.insert("", "end", iid=iid, values=(nome, idade, escola))

        self.set_status(f"{len(items)} registros" + (" (filtrado)" if query else ""))

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
        self.txt_atendimento.delete("1.0", "end")
        self.txt_vd.delete("1.0", "end")
        self.meta_var.set("")

    def fill_form(self, child: dict) -> None:
        self.selected_id = child.get("id")
        self.id_var.set(child.get("id") or "")
        self.nome_var.set(child.get("nome") or "")
        self.idade_var.set("" if child.get("idade") is None else str(child.get("idade")))
        self.escola_var.set(child.get("escola") or "")
        self.nasc_var.set(iso_to_br_date(child.get("data_nascimento")))

        self.txt_atendimento.delete("1.0", "end")
        self.txt_atendimento.insert("1.0", child.get("atendimento_realizado") or "")
        self.txt_vd.delete("1.0", "end")
        self.txt_vd.insert("1.0", child.get("vd") or "")

        self.meta_var.set(f"created_at={child.get('created_at')} | updated_at={child.get('updated_at')}")

    def _child_from_form(self, *, use_selected_id: bool) -> dict:
        birth_iso = br_date_to_iso(self.nasc_var.get() or "")
        return self.store.new_child_from_form(
            child_id=self.selected_id if use_selected_id else None,
            nome=self.nome_var.get() or "",
            idade=self.idade_var.get() or "",
            escola=self.escola_var.get() or "",
            data_nascimento_iso=birth_iso,
            atendimento=self.txt_atendimento.get("1.0", "end").rstrip("\n"),
            vd=self.txt_vd.get("1.0", "end").rstrip("\n"),
        )

    def on_add(self) -> None:
        nome = (self.nome_var.get() or "").strip()
        if not nome:
            messagebox.showwarning("Validação", "Preencha o nome da criança.")
            return
        child = self._child_from_form(use_selected_id=False)
        action, saved = self.store.upsert_child(child)
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.fill_form(saved)
        self.set_status(f"Adicionado ({action})")

    def on_save(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Salvar", "Selecione um registro para salvar alterações (ou use 'Adicionar criança').")
            return
        nome = (self.nome_var.get() or "").strip()
        if not nome:
            messagebox.showwarning("Validação", "Preencha o nome da criança.")
            return
        child = self._child_from_form(use_selected_id=True)
        action, saved = self.store.upsert_child(child)
        self.reload_cache()
        self.apply_filter()
        self.refresh_stats()
        self.fill_form(saved)
        self.set_status(f"Salvo ({action})")

    def on_import(self) -> None:
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
            messagebox.showinfo(
                "Importação",
                f"OK: {res.inserted} novos, {res.updated} atualizados, {res.skipped} pulados (total {res.total})",
            )
            self.set_status(f"Importação OK (batch {res.batch_id})")
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            self.set_status("Erro ao importar")

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


def run() -> None:
    app_root = Path(__file__).resolve().parents[2]
    App(app_root).mainloop()
