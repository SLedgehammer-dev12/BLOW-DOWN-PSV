import os
import sys
import tempfile

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from ui_file_actions import (
    apply_settings_payload,
    build_settings_payload,
    read_settings_payload,
    write_settings_payload,
)


class FakeField:
    def __init__(self, value=""):
        self.value = str(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = str(value)

    def delete(self, *_args):
        self.value = ""

    def insert(self, _idx, value):
        self.value = str(value)


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeApp:
    def __init__(self):
        self.mode_combo = FakeField("mode")
        self.sys_type_combo = FakeField("system")
        self.valve_type_combo = FakeField("API 526 (PSV/PRV)")
        self.engine_combo = FakeField("Yerel Çözücü")
        self.segment_count_entry = FakeField("8")
        self.vendor_catalog_path = None
        self.psv_service_combo = FakeField("Gas/Vapor")
        self.prv_design_combo = FakeField("Conventional")
        self.rupture_disk_combo = FakeField("No")
        self.fire_case_var = FakeVar(False)
        self.fire_case_scenario_combo = FakeField("Adequate drainage + firefighting")
        self.fire_case_factor_entry = FakeField("1.0")
        self.ht_enabled_var = FakeVar(True)
        self.entries = {
            "Valve Discharge Coeff (Cd)": FakeField("0.975"),
            "PSV Certified Kd": FakeField("0.975"),
            "Backpressure Coeff (Kb)": FakeField("1.0"),
        }
        self.unit_combos = {
            "Valve Discharge Coeff (Cd)": FakeField(""),
            "PSV Certified Kd": FakeField(""),
        }
        self.composition = {"Methane": 100.0}
        self.update_calls = 0
        self.mode_change_calls = 0

    def update_composition_display(self):
        self.update_calls += 1

    def on_mode_change(self):
        self.mode_change_calls += 1


def test_build_and_apply_settings_payload_roundtrip():
    app = FakeApp()
    app.vendor_catalog_path = "catalog.json"
    payload = build_settings_payload(app)

    clone = FakeApp()
    apply_settings_payload(clone, payload, default_engine_name="Yerel Çözücü")

    assert clone.vendor_catalog_path == "catalog.json"
    assert clone.entries["Valve Discharge Coeff (Cd)"].get() == "0.975"
    assert clone.entries["PSV Certified Kd"].get() == "0.975"
    assert clone.composition == {"Methane": 100.0}
    assert clone.update_calls == 1
    assert clone.mode_change_calls == 1


def test_apply_settings_payload_handles_legacy_cd_field():
    app = FakeApp()
    data = {
        "entries": {"Discharge Coeff (Cd)": "0.88"},
        "composition": {"Ethane": 25.0},
    }

    apply_settings_payload(app, data, default_engine_name="Yerel Çözücü")

    assert app.entries["Valve Discharge Coeff (Cd)"].get() == "0.88"
    assert app.entries["PSV Certified Kd"].get() == "0.88"
    assert app.composition == {"Ethane": 25.0}


def test_write_and_read_settings_payload():
    payload = {"mode": "demo", "entries": {"x": "1"}}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "settings.json")
        write_settings_payload(path, payload)
        loaded = read_settings_payload(path)
    assert loaded == payload


if __name__ == "__main__":
    test_build_and_apply_settings_payload_roundtrip()
    test_apply_settings_payload_handles_legacy_cd_field()
    test_write_and_read_settings_payload()
    print("TEST COMPLETED")
