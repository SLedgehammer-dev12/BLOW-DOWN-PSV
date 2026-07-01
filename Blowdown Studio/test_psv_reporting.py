from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory

from blowdown_studio import P_ATM
from psv_preliminary import calculate_preliminary_gas_psv_area
from psv_reporting import build_psv_report_bundle, export_psv_report_csv, export_psv_report_pdf


Valve = namedtuple("Valve", ["size_in", "size_dn", "area_mm2"])


def test_psv_report_bundle_and_exports():
    inputs = {
        "composition": {"Methane": 1.0},
        "set_pressure_pa": P_ATM + 100.0e5,
        "mawp_pa": P_ATM + 100.0e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 323.15,
        "p_total_backpressure_pa": P_ATM,
        "prv_design": "Conventional",
        "W_req_kg_h": 10000.0,
        "Kd_api520": 0.975,
        "Kc": 1.0,
    }
    sizing = calculate_preliminary_gas_psv_area(inputs)
    selected_valve = Valve('3" x 4"', "DN80 x DN100", 1265.0)

    class VendorModel:
        manufacturer = "TempVendor"
        series = "TV-100"
        model_code = "TV-100-J"
        display_size = "J"
        inlet_outlet_size_in = '3" x 4"'
        inlet_outlet_size_dn = "DN80 x DN100"
        effective_area_mm2 = 830.3
        actual_area_mm2 = 950.0
        certified_kd_gas = 0.874
        trim_code = "TRIM-J"
        code_stamp = "UV/NB"
        body_material = "A216-WCB"
        trim_material = "316SS"
        inlet_rating_class = "CL300"
        outlet_rating_class = "CL150"
        source = "Unit Test"

    class VendorSelection:
        model = VendorModel()
        kb_used = 1.0
        kb_source = "Vendor Kb curve"
        required_flow_kg_h = 10000.0
        certified_capacity_kg_h = 12000.0
        effective_area_margin_pct = 10.0
        certified_capacity_margin_pct = 20.0

    bundle = build_psv_report_bundle(
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        prv_design="Conventional",
        rupture_disk="No",
        inputs=inputs,
        sizing=sizing,
        mass_flow_kg_h=inputs["W_req_kg_h"],
        volumetric_flow_m3_h=250.0,
        valve_count=1,
        required_area_mm2=sizing.A_req_mm2,
        required_area_per_valve_mm2=sizing.A_req_mm2,
        preliminary_kb_source="N/A",
        force_n=1200.0,
        force_kgf=122.3,
        mach_number=0.25,
        selected_valve=selected_valve,
        valve_data=[selected_valve],
        vendor_selection=VendorSelection(),
        vendor_evaluation=None,
        warning_lines=["screening warning"],
        reaction_discharge_area_m2=0.001,
    )

    assert "PSV ÖN BOYUTLANDIRMA VE SCREENING RAPORU" in bundle.text
    assert "Gövde malzemesi" in bundle.text
    assert "Giriş rating class" in bundle.text
    assert any(key == "Uyarı 1" for key, _ in bundle.summary_rows)

    with TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "psv_report.csv"
        pdf_path = Path(tmp_dir) / "psv_report.pdf"
        export_psv_report_csv(csv_path, bundle)
        export_psv_report_pdf(pdf_path, bundle)
        assert csv_path.exists() and csv_path.stat().st_size > 0
        assert pdf_path.exists() and pdf_path.stat().st_size > 0
