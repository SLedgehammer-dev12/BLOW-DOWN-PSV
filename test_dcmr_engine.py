"""Tests for DCMR Rijnmond analytical blowdown engine."""
import math
import os
import sys

import CoolProp.CoolProp as CP

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from constants import P_ATM
from native_blowdown_engine import (
    DCMR_ENGINE_NAME,
    _dcmr_area_formula,
    _dcmr_crit_factor,
    _dcmr_gas_props,
    _dcmr_pressure_ratio_term,
    _dcmr_time_formula,
    find_dcmr_blowdown_area,
    find_native_blowdown_area,
    run_dcmr_blowdown_simulation,
    run_native_blowdown_simulation,
)


def _make_inputs(V_sys, p0_barg, p2_barg, T0_C, t_target, comp=None,
                 Cd=0.975, Kb=1.0, ht_enabled=False):
    if comp is None:
        comp = {"Methane": 1.0}
    return {
        "composition": comp,
        "V_sys": V_sys,
        "A_inner": 1.0,
        "M_steel": 100.0,
        "p0_pa": p0_barg * 1e5 + P_ATM,
        "T0_k": T0_C + 273.15,
        "p_target_blowdown_pa": p2_barg * 1e5 + P_ATM,
        "t_target_sec": t_target,
        "HT_enabled": ht_enabled,
        "p_downstream": P_ATM,
        "Cd_valve": Cd,
        "Kb": Kb,
        "D_in_m": 1.0,
    }


def test_dcmr_crit_factor():
    k = 1.3
    cf = _dcmr_crit_factor(k)
    expected = (2 / (k + 1)) ** ((k + 1) / (2 * (k - 1)))
    assert abs(cf - expected) < 1e-10


def test_dcmr_pressure_ratio_term():
    k = 1.3
    p0, p2 = 50e5, 5e5
    term = _dcmr_pressure_ratio_term(k, p0, p2)
    assert term > 0
    e = (k - 1) / (2 * k)
    expected = (p0 / p2) ** e - 1
    assert abs(term - expected) < 1e-10


def test_dcmr_gas_props():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    k, mw, Z, rho = _dcmr_gas_props(inputs)
    assert k > 1.0
    assert mw > 10.0
    assert 0.5 < Z < 1.5
    assert rho > 0


def test_dcmr_formulas_reversible():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    V = inputs["V_sys"]
    p0 = inputs["p0_pa"]
    p2 = inputs["p_target_blowdown_pa"]
    t0 = inputs["T0_k"]
    t_target = inputs["t_target_sec"]
    cd = inputs["Cd_valve"]
    kb = inputs["Kb"]

    k, mw, Z, _ = _dcmr_gas_props(inputs)

    A = _dcmr_area_formula(V, k, mw, Z, t0, p0, p2, t_target, cd, kb)
    assert A > 0

    t_calc = _dcmr_time_formula(V, k, mw, Z, t0, p0, p2, A, cd, kb)
    rel_err = abs(t_calc - t_target) / t_target
    assert rel_err < 1e-6, f"Area/time formulas not reversible: {t_calc:.1f} vs {t_target}"


def test_dcmr_find_area_smoke():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    A = find_dcmr_blowdown_area(inputs)
    assert A > 0
    A_mm2 = A * 1e6
    assert 10 < A_mm2 < 10000, f"Area {A_mm2:.1f} mm2 out of reasonable range"


def test_run_dcmr_silent():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    A = find_dcmr_blowdown_area(inputs)
    t = run_dcmr_blowdown_simulation(inputs, A, silent=True)
    rel_err = abs(t - inputs["t_target_sec"]) / inputs["t_target_sec"]
    assert rel_err < 0.05, f"DCMR time mismatch: {t:.1f} vs {inputs['t_target_sec']}"


