from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from api2000_ui_actions import (
    API2000_FIELD_EMERGENCY_WETTED_AREA,
    API2000_FIELD_FIRE_FACTOR,
    API2000_FIELD_INSULATION,
    API2000_FIELD_LATENT_HEAT,
    API2000_FIELD_LATITUDE,
    API2000_FIELD_PUMP_IN,
    API2000_FIELD_PUMP_OUT,
    API2000_FIELD_TANK_VOLUME,
    API2000_FIELD_VAPOR_MW,
)
from ui_mode_logic import (
    FIELD_BACKPRESSURE,
    FIELD_BACKPRESSURE_KB,
    FIELD_INNER_DIAMETER,
    FIELD_LENGTH,
    FIELD_MAWP,
    FIELD_OVERPRESSURE,
    FIELD_PSV_KD,
    FIELD_REQUIRED_BODY_MATERIAL,
    FIELD_REQUIRED_CODE_STAMP,
    FIELD_REQUIRED_FLOW,
    FIELD_REQUIRED_INLET_CLASS,
    FIELD_REQUIRED_OUTLET_CLASS,
    FIELD_REQUIRED_TRIM_CODE,
    FIELD_REQUIRED_TRIM_MATERIAL,
    FIELD_START_PRESSURE,
    FIELD_START_TEMPERATURE,
    FIELD_TARGET_PRESSURE,
    FIELD_TARGET_TIME,
    FIELD_THICKNESS,
    FIELD_TOTAL_VOLUME,
    FIELD_VALVE_CD,
    FIELD_VALVE_COUNT,
)


def _bind_copyable_readonly_text(widget) -> None:
    widget.copyable_readonly = True

    def _block_edit(event):
        ctrl_pressed = bool(event.state & 0x4)
        allowed_with_ctrl = {"c", "a", "C", "A", "Insert"}
        navigation_keys = {
            "Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
        }
        if ctrl_pressed and event.keysym in allowed_with_ctrl:
            return None
        if event.keysym in navigation_keys:
            return None
        return "break"

    widget.bind("<Key>", _block_edit)


def _display_label(field_key: str) -> str:
    label_map = {
        FIELD_INNER_DIAMETER: "İç Çap",
        FIELD_LENGTH: "Uzunluk",
        FIELD_THICKNESS: "Et Kalınlığı",
        FIELD_TOTAL_VOLUME: "Toplam Hacim",
        FIELD_REQUIRED_FLOW: "Gerekli Tahliye Debisi",
        FIELD_START_PRESSURE: "Başlangıç Basıncı",
        FIELD_MAWP: "MAWP / Dizayn Basıncı",
        FIELD_OVERPRESSURE: "İzin Verilen Overpressure (%)",
        FIELD_START_TEMPERATURE: "Başlangıç Sıcaklığı",
        FIELD_TARGET_TIME: "Hedef Blowdown Süresi",
        FIELD_TARGET_PRESSURE: "Hedef Blowdown Basıncı",
        FIELD_VALVE_COUNT: "Vana Sayısı",
        FIELD_VALVE_CD: "Blowdown Deşarj Katsayısı (Cd)",
        FIELD_PSV_KD: "PSV Sertifikalı Kd",
        FIELD_BACKPRESSURE: "Karşı Basınç",
        FIELD_BACKPRESSURE_KB: "Backpressure Katsayısı (Kb)",
        FIELD_REQUIRED_TRIM_CODE: "İstenen Trim Kodu",
        FIELD_REQUIRED_CODE_STAMP: "İstenen Code Stamp",
        FIELD_REQUIRED_BODY_MATERIAL: "İstenen Gövde Malzemesi",
        FIELD_REQUIRED_TRIM_MATERIAL: "İstenen Trim Malzemesi",
        FIELD_REQUIRED_INLET_CLASS: "İstenen Giriş Rating Class",
        FIELD_REQUIRED_OUTLET_CLASS: "İstenen Çıkış Rating Class",
    }
    return label_map.get(field_key, field_key)


