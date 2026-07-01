from __future__ import annotations

import math
import tkinter as tk

from ui_mode_logic import (
    FIELD_BACKPRESSURE,
    FIELD_BACKPRESSURE_KB,
    FIELD_INNER_DIAMETER,
    FIELD_LENGTH,
    FIELD_MAWP,
    FIELD_START_PRESSURE,
    FIELD_START_TEMPERATURE,
    FIELD_TARGET_PRESSURE,
    FIELD_TARGET_TIME,
    FIELD_THICKNESS,
    FIELD_TOTAL_VOLUME,
    FIELD_VALVE_CD,
    FIELD_VALVE_COUNT,
)


def normalize_composition(composition: dict[str, float]) -> dict[str, float]:
    if not composition:
        raise ValueError("Lütfen en az bir gaz ekleyin.")
    total_pct = sum(composition.values())
    if total_pct <= 0.0:
        raise ValueError("Kompozisyon toplamı pozitif olmalıdır.")
    return {key: value / total_pct for key, value in composition.items()}


def _get_optional_float(entry_widget) -> float | None:
    value = entry_widget.get().strip()
    return float(value) if value else None


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


def _get_unit(unit_widget) -> str:
    return unit_widget.get()


def _set_entry_value(entry_widget, value: str) -> None:
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, value)


