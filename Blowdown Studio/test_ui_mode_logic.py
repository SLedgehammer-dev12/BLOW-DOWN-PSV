import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from ui_mode_logic import (
    FIELD_BACKPRESSURE_KB,
    FIELD_PSV_KD,
    FIELD_REQUIRED_CODE_STAMP,
    FIELD_REQUIRED_TRIM_CODE,
    FIELD_VALVE_CD,
    FIELD_VALVE_COUNT,
    build_mode_ui_state,
    build_psv_service_field_config,
)


def test_build_psv_service_field_config_gas():
    config = build_psv_service_field_config("Gas/Vapor", "0.650")
    assert "Nm3/h" in config.flow_units
    assert config.kd_default_value == "0.975"
    assert "API 520" in config.field_labels[FIELD_PSV_KD]


def test_build_psv_service_field_config_liquid():
    config = build_psv_service_field_config("Liquid", "0.975")
    assert "L/min" in config.flow_units
    assert config.kd_default_value == "0.650"
    assert "Kw" in config.field_labels[FIELD_BACKPRESSURE_KB]


def test_build_mode_ui_state_blowdown_fire_case():
    state = build_mode_ui_state(
        mode="Blowdown",
        fire_case_enabled=True,
        engine_name="Yerel Çözücü",
        app_version="v2.3.1",
    )
    assert any("MAWP / Dizayn" in field for field in state.visible_fields)
    assert FIELD_VALVE_COUNT in state.visible_fields
    assert FIELD_REQUIRED_CODE_STAMP in state.hidden_fields
    assert "transient" in state.helper_text.lower()
    assert state.show_fire_case_frame is True
    assert "Fire Case" in state.run_button_text
    assert state.placeholder_mode == "Blowdown"


def test_build_mode_ui_state_psv():
    state = build_mode_ui_state(
        mode="PSV Sizing",
        fire_case_enabled=False,
        engine_name="Yerel Çözücü",
        app_version="v2.3.1",
    )
    assert FIELD_PSV_KD in state.visible_fields
    assert FIELD_VALVE_COUNT in state.visible_fields
    assert FIELD_REQUIRED_CODE_STAMP in state.visible_fields
    assert FIELD_REQUIRED_TRIM_CODE in state.visible_fields
    assert FIELD_VALVE_CD in state.hidden_fields
    assert "vendor screening" in state.helper_text.lower()
    assert state.show_psv_options is True
    assert state.show_engine_options is False
    assert "PSV" in state.run_button_text
    assert "520-1" in state.run_button_text


if __name__ == "__main__":
    test_build_psv_service_field_config_gas()
    test_build_psv_service_field_config_liquid()
    test_build_mode_ui_state_blowdown_fire_case()
    test_build_mode_ui_state_psv()
    print("TEST COMPLETED")
