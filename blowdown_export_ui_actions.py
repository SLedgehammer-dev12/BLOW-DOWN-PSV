from __future__ import annotations


def require_blowdown_report_bundle(bundle):
    if bundle is None:
        raise ValueError("Aktif bir blowdown raporu yok. Önce blowdown analizi yapın.")
    return bundle


def export_blowdown_report_with_feedback(
    bundle,
    *,
    export_kind: str,
    export_bundle_with_dialog_fn,
    show_result_fn,
    showwarning_fn,
    showerror_fn,
):
    try:
        active_bundle = require_blowdown_report_bundle(bundle)
    except Exception as exc:
        showwarning_fn("Blowdown Export", str(exc))
        return False

    try:
        success = export_bundle_with_dialog_fn(active_bundle, export_kind=export_kind)
        show_result_fn(export_kind=export_kind, success=success)
        return success
    except Exception as exc:
        label = "CSV" if export_kind == "csv" else "PDF"
        showerror_fn("Blowdown Export", f"{label} kaydedilemedi: {exc}")
        return False
