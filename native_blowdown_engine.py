from __future__ import annotations

import math

import CoolProp.CoolProp as CP
import pandas as pd

from constants import P_ATM, R_U
from materials import carbon_steel_cp_j_kgk
from thermodynamic_utils import build_state, evaluate_phase_screening, get_h_inner, update_state_from_rho_u_gas

NATIVE_ENGINE_NAME = "Yerel Çözücü"
DCMR_ENGINE_NAME = "DCMR Rijnmond (Analitik)"


def calculate_flow_rate(
    area_m2,
    p1_pa,
    t1_k,
    k,
    z_factor,
    mw_kg_kmol,
    is_choked=True,
    p_downstream=P_ATM,
    Cd_valve=0.975,
    Kb=1.0,
):
    if is_choked:
        w_kg_s = (
            Cd_valve
            * Kb
            * area_m2
            * p1_pa
            * math.sqrt(k * mw_kg_kmol / (z_factor * R_U * t1_k))
            * (2 / (k + 1)) ** ((k + 1) / (2 * (k - 1)))
        )
    else:
        beta = p_downstream / p1_pa
        radicand = max(1e-9, beta ** (2 / k) - beta ** ((k + 1) / k))
        w_kg_s = (
            Cd_valve
            * Kb
            * area_m2
            * p1_pa
            * math.sqrt((2 * k * mw_kg_kmol) / ((k - 1) * z_factor * R_U * t1_k))
            * math.sqrt(radicand)
        )
    return w_kg_s * 3600.0


def parse_outlet_diameter_mm(size_dn_str):
    try:
        first_option = size_dn_str.split("/")[0].strip()
        outlet_part = first_option.split("x")[-1].strip()
        dn_val = "".join(filter(str.isdigit, outlet_part))
        return float(dn_val)
    except Exception:
        return 50.0


def calculate_reaction_force(W_kg_s, T1_k, p1_pa, A_exit_m2, k, MW_kg_kmol, p_exit_pa=None):
    """
    Screening-level gas reaction force.

    This helper applies a single exit-plane screening approximation:
    momentum and pressure thrust are both evaluated at the same discharge
    plane using the provided exit area and exit pressure. Exit velocity is
    derived from continuity and capped at local sonic speed for screening.
    It is useful for quick checks but is not a full API 520-2 outlet-plane
    force calculation.
    """
    if A_exit_m2 <= 0.0 or W_kg_s <= 0.0:
        return 0.0

    r_spec = R_U / MW_kg_kmol
    if p_exit_pa is None:
        p_exit_pa = P_ATM
    p_exit_pa = min(max(float(p_exit_pa), P_ATM), p1_pa)

    pressure_ratio = max(p_exit_pa / max(p1_pa, 1e-12), 1e-12)
    t_exit = max(T1_k * (pressure_ratio ** ((k - 1.0) / k)), 1.0)
    rho_exit = max(p_exit_pa / (r_spec * t_exit), 1e-12)
    a_exit = math.sqrt(max(k * r_spec * t_exit, 1e-12))
    v_exit = min(W_kg_s / (rho_exit * A_exit_m2), a_exit)

    return W_kg_s * v_exit + (p_exit_pa - P_ATM) * A_exit_m2


