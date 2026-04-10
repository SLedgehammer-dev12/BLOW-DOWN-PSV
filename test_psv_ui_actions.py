import os
import sys
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from blowdown_studio import UnitConverter
from psv_ui_actions import apply_psv_workflow_result, collect_psv_ui_payload
from ui_builders import build_gas_settings_ui, build_left_pane_ui, build_main_settings_ui
from ui_mode_logic import (
    FIELD_BACKPRESSURE,
    FIELD_BACKPRESSURE_KB,
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
    FIELD_VALVE_COUNT,
)


class DummyApp:
    def __init__(self):
        self.available_gases = ["Methane", "Ethane", "Water"]
        self.composition = {}
        self.last_psv_report_bundle = None
        self.result_text = None
        self.plot_calls = []

    def on_mode_change(self, event=None):
        return None

    def handle_run_button(self):
        return None

    def abort_simulation(self):
        return None

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
        build_gas_settings_ui(self, frame, self.available_gases)

    def update_results_text(self, text):
        self.result_text = text

    def plot_psv_graphs(self, *args):
        self.plot_calls.append(args)


def _build_app(root):
    app = DummyApp()
    frame = ttk.Frame(root)
    frame.pack()
    build_left_pane_ui(app, frame)
    return app


def test_collect_psv_ui_payload_gas():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 95.0, "Ethane": 5.0}
        app.psv_service_combo.set("Gas/Vapor")
        app.entries[FIELD_REQUIRED_FLOW].insert(0, "10000")
        app.entries[FIELD_START_PRESSURE].insert(0, "100")
        app.entries[FIELD_MAWP].insert(0, "100")
        app.entries[FIELD_OVERPRESSURE].delete(0, tk.END)
        app.entries[FIELD_OVERPRESSURE].insert(0, "10")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "25")
        app.entries[FIELD_BACKPRESSURE].insert(0, "5")
        app.entries[FIELD_VALVE_COUNT].delete(0, tk.END)
        app.entries[FIELD_VALVE_COUNT].insert(0, "3")

        app.entries[FIELD_REQUIRED_TRIM_CODE].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_TRIM_CODE].insert(0, "TRIM-J")
        app.entries[FIELD_REQUIRED_CODE_STAMP].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_CODE_STAMP].insert(0, "UV")
        app.entries[FIELD_REQUIRED_BODY_MATERIAL].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_BODY_MATERIAL].insert(0, "A216-WCB")
        app.entries[FIELD_REQUIRED_TRIM_MATERIAL].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_TRIM_MATERIAL].insert(0, "316SS")
        app.entries[FIELD_REQUIRED_INLET_CLASS].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_INLET_CLASS].insert(0, "CL300")
        app.entries[FIELD_REQUIRED_OUTLET_CLASS].delete(0, tk.END)
        app.entries[FIELD_REQUIRED_OUTLET_CLASS].insert(0, "CL150")

        payload = collect_psv_ui_payload(app, converter=UnitConverter())

        assert payload["service_type"] == "Gas/Vapor"
        assert payload["valve_count"] == 3
        assert abs(sum(payload["normalized_composition"].values()) - 1.0) < 1e-9
        assert payload["inputs"]["Kd_api520"] == 0.975
        assert payload["inputs"]["required_trim_code"] == "TRIM-J"
        assert payload["inputs"]["required_code_stamp"] == "UV"
        assert payload["inputs"]["required_body_material"] == "A216-WCB"
        assert payload["inputs"]["required_trim_material"] == "316SS"
        assert payload["inputs"]["required_inlet_rating_class"] == "CL300"
        assert payload["inputs"]["required_outlet_rating_class"] == "CL150"
    finally:
        root.destroy()


def test_collect_psv_ui_payload_liquid_uses_kw():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Water": 100.0}
        app.psv_service_combo.set("Liquid")
        app.entries[FIELD_REQUIRED_FLOW].insert(0, "150")
        app.entries[FIELD_START_PRESSURE].insert(0, "12")
        app.entries[FIELD_MAWP].insert(0, "12")
        app.entries[FIELD_OVERPRESSURE].delete(0, tk.END)
        app.entries[FIELD_OVERPRESSURE].insert(0, "10")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "30")
        app.entries[FIELD_BACKPRESSURE].insert(0, "2")
        app.entries[FIELD_PSV_KD].delete(0, tk.END)
        app.entries[FIELD_PSV_KD].insert(0, "0.650")
        app.entries[FIELD_BACKPRESSURE_KB].delete(0, tk.END)
        app.entries[FIELD_BACKPRESSURE_KB].insert(0, "0.95")

        payload = collect_psv_ui_payload(app, converter=UnitConverter())

        assert payload["service_type"] == "Liquid"
        assert payload["inputs"]["Kw"] == 0.95
        assert payload["inputs"]["Kd_api520"] == 0.65
    finally:
        root.destroy()


def test_apply_psv_workflow_result_adds_vendor_note():
    app = DummyApp()
    report_bundle = SimpleNamespace(text="Report body", summary_rows=[])
    workflow = SimpleNamespace(
        report_bundle=report_bundle,
        sizing=object(),
        inputs={"a": 1},
        selected_valve=object(),
        valve_data=[],
        vendor_selection=None,
        vendor_evaluation=None,
        force_n=None,
        valve_count=1,
    )

    returned_bundle = apply_psv_workflow_result(app, workflow, r"C:\Temp\catalog.json")

    assert app.last_psv_report_bundle is returned_bundle
    assert "catalog.json" in app.result_text
    assert app.plot_calls
    assert ("Vendor Catalog Path", r"C:\Temp\catalog.json") in returned_bundle.summary_rows


if __name__ == "__main__":
    test_collect_psv_ui_payload_gas()
    test_collect_psv_ui_payload_liquid_uses_kw()
    test_apply_psv_workflow_result_adds_vendor_note()
    print("TEST COMPLETED")
