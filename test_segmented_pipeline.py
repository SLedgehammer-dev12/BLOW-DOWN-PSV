import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from segmented_pipeline import (
    SEGMENTED_ENGINE_NAME,
    find_segmented_pipeline_blowdown_area,
    run_segmented_pipeline_blowdown_simulation,
)


def test_segmented_pipeline_solver():
    print("--- Segmented Pipeline Blowdown Test ---")
    d_in_m = 0.15
    l_m = 10.0
    t_m = 0.006
    v_sys = math.pi * ((d_in_m / 2) ** 2) * l_m
    a_inner = math.pi * d_in_m * l_m
    v_outer = math.pi * (((d_in_m + 2 * t_m) / 2) ** 2) * l_m
    m_steel = (v_outer - v_sys) * 7850.0

    inputs = {
        "composition": {"Methane": 1.0},
        "system_type": "Boru Hattı (Pipeline)",
        "V_sys": v_sys,
        "A_inner": a_inner,
        "M_steel": m_steel,
        "D_in_m": d_in_m,
        "L_m": l_m,
        "t_m": t_m,
        "p0_pa": 8.0e5 + 101325.0,
        "T0_k": 25.0 + 273.15,
        "p_target_blowdown_pa": 2.0e5 + 101325.0,
        "t_target_sec": 20.0,
        "p_downstream": 101325.0,
        "segment_count": 2,
        "Cd_valve": 0.90,
        "HT_enabled": False,
    }

    area_m2 = find_segmented_pipeline_blowdown_area(inputs, progress_callback=None, abort_flag=None)
    print(f"Segmented sized area: {area_m2 * 1e6:.2f} mm2")
    assert area_m2 > 0.0

    df = run_segmented_pipeline_blowdown_simulation(inputs, area_m2, progress_callback=None, abort_flag=None, silent=False)
    assert not df.empty
    assert df.attrs["engine"] == SEGMENTED_ENGINE_NAME
    assert df.attrs["friction_model"] == "darcy_weisbach_screening_with_choked_cap"
    assert {"p_upstream", "p_terminal", "p_avg"}.issubset(df.columns)
    assert {"segment_re", "segment_f"}.issubset(df.columns)
    assert df["segment_re"].iloc[-1] >= 0.0
    assert df["segment_f"].iloc[-1] >= 0.0
    assert any("Darcy-Weisbach" in warning for warning in df.attrs.get("warnings", []))
    print(f"Time to target: {df['t'].iloc[-1]:.1f} s")
    print(f"Final upstream pressure: {(df['p_upstream'].iloc[-1] - 101325.0) / 1e5:.2f} barg")
    print(f"Final terminal pressure: {(df['p_terminal'].iloc[-1] - 101325.0) / 1e5:.2f} barg")
    assert df["p_sys"].iloc[-1] <= inputs["p_target_blowdown_pa"] * 1.05
    assert df["t"].iloc[-1] <= inputs["t_target_sec"] * 1.2


if __name__ == "__main__":
    test_segmented_pipeline_solver()
    print("TEST COMPLETED")