def _default_field_value(field_key: str) -> str:
    defaults = {
        FIELD_VALVE_COUNT: "1",
        FIELD_VALVE_CD: "0.975",
        FIELD_PSV_KD: "0.975",
        FIELD_BACKPRESSURE_KB: "1.0",
        FIELD_BACKPRESSURE: "0",
        FIELD_OVERPRESSURE: "10",
    }
    return defaults.get(field_key, "")


def _register_entry_field(
    app,
    parent,
    row: int,
    field_key: str,
    *,
    default_unit: str | None = None,
    units: list[str] | None = None,
    column_offset: int = 0,
) -> None:
    label = ttk.Label(parent, text=f"{_display_label(field_key)}:")
    label.grid(row=row, column=column_offset, padx=6, pady=4, sticky="w")

    entry_frame = ttk.Frame(parent)
    entry_frame.grid(row=row, column=column_offset + 1, padx=6, pady=4, sticky="ew")
    entry_frame.columnconfigure(0, weight=1)

    entry = ttk.Entry(entry_frame)
    entry.grid(row=0, column=0, sticky="ew")
    default_value = _default_field_value(field_key)
    if default_value:
        entry.insert(0, default_value)

    app.entries[field_key] = entry
    app.entry_frames[field_key] = (label, entry_frame)

    if units is not None and default_unit is not None:
        combo = ttk.Combobox(entry_frame, values=units, state="readonly", width=9)
        combo.grid(row=0, column=1, padx=(6, 0))
        combo.set(default_unit)
        app.unit_combos[field_key] = combo


