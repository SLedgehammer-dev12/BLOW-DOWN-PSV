from __future__ import annotations

import math
from typing import Callable

import CoolProp.CoolProp as CP
import numpy as np
import pandas as pd

from constants import P_ATM, R_U
from materials import carbon_steel_cp_j_kgk
from thermodynamic_utils import (
    build_state as _build_state,
    evaluate_phase_screening,
    get_h_inner as _get_h_inner,
    update_state_from_rho_u_gas as _update_state_from_rho_u_gas,
)


SEGMENTED_ENGINE_NAME = "Segmented Pipeline"


def _mass_flow_rate_kg_s(
    *,
    area_m2: float,
    p_upstream_pa: float,
    p_downstream_pa: float,
    temperature_k: float,
    k: float,
    z_factor: float,
    mw_kg_kmol: float,
    discharge_coeff: float,
) -> float:
    if p_upstream_pa <= p_downstream_pa or area_m2 <= 0.0:
        return 0.0
    critical_ratio = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    beta = p_downstream_pa / p_upstream_pa
    if beta <= critical_ratio:
        return (
            discharge_coeff
            * area_m2
            * p_upstream_pa
            * math.sqrt(k * mw_kg_kmol / (z_factor * R_U * temperature_k))
            * (2.0 / (k + 1.0)) ** ((k + 1.0) / (2.0 * (k - 1.0)))
        )
    radicand = max(1e-12, beta ** (2.0 / k) - beta ** ((k + 1.0) / k))
    return (
        discharge_coeff
        * area_m2
        * p_upstream_pa
        * math.sqrt((2.0 * k * mw_kg_kmol) / ((k - 1.0) * z_factor * R_U * temperature_k))
        * math.sqrt(radicand)
    )


def _darcy_friction_factor(reynolds_number: float, relative_roughness: float) -> float:
    if reynolds_number <= 0.0:
        return 0.02
    if reynolds_number < 2300.0:
        return 64.0 / max(reynolds_number, 1.0)
    term = (relative_roughness / 3.7) ** 1.11 + (6.9 / reynolds_number)
    return 1.0 / (-1.8 * math.log10(max(term, 1e-12))) ** 2


def _segment_pipe_mass_flow_rate_kg_s(
    *,
    area_m2: float,
    p_upstream_pa: float,
    p_downstream_pa: float,
    rho_upstream_kg_m3: float,
    rho_downstream_kg_m3: float,
    viscosity_pa_s: float,
    diameter_m: float,
    segment_length_m: float,
    discharge_coeff: float,
    roughness_mm: float,
    choked_cap_mdot_kg_s: float | None = None,
):
    if p_upstream_pa <= p_downstream_pa or area_m2 <= 0.0:
        return 0.0, 0.0, 0.0

    rho_mean = max(1e-6, 0.5 * (rho_upstream_kg_m3 + rho_downstream_kg_m3))
    dp_pa = max(p_upstream_pa - p_downstream_pa, 0.0)
    diameter_m = max(diameter_m, 1e-6)
    segment_length_m = max(segment_length_m, diameter_m)
    viscosity_pa_s = max(viscosity_pa_s, 1e-9)
    relative_roughness = max((roughness_mm * 1e-3) / diameter_m, 0.0)

    friction_factor = 0.02
    velocity_m_s = 0.0
    reynolds_number = 0.0
    for _ in range(6):
        loss_coefficient = 1.0 + friction_factor * (segment_length_m / diameter_m)
        velocity_m_s = math.sqrt(max(2.0 * dp_pa / (rho_mean * max(loss_coefficient, 1e-9)), 0.0))
        reynolds_number = rho_mean * velocity_m_s * diameter_m / viscosity_pa_s
        friction_factor = _darcy_friction_factor(reynolds_number, relative_roughness)

    mdot_kg_s = discharge_coeff * area_m2 * rho_mean * velocity_m_s
    if choked_cap_mdot_kg_s is not None:
        mdot_kg_s = min(mdot_kg_s, max(choked_cap_mdot_kg_s, 0.0))
    return mdot_kg_s, reynolds_number, friction_factor


