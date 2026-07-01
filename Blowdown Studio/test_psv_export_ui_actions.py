import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from psv_export_ui_actions import export_psv_report_with_feedback, require_psv_report_bundle


def test_require_psv_report_bundle_raises():
    try:
        require_psv_report_bundle(None)
    except ValueError as exc:
        assert "Aktif bir PSV raporu yok" in str(exc)
        return
    raise AssertionError("ValueError bekleniyordu")


def test_export_psv_report_with_feedback_success():
    results = []
    bundle = {"demo": True}

    ok = export_psv_report_with_feedback(
        bundle,
        export_kind="csv",
        export_bundle_with_dialog_fn=lambda payload, export_kind: payload is bundle and export_kind == "csv",
        show_result_fn=lambda **kwargs: results.append(kwargs),
        showwarning_fn=lambda *_args: None,
        showerror_fn=lambda *_args: None,
    )

    assert ok is True
    assert results == [{"export_kind": "csv", "success": True}]


def test_export_psv_report_with_feedback_missing_bundle():
    warnings = []

    ok = export_psv_report_with_feedback(
        None,
        export_kind="pdf",
        export_bundle_with_dialog_fn=lambda *_args, **_kwargs: True,
        show_result_fn=lambda **_kwargs: None,
        showwarning_fn=lambda title, text: warnings.append((title, text)),
        showerror_fn=lambda *_args: None,
    )

    assert ok is False
    assert warnings


if __name__ == "__main__":
    test_require_psv_report_bundle_raises()
    test_export_psv_report_with_feedback_success()
    test_export_psv_report_with_feedback_missing_bundle()
    print("TEST COMPLETED")