def build_main_settings_ui(
    app,
    frame,
    *,
    app_version: str,
    native_engine_name: str,
    segmented_engine_name: str,
    two_phase_engine_name: str,
) -> None:
    frame.columnconfigure(0, weight=1)

    app.entries = {}
    app.unit_combos = {}
    app.entry_frames = {}

    top_frame = ttk.Frame(frame)
    top_frame.grid(row=0, column=0, sticky="ew")
    top_frame.columnconfigure(1, weight=1)

    ttk.Label(top_frame, text="Analiz Modu:").grid(row=0, column=0, padx=6, pady=3, sticky="w")
    app.mode_combo = ttk.Combobox(
        top_frame,
        values=[
            "Zamana Bağlı Basınç Düşürme (Blowdown)",
            "Gerekli Debiye Göre Emniyet Vanası Çapı (PSV Sizing)",
        ],
        state="readonly",
    )
    app.mode_combo.grid(row=0, column=1, padx=6, pady=3, sticky="ew")
    app.mode_combo.set("Zamana Bağlı Basınç Düşürme (Blowdown)")
    app.mode_combo.bind("<<ComboboxSelected>>", app.on_mode_change)

    app.sys_type_lbl = ttk.Label(top_frame, text="Sistem Tipi:")
    app.sys_type_lbl.grid(row=1, column=0, padx=6, pady=3, sticky="w")
    app.sys_type_combo = ttk.Combobox(
        top_frame,
        values=["Boru Hattı (Pipeline)", "Tank / Vessel"],
        state="readonly",
    )
    app.sys_type_combo.grid(row=1, column=1, padx=6, pady=3, sticky="ew")
    app.sys_type_combo.set("Boru Hattı (Pipeline)")

    app.mode_help_label = ttk.Label(
        frame,
        text="",
        justify="left",
        wraplength=760,
        foreground="#324b63",
    )
    app.mode_help_label.grid(row=1, column=0, padx=6, pady=(6, 10), sticky="ew")

    geom_frame = ttk.LabelFrame(frame, text="Temel Girdiler")
    geom_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=6)
    geom_frame.columnconfigure(1, weight=1)
    geom_frame.columnconfigure(3, weight=1)

    main_fields = [
        (FIELD_INNER_DIAMETER, "mm", ["mm", "m", "cm", "in", "ft"], 0, 0),
        (FIELD_LENGTH, "m", ["m", "mm", "cm", "in", "ft"], 0, 2),
        (FIELD_THICKNESS, "mm", ["mm", "m", "cm", "in", "ft"], 1, 0),
        (FIELD_TOTAL_VOLUME, "m3", ["m3", "L", "gal", "ft3"], 1, 2),
        (FIELD_REQUIRED_FLOW, "kg/h", ["kg/h", "lb/h", "Nm3/h", "Sm3/h", "SCFM", "MMSCFD"], 2, 0),
        (FIELD_START_PRESSURE, "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"], 2, 2),
        (FIELD_MAWP, "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"], 3, 0),
        (FIELD_OVERPRESSURE, "%", ["%"], 3, 2),
        (FIELD_START_TEMPERATURE, "C", ["C", "K", "F", "R"], 4, 0),
        (FIELD_TARGET_PRESSURE, "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"], 4, 2),
        (FIELD_TARGET_TIME, "s", ["s"], 5, 0),
        (FIELD_VALVE_COUNT, "Adet", ["Adet"], 5, 2),
        (FIELD_VALVE_CD, "", [""], 6, 0),
        (FIELD_PSV_KD, "", [""], 6, 2),
        (FIELD_BACKPRESSURE, "barg", ["barg", "bara", "psi", "psig", "atm"], 7, 0),
        (FIELD_BACKPRESSURE_KB, "", [""], 7, 2),
    ]
    for field_key, default_unit, units, row_index, column_offset in main_fields:
        _register_entry_field(
            app,
            geom_frame,
            row_index,
            field_key,
            default_unit=default_unit,
            units=units,
            column_offset=column_offset,
        )

    app.engine_options_frame = ttk.LabelFrame(frame, text="Çözüm Motoru")
    app.engine_options_frame.grid(row=3, column=0, sticky="ew", padx=6, pady=6)
    app.engine_options_frame.columnconfigure(1, weight=1)
    ttk.Label(app.engine_options_frame, text="Blowdown Motoru:").grid(row=0, column=0, padx=6, pady=5, sticky="w")
    app.engine_combo = ttk.Combobox(
        app.engine_options_frame,
        values=[native_engine_name, segmented_engine_name, two_phase_engine_name, "HydDown"],
        state="readonly",
    )
    app.engine_combo.grid(row=0, column=1, padx=6, pady=5, sticky="ew")
    app.engine_combo.set(native_engine_name)
    app.engine_combo.bind("<<ComboboxSelected>>", app.on_mode_change)

    ttk.Label(app.engine_options_frame, text="Pipeline Segment Sayısı:").grid(row=1, column=0, padx=6, pady=5, sticky="w")
    app.segment_count_entry = ttk.Entry(app.engine_options_frame)
    app.segment_count_entry.grid(row=1, column=1, padx=6, pady=5, sticky="ew")
    app.segment_count_entry.insert(0, "8")

    app.fire_case_frame = ttk.LabelFrame(frame, text="API 521 Fire Case")
    app.fire_case_frame.grid(row=4, column=0, sticky="ew", padx=6, pady=6)
    app.fire_case_frame.columnconfigure(1, weight=1)
    app.fire_case_var = tk.BooleanVar(value=False)
    app.fire_case_check = ttk.Checkbutton(
        app.fire_case_frame,
        text="Pool fire depressuring screening aktif",
        variable=app.fire_case_var,
        command=app.on_mode_change,
    )
    app.fire_case_check.grid(row=0, column=0, columnspan=2, padx=6, pady=5, sticky="w")
    ttk.Label(app.fire_case_frame, text="Scenario:").grid(row=1, column=0, padx=6, pady=5, sticky="w")
    app.fire_case_scenario_combo = ttk.Combobox(
        app.fire_case_frame,
        values=["Adequate drainage + firefighting", "Poor drainage / limited firefighting"],
        state="readonly",
    )
    app.fire_case_scenario_combo.grid(row=1, column=1, padx=6, pady=5, sticky="ew")
    app.fire_case_scenario_combo.set("Adequate drainage + firefighting")
    ttk.Label(app.fire_case_frame, text="Environment factor (F):").grid(row=2, column=0, padx=6, pady=5, sticky="w")
    app.fire_case_factor_entry = ttk.Entry(app.fire_case_frame)
    app.fire_case_factor_entry.grid(row=2, column=1, padx=6, pady=5, sticky="ew")
    app.fire_case_factor_entry.insert(0, "1.0")

    app.psv_options_frame = ttk.LabelFrame(frame, text="PSV Ön Boyutlandırma")
    app.psv_options_frame.grid(row=5, column=0, sticky="ew", padx=6, pady=6)
    app.psv_options_frame.columnconfigure(1, weight=1)
    app.psv_options_frame.columnconfigure(3, weight=1)

    ttk.Label(app.psv_options_frame, text="PSV Servis Tipi:").grid(row=0, column=0, padx=6, pady=5, sticky="w")
    app.psv_service_combo = ttk.Combobox(
        app.psv_options_frame,
        values=["Gas/Vapor", "Steam", "Liquid"],
        state="readonly",
    )
    app.psv_service_combo.grid(row=0, column=1, padx=6, pady=5, sticky="ew")
    app.psv_service_combo.set("Gas/Vapor")
    app.psv_service_combo.bind("<<ComboboxSelected>>", app.on_mode_change)

    ttk.Label(app.psv_options_frame, text="PRV Tasarım Tipi:").grid(row=1, column=0, padx=6, pady=5, sticky="w")
    app.prv_design_combo = ttk.Combobox(
        app.psv_options_frame,
        values=["Conventional", "Balanced Bellows", "Balanced Spring", "Pilot-Operated"],
        state="readonly",
    )
    app.prv_design_combo.grid(row=1, column=1, padx=6, pady=5, sticky="ew")
    app.prv_design_combo.set("Conventional")

    ttk.Label(app.psv_options_frame, text="Upstream Rupture Disk:").grid(row=1, column=2, padx=6, pady=5, sticky="w")
    app.rupture_disk_combo = ttk.Combobox(app.psv_options_frame, values=["No", "Yes"], state="readonly")
    app.rupture_disk_combo.grid(row=1, column=3, padx=6, pady=5, sticky="ew")
    app.rupture_disk_combo.set("No")

    app.psv_filter_help_label = ttk.Label(
        app.psv_options_frame,
        text="İsteğe bağlı exact vendor filtreleri. Boş bırakılırsa screening daha geniş yapılır.",
        justify="left",
        wraplength=740,
        foreground="#4f5d6b",
    )
    app.psv_filter_help_label.grid(row=2, column=0, columnspan=4, padx=6, pady=(2, 4), sticky="w")

    app.psv_vendor_filters_frame = ttk.LabelFrame(app.psv_options_frame, text="Opsiyonel Exact Vendor Filtreleri")
    app.psv_vendor_filters_frame.grid(row=3, column=0, columnspan=4, padx=6, pady=6, sticky="ew")
    app.psv_vendor_filters_frame.columnconfigure(1, weight=1)
    app.psv_vendor_filters_frame.columnconfigure(3, weight=1)

    vendor_filter_fields = [
        (FIELD_REQUIRED_TRIM_CODE, 0, 0),
        (FIELD_REQUIRED_CODE_STAMP, 0, 2),
        (FIELD_REQUIRED_BODY_MATERIAL, 1, 0),
        (FIELD_REQUIRED_TRIM_MATERIAL, 1, 2),
        (FIELD_REQUIRED_INLET_CLASS, 2, 0),
        (FIELD_REQUIRED_OUTLET_CLASS, 2, 2),
    ]
    for field_key, row_index, column_offset in vendor_filter_fields:
        _register_entry_field(app, app.psv_vendor_filters_frame, row_index, field_key, column_offset=column_offset)

    app.ht_enabled_var = tk.BooleanVar(value=True)
    app.ht_check = ttk.Checkbutton(frame, text="Isıl Analiz (Heat Transfer) Aktif", variable=app.ht_enabled_var)
    app.ht_check.grid(row=6, column=0, pady=6, sticky="w", padx=6)

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=7, column=0, sticky="ew", padx=6, pady=(6, 4))
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)

    app.btn_run = ttk.Button(
        button_frame,
        text=f"{app_version} Analizini Başlat",
        command=app.handle_run_button,
    )
    app.btn_run.grid(row=0, column=0, padx=(0, 6), sticky="ew")

    app.btn_abort = ttk.Button(button_frame, text="Durdur", state=tk.DISABLED, command=app.abort_simulation)
    app.btn_abort.grid(row=0, column=1, sticky="ew")

    app.progress_label = ttk.Label(frame, text="")
    app.progress_label.grid(row=8, column=0, padx=6, pady=(4, 0), sticky="ew")

    app.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
    app.progress.grid(row=9, column=0, padx=6, pady=(2, 8), sticky="ew")

    app.on_mode_change()


