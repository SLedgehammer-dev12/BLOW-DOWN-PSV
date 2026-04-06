import sys
import os

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_psv_mode():
    print("--- PSV SIZING ADVANCED LOGIC TEST ---")
    import importlib.util
    spec = importlib.util.spec_from_file_location("blowdown_studio", os.path.join(current_dir, "blowdown_studio.py"))
    v3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v3)
    
    comp = {'Methane': 1.0}
    inputs = {
        'W_req_kg_h': 10000.0,
        'p0_pa': 101325 + 100e5,
        'T0_k': 298.15,
        'composition': comp,
        'Cd': 0.975,
        'Kb': 1.0,
        'p_downstream': 101325 + 5e5 # 5 barg backpressure (approx 5%)
    }
    
    result = v3.find_psv_area_by_flow_rate(inputs)
    A_req_m2, is_choked, k_val, MW_val, H_mass = result[:5]
    print(f"Area req: {A_req_m2*1e6:.2f}")
    print(f"Choked: {is_choked}")
    assert A_req_m2 > 0.0
    
    # Reaction force
    W_kg_s = inputs['W_req_kg_h'] / 3600.0
    F_N = v3.calculate_reaction_force(W_kg_s, inputs['T0_k'], inputs['p0_pa'], A_req_m2, k_val, MW_val)
    print(f"Reaction Force: {F_N:.2f} N")
    
    # Backpressure check
    bp_pct = (inputs['p_downstream'] / inputs['p0_pa']) * 100
    print(f"Backpressure Ratio: {bp_pct:.2f}%")
    assert bp_pct > 0.0
    
    # Mach Number
    import CoolProp.CoolProp as CP
    import math
    state_down = CP.AbstractState("HEOS", "Methane")
    state_down.update(CP.HmassP_INPUTS, H_mass, inputs['p_downstream'])
    rho_down = state_down.rhomass()
    c_down = state_down.speed_sound()
    
    pipe_d_mm = v3.parse_outlet_diameter_mm('DN50 x DN80')
    A_pipe_m2 = math.pi * ((pipe_d_mm / 1000.0) / 2.0)**2
    v_down = W_kg_s / (rho_down * A_pipe_m2)
    mach = v_down / c_down
    print(f"Mach Number (DN80): {mach:.3f}")
    assert F_N > 0.0
    assert mach > 0.0

    subcritical_inputs = {
        'W_req_kg_h': 1000.0,
        'p0_pa': 2.0e5,
        'T0_k': 298.15,
        'composition': comp,
        'Cd': 0.975,
        'Kb': 1.0,
        'p_downstream': 1.8e5,
    }
    A_high_bp, is_choked_high_bp, *_ = v3.find_psv_area_by_flow_rate(subcritical_inputs)
    low_bp_inputs = dict(subcritical_inputs)
    low_bp_inputs['p_downstream'] = 101325.0
    A_low_bp, is_choked_low_bp, *_ = v3.find_psv_area_by_flow_rate(low_bp_inputs)
    print(f"Area req at high backpressure: {A_high_bp*1e6:.2f}")
    print(f"Area req at atmospheric backpressure: {A_low_bp*1e6:.2f}")
    assert not is_choked_high_bp
    assert is_choked_low_bp
    assert A_high_bp > A_low_bp

    print("\nTEST COMPLETED")

if __name__ == "__main__":
    test_psv_mode()
