from __future__ import annotations

from dataclasses import dataclass


FIELD_INNER_DIAMETER = "İç Çap"
FIELD_LENGTH = "Uzunluk"
FIELD_THICKNESS = "Et Kalınlığı"
FIELD_TOTAL_VOLUME = "Toplam Hacim"
FIELD_REQUIRED_FLOW = "Gerekli Tahliye Debisi"
FIELD_START_PRESSURE = "Başlangıç Basıncı"
FIELD_MAWP = "MAWP / Dizayn Basıncı"
FIELD_OVERPRESSURE = "İzin Verilen Overpressure (%)"
FIELD_START_TEMPERATURE = "Başlangıç Sıcaklığı"
FIELD_TARGET_TIME = "Hedef Blowdown Süresi"
FIELD_TARGET_PRESSURE = "Hedef Blowdown Basıncı"
FIELD_VALVE_COUNT = "Vana Sayısı"
FIELD_VALVE_CD = "Valve Discharge Coeff (Cd)"
FIELD_PSV_KD = "PSV Certified Kd"
FIELD_BACKPRESSURE = "Backpressure (Karşı Basınç)"
FIELD_BACKPRESSURE_KB = "Backpressure Coeff (Kb)"
FIELD_REQUIRED_TRIM_CODE = "Required Trim Code"
FIELD_REQUIRED_CODE_STAMP = "Required Code Stamp"
FIELD_REQUIRED_BODY_MATERIAL = "Required Body Material"
FIELD_REQUIRED_TRIM_MATERIAL = "Required Trim Material"
FIELD_REQUIRED_INLET_CLASS = "Required Inlet Rating Class"
FIELD_REQUIRED_OUTLET_CLASS = "Required Outlet Rating Class"


@dataclass(frozen=True)
class ServiceFieldConfig:
    field_labels: dict[str, str]
    flow_units: list[str]
    flow_default_unit: str
    kd_default_value: str | None


@dataclass(frozen=True)
class ModeUIState:
    visible_fields: tuple[str, ...]
    hidden_fields: tuple[str, ...]
    field_labels: dict[str, str]
    helper_text: str
    show_sys_type: bool
    show_engine_options: bool
    show_fire_case_frame: bool
    show_psv_options: bool
    show_ht_check: bool
    show_abort: bool
    show_progress: bool
    run_button_text: str
    placeholder_mode: str


def build_psv_service_field_config(service_type: str, current_kd_value: str) -> ServiceFieldConfig:
    if service_type == "Gas/Vapor":
        kd_default = None
        if current_kd_value.strip() in {"", "0.650"}:
            kd_default = "0.975"
        return ServiceFieldConfig(
            field_labels={
                FIELD_REQUIRED_FLOW: "Gerekli Tahliye Debisi:",
                FIELD_PSV_KD: "Sertifikalı Kd (API 520):",
                FIELD_BACKPRESSURE_KB: "Backpressure Katsayısı (Kb):",
            },
            flow_units=["kg/h", "lb/h", "kg/s", "Nm3/h", "Sm3/h", "SCFM", "MMSCFD"],
            flow_default_unit="kg/h",
            kd_default_value=kd_default,
        )

    if service_type == "Steam":
        return ServiceFieldConfig(
            field_labels={
                FIELD_REQUIRED_FLOW: "Steam Tahliye Debisi:",
                FIELD_PSV_KD: "Sertifikalı Kd (Steam):",
                FIELD_BACKPRESSURE_KB: "Backpressure Katsayısı (Kb):",
            },
            flow_units=["kg/h", "lb/h", "kg/s"],
            flow_default_unit="kg/h",
            kd_default_value=None,
        )

    kd_default = None
    if current_kd_value.strip() in {"", "0.975"}:
        kd_default = "0.650"
    return ServiceFieldConfig(
        field_labels={
            FIELD_REQUIRED_FLOW: "Sıvı Tahliye Debisi:",
            FIELD_PSV_KD: "Sertifikalı Kd (Liquid):",
            FIELD_BACKPRESSURE_KB: "Backpressure Katsayısı (Kw):",
        },
        flow_units=["kg/h", "lb/h", "kg/s", "L/min", "m3/h", "gpm"],
        flow_default_unit="kg/h",
        kd_default_value=kd_default,
    )



