from constants import P_ATM
from psvpy_adapter import build_psvpy_crosscheck


def test_psvpy_crosscheck_liquid_uses_vendored_subset():
    inputs = {
        "composition": {"Water": 1.0},
        "set_pressure_pa": P_ATM + 12.0e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 303.15,
        "p_total_backpressure_pa": P_ATM + 2.0e5,
        "W_req_kg_h": 9000.0,
        "Kw": 0.95,
        "Kc": 1.0,
    }

    result = build_psvpy_crosscheck(inputs=inputs, service_type="Liquid", native_area_mm2=3000.0)

    assert result.service_type == "Liquid"
    assert result.area_mm2 > 0.0
    assert "psvpy" in result.provider
    assert any("Kw" in note for note in result.notes)


def test_psvpy_crosscheck_steam_reports_fixed_backpressure_assumption():
    inputs = {
        "composition": {"Water": 1.0},
        "set_pressure_pa": P_ATM + 100.0e5,
        "overpressure_pct": 10.0,
        "relieving_temperature_k": 707.15,
        "p_total_backpressure_pa": P_ATM + 5.0e5,
        "W_req_kg_h": 10000.0,
        "Kb": 0.95,
        "Kc": 1.0,
    }

    result = build_psvpy_crosscheck(inputs=inputs, service_type="Steam", native_area_mm2=1000.0)

    assert result.service_type == "Steam"
    assert result.area_mm2 > 0.0
    assert any("backpressure" in note.lower() for note in result.notes)
