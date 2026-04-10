import math

from constants import P_ATM
from hyddown_adapter import build_hyddown_input, run_hyddown_blowdown_simulation
from psv_preliminary import calculate_preliminary_gas_psv_area
from segmented_pipeline import SEGMENTED_ENGINE_NAME, run_segmented_pipeline_blowdown_simulation


HEAVY_NATURAL_GAS = {
    "Methane": 0.89,
    "Ethane": 0.04,
    "Propane": 0.02,
    "n-Butane": 0.01,
    "IsoButane": 0.005,
    "n-Pentane": 0.003,
    "Isopentane": 0.002,
    "CarbonDioxide": 0.01,
    "Nitrogen": 0.009,
    "HydrogenSulfide": 0.001,
}

LIGHT_NATURAL_GAS = {
    "Methane": 0.97,
    "Ethane": 0.02,
    "Nitrogen": 0.01,
}


def _build_pipeline_inputs(composition, *, length_m, target_time_s, start_barg, target_barg, temperature_c):
    d_in_m = 0.08
    t_m = 0.004
    v_sys = math.pi * ((d_in_m / 2.0) ** 2) * length_m
    a_inner = math.pi * d_in_m * length_m
    v_outer = math.pi * (((d_in_m + 2.0 * t_m) / 2.0) ** 2) * length_m
    m_steel = (v_outer - v_sys) * 7850.0
    return {
        "composition": composition,
        "V_sys": v_sys,
        "A_inner": a_inner,
        "M_steel": m_steel,
        "D_in_m": d_in_m,
        "L_m": length_m,
        "t_m": t_m,
        "p0_pa": P_ATM + start_barg * 1e5,
        "T0_k": 273.15 + temperature_c,
        "p_target_blowdown_pa": P_ATM + target_barg * 1e5,
        "t_target_sec": target_time_s,
        "system_type": "Boru Hattı (Pipeline)",
        "HT_enabled": False,
        "Cd_valve": 0.84,
        "p_downstream": P_ATM,
        "valve_count": 1,
    }


def test_multicomponent_psv_preliminary_regression():
    inputs = {
        "composition": HEAVY_NATURAL_GAS,
        "set_pressure_pa": P_ATM + 85e5,
        "mawp_pa": P_ATM + 85e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 323.15,
        "p_total_backpressure_pa": P_ATM + 5e5,
        "prv_design": "Balanced Bellows",
        "W_req_kg_h": 18000.0,
        "Kd_api520": 0.975,
        "Kc": 1.0,
        "Kb": 0.85,
    }

    result = calculate_preliminary_gas_psv_area(inputs)
    assert result.A_req_mm2 > 0.0
    assert 0.6 < result.Z < 1.2
    assert 17.0 < result.MW_kg_kmol < 30.0
    assert 1.0 < result.k_real < 2.5


def test_multicomponent_segmented_pipeline_smoke():
    inputs = _build_pipeline_inputs(
        LIGHT_NATURAL_GAS,
        length_m=1.0,
        target_time_s=5.0,
        start_barg=8.0,
        target_barg=3.0,
        temperature_c=30.0,
    )

    sim_df = run_segmented_pipeline_blowdown_simulation(inputs, 3.0e-4, silent=False)
    assert sim_df.attrs["engine"] == SEGMENTED_ENGINE_NAME
    assert sim_df.attrs["time_to_target"] > 0.0
    assert sim_df["p_sys"].iloc[-1] < inputs["p0_pa"]
    assert {"segment_re", "segment_f"}.issubset(sim_df.columns)


def test_multicomponent_hyddown_smoke():
    inputs = _build_pipeline_inputs(
        LIGHT_NATURAL_GAS,
        length_m=2.0,
        target_time_s=30.0,
        start_barg=10.0,
        target_barg=3.0,
        temperature_c=30.0,
    )

    hyddown_input = build_hyddown_input(inputs, 1.23069091796875e-06)
    assert "&" in hyddown_input["initial"]["fluid"]

    sim_df = run_hyddown_blowdown_simulation(inputs, 1.23069091796875e-06, silent=False)
    assert sim_df.attrs["engine"] == "HydDown"
    assert 20.0 <= sim_df.attrs["time_to_target"] <= 40.0
    assert sim_df["p_sys"].iloc[-1] < inputs["p0_pa"]


def test_heavy_multicomponent_segmented_failure_is_controlled():
    inputs = _build_pipeline_inputs(
        HEAVY_NATURAL_GAS,
        length_m=20.0,
        target_time_s=240.0,
        start_barg=70.0,
        target_barg=7.0,
        temperature_c=60.0,
    )

    try:
        run_segmented_pipeline_blowdown_simulation(inputs, 8.0e-5, silent=False)
    except RuntimeError as exc:
        assert "termodinamik çözücü hatası" in str(exc)
        assert "segmented pipeline" in str(exc)
        return
    raise AssertionError("Ağır çok bileşenli segmented vaka için kontrollü RuntimeError bekleniyordu")


if __name__ == "__main__":
    test_multicomponent_psv_preliminary_regression()
    test_multicomponent_segmented_pipeline_smoke()
    test_multicomponent_hyddown_smoke()
    test_heavy_multicomponent_segmented_failure_is_controlled()
    print("TEST COMPLETED")
