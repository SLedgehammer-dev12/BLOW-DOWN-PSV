"""
Regression and refinement tests for engineering-correctness fixes.

Covers the API 520-1 liquid viscosity correction, API 526 data single-sourcing,
native blowdown edge cases, DCMR closed-form consistency, API 2000 liquid
movement factors, vendor catalog schema validation and PSV report unit
formatting.
"""

import math
import os
import sys
from collections import namedtuple

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api2000_engine import calculate_api2000_venting
from constants import P_ATM
from native_blowdown_engine import find_dcmr_blowdown_area, run_dcmr_blowdown_simulation, run_native_blowdown_simulation
from psv_preliminary import (
    liquid_reynolds_number,
    liquid_viscosity_correction_kv,
    size_liquid_area_api520,
)
from psv_vendor_catalog import validate_vendor_records
from valve_catalog_data import api526_effective_orifices, load_api526_data, load_api6d_data


# --- API 520-1 liquid viscosity correction (Figure 34) ----------------------

def test_liquid_viscosity_correction_is_monotonic_and_bounded():
    for reynolds, expected in ((10, 0.45), (100, 0.70), (1000, 0.90), (100000, 1.0)):
        kv = liquid_viscosity_correction_kv(reynolds)
        assert 0.0 < kv <= 1.0
        assert kv == expected, f"Re={reynolds} -> Kv={kv}, expected {expected}"
    # Monotonic increasing in Reynolds.
    previous = 0.0
    for reynolds in (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000):
        kv = liquid_viscosity_correction_kv(reynolds)
        assert kv >= previous
        previous = kv


def test_liquid_reynolds_number_units():
    # Hand-check: R = 18800 * Q_gpm * G / (mu_cP * sqrt(A_in2)).
    Q_gpm = 100.0 / 3.785411784
    A_in2 = 500.0 / 645.16
    expected = 18800.0 * Q_gpm * 0.9 / (50.0 * math.sqrt(A_in2))
    actual = liquid_reynolds_number(100.0, 0.9, 50.0, 500.0)
    assert abs(actual - expected) < 1e-6


def test_liquid_sizing_applies_viscosity_correction_when_re_below_100():
    result = size_liquid_area_api520(
        Q_req_l_min=10.0,
        relieving_pressure_pa=P_ATM + 10e5,
        backpressure_pa=P_ATM,
        specific_gravity=0.90,
        viscosity_cp=8000.0,
        valve_design="Conventional",
        Kd=0.65,
        Kc=1.0,
    )
    assert result.reynolds is not None and result.reynolds < 100.0
    assert result.Kv_used < 1.0
    assert result.A_req_mm2 > 0.0


def test_liquid_sizing_no_correction_at_high_re():
    result = size_liquid_area_api520(
        Q_req_l_min=6814.0,
        relieving_pressure_pa=P_ATM + 1896e3,
        backpressure_pa=P_ATM + 345e3,
        specific_gravity=0.90,
        viscosity_cp=50.0,
        valve_design="Balanced Bellows",
        Kd=0.65,
        Kc=1.0,
        Kw=0.97,
    )
    assert result.Kv_used == 1.0
    assert abs(result.A_req_mm2 - 3066.0) / 3066.0 < 0.01


# --- API 526 / API 6D single source of truth --------------------------------

def test_api526_data_single_source_consistency():
    orifices = load_api526_data()
    effective = api526_effective_orifices()
    assert len(orifices) == 14
    assert len(effective) == len(orifices)
    for orifice, (letter, area_mm2, _size_in, _size_dn) in zip(orifices, effective):
        assert orifice.letter == letter
        assert orifice.area_mm2 == area_mm2


def test_api6d_data_is_present_and_positive():
    valves = load_api6d_data()
    assert len(valves) > 0
    for valve in valves:
        assert valve.area_mm2 > 0.0


# --- Native blowdown edge case (no NameError when p0 <= target) -------------

def test_native_blowdown_skips_loop_without_name_error():
    inputs = {
        "composition": {"Methane": 1.0},
        "V_sys": 1.0,
        "p0_pa": 2.0e5,
        "T0_k": 300.0,
        "p_target_blowdown_pa": 3.0e5,
        "t_target_sec": 60.0,
    }
    sim_df = run_native_blowdown_simulation(inputs, 1.0e-4, silent=False)
    assert sim_df is not None
    assert len(sim_df) >= 1


