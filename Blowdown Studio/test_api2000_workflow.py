import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api2000_workflow import (
    build_api2000_summary_text,
    latitude_band_to_value,
    run_api2000_workflow,
)


def test_latitude_band_to_value():
    assert latitude_band_to_value("Below 42") == 30
    assert latitude_band_to_value("42-58") == 50
    assert latitude_band_to_value("Above 58") == 65


def test_run_api2000_workflow_normal_only():
    result = run_api2000_workflow(
        tank_volume_m3=7949.0,
        latitude_band="Below 42",
        is_volatile=True,
        pump_in_m3h=100.0,
        pump_out_m3h=100.0,
        insulation_factor=1.0,
    )
    assert result.normal_result["c_factor_used"] == 6.5
    assert result.emergency_result is None
    assert "Toplam vacuum ihtiyacı" in result.summary_text


def test_run_api2000_workflow_with_emergency():
    result = run_api2000_workflow(
        tank_volume_m3=5000.0,
        latitude_band="42-58",
        is_volatile=False,
        pump_in_m3h=50.0,
        pump_out_m3h=60.0,
        insulation_factor=1.0,
        emergency_enabled=True,
        emergency_wetted_area_m2=120.0,
        latent_heat_kj_kg=250.0,
        vapor_mw_kg_kmol=44.0,
        fire_factor=1.0,
        drainage_condition="Adequate drainage + firefighting",
    )
    assert result.emergency_result is not None
    assert result.emergency_result["emergency_venting_nm3_h"] > 0.0
    assert "Emergency Venting / Fire Case Screening" in result.summary_text


def test_build_api2000_summary_text_basic():
    text = build_api2000_summary_text(
        {
            "c_factor_used": 4.0,
            "thermal_inbreathing": 10.0,
            "thermal_outbreathing": 8.0,
            "pump_out_component": 3.0,
            "pump_in_component": 2.0,
            "total_inbreathing": 13.0,
            "total_outbreathing": 10.0,
        },
        is_volatile=False,
    )
    assert "C faktörü                    : 4.000" in text
    assert "Uçucu akışkan                : Hayır" in text


if __name__ == "__main__":
    test_latitude_band_to_value()
    test_run_api2000_workflow_normal_only()
    test_run_api2000_workflow_with_emergency()
    test_build_api2000_summary_text_basic()
    print("TEST COMPLETED")
