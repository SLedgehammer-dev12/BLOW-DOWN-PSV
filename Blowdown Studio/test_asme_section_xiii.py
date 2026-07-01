from types import SimpleNamespace

from asme_section_xiii import validate_section_xiii_screening


def test_section_xiii_pass_case():
    model = SimpleNamespace(
        manufacturer="TestVendor",
        series="TS-1",
        model_code="TS-1-J",
        actual_area_mm2=950.0,
        certified_kd_gas=0.875,
        source="Official vendor bulletin",
        notes="",
        is_sample_data=False,
    )
    selection = SimpleNamespace(
        model=model,
        required_flow_kg_h=1000.0,
        certified_capacity_kg_h=1250.0,
        effective_area_margin_pct=12.0,
        certified_capacity_margin_pct=25.0,
        kb_source="Vendor Kb curve",
        meets_required_effective_area=True,
        meets_required_capacity=True,
    )
    result = validate_section_xiii_screening(
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        vendor_selection=selection,
        vendor_evaluation=None,
    )
    assert result.status == "PASS"


def test_section_xiii_limited_case():
    model = SimpleNamespace(
        manufacturer="Goetze",
        series="461",
        model_code="461-DN10",
        actual_area_mm2=120.0,
        certified_kd_gas=0.820,
        source="Official datasheet",
        notes="ISO 4126 / AD2000 basis",
        is_sample_data=False,
    )
    selection = SimpleNamespace(
        model=model,
        required_flow_kg_h=100.0,
        certified_capacity_kg_h=140.0,
        effective_area_margin_pct=5.0,
        certified_capacity_margin_pct=40.0,
        kb_source="Fixed",
        meets_required_effective_area=True,
        meets_required_capacity=True,
    )
    result = validate_section_xiii_screening(
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        vendor_selection=selection,
        vendor_evaluation=None,
    )
    assert result.status == "LIMITED"


if __name__ == "__main__":
    test_section_xiii_pass_case()
    test_section_xiii_limited_case()
    print("TEST COMPLETED")
