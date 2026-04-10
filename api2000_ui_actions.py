from __future__ import annotations


API2000_FIELD_TANK_VOLUME = "Tank Hacmi (m3)"
API2000_FIELD_LATITUDE = "Latitude (Band)"
API2000_FIELD_PUMP_IN = "Pompalama Giriş Hızı (m3/h)"
API2000_FIELD_PUMP_OUT = "Pompalama Çıkış Hızı (m3/h)"
API2000_FIELD_INSULATION = "İzolasyon Faktörü (Ri)"
API2000_FIELD_EMERGENCY_WETTED_AREA = "Emergency Wetted Area (m2)"
API2000_FIELD_LATENT_HEAT = "Latent Heat (kJ/kg)"
API2000_FIELD_VAPOR_MW = "Vapor MW (kg/kmol)"
API2000_FIELD_FIRE_FACTOR = "Fire Exposure Factor (F)"


def _get_required_float(entry_widget, field_name: str) -> float:
    value = entry_widget.get().strip()
    if not value:
        raise ValueError(f"{field_name} alanı zorunludur.")
    parsed = float(value)
    if parsed <= 0.0:
        raise ValueError(f"{field_name} pozitif olmalıdır.")
    return parsed


def collect_api2000_ui_payload(app) -> dict:
    emergency_enabled = app.api_emergency_var.get()
    return {
        "tank_volume_m3": _get_required_float(app.api_entries[API2000_FIELD_TANK_VOLUME], API2000_FIELD_TANK_VOLUME),
        "latitude_band": app.api_entries[API2000_FIELD_LATITUDE].get(),
        "is_volatile": app.api_volatile_var.get(),
        "pump_in_m3h": _get_required_float(app.api_entries[API2000_FIELD_PUMP_IN], API2000_FIELD_PUMP_IN),
        "pump_out_m3h": _get_required_float(app.api_entries[API2000_FIELD_PUMP_OUT], API2000_FIELD_PUMP_OUT),
        "insulation_factor": _get_required_float(app.api_entries[API2000_FIELD_INSULATION], API2000_FIELD_INSULATION),
        "emergency_enabled": emergency_enabled,
        "emergency_wetted_area_m2": _get_required_float(app.api_entries[API2000_FIELD_EMERGENCY_WETTED_AREA], API2000_FIELD_EMERGENCY_WETTED_AREA) if emergency_enabled else None,
        "latent_heat_kj_kg": _get_required_float(app.api_entries[API2000_FIELD_LATENT_HEAT], API2000_FIELD_LATENT_HEAT) if emergency_enabled else None,
        "vapor_mw_kg_kmol": _get_required_float(app.api_entries[API2000_FIELD_VAPOR_MW], API2000_FIELD_VAPOR_MW) if emergency_enabled else None,
        "fire_factor": _get_required_float(app.api_entries[API2000_FIELD_FIRE_FACTOR], API2000_FIELD_FIRE_FACTOR) if emergency_enabled else None,
        "drainage_condition": app.api_emergency_combo.get(),
    }


def execute_api2000_ui_flow(app, *, run_workflow_fn):
    payload = collect_api2000_ui_payload(app)
    return run_workflow_fn(**payload)


def run_api2000_ui_with_feedback(
    app,
    *,
    run_workflow_fn,
    set_text_fn,
    log_info_fn,
    showerror_fn,
):
    try:
        workflow = execute_api2000_ui_flow(app, run_workflow_fn=run_workflow_fn)
        set_text_fn(workflow.summary_text)
        log_info_fn("API 2000 hesabı başarıyla tamamlandı.")
        return workflow
    except Exception as exc:
        showerror_fn("Hata", f"Giriş değerlerini kontrol edin: {exc}")
        return None
