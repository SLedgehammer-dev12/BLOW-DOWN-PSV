from types import SimpleNamespace

from vendor_final_selection import evaluate_vendor_final_selection_readiness


def test_vendor_final_selection_screening_only_for_sample():
    model = SimpleNamespace(
        manufacturer="SampleVendor",
        series="SV",
        model_code="SV-J",
        actual_area_mm2=900.0,
        certified_kd_gas=0.975,
        notes="Sample data only. Use real vendor documentation before final certified selection.",
        is_sample_data=True,
    )
    selection = SimpleNamespace(
        model=model,
        certified_capacity_kg_h=1500.0,
        kb_source="Vendor Kb curve",
        kb_used=0.97,
    )
    result = evaluate_vendor_final_selection_readiness(
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        vendor_selection=selection,
    )
    assert result.status == "SCREENING_ONLY"
    assert result.readiness_score_pct < 40.0


def test_vendor_final_selection_limited_for_real_vendor():
    model = SimpleNamespace(
        manufacturer="LESER",
        series="Type 526",
        model_code="526-J",
        actual_area_mm2=1019.4,
        certified_kd_gas=0.801,
        notes="Official catalog data.",
        is_sample_data=False,
    )
    selection = SimpleNamespace(
        model=model,
        certified_capacity_kg_h=2200.0,
        kb_source="Vendor Kb curve",
        kb_used=0.99,
    )
    result = evaluate_vendor_final_selection_readiness(
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        vendor_selection=selection,
    )
    assert result.status in {"LIMITED", "READY_FOR_VENDOR_RFQ"}
    assert result.readiness_score_pct > 0.0
    assert result.missing_items


if __name__ == "__main__":
    test_vendor_final_selection_screening_only_for_sample()
    test_vendor_final_selection_limited_for_real_vendor()
    print("TEST COMPLETED")
