from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .dialogs import _apply_parent_language, _build_dialog_header, _setup_modal_window


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
            "Login.TEntry",
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
            bg="#E48DB8",
            fg="#FFFFFF",
            sub_fg="#F6D7E6",
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
        ttk.Label(self, textvariable=self.status_var, style="LoginStatus.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(6, 0)
        )

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=(12, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="LoginCancel.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Entrar", command=self._login, style="LoginPrimary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)
        self.after(10, lambda: username_widget.focus_set())

    def _login(self) -> None:
        username = (self.user_var.get() or "").strip()
        password = self.pw_var.get() or ""
        if not username or not password:
            self.status_var.set("Informe usuário e senha.")
            return
        self.result = {"username": username, "password": password}
        self.destroy()


class SetupAdminDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Primeiro acesso - Criar admin")
        self.resizable(False, False)
        self.result: dict | None = None

        if hasattr(parent, "colors"):
            self.configure(bg=getattr(parent, "colors", {}).get("bg", "#F4F7FB"))

        ttk.Label(self, text="Bem-vinda(o) ao sistema", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 8)
        )

        ttk.Label(self, text="Usuário admin:").grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
        self.user_var = tk.StringVar(value="admin")
        ttk.Entry(self, textvariable=self.user_var).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))

        ttk.Label(self, text="Senha:").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        self.pw_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw_var, show="*").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))

        ttk.Label(self, text="Confirmar:").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))
        self.pw2_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.pw2_var, show="*").grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 10))

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(btns, text="Criar", command=self._create, style="Primary.TButton").grid(row=0, column=1)

        self.columnconfigure(1, weight=1)
        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)
        self.after(10, lambda: self.user_var.trace_add("write", lambda *_: None))

    def _create(self) -> None:
        username = (self.user_var.get() or "").strip()
        password = self.pw_var.get() or ""
        password2 = self.pw2_var.get() or ""
        if not username:
            messagebox.showwarning("Validação", "Informe o usuário.")
            return
        if len(password) < 4:
            messagebox.showwarning("Validação", "Senha muito curta (mínimo 4).")
            return
        if password != password2:
            messagebox.showwarning("Validação", "As senhas não conferem.")
            return
        self.result = {"username": username, "password": password}
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
        role_cb = ttk.Combobox(
            self,
            textvariable=self.user_role_var,
            state="readonly",
            values=["admin", "editor", "viewer"],
        )
        role_cb.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))
        if not allow_role_change:
            role_cb.configure(state="disabled")

        ttk.Checkbutton(self, text="Ativo", variable=self.user_active_var).grid(
            row=1, column=2, sticky="w", padx=(16, 0), pady=(0, 6)
        )

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
        ttk.Button(btns, text="Cancelar", command=self.destroy, style="Secondary.TButton").grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(btns, text="Salvar usuário", command=self._save, style="Primary.TButton").grid(row=0, column=1)

        _setup_modal_window(self, parent, min_width=560, min_height=320)
        _apply_parent_language(parent, self)

    def _save(self) -> None:
        username = (self.user_username_var.get() or "").strip()
        password = self.user_pw_var.get() or ""
        password2 = self.user_pw2_var.get() or ""
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
