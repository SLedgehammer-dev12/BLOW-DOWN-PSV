import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from constants import P_ATM
from psv_preliminary import (
    calculate_preliminary_liquid_psv_area,
    calculate_preliminary_steam_psv_area,
    napier_correction_kn_si,
    size_liquid_area_api520,
    size_steam_area_api520,
)


def assert_close(actual, expected, rel_tol=0.02):
    diff = abs(actual - expected)
    limit = rel_tol * max(abs(expected), 1.0)
    assert diff <= limit, f"Beklenen {expected}, gerçek {actual}, tolerans {limit}"


def test_steam_example_4():
    print("--- API 520-1 Steam Example Test ---")
    res = size_steam_area_api520(
        W_req_kg_h=69615.0,
        relieving_pressure_pa=12236e3,
        backpressure_pa=P_ATM,
        relieving_temperature_k=434.0 + 273.15,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    print(f"Steam area: {res.A_req_mm2:.2f} mm2")
    print(f"KN: {res.KN:.4f}")
    print(f"KSH: {res.KSH:.4f}")
    assert_close(res.A_req_mm2, 1287.0, rel_tol=0.01)
    assert_close(res.KN, 1.01, rel_tol=0.01)
    assert_close(res.KSH, 0.855, rel_tol=0.005)


def test_liquid_example_without_viscosity_correction():
    print("--- API 520-1 Liquid Example Baseline ---")
    res = size_liquid_area_api520(
        Q_req_l_min=6814.0,
        relieving_pressure_pa=P_ATM + 1896e3,
        backpressure_pa=P_ATM + 345e3,
        specific_gravity=0.90,
        viscosity_cp=50.0,
        valve_design="Balanced Bellows",
        Kd=0.65,
        Kc=1.0,
        Kw=0.97,
    )
    print(f"Liquid area: {res.A_req_mm2:.2f} mm2")
    print(f"Kv: {res.Kv_used:.3f}")
    assert_close(res.A_req_mm2, 3066.0, rel_tol=0.01)
    assert_close(res.Kv_used, 1.0, rel_tol=1e-6)


def test_liquid_preliminary_accepts_kw_key():
    res = calculate_preliminary_liquid_psv_area(
        {
            "composition": {"Propane": 1.0},
            "set_pressure_pa": P_ATM + 15.0e5,
            "overpressure_pct": 10.0,
            "relieving_temperature_k": 298.15,
            "p_total_backpressure_pa": P_ATM + 2.0e5,
            "prv_design": "Balanced Bellows",
            "Kd_api520": 0.65,
            "Kw": 0.96,
            "Q_req_l_min": 2500.0,
        }
    )
    assert_close(res.Kw_used, 0.96, rel_tol=1e-9)


# ── B. Supercritical Steam Tests ──────────────────────────────────────────

def test_steam_supercritical_fallback():
    """P > 22.064 MPa kritik nokta -> gas fallback calismali, crash olmamali."""
    res = size_steam_area_api520(
        W_req_kg_h=69615.0,
        relieving_pressure_pa=221e5,
        backpressure_pa=P_ATM,
        relieving_temperature_k=650.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    assert res.A_req_mm2 > 0.0, "Supercritical steam fallback alan uretemedi."
    fallback_warnings = [w for w in res.warnings if "fallback" in w.lower()]
    assert any("fallback" in w.lower() or "kritik" in w.lower().replace("subkritik", "") for w in res.warnings), (
        f"Supercritical steam fallback uyarisi bekleniyor: {res.warnings}"
    )


def test_steam_near_critical_boundary():
    """P=22.0 MPa (kritik nokta alti) -> normal steam sizing calismali."""
    res = size_steam_area_api520(
        W_req_kg_h=69615.0,
        relieving_pressure_pa=220e5,
        backpressure_pa=P_ATM,
        relieving_temperature_k=650.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    assert res.A_req_mm2 > 0.0
    assert res.equation_id != "", "Equation ID dolu olmali."


def test_preliminary_steam_high_pressure():
    """calculate_preliminary_steam_psv_area yuksek basincla crash olmamali."""
    res = calculate_preliminary_steam_psv_area(
        {
            "composition": {"Water": 1.0},
            "set_pressure_pa": P_ATM + 210e5,
            "overpressure_pct": 10.0,
            "relieving_temperature_k": 650.0,
            "p_total_backpressure_pa": P_ATM,
            "prv_design": "Conventional",
            "Kd_api520": 0.975,
            "W_req_kg_h": 69615.0,
        }
    )
    assert res.A_req_mm2 > 0.0


# ── E. Napier KN Safety Tests ─────────────────────────────────────────────

def test_napier_correction_boundaries():
    """Napier KN sinir degerlerde dogru sonuc vermeli."""
    kn_low = napier_correction_kn_si(10339e3)
    assert_close(kn_low, 1.0, rel_tol=1e-9)

    kn_high = napier_correction_kn_si(22057e3)
    assert kn_high > 0.0


def test_napier_kn_above_limit_through_steam_sizing():
    """P > 22057 kPa ile size_steam_area_api520 crash olmadan gas fallback'e gitmeli."""
    res = size_steam_area_api520(
        W_req_kg_h=69615.0,
        relieving_pressure_pa=230e5,
        backpressure_pa=P_ATM,
        relieving_temperature_k=650.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    assert res.A_req_mm2 > 0.0
    fallback_warnings = [w for w in res.warnings if "fallback" in w.lower()]
    assert len(fallback_warnings) > 0, f"Napier KN fallback uyarisi bekleniyor: {res.warnings}"


def test_preliminary_steam_above_napier_limit():
    """calculate_preliminary_steam_psv_area P=250 barg ile crash olmamali."""
    res = calculate_preliminary_steam_psv_area(
        {
            "composition": {"Water": 1.0},
            "set_pressure_pa": P_ATM + 250e5,
            "overpressure_pct": 10.0,
            "relieving_temperature_k": 700.0,
            "p_total_backpressure_pa": P_ATM,
            "prv_design": "Conventional",
            "Kd_api520": 0.975,
            "W_req_kg_h": 69615.0,
        }
    )
    assert res.A_req_mm2 > 0.0


if __name__ == "__main__":
    test_steam_example_4()
    test_liquid_example_without_viscosity_correction()
    test_liquid_preliminary_accepts_kw_key()
    test_steam_supercritical_fallback()
    test_steam_near_critical_boundary()
    test_preliminary_steam_high_pressure()
    test_napier_correction_boundaries()
    test_napier_kn_above_limit_through_steam_sizing()
    test_preliminary_steam_above_napier_limit()
    print("TEST COMPLETED")
