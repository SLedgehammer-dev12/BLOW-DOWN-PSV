import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from psv_preliminary import P_ATM, relieving_pressure_from_set_pressure, size_gas_or_vapor_area_api520


PSI_TO_PA = 6894.76


def assert_close(actual, expected, rel_tol=0.02):
    diff = abs(actual - expected)
    limit = rel_tol * max(abs(expected), 1.0)
    assert diff <= limit, f"Beklenen {expected}, gerçek {actual}, tolerans {limit}"


def test_api520_examples():
    print("--- API 520-1 Preliminary Sizing Tests ---")
    set_pressure_pa = 75.0 * PSI_TO_PA + P_ATM
    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, 10.0)

    subcritical = size_gas_or_vapor_area_api520(
        W_req_kg_h=24270.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=77.2 * PSI_TO_PA,
        relieving_temperature_k=348.0,
        k_ideal=1.11,
        Z=0.90,
        MW_kg_kmol=51.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    print(f"Subcritical area: {subcritical.A_req_mm2:.2f} mm2")
    print(f"Subcritical F2: {subcritical.F2:.4f}")
    assert not subcritical.is_critical
    assert_close(subcritical.A_req_mm2, 4226.0, rel_tol=0.02)
    assert_close(subcritical.F2, 0.86, rel_tol=0.02)

    critical = size_gas_or_vapor_area_api520(
        W_req_kg_h=24270.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=P_ATM,
        relieving_temperature_k=348.0,
        k_ideal=1.11,
        Z=0.90,
        MW_kg_kmol=51.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    print(f"Critical area: {critical.A_req_mm2:.2f} mm2")
    assert critical.is_critical
    assert_close(critical.A_req_mm2, 3699.0, rel_tol=0.01)

    balanced_spring = size_gas_or_vapor_area_api520(
        W_req_kg_h=24270.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=77.2 * PSI_TO_PA,
        relieving_temperature_k=348.0,
        k_ideal=1.11,
        Z=0.90,
        MW_kg_kmol=51.0,
        valve_design="Balanced Spring",
        Kd=0.975,
        Kc=1.0,
    )
    print(f"Balanced spring area: {balanced_spring.A_req_mm2:.2f} mm2")
    assert not balanced_spring.is_critical
    assert_close(balanced_spring.A_req_mm2, subcritical.A_req_mm2, rel_tol=1e-9)

    print("TEST COMPLETED")


if __name__ == "__main__":
    test_api520_examples()