def build_api2000_pane_ui(app, parent) -> None:
    frame = ttk.Frame(parent, padding=20)
    frame.pack(expand=True, fill="both")
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="API Standard 2000 Tank Venting Hesaplayıcısı", font=("Arial", 12, "bold")).grid(
        row=0,
        column=0,
        columnspan=2,
        pady=10,
    )

    app.api_entries = {}
    api_config = [
        (API2000_FIELD_TANK_VOLUME, "7949"),
        (API2000_FIELD_LATITUDE, "Below 42"),
        (API2000_FIELD_PUMP_IN, "100"),
        (API2000_FIELD_PUMP_OUT, "100"),
        (API2000_FIELD_INSULATION, "1.0"),
        (API2000_FIELD_EMERGENCY_WETTED_AREA, ""),
        (API2000_FIELD_LATENT_HEAT, "250"),
        (API2000_FIELD_VAPOR_MW, "44"),
        (API2000_FIELD_FIRE_FACTOR, "1.0"),
    ]

    for index, (text, default) in enumerate(api_config, start=1):
        ttk.Label(frame, text=f"{text}:").grid(row=index, column=0, sticky="w", padx=5, pady=5)
        if text == API2000_FIELD_LATITUDE:
            combo = ttk.Combobox(frame, values=["Below 42", "42-58", "Above 58"], state="readonly")
            combo.grid(row=index, column=1, sticky="ew", padx=5, pady=5)
            combo.set("Below 42")
            app.api_entries[text] = combo
        else:
            entry = ttk.Entry(frame)
            entry.grid(row=index, column=1, sticky="ew", padx=5, pady=5)
            entry.insert(0, default)
            app.api_entries[text] = entry

    app.api_volatile_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="Akışkan uçucu (volatile)?", variable=app.api_volatile_var).grid(
        row=len(api_config) + 1,
        column=0,
        columnspan=2,
        pady=5,
        sticky="w",
    )
    app.api_emergency_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Emergency Venting / Fire Case Screening aktif", variable=app.api_emergency_var).grid(
        row=len(api_config) + 2,
        column=0,
        columnspan=2,
        pady=5,
        sticky="w",
    )
    ttk.Label(frame, text="Drainage / Firefighting:").grid(row=len(api_config) + 3, column=0, sticky="w", padx=5, pady=5)
    app.api_emergency_combo = ttk.Combobox(
        frame,
        values=["Adequate drainage + firefighting", "Poor drainage / limited firefighting"],
        state="readonly",
    )
    app.api_emergency_combo.grid(row=len(api_config) + 3, column=1, sticky="ew", padx=5, pady=5)
    app.api_emergency_combo.set("Adequate drainage + firefighting")

    ttk.Button(frame, text="API 2000 Hesabını Başlat", command=app.run_api2000_calculation).grid(
        row=len(api_config) + 4,
        column=0,
        columnspan=2,
        pady=10,
    )

    app.api_results_text = scrolledtext.ScrolledText(frame, height=18, width=70, wrap=tk.WORD, font=("Consolas", 10))
    app.api_results_text.grid(row=len(api_config) + 5, column=0, columnspan=2, pady=10, sticky="nsew")
    _bind_copyable_readonly_text(app.api_results_text)


