import os
import sys
from types import SimpleNamespace

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

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
    collect_api2000_ui_payload,
    run_api2000_ui_with_feedback,
)


class FakeField:
    def __init__(self, value=""):
        self.value = str(value)

    def get(self):
        return self.value


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value


class FakeApp:
    def __init__(self, emergency_enabled=False):
        self.api_entries = {
            API2000_FIELD_TANK_VOLUME: FakeField("1000"),
            API2000_FIELD_LATITUDE: FakeField("Below 42"),
            API2000_FIELD_PUMP_IN: FakeField("25"),
            API2000_FIELD_PUMP_OUT: FakeField("30"),
            API2000_FIELD_INSULATION: FakeField("1.0"),
            API2000_FIELD_EMERGENCY_WETTED_AREA: FakeField("120"),
            API2000_FIELD_LATENT_HEAT: FakeField("250"),
            API2000_FIELD_VAPOR_MW: FakeField("44"),
            API2000_FIELD_FIRE_FACTOR: FakeField("1.0"),
        }
        self.api_volatile_var = FakeVar(True)
        self.api_emergency_var = FakeVar(emergency_enabled)
        self.api_emergency_combo = FakeField("Adequate drainage + firefighting")


def test_collect_api2000_ui_payload_normal_only():
    app = FakeApp(emergency_enabled=False)
    payload = collect_api2000_ui_payload(app)

    assert payload["tank_volume_m3"] == 1000.0
    assert payload["emergency_enabled"] is False
    assert payload["emergency_wetted_area_m2"] is None


def test_collect_api2000_ui_payload_with_emergency():
    app = FakeApp(emergency_enabled=True)
    payload = collect_api2000_ui_payload(app)

    assert payload["emergency_enabled"] is True
    assert payload["emergency_wetted_area_m2"] == 120.0
    assert payload["latent_heat_kj_kg"] == 250.0


def test_collect_api2000_ui_payload_required_field_validation():
    app = FakeApp(emergency_enabled=False)
    app.api_entries[API2000_FIELD_TANK_VOLUME] = FakeField("")
    try:
        collect_api2000_ui_payload(app)
    except ValueError as exc:
        assert "alanı zorunludur" in str(exc)
        return
    raise AssertionError("Boş zorunlu alan için ValueError bekleniyordu")


def test_collect_api2000_ui_payload_positive_validation():
    app = FakeApp(emergency_enabled=False)
    app.api_entries[API2000_FIELD_PUMP_IN] = FakeField("0")
    try:
        collect_api2000_ui_payload(app)
    except ValueError as exc:
        assert "pozitif olmalıdır" in str(exc)
        return
    raise AssertionError("Pozitif olmayan alan için ValueError bekleniyordu")


def test_run_api2000_ui_with_feedback_success():
    app = FakeApp(emergency_enabled=False)
    messages = []
    errors = []
    workflow = SimpleNamespace(summary_text="summary")

    returned = run_api2000_ui_with_feedback(
        app,
        run_workflow_fn=lambda **_kwargs: workflow,
        set_text_fn=messages.append,
        log_info_fn=messages.append,
        showerror_fn=lambda title, text: errors.append((title, text)),
    )

    assert returned is workflow
    assert messages[0] == "summary"
    assert not errors


def test_run_api2000_ui_with_feedback_validation_error():
    app = FakeApp(emergency_enabled=False)
    app.api_entries[API2000_FIELD_TANK_VOLUME] = FakeField("")
    messages = []
    errors = []

    returned = run_api2000_ui_with_feedback(
        app,
        run_workflow_fn=lambda **_kwargs: SimpleNamespace(summary_text="summary"),
        set_text_fn=messages.append,
        log_info_fn=messages.append,
        showerror_fn=lambda title, text: errors.append((title, text)),
    )

    assert returned is None
    assert not messages
    assert errors and "Tank Hacmi" in errors[0][1]


if __name__ == "__main__":
    test_collect_api2000_ui_payload_normal_only()
    test_collect_api2000_ui_payload_with_emergency()
    test_collect_api2000_ui_payload_required_field_validation()
    test_collect_api2000_ui_payload_positive_validation()
    test_run_api2000_ui_with_feedback_success()
    test_run_api2000_ui_with_feedback_validation_error()
    print("TEST COMPLETED")
