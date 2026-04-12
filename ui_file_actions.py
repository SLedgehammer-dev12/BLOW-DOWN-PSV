from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox


def build_settings_payload(app) -> dict:
    return {
        "mode": app.mode_combo.get(),
        "system_type": app.sys_type_combo.get(),
        "valve_type": app.valve_type_combo.get(),
        "solver_engine": app.engine_combo.get(),
        "segment_count": app.segment_count_entry.get(),
        "vendor_catalog_path": app.vendor_catalog_path,
        "psv_service": app.psv_service_combo.get(),
        "prv_design": app.prv_design_combo.get(),
        "rupture_disk": app.rupture_disk_combo.get(),
        "psvpy_crosscheck_enabled": app.psvpy_crosscheck_var.get() if hasattr(app, "psvpy_crosscheck_var") else False,
        "fire_case_enabled": app.fire_case_var.get(),
        "fire_case_scenario": app.fire_case_scenario_combo.get(),
        "fire_case_factor": app.fire_case_factor_entry.get(),
        "ht_enabled": app.ht_enabled_var.get(),
        "entries": {key: widget.get() for key, widget in app.entries.items()},
        "units": {key: widget.get() for key, widget in app.unit_combos.items()},
        "composition": dict(app.composition),
    }


def write_settings_payload(path: str | Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)


def read_settings_payload(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_settings_payload(app, data: dict, *, default_engine_name: str) -> None:
    legacy_entries = dict(data.get("entries", {}))
    legacy_cd = legacy_entries.get("Discharge Coeff (Cd)")
    if legacy_cd is not None:
        legacy_entries.setdefault("Valve Discharge Coeff (Cd)", legacy_cd)
        legacy_entries.setdefault("PSV Certified Kd", legacy_cd)

    app.mode_combo.set(data.get("mode", "Zamana Bağlı Basınç Düşürme (Blowdown)"))
    app.sys_type_combo.set(data.get("system_type", "Boru Hattı (Pipeline)"))
    app.valve_type_combo.set(data.get("valve_type", "API 526 (PSV/PRV)"))
    app.engine_combo.set(data.get("solver_engine", default_engine_name))
    app.segment_count_entry.delete(0, "end")
    app.segment_count_entry.insert(0, str(data.get("segment_count", "8")))
    app.vendor_catalog_path = data.get("vendor_catalog_path")
    app.psv_service_combo.set(data.get("psv_service", "Gas/Vapor"))
    app.prv_design_combo.set(data.get("prv_design", "Conventional"))
    app.rupture_disk_combo.set(data.get("rupture_disk", "No"))
    if hasattr(app, "psvpy_crosscheck_var"):
        app.psvpy_crosscheck_var.set(data.get("psvpy_crosscheck_enabled", False))
    app.fire_case_var.set(data.get("fire_case_enabled", False))
    app.fire_case_scenario_combo.set(data.get("fire_case_scenario", "Adequate drainage + firefighting"))
    app.fire_case_factor_entry.delete(0, "end")
    app.fire_case_factor_entry.insert(0, str(data.get("fire_case_factor", "1.0")))
    app.ht_enabled_var.set(data.get("ht_enabled", True))

    for key, value in legacy_entries.items():
        if key in app.entries:
            app.entries[key].delete(0, "end")
            app.entries[key].insert(0, str(value))

    for key, value in data.get("units", {}).items():
        if key in app.unit_combos:
            app.unit_combos[key].set(str(value))

    app.composition = data.get("composition", {})
    app.update_composition_display()
    app.on_mode_change()


def export_psv_bundle_with_dialog(bundle, *, export_kind: str, export_csv_fn, export_pdf_fn) -> bool:
    if export_kind == "csv":
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="PSV CSV Raporunu Kaydet",
        )
        if not file_path:
            return False
        export_csv_fn(file_path, bundle)
        return True

    if export_kind == "pdf":
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="PSV PDF Raporunu Kaydet",
        )
        if not file_path:
            return False
        export_pdf_fn(file_path, bundle)
        return True

    raise ValueError(f"Unsupported export kind: {export_kind}")


def export_blowdown_bundle_with_dialog(bundle, *, export_kind: str, export_csv_fn, export_pdf_fn) -> bool:
    if export_kind == "csv":
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Blowdown CSV Raporunu Kaydet",
        )
        if not file_path:
            return False
        export_csv_fn(file_path, bundle)
        return True

    if export_kind == "pdf":
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Blowdown PDF Raporunu Kaydet",
        )
        if not file_path:
            return False
        export_pdf_fn(file_path, bundle)
        return True

    raise ValueError(f"Unsupported export kind: {export_kind}")


def show_psv_export_result(*, export_kind: str, success: bool) -> None:
    if not success:
        return
    if export_kind == "csv":
        messagebox.showinfo("PSV Export", "CSV raporu kaydedildi.")
        return
    if export_kind == "pdf":
        messagebox.showinfo("PSV Export", "PDF raporu kaydedildi.")
        return
    raise ValueError(f"Unsupported export kind: {export_kind}")


def show_blowdown_export_result(*, export_kind: str, success: bool) -> None:
    if not success:
        return
    if export_kind == "csv":
        messagebox.showinfo("Blowdown Export", "CSV raporu kaydedildi.")
        return
    if export_kind == "pdf":
        messagebox.showinfo("Blowdown Export", "PDF raporu kaydedildi.")
        return
    raise ValueError(f"Unsupported export kind: {export_kind}")