def build_menu_bar(app) -> None:
    menubar = tk.Menu(app)

    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Ayarlar Yükle", command=app.load_settings)
    filemenu.add_command(label="Ayarlar Kaydet", command=app.save_settings)
    filemenu.add_separator()
    filemenu.add_command(label="Blowdown CSV Aktar...", command=app.export_blowdown_csv)
    filemenu.add_command(label="Blowdown PDF Aktar...", command=app.export_blowdown_pdf)
    filemenu.add_separator()
    filemenu.add_command(label="PSV CSV Aktar...", command=app.export_psv_csv)
    filemenu.add_command(label="PSV PDF Aktar...", command=app.export_psv_pdf)
    filemenu.add_separator()
    filemenu.add_command(label="Çıkış", command=app.quit)
    menubar.add_cascade(label="Dosya", menu=filemenu)

    vendormenu = tk.Menu(menubar, tearoff=0)
    vendormenu.add_command(label="Vendor Kataloğu Yükle...", command=app.import_vendor_catalog)
    vendormenu.add_command(label="Varsayılan Kataloğa Dön", command=app.reset_vendor_catalog)
    vendormenu.add_command(label="Aktif Katalog Özeti", command=app.show_vendor_catalog_summary)
    menubar.add_cascade(label="Vendor", menu=vendormenu)

    helpmenu = tk.Menu(menubar, tearoff=0)
    helpmenu.add_command(label="Metodoloji (API 520/521/2000)", command=app.show_methodology)
    helpmenu.add_command(label="Güncellemeleri Kontrol Et...", command=lambda: app.check_for_updates(manual=True))
    menubar.add_cascade(label="Yardım", menu=helpmenu)

    app.config(menu=menubar)