def run_native_blowdown_simulation(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
    """
    First-law depressuring model for the native engine.
    """
    v_sys = inputs["V_sys"]
    p_sys = inputs["p0_pa"]
    t_sys = inputs["T0_k"]
    t_wall = inputs["T0_k"]
    comp = inputs["composition"]
    target_pressure = inputs["p_target_blowdown_pa"]
    target_time = inputs["t_target_sec"]

    ht_enabled = inputs.get("HT_enabled", True)
    a_inner = inputs.get("A_inner", 1.0)
    m_steel = inputs.get("M_steel", 100.0)
    p_downstream = inputs.get("p_downstream", P_ATM)
    fire_heat_w = inputs.get("fire_heat_input_w", 0.0)
    zaman_serisi = []
    screening_warnings = []

    state = build_state(comp, p_sys, t_sys, phase=CP.iphase_gas)
    screening_state = build_state(comp)

    u_mass = state.umass()
    mw = state.molar_mass() * 1000.0
    m_fluid = state.rhomass() * v_sys

    t = 0.0
    dt = max(0.01, min(0.5, target_time / 1000.0))
    max_t = target_time * 10.0
    cd_val = inputs.get("Cd_valve", inputs.get("Cd", 0.975))
    kb_val = inputs.get("Kb", 1.0)
    p_old = p_sys
    dm_kg_s = 0.0
    h_in = 0.0

    while p_sys > target_pressure:
        if abort_flag and abort_flag.is_set():
            return None

        try:
            update_state_from_rho_u_gas(state, m_fluid / v_sys, u_mass, t_sys, context="native blowdown step")
            p_sys = state.p()
            t_sys = state.T()
            k = state.cpmass() / state.cvmass()
            z_factor = state.compressibility_factor()
            h_mass = state.hmass()
        except Exception as exc:
            raise RuntimeError(f"t={t:.2f}s anında termodinamik çözücü hatası (native blowdown).") from exc

        phase_warning = evaluate_phase_screening(screening_state, p_sys, t_sys)
        if phase_warning and phase_warning not in screening_warnings:
            screening_warnings.append(phase_warning)

        if p_sys <= target_pressure:
            break

        pr_crit = (2 / (k + 1)) ** (k / (k - 1))
        is_choked = (p_downstream / p_sys) <= pr_crit

        w_kg_h = calculate_flow_rate(
            vana_alani_m2,
            p_sys,
            t_sys,
            k,
            z_factor,
            mw,
            is_choked,
            p_downstream,
            Cd_valve=cd_val,
            Kb=kb_val,
        )
        dm_kg_s = w_kg_h / 3600.0

        if ht_enabled:
            char_length_m = max(inputs.get("D_in_m", 1.0) / 2.0, 0.01)
            h_in = get_h_inner(t_sys, t_wall, state, characteristic_length_m=char_length_m)
            q_in_conv = h_in * a_inner * (t_wall - t_sys)
            cp_steel = carbon_steel_cp_j_kgk(t_wall)
            t_wall += ((fire_heat_w - q_in_conv) * dt) / (m_steel * cp_steel)
            q_in_watts = q_in_conv
        else:
            q_in_watts = fire_heat_w
            h_in = 0.0

        old_m = m_fluid
        actual_dm = dm_kg_s * dt
        if actual_dm >= old_m:
            m_fluid = 1e-12
            t += dt
            break
        m_fluid = old_m - actual_dm
        u_mass = ((u_mass * old_m) + (q_in_watts * dt) - (h_mass * actual_dm)) / m_fluid

        d_p = abs(p_sys - p_old) / p_sys
        p_old = p_sys
        if d_p < 0.005:
            dt = min(dt * 1.2, 5.0)
        elif d_p > 0.02:
            dt = max(dt / 1.5, 0.001)

        zaman_serisi.append(
            {
                "t": t,
                "p_sys": p_sys,
                "mdot_kg_s": dm_kg_s,
                "T_sys": t_sys,
                "T_wall": t_wall,
                "h_in": h_in,
                "rho_g": state.rhomass(),
                "m_sys": m_fluid,
            }
        )

        t += dt
        if not silent and progress_callback and int(t / max(0.001, dt)) % 20 == 0:
            progress_callback(t, target_time)

        if t > max_t:
            break

    if silent:
        return t

    df = pd.DataFrame(
        zaman_serisi
        + [
            {
                "t": t,
                "p_sys": p_sys,
                "mdot_kg_s": dm_kg_s,
                "T_sys": t_sys,
                "T_wall": t_wall,
                "h_in": h_in,
                "rho_g": state.rhomass(),
                "m_sys": m_fluid,
            }
        ]
    )
    df.attrs["engine"] = NATIVE_ENGINE_NAME
    df.attrs["time_to_target"] = t
    df.attrs["warnings"] = screening_warnings
    return df


def find_native_blowdown_area(inputs, progress_callback=None, abort_flag=None):
    target_time = inputs["t_target_sec"]
    pipe_area = None
    if "D_in_m" in inputs:
        pipe_area = math.pi * (inputs["D_in_m"] / 2.0) ** 2
    a_high = min(pipe_area, 2.0) if pipe_area else 2.0
    a_low = 1e-8
    max_iter = 35

    for i in range(max_iter):
        if abort_flag and abort_flag.is_set():
            return None
        if progress_callback:
            progress_callback(i, max_iter, text=f"Boyutlandirma Analizi ({i+1}/{max_iter})...")

        a_mid = (a_low + a_high) / 2.0
        sim_time = run_native_blowdown_simulation(inputs, a_mid, silent=True, abort_flag=abort_flag)

        if sim_time is None:
            return None
        if abs(sim_time - target_time) / target_time < 0.02:
            return a_mid
        if sim_time > target_time:
            a_low = a_mid
        else:
            a_high = a_mid

    import warnings
    warnings.warn(
        f"find_native_blowdown_area: did not converge after {max_iter} iterations. "
        f"Result ~ {a_mid:.6f} m2 ({a_mid*1e6:.1f} mm2) may not meet 2% tolerance."
    )
    return a_mid


def _dcmr_gas_props(inputs):
    comp = inputs["composition"]
    p0 = inputs["p0_pa"]
    t0 = inputs["T0_k"]
    state = build_state(comp, p0, t0, phase=CP.iphase_gas)
    k = state.cpmass() / state.cvmass()
    mw = state.molar_mass() * 1000.0
    z_factor = state.compressibility_factor()
    rho0 = state.rhomass()
    return k, mw, z_factor, rho0


def _dcmr_crit_factor(k):
    return (2.0 / (k + 1.0)) ** ((k + 1.0) / (2.0 * (k - 1.0)))


def _dcmr_pressure_ratio_term(k, p0, p2):
    exponent = (k - 1.0) / (2.0 * k)
    return (p0 / p2) ** exponent - 1.0


def _dcmr_area_formula(V_sys, k, mw, z_factor, t0_k, p0, p2, t_target, Cd, Kb):
    C_crit = _dcmr_crit_factor(k)
    term1 = (2.0 * V_sys) / ((k - 1.0) * Cd * Kb * C_crit * t_target)
    term2 = _dcmr_pressure_ratio_term(k, p0, p2)
    term3 = math.sqrt(mw / (z_factor * R_U * t0_k))
    return term1 * term2 * term3


def _dcmr_time_formula(V_sys, k, mw, z_factor, t0_k, p0, p2, A, Cd, Kb):
    C_crit = _dcmr_crit_factor(k)
    term1 = (2.0 * V_sys) / ((k - 1.0) * Cd * Kb * A * C_crit)
    term2 = _dcmr_pressure_ratio_term(k, p0, p2)
    term3 = math.sqrt(mw / (z_factor * R_U * t0_k))
    return term1 * term2 * term3


def run_dcmr_blowdown_simulation(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
    """
    DCMR Rijnmond analytical blowdown: closed-form solution (no ODE).
    Assumes adiabatic isentropic expansion and continuously choked flow.

    Reference: DCMR Milieudienst Rijnmond depressurization methodology as used
    in Dutch Veiligheidsrapport (VR) applications. The closed-form expression
    should be confirmed against the applicable DCMR/VR guideline before use in
    a final submission.
    """
    del progress_callback, abort_flag

    V_sys = inputs["V_sys"]
    p0 = inputs["p0_pa"]
    t0 = inputs["T0_k"]
    p2 = inputs["p_target_blowdown_pa"]
    comp = inputs["composition"]
    cd_val = inputs.get("Cd_valve", 0.975)
    kb_val = inputs.get("Kb", 1.0)

    k, mw, Z, rho0 = _dcmr_gas_props(inputs)
    m_initial = rho0 * V_sys

    t_total = _dcmr_time_formula(V_sys, k, mw, Z, t0, p0, p2, vana_alani_m2, cd_val, kb_val)

    if silent:
        return max(t_total, 0.01)

    pr_crit = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    p_downstream = inputs.get("p_downstream", P_ATM)
    p_crit = max(p_downstream / pr_crit, p2 * 1.01)

    n_points = min(200, max(20, int(t_total / 2.0)))
    records = []
    for i in range(n_points + 1):
        frac = i / n_points
        t = frac * t_total
        p = p0 * (1.0 - frac) ** ((2.0 * k) / (k - 1.0))
        p = max(p, p2)
        p_y = (p - P_ATM) / 1e5 if p > P_ATM else 0.0
        T_y = t0 * ((p / p0) ** ((k - 1.0) / k)) if p > 1e3 else t0
        m_y = m_initial * (p / p0) ** (1.0 / k) * (t0 / T_y)

        is_choked = p >= p_crit
        if is_choked:
            flow_coeff = cd_val * kb_val * vana_alani_m2 * (2.0 / (k + 1.0)) ** ((k + 1.0) / (2.0 * (k - 1.0)))
            mdot = flow_coeff * p * math.sqrt(k * mw / (Z * R_U * T_y))
        else:
            beta = max(p_downstream / max(p, 1e-12), 1e-12)
            radicand = max(beta ** (2.0 / k) - beta ** ((k + 1.0) / k), 1e-12)
            mdot = cd_val * kb_val * vana_alani_m2 * p * math.sqrt((2.0 * k * mw) / ((k - 1.0) * Z * R_U * T_y)) * math.sqrt(radicand)

        records.append({
            "t": t,
            "p_sys": p,
            "mdot_kg_s": mdot,
            "T_sys": T_y,
            "T_wall": t0,
            "h_in": 0.0,
            "rho_g": m_y / max(V_sys, 1e-12),
            "m_sys": m_y,
        })

    df = pd.DataFrame(records)
    df.attrs["engine"] = DCMR_ENGINE_NAME
    df.attrs["time_to_target"] = t_total
    df.attrs["warnings"] = []
    return df


def find_dcmr_blowdown_area(inputs, progress_callback=None, abort_flag=None):
    """
    DCMR Rijnmond direct formula for required blowdown orifice area.
    No bisection needed — single analytical evaluation.
    """
    del progress_callback, abort_flag

    V_sys = inputs["V_sys"]
    p0 = inputs["p0_pa"]
    t0 = inputs["T0_k"]
    p2 = inputs["p_target_blowdown_pa"]
    t_target = inputs["t_target_sec"]
    cd_val = inputs.get("Cd_valve", 0.975)
    kb_val = inputs.get("Kb", 1.0)

    k, mw, Z, _ = _dcmr_gas_props(inputs)
    A = _dcmr_area_formula(V_sys, k, mw, Z, t0, p0, p2, t_target, cd_val, kb_val)

    pr_crit = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    p_downstream = inputs.get("p_downstream", P_ATM)
    if p2 / p0 > pr_crit:
        import warnings
        warnings.warn(
            "DCMR motoru: hedef basinc kritik orana yakin. "
            "Sub-sonik rejim etkili olabilir, sonuc konservatif olmayabilir. "
            "Yerel Cozucu motorunu kullanmayi degerlendirin."
        )

    return A
