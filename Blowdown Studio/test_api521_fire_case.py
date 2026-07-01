from api521_fire_case import (
    build_pool_fire_case_screening,
    calculate_pool_fire_heat_input_si,
    estimate_cylindrical_wetted_area_m2,
)
from constants import P_ATM


def test_api521_fire_case_target_and_heat_input():
    result = build_pool_fire_case_screening(
        design_pressure_pa=P_ATM + 100.0e5,
        outer_diameter_m=0.5,
        length_m=12.0,
        environment_factor=1.0,
        scenario="Adequate drainage + firefighting",
    )

    assert abs(result.target_pressure_pa - (P_ATM + 50.0e5)) < 1.0
    assert abs(result.target_time_s - 900.0) < 1e-9
    assert result.wetted_area_m2 is not None
    assert result.heat_input_w is not None
    assert result.heat_input_w > 0.0


def test_api521_fire_heat_input_matches_helper():
    wetted_area = estimate_cylindrical_wetted_area_m2(outer_diameter_m=0.4, length_m=8.0)
    heat_input_w, coefficient_si = calculate_pool_fire_heat_input_si(
        wetted_area_m2=wetted_area,
        environment_factor=1.3,
        scenario="Poor drainage / limited firefighting",
    )

    assert wetted_area > 0.0
    assert coefficient_si == 70900.0
    assert heat_input_w > 0.0
