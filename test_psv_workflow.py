import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import blowdown_studio as studio
from psv_vendor_catalog import load_vendor_catalog
from psv_workflow import execute_psv_workflow


def test_execute_psv_workflow_gas_vendor_screening():
    converter = studio.UnitConverter()
    composition = {"Methane": 1.0}
    inputs = {
        "composition": composition,
        "psv_service_type": "Gas/Vapor",
        "set_pressure_pa": converter.convert_pressure(100.0, "barg"),
        "mawp_pa": converter.convert_pressure(100.0, "barg"),
        "overpressure_pct": 10.0,
        "relieving_temperature_k": converter.convert_temperature(25.0, "C"),
        "p_total_backpressure_pa": converter.convert_pressure(5.0, "barg"),
        "Kd_api520": 0.975,
        "Kb": None,
        "Kw": None,
        "Kc": 1.0,
        "prv_design": "Balanced Bellows",
        "valve_count": 1,
        "valve_type": "API 526 (PSV/PRV)",
    }

    result = execute_psv_workflow(
        inputs=inputs,
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        valve_count=1,
        rupture_disk="No",
        flow_unit="kg/h",
        flow_value=10000.0,
        normalized_composition=composition,
        active_vendor_catalog=load_vendor_catalog(),
        load_api526_data=studio.load_api526_data,
        load_api6d_data=studio.load_api6d_data,
        converter=converter,
    )

    assert result.sizing.A_req_mm2 > 0.0
    assert result.inputs["W_req_kg_h"] == 10000.0
    assert result.vendor_evaluation is not None
    assert result.force_n is not None
    assert "PSV ÖN BOYUTLANDIRMA VE SCREENING RAPORU" in result.report_bundle.text


def test_execute_psv_workflow_liquid_screening():
    converter = studio.UnitConverter()
    inputs = {
        "composition": {"Water": 1.0},
        "psv_service_type": "Liquid",
        "set_pressure_pa": converter.convert_pressure(12.0, "barg"),
        "mawp_pa": converter.convert_pressure(12.0, "barg"),
        "overpressure_pct": 10.0,
        "relieving_temperature_k": converter.convert_temperature(30.0, "C"),
        "p_total_backpressure_pa": converter.convert_pressure(2.0, "barg"),
        "Kd_api520": 0.65,
        "Kb": None,
        "Kw": 0.95,
        "Kc": 1.0,
        "prv_design": "Conventional",
        "valve_count": 1,
        "valve_type": "API 526 (PSV/PRV)",
    }

    result = execute_psv_workflow(
        inputs=inputs,
        service_type="Liquid",
        valve_type="API 526 (PSV/PRV)",
        valve_count=1,
        rupture_disk="No",
        flow_unit="L/min",
        flow_value=150.0,
        normalized_composition={"Water": 1.0},
        active_vendor_catalog=load_vendor_catalog(),
        load_api526_data=studio.load_api526_data,
        load_api6d_data=studio.load_api6d_data,
        converter=converter,
    )

    assert result.sizing.A_req_mm2 > 0.0
    assert result.vendor_evaluation is None
    assert result.force_n is None
    assert "Kw kullanılan" in result.report_bundle.text


def test_execute_psv_workflow_liquid_psvpy_crosscheck():
    converter = studio.UnitConverter()
    inputs = {
        "composition": {"Water": 1.0},
        "psv_service_type": "Liquid",
        "set_pressure_pa": converter.convert_pressure(12.0, "barg"),
        "mawp_pa": converter.convert_pressure(12.0, "barg"),
        "overpressure_pct": 10.0,
        "relieving_temperature_k": converter.convert_temperature(30.0, "C"),
        "p_total_backpressure_pa": converter.convert_pressure(2.0, "barg"),
        "Kd_api520": 0.65,
        "Kb": None,
        "Kw": 0.95,
        "Kc": 1.0,
        "prv_design": "Conventional",
        "psvpy_crosscheck": True,
        "valve_count": 1,
        "valve_type": "API 526 (PSV/PRV)",
    }

    result = execute_psv_workflow(
        inputs=inputs,
        service_type="Liquid",
        valve_type="API 526 (PSV/PRV)",
        valve_count=1,
        rupture_disk="No",
        flow_unit="L/min",
        flow_value=150.0,
        normalized_composition={"Water": 1.0},
        active_vendor_catalog=load_vendor_catalog(),
        load_api526_data=studio.load_api526_data,
        load_api6d_data=studio.load_api6d_data,
        converter=converter,
    )

    assert result.psvpy_crosscheck is not None
    assert result.psvpy_crosscheck.area_mm2 > 0.0
    assert "psvpy Cross-Check" in result.report_bundle.text


def test_execute_psv_workflow_uses_valve_count_for_per_valve_selection():
    converter = studio.UnitConverter()
    composition = {"Methane": 1.0}
    inputs = {
        "composition": composition,
        "psv_service_type": "Gas/Vapor",
        "set_pressure_pa": converter.convert_pressure(100.0, "barg"),
        "mawp_pa": converter.convert_pressure(100.0, "barg"),
        "overpressure_pct": 10.0,
        "relieving_temperature_k": converter.convert_temperature(25.0, "C"),
        "p_total_backpressure_pa": converter.convert_pressure(5.0, "barg"),
        "Kd_api520": 0.975,
        "Kb": None,
        "Kw": None,
        "Kc": 1.0,
        "prv_design": "Balanced Bellows",
        "valve_count": 3,
        "valve_type": "API 526 (PSV/PRV)",
    }

    result = execute_psv_workflow(
        inputs=inputs,
        service_type="Gas/Vapor",
        valve_type="API 526 (PSV/PRV)",
        valve_count=3,
        rupture_disk="No",
        flow_unit="kg/h",
        flow_value=10000.0,
        normalized_composition=composition,
        active_vendor_catalog=load_vendor_catalog(),
        load_api526_data=studio.load_api526_data,
        load_api6d_data=studio.load_api6d_data,
        converter=converter,
    )

    assert result.valve_count == 3
    assert result.selected_valve is not None
    assert result.selected_valve.area_mm2 >= (result.sizing.A_req_mm2 / 3.0)
    assert "Vana say" in result.report_bundle.text
    assert ": 3" in result.report_bundle.text


if __name__ == "__main__":
    test_execute_psv_workflow_gas_vendor_screening()
    test_execute_psv_workflow_liquid_screening()
    test_execute_psv_workflow_uses_valve_count_for_per_valve_selection()
    print("TEST COMPLETED")
