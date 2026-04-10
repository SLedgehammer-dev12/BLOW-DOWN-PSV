from __future__ import annotations


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


def _resolve_field_key(app, field_name: str, mapping_name: str = "entry_frames") -> str:
    mapping = getattr(app, mapping_name)
    for candidate in _candidate_field_keys(field_name):
        if candidate in mapping:
            return candidate
    return field_name


def set_field_label(app, field_name: str, label_text: str) -> None:
    resolved_key = _resolve_field_key(app, field_name, "entry_frames")
    app.entry_frames[resolved_key][0].config(text=label_text)


def set_unit_options(app, field_name: str, units, default_unit: str) -> None:
    resolved_key = _resolve_field_key(app, field_name, "unit_combos")
    combo = app.unit_combos[resolved_key]
    combo.configure(values=units)
    if combo.get() not in units:
        combo.set(default_unit)


def configure_psv_service_fields(app, service_field_config_builder):
    service_type = app.psv_service_combo.get() if hasattr(app, "psv_service_combo") else "Gas/Vapor"
    kd_key = _resolve_field_key(app, "PSV Certified Kd", "entries")
    flow_key = _resolve_field_key(app, "Gerekli Tahliye Debisi", "unit_combos")
    config = service_field_config_builder(service_type, app.entries[kd_key].get())
    for field_name, label_text in config.field_labels.items():
        set_field_label(app, field_name, label_text)
    set_unit_options(app, flow_key, config.flow_units, config.flow_default_unit)
    if config.kd_default_value is not None:
        app.entries[kd_key].delete(0, 0x7FFFFFFF)
        app.entries[kd_key].insert(0, config.kd_default_value)
    return config


def apply_mode_change(
    app,
    *,
    app_version: str,
    native_engine_name: str,
    state_builder,
    service_field_config_builder,
    placeholder_callback,
):
    mode = app.mode_combo.get()
    fire_case_enabled = app.fire_case_var.get() if hasattr(app, "fire_case_var") else False
    engine_name = app.engine_combo.get() if hasattr(app, "engine_combo") else native_engine_name
    state = state_builder(
        mode=mode,
        fire_case_enabled=fire_case_enabled,
        engine_name=engine_name,
        app_version=app_version,
    )

    resolved_visible_fields = {
        _resolve_field_key(app, field_name, "entry_frames")
        for field_name in state.visible_fields
    }
    all_fields = set(app.entry_frames.keys())
    for field in all_fields:
        should_show = field in resolved_visible_fields
        if should_show:
            app.entry_frames[field][0].grid()
            app.entry_frames[field][1].grid()
        else:
            app.entry_frames[field][0].grid_remove()
            app.entry_frames[field][1].grid_remove()

    for field_name, label_text in state.field_labels.items():
        set_field_label(app, field_name, label_text)

    if hasattr(app, "mode_help_label"):
        app.mode_help_label.config(text=state.helper_text)

    if hasattr(app, "valve_type_combo"):
        if state.placeholder_mode == "PSV":
            app.valve_type_combo.configure(state="readonly")
            app.valve_type_combo.set("API 526 (PSV/PRV)")
            app.valve_type_combo.configure(state="disabled")
        else:
            app.valve_type_combo.configure(state="readonly")
            app.valve_type_combo.set("API 6D (Küresel/Blowdown)")
            app.valve_type_combo.configure(state="disabled")

    if state.show_sys_type:
        app.sys_type_combo.grid()
        app.sys_type_lbl.grid()
    else:
        app.sys_type_combo.grid_remove()
        app.sys_type_lbl.grid_remove()

    if state.show_engine_options:
        app.engine_options_frame.grid()
    else:
        app.engine_options_frame.grid_remove()

    if state.show_fire_case_frame:
        app.fire_case_frame.grid()
    else:
        app.fire_case_frame.grid_remove()

    if state.show_psv_options:
        app.psv_options_frame.grid()
        configure_psv_service_fields(app, service_field_config_builder)
    else:
        app.psv_options_frame.grid_remove()

    if state.show_ht_check:
        app.ht_check.grid()
    else:
        app.ht_check.grid_remove()

    if state.show_abort:
        app.btn_abort.grid()
    else:
        app.btn_abort.grid_remove()

    if state.show_progress:
        app.progress.grid()
        app.progress_label.grid()
    else:
        app.progress.grid_remove()
        app.progress_label.grid_remove()

    app.btn_run.config(text=state.run_button_text)
    placeholder_callback(state.placeholder_mode)
    return state
