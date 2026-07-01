import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from psv_vendor_catalog import (
    evaluate_vendor_models_for_gas_service,
    load_vendor_catalog,
    summarize_vendor_catalog,
)
from psv_preliminary import calculate_preliminary_gas_psv_area
from constants import P_ATM


def test_csv_vendor_catalog_import():
    csv_text = """manufacturer,series,model_code,design_type,orifice_letter,size_label,api526_equivalent,inlet_outlet_size_in,inlet_outlet_size_dn,effective_area_mm2,actual_area_mm2,certified_kd_gas,trim_code,set_pressure_min_pa,set_pressure_max_pa,code_stamp,body_material,trim_material,inlet_rating_class,outlet_rating_class,catalog_name,source,notes,is_sample_data
TempVendor,TV-100,TV-100-J,Conventional,J,J,J,3\" x 4\",DN80 x DN100,830.3,950.0,0.874,TRIM-J,500000,2500000,UV/NB,A216-WCB,316SS,CL300,CL150,Imported Test Catalog,Unit Test CSV,Imported from CSV,false
"""
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "vendor_import.csv"
        path.write_text(csv_text, encoding="utf-8")
        catalog = load_vendor_catalog(path)
        summary = summarize_vendor_catalog(catalog)

    assert len(catalog) == 1
    assert catalog[0].manufacturer == "TempVendor"
    assert catalog[0].trim_code == "TRIM-J"
    assert catalog[0].code_stamp == "UV/NB"
    assert catalog[0].set_pressure_min_pa == 500000.0
    assert summary["catalog_name"] == "Imported Test Catalog"
    assert summary["model_count"] == 1
    assert summary["exact_metadata_counts"]["trim_code"] == 1
    assert summary["exact_metadata_counts"]["rating_classes"] == 1


def test_csv_vendor_catalog_exact_field_filtering():
    csv_text = """manufacturer,series,model_code,design_type,orifice_letter,size_label,api526_equivalent,inlet_outlet_size_in,inlet_outlet_size_dn,effective_area_mm2,actual_area_mm2,certified_kd_gas,trim_code,set_pressure_min_pa,set_pressure_max_pa,code_stamp,body_material,trim_material,inlet_rating_class,outlet_rating_class,catalog_name,source,notes,is_sample_data
TempVendor,TV-100,TV-100-J,Conventional,J,J,J,3\" x 4\",DN80 x DN100,830.3,950.0,0.874,TRIM-J,500000,2500000,UV/NB,A216-WCB,316SS,CL300,CL150,Imported Test Catalog,Unit Test CSV,Imported from CSV,false
"""
    sizing_inputs = {
        "composition": {"Methane": 1.0},
        "set_pressure_pa": P_ATM + 10.0e5,
        "mawp_pa": P_ATM + 10.0e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 323.15,
        "p_total_backpressure_pa": P_ATM,
        "prv_design": "Conventional",
        "W_req_kg_h": 1000.0,
        "Kd_api520": 0.975,
        "Kc": 1.0,
    }
    sizing = calculate_preliminary_gas_psv_area(sizing_inputs)
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "vendor_import.csv"
        path.write_text(csv_text, encoding="utf-8")
        catalog = load_vendor_catalog(path)

    ok_eval = evaluate_vendor_models_for_gas_service(
        sizing=sizing,
        required_flow_kg_h=1000.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=sizing.Kc,
        catalog=catalog,
        set_pressure_pa=sizing_inputs["set_pressure_pa"],
        required_trim_code="TRIM-J",
        required_code_stamp="UV",
        required_body_material="A216-WCB",
        required_trim_material="316SS",
        required_inlet_rating_class="CL300",
        required_outlet_rating_class="CL150",
    )
    reject_eval = evaluate_vendor_models_for_gas_service(
        sizing=sizing,
        required_flow_kg_h=1000.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=sizing.Kc,
        catalog=catalog,
        set_pressure_pa=sizing_inputs["set_pressure_pa"],
        required_body_material="A351-CF8M",
    )
    reject_trim_eval = evaluate_vendor_models_for_gas_service(
        sizing=sizing,
        required_flow_kg_h=1000.0,
        valve_count=1,
        valve_design="Conventional",
        Kc=sizing.Kc,
        catalog=catalog,
        set_pressure_pa=sizing_inputs["set_pressure_pa"],
        required_trim_code="TRIM-K",
    )

    assert len(ok_eval.evaluated) == 1
    assert reject_eval.evaluated == []
    assert reject_trim_eval.evaluated == []


if __name__ == "__main__":
    test_csv_vendor_catalog_import()
    test_csv_vendor_catalog_exact_field_filtering()
    print("TEST COMPLETED")
