import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from psv_preliminary import P_ATM, calculate_preliminary_gas_psv_area, relieving_pressure_from_set_pressure, size_gas_or_vapor_area_api520
from psv_vendor_catalog import (
    build_builtin_vendor_catalog,
    default_vendor_catalog_path,
    estimate_family_kb,
    evaluate_vendor_models_for_gas_service,
    load_vendor_catalog,
    summarize_vendor_catalog,
)


PSI_TO_PA = 6894.76


def test_vendor_catalog_selection():
    print("--- PSV Vendor Catalog Tests ---")
    assert default_vendor_catalog_path().exists()

    catalog = load_vendor_catalog()
    print(f"Catalog models: {len(catalog)}")
    assert len(catalog) > 0
    assert not any(model.is_sample_data for model in catalog)

    manufacturers = {model.manufacturer for model in catalog}
    print(f"Manufacturers: {sorted(manufacturers)}")
    assert {
        "Curtiss-Wright Farris",
        "Baker Hughes Consolidated",
        "LESER",
        "Flow Safe",
        "Spirax Sarco",
        "Goetze",
    }.issubset(manufacturers)

    summary = summarize_vendor_catalog(catalog)
    assert summary["exact_metadata_counts"]["code_stamp"] >= 15
    assert summary["exact_metadata_counts"]["body_material"] >= 12
    assert summary["exact_metadata_counts"]["set_pressure_range"] >= 3

    sample_catalog = build_builtin_vendor_catalog()
    assert any(model.is_sample_data for model in sample_catalog)

    set_pressure_pa = 75.0 * PSI_TO_PA + P_ATM
    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, 10.0)
    conventional = size_gas_or_vapor_area_api520(
        W_req_kg_h=24270.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=77.2 * PSI_TO_PA,
        relieving_temperature_k=348.0,
        k_ideal=1.11,
        Z=0.90,
        MW_kg_kmol=51.0,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    conventional_eval = evaluate_vendor_models_for_gas_service(
        sizing=conventional,
        required_flow_kg_h=24270.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=1.0,
        catalog=catalog,
    )
    assert conventional_eval.selected is not None
    print(f"Selected conventional model: {conventional_eval.selected.model.manufacturer} {conventional_eval.selected.model.model_code}")
    assert conventional_eval.selected.model.actual_area_mm2 > conventional_eval.selected.model.effective_area_mm2
    assert conventional_eval.selected.meets_required_effective_area
    assert conventional_eval.selected.meets_required_capacity

    family_kb, source, warnings = estimate_family_kb("Balanced Bellows", 53.3, catalog)
    print(f"Balanced family Kb @53.3%: {family_kb}")
    assert source.startswith("Conservative vendor Kb envelope")
    assert warnings == []
    assert family_kb is not None
    assert abs(family_kb - 0.72) < 1e-9

    balanced_inputs = {
        "composition": {"Methane": 1.0},
        "set_pressure_pa": 101325.0 + 100.0 * 1e5,
        "mawp_pa": 101325.0 + 100.0 * 1e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 298.15,
        "p_total_backpressure_pa": 101325.0 + 53.3 * 1e5,
        "W_req_kg_h": 10000.0,
        "Kd": 0.975,
        "Kc": 1.0,
        "prv_design": "Balanced Bellows",
        "Kb": family_kb,
    }
    balanced = calculate_preliminary_gas_psv_area(balanced_inputs)
    balanced_eval = evaluate_vendor_models_for_gas_service(
        sizing=balanced,
        required_flow_kg_h=balanced_inputs["W_req_kg_h"],
        valve_count=1,
        valve_design="Balanced Bellows",
        Kc=1.0,
        catalog=catalog,
    )
    assert balanced_eval.selected is not None
    print(f"Selected balanced model: {balanced_eval.selected.model.manufacturer} {balanced_eval.selected.model.model_code}")
    print(f"Selected balanced Kb: {balanced_eval.selected.kb_used}")
    assert 0.6 <= balanced_eval.selected.kb_used <= 0.9
    assert balanced_eval.selected.meets_required_effective_area
    assert balanced_eval.selected.meets_required_capacity

    balanced_spring_inputs = {
        "composition": {"Methane": 1.0},
        "set_pressure_pa": 101325.0 + 80.0 * 1e5,
        "mawp_pa": 101325.0 + 80.0 * 1e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 308.15,
        "p_total_backpressure_pa": 101325.0 + 20.0 * 1e5,
        "W_req_kg_h": 3500.0,
        "Kd": 0.975,
        "Kc": 1.0,
        "prv_design": "Balanced Spring",
        "Kb": None,
    }
    balanced_spring = calculate_preliminary_gas_psv_area(balanced_spring_inputs)
    balanced_spring_eval = evaluate_vendor_models_for_gas_service(
        sizing=balanced_spring,
        required_flow_kg_h=balanced_spring_inputs["W_req_kg_h"],
        valve_count=1,
        valve_design="Balanced Spring",
        Kc=1.0,
        catalog=catalog,
    )
    assert balanced_spring_eval.selected is not None
    print(f"Selected balanced spring model: {balanced_spring_eval.selected.model.manufacturer} {balanced_spring_eval.selected.model.display_size}")
    assert balanced_spring_eval.selected.model.manufacturer == "Flow Safe"
    assert balanced_spring_eval.selected.model.display_size.startswith("-")
    assert balanced_spring_eval.selected.kb_used == 1.0
    assert balanced_spring_eval.selected.meets_required_capacity

    low_flow = size_gas_or_vapor_area_api520(
        W_req_kg_h=120.0,
        relieving_pressure_pa=relieving_pressure_from_set_pressure(6.0 * 1e5 + P_ATM, 10.0),
        backpressure_pa=P_ATM,
        relieving_temperature_k=293.15,
        k_ideal=1.30,
        Z=1.0,
        MW_kg_kmol=28.97,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    low_flow_eval = evaluate_vendor_models_for_gas_service(
        sizing=low_flow,
        required_flow_kg_h=120.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=1.0,
        catalog=catalog,
    )
    assert low_flow_eval.selected is not None
    print(f"Selected low-flow model: {low_flow_eval.selected.model.manufacturer} {low_flow_eval.selected.model.model_code}")
    assert low_flow_eval.selected.model.manufacturer in {"Goetze", "Spirax Sarco"}

    low_flow_uv_eval = evaluate_vendor_models_for_gas_service(
        sizing=low_flow,
        required_flow_kg_h=120.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=1.0,
        catalog=catalog,
        required_code_stamp="UV",
    )
    assert low_flow_uv_eval.selected is not None
    assert low_flow_uv_eval.selected.model.manufacturer == "Spirax Sarco"

    higher_pressure_low_flow = size_gas_or_vapor_area_api520(
        W_req_kg_h=120.0,
        relieving_pressure_pa=relieving_pressure_from_set_pressure(30.0 * 1e5 + P_ATM, 10.0),
        backpressure_pa=P_ATM,
        relieving_temperature_k=293.15,
        k_ideal=1.30,
        Z=1.0,
        MW_kg_kmol=28.97,
        valve_design="Conventional",
        Kd=0.975,
        Kc=1.0,
    )
    higher_pressure_uv_eval = evaluate_vendor_models_for_gas_service(
        sizing=higher_pressure_low_flow,
        required_flow_kg_h=120.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=1.0,
        catalog=catalog,
        set_pressure_pa=30.0 * 1e5 + P_ATM,
        required_code_stamp="UV",
    )
    assert higher_pressure_uv_eval.selected is not None
    assert higher_pressure_uv_eval.selected.model.manufacturer == "Spirax Sarco"
    assert higher_pressure_uv_eval.selected.model.series == "SV418 Series"

    print("TEST COMPLETED")


if __name__ == "__main__":
    test_vendor_catalog_selection()
