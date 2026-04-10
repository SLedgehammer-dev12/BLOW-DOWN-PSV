import os
import sys
from types import SimpleNamespace

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from execution_ui_actions import run_blowdown_ui_flow_with_feedback, run_psv_ui_flow_with_feedback


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg, *args):
        self.messages.append(("info", msg % args if args else msg))

    def warning(self, msg, *args):
        self.messages.append(("warning", msg % args if args else msg))

    def error(self, msg, *args):
        self.messages.append(("error", msg % args if args else msg))

    def exception(self, msg, *args):
        self.messages.append(("exception", msg % args if args else msg))


class DummyApp:
    def __init__(self):
        self.last_psv_report_bundle = "old"
        self.vendor_catalog_path = r"C:\Temp\vendor.json"


def test_run_psv_ui_flow_with_feedback_success():
    app = DummyApp()
    status_texts = []

    def collect_payload(_app, *, converter):
        assert converter == "conv"
        return {
            "inputs": {"a": 1},
            "service_type": "Gas/Vapor",
            "valve_type": "API 526 (PSV/PRV)",
            "valve_count": 1,
            "rupture_disk": "No",
            "flow_unit": "kg/h",
            "flow_value": 100.0,
            "normalized_composition": {"Methane": 1.0},
        }

    called = {}

    result = run_psv_ui_flow_with_feedback(
        app,
        converter="conv",
        collect_payload_fn=collect_payload,
        get_active_vendor_catalog_fn=lambda: {"models": []},
        execute_workflow_fn=lambda **kwargs: called.setdefault("workflow", kwargs) or SimpleNamespace(),
        apply_result_fn=lambda app_obj, workflow, catalog_path: (app_obj, workflow, catalog_path),
        load_api526_data=lambda: [],
        load_api6d_data=lambda: [],
        set_status_text_fn=status_texts.append,
        refresh_ui_fn=lambda: called.setdefault("refreshed", True),
        showerror_fn=lambda *_args: None,
    )

    assert status_texts[0].startswith("Hesaplan")
    assert called["workflow"]["service_type"] == "Gas/Vapor"
    assert result[0] is app
    assert result[2] == r"C:\Temp\vendor.json"


def test_run_blowdown_ui_flow_with_feedback_success():
    logger = DummyLogger()
    scheduled = []
    stored = []

    result_obj = SimpleNamespace(
        status="completed",
        fallback_used=False,
        workflow_result={
            "report_text": "ok",
            "screening_inputs": {"x": 1},
            "verdict": "PASS",
            "sim_time_s": 5.0,
            "target_time_s": 10.0,
            "report_bundle": {"title": "demo"},
        },
        sim_df="df",
        selected_valve="valve",
    )

    result = run_blowdown_ui_flow_with_feedback(
        user_inputs={"solver_engine": "Yerel"},
        native_engine_name="Yerel",
        execute_flow_fn=lambda **_kwargs: result_obj,
        update_progress_ui=lambda *_args, **_kwargs: None,
        abort_flag=SimpleNamespace(),
        load_api526_data=lambda: [],
        load_api6d_data=lambda: [],
        size_area_fn=lambda *_args, **_kwargs: None,
        select_standard_valve_fn=lambda *_args, **_kwargs: None,
        run_engine_fn=lambda *_args, **_kwargs: None,
        build_report_fn=lambda **_kwargs: None,
        logger=logger,
        schedule_ui_fn=lambda delay, fn, *args: scheduled.append((delay, fn, args)),
        update_results_fn=lambda *_args: None,
        plot_results_fn=lambda *_args: None,
        showerror_fn=lambda *_args: None,
        showwarning_fn=lambda *_args: None,
        finalize_run_button_fn=lambda: None,
        finalize_abort_button_fn=lambda: None,
        store_report_bundle_fn=lambda bundle: stored.append(bundle),
    )

    assert result is result_obj
    assert any(level == "info" for level, _ in logger.messages)
    assert len(scheduled) == 5

    for _delay, fn, args in scheduled:
        fn(*args)
    assert stored == [{"title": "demo"}]