def build_mode_ui_state(*, mode: str, fire_case_enabled: bool, engine_name: str, app_version: str) -> ModeUIState:
    vendor_filter_fields = (
        FIELD_REQUIRED_TRIM_CODE,
        FIELD_REQUIRED_CODE_STAMP,
        FIELD_REQUIRED_BODY_MATERIAL,
        FIELD_REQUIRED_TRIM_MATERIAL,
        FIELD_REQUIRED_INLET_CLASS,
        FIELD_REQUIRED_OUTLET_CLASS,
    )

    if "Blowdown" in mode:
        visible_fields = [
            FIELD_INNER_DIAMETER,
            FIELD_LENGTH,
            FIELD_THICKNESS,
            FIELD_TOTAL_VOLUME,
            FIELD_START_PRESSURE,
            FIELD_START_TEMPERATURE,
            FIELD_TARGET_TIME,
            FIELD_TARGET_PRESSURE,
            FIELD_VALVE_COUNT,
            FIELD_VALVE_CD,
            FIELD_BACKPRESSURE,
            FIELD_BACKPRESSURE_KB,
        ]
        if fire_case_enabled:
            visible_fields.append(FIELD_MAWP)

        if fire_case_enabled:
            run_button_text = f"{app_version} API 521 Fire Case Analizini Başlat"
        elif engine_name == "Segmented Pipeline":
            run_button_text = f"{app_version} Segmentli Pipeline Analizini Başlat"
        elif engine_name == "Two-Phase Screening":
            run_button_text = f"{app_version} Two-Phase Screening Analizini Başlat"
        else:
            run_button_text = f"{app_version} Blowdown Analizini Başlat"

        hidden_fields = (
            (FIELD_REQUIRED_FLOW, FIELD_OVERPRESSURE, FIELD_PSV_KD) + vendor_filter_fields
            if fire_case_enabled
            else (FIELD_REQUIRED_FLOW, FIELD_MAWP, FIELD_OVERPRESSURE, FIELD_PSV_KD) + vendor_filter_fields
        )

        return ModeUIState(
            visible_fields=tuple(visible_fields),
            hidden_fields=hidden_fields,
            field_labels={
                FIELD_START_PRESSURE: "Başlangıç Basıncı:",
                FIELD_START_TEMPERATURE: "Başlangıç Sıcaklığı:",
                FIELD_VALVE_CD: "Blowdown Deşarj Katsayısı (Cd):",
                FIELD_BACKPRESSURE: "Downstream / Karşı Basınç:",
                FIELD_BACKPRESSURE_KB: "Backpressure Katsayısı (Kb):",
                FIELD_MAWP: "Fire Case Design Pressure:",
            },
            helper_text=(
                "Blowdown modu, hedef basınca iniş için zamana bağlı transient çözüm yapar. "
                "Başlangıç basıncı, sıcaklık, geometri ve hedef süreyi girin. Fire case aktifse hedef koşullar otomatik türetilir."
            ),
            show_sys_type=True,
            show_engine_options=True,
            show_fire_case_frame=True,
            show_psv_options=False,
            show_ht_check=True,
            show_abort=True,
            show_progress=True,
            run_button_text=run_button_text,
            placeholder_mode="Blowdown",
        )

    return ModeUIState(
        visible_fields=(
            FIELD_REQUIRED_FLOW,
            FIELD_START_PRESSURE,
            FIELD_START_TEMPERATURE,
            FIELD_MAWP,
            FIELD_OVERPRESSURE,
            FIELD_VALVE_COUNT,
            FIELD_PSV_KD,
            FIELD_BACKPRESSURE,
            FIELD_BACKPRESSURE_KB,
            *vendor_filter_fields,
        ),
        hidden_fields=(
            FIELD_INNER_DIAMETER,
            FIELD_LENGTH,
            FIELD_THICKNESS,
            FIELD_TOTAL_VOLUME,
            FIELD_TARGET_TIME,
            FIELD_TARGET_PRESSURE,
            FIELD_VALVE_CD,
        ),
        field_labels={
            FIELD_START_PRESSURE: "Set Pressure:",
            FIELD_START_TEMPERATURE: "Relieving Temperature:",
            FIELD_BACKPRESSURE: "Toplam Backpressure:",
            FIELD_MAWP: "MAWP / Dizayn Basıncı:",
        },
        helper_text=(
            "PSV modu, API 520-1 ön boyutlandırma ve vendor screening yapar. "
            "Set pressure, relieving temperature, debi ve gerekirse exact vendor filtrelerini girin."
        ),
        show_sys_type=False,
        show_engine_options=False,
        show_fire_case_frame=False,
        show_psv_options=True,
        show_ht_check=False,
        show_abort=False,
        show_progress=False,
        run_button_text="PSV Ön Boyutlandırmayı Hesapla (API 520-1)",
        placeholder_mode="PSV",
    )
