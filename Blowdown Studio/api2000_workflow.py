from __future__ import annotations

from dataclasses import dataclass

from api2000_engine import calculate_api2000_emergency_venting, calculate_api2000_venting


@dataclass
class API2000WorkflowResult:
    normal_result: dict
    emergency_result: dict | None
    summary_text: str


def latitude_band_to_value(latitude_band: str) -> int:
    if "Below" in latitude_band:
        return 30
    if "42-58" in latitude_band:
        return 50
    return 65


def build_api2000_summary_text(normal_result: dict, is_volatile: bool, emergency_result: dict | None = None) -> str:
    lines = [
        "API 2000 TANK HAVALANDIRMA RAPORU",
        "=================================",
        "",
        "[1] Normal Havalandırma Sonuçları",
        f"C faktörü                    : {normal_result['c_factor_used']:.3f}",
        f"Uçucu akışkan                : {'Evet' if is_volatile else 'Hayır'}",
        f"Isıl inbreathing             : {normal_result['thermal_inbreathing']:,.1f} Nm3/h",
        f"Isıl outbreathing            : {normal_result['thermal_outbreathing']:,.1f} Nm3/h",
        f"Pompa çıkış bileşeni         : {normal_result['pump_out_component']:,.1f} Nm3/h",
        f"Pompa giriş bileşeni         : {normal_result['pump_in_component']:,.1f} Nm3/h",
        f"Toplam vacuum ihtiyacı       : {normal_result['total_inbreathing']:,.1f} Nm3/h",
        f"Toplam pressure ihtiyacı     : {normal_result['total_outbreathing']:,.1f} Nm3/h",
    ]

    if emergency_result is not None:
        lines.extend(
            [
                "",
                "[2] Emergency Venting / Fire Case Screening",
                f"Senaryo                      : {emergency_result['drainage_condition']}",
                f"Wetted area                  : {emergency_result['wetted_area_m2']:,.2f} m2",
                f"Isı girdisi                  : {emergency_result['heat_input_w'] / 1000.0:,.1f} kW",
                f"Buharlaşma debisi            : {emergency_result['vapor_generation_kg_h']:,.1f} kg/h",
                f"Emergency venting            : {emergency_result['emergency_venting_nm3_h']:,.1f} Nm3/h",
            ]
        )

    return "\n".join(lines)


def run_api2000_workflow(
    *,
    tank_volume_m3: float,
    latitude_band: str,
    is_volatile: bool,
    pump_in_m3h: float,
    pump_out_m3h: float,
    insulation_factor: float,
    emergency_enabled: bool = False,
    emergency_wetted_area_m2: float | None = None,
    latent_heat_kj_kg: float | None = None,
    vapor_mw_kg_kmol: float | None = None,
    fire_factor: float | None = None,
    drainage_condition: str = "Adequate drainage + firefighting",
) -> API2000WorkflowResult:
    latitude = latitude_band_to_value(latitude_band)
    normal_result = calculate_api2000_venting(
        tank_volume_m3,
        latitude,
        is_volatile,
        pump_in_m3h,
        pump_out_m3h,
        insulation_factor,
    )

    emergency_result = None
    if emergency_enabled:
        if emergency_wetted_area_m2 is None or latent_heat_kj_kg is None or vapor_mw_kg_kmol is None or fire_factor is None:
            raise ValueError("Emergency venting aktifken gerekli acil durum girdileri eksik.")
        emergency_result = calculate_api2000_emergency_venting(
            wetted_area_m2=emergency_wetted_area_m2,
            latent_heat_kj_kg=latent_heat_kj_kg,
            vapor_mw_kg_kmol=vapor_mw_kg_kmol,
            fire_factor=fire_factor,
            drainage_condition=drainage_condition,
        )

    summary_text = build_api2000_summary_text(normal_result, is_volatile, emergency_result)
    return API2000WorkflowResult(
        normal_result=normal_result,
        emergency_result=emergency_result,
        summary_text=summary_text,
    )
