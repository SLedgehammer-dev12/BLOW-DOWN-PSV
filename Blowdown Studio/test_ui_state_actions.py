import os
import sys
import tkinter as tk
from tkinter import ttk

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from ui_builders import build_left_pane_ui, build_main_settings_ui
from ui_mode_logic import (
    FIELD_PSV_KD,
    FIELD_REQUIRED_FLOW,
    build_mode_ui_state,
    build_psv_service_field_config,
)
from ui_state_actions import apply_mode_change, configure_psv_service_fields


class DummyApp:
    def on_mode_change(self, event=None):
        return None

    def handle_run_button(self):
        return None

    def abort_simulation(self):
        return None

    def _show_graph_placeholder(self, mode_text):
        self.placeholder_mode = mode_text

    def filter_gas_list(self, event=None):
        return None

    def add_gas(self):
        return None

    def clear_comp(self):
        return None

    def create_main_settings(self, frame):
        build_main_settings_ui(
            self,
            frame,
            app_version="v2.3.1",
            native_engine_name="Yerel Çözücü",
            segmented_engine_name="Segmented Pipeline",
            two_phase_engine_name="Two-Phase Screening",
        )

    def create_gas_settings(self, frame):
        return None


def test_configure_psv_service_fields_liquid():
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
        app.psv_service_combo.set("Liquid")
        app.entries[FIELD_PSV_KD].delete(0, tk.END)
        app.entries[FIELD_PSV_KD].insert(0, "0.975")
        configure_psv_service_fields(app, build_psv_service_field_config)
        assert app.entries[FIELD_PSV_KD].get() == "0.650"
        assert "L/min" in app.unit_combos[FIELD_REQUIRED_FLOW].cget("values")
    finally:
        root.destroy()


def test_apply_mode_change_switches_to_psv():
    root = tk.Tk()
    root.withdraw()
    try:
        frame = ttk.Frame(root)
        frame.pack()
        app = DummyApp()
        build_left_pane_ui(app, frame)
        app.mode_combo.set("Gerekli Debiye Göre Emniyet Vanası Çapı (PSV Sizing)")
        apply_mode_change(
            app,
            app_version="v2.3.1",
            native_engine_name="Yerel Çözücü",
            state_builder=build_mode_ui_state,
            service_field_config_builder=build_psv_service_field_config,
            placeholder_callback=app._show_graph_placeholder,
        )
        assert app.placeholder_mode == "PSV"
        assert app.btn_run.cget("text").startswith("PSV")
        assert app.psv_options_frame.winfo_manager() == "grid"
        assert app.valve_type_combo.get() == "API 526 (PSV/PRV)"
    finally:
        root.destroy()


if __name__ == "__main__":
    test_configure_psv_service_fields_liquid()
    test_apply_mode_change_switches_to_psv()
    print("TEST COMPLETED")
