from __future__ import annotations

from typing import Mapping

import CoolProp.CoolProp as CP


def normalize_composition(composition: Mapping[str, float]) -> dict[str, float]:
    total = sum(float(v) for v in composition.values())
    if total <= 0.0:
        raise ValueError("Kompozisyon toplami sifir veya negatif olamaz.")
    return {str(k): float(v) / total for k, v in composition.items()}


def build_state(
    composition: Mapping[str, float],
    pressure_pa: float | None = None,
    temperature_k: float | None = None,
    phase: int | None = None,
) -> CP.AbstractState:
    comp = normalize_composition(composition)
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    if phase is not None:
        state.specify_phase(phase)
    if pressure_pa is not None and temperature_k is not None:
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    return state


def update_state_from_rho_u_gas(
    state: CP.AbstractState,
    rho_kg_m3: float,
    u_target_j_kg: float,
    t_guess_k: float,
    context: str = "blowdown step",
) -> CP.AbstractState:
    """
    Approximate mixture rho-u flash with a bounded rho-T bisection in forced gas phase.
    """
    rho_kg_m3 = max(rho_kg_m3, 1e-9)
    t_guess_k = max(t_guess_k, 80.0)
    state.specify_phase(CP.iphase_gas)

    def eval_u(temp_k: float) -> float:
        state.update(CP.DmassT_INPUTS, rho_kg_m3, temp_k)
        return state.umass()

    def try_eval(temp_k: float) -> float | None:
        try:
            return eval_u(temp_k)
        except Exception:
            return None

    candidate_temps = sorted(
        {
            max(80.0, min(t_guess_k * 0.5, t_guess_k - 100.0)),
            max(90.0, t_guess_k * 0.6),
            max(120.0, t_guess_k * 0.8),
            max(150.0, t_guess_k),
            max(220.0, t_guess_k * 1.15),
            max(350.0, t_guess_k + 100.0, t_guess_k * 1.5),
            max(500.0, t_guess_k * 1.8),
            800.0,
            1200.0,
            1800.0,
        }
    )

    valid_points: list[tuple[float, float]] = []
    for temp_k in candidate_temps:
        u_val = try_eval(temp_k)
        if u_val is not None:
            valid_points.append((temp_k, u_val))

    if len(valid_points) < 2:
        raise ValueError(f"Unable to bracket rho-u gas state for {context}.")

    t_low = valid_points[0][0]
    u_low = valid_points[0][1]
    t_high = valid_points[-1][0]
    u_high = valid_points[-1][1]
    bracket_found = False
    for left, right in zip(valid_points, valid_points[1:]):
        if left[1] <= u_target_j_kg <= right[1]:
            t_low, u_low = left
            t_high, u_high = right
            bracket_found = True
            break

    if not bracket_found:
        for _ in range(20):
            if u_low <= u_target_j_kg <= u_high:
                bracket_found = True
                break
            if u_target_j_kg > u_high:
                next_high = t_high * 1.2
                u_next = try_eval(next_high)
                if u_next is None:
                    break
                t_high, u_high = next_high, u_next
            else:
                next_low = max(80.0, t_low * 0.9)
                if next_low == t_low:
                    break
                u_next = try_eval(next_low)
                if u_next is None:
                    t_low = max(80.0, min(t_low, t_low + 5.0))
                    break
                t_low, u_low = next_low, u_next

    if not bracket_found and not (u_low <= u_target_j_kg <= u_high):
        raise ValueError(f"Unable to bracket rho-u gas state for {context}.")

    for _ in range(60):
        t_mid = 0.5 * (t_low + t_high)
        try:
            u_mid = eval_u(t_mid)
        except Exception:
            t_low = t_mid
            continue
        if abs(u_mid - u_target_j_kg) <= 1e-6 * max(1.0, abs(u_target_j_kg)):
            break
        if u_mid < u_target_j_kg:
            t_low = t_mid
        else:
            t_high = t_mid

    state.update(CP.DmassT_INPUTS, rho_kg_m3, 0.5 * (t_low + t_high))
    return state


def get_h_inner(
    T_gas: float,
    T_wall: float,
    state: CP.AbstractState,
    characteristic_length_m: float = 1.0,
) -> float:
    """
    Screening-level internal free convection coefficient based on Ra/Pr/Nu.
    """
    try:
        cond = state.conductivity()
        visc = state.viscosity()
        cp = state.cpmass()
        rho = state.rhomass()
        pr = cp * visc / max(cond, 1e-12)
        beta = max(state.isobaric_expansion_coefficient(), 1e-12)
        nu = visc / max(rho, 1e-12)
        l_char = max(characteristic_length_m, 0.01)
        d_t = max(abs(T_wall - T_gas), 0.1)
        gr = 9.81 * beta * d_t * (l_char ** 3) / max(nu ** 2, 1e-18)
        ra = pr * gr
        if ra >= 1e9:
            nu_number = 0.13 * (ra ** 0.333)
        elif ra > 1e4:
            nu_number = 0.59 * (ra ** 0.25)
        else:
            nu_number = 1.36 * (ra ** 0.20)
        return min(max(nu_number * cond / l_char, 2.0), 300.0)
    except Exception:
        return 10.0


def evaluate_phase_screening(
    state_no_phase: CP.AbstractState,
    pressure_pa: float,
    temperature_k: float,
    prefix: str = "Phase screening",
) -> str | None:
    """
    PT-based phase-boundary warning for screening use only.
    """
    try:
        state_no_phase.unspecify_phase()
        state_no_phase.update(CP.PT_INPUTS, pressure_pa, temperature_k)
        phase = state_no_phase.phase()
        gas_like_phases = {
            CP.iphase_gas,
            CP.iphase_supercritical,
            CP.iphase_supercritical_gas,
            CP.iphase_critical_point,
        }
        if phase not in gas_like_phases:
            return (
                f"{prefix}: akiskan t={temperature_k - 273.15:.2f} C ve "
                f"p={pressure_pa / 1e5:.2f} bara kosullarinda gaz-faz disina cikiyor olabilir."
            )
    except Exception:
        return (
            f"{prefix}: t={temperature_k - 273.15:.2f} C ve "
            f"p={pressure_pa / 1e5:.2f} bara noktasinda PT flash kararsiz; faz sinirina yaklasilmis olabilir."
        )
    return None
