import os
import sys
import tkinter as tk
from tkinter import ttk

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api521_fire_case import build_pool_fire_case_screening
from blowdown_studio import SEGMENTED_ENGINE_NAME, UnitConverter
from input_collection_actions import collect_blowdown_inputs
from ui_builders import build_gas_settings_ui, build_left_pane_ui, build_main_settings_ui
from ui_mode_logic import (
    FIELD_INNER_DIAMETER,
    FIELD_LENGTH,
    FIELD_MAWP,
    FIELD_START_PRESSURE,
    FIELD_START_TEMPERATURE,
    FIELD_TARGET_PRESSURE,
    FIELD_TARGET_TIME,
    FIELD_THICKNESS,
    FIELD_TOTAL_VOLUME,
    FIELD_VALVE_CD,
    FIELD_VALVE_COUNT,
)


class DummyApp:
    def __init__(self):
        self.available_gases = ["Methane", "Ethane", "Nitrogen"]
        self.composition = {}

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

    def _show_graph_placeholder(self, mode_text):
        self.placeholder_mode = mode_text

    def create_main_settings(self, frame):
        build_main_settings_ui(
            self,
            frame,
            app_version="v2.3.1",
            native_engine_name="Yerel Çözücü",
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            two_phase_engine_name="Two-Phase Screening",
        )

    def create_gas_settings(self, frame):
        build_gas_settings_ui(self, frame, self.available_gases)


def _build_app(root):
    app = DummyApp()
    app.converter = UnitConverter()
    parent = ttk.Frame(root)
    parent.pack()
    build_left_pane_ui(app, parent)
    return app


def test_collect_blowdown_inputs_geometric():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 95.0, "Ethane": 5.0}
        app.entries[FIELD_INNER_DIAMETER].insert(0, "500")
        app.entries[FIELD_LENGTH].insert(0, "10")
        app.entries[FIELD_THICKNESS].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "100")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "25")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "900")
        warnings = []

        inputs = collect_blowdown_inputs(
            app,
            converter=app.converter,
            fire_case_builder=build_pool_fire_case_screening,
            p_atm=101325.0,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            showwarning_fn=lambda title, msg: warnings.append((title, msg)),
        )

        assert abs(sum(inputs["composition"].values()) - 1.0) < 1e-9
        assert inputs["D_in_m"] > 0.0
        assert inputs["V_sys"] > 0.0
        assert inputs["fire_case"] is False
        assert not warnings
    finally:
        root.destroy()


def test_collect_blowdown_inputs_manual_volume():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "20")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")
        warnings = []

        inputs = collect_blowdown_inputs(
            app,
            converter=app.converter,
            fire_case_builder=build_pool_fire_case_screening,
            p_atm=101325.0,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            showwarning_fn=lambda title, msg: warnings.append((title, msg)),
        )

        assert inputs["HT_enabled"] is False
        assert app.ht_enabled_var.get() is False
        assert warnings
    finally:
        root.destroy()


def test_collect_blowdown_inputs_fire_case_updates_targets():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_INNER_DIAMETER].insert(0, "500")
        app.entries[FIELD_LENGTH].insert(0, "10")
        app.entries[FIELD_THICKNESS].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "80")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "25")
        app.entries[FIELD_MAWP].insert(0, "90")
        app.fire_case_var.set(True)

        inputs = collect_blowdown_inputs(
            app,
            converter=app.converter,
            fire_case_builder=build_pool_fire_case_screening,
            p_atm=101325.0,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            showwarning_fn=lambda *args, **kwargs: None,
        )

        assert inputs["fire_case"] is True
        assert "fire_case_target_pressure_pa" in inputs
        assert app.entries[FIELD_TARGET_TIME].get().strip() != ""
        assert app.entries[FIELD_TARGET_PRESSURE].get().strip() != ""
    finally:
        root.destroy()


def test_collect_blowdown_inputs_temperature_limit_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "-260")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "50 K" in str(exc)
            return
        raise AssertionError("Düşük sıcaklık için ValueError bekleniyordu")
    finally:
        root.destroy()


def test_collect_blowdown_inputs_cd_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "20")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")
        app.entries[FIELD_VALVE_CD].delete(0, tk.END)
        app.entries[FIELD_VALVE_CD].insert(0, "1.5")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "Cd" in str(exc)
            return
        raise AssertionError("Geçersiz Cd için ValueError bekleniyordu")
    finally:
        root.destroy()


def test_collect_blowdown_inputs_negative_pressure_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "-5")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "20")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "1")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "Başlangıç basıncı pozitif" in str(exc)
            return
        raise AssertionError("Negatif basınç için ValueError bekleniyordu")
    finally:
        root.destroy()


def test_collect_blowdown_inputs_impossible_geometry_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_INNER_DIAMETER].insert(0, "20")
        app.entries[FIELD_LENGTH].insert(0, "10")
        app.entries[FIELD_THICKNESS].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "20")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "İç çap" in str(exc)
            return
        raise AssertionError("İmkansız geometri için ValueError bekleniyordu")
    finally:
        root.destroy()


def test_collect_blowdown_inputs_high_temperature_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "1300")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "1500 K" in str(exc)
            return
        raise AssertionError("Aşırı sıcaklık için ValueError bekleniyordu")
    finally:
        root.destroy()


def test_collect_blowdown_inputs_zero_valve_count_validation():
    root = tk.Tk()
    root.withdraw()
    try:
        app = _build_app(root)
        app.composition = {"Methane": 100.0}
        app.entries[FIELD_TOTAL_VOLUME].insert(0, "12")
        app.entries[FIELD_START_PRESSURE].insert(0, "50")
        app.entries[FIELD_START_TEMPERATURE].insert(0, "20")
        app.entries[FIELD_TARGET_PRESSURE].insert(0, "7")
        app.entries[FIELD_TARGET_TIME].insert(0, "600")
        app.entries[FIELD_VALVE_COUNT].delete(0, tk.END)
        app.entries[FIELD_VALVE_COUNT].insert(0, "0")

        try:
            collect_blowdown_inputs(
                app,
                converter=app.converter,
                fire_case_builder=build_pool_fire_case_screening,
                p_atm=101325.0,
                segmented_engine_name=SEGMENTED_ENGINE_NAME,
                showwarning_fn=lambda *args, **kwargs: None,
            )
        except ValueError as exc:
            assert "Vana sayısı" in str(exc)
            return
        raise AssertionError("Sıfır vana sayısı için ValueError bekleniyordu")
    finally:
        root.destroy()


if __name__ == "__main__":
    test_collect_blowdown_inputs_geometric()
    test_collect_blowdown_inputs_manual_volume()
    test_collect_blowdown_inputs_fire_case_updates_targets()
    test_collect_blowdown_inputs_temperature_limit_validation()
    test_collect_blowdown_inputs_cd_validation()
    test_collect_blowdown_inputs_negative_pressure_validation()
    test_collect_blowdown_inputs_impossible_geometry_validation()
    test_collect_blowdown_inputs_high_temperature_validation()
    test_collect_blowdown_inputs_zero_valve_count_validation()
    print("TEST COMPLETED")