def collect_blowdown_inputs(
    app,
    *,
    converter,
    fire_case_builder,
    p_atm: float,
    segmented_engine_name: str,
    showwarning_fn,
):
    inputs = {"composition": normalize_composition(app.composition)}
    inputs["solver_engine"] = app.engine_combo.get()
    inputs["segment_count"] = max(2, int(float(app.segment_count_entry.get() or "8")))
    inputs["system_type"] = app.sys_type_combo.get()
    inputs["valve_type"] = app.valve_type_combo.get()

    def get_val(key):
        resolved_key = _resolve_mapping_key(app.entries, key)
        return _get_optional_float(app.entries[resolved_key])

    def get_unit(key):
        resolved_key = _resolve_mapping_key(app.unit_combos, key)
        return _get_unit(app.unit_combos[resolved_key])

    d_val = get_val(FIELD_INNER_DIAMETER)
    l_val = get_val(FIELD_LENGTH)
    t_val = get_val(FIELD_THICKNESS)
    vol_val = get_val(FIELD_TOTAL_VOLUME)

    if vol_val is not None and (d_val is None or l_val is None):
        inputs["V_sys"] = converter.convert_volume(vol_val, get_unit(FIELD_TOTAL_VOLUME))
        inputs["HT_enabled"] = False
        app.ht_enabled_var.set(False)
        showwarning_fn(
            "Analiz Uyarısı",
            "Toplam hacim manuel girildiği için API 521 ısıl analizi devre dışı bırakıldı. Simülasyon adyabatik olarak yürütülecektir.",
        )
        inputs["A_inner"] = 1.0
        inputs["M_steel"] = 100.0
    else:
        if d_val is None or l_val is None or t_val is None:
            raise ValueError(
                "Geometrik hesaplama için İç Çap, Uzunluk ve Et Kalınlığı zorunludur. Alternatif olarak yalnız Toplam Hacim girebilirsin."
            )

        d_in_m = converter.convert_length(d_val, get_unit(FIELD_INNER_DIAMETER))
        l_m = converter.convert_length(l_val, get_unit(FIELD_LENGTH))
        t_m = converter.convert_length(t_val, get_unit(FIELD_THICKNESS))
        inputs["D_in_m"] = d_in_m
        inputs["L_m"] = l_m
        inputs["t_m"] = t_m

        inputs["V_sys"] = math.pi * ((d_in_m / 2) ** 2) * l_m
        inputs["A_inner"] = math.pi * d_in_m * l_m

        d_out_m = d_in_m + 2 * t_m
        v_outer = math.pi * ((d_out_m / 2) ** 2) * l_m
        v_metal = v_outer - inputs["V_sys"]
        inputs["M_steel"] = v_metal * 7850.0
        inputs["HT_enabled"] = app.ht_enabled_var.get()

    p0_val = get_val(FIELD_START_PRESSURE)
    t0_val = get_val(FIELD_START_TEMPERATURE)
    pt_val = get_val(FIELD_TARGET_PRESSURE)
    tt_val = get_val(FIELD_TARGET_TIME)
    fire_case_enabled = app.fire_case_var.get() if hasattr(app, "fire_case_var") else False

    if p0_val is None or t0_val is None:
        raise ValueError("Başlangıç basıncı ve başlangıç sıcaklığı alanları zorunludur.")
    if not fire_case_enabled and (pt_val is None or tt_val is None):
        raise ValueError("Fire case dışı senaryoda hedef basınç ve hedef süre zorunludur.")

    inputs["p0_pa"] = converter.convert_pressure(p0_val, get_unit(FIELD_START_PRESSURE))
    inputs["T0_k"] = converter.convert_temperature(t0_val, get_unit(FIELD_START_TEMPERATURE))
    if inputs["p0_pa"] <= p_atm * 0.01:
        raise ValueError("Başlangıç basıncı pozitif bir değer olmalıdır.")
    if inputs["T0_k"] < 50.0:
        raise ValueError("Başlangıç sıcaklığı 50 K (-223°C) altında olamaz.")
    if inputs["T0_k"] > 1500.0:
        raise ValueError("Başlangıç sıcaklığı 1500 K üzerinde desteklenmiyor.")
    if "D_in_m" in inputs:
        if inputs["D_in_m"] <= 0.0:
            raise ValueError("İç çap pozitif olmalıdır.")
        if inputs["t_m"] <= 0.0:
            raise ValueError("Et kalınlığı pozitif olmalıdır.")
        if inputs["D_in_m"] < 2.0 * inputs["t_m"]:
            raise ValueError("İç çap, et kalınlığının iki katından büyük olmalıdır.")

    inputs["fire_case"] = fire_case_enabled
    if fire_case_enabled:
        mawp_val = get_val(FIELD_MAWP)
        if mawp_val is None:
            raise ValueError("API 521 fire case için MAWP / Dizayn Basıncı zorunludur.")
        design_pressure_pa = converter.convert_pressure(mawp_val, get_unit(FIELD_MAWP))
        fire_factor_raw = app.fire_case_factor_entry.get().strip() if hasattr(app, "fire_case_factor_entry") else "1.0"
        fire_factor = float(fire_factor_raw) if fire_factor_raw else 1.0
        fire_scenario = (
            app.fire_case_scenario_combo.get()
            if hasattr(app, "fire_case_scenario_combo")
            else "Adequate drainage + firefighting"
        )
        d_outer_m = None
        if "D_in_m" in inputs and "t_m" in inputs:
            d_outer_m = inputs["D_in_m"] + 2.0 * inputs["t_m"]

        fire_case_result = fire_case_builder(
            design_pressure_pa=design_pressure_pa,
            outer_diameter_m=d_outer_m,
            length_m=inputs.get("L_m"),
            environment_factor=fire_factor,
            scenario=fire_scenario,
        )
        inputs["design_pressure_pa"] = design_pressure_pa
        inputs["fire_case_scenario"] = fire_scenario
        inputs["fire_environment_factor"] = fire_factor
        inputs["fire_case_target_pressure_pa"] = fire_case_result.target_pressure_pa
        inputs["fire_case_target_time_s"] = fire_case_result.target_time_s
        inputs["fire_heat_input_w"] = fire_case_result.heat_input_w
        inputs["fire_wetted_area_m2"] = fire_case_result.wetted_area_m2
        inputs["fire_case_warnings"] = list(fire_case_result.warnings)
        inputs["fire_coefficient_si"] = fire_case_result.coefficient_si
        inputs["p_target_blowdown_pa"] = fire_case_result.target_pressure_pa
        inputs["t_target_sec"] = fire_case_result.target_time_s

        target_pressure_unit = get_unit(FIELD_TARGET_PRESSURE)
        target_pressure_display = converter.convert_pressure_from_pa(
            fire_case_result.target_pressure_pa,
            target_pressure_unit,
        )
        target_pressure_key = _resolve_mapping_key(app.entries, FIELD_TARGET_PRESSURE)
        target_time_key = _resolve_mapping_key(app.entries, FIELD_TARGET_TIME)
        _set_entry_value(app.entries[target_pressure_key], f"{target_pressure_display:.3f}")
        _set_entry_value(app.entries[target_time_key], f"{fire_case_result.target_time_s:.0f}")
    else:
        inputs["p_target_blowdown_pa"] = converter.convert_pressure(pt_val, get_unit(FIELD_TARGET_PRESSURE))
        inputs["t_target_sec"] = tt_val
    if inputs.get("t_target_sec") is not None and inputs["t_target_sec"] <= 0.0:
        raise ValueError("Hedef blowdown süresi pozitif olmalıdır.")
    if inputs["p_target_blowdown_pa"] <= p_atm * 0.001:
        raise ValueError("Hedef basınç pozitif bir değer olmalıdır.")

    if inputs["p_target_blowdown_pa"] >= inputs["p0_pa"]:
        raise ValueError("Hedef basınç, başlangıç basıncından küçük olmalıdır.")

    v_count_val = get_val(FIELD_VALVE_COUNT)
    inputs["valve_count"] = int(v_count_val) if v_count_val is not None else 1
    if inputs["valve_count"] < 1:
        raise ValueError("Vana sayısı en az 1 olmalıdır.")

    pb_val = get_val(FIELD_BACKPRESSURE)
    inputs["p_downstream"] = (
        converter.convert_pressure(pb_val, get_unit(FIELD_BACKPRESSURE))
        if pb_val is not None
        else p_atm
    )
    inputs["Cd_valve"] = get_val(FIELD_VALVE_CD) or 0.975
    inputs["Kb"] = get_val(FIELD_BACKPRESSURE_KB) or 1.0
    if inputs["Cd_valve"] <= 0.0 or inputs["Cd_valve"] > 1.0:
        raise ValueError("Discharge katsayısı (Cd) 0 ile 1 arasında olmalıdır.")

    if inputs["solver_engine"] == "HydDown" and any(key not in inputs for key in ("D_in_m", "L_m", "t_m")):
        raise ValueError("HydDown motoru için geometrik giriş zorunludur. İç çap, uzunluk ve et kalınlığı girilmelidir.")
    if inputs["solver_engine"] == segmented_engine_name and any(key not in inputs for key in ("D_in_m", "L_m", "t_m")):
        raise ValueError("Segmentli pipeline motoru için iç çap, uzunluk ve et kalınlığı zorunludur.")
    if inputs["solver_engine"] == segmented_engine_name and "Boru" not in inputs["system_type"]:
        raise ValueError("Segmentli pipeline motoru yalnız pipeline sistemi için kullanılabilir.")

    return inputs