def test_run_blowdown_ui_flow_with_feedback_fail_and_fallback():
    logger = DummyLogger()
    scheduled = []

    result_obj = SimpleNamespace(
        status="completed",
        fallback_used=True,
        workflow_result={
            "report_text": "bad",
            "screening_inputs": {"x": 1},
            "verdict": "FAIL",
            "sim_time_s": 25.0,
            "target_time_s": 10.0,
            "report_bundle": None,
        },
        sim_df="df",
        selected_valve="valve",
    )
    warnings = []
    errors = []

    result = run_blowdown_ui_flow_with_feedback(
        user_inputs={"solver_engine": "Yerel"},
        native_engine_name="Yerel",
        execute_flow_fn=lambda **_kwargs: result_obj,
        update_progress_ui=lambda *_args, **_kwargs: None,
        abort_flag=SimpleNamespace(),
        load_api526_data=lambda: [],
        load_api6d_data=lambda: [],
        size_area_fn=lambda *_args, **_kwargs: None,
        select_standard_valve_fn=lambda *_args, **_kwargs: None,
        run_engine_fn=lambda *_args, **_kwargs: None,
        build_report_fn=lambda **_kwargs: None,
        logger=logger,
        schedule_ui_fn=lambda delay, fn, *args: scheduled.append((delay, fn, args)),
        update_results_fn=lambda *_args: None,
        plot_results_fn=lambda *_args: None,
        showerror_fn=lambda title, msg: errors.append((title, msg)),
        showwarning_fn=lambda title, msg: warnings.append((title, msg)),
        finalize_run_button_fn=lambda: None,
        finalize_abort_button_fn=lambda: None,
    )

    assert result is result_obj
    assert len(scheduled) == 7
    for _delay, fn, args in scheduled:
        fn(*args)
    assert warnings and "En büyük standart vana seçildi" in warnings[0][1]
    assert errors and "BAŞARISIZ" in errors[0][0]


def test_run_blowdown_ui_flow_with_feedback_solver_exception():
    logger = DummyLogger()
    scheduled = []
    errors = []
    finalized = {"run": 0, "abort": 0}

    result = run_blowdown_ui_flow_with_feedback(
        user_inputs={"solver_engine": "Yerel"},
        native_engine_name="Yerel",
        execute_flow_fn=lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("t=4.50s anında termodinamik çözücü hatası (segmented pipeline, segment=3).")
        ),
        update_progress_ui=lambda *_args, **_kwargs: None,
        abort_flag=SimpleNamespace(),
        load_api526_data=lambda: [],
        load_api6d_data=lambda: [],
        size_area_fn=lambda *_args, **_kwargs: None,
        select_standard_valve_fn=lambda *_args, **_kwargs: None,
        run_engine_fn=lambda *_args, **_kwargs: None,
        build_report_fn=lambda **_kwargs: None,
        logger=logger,
        schedule_ui_fn=lambda delay, fn, *args: scheduled.append((delay, fn, args)),
        update_results_fn=lambda *_args: None,
        plot_results_fn=lambda *_args: None,
        showerror_fn=lambda title, msg: errors.append((title, msg)),
        showwarning_fn=lambda *_args: None,
        finalize_run_button_fn=lambda: finalized.__setitem__("run", finalized["run"] + 1),
        finalize_abort_button_fn=lambda: finalized.__setitem__("abort", finalized["abort"] + 1),
    )

    assert result is None
    for _delay, fn, args in scheduled:
        fn(*args)
    assert errors and "t=4.50s" in errors[0][1]
    assert finalized == {"run": 1, "abort": 1}
    assert any(level == "exception" for level, _ in logger.messages)


if __name__ == "__main__":
    test_run_psv_ui_flow_with_feedback_success()
    test_run_blowdown_ui_flow_with_feedback_success()
    test_run_blowdown_ui_flow_with_feedback_fail_and_fallback()
    test_run_blowdown_ui_flow_with_feedback_solver_exception()
    print("TEST COMPLETED")
