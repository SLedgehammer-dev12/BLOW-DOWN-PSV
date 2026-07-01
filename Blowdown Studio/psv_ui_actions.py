from __future__ import annotations

from ui_mode_logic import (
    FIELD_BACKPRESSURE,
    FIELD_BACKPRESSURE_KB,
    FIELD_MAWP,
    FIELD_OVERPRESSURE,
    FIELD_PSV_KD,
    FIELD_REQUIRED_BODY_MATERIAL,
    FIELD_REQUIRED_CODE_STAMP,
    FIELD_REQUIRED_FLOW,
    FIELD_REQUIRED_INLET_CLASS,
    FIELD_REQUIRED_OUTLET_CLASS,
    FIELD_REQUIRED_TRIM_CODE,
    FIELD_REQUIRED_TRIM_MATERIAL,
    FIELD_START_PRESSURE,
    FIELD_START_TEMPERATURE,
    FIELD_VALVE_COUNT,
)


def _get_optional_float(entry_widget) -> float | None:
    value = entry_widget.get().strip()
    return float(value) if value else None


def _get_optional_str(entry_widget) -> str | None:
    value = entry_widget.get().strip()
    return value or None


def _candidate_field_keys(field_name: str) -> list[str]:
    candidates = [field_name]
    transforms = (
        ("utf-8", "latin1"),
        ("latin1", "utf-8"),
        ("cp1254", "utf-8"),
        ("utf-8", "cp1254"),
    )
    for encode_name, decode_name in transforms:
        try:
            variant = field_name.encode(encode_name).decode(decode_name)
        except Exception:
            continue
        if variant not in candidates:
            candidates.append(variant)
    return candidates


def _resolve_mapping_key(mapping, field_name: str) -> str:
    for candidate in _candidate_field_keys(field_name):
        if candidate in mapping:
            return candidate
    return field_name


def collect_psv_ui_payload(app, *, converter):
    raw_composition = dict(app.composition)
    normalized_composition = {}
    if raw_composition:
        total_pct = sum(raw_composition.values())
        normalized_composition = {key: value / total_pct for key, value in raw_composition.items()}

    def get_val(key):
        resolved_key = _resolve_mapping_key(app.entries, key)
        return _get_optional_float(app.entries[resolved_key])

    def get_text(key):
        resolved_key = _resolve_mapping_key(app.entries, key)
        return _get_optional_str(app.entries[resolved_key])

    def get_unit(key):
        resolved_key = _resolve_mapping_key(app.unit_combos, key)
        return app.unit_combos[resolved_key].get()

    service_type = app.psv_service_combo.get()
    flow_val = get_val(FIELD_REQUIRED_FLOW)
    set_pressure_val = get_val(FIELD_START_PRESSURE)
    mawp_val = get_val(FIELD_MAWP)
    overpressure_val = get_val(FIELD_OVERPRESSURE)
    relieving_temp_val = get_val(FIELD_START_TEMPERATURE)
    backpressure_val = get_val(FIELD_BACKPRESSURE)
    valve_count = int(get_val(FIELD_VALVE_COUNT) or 1)
    valve_type = app.valve_type_combo.get()

    if valve_count < 1:
        raise ValueError("Vana sayısı en az 1 olmalıdır.")
    if flow_val is None or set_pressure_val is None or relieving_temp_val is None or backpressure_val is None:
        raise ValueError("Debi, set pressure, relieving temperature ve backpressure alanları zorunludur.")
    if service_type != "Steam" and not normalized_composition:
        raise ValueError("Lütfen en az bir akışkan bileşeni ekleyin.")

    inputs = {
        "composition": normalized_composition,
        "psv_service_type": service_type,
        "set_pressure_pa": converter.convert_pressure(set_pressure_val, get_unit(FIELD_START_PRESSURE)),
        "overpressure_pct": overpressure_val if overpressure_val is not None else 10.0,
        "relieving_temperature_k": converter.convert_temperature(relieving_temp_val, get_unit(FIELD_START_TEMPERATURE)),
        "p_total_backpressure_pa": converter.convert_pressure(backpressure_val, get_unit(FIELD_BACKPRESSURE)),
        "Kd_api520": get_val(FIELD_PSV_KD) or (0.65 if service_type == "Liquid" else 0.975),
        "Kb": get_val(FIELD_BACKPRESSURE_KB),
        "Kw": get_val(FIELD_BACKPRESSURE_KB) if service_type == "Liquid" else None,
        "Kc": 0.9 if app.rupture_disk_combo.get() == "Yes" else 1.0,
        "prv_design": app.prv_design_combo.get(),
        "psvpy_crosscheck": bool(app.psvpy_crosscheck_var.get()) if hasattr(app, "psvpy_crosscheck_var") else False,
        "valve_count": valve_count,
        "valve_type": valve_type,
        "required_trim_code": get_text(FIELD_REQUIRED_TRIM_CODE),
        "required_code_stamp": get_text(FIELD_REQUIRED_CODE_STAMP),
        "required_body_material": get_text(FIELD_REQUIRED_BODY_MATERIAL),
        "required_trim_material": get_text(FIELD_REQUIRED_TRIM_MATERIAL),
        "required_inlet_rating_class": get_text(FIELD_REQUIRED_INLET_CLASS),
        "required_outlet_rating_class": get_text(FIELD_REQUIRED_OUTLET_CLASS),
    }
    inputs["mawp_pa"] = (
        converter.convert_pressure(mawp_val, get_unit(FIELD_MAWP))
        if mawp_val is not None
        else inputs["set_pressure_pa"]
    )

    return {
        "inputs": inputs,
        "service_type": service_type,
        "valve_type": valve_type,
        "valve_count": valve_count,
        "rupture_disk": app.rupture_disk_combo.get(),
        "flow_unit": get_unit(FIELD_REQUIRED_FLOW),
        "flow_value": flow_val,
        "normalized_composition": normalized_composition,
    }


def apply_vendor_catalog_note(report_bundle, vendor_catalog_path: str | None):
    if vendor_catalog_path:
        catalog_note = f"Aktif vendor screening kataloğu: {vendor_catalog_path}"
        report_bundle.text = f"{report_bundle.text}\n- {catalog_note}"
        report_bundle.summary_rows.append(("Vendor Catalog Path", vendor_catalog_path))
    return report_bundle


def apply_psv_workflow_result(app, workflow, vendor_catalog_path: str | None = None):
    report_bundle = apply_vendor_catalog_note(workflow.report_bundle, vendor_catalog_path)
    app.last_psv_report_bundle = report_bundle
    app.update_results_text(report_bundle.text)
    app.plot_psv_graphs(
        workflow.sizing,
        workflow.inputs,
        workflow.selected_valve,
        workflow.valve_data,
        workflow.vendor_selection,
        workflow.vendor_evaluation,
        workflow.force_n,
        workflow.valve_count,
    )
    return report_bundle