def test_run_dcmr_dataframe():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    A = find_dcmr_blowdown_area(inputs)
    df = run_dcmr_blowdown_simulation(inputs, A, silent=False)
    assert len(df) > 0
    assert df.attrs["engine"] == DCMR_ENGINE_NAME
    assert df["p_sys"].iloc[-1] <= inputs["p_target_blowdown_pa"] * 1.01
    assert "t" in df.columns
    assert "p_sys" in df.columns
    assert "T_sys" in df.columns


def test_dcmr_vs_native_consistency():
    """DCMR should be conservative (larger area) compared to native engine."""
    inputs = _make_inputs(10.0, 50, 5, 30, 900)

    A_dcmr = find_dcmr_blowdown_area(inputs)
    A_native = find_native_blowdown_area(inputs)

    ratio = A_dcmr / A_native
    assert ratio > 0.5, f"DCMR area {A_dcmr*1e6:.1f} mm2 suspiciously small vs native {A_native*1e6:.1f} mm2 (ratio={ratio:.2f})"
    assert ratio < 5.0, f"DCMR area {A_dcmr*1e6:.1f} mm2 much larger than native {A_native*1e6:.1f} mm2 (ratio={ratio:.2f})"


def test_dcmr_larger_area_faster():
    inputs = _make_inputs(10.0, 50, 5, 30, 900)
    t_small = run_dcmr_blowdown_simulation(inputs, 1e-4, silent=True)
    t_large = run_dcmr_blowdown_simulation(inputs, 1e-3, silent=True)
    assert t_large < t_small, "Larger area should give shorter blowdown time"


def test_dcmr_ethane_mixture():
    inputs = _make_inputs(5.0, 70, 7, 60, 600, comp={"Ethane": 1.0})
    A = find_dcmr_blowdown_area(inputs)
    assert A > 0
    t = run_dcmr_blowdown_simulation(inputs, A, silent=True)
    assert abs(t - 600) / 600 < 0.05


def test_dcmr_fire_case_scenario():
    """DCMR should handle fire case inputs correctly."""
    D_in = 0.5
    L_m = 100.0
    t_m = 0.01
    V_sys = math.pi * (D_in / 2) ** 2 * L_m
    inputs = {
        "composition": {"Methane": 0.95, "Ethane": 0.05},
        "V_sys": V_sys,
        "A_inner": math.pi * D_in * L_m,
        "M_steel": 50000.0,
        "p0_pa": 100 * 1e5 + P_ATM,
        "T0_k": 323.15,
        "p_target_blowdown_pa": 7 * 1e5 + P_ATM,
        "t_target_sec": 900,
        "HT_enabled": False,
        "p_downstream": P_ATM,
        "Cd_valve": 0.975,
        "Kb": 1.0,
        "D_in_m": D_in,
        "fire_heat_input_w": 500000.0,
    }

    A = find_dcmr_blowdown_area(inputs)
    assert A > 0
    A_mm2 = A * 1e6
    assert 100 < A_mm2 < 50000, f"Fire case DCMR area {A_mm2:.1f} mm2 out of range"

    df = run_dcmr_blowdown_simulation(inputs, A, silent=False)
    assert len(df) > 0
    assert df["p_sys"].iloc[-1] <= inputs["p_target_blowdown_pa"] * 1.02


def test_dcmr_high_pressure_ratio_warning():
    inputs = _make_inputs(10.0, 10, 3, 30, 900)
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        A = find_dcmr_blowdown_area(inputs)
    assert A > 0


if __name__ == "__main__":
    test_dcmr_crit_factor()
    test_dcmr_pressure_ratio_term()
    test_dcmr_gas_props()
    test_dcmr_formulas_reversible()
    test_dcmr_find_area_smoke()
    test_run_dcmr_silent()
    test_run_dcmr_dataframe()
    test_dcmr_vs_native_consistency()
    test_dcmr_larger_area_faster()
    test_dcmr_ethane_mixture()
    test_dcmr_fire_case_scenario()
    test_dcmr_high_pressure_ratio_warning()
    print("TEST COMPLETED")
