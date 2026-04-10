import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api521_discharge_piping import calculate_discharge_piping_loss


def test_discharge_piping_reynolds_and_losses():
    result = calculate_discharge_piping_loss(
        pipe_length_m=12.0,
        pipe_diameter_mm=100.0,
        elbow_count=2,
        tee_count=1,
        check_valve_count=1,
        roughness_mm=0.045,
        mass_flow_kg_s=5.0,
        gas_density_kg_m3=10.0,
        gas_viscosity_pa_s=1.0e-5,
    )

    area_m2 = math.pi * (0.1 ** 2) / 4.0
    velocity = 5.0 / (10.0 * area_m2)
    reynolds_expected = 10.0 * velocity * 0.1 / 1.0e-5

    assert math.isclose(result["velocity_m_s"], velocity, rel_tol=1e-9)
    assert math.isclose(result["reynolds_number"], reynolds_expected, rel_tol=1e-9)
    assert result["pipe_friction_loss"] > 0.0
    assert result["fittings_loss"] > 0.0
    assert result["total_K"] == result["pipe_friction_loss"] + result["fittings_loss"]
    assert result["details"]["roughness_mm"] == 0.045


def test_discharge_piping_fallback_reynolds():
    result = calculate_discharge_piping_loss(
        pipe_length_m=5.0,
        pipe_diameter_mm=80.0,
        elbow_count=1,
    )
    assert result["reynolds_number"] == 1.0e5
    assert result["velocity_m_s"] is None


if __name__ == "__main__":
    test_discharge_piping_reynolds_and_losses()
    test_discharge_piping_fallback_reynolds()
    print("TEST COMPLETED")
