import math

def calculate_api2000_venting(tank_volume_m3, latitude, is_volatile, pump_in_m3h, pump_out_m3h, insulation_factor=1.0):
    """
    Calculates API 2000 (7th Ed) venting requirements.
    Results in Nm3/h (Standard m3/h of air).
    """
    
    # 1. Thermal Inbreathing (V_IT)
    # C-factor based on Latitude and Volatility (Simplified Table for 7th Ed)
    # Volatile: VP > 5.0 kPa or Flash Point < 37.8 C
    if latitude < 42:
        c_factor = 6.5 if is_volatile else 4.0
    elif latitude <= 58:
        c_factor = 5.0 if is_volatile else 3.0
    else:  # Above 58
        c_factor = 4.0 if is_volatile else 2.0
        
    v_it = c_factor * (tank_volume_m3 ** 0.7) * insulation_factor
    
    # 2. Thermal Outbreathing (V_OT)
    # Simplified: V_OT = 0.6 * V_IT (Non-volatile) or V_OT = V_IT (Volatile)
    v_ot = v_it if is_volatile else 0.6 * v_it
    
    # 3. Liquid Movement (Pump-in / Pump-out)
    # V_in = 1.01 * Q_in
    # V_out = 1.0 * Q_out (Non-volatile) or 2.0 * Q_out (Volatile / High Temp)
    # Note: API 2000 7th Ed uses 1.07 Nm3/h per m3/h for non-volatile, 
    # but a multiplier for volatile fluids.
    
    v_pump_in = 1.01 * pump_in_m3h
    v_pump_out = 2.0 * pump_out_m3h if is_volatile else 1.07 * pump_out_m3h
    
    # Total Requirements
    total_inbreathing = v_it + v_pump_out
    total_outbreathing = v_ot + v_pump_in
    
    return {
        'thermal_inbreathing': v_it,
        'thermal_outbreathing': v_ot,
        'pump_in_component': v_pump_in,
        'pump_out_component': v_pump_out,
        'total_inbreathing': total_inbreathing,
        'total_outbreathing': total_outbreathing,
        'c_factor_used': c_factor
    }

if __name__ == "__main__":
    # Test case: 50000 bbl ~ 7949 m3
    # Lat < 42, Volatile, C = 6.5
    # Result: 6.5 * (7949.0 ** 0.7) = 3567 Nm3/h
    res = calculate_api2000_venting(7949, 30, True, 0, 0)
    print(f"Thermal Inbreathing (Nm3/h): {res['thermal_inbreathing']:.2f}")
    