def build_right_pane_ui(app, parent) -> None:
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

    app.results_text = scrolledtext.ScrolledText(
        parent,
        bg="#f7f8fa",
        wrap=tk.WORD,
        font=("Consolas", 10),
        padx=10,
        pady=10,
    )
    app.results_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    _bind_copyable_readonly_text(app.results_text)

    app.graphs_tab.columnconfigure(0, weight=1)
    app.graphs_tab.rowconfigure(1, weight=1)
    app.graph_toolbar_frame = ttk.Frame(app.graphs_tab)
    app.graph_toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
    app.fig = plt.Figure(figsize=(7.4, 8.2))
    app.canvas = FigureCanvasTkAgg(app.fig, master=app.graphs_tab)
    app.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    app.graph_toolbar = NavigationToolbar2Tk(app.canvas, app.graph_toolbar_frame, pack_toolbar=False)
    app.graph_toolbar.update()
    app.graph_toolbar.pack(side=tk.LEFT, fill=tk.X)
    app._show_graph_placeholder("Blowdown")


def build_gas_settings_ui(app, frame, available_gases) -> None:
    ttk.Label(
        frame,
        text="Kompozisyon otomatik normalize edilir. Toplamın tam 100 olması gerekmez; çift tık veya Enter ile hızlı ekleme yapabilirsiniz.",
        justify="left",
        wraplength=280,
        foreground="#4f5d6b",
    ).pack(fill="x", padx=5, pady=(2, 4))

    search_frame = ttk.Frame(frame)
    search_frame.pack(fill="x", padx=5, pady=2)
    ttk.Label(search_frame, text="Gaz Ara:").pack(side="left")
    app.gas_search_entry = ttk.Entry(search_frame)
    app.gas_search_entry.pack(side="left", fill="x", expand=True, padx=5)
    app.gas_search_entry.bind("<KeyRelease>", app.filter_gas_list)

    app.gas_listbox = tk.Listbox(frame, height=8)
    app.gas_listbox.pack(fill="both", expand=True, padx=5, pady=2)
    for gas in available_gases:
        app.gas_listbox.insert(tk.END, gas)
    app.gas_listbox.bind("<Double-Button-1>", lambda _event: app.add_gas())
    app.gas_listbox.bind("<Return>", lambda _event: app.add_gas())

    add_frame = ttk.Frame(frame)
    add_frame.pack(fill="x", padx=5, pady=4)
    ttk.Label(add_frame, text="Mol %:").pack(side="left")
    app.mole_entry = ttk.Entry(add_frame, width=8)
    app.mole_entry.pack(side="left", padx=5)
    app.mole_entry.bind("<Return>", lambda _event: app.add_gas())
    ttk.Button(add_frame, text="Ekle", command=app.add_gas).pack(side="left", padx=2)
    ttk.Button(add_frame, text="Temizle", command=app.clear_comp).pack(side="left", padx=2)

    app.comp_text = tk.Text(frame, height=10, state=tk.DISABLED, bg="#fdfdfd", font=("Arial", 9), wrap=tk.WORD)
    app.comp_text.pack(fill="both", expand=True, padx=5, pady=5)


