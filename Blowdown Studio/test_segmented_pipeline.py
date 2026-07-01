import math
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from segmented_pipeline import (
    SEGMENTED_ENGINE_NAME,
    _darcy_friction_factor,
    find_segmented_pipeline_blowdown_area,
    run_segmented_pipeline_blowdown_simulation,
)


def assert_close(actual, expected, rel_tol=0.02):
    diff = abs(actual - expected)
    limit = rel_tol * max(abs(expected), 1.0)
    assert diff <= limit, f"Beklenen {expected}, gerçek {actual}, tolerans {limit}"


# ── D. Laminar-Turbulent Friction Transition Tests ────────────────────────

def test_darcy_friction_transition_smooth():
    """Laminer-turbulans gecisi Re=2000-4000 arasinda surekli olmali."""
    roughness = 0.045e-3 / 0.15
    f_vals = {}
    for re in range(2000, 4100, 50):
        f_vals[re] = _darcy_friction_factor(float(re), roughness)

    max_jump = max(
        abs(f_vals[re] - f_vals[re - 50]) for re in range(2050, 4100, 50)
    )
    assert max_jump < 0.005, (
        f"Gecis bolgesinde maksimum sicrama {max_jump:.4f}, 0.005'den kucuk olmali."
    )


def test_darcy_friction_edge_cases():
    """Sinir degerlerde fonksiyon kararli davranmali."""
    roughness = 0.0
    f_zero = _darcy_friction_factor(0.0, roughness)
    assert isinstance(f_zero, float)
    assert f_zero > 0.0

    f_neg = _darcy_friction_factor(-100.0, roughness)
    assert isinstance(f_neg, float)

    f_lam = _darcy_friction_factor(1500.0, roughness)
    assert_close(f_lam, 64.0 / 1500.0, rel_tol=1e-9)

    f_turb = _darcy_friction_factor(100000.0, 0.001)
    assert 0.01 <= f_turb <= 0.05


def test_darcy_friction_discontinuity_before_fix():
    """f(2299) ile f(2300) arasinda buyuk sicrama OLMAMALI (duzeltme sonrasi)."""
    roughness = 0.045e-3 / 0.15
    f_2299 = _darcy_friction_factor(2299.0, roughness)
    f_2300 = _darcy_friction_factor(2300.0, roughness)
    jump = abs(f_2300 - f_2299) / max(f_2299, 1e-9)
    assert jump < 0.15, f"Re=2299->2300 gecisinde %{jump*100:.1f} sicrama var (sinir: %%15)."


# ── A. CFL Stability Tests ────────────────────────────────────────────────

def test_segmented_pipeline_solver_cfl_stable():
    """CFL kosulu uygulanan segmented pipeline cozucusu kararli sonuc vermeli."""
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
    assert area_m2 > 0.0

    df = run_segmented_pipeline_blowdown_simulation(inputs, area_m2, progress_callback=None, abort_flag=None, silent=False)
    assert not df.empty
    assert df["p_sys"].iloc[-1] <= inputs["p_target_blowdown_pa"] * 1.05
    assert df["segment_re"].iloc[-1] >= 0.0


def test_segmented_pipeline_cfl_short_segments():
    """Kisa segmentlerde CFL limiti dt'yi kucultmali, cozucu kararli kalmali."""
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
        "p_target_blowdown_pa": 4.0e5 + 101325.0,
        "t_target_sec": 5.0,
        "p_downstream": 101325.0,
        "segment_count": 5,
        "Cd_valve": 0.90,
        "HT_enabled": False,
    }

    area_m2 = find_segmented_pipeline_blowdown_area(inputs, progress_callback=None, abort_flag=None)
    assert area_m2 > 0.0

    df = run_segmented_pipeline_blowdown_simulation(inputs, area_m2, progress_callback=None, abort_flag=None, silent=False)
    assert not df.empty
    assert df["p_sys"].iloc[-1] <= inputs["p_target_blowdown_pa"] * 1.05
    assert len(df) > 5, f"Segmentli cozumde en az 5 zaman adimi beklenir: {len(df)}"


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
