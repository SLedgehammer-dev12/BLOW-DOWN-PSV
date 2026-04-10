import os
import sys
import tkinter as tk
from tkinter import ttk

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api2000_ui_actions import API2000_FIELD_LATITUDE, API2000_FIELD_TANK_VOLUME
from ui_builders import (
    build_application_shell_ui,
    build_api2000_pane_ui,
    build_gas_settings_ui,
    build_left_pane_ui,
    build_log_tab_ui,
    build_main_settings_ui,
    build_menu_bar,
    build_right_pane_ui,
)
from ui_mode_logic import FIELD_PSV_KD, FIELD_REQUIRED_CODE_STAMP, FIELD_REQUIRED_TRIM_CODE


class DummyApp:
    def on_mode_change(self, event=None):
        self.mode_change_calls = getattr(self, "mode_change_calls", 0) + 1

    def handle_run_button(self):
        return None

    def abort_simulation(self):
        return None

    def run_api2000_calculation(self):
        return None

    def filter_gas_list(self, event=None):
        return None

    def add_gas(self):
        return None

    def clear_comp(self):
        return None

    def _show_graph_placeholder(self, mode_text):
        self.placeholder_mode = mode_text

    def create_main_settings(self, frame):
        self.main_settings_parent = frame

    def create_gas_settings(self, frame):
        self.gas_settings_parent = frame


class MenuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()

    def load_settings(self):
        return None

    def save_settings(self):
        return None

    def export_blowdown_csv(self):
        return None

    def export_blowdown_pdf(self):
        return None

    def export_psv_csv(self):
        return None

    def export_psv_pdf(self):
        return None

    def import_vendor_catalog(self):
        return None

    def reset_vendor_catalog(self):
        return None

    def show_vendor_catalog_summary(self):
        return None

    def show_methodology(self):
        return None

    def check_for_updates(self, manual=False):
        return None


def test_build_main_settings_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        frame = ttk.Frame(root)
        frame.pack()
        app = DummyApp()
        build_main_settings_ui(
            app,
            frame,
            app_version="v2.3.1",
            native_engine_name="Yerel Çözücü",
            segmented_engine_name="Segmented Pipeline",
            two_phase_engine_name="Two-Phase Screening",
        )
        assert app.mode_combo.get()
        assert app.engine_combo.get() == "Yerel Çözücü"
        assert FIELD_PSV_KD in app.entries
        assert FIELD_REQUIRED_CODE_STAMP in app.entries
        assert FIELD_REQUIRED_TRIM_CODE in app.entries
        assert app.entries[FIELD_PSV_KD].get() == "0.975"
        assert app.entries[FIELD_REQUIRED_CODE_STAMP].get() == ""
        assert FIELD_REQUIRED_CODE_STAMP not in app.unit_combos
        assert hasattr(app, "mode_help_label")
        assert hasattr(app, "psv_vendor_filters_frame")
        assert getattr(app, "mode_change_calls", 0) >= 1
    finally:
        root.destroy()


def test_build_api2000_pane_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        parent = ttk.Frame(root)
        parent.pack()
        app = DummyApp()
        build_api2000_pane_ui(app, parent)
        assert API2000_FIELD_TANK_VOLUME in app.api_entries
        assert app.api_entries[API2000_FIELD_LATITUDE].get() == "Below 42"
        assert hasattr(app, "api_results_text")
        assert getattr(app.api_results_text, "copyable_readonly", False) is True
    finally:
        root.destroy()


def test_build_gas_settings_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        frame = ttk.Frame(root)
        frame.pack()
        app = DummyApp()
        build_gas_settings_ui(app, frame, ["Methane", "Ethane"])
        assert app.gas_search_entry.get() == ""
        assert app.gas_listbox.size() == 2
        assert hasattr(app, "comp_text")
        assert app.gas_listbox.bind("<Double-Button-1>")
        assert app.gas_listbox.bind("<Return>")
        assert app.mole_entry.bind("<Return>")
    finally:
        root.destroy()


def test_build_right_pane_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        parent = ttk.Frame(root)
        parent.pack()
        app = DummyApp()
        app.graphs_tab = ttk.Frame(root)
        app.graphs_tab.pack()
        build_right_pane_ui(app, parent)
        assert hasattr(app, "results_text")
        assert hasattr(app, "fig")
        assert hasattr(app, "canvas")
        assert hasattr(app, "graph_toolbar")
        assert getattr(app.results_text, "copyable_readonly", False) is True
        assert app.placeholder_mode == "Blowdown"
    finally:
        root.destroy()


def test_build_menu_bar_smoke():
    app = MenuApp()
    try:
        build_menu_bar(app)
        assert str(app.cget("menu"))
    finally:
        app.destroy()


def test_build_application_shell_ui_smoke():
    app = MenuApp()
    try:
        build_application_shell_ui(app)
        assert hasattr(app, "notebook")
        assert hasattr(app, "main_tab")
        assert hasattr(app, "left_container")
        assert hasattr(app, "log_text")
    finally:
        app.destroy()


def test_build_left_pane_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        parent = ttk.Frame(root)
        parent.pack()
        app = DummyApp()
        build_left_pane_ui(app, parent)
        assert app.valve_type_combo.get() == "API 6D (Küresel/Blowdown)"
        assert hasattr(app, "main_settings_frame")
        assert hasattr(app, "gas_settings_frame")
        assert hasattr(app, "main_settings_parent")
        assert hasattr(app, "gas_settings_parent")
    finally:
        root.destroy()


def test_build_log_tab_ui_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        app = DummyApp()
        app.log_tab = ttk.Frame(root)
        app.log_tab.pack()
        build_log_tab_ui(app)
        assert hasattr(app, "log_text")
    finally:
        root.destroy()


if __name__ == "__main__":
    test_build_main_settings_ui_smoke()
    test_build_api2000_pane_ui_smoke()
    test_build_gas_settings_ui_smoke()
    test_build_right_pane_ui_smoke()
    test_build_menu_bar_smoke()
    test_build_application_shell_ui_smoke()
    test_build_left_pane_ui_smoke()
    test_build_log_tab_ui_smoke()
    print("TEST COMPLETED")