def build_log_tab_ui(app) -> None:
    app.log_text = scrolledtext.ScrolledText(app.log_tab, state=tk.DISABLED, bg="white", font=("Consolas", 9))
    app.log_text.pack(expand=True, fill="both", padx=5, pady=5)


def build_application_shell_ui(app) -> None:
    app.notebook = ttk.Notebook(app)
    app.notebook.pack(pady=5, expand=True, fill="both", padx=5)

    app.main_tab = ttk.Frame(app.notebook)
    app.graphs_tab = ttk.Frame(app.notebook)
    app.api2000_tab = ttk.Frame(app.notebook)
    app.log_tab = ttk.Frame(app.notebook)

    app.notebook.add(app.main_tab, text="Blowdown Analizi")
    app.notebook.add(app.graphs_tab, text="Grafikler")
    app.notebook.add(app.api2000_tab, text="Tank Havalandırma (API 2000)")
    app.notebook.add(app.log_tab, text="Loglar")

    build_log_tab_ui(app)

    app.paned = ttk.Panedwindow(app.main_tab, orient=tk.HORIZONTAL)
    app.paned.pack(expand=True, fill="both")

    app.left_pane = ttk.Frame(app.paned)
    app.right_pane = ttk.Frame(app.paned)
    app.paned.add(app.left_pane, weight=6)
    app.paned.add(app.right_pane, weight=4)

    app.left_pane.columnconfigure(0, weight=1)
    app.left_pane.rowconfigure(0, weight=1)
    app.left_canvas = tk.Canvas(app.left_pane, highlightthickness=0, background="#f8f9fa")
    app.left_scrollbar = ttk.Scrollbar(app.left_pane, orient=tk.VERTICAL, command=app.left_canvas.yview)
    app.left_canvas.configure(yscrollcommand=app.left_scrollbar.set)
    app.left_canvas.grid(row=0, column=0, sticky="nsew")
    app.left_scrollbar.grid(row=0, column=1, sticky="ns")

    app.left_container = ttk.Frame(app.left_canvas)
    app.left_canvas_window = app.left_canvas.create_window((0, 0), window=app.left_container, anchor="nw")

    def _sync_scroll_region(_event=None):
        app.left_canvas.configure(scrollregion=app.left_canvas.bbox("all"))

    def _sync_inner_width(event):
        app.left_canvas.itemconfigure(app.left_canvas_window, width=event.width)

    app.left_container.bind("<Configure>", _sync_scroll_region)
    app.left_canvas.bind("<Configure>", _sync_inner_width)

    def _on_mousewheel(event):
        if app.left_canvas.winfo_exists():
            app.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    app.left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _set_initial_sash():
        try:
            total_width = max(app.winfo_width(), 1024)
            app.paned.sashpos(0, int(total_width * 0.58))
        except Exception:
            pass

    app.after(80, _set_initial_sash)


def build_left_pane_ui(app, parent) -> None:
    type_frame = ttk.LabelFrame(parent, text="Vana Seçimi")
    type_frame.pack(fill="x", padx=5, pady=5)
    type_frame.columnconfigure(1, weight=1)

    ttk.Label(type_frame, text="Vana Standardı / Tipi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    app.valve_type_combo = ttk.Combobox(
        type_frame,
        values=["API 526 (PSV/PRV)", "API 6D (Küresel/Blowdown)"],
        state="readonly",
    )
    app.valve_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    app.valve_type_combo.set("API 6D (Küresel/Blowdown)")

    ttk.Label(
        type_frame,
        text="Vana tipi analiz moduna göre otomatik seçilir.",
        foreground="#4f5d6b",
    ).grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

    content_frame = ttk.Frame(parent)
    content_frame.pack(fill="both", expand=True, padx=5, pady=5)
    content_frame.columnconfigure(0, weight=3)
    content_frame.columnconfigure(1, weight=2)

    app.main_settings_frame = ttk.Frame(content_frame)
    app.main_settings_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    app.create_main_settings(app.main_settings_frame)

    app.gas_settings_frame = ttk.LabelFrame(content_frame, text="Gaz Kompozisyonu")
    app.gas_settings_frame.grid(row=0, column=1, sticky="nsew")
    app.create_gas_settings(app.gas_settings_frame)
