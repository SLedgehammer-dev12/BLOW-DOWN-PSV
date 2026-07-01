import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from hyddown_adapter import build_hyddown_input, find_hyddown_blowdown_area, run_hyddown_blowdown_simulation


def test_hyddown_adapter():
    print("--- HydDown Adapter Integration Test ---")
    inputs = {
        "composition": {"Methane": 1.0},
        "D_in_m": 0.1,
        "L_m": 5.0,
        "t_m": 0.005,
        "T0_k": 293.15,
        "p0_pa": 101325.0 + 10e5,
        "p_target_blowdown_pa": 101325.0 + 2e5,
        "t_target_sec": 60.0,
        "system_type": "Boru Hattı (Pipeline)",
        "HT_enabled": False,
        "Cd": 0.84,
        "p_downstream": 101325.0,
    }

    hyddown_input = build_hyddown_input(inputs, 5e-5)
    print(f"Fluid string: {hyddown_input['initial']['fluid']}")
    assert hyddown_input["initial"]["fluid"] == "Methane"

    area = find_hyddown_blowdown_area(inputs)
    print(f"Sized area: {area:.9f} m2")
    assert area > 0.0
    assert area < math.pi * inputs["D_in_m"] ** 2 / 4.0

    df = run_hyddown_blowdown_simulation(inputs, area, silent=False)
    print(f"Time to target: {df.attrs['time_to_target']:.2f} s")
    assert df.attrs["engine"] == "HydDown"
    assert abs(df.attrs["time_to_target"] - inputs["t_target_sec"]) / inputs["t_target_sec"] < 0.05
    assert {"t", "p_sys", "T_sys", "T_wall", "mdot_kg_s"}.issubset(df.columns)

    print("TEST COMPLETED")


if __name__ == "__main__":
    test_hyddown_adapter()
