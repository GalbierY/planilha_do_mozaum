from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

if TYPE_CHECKING:
    from .gui import App


def build_cadastros_tab(app: "App", root: ttk.Frame) -> None:
    root.columnconfigure(0, weight=2)
    root.columnconfigure(1, weight=3)
    root.rowconfigure(2, weight=1)

    top = ttk.LabelFrame(root, text="Busca rapida", style="Card.TLabelframe", padding=(12, 10))
    top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
    top.columnconfigure(1, weight=1)

    ttk.Label(top, text="Nome, escola ou termo do historico:").grid(row=0, column=0, sticky="w")
    app.search_var = tk.StringVar()
    app.search_entry = ttk.Entry(top, textvariable=app.search_var)
    app.search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 10))
    app.search_entry.bind("<KeyRelease>", lambda _e: app.apply_filter())

    app.btn_new_child_inline = ttk.Button(top, text="+ Novo cadastro", command=app.on_new_child_form, style="Primary.TButton")
    app.btn_new_child_inline.grid(row=0, column=2, sticky="e", padx=(0, 8))
    app.btn_clear_filters = ttk.Button(top, text="Limpar filtros", command=app.on_clear_filters, style="Secondary.TButton")
    app.btn_clear_filters.grid(row=0, column=3, sticky="e")

    ttk.Label(
        top,
        text="Dica: Ctrl+F foca a busca e Enter na lista abre o cadastro selecionado.",
        style="Muted.TLabel",
    ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    filter_row = ttk.LabelFrame(root, text="Filtros", style="Card.TLabelframe", padding=(12, 10))
    filter_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
    for c in range(14):
        filter_row.columnconfigure(c, weight=0)
    filter_row.columnconfigure(13, weight=1)

    app.filter_school_var = tk.StringVar(value="")
    app.filter_age_min_var = tk.StringVar(value="")
    app.filter_age_max_var = tk.StringVar(value="")
    app.filter_has_att_var = tk.BooleanVar(value=False)
    app.filter_has_vd_var = tk.BooleanVar(value=False)
    app.filter_start_var = tk.StringVar(value="")
    app.filter_end_var = tk.StringVar(value="")
    app.filter_tag_var = tk.StringVar(value="")
    app.filter_tag_none_label = "(Sem tag)"

    ttk.Label(filter_row, text="Escola:").grid(row=0, column=0, sticky="w")
    app.filter_school_cb = ttk.Combobox(filter_row, textvariable=app.filter_school_var, state="normal", width=22, values=[])
    app.filter_school_cb.grid(row=0, column=1, sticky="w", padx=(6, 16))
    app.filter_school_cb.bind("<<ComboboxSelected>>", lambda _e: app.apply_filter())
    app.filter_school_cb.bind("<KeyRelease>", lambda _e: app.apply_filter())

    ttk.Label(filter_row, text="Idade:").grid(row=0, column=2, sticky="w")
    age_min = ttk.Entry(filter_row, textvariable=app.filter_age_min_var, width=5)
    age_min.grid(row=0, column=3, sticky="w", padx=(6, 4))
    ttk.Label(filter_row, text="ate").grid(row=0, column=4, sticky="w")
    age_max = ttk.Entry(filter_row, textvariable=app.filter_age_max_var, width=5)
    age_max.grid(row=0, column=5, sticky="w", padx=(6, 16))
    age_min.bind("<KeyRelease>", lambda _e: app.apply_filter())
    age_max.bind("<KeyRelease>", lambda _e: app.apply_filter())

    ttk.Checkbutton(filter_row, text="Com atendimento", variable=app.filter_has_att_var, command=app.apply_filter).grid(
        row=0, column=6, sticky="w", padx=(0, 12)
    )
    ttk.Checkbutton(filter_row, text="Com VD", variable=app.filter_has_vd_var, command=app.apply_filter).grid(
        row=0, column=7, sticky="w", padx=(0, 16)
    )

    ttk.Label(filter_row, text="Periodo (aaaa-mm-dd):").grid(row=0, column=8, sticky="w")
    start_e = ttk.Entry(filter_row, textvariable=app.filter_start_var, width=14)
    start_e.grid(row=0, column=9, sticky="w", padx=(6, 6))
    end_e = ttk.Entry(filter_row, textvariable=app.filter_end_var, width=14)
    end_e.grid(row=0, column=10, sticky="w")
    start_e.bind("<KeyRelease>", lambda _e: app.apply_filter())
    end_e.bind("<KeyRelease>", lambda _e: app.apply_filter())

    ttk.Label(filter_row, text="Tag:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    app.filter_tag_cb = ttk.Combobox(filter_row, textvariable=app.filter_tag_var, state="readonly", width=22, values=[""])
    app.filter_tag_cb.grid(row=1, column=1, sticky="w", padx=(6, 16), pady=(8, 0))
    app.filter_tag_cb.bind("<<ComboboxSelected>>", lambda _e: app.apply_filter())

    ttk.Label(filter_row, text="Workflow:").grid(row=1, column=2, sticky="w", pady=(8, 0))
    app.filter_workflow_var = tk.StringVar(value="")
    app.filter_workflow_cb = ttk.Combobox(
        filter_row,
        textvariable=app.filter_workflow_var,
        state="readonly",
        values=["", "Pendente", "Concluido"],
        width=14,
    )
    app.filter_workflow_cb.grid(row=1, column=3, sticky="w", padx=(6, 16), pady=(8, 0))
    app.filter_workflow_cb.bind("<<ComboboxSelected>>", lambda _e: app.apply_filter())
    app.filter_workflow_cb.bind("<KeyRelease>", lambda _e: app.apply_filter())

    main_left = ttk.LabelFrame(root, text="Lista de criancas", style="Card.TLabelframe", padding=(10, 8))
    main_left.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
    main_left.rowconfigure(2, weight=1)
    main_left.columnconfigure(0, weight=1)

    app.results_var = tk.StringVar(value="0 cadastro(s)")
    ttk.Label(main_left, textvariable=app.results_var, style="Muted.TLabel").grid(
        row=0, column=0, sticky="w", pady=(0, 2)
    )

    # Nome da planilha configurada + aba
    sheet_info = app.cfg.xlsx_default_path or ""
    if getattr(app.cfg, "xlsx_default_sheet", ""):
        sheet_info += f" | Aba: {app.cfg.xlsx_default_sheet}"
    app.sheet_label_var = tk.StringVar(value="Planilha: " + sheet_info)
    ttk.Label(main_left, textvariable=app.sheet_label_var, style="Muted.TLabel").grid(
        row=1, column=0, sticky="w", pady=(0, 6)
    )

    app.tree = ttk.Treeview(
        main_left,
        columns=("nome", "idade", "escola", "tag_principal"),
        show="headings",
        selectmode="browse",
    )
    app.tree["displaycolumns"] = ("nome", "idade", "escola", "tag_principal")

    app.tree.heading("nome", text="Crianca")
    app.tree.column("nome", width=280, anchor="w")
    app.tree.heading("idade", text="Idade")
    app.tree.column("idade", width=80, anchor="center")
    app.tree.heading("escola", text="Escola")
    app.tree.column("escola", width=180, anchor="w")
    app.tree.heading("tag_principal", text="Tag principal")
    app.tree.column("tag_principal", width=150, anchor="w")

    app._setup_treeview(app.tree, numeric_cols={"idade"})

    app.tree.grid(row=2, column=0, sticky="nsew")

    app.tree.bind("<<TreeviewSelect>>", lambda _e: app.on_select())
    app.tree.bind("<Return>", lambda _e: getattr(app, "nome_entry", app.tree).focus_set())

    vsb = ttk.Scrollbar(main_left, orient="vertical", command=app.tree.yview)
    app.tree.configure(yscrollcommand=vsb.set)
    vsb.grid(row=2, column=1, sticky="ns")

    right_wrap = ttk.Frame(root, style="Root.TFrame")
    right_wrap.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
    right_wrap.columnconfigure(0, weight=1)
    right_wrap.rowconfigure(0, weight=1)

    app.cadastros_right_canvas = tk.Canvas(
        right_wrap,
        highlightthickness=0,
        borderwidth=0,
        background=app.colors.get("bg", "#F4F7FB"),
    )
    app.cadastros_right_canvas.grid(row=0, column=0, sticky="nsew")

    cad_right_vsb = ttk.Scrollbar(right_wrap, orient="vertical", command=app.cadastros_right_canvas.yview)
    cad_right_vsb.grid(row=0, column=1, sticky="ns")
    app.cadastros_right_canvas.configure(yscrollcommand=cad_right_vsb.set)

    main_right = ttk.LabelFrame(app.cadastros_right_canvas, text="Dados da crianca selecionada", style="Card.TLabelframe", padding=(10, 8))
    app._cadastros_right_window = app.cadastros_right_canvas.create_window((0, 0), window=main_right, anchor="nw")
    main_right.columnconfigure(1, weight=1)

    def _sync_cadastros_right_scroll(_event=None) -> None:
        try:
            app.cadastros_right_canvas.configure(scrollregion=app.cadastros_right_canvas.bbox("all"))
            app.cadastros_right_canvas.itemconfigure(
                app._cadastros_right_window,
                width=app.cadastros_right_canvas.winfo_width(),
            )
        except tk.TclError:
            return

    main_right.bind("<Configure>", _sync_cadastros_right_scroll)
    app.cadastros_right_canvas.bind("<Configure>", _sync_cadastros_right_scroll)

    def _bind_wheel(_event=None) -> None:
        app.bind_all("<MouseWheel>", app._on_cadastros_right_mousewheel)

    def _unbind_wheel(_event=None) -> None:
        app.unbind_all("<MouseWheel>")

    right_wrap.bind("<Enter>", _bind_wheel)
    right_wrap.bind("<Leave>", _unbind_wheel)
    app.cadastros_right_canvas.bind("<Enter>", _bind_wheel)
    app.cadastros_right_canvas.bind("<Leave>", _unbind_wheel)

    r = 0
    ttk.Label(main_right, text="ID:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.id_var = tk.StringVar()
    ttk.Entry(main_right, textvariable=app.id_var, state="readonly").grid(row=r, column=1, sticky="ew", pady=(0, 6))

    r += 1
    ttk.Label(main_right, text="Nome da crianca*:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.nome_var = tk.StringVar()
    app.nome_entry = ttk.Entry(main_right, textvariable=app.nome_var)
    app.nome_entry.grid(row=r, column=1, sticky="ew", pady=(0, 6))
    app.nome_entry.bind("<KeyRelease>", lambda _e: app._clear_invalid(app.nome_entry))

    r += 1
    ttk.Label(main_right, text="Idade:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.idade_var = tk.StringVar()
    ttk.Entry(main_right, textvariable=app.idade_var, width=10).grid(row=r, column=1, sticky="w", pady=(0, 6))

    r += 1
    ttk.Label(main_right, text="Escola*:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.escola_var = tk.StringVar()
    app.escola_cb = ttk.Combobox(main_right, textvariable=app.escola_var, state="normal", values=[])
    app.escola_cb.grid(row=r, column=1, sticky="ew", pady=(0, 6))
    app.escola_cb.bind("<KeyRelease>", lambda _e: app._clear_invalid(app.escola_cb))
    app.escola_cb.bind("<<ComboboxSelected>>", lambda _e: app._clear_invalid(app.escola_cb))

    r += 1
    ttk.Label(main_right, text="Nascimento (dd/mm/aaaa):").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.nasc_var = tk.StringVar()
    app.nasc_entry = ttk.Entry(main_right, textvariable=app.nasc_var, width=16)
    app.nasc_entry.grid(row=r, column=1, sticky="w", pady=(0, 6))
    app.nasc_var.trace_add("write", app._on_nasc_var_change)

    r += 1
    ttk.Label(main_right, text="Contato:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.contato_var = tk.StringVar()
    ttk.Entry(main_right, textvariable=app.contato_var).grid(row=r, column=1, sticky="ew", pady=(0, 6))

    r += 1
    ttk.Label(main_right, text="Endereco:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.endereco_var = tk.StringVar()
    ttk.Entry(main_right, textvariable=app.endereco_var).grid(row=r, column=1, sticky="ew", pady=(0, 6))

    r += 1
    ttk.Label(main_right, text="Tags:").grid(row=r, column=0, sticky="nw", pady=(0, 6))
    tags_wrap = ttk.Frame(main_right)
    tags_wrap.grid(row=r, column=1, sticky="ew", pady=(0, 6))
    tags_wrap.columnconfigure(0, weight=1)
    add_tag_row = ttk.Frame(tags_wrap)
    add_tag_row.grid(row=0, column=0, sticky="ew")
    add_tag_row.columnconfigure(0, weight=1)
    app.tag_pick_var = tk.StringVar(value="")
    app.tag_pick_cb = ttk.Combobox(add_tag_row, textvariable=app.tag_pick_var, state="normal", values=[])
    app.tag_pick_cb.grid(row=0, column=0, sticky="ew")
    app.tag_pick_cb.bind("<Return>", lambda _e: app.on_add_new_tag())
    app.btn_add_tag = ttk.Button(add_tag_row, text="+", width=3, command=app.on_add_new_tag, style="Secondary.TButton")
    app.btn_add_tag.grid(row=0, column=1, padx=(8, 0))
    ttk.Label(
        tags_wrap,
        text="Selecione ou digite uma tag e clique +",
        style="Muted.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(4, 2))

    app.tags_chip_wrap = tk.Frame(tags_wrap, bg=app.colors.get("panel", "#FFFFFF"))
    app.tags_chip_wrap.grid(row=2, column=0, sticky="ew", pady=(2, 0))

    r += 1
    ttk.Label(main_right, text="Atendimentos:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    ttk.Label(main_right, text="Use a aba Historico para registrar e editar os atendimentos.", style="Muted.TLabel").grid(
        row=r, column=1, sticky="w", pady=(0, 6)
    )

    r += 1
    ttk.Label(main_right, text="Criado / atualizado:").grid(row=r, column=0, sticky="w", pady=(0, 6))
    app.meta_var = tk.StringVar()
    ttk.Entry(main_right, textvariable=app.meta_var, state="readonly").grid(row=r, column=1, sticky="ew", pady=(0, 6))

    actions = ttk.Frame(main_right)
    actions.grid(row=r + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))
    app.btn_save_inline = ttk.Button(actions, text="Salvar cadastro", command=app.on_save, style="Primary.TButton")
    app.btn_save_inline.grid(row=0, column=0, padx=(0, 8))
    app.btn_merge = ttk.Button(actions, text="Mesclar duplicados...", command=app.on_merge_children, style="Secondary.TButton")
    app.btn_merge.grid(row=0, column=1, padx=(0, 8))
    app.btn_export_selected = ttk.Button(actions, text="Exportar selecionados", command=app.on_export_selected, style="Secondary.TButton")
    app.btn_export_selected.grid(row=0, column=2, padx=(0, 8))
    app.btn_generate_report = ttk.Button(actions, text="Gerar relatorio", command=app.on_generate_report, style="Secondary.TButton")
    app.btn_generate_report.grid(row=0, column=3)

    import_frame = ttk.LabelFrame(main_right, text="Importacao", style="Card.TLabelframe", padding=(8, 8))
    import_frame.grid(row=r + 2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Label(import_frame, text="Atualize os cadastros com a planilha configurada.", style="Muted.TLabel").grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
    )
    app.btn_import_cadastros = ttk.Button(import_frame, text="Importar cadastros", command=app.on_import_cadastros, style="Primary.TButton")
    app.btn_import_cadastros.grid(row=1, column=0, sticky="w")
    app.btn_select_spreadsheet = ttk.Button(import_frame, text="Selecionar planilha", command=app.on_select_spreadsheet, style="Secondary.TButton")
    app.btn_select_spreadsheet.grid(row=1, column=1, sticky="w", padx=(8, 0))

    _sync_cadastros_right_scroll()
