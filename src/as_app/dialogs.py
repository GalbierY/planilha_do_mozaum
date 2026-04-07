from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .core.util import now_iso


def _setup_modal_window(win: tk.Toplevel, parent: tk.Tk, *, min_width: int = 460, min_height: int = 260) -> None:
    parent_visible = False
    try:
        parent_visible = bool(parent.winfo_viewable()) and str(parent.state()) != "withdrawn"
    except Exception:
        parent_visible = False

    if parent_visible:
        try:
            win.transient(parent)
        except Exception:
            pass

    win.update_idletasks()
    width = max(min_width, win.winfo_reqwidth())
    height = max(min_height, win.winfo_reqheight())

    if parent_visible:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = max(parent.winfo_width(), width)
        ph = max(parent.winfo_height(), height)
        x = px + max((pw - width) // 2, 20)
        y = py + max((ph - height) // 2, 20)
    else:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max((sw - width) // 2, 20)
        y = max((sh - height) // 3, 20)

    win.geometry(f"{width}x{height}+{x}+{y}")

    try:
        win.lift()
        win.focus_force()
    except Exception:
        pass

    if parent_visible:
        try:
            win.grab_set()
        except Exception:
            pass


def _load_brand_asset(parent: tk.Tk) -> tk.PhotoImage | None:
    candidates: list[Path] = []
    app_root = getattr(parent, "app_root", None)
    if isinstance(app_root, Path):
        candidates.extend(
            [
                app_root / "assets" / "login.png",
                app_root / "assets" / "logo.png",
                app_root / "assets" / "icon.png",
                app_root / "login.png",
                app_root / "logo.png",
                app_root / "icon.png",
                app_root / "app.png",
            ]
        )
    project_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            project_root / "assets" / "login.png",
            project_root / "assets" / "logo.png",
            project_root / "assets" / "icon.png",
            project_root / "login.png",
            project_root / "logo.png",
            project_root / "icon.png",
            project_root / "app.png",
        ]
    )
    for p in candidates:
        if not p.exists():
            continue
        try:
            return tk.PhotoImage(file=str(p))
        except Exception:
            continue
    return None


def _build_dialog_header(
    win: tk.Toplevel,
    parent: tk.Tk,
    *,
    title: str,
    subtitle: str,
    bg: str | None = None,
    fg: str | None = None,
    sub_fg: str | None = None,
) -> None:
    colors = getattr(parent, "colors", {})
    bg = bg or colors.get("header", "#0E2A47")
    fg = fg or "#F4FFFF"
    sub_fg = sub_fg or "#D9E4F8"
    frame = tk.Frame(win, bg=bg, padx=12, pady=10)
    frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    frame.grid_columnconfigure(1, weight=1)

    img = _load_brand_asset(parent)
    if img is not None:
        setattr(win, "_brand_img", img)
        tk.Label(frame, image=img, bg=bg).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))

    tk.Label(frame, text=title, bg=bg, fg=fg, anchor="w", font=("Segoe UI Semibold", 12)).grid(
        row=0, column=1, sticky="w"
    )
    tk.Label(frame, text=subtitle, bg=bg, fg=sub_fg, anchor="w", font=("Segoe UI", 9)).grid(
        row=1, column=1, sticky="w", pady=(2, 0)
    )


def _apply_parent_language(parent: tk.Tk, win: tk.Toplevel) -> None:
    apply_lang = getattr(parent, "_apply_language_to_window", None)
    if callable(apply_lang):
        try:
            apply_lang(win)
        except Exception:
            return


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
        when_entry = ttk.Entry(self, textvariable=self.when_var)
        when_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 6))

        ttk.Label(self, text="Tipo de atendimento:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        self.type_var = tk.StringVar(value=(attendance.get("type") if attendance else ""))
        ttk.Entry(self, textvariable=self.type_var).grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Profissional:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        self.professional_var = tk.StringVar(value=(attendance.get("professional") if attendance else default_prof))
        ttk.Entry(self, textvariable=self.professional_var).grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Resultado:").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 6))
        self.result_var = tk.StringVar(value=(attendance.get("result") if attendance else ""))
        ttk.Entry(self, textvariable=self.result_var).grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Atendimento:").grid(row=4, column=0, sticky="w", padx=10, pady=(0, 6))
        self.attendance_var = tk.StringVar(value=(attendance.get("attendance") if attendance else ""))
        ttk.Entry(self, textvariable=self.attendance_var).grid(row=4, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="VD:").grid(row=5, column=0, sticky="w", padx=10, pady=(0, 6))
        self.vd_var = tk.StringVar(value=(attendance.get("vd") if attendance else ""))
        ttk.Entry(self, textvariable=self.vd_var).grid(row=5, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Observações:").grid(row=6, column=0, sticky="nw", padx=10, pady=(0, 6))
        self.notes_text = tk.Text(self, height=8, wrap="word")
        self.notes_text.grid(row=6, column=1, sticky="ew", padx=10, pady=(0, 6))
        if attendance and isinstance(attendance.get("notes"), str):
            self.notes_text.insert("1.0", attendance["notes"])

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 0)
        )

        style = ttk.Style(self)
        style.configure(
            "LoginPrimary.TButton",
            background="#E48DB8",
            foreground="#FFFFFF",
            borderwidth=0,
            padding=(12, 7),
        )
        style.map(
            "LoginPrimary.TButton",
            background=[("active", "#D76BA8"), ("pressed", "#C56295")],
            foreground=[("disabled", "#F4F7FF")],
        )

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Entrar", command=self._login, style="LoginPrimary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=760, min_height=620)
        _apply_parent_language(parent, self)
        self.after(10, when_entry.focus_set)

    def _save(self) -> None:
        if not (self.when_var.get().strip() and self.professional_var.get().strip()):
            self.status_var.set("Preencha a data/hora e o profissional.")
            return
        if not (self.result_var.get().strip() or self.attendance_var.get().strip() or self.vd_var.get().strip()):
            self.status_var.set("Informe pelo menos Resultado, Atendimento ou VD.")
            return
        self.result = {
            "occurred_at": self.when_var.get().strip(),
            "type": self.type_var.get().strip(),
            "professional": self.professional_var.get().strip(),
            "result": self.result_var.get().strip(),
            "attendance": self.attendance_var.get().strip(),
            "vd": self.vd_var.get().strip(),
            "notes": self.notes_text.get("1.0", "end").strip(),
        }
        self.destroy()


class UserSetupDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, *, current_user: dict | None = None, allow_role_change: bool = True):
        super().__init__(parent)
        self.title("Usuário admin:" if current_user is None else "Editar usuário")
        self.resizable(False, False)
        self.result: dict | None = None

        self.columnconfigure(1, weight=1)

        self.user_username_var = tk.StringVar(value=(current_user.get("username") if current_user else ""))
        self.user_role_var = tk.StringVar(value=(current_user.get("role") if current_user else "admin"))
        self.user_active_var = tk.BooleanVar(value=(current_user.get("active", True) if current_user else True))
        self.user_pw_var = tk.StringVar()
        self.user_pw2_var = tk.StringVar()

        ttk.Label(self, text="Usuário:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        ttk.Entry(self, textvariable=self.user_username_var).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(10, 6))

        ttk.Label(self, text="Role:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        role_cb = ttk.Combobox(self, textvariable=self.user_role_var, state="readonly", values=["admin", "editor", "viewer"])
        role_cb.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))
        if not allow_role_change:
            role_cb.configure(state="disabled")

        ttk.Checkbutton(self, text="Ativo", variable=self.user_active_var).grid(row=1, column=2, sticky="w", padx=(16, 0), pady=(0, 6))

        ttk.Label(self, text="Senha:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        ttk.Entry(self, textvariable=self.user_pw_var, show="*").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))

        ttk.Label(self, text="Confirmar:").grid(row=2, column=2, sticky="w", padx=10, pady=(0, 6))
        ttk.Entry(self, textvariable=self.user_pw2_var, show="*").grid(row=2, column=3, sticky="ew", padx=(8, 0), pady=(0, 6))

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=10, pady=(4, 0)
        )

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=4, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Salvar usuário", command=self._save, style="Primary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)

    def _save(self) -> None:
        username = self.user_username_var.get().strip()
        password = self.user_pw_var.get()
        password2 = self.user_pw2_var.get()

        if not username:
            self.status_var.set("Informe o usuário.")
            return
        if password or password2:
            if password != password2:
                self.status_var.set("As senhas não conferem.")
                return
            if len(password) < 4:
                self.status_var.set("Senha muito curta (mínimo 4).")
                return

        self.result = {
            "username": username,
            "role": self.user_role_var.get(),
            "active": self.user_active_var.get(),
            "password": password,
        }
        self.destroy()


class SetupAdminDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Primeiro acesso - Criar admin")
        self.resizable(False, False)
        self.result: dict | None = None

        if hasattr(parent, "colors"):
            self.configure(bg=getattr(parent, "colors", {}).get("bg", "#F4F7FB"))

        _build_dialog_header(
            self,
            parent,
            title="Bem-vinda(o) ao sistema",
            subtitle="Crie o usuario administrador para iniciar.",
        )

        ttk.Label(self, text="Usuario admin:").grid(row=1, column=0, sticky="w", padx=10, pady=(10, 6))
        self.user_var = tk.StringVar(value="admin")
        user_entry = ttk.Entry(self, textvariable=self.user_var)
        user_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=(10, 6))

        ttk.Label(self, text="Senha:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        self.pw_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw_var, show="*").grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 6))

        ttk.Label(self, text="Confirmar:").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))
        self.pw2_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw2_var, show="*").grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 10))

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Criar", command=self._create, style="Primary.TButton").grid(row=0, column=1)

        self.columnconfigure(1, weight=1)
        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)
        self.after(10, user_entry.focus_set)

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
    def __init__(self, parent: tk.Tk, *, show_setup: bool = False, usernames: list[str] | None = None):
        super().__init__(parent)
        self.title("Acesso ao sistema")
        self.resizable(False, False)
        self.result: dict | None = None

        self.configure(bg="#FFE6F2")
        self.minsize(560, 280)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        style = ttk.Style(self)
        style.configure(
            "LoginLabel.TLabel",
            background="#FFE6F2",
            foreground="#421E40",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "LoginTEntry",
            fieldbackground="#FFF0F6",
            bordercolor="#E7BAD0",
            lightcolor="#E7BAD0",
            darkcolor="#E7BAD0",
            borderwidth=1,
            padding=6,
        )
        style.configure(
            "Login.TCombobox",
            fieldbackground="#FFF0F6",
            bordercolor="#E7BAD0",
            lightcolor="#E7BAD0",
            darkcolor="#E7BAD0",
            borderwidth=1,
            padding=6,
        )
        style.configure("LoginStatus.TLabel", background="#FFE6F2", foreground="#9A1F60")
        style.configure(
            "LoginPrimary.TButton",
            background="#E48DB8",
            foreground="#FFFFFF",
            borderwidth=0,
            padding=(12, 8),
        )
        style.map(
            "LoginPrimary.TButton",
            background=[("active", "#D76BA8"), ("pressed", "#C56295")],
            foreground=[("disabled", "#F4F7FF")],
        )
        style.configure(
            "LoginCancel.TButton",
            background="#F8D4E6",
            foreground="#9A1F60",
            borderwidth=1,
            padding=(10, 7),
        )
        style.map(
            "LoginCancel.TButton",
            background=[("active", "#F5B7D5"), ("pressed", "#E48DB8")],
            foreground=[("disabled", "#D98BB0")],
        )

        header_text = "Bem-vinda(o) ao sistema" if show_setup else "Entre com seu usuário para continuar."
        _build_dialog_header(
            self,
            parent,
            title="SAS Civitas",
            subtitle=header_text,
            bg="#D6D6D6",
            fg="#E770AB",
            sub_fg="#E770AB",
        )

        ttk.Label(self, text="Usuário:", style="LoginLabel.TLabel").grid(row=1, column=0, sticky="w", padx=10, pady=(10, 6))
        self.user_var = tk.StringVar()
        if usernames:
            self.user_var.set(usernames[0])
            username_widget = ttk.Combobox(
                self,
                textvariable=self.user_var,
                values=usernames,
                state="readonly",
                style="Login.TCombobox",
                width=32,
            )
        else:
            username_widget = ttk.Entry(self, textvariable=self.user_var, style="Login.TEntry", width=32)
        username_widget.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 6))

        ttk.Label(self, text="Senha:", style="LoginLabel.TLabel").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        self.pw_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.pw_var, show="*", style="Login.TEntry", width=32).grid(
            row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 6)
        )

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, bg="#FFE6F2", fg="#9A1F60", anchor="w").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(6, 0)
        )

        style = ttk.Style(self)
        style.configure(
            "LoginCancel.TButton",
            background="#F8D4E6",
            foreground="#9A1F60",
            borderwidth=1,
            focusthickness=1,
            focuscolor="#E48DB8",
            padding=(10, 6),
        )
        style.map(
            "LoginCancel.TButton",
            background=[("active", "#F5B7D5"), ("pressed", "#E48DB8")],
            foreground=[("disabled", "#D98BB0")],
        )

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=(12, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="LoginCancel.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Entrar", command=self._login, style="LoginPrimary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)
        self.after(10, lambda: username_widget.focus_set())

    def _login(self) -> None:
        u = (self.user_var.get() or "").strip()
        pw = self.pw_var.get() or ""
        if not u or not pw:
            self.status_var.set("Informe usuário e senha.")
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
        keep_cb = ttk.Combobox(self, textvariable=self.keep_var, values=options, state="readonly", width=70)
        keep_cb.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 6))

        ttk.Label(self, text="Mesclar:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        self.merge_var = tk.StringVar(value=(options[1] if len(options) > 1 else ""))
        ttk.Combobox(self, textvariable=self.merge_var, values=options, state="readonly", width=70).grid(
            row=1, column=1, sticky="ew", padx=10, pady=(0, 10)
        )

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Mesclar", command=self._merge, style="Primary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=740, min_height=220)
        _apply_parent_language(parent, self)
        self.after(10, keep_cb.focus_set)

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


class ExportFormatDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Formato de Exportação")
        self.resizable(False, False)
        self.result: dict | None = None

        ttk.Label(self, text="Selecione o formato de exportação:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))

        self.format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(self, text="CSV", variable=self.format_var, value="csv").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        ttk.Radiobutton(self, text="JSON", variable=self.format_var, value="json").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        ttk.Radiobutton(self, text="Excel (XLSX)", variable=self.format_var, value="xlsx").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Exportar", command=self._export, style="Primary.TButton").grid(row=0, column=1)

        self.columnconfigure(0, weight=1)
        _setup_modal_window(self, parent, min_width=420, min_height=230)
        _apply_parent_language(parent, self)

    def _export(self) -> None:
        self.result = {"format": self.format_var.get()}
        self.destroy()
