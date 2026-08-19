from constants import API2000_EDITION, P_ATM, R_U

# API 2000 fire-exposure wetted-area elevation limit (30 ft).
WETTED_AREA_HEIGHT_LIMIT_M = 9.14


def calculate_api2000_venting(tank_volume_m3, latitude, is_volatile, pump_in_m3h, pump_out_m3h, insulation_factor=1.0):
    """
    Calculates API 2000 (7th Ed) normal venting requirements.

    Results in Nm3/h (Standard m3/h of air).

    The thermal inbreathing/outbreathing uses a simplified latitude-band
    C-factor (V**0.7 scaling); liquid-movement components follow the 7th
    edition Table 2 factors (0.94 / 1.01 / 2.02 Nm3/h per m3/h).
    """

    # 1. Thermal Inbreathing (V_IT)
    # C-factor based on Latitude and Volatility (simplified screening table).
    # Volatile: VP > 5.0 kPa or Flash Point < 37.8 C.
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

    # 3. Liquid Movement (Pump-in / Pump-out) per API 2000 7th ed. Table 2:
    #    - Outbreathing (pump-in):  1.01 Nm3/h per m3/h (non-volatile), 2.02 (volatile)
    #    - Inbreathing (pump-out):  0.94 Nm3/h per m3/h (non-volatile), 2.02 (volatile)
    pump_in_factor = 2.02 if is_volatile else 1.01
    pump_out_factor = 2.02 if is_volatile else 0.94

    v_pump_in = pump_in_factor * pump_in_m3h
    v_pump_out = pump_out_factor * pump_out_m3h

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
        'c_factor_used': c_factor,
        'standard_edition': API2000_EDITION,
    }


def calculate_api2000_emergency_venting(
    wetted_area_m2,
    latent_heat_kj_kg,
    vapor_mw_kg_kmol,
    fire_factor=1.0,
    drainage_condition="Adequate drainage + firefighting",
):
    """
    Screening-level emergency venting estimate for tank fire exposure.

    Heat input follows the same SI pool-fire scaling used elsewhere in the app.
    Vapor generation is estimated from latent heat, then converted to Nm3/h.

    The wetted area supplied by the caller should be limited to the exposed
    surface up to 9.14 m (30 ft) elevation per API 2000 / API 521 fire-exposure
    rules; this function does not compute the wetted area from tank geometry.
    """
    if wetted_area_m2 <= 0.0:
        raise ValueError("Emergency wetted area positive olmalidir.")
    if latent_heat_kj_kg <= 0.0:
        raise ValueError("Latent heat positive olmalidir.")
    if vapor_mw_kg_kmol <= 0.0:
        raise ValueError("Vapor molecular weight positive olmalidir.")
    if fire_factor <= 0.0:
        raise ValueError("Fire factor positive olmalidir.")

    coeff_si = 43200.0 if "Adequate" in drainage_condition else 70900.0
    heat_input_w = coeff_si * fire_factor * (wetted_area_m2 ** 0.82)
    vapor_generation_kg_h = heat_input_w * 3600.0 / (latent_heat_kj_kg * 1000.0)
    normal_m3_h = vapor_generation_kg_h * R_U * 273.15 / (max(vapor_mw_kg_kmol, 1e-12) * P_ATM)

    return {
        "heat_input_w": heat_input_w,
        "vapor_generation_kg_h": vapor_generation_kg_h,
        "emergency_venting_nm3_h": normal_m3_h,
        "wetted_area_m2": wetted_area_m2,
        "latent_heat_kj_kg": latent_heat_kj_kg,
        "vapor_mw_kg_kmol": vapor_mw_kg_kmol,
        "fire_factor": fire_factor,
        "drainage_condition": drainage_condition,
        "method_note": (
            "Screening-level emergency venting estimate based on pool-fire heat input and latent-heat vaporization; "
            "final API 2000 emergency vent design still requires service-specific validation."
        ),
    }

if __name__ == "__main__":
    # Test case: 50000 bbl ~ 7949 m3
    # Lat < 42, Volatile, C = 6.5
    # Result: 6.5 * (7949.0 ** 0.7) = 3567 Nm3/h
    res = calculate_api2000_venting(7949, 30, True, 0, 0)
    print(f"Thermal Inbreathing (Nm3/h): {res['thermal_inbreathing']:.2f}")

