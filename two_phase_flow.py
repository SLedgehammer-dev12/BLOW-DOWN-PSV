"""
Screening-level two-phase blowdown utilities.

This module does not claim full API 520/521 two-phase compliance. It provides a
compile-safe, testable homogeneous-equilibrium-style screening workflow that can
be used for preliminary engineering checks and for future UI integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Dict, Optional

import CoolProp.CoolProp as CP
import numpy as np
import pandas as pd

from constants import P_ATM, R_U
from thermodynamic_utils import (
    build_state as _build_state,
    get_h_inner as _get_h_inner,
    update_state_from_rho_u_gas as _update_state_from_rho_u_gas,
)


@dataclass(frozen=True)
class TwoPhaseResult:
    quality: float
    mixture_density: float
    vapor_density: float
    liquid_density: float
    mixture_enthalpy: float
    mixture_specific_volume: float
    flow_regime: str
    phase_label: str

    def to_dict(self) -> Dict[str, float | str]:
        return asdict(self)


def _normalize_composition(components: Optional[list[str] | Dict[str, float]]) -> Dict[str, float]:
    if components is None:
        return {"Methane": 1.0}
    if isinstance(components, dict):
        total = sum(float(v) for v in components.values())
        if total <= 0.0:
            raise ValueError("Kompozisyon toplamı sıfır veya negatif olamaz.")
        return {str(k): float(v) / total for k, v in components.items()}
    if len(components) == 1:
        return {str(components[0]): 1.0}
    raise ValueError(
        "Çok bileşenli iki-faz screening için `components` parametresi dict olarak verilmelidir "
        "(ör. {'Methane': 0.95, 'Ethane': 0.05})."
    )


def _phase_label(phase_code: int) -> str:
    mapping = {
        CP.iphase_gas: "gas",
        CP.iphase_supercritical_gas: "supercritical_gas",
        CP.iphase_liquid: "liquid",
        CP.iphase_supercritical_liquid: "supercritical_liquid",
        CP.iphase_supercritical: "supercritical",
        CP.iphase_twophase: "two_phase",
        CP.iphase_critical_point: "critical_point",
    }
    return mapping.get(phase_code, f"phase_{phase_code}")


def _safe_quality(state: CP.AbstractState) -> float | None:
    try:
        q = float(state.Q())
    except Exception:
        return None
    if 0.0 <= q <= 1.0:
        return q
    return None


def _forced_density(composition: Dict[str, float], pressure_pa: float, temperature_k: float, phase: int) -> float | None:
    try:
        state = _build_state(composition)
        state.specify_phase(phase)
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
        return state.rhomass()
    except Exception:
        return None


def determine_flow_regime(
    quality: float,
    mixture_density: float,
    vapor_density: float,
    liquid_density: float,
    velocity_m_s: float,
) -> str:
    quality = min(max(float(quality), 0.0), 1.0)
    if quality >= 0.98:
        return "Gas"
    if quality <= 0.02:
        return "Liquid"

    rho_v = max(vapor_density, 1e-9)
    rho_l = max(liquid_density, rho_v * 1.01)
    alpha = 1.0 / (1.0 + ((1.0 - quality) / max(quality, 1e-9)) * (rho_v / rho_l))

    if alpha < 0.25:
        return "Bubbly"
    if alpha < 0.75:
        return "Churn/Slug"
    if velocity_m_s > 30.0:
        return "Annular/Mist"
    return "Intermittent"


def calculate_mixture_properties(
    gas_mole_fraction: float,
    liquid_mole_fraction: float,
    pressure_pa: float,
    temperature_k: float,
    components: Optional[list[str] | Dict[str, float]] = None,
) -> Dict:
    del gas_mole_fraction, liquid_mole_fraction  # legacy placeholders

    composition = _normalize_composition(components)
    state = _build_state(composition)
    state.unspecify_phase()
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)

    phase_code = state.phase()
    phase = _phase_label(phase_code)
    rho_mix = state.rhomass()
    h_mix = state.hmass()
    quality = _safe_quality(state)

    if quality is None:
        if phase in {"gas", "supercritical_gas", "supercritical", "critical_point"}:
            quality = 1.0
        elif phase in {"liquid", "supercritical_liquid"}:
            quality = 0.0
        else:
            quality = 0.5

    rho_v = None
    rho_l = None
    if phase == "two_phase":
        try:
            rho_l = state.saturated_liquid_keyed_output(CP.iDmass)
            rho_v = state.saturated_vapor_keyed_output(CP.iDmass)
        except Exception:
            rho_l = None
            rho_v = None

    if rho_v is None:
        rho_v = _forced_density(composition, pressure_pa, temperature_k, CP.iphase_gas)
    if rho_l is None:
        rho_l = _forced_density(composition, pressure_pa, temperature_k, CP.iphase_liquid)

    if rho_v is None:
        rho_v = max(rho_mix * max(quality, 0.05), 1e-6)
    if rho_l is None:
        rho_l = max(rho_mix / max(1.0 - quality, 0.05), rho_v * 1.5)

    result = TwoPhaseResult(
        quality=min(max(quality, 0.0), 1.0),
        mixture_density=rho_mix,
        vapor_density=max(rho_v, 1e-9),
        liquid_density=max(rho_l, max(rho_v, 1e-9) * 1.01),
        mixture_enthalpy=h_mix,
        mixture_specific_volume=1.0 / max(rho_mix, 1e-12),
        flow_regime=determine_flow_regime(
            quality=min(max(quality, 0.0), 1.0),
            mixture_density=rho_mix,
            vapor_density=max(rho_v, 1e-9),
            liquid_density=max(rho_l, max(rho_v, 1e-9) * 1.01),
            velocity_m_s=0.0,
        ),
        phase_label=phase,
    )
    return result.to_dict()


def calculate_two_phase_mass_flow(
    area_m2: float,
    pressure_pa: float,
    temperature_k: float,
    quality: float,
    k_vapor: float,
    k_liquid: float,
    Z_mixture: float,
    MW_mixture: float,
    Cd: float = 0.975,
    discharge_K: float = 0.5,
) -> float:
    if area_m2 <= 0.0:
        raise ValueError("Alan pozitif olmalıdır.")
    if pressure_pa <= P_ATM:
        return 0.0

    quality = min(max(float(quality), 0.0), 1.0)
    k_eff = max(1.01, quality * max(k_vapor, 1.01) + (1.0 - quality) * max(k_liquid, 1.01))
    z_eff = max(float(Z_mixture), 0.05)
    mw_eff = max(float(MW_mixture), 1e-6)

    rho_pseudo = pressure_pa * mw_eff / (z_eff * R_U * max(temperature_k, 1.0))
    rho_hem = rho_pseudo / max(0.15, 0.15 + quality)

    delta_p = max(pressure_pa - P_ATM, 0.0) / max(1.0 + discharge_K, 1.0)
    mdot_dp = Cd * area_m2 * math.sqrt(max(2.0 * rho_hem * delta_p, 0.0))

    c_pseudo = math.sqrt(k_eff * R_U * temperature_k / mw_eff / z_eff)
    mdot_choked = Cd * area_m2 * rho_hem * c_pseudo

    return min(mdot_dp, mdot_choked)


def _safe_speed_of_sound(state: CP.AbstractState, pressure_pa: float, temperature_k: float, mw_kg_kmol: float) -> float:
    try:
        return max(state.speed_sound(), 5.0)
    except Exception:
        k_real = max(state.cpmass() / max(state.cvmass(), 1e-9), 1.01)
        r_spec = R_U / max(mw_kg_kmol, 1e-9)
        return max(math.sqrt(k_real * r_spec * max(temperature_k, 1.0)), 5.0)


def _update_state_from_rho_u(
    state: CP.AbstractState,
    composition: Dict[str, float],
    rho_kg_m3: float,
    u_target_j_kg: float,
    t_guess_k: float,
) -> tuple[CP.AbstractState, list[str]]:
    warnings: list[str] = []
    try:
        state.unspecify_phase()
        state.update(CP.DmassUmass_INPUTS, max(rho_kg_m3, 1e-9), u_target_j_kg)
        return state, warnings
    except Exception:
        if len(composition) == 1:
            warnings.append("Pure-fluid rho-u flash başarısız; gas-phase fallback kullanıldı.")
        else:
            warnings.append("Multicomponent two-phase rho-u flash desteklenmedi; gas-phase screening fallback kullanıldı.")
        state = _update_state_from_rho_u_gas(
            state,
            rho_kg_m3,
            u_target_j_kg,
            t_guess_k,
            context="two-phase screening fallback",
        )
        return state, warnings


def run_two_phase_blowdown_simulation(
    inputs: Dict,
    area_m2: float,
    discharge_K: float = 0.5,
    progress_callback=None,
    abort_flag=None,
    silent: bool = False,
):
    composition = _normalize_composition(inputs.get("composition"))
    V_sys = float(inputs["V_sys"])
    p_sys = float(inputs["p0_pa"])
    T_sys = float(inputs["T0_k"])
    T_wall = float(inputs.get("T_wall0_k", T_sys))
    target_pressure = float(inputs["p_target_blowdown_pa"])
    target_time = float(inputs["t_target_sec"])
    p_downstream = float(inputs.get("p_downstream", P_ATM))
    Cd_valve = float(inputs.get("Cd_valve", inputs.get("Cd", 0.975)))
    A_inner = float(inputs.get("A_inner", 1.0))
    M_steel = float(inputs.get("M_steel", 100.0))
    Cp_steel = float(inputs.get("Cp_steel", 480.0))
    HT_enabled = bool(inputs.get("HT_enabled", True))
    char_length_m = max(float(inputs.get("D_in_m", 1.0)) / 2.0, 0.01)

    state = _build_state(composition)
    state.unspecify_phase()
    state.update(CP.PT_INPUTS, p_sys, T_sys)

    U_mass = state.umass()
    m_fluid = state.rhomass() * V_sys
    MW_kg_kmol = state.molar_mass() * 1000.0

    time_rows = []
    warnings: list[str] = []
    t = 0.0
    dt = max(0.01, min(0.5, target_time / 1000.0))
    max_t = target_time * 10.0
    p_old = p_sys

    while p_sys > target_pressure and t <= max_t:
        if abort_flag and abort_flag.is_set():
            return None

        state, state_warnings = _update_state_from_rho_u(state, composition, m_fluid / V_sys, U_mass, T_sys)
        for item in state_warnings:
            if item not in warnings:
                warnings.append(item)

        p_sys = state.p()
        T_sys = state.T()
        rho_mix = state.rhomass()
        h_mass = state.hmass()
        k_real = max(state.cpmass() / max(state.cvmass(), 1e-9), 1.01)

        props = calculate_mixture_properties(
            gas_mole_fraction=1.0,
            liquid_mole_fraction=0.0,
            pressure_pa=p_sys,
            temperature_k=T_sys,
            components=composition,
        )

        if p_sys <= target_pressure:
            break

        dp = max(p_sys - p_downstream, 0.0)
        c_sound = _safe_speed_of_sound(state, p_sys, T_sys, MW_kg_kmol)
        mdot_choked = Cd_valve * area_m2 * rho_mix * c_sound
        mdot_dp = Cd_valve * area_m2 * math.sqrt(max(2.0 * rho_mix * dp / max(1.0 + discharge_K, 1.0), 0.0))
        dm_kg_s = min(mdot_choked, mdot_dp)

        if HT_enabled:
            h_in = _get_h_inner(T_sys, T_wall, state, char_length_m)
            Q_in_watts = h_in * A_inner * (T_wall - T_sys)
            T_wall += (-Q_in_watts * dt) / max(M_steel * Cp_steel, 1e-9)
        else:
            h_in = 0.0
            Q_in_watts = 0.0

        old_m = m_fluid
        m_fluid = max(1e-7, m_fluid - dm_kg_s * dt)
        U_mass = ((U_mass * old_m) + (Q_in_watts * dt) - (h_mass * (old_m - m_fluid))) / m_fluid

        velocity = dm_kg_s / max(rho_mix * area_m2, 1e-12)
        flow_regime = determine_flow_regime(
            quality=float(props["quality"]),
            mixture_density=float(props["mixture_density"]),
            vapor_density=float(props["vapor_density"]),
            liquid_density=float(props["liquid_density"]),
            velocity_m_s=velocity,
        )

        dP_rel = abs(p_sys - p_old) / max(p_sys, 1e-9)
        p_old = p_sys
        if dP_rel < 0.005:
            dt = min(dt * 1.2, 5.0)
        elif dP_rel > 0.02:
            dt = max(dt / 1.5, 0.001)

        time_rows.append(
            {
                "t": t,
                "p_sys": p_sys,
                "mdot_kg_s": dm_kg_s,
                "T_sys": T_sys,
                "T_wall": T_wall,
                "h_in": h_in,
                "rho_g": rho_mix,
                "m_sys": m_fluid,
                "quality": float(props["quality"]),
                "flow_regime": flow_regime,
            }
        )

        t += dt
        if not silent and progress_callback and int(t / max(0.001, dt)) % 20 == 0:
            progress_callback(t, target_time)

    if not time_rows:
        raise RuntimeError("Two-phase screening simülasyonu herhangi bir zaman adımı üretemedi.")

    if silent:
        return float(time_rows[-1]["t"])

    df = pd.DataFrame(time_rows)
    df.attrs["engine"] = "Two-Phase HEM Screening"
    df.attrs["time_to_target"] = float(df["t"].iloc[-1])
    df.attrs["warnings"] = warnings
    return df


def _safe_two_phase_time(inputs: Dict, area_m2: float, abort_flag=None) -> float | None:
    try:
        return run_two_phase_blowdown_simulation(inputs, area_m2, abort_flag=abort_flag, silent=True)
    except Exception:
        return None


def find_two_phase_blowdown_area(inputs: Dict, progress_callback=None, abort_flag=None) -> float | None:
    target_time = float(inputs["t_target_sec"])
    area_low_m2 = 1e-8
    pipe_area_m2 = math.pi * max(float(inputs.get("D_in_m", 0.25)) ** 2, 1e-6) / 4.0
    area_high_m2 = max(1e-6, min(1e-3, pipe_area_m2))
    max_area_m2 = max(area_high_m2, pipe_area_m2)
    max_iter = 30
    area_mid_m2 = area_high_m2

    sim_time_high = _safe_two_phase_time(inputs, area_high_m2, abort_flag=abort_flag)
    expand_iter = 0
    while sim_time_high is not None and sim_time_high > target_time and area_high_m2 < max_area_m2:
        area_low_m2 = area_high_m2
        area_high_m2 = min(max_area_m2, area_high_m2 * 2.0)
        sim_time_high = _safe_two_phase_time(inputs, area_high_m2, abort_flag=abort_flag)
        expand_iter += 1
        if expand_iter > 20:
            break

    for i in range(max_iter):
        if abort_flag and abort_flag.is_set():
            return None
        if progress_callback:
            progress_callback(i, max_iter, text=f"Two-Phase boyutlandırma ({i+1}/{max_iter})...")

        area_mid_m2 = 0.5 * (area_low_m2 + area_high_m2)
        sim_time = _safe_two_phase_time(inputs, area_mid_m2, abort_flag=abort_flag)
        if sim_time is None:
            area_high_m2 = area_mid_m2
            continue
        if abs(sim_time - target_time) / max(target_time, 1e-9) < 0.02:
            return area_mid_m2
        if sim_time > target_time:
            area_low_m2 = area_mid_m2
        else:
            area_high_m2 = area_mid_m2

    return area_mid_m2