def run_segmented_pipeline_blowdown_simulation(
    inputs,
    valve_area_m2,
    progress_callback: Callable | None = None,
    abort_flag=None,
    silent=False,
):
    """
    Screening-level segmented pipeline depressuring solver.

    Segment-to-segment transport uses a Darcy-Weisbach screening model with a
    choked-flow cap, not a full compressible Fanno solver. Use this engine for
    preliminary line-pack screening, especially on short to medium pipelines.
    """
    if "D_in_m" not in inputs or "L_m" not in inputs:
        raise ValueError("Segmented pipeline motoru icin geometrik pipeline girisleri zorunludur.")
    if "Boru" not in str(inputs.get("system_type", "Boru")):
        raise ValueError("Segmented pipeline motoru yalniz pipeline sistemi icin kullanilabilir.")

    composition = inputs["composition"]
    segment_count = int(inputs.get("segment_count", 8) or 8)
    segment_count = max(2, min(segment_count, 30))

    total_volume = inputs["V_sys"]
    total_inner_area = inputs.get("A_inner", 1.0)
    total_steel_mass = inputs.get("M_steel", 100.0)
    diameter_m = inputs["D_in_m"]
    length_m = inputs["L_m"]
    p_downstream = inputs.get("p_downstream", P_ATM)
    target_pressure = inputs["p_target_blowdown_pa"]
    target_time = inputs["t_target_sec"]
    heat_transfer_enabled = inputs.get("HT_enabled", True)
    cd_valve = inputs.get("Cd_valve", inputs.get("Cd", 0.975))
    internal_cd = float(inputs.get("segment_internal_cd", 0.90))
    roughness_mm = float(inputs.get("segment_roughness_mm", 0.045))

    cross_section_area_m2 = math.pi * (diameter_m / 2.0) ** 2
    segment_volume = total_volume / segment_count
    segment_inner_area = total_inner_area / segment_count
    segment_steel_mass = total_steel_mass / segment_count
    segment_length = length_m / segment_count

    base_state = _build_state(composition)
    base_state.specify_phase(CP.iphase_gas)
    base_state.update(CP.PT_INPUTS, inputs["p0_pa"], inputs["T0_k"])
    rho0 = base_state.rhomass()
    u0 = base_state.umass()

    masses = np.full(segment_count, rho0 * segment_volume, dtype=float)
    u_masses = np.full(segment_count, u0, dtype=float)
    gas_temperatures = np.full(segment_count, inputs["T0_k"], dtype=float)
    wall_temperatures = np.full(segment_count, inputs["T0_k"], dtype=float)

    states = [_build_state(composition) for _ in range(segment_count)]
    phase_states = [_build_state(composition) for _ in range(segment_count)]

    dt = max(0.05, min(2.0, target_time / 600.0))
    max_t = target_time * 10.0
    t = 0.0
    previous_p_max = inputs["p0_pa"]
    warnings = [
        "Segmented Pipeline screening: intersegment akis Darcy-Weisbach screening + choked-flow cap ile temsil edilir; tam Fanno / distributed momentum cozumu degildir."
    ]
    history: list[dict] = []
    last_segment_re = 0.0
    last_segment_f = 0.0

    while True:
        if abort_flag and abort_flag.is_set():
            return None

        pressures = np.zeros(segment_count)
        enthalpies = np.zeros(segment_count)
        densities = np.zeros(segment_count)
        heat_transfer_coeffs = np.zeros(segment_count)
        real_k = np.zeros(segment_count)
        viscosities = np.zeros(segment_count)
        z_factors = np.zeros(segment_count)
        mw_values = np.zeros(segment_count)

        for idx in range(segment_count):
            state = states[idx]
            try:
                _update_state_from_rho_u_gas(
                    state,
                    masses[idx] / segment_volume,
                    u_masses[idx],
                    gas_temperatures[idx],
                    context="segmented pipeline step",
                )
            except Exception as exc:
                raise RuntimeError(
                    f"t={t:.2f}s anında termodinamik çözücü hatası (segmented pipeline, segment={idx + 1})."
                ) from exc
            pressures[idx] = state.p()
            gas_temperatures[idx] = state.T()
            enthalpies[idx] = state.hmass()
            densities[idx] = state.rhomass()
            real_k[idx] = state.cpmass() / state.cvmass()
            try:
                viscosities[idx] = state.viscosity()
            except Exception:
                viscosities[idx] = 1.1e-5
            z_factors[idx] = state.compressibility_factor()
            mw_values[idx] = state.molar_mass() * 1000.0

            phase_warning = evaluate_phase_screening(
                phase_states[idx],
                pressures[idx],
                gas_temperatures[idx],
                prefix="Segmented screening",
            )
            if phase_warning and phase_warning not in warnings:
                warnings.append(phase_warning)

        p_max = float(np.max(pressures))
        p_avg = float(np.mean(pressures))
        if p_max <= target_pressure or t > max_t:
            break

        inflow_mdot = np.zeros(segment_count)
        outflow_mdot = np.zeros(segment_count)
        inflow_h = np.zeros(segment_count)
        outflow_h = np.zeros(segment_count)
        intersegment_re_values: list[float] = []
        intersegment_f_values: list[float] = []

        intersegment_area_m2 = cross_section_area_m2
        for idx in range(segment_count - 1):
            left_p = pressures[idx]
            right_p = pressures[idx + 1]
            if abs(left_p - right_p) < 1.0:
                continue
            if left_p > right_p:
                upstream = idx
                downstream = idx + 1
            else:
                upstream = idx + 1
                downstream = idx

            choked_cap_mdot = _mass_flow_rate_kg_s(
                area_m2=intersegment_area_m2,
                p_upstream_pa=pressures[upstream],
                p_downstream_pa=pressures[downstream],
                temperature_k=gas_temperatures[upstream],
                k=real_k[upstream],
                z_factor=z_factors[upstream],
                mw_kg_kmol=mw_values[upstream],
                discharge_coeff=internal_cd,
            )
            mdot, reynolds_number, friction_factor = _segment_pipe_mass_flow_rate_kg_s(
                area_m2=intersegment_area_m2,
                p_upstream_pa=pressures[upstream],
                p_downstream_pa=pressures[downstream],
                rho_upstream_kg_m3=densities[upstream],
                rho_downstream_kg_m3=densities[downstream],
                viscosity_pa_s=viscosities[upstream],
                diameter_m=diameter_m,
                segment_length_m=segment_length,
                discharge_coeff=internal_cd,
                roughness_mm=roughness_mm,
                choked_cap_mdot_kg_s=choked_cap_mdot,
            )
            if reynolds_number > 0.0:
                intersegment_re_values.append(reynolds_number)
            if friction_factor > 0.0:
                intersegment_f_values.append(friction_factor)
            mdot = min(mdot, 0.15 * masses[upstream] / max(dt, 1e-6))
            inflow_mdot[downstream] += mdot
            outflow_mdot[upstream] += mdot
            inflow_h[downstream] += mdot * enthalpies[upstream]
            outflow_h[upstream] += mdot * enthalpies[upstream]

        if intersegment_re_values:
            last_segment_re = float(np.mean(intersegment_re_values))
        if intersegment_f_values:
            last_segment_f = float(np.mean(intersegment_f_values))

        outlet_index = segment_count - 1
        outlet_mdot = _mass_flow_rate_kg_s(
            area_m2=valve_area_m2,
            p_upstream_pa=pressures[outlet_index],
            p_downstream_pa=p_downstream,
            temperature_k=gas_temperatures[outlet_index],
            k=real_k[outlet_index],
            z_factor=z_factors[outlet_index],
            mw_kg_kmol=mw_values[outlet_index],
            discharge_coeff=cd_valve,
        )
        outlet_mdot = min(outlet_mdot, 0.20 * masses[outlet_index] / max(dt, 1e-6))
        outflow_mdot[outlet_index] += outlet_mdot
        outflow_h[outlet_index] += outlet_mdot * enthalpies[outlet_index]

        q_in = np.zeros(segment_count)
        if heat_transfer_enabled:
            for idx in range(segment_count):
                try:
                    heat_transfer_coeffs[idx] = _get_h_inner(
                        gas_temperatures[idx],
                        wall_temperatures[idx],
                        states[idx],
                        characteristic_length_m=max(diameter_m / 2.0, 0.01),
                    )
                except Exception:
                    heat_transfer_coeffs[idx] = 10.0
                q_in[idx] = heat_transfer_coeffs[idx] * segment_inner_area * (wall_temperatures[idx] - gas_temperatures[idx])
                cp_steel = carbon_steel_cp_j_kgk(wall_temperatures[idx])
                wall_temperatures[idx] += (-q_in[idx] * dt) / max(segment_steel_mass * cp_steel, 1e-9)

        old_total_energy = masses * u_masses
        masses = np.maximum(1e-7, masses + (inflow_mdot - outflow_mdot) * dt)
        new_total_energy = old_total_energy + (q_in + inflow_h - outflow_h) * dt
        u_masses = new_total_energy / masses

        history.append(
            {
                "t": t,
                "p_sys": p_max,
                "p_avg": p_avg,
                "p_upstream": float(pressures[0]),
                "p_terminal": float(pressures[-1]),
                "mdot_kg_s": float(outlet_mdot),
                "T_sys": float(np.average(gas_temperatures, weights=masses)),
                "T_wall": float(np.average(wall_temperatures)),
                "h_in": float(np.average(heat_transfer_coeffs)),
                "rho_g": float(np.average(densities)),
                "m_sys": float(np.sum(masses)),
                "segment_count": float(segment_count),
                "segment_length_m": float(segment_length),
                "segment_re": float(last_segment_re),
                "segment_f": float(last_segment_f),
            }
        )

        relative_dp = abs(p_max - previous_p_max) / max(p_max, 1e-9)
        previous_p_max = p_max
        if relative_dp < 0.003:
            dt = min(dt * 1.15, 4.0)
        elif relative_dp > 0.02:
            dt = max(dt / 1.5, 0.01)

        t += dt
        if not silent and progress_callback and int(t / max(0.001, dt)) % 20 == 0:
            progress_callback(t, target_time)

    if silent:
        return t

    final_p_max = float(np.max(pressures))
    final_row = {
        "t": t,
        "p_sys": final_p_max,
        "p_avg": float(np.mean(pressures)),
        "p_upstream": float(pressures[0]),
        "p_terminal": float(pressures[-1]),
        "mdot_kg_s": float(outlet_mdot if "outlet_mdot" in locals() else 0.0),
        "T_sys": float(np.average(gas_temperatures, weights=masses)),
        "T_wall": float(np.average(wall_temperatures)),
        "h_in": float(np.average(heat_transfer_coeffs)) if "heat_transfer_coeffs" in locals() else 0.0,
        "rho_g": float(np.average(densities)),
        "m_sys": float(np.sum(masses)),
        "segment_count": float(segment_count),
        "segment_length_m": float(segment_length),
        "segment_re": float(last_segment_re),
        "segment_f": float(last_segment_f),
    }
    df = pd.DataFrame(history + [final_row])
    df.attrs["engine"] = SEGMENTED_ENGINE_NAME
    df.attrs["time_to_target"] = t
    df.attrs["warnings"] = warnings
    df.attrs["friction_model"] = "darcy_weisbach_screening_with_choked_cap"
    df.attrs["segment_roughness_mm"] = roughness_mm
    return df


def find_segmented_pipeline_blowdown_area(inputs, progress_callback=None, abort_flag=None):
    target_time = inputs["t_target_sec"]
    diameter_m = float(inputs["D_in_m"])
    pipe_area_m2 = math.pi * (diameter_m / 2.0) ** 2
    area_low = 1e-8
    area_high = max(1e-6, min(pipe_area_m2, 0.25))
    max_iter = 20
    area_mid = area_high

    for idx in range(max_iter):
        if abort_flag and abort_flag.is_set():
            return None
        if progress_callback:
            progress_callback(idx, max_iter, text=f"Segmented sizing ({idx + 1}/{max_iter})...")

        area_mid = 0.5 * (area_low + area_high)
        sim_time = run_segmented_pipeline_blowdown_simulation(
            inputs,
            area_mid,
            progress_callback=None,
            abort_flag=abort_flag,
            silent=True,
        )
        if sim_time is None:
            return None
        if abs(sim_time - target_time) / max(target_time, 1e-9) < 0.03:
            return area_mid
        if sim_time > target_time:
            area_low = area_mid
        else:
            area_high = area_mid

    return area_mid
