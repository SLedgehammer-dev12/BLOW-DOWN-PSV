import os
import sys
from collections import namedtuple

import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from blowdown_ui_actions import execute_blowdown_ui_flow


Valve = namedtuple("Valve", ["size_in", "size_dn", "area_mm2", "letter"])


class DummyAbortFlag:
    def __init__(self, aborted=False):
        self._aborted = aborted

    def is_set(self):
        return self._aborted


def test_execute_blowdown_ui_flow_completed():
    progress_calls = []

    def progress(current, target, text=""):
        progress_calls.append((current, target, text))

    sim_df = pd.DataFrame(
        [
            {"t": 0.0, "p_sys": 10e5, "mdot_kg_s": 1.0, "T_sys": 300.0, "T_wall": 300.0, "rho_g": 8.0, "m_sys": 100.0, "h_in": 10.0},
            {"t": 5.0, "p_sys": 5e5, "mdot_kg_s": 0.5, "T_sys": 290.0, "T_wall": 295.0, "rho_g": 4.0, "m_sys": 80.0, "h_in": 8.0},
        ]
    )

    result = execute_blowdown_ui_flow(
        user_inputs={"solver_engine": "Yerel Cozucu", "valve_count": 1, "valve_type": "API 526 (PSV/PRV)"},
        native_engine_name="Yerel Cozucu",
        update_progress_ui=progress,
        abort_flag=DummyAbortFlag(False),
        load_api526_data=lambda: [Valve('2"', "DN50", 250.0, "F")],
        load_api6d_data=lambda: [Valve('2"', "DN50", 250.0, "F")],
        size_area_fn=lambda *args, **kwargs: 2.0e-4,
        select_standard_valve_fn=lambda valve_data, required: (valve_data[0], False),
        run_engine_fn=lambda *args, **kwargs: sim_df,
        build_report_fn=lambda **kwargs: {"report_text": "ok", "screening_inputs": {"a": 1}, "verdict": "PASS", "sim_time_s": 5.0, "target_time_s": 10.0},
    )

    assert result.status == "completed"
    assert result.required_area_m2 == 2.0e-4
    assert result.workflow_result["report_text"] == "ok"
    assert result.selected_valve.area_mm2 == 250.0
    assert progress_calls[0][0] == 10
    assert progress_calls[-1][0] == 100


def test_execute_blowdown_ui_flow_aborted():
    progress_calls = []

    result = execute_blowdown_ui_flow(
        user_inputs={"solver_engine": "Yerel Cozucu", "valve_count": 1, "valve_type": "API 526 (PSV/PRV)"},
        native_engine_name="Yerel Cozucu",
        update_progress_ui=lambda c, t, text="": progress_calls.append((c, t, text)),
        abort_flag=DummyAbortFlag(True),
        load_api526_data=lambda: [Valve('2"', "DN50", 250.0, "F")],
        load_api6d_data=lambda: [Valve('2"', "DN50", 250.0, "F")],
        size_area_fn=lambda *args, **kwargs: None,
        select_standard_valve_fn=lambda valve_data, required: (valve_data[0], False),
        run_engine_fn=lambda *args, **kwargs: None,
        build_report_fn=lambda **kwargs: {},
    )

    assert result.status == "aborted"
    assert progress_calls[-1][0] == 0


if __name__ == "__main__":
    test_execute_blowdown_ui_flow_completed()
    test_execute_blowdown_ui_flow_aborted()
    print("TEST COMPLETED")