# --- DCMR closed-form area/time inverse consistency -------------------------

def test_dcmr_area_time_inverse_consistency():
    inputs = {
        "composition": {"Methane": 0.95, "Ethane": 0.05},
        "V_sys": 50.0,
        "p0_pa": 100.0e5,
        "T0_k": 320.0,
        "p_target_blowdown_pa": 10.0e5,
        "t_target_sec": 300.0,
        "p_downstream": P_ATM,
    }
    area = find_dcmr_blowdown_area(inputs)
    assert area is not None and area > 0.0
    sim_df = run_dcmr_blowdown_simulation(inputs, area, silent=False)
    time_to_target = sim_df.attrs["time_to_target"]
    assert abs(time_to_target - inputs["t_target_sec"]) / inputs["t_target_sec"] < 0.01


# --- API 2000 liquid movement factors (7th ed.) -----------------------------

def test_api2000_liquid_movement_factors():
    non_volatile = calculate_api2000_venting(1000.0, 30.0, False, pump_in_m3h=100.0, pump_out_m3h=100.0)
    assert abs(non_volatile["pump_in_component"] - 1.01 * 100.0) < 1e-9
    assert abs(non_volatile["pump_out_component"] - 0.94 * 100.0) < 1e-9

    volatile = calculate_api2000_venting(1000.0, 30.0, True, pump_in_m3h=100.0, pump_out_m3h=100.0)
    assert abs(volatile["pump_in_component"] - 2.02 * 100.0) < 1e-9
    assert abs(volatile["pump_out_component"] - 2.02 * 100.0) < 1e-9


# --- Vendor catalog schema validation ---------------------------------------

def _valid_record():
    return {
        "manufacturer": "TestVendor",
        "series": "TV-100",
        "model_code": "TV-100-J",
        "design_type": "Conventional",
        "orifice_letter": "J",
        "inlet_outlet_size_in": '3" x 4"',
        "inlet_outlet_size_dn": "DN80 x DN100",
        "effective_area_mm2": "830.3",
        "actual_area_mm2": "950.0",
        "certified_kd_gas": "0.874",
    }


def test_vendor_record_validation_rejects_malformed():
    valid, errors = validate_vendor_records([{"manufacturer": "OnlyOneField"}])
    assert valid == []
    assert len(errors) == 1
    assert "required field" in errors[0]


def test_vendor_record_validation_coerces_numeric_strings():
    valid, errors = validate_vendor_records([_valid_record()])
    assert errors == []
    assert len(valid) == 1
    assert isinstance(valid[0]["effective_area_mm2"], float)


# --- PSV report honours unit preferences ------------------------------------

class _FakeConverter:
    def convert_pressure_from_pa(self, value_pa, unit_str):
        if "psi" in unit_str.lower():
            return value_pa / 6894.76
        return value_pa / 1e5


def test_psv_report_uses_unit_preferences():
    from psv_preliminary import calculate_preliminary_gas_psv_area
    from psv_reporting import build_psv_report_bundle

    Valve = namedtuple("Valve", ["size_in", "size_dn", "area_mm2"])
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

    unit_prefs = {
        "pressure": "psia",
        "temperature": "F",
        "mass_flow": "lb/h",
        "vol_flow": "m3/h",
    }
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
        force_n=None,
        force_kgf=None,
        mach_number=None,
        selected_valve=selected_valve,
        valve_data=[selected_valve],
        vendor_selection=None,
        vendor_evaluation=None,
        warning_lines=[],
        reaction_discharge_area_m2=0.001,
        unit_prefs=unit_prefs,
        converter=_FakeConverter(),
    )
    assert "psia" in bundle.text
    assert "°F" in bundle.text
    assert "lb/h" in bundle.text


if __name__ == "__main__":
    test_liquid_viscosity_correction_is_monotonic_and_bounded()
    test_liquid_reynolds_number_units()
    test_liquid_sizing_applies_viscosity_correction_when_re_below_100()
    test_liquid_sizing_no_correction_at_high_re()
    test_api526_data_single_source_consistency()
    test_api6d_data_is_present_and_positive()
    test_native_blowdown_skips_loop_without_name_error()
    test_dcmr_area_time_inverse_consistency()
    test_api2000_liquid_movement_factors()
    test_vendor_record_validation_rejects_malformed()
    test_vendor_record_validation_coerces_numeric_strings()
    test_psv_report_uses_unit_preferences()
    print("TEST COMPLETED")
