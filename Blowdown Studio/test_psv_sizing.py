import math
import os
import sys

import CoolProp.CoolProp as CP

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import blowdown_studio as studio
from native_blowdown_engine import calculate_reaction_force, parse_outlet_diameter_mm
from psv_preliminary import calculate_preliminary_gas_psv_area


def test_psv_mode():
    print("--- PSV SIZING ADVANCED LOGIC TEST ---")

    comp = {'Methane': 1.0}
    inputs = {
        'W_req_kg_h': 10000.0,
        'set_pressure_pa': 101325 + 100e5,
        'mawp_pa': 101325 + 100e5,
        'overpressure_pct': 0.0,
        'relieving_temperature_k': 298.15,
        'composition': comp,
        'Kd': 0.975,
        'Kb': 1.0,
        'Kc': 1.0,
        'prv_design': 'Conventional',
        'p_total_backpressure_pa': 101325 + 5e5,
    }

    sizing = calculate_preliminary_gas_psv_area(inputs)
    print(f"Area req: {sizing.A_req_m2*1e6:.2f}")
    print(f"Choked: {sizing.is_critical}")
    assert sizing.A_req_m2 > 0.0

    # Reaction force screening now uses discharge/outlet area instead of orifice area.
    W_kg_s = inputs['W_req_kg_h'] / 3600.0
    pipe_d_mm = parse_outlet_diameter_mm('DN50 x DN80')
    A_pipe_m2 = math.pi * ((pipe_d_mm / 1000.0) / 2.0) ** 2
    F_N = calculate_reaction_force(
        W_kg_s,
        inputs['relieving_temperature_k'],
        sizing.relieving_pressure_pa,
        A_pipe_m2,
        sizing.k_real,
        sizing.MW_kg_kmol,
        p_exit_pa=sizing.backpressure_pa,
    )
    print(f"Reaction Force: {F_N:.2f} N")

    # Backpressure check
    bp_pct = (inputs['p_total_backpressure_pa'] / sizing.relieving_pressure_pa) * 100.0
    print(f"Backpressure Ratio: {bp_pct:.2f}%")
    assert bp_pct > 0.0

    # Mach Number screening in discharge pipe
    state_down = CP.AbstractState("HEOS", "Methane")
    state_down.update(CP.HmassP_INPUTS, sizing.h_relieving_j_kg, sizing.backpressure_pa)
    rho_down = state_down.rhomass()
    c_down = state_down.speed_sound()
    v_down = W_kg_s / (rho_down * A_pipe_m2)
    mach = v_down / c_down
    print(f"Mach Number (DN80): {mach:.3f}")
    assert F_N > 0.0
    assert mach > 0.0

    F_low_bp = calculate_reaction_force(
        W_kg_s,
        inputs['relieving_temperature_k'],
        sizing.relieving_pressure_pa,
        A_pipe_m2,
        sizing.k_real,
        sizing.MW_kg_kmol,
        p_exit_pa=101325.0,
    )
    assert F_N >= F_low_bp

    subcritical_inputs = {
        'W_req_kg_h': 1000.0,
        'set_pressure_pa': 2.0e5,
        'mawp_pa': 2.0e5,
        'overpressure_pct': 0.0,
        'relieving_temperature_k': 298.15,
        'composition': comp,
        'Kd': 0.975,
        'Kb': 1.0,
        'Kc': 1.0,
        'prv_design': 'Conventional',
        'p_total_backpressure_pa': 1.8e5,
    }
    high_bp = calculate_preliminary_gas_psv_area(subcritical_inputs)
    low_bp_inputs = dict(subcritical_inputs)
    low_bp_inputs['p_total_backpressure_pa'] = 101325.0
    low_bp = calculate_preliminary_gas_psv_area(low_bp_inputs)
    print(f"Area req at high backpressure: {high_bp.A_req_m2*1e6:.2f}")
    print(f"Area req at atmospheric backpressure: {low_bp.A_req_m2*1e6:.2f}")
    assert not high_bp.is_critical
    assert low_bp.is_critical
    assert high_bp.A_req_m2 > low_bp.A_req_m2

    print("\nTEST COMPLETED")


if __name__ == "__main__":
    test_psv_mode()
