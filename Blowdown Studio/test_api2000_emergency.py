import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api2000_engine import calculate_api2000_emergency_venting, calculate_api2000_venting


def test_api2000_normal_venting():
    res = calculate_api2000_venting(
        tank_volume_m3=7949.0,
        latitude=30.0,
        is_volatile=True,
        pump_in_m3h=100.0,
        pump_out_m3h=80.0,
        insulation_factor=1.0,
    )
    expected_thermal = 6.5 * (7949.0 ** 0.7)
    assert abs(res["thermal_inbreathing"] - expected_thermal) / expected_thermal < 1e-9
    assert res["c_factor_used"] == 6.5
    assert res["total_inbreathing"] > res["thermal_inbreathing"]
    assert res["total_outbreathing"] > res["thermal_outbreathing"]


def test_api2000_emergency_venting():
    res = calculate_api2000_emergency_venting(
        wetted_area_m2=120.0,
        latent_heat_kj_kg=280.0,
        vapor_mw_kg_kmol=44.0,
        fire_factor=1.0,
        drainage_condition="Adequate drainage + firefighting",
    )
    assert res["heat_input_w"] > 0.0
    assert res["vapor_generation_kg_h"] > 0.0
    assert res["emergency_venting_nm3_h"] > 0.0


if __name__ == "__main__":
    test_api2000_normal_venting()
    test_api2000_emergency_venting()
    print("TEST COMPLETED")
