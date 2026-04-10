import json
import math
import os
import sys
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from constants import P_ATM
from psv_preliminary import (
    relieving_pressure_from_set_pressure,
    size_gas_or_vapor_area_api520,
    size_liquid_area_api520,
    size_steam_area_api520,
)

import importlib.util

spec = importlib.util.spec_from_file_location("blowdown_studio", os.path.join(current_dir, "blowdown_studio.py"))
blowdown_studio = importlib.util.module_from_spec(spec)
sys.modules["blowdown_studio"] = blowdown_studio
spec.loader.exec_module(blowdown_studio)

find_native_blowdown_area = blowdown_studio.find_native_blowdown_area
run_native_blowdown_simulation = blowdown_studio.run_native_blowdown_simulation


def load_baselines():
    baseline_path = Path(current_dir) / "regression_baselines.json"
    return json.loads(baseline_path.read_text(encoding="utf-8"))


def assert_regression_metric(actual, config, label):
    expected = config["value"]
    rel_tol = config.get("rel_tol")
    abs_tol = config.get("abs_tol")
    if rel_tol is not None:
        limit = rel_tol * max(abs(expected), 1.0)
    elif abs_tol is not None:
        limit = abs_tol
    else:
        raise AssertionError(f"{label}: tolerance tanimsiz")
    diff = abs(actual - expected)
    assert diff <= limit, f"{label}: beklenen {expected}, gercek {actual}, tolerans {limit}"


def test_regression_benchmark_suite():
    baselines = load_baselines()

    set_pressure_pa = 75.0 * 6894.76 + P_ATM
    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, 10.0)
    gas = size_gas_or_vapor_area_api520(
        W_req_kg_h=24270.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=77.2 * 6894.76,
        relieving_temperature_k=348.0,
        k_ideal=1.11,
        Z=0.90,
        MW_kg_kmol=51.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    assert_regression_metric(gas.A_req_mm2, baselines["api520_gas_subcritical_area_mm2"], "API520 gas area")

    steam = size_steam_area_api520(
        W_req_kg_h=69615.0,
        relieving_pressure_pa=12236e3,
        backpressure_pa=P_ATM,
        relieving_temperature_k=434.0 + 273.15,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    assert_regression_metric(steam.A_req_mm2, baselines["api520_steam_area_mm2"], "API520 steam area")

    liquid = size_liquid_area_api520(
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
    assert_regression_metric(liquid.A_req_mm2, baselines["api520_liquid_area_mm2"], "API520 liquid area")

    D_in_m = 0.5
    L_m = 1000.0
    t_m = 0.0127
    V_sys = math.pi * ((D_in_m / 2) ** 2) * L_m
    A_inner = math.pi * D_in_m * L_m
    v_outer = math.pi * (((D_in_m + 2 * t_m) / 2) ** 2) * L_m
    M_steel = (v_outer - V_sys) * 7850.0
    inputs = {
        "composition": {"Methane": 0.95, "Ethane": 0.05},
        "V_sys": V_sys,
        "A_inner": A_inner,
        "M_steel": M_steel,
        "D_in_m": D_in_m,
        "L_m": L_m,
        "t_m": t_m,
        "p0_pa": 100 * 1e5 + P_ATM,
        "T0_k": 50 + 273.15,
        "p_target_blowdown_pa": 6.89 * 1e5 + P_ATM,
        "t_target_sec": 900.0,
    }
    native_cfg = baselines["native_blowdown_pipeline"]
    area_m2 = find_native_blowdown_area(inputs, progress_callback=None, abort_flag=None)
    assert area_m2 is not None
    assert_regression_metric(area_m2 * 1e6, native_cfg["required_area_mm2"], "Native blowdown area")

    sim_df = run_native_blowdown_simulation(inputs, area_m2, progress_callback=None, abort_flag=None, silent=False)
    assert_regression_metric(float(sim_df["t"].iloc[-1]), native_cfg["time_to_target_s"], "Native blowdown time")
    assert_regression_metric(float(sim_df["T_sys"].min() - 273.15), native_cfg["min_gas_temperature_c"], "Native blowdown min gas temp")
    assert_regression_metric(float(sim_df["T_wall"].iloc[-1] - 273.15), native_cfg["final_wall_temperature_c"], "Native blowdown final wall temp")


if __name__ == "__main__":
    test_regression_benchmark_suite()
    print("TEST COMPLETED")
