from __future__ import annotations

from dataclasses import dataclass
import math

import CoolProp.CoolProp as CP

from asme_section_xiii import validate_section_xiii_screening
from constants import P_ATM
from native_blowdown_engine import calculate_reaction_force, parse_outlet_diameter_mm
from psv_preliminary import (
    calculate_preliminary_gas_psv_area,
    calculate_preliminary_liquid_psv_area,
    calculate_preliminary_steam_psv_area,
)
from psv_reporting import build_psv_report_bundle, PSVReportBundle
from psv_vendor_catalog import estimate_family_kb, evaluate_vendor_models_for_gas_service
from vendor_final_selection import evaluate_vendor_final_selection_readiness


@dataclass
class PSVWorkflowResult:
    report_bundle: PSVReportBundle
    sizing: object
    inputs: dict
    selected_valve: object | None
    valve_data: list
    vendor_selection: object | None
    vendor_evaluation: object | None
    final_selection_readiness: object | None
    force_n: float | None
    valve_count: int


def execute_psv_workflow(
    *,
    inputs: dict,
    service_type: str,
    valve_type: str,
    valve_count: int,
    rupture_disk: str,
    flow_unit: str,
    flow_value: float,
    normalized_composition: dict[str, float],
    active_vendor_catalog: list,
    load_api526_data,
    load_api6d_data,
    converter,
) -> PSVWorkflowResult:
    preliminary_kb_source = "N/A"
    preliminary_extra_warnings: list[str] = []
    family_kb = None

    if service_type == "Gas/Vapor" and "API 526" in valve_type and inputs["prv_design"] == "Balanced Bellows":
        set_pressure_gauge_pa = max(inputs["set_pressure_pa"] - P_ATM, 0.0)
        backpressure_gauge_pa = max(inputs["p_total_backpressure_pa"] - P_ATM, 0.0)
        backpressure_pct_of_set = 0.0 if set_pressure_gauge_pa <= 0.0 else (backpressure_gauge_pa / set_pressure_gauge_pa) * 100.0
        family_kb, preliminary_kb_source, family_warnings = estimate_family_kb(
            inputs["prv_design"],
            backpressure_pct_of_set,
            catalog=active_vendor_catalog,
        )
        preliminary_extra_warnings.extend(family_warnings)
        if inputs["Kb"] is None and family_kb is not None:
            inputs["Kb"] = family_kb
        elif inputs["Kb"] is not None:
            preliminary_kb_source = "Manual user input"

    flow_unit_key = flow_unit.lower().strip()
    if service_type == "Gas/Vapor":
        inputs["W_req_kg_h"] = converter.convert_flow_rate_to_kg_h(flow_value, flow_unit, normalized_composition)
        sizing = calculate_preliminary_gas_psv_area(inputs)
    elif service_type == "Steam":
        if flow_unit_key not in {"kg/h", "lb/h", "kg/s"}:
            raise ValueError("Steam service icin debi birimi kg/h, lb/h veya kg/s olmalidir.")
        inputs["W_req_kg_h"] = converter.convert_mass_flow_to_kg_h(flow_value, flow_unit)
        if inputs["Kb"] is not None:
            preliminary_kb_source = "Manual user input"
        sizing = calculate_preliminary_steam_psv_area(inputs)
    else:
        standard_valve_data = load_api526_data() if "API 526" in valve_type else load_api6d_data()
        standard_areas_mm2 = [item.area_mm2 for item in standard_valve_data]
        if flow_unit_key in {"kg/h", "lb/h", "kg/s"}:
            inputs["W_req_kg_h"] = converter.convert_mass_flow_to_kg_h(flow_value, flow_unit)
        elif flow_unit_key in {"l/min", "m3/h", "gpm"}:
            inputs["Q_req_l_min"] = converter.convert_liquid_flow_to_l_min(flow_value, flow_unit)
        else:
            raise ValueError("Liquid service icin debi birimi kg/h, lb/h, kg/s, L/min, m3/h veya gpm olmalidir.")
        if inputs["Kb"] is not None:
            preliminary_kb_source = "Manual user input"
        sizing = calculate_preliminary_liquid_psv_area(inputs, standard_orifice_areas_mm2=standard_areas_mm2)

    required_area_m2 = sizing.A_req_m2
    required_area_mm2 = sizing.A_req_mm2
    mass_flow_kg_h = inputs.get("W_req_kg_h", getattr(sizing, "W_req_kg_h", 0.0))
    rho_g = getattr(sizing, "rho_relieving_kg_m3", 0.0) or 0.0
    volumetric_flow_m3_h = (mass_flow_kg_h / rho_g) if rho_g > 0.0 and mass_flow_kg_h else None

    required_area_per_valve_m2 = required_area_m2 / valve_count
    required_area_per_valve_mm2 = required_area_mm2 / valve_count

    valve_data = load_api526_data() if "API 526" in valve_type else load_api6d_data()
    selected_valve = next((item for item in valve_data if item.area_mm2 >= required_area_per_valve_mm2), None)

    vendor_evaluation = None
    vendor_selection = None
    pipe_d_mm = 50.0
    if service_type == "Gas/Vapor" and "API 526" in valve_type:
        vendor_evaluation = evaluate_vendor_models_for_gas_service(
            sizing=sizing,
            required_flow_kg_h=inputs["W_req_kg_h"],
            valve_count=valve_count,
            valve_design=inputs["prv_design"],
            Kc=sizing.Kc,
            catalog=active_vendor_catalog,
            set_pressure_pa=inputs["set_pressure_pa"],
            required_trim_code=inputs.get("required_trim_code"),
            required_code_stamp=inputs.get("required_code_stamp"),
            required_body_material=inputs.get("required_body_material"),
            required_trim_material=inputs.get("required_trim_material"),
            required_inlet_rating_class=inputs.get("required_inlet_rating_class"),
            required_outlet_rating_class=inputs.get("required_outlet_rating_class"),
        )
        vendor_selection = vendor_evaluation.selected
        if vendor_selection is not None:
            pipe_d_mm = parse_outlet_diameter_mm(vendor_selection.model.inlet_outlet_size_dn)
        elif selected_valve:
            pipe_d_mm = parse_outlet_diameter_mm(selected_valve.size_dn)
    elif selected_valve:
        pipe_d_mm = parse_outlet_diameter_mm(selected_valve.size_dn)

    discharge_area_m2 = math.pi * ((pipe_d_mm / 1000.0) / 2.0) ** 2
    force_n = None
    force_kgf = None
    mass_flow_per_valve_kg_s = (mass_flow_kg_h / 3600.0) / valve_count if mass_flow_kg_h else 0.0
    if service_type in {"Gas/Vapor", "Steam"} and getattr(sizing, "k_real", None) and getattr(sizing, "MW_kg_kmol", None):
        force_n = calculate_reaction_force(
            mass_flow_per_valve_kg_s,
            inputs["relieving_temperature_k"],
            sizing.relieving_pressure_pa,
            discharge_area_m2,
            float(sizing.k_real),
            float(sizing.MW_kg_kmol),
            p_exit_pa=sizing.backpressure_pa,
        )
        force_kgf = force_n / 9.81

    mach_number = None
    if service_type in {"Gas/Vapor", "Steam"} and selected_valve and getattr(sizing, "h_relieving_j_kg", None) is not None:
        state_down = CP.AbstractState("HEOS", "Water" if service_type == "Steam" else "&".join(inputs["composition"].keys()))
        if service_type != "Steam":
            state_down.set_mole_fractions(list(inputs["composition"].values()))
        try:
            state_down.update(CP.HmassP_INPUTS, sizing.h_relieving_j_kg, sizing.backpressure_pa)
            rho_down = state_down.rhomass()
            c_down = state_down.speed_sound()
            v_down = mass_flow_per_valve_kg_s / max(rho_down * discharge_area_m2, 1e-12)
            mach_number = v_down / c_down
        except Exception:
            mach_number = None

    warning_lines = list(sizing.warnings)
    warning_lines.extend(preliminary_extra_warnings)
    if service_type == "Gas/Vapor" and sizing.backpressure_pct_of_set > 10.0 and inputs["prv_design"] == "Conventional":
        warning_lines.append(
            "Conventional PRV icin total backpressure, set pressure'in %10 screening seviyesini asiyor. API 520-1 ve uretici limiti ayrica dogrulanmalidir."
        )
    if service_type == "Gas/Vapor" and inputs["prv_design"] != "Balanced Bellows" and inputs.get("Kb") is not None:
        warning_lines.append(f"{inputs['prv_design']} için manuel Kb girdisi ön boyutlandırmada kullanılmadı.")
    if (
        service_type == "Gas/Vapor"
        and inputs["prv_design"] == "Balanced Bellows"
        and inputs["Kb"] is not None
        and family_kb is not None
        and abs(float(inputs["Kb"]) - family_kb) > 0.01
    ):
        warning_lines.append(
            f"Kullanici Kb={float(inputs['Kb']):.3f}; built-in vendor egrisi ayni backpressure icin Kb={family_kb:.3f} veriyor."
        )
    if service_type != "Gas/Vapor" and "API 526" in valve_type:
        warning_lines.append(
            "Vendor screening bu surumde yalniz Gas/Vapor servis icin aktif; steam/liquid tarafi alan bazli screening ile sinirlidir."
        )
    if "API 526" not in valve_type:
        warning_lines.append(
            "API 6D sonucu yalniz nominal gecis alani karsilastirmasidir; ASME/API sertifikali PSV kapasite secimi yerine kullanilamaz."
        )
    if vendor_selection is not None:
        warning_lines.extend(vendor_selection.warnings)
    elif vendor_evaluation is not None and vendor_evaluation.evaluated:
        warning_lines.append(
            "Vendor veri modeline gore hicbir PSV modeli ayni anda efektif alan ve certified-capacity sartini saglamadi."
        )

    section_xiii_validation = validate_section_xiii_screening(
        service_type=service_type,
        valve_type=valve_type,
        vendor_selection=vendor_selection,
        vendor_evaluation=vendor_evaluation,
    )
    warning_lines.extend(section_xiii_validation.warnings)
    final_selection_readiness = evaluate_vendor_final_selection_readiness(
        service_type=service_type,
        valve_type=valve_type,
        vendor_selection=vendor_selection,
        set_pressure_pa=inputs["set_pressure_pa"],
    )
    warning_lines.extend(final_selection_readiness.warnings)

    report_bundle = build_psv_report_bundle(
        service_type=service_type,
        valve_type=valve_type,
        prv_design=inputs["prv_design"],
        rupture_disk=rupture_disk,
        inputs=inputs,
        sizing=sizing,
        mass_flow_kg_h=mass_flow_kg_h,
        volumetric_flow_m3_h=volumetric_flow_m3_h,
        valve_count=valve_count,
        required_area_mm2=required_area_mm2,
        required_area_per_valve_mm2=required_area_per_valve_mm2,
        preliminary_kb_source=preliminary_kb_source,
        force_n=force_n,
        force_kgf=force_kgf,
        mach_number=mach_number,
        selected_valve=selected_valve,
        valve_data=valve_data,
        vendor_selection=vendor_selection,
        vendor_evaluation=vendor_evaluation,
        warning_lines=warning_lines,
        reaction_discharge_area_m2=discharge_area_m2,
        section_xiii_validation=section_xiii_validation,
        final_selection_readiness=final_selection_readiness,
    )

    return PSVWorkflowResult(
        report_bundle=report_bundle,
        sizing=sizing,
        inputs=inputs,
        selected_valve=selected_valve,
        valve_data=valve_data,
        vendor_selection=vendor_selection,
        vendor_evaluation=vendor_evaluation,
        final_selection_readiness=final_selection_readiness,
        force_n=force_n,
        valve_count=valve_count,
    )
