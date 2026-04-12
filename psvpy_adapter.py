from __future__ import annotations

from dataclasses import dataclass, field

import CoolProp.CoolProp as CP

from constants import P_ATM
from psv_preliminary import normalize_composition, relieving_pressure_from_set_pressure
from third_party import psvpy_subset as psvpy


@dataclass
class PSVPyCrosscheckResult:
    provider: str
    service_type: str
    area_mm2: float
    native_area_mm2: float
    delta_pct: float
    notes: list[str] = field(default_factory=list)


def _delta_pct(candidate_area_mm2: float, native_area_mm2: float) -> float:
    return ((candidate_area_mm2 - native_area_mm2) / max(native_area_mm2, 1e-12)) * 100.0


def _build_liquid_state(composition: dict[str, float], pressure_pa: float, temperature_k: float) -> CP.AbstractState:
    comp = normalize_composition(composition)
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    try:
        state.specify_phase(CP.iphase_liquid)
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    except Exception:
        state.unspecify_phase()
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    return state


def _build_liquid_crosscheck(inputs: dict, native_area_mm2: float) -> PSVPyCrosscheckResult:
    relieving_pressure_pa = relieving_pressure_from_set_pressure(float(inputs["set_pressure_pa"]), float(inputs.get("overpressure_pct", 10.0)))
    backpressure_pa = float(inputs.get("p_total_backpressure_pa", P_ATM))
    temperature_k = float(inputs["relieving_temperature_k"])
    state = _build_liquid_state(inputs["composition"], relieving_pressure_pa, temperature_k)
    rho_kg_m3 = state.rhomass()
    viscosity_cp = state.viscosity() * 1000.0

    if inputs.get("W_req_kg_h") not in (None, ""):
        flow_kg_h = float(inputs["W_req_kg_h"])
    elif inputs.get("Q_req_l_min") not in (None, ""):
        flow_kg_h = float(inputs["Q_req_l_min"]) / 1000.0 * rho_kg_m3 * 60.0
    else:
        raise ValueError("psvpy liquid cross-check requires W_req_kg_h or Q_req_l_min.")

    area_mm2 = psvpy.PSVliquidSize(
        flow_kg_h,
        max(relieving_pressure_pa - P_ATM, 0.0) / 1000.0,
        max(backpressure_pa - P_ATM, 0.0) / 1000.0,
        rho_kg_m3,
        viscosity_cp,
    )
    notes = [
        "psvpy liquid subset uses fixed Kd=0.65, Kw=1.0, Kc=1.0.",
    ]
    if inputs.get("Kw") not in (None, "", 1.0):
        notes.append("User/vendor Kw is ignored by the psvpy liquid cross-check.")
    if float(inputs.get("Kc", 1.0) or 1.0) != 1.0:
        notes.append("Rupture-disk Kc is ignored by the psvpy liquid cross-check.")

    return PSVPyCrosscheckResult(
        provider="psvpy subset (MIT vendored)",
        service_type="Liquid",
        area_mm2=area_mm2,
        native_area_mm2=native_area_mm2,
        delta_pct=_delta_pct(area_mm2, native_area_mm2),
        notes=notes,
    )


def _build_steam_crosscheck(inputs: dict, native_area_mm2: float) -> PSVPyCrosscheckResult:
    relieving_pressure_pa = relieving_pressure_from_set_pressure(float(inputs["set_pressure_pa"]), float(inputs.get("overpressure_pct", 10.0)))
    temperature_k = float(inputs["relieving_temperature_k"])
    tsat_k = CP.PropsSI("T", "P", relieving_pressure_pa, "Q", 1, "Water")
    state_token: float | str = "Sat" if abs(temperature_k - tsat_k) <= 1.0 else (temperature_k - 273.15)

    area_mm2 = psvpy.PSVsteamSize(
        float(inputs["W_req_kg_h"]),
        relieving_pressure_pa / 1000.0,
        state_token,
    )
    notes = [
        "psvpy steam subset uses fixed Kd=0.975, Kb=1.0, Kc=1.0.",
    ]
    if float(inputs.get("p_total_backpressure_pa", P_ATM)) > P_ATM * 1.001 or inputs.get("Kb") not in (None, ""):
        notes.append("Steam backpressure derating is ignored by the psvpy cross-check.")
    if float(inputs.get("Kc", 1.0) or 1.0) != 1.0:
        notes.append("Rupture-disk Kc is ignored by the psvpy steam cross-check.")

    return PSVPyCrosscheckResult(
        provider="psvpy subset (MIT vendored)",
        service_type="Steam",
        area_mm2=area_mm2,
        native_area_mm2=native_area_mm2,
        delta_pct=_delta_pct(area_mm2, native_area_mm2),
        notes=notes,
    )


def build_psvpy_crosscheck(*, inputs: dict, service_type: str, native_area_mm2: float) -> PSVPyCrosscheckResult:
    if service_type == "Liquid":
        return _build_liquid_crosscheck(inputs, native_area_mm2)
    if service_type == "Steam":
        return _build_steam_crosscheck(inputs, native_area_mm2)
    raise ValueError("psvpy cross-check is currently limited to Steam and Liquid service.")
