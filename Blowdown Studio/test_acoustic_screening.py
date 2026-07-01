import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from acoustic_screening import (
    calculate_acoustic_velocity,
    calculate_aiv_vibration,
    check_acoustic_fatigue,
)


def test_real_gas_speed_of_sound_methane():
    speed = calculate_acoustic_velocity({"Methane": 1.0}, 101325.0, 298.15)
    assert 430.0 <= speed <= 470.0


def test_acoustic_fatigue_thresholds():
    low = check_acoustic_fatigue(90.0, 450.0, pipe_diameter_mm=100.0, gas_density_kg_m3=1.0)
    moderate = check_acoustic_fatigue(180.0, 450.0, pipe_diameter_mm=100.0, gas_density_kg_m3=1.0)
    high = check_acoustic_fatigue(260.0, 450.0, pipe_diameter_mm=100.0, gas_density_kg_m3=1.0)

    assert low["status"] == "OK"
    assert low["fatigue_risk"] == "LOW"
    assert moderate["fatigue_risk"] == "MODERATE"
    assert high["fatigue_risk"] == "HIGH"
    assert float(high["jet_mechanical_power_w"]) > float(moderate["jet_mechanical_power_w"]) > float(low["jet_mechanical_power_w"])
    assert float(high["acoustic_power"]) > float(moderate["acoustic_power"]) > float(low["acoustic_power"])
    assert float(high["sound_power_level_db"]) > float(moderate["sound_power_level_db"]) > float(low["sound_power_level_db"])


def test_aiv_screening_has_no_fake_amplitude():
    result = calculate_aiv_vibration(0.55, 150.0, frequency_hz=950.0)
    assert result["amplitude_mm"] is None
    assert float(result["aiv_screening_index"]) > 0.0
    assert isinstance(result["resonance_risk"], bool)
    assert result["aiv_risk"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}


if __name__ == "__main__":
    test_real_gas_speed_of_sound_methane()
    test_acoustic_fatigue_thresholds()
    test_aiv_screening_has_no_fake_amplitude()
    print("TEST COMPLETED")
