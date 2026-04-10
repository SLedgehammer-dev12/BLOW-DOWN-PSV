import os
import sys
from collections import namedtuple

import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from blowdown_workflow import build_blowdown_report, select_standard_valve


Valve = namedtuple("Valve", ["size_in", "size_dn", "area_mm2", "letter"])


def test_select_standard_valve():
    valve_data = [
        Valve('1"', "DN25", 100.0, "D"),
        Valve('2"', "DN50", 250.0, "F"),
    ]
    selected, fallback = select_standard_valve(valve_data, 180.0)
    assert selected.area_mm2 == 250.0
    assert fallback is False

    selected, fallback = select_standard_valve(valve_data, 500.0)
    assert selected.area_mm2 == 250.0
    assert fallback is True


def test_build_blowdown_report_basic():
    sim_df = pd.DataFrame(
        [
            {"t": 0.0, "p_sys": 11e5, "mdot_kg_s": 1.2, "T_sys": 300.0, "T_wall": 300.0, "rho_g": 8.0, "m_sys": 100.0, "h_in": 10.0},
            {"t": 10.0, "p_sys": 3e5, "mdot_kg_s": 0.4, "T_sys": 290.0, "T_wall": 295.0, "rho_g": 3.0, "m_sys": 70.0, "h_in": 9.0},
        ]
    )
    sim_df.attrs["warnings"] = ["native warning"]
    sim_df.attrs["time_to_target"] = 10.0

    selected = Valve('2"', "DN50", 250.0, "F")
    result = build_blowdown_report(
        sim_df=sim_df,
        inputs={
            "composition": {"Methane": 1.0},
            "t_target_sec": 15.0,
            "p_target_blowdown_pa": 2e5,
            "system_type": "Boru Hattı (Pipeline)",
            "valve_type": "API 526 (PSV/PRV)",
        },
        engine_name="Yerel Çözücü",
        selected_valve=selected,
        valve_type_label='2" F (DN50)',
        valve_type_description="PSV/PRV Orifis",
        valve_count=1,
        required_area_m2=2.0e-4,
        total_selected_area_m2=2.5e-4,
    )

    assert result["verdict"] == "PASS"
    assert "BLOWDOWN ANALİZ RAPORU" in result["report_text"]
    assert "native warning" in result["report_text"]
    assert "discharge_piping" in result["screening_inputs"]


if __name__ == "__main__":
    test_select_standard_valve()
    test_build_blowdown_report_basic()
    print("TEST COMPLETED")
