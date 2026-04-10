from __future__ import annotations

from datetime import datetime
from typing import Any

import CoolProp.CoolProp as CP
import numpy as np

from acoustic_screening import (
    calculate_acoustic_velocity,
    calculate_aiv_vibration,
    calculate_discharge_velocity,
    check_acoustic_fatigue,
)
from api521_discharge_piping import calculate_discharge_piping_loss
from blowdown_reporting import BlowdownReportBundle
from constants import P_ATM
from hyddown_adapter import find_hyddown_blowdown_area, run_hyddown_blowdown_simulation
from native_blowdown_engine import (
    NATIVE_ENGINE_NAME,
    calculate_reaction_force,
    parse_outlet_diameter_mm,
    find_native_blowdown_area,
    run_native_blowdown_simulation,
)
from segmented_pipeline import (
    SEGMENTED_ENGINE_NAME,
    find_segmented_pipeline_blowdown_area,
    run_segmented_pipeline_blowdown_simulation,
)
from two_phase_flow import find_two_phase_blowdown_area, run_two_phase_blowdown_simulation


TWO_PHASE_ENGINE_NAME = "Two-Phase Screening"


def size_blowdown_area(engine_name, inputs, progress_callback=None, abort_flag=None):
    if engine_name == "HydDown":
        return find_hyddown_blowdown_area(inputs, progress_callback, abort_flag)
    if engine_name == SEGMENTED_ENGINE_NAME:
        return find_segmented_pipeline_blowdown_area(inputs, progress_callback, abort_flag)
    if engine_name == TWO_PHASE_ENGINE_NAME:
        return find_two_phase_blowdown_area(inputs, progress_callback, abort_flag)
    return find_native_blowdown_area(inputs, progress_callback, abort_flag)


def run_blowdown_engine(engine_name, inputs, total_selected_area, progress_callback=None, abort_flag=None):
    if engine_name == "HydDown":
        return run_hyddown_blowdown_simulation(inputs, total_selected_area, progress_callback, abort_flag, silent=False)
    if engine_name == SEGMENTED_ENGINE_NAME:
        return run_segmented_pipeline_blowdown_simulation(inputs, total_selected_area, progress_callback, abort_flag, silent=False)
    if engine_name == TWO_PHASE_ENGINE_NAME:
        return run_two_phase_blowdown_simulation(inputs, total_selected_area, progress_callback=progress_callback, abort_flag=abort_flag, silent=False)
    return run_native_blowdown_simulation(inputs, total_selected_area, progress_callback, abort_flag, silent=False)


def select_standard_valve(valve_data, required_area_per_valve_mm2):
    selected_valve = next((v for v in valve_data if v.area_mm2 >= required_area_per_valve_mm2), None)
    fallback_used = False
    if not selected_valve:
        selected_valve = valve_data[-1]
        fallback_used = True
    return selected_valve, fallback_used


def build_blowdown_report(
    *,
    sim_df,
    inputs,
    engine_name,
    selected_valve,
    valve_type_label,
    valve_type_description,
    valve_count,
    required_area_m2,
    total_selected_area_m2,
) -> dict[str, Any]:
    generated_on = datetime.now().strftime("%d.%m.%Y")
    software_version = "Blowdown Studio v2.4.1"
    screening_inputs = dict(inputs)
    blowdown_warnings = list(sim_df.attrs.get("warnings", []))
    blowdown_warnings.extend(screening_inputs.get("fire_case_warnings", []))

    sim_time = sim_df.attrs.get("time_to_target", sim_df["t"].iloc[-1])
    target_time = screening_inputs["t_target_sec"]
    margin = ((total_selected_area_m2 / required_area_m2) - 1.0) * 100.0
    verdict = "PASS" if sim_time <= target_time else "FAIL"
    operator = "<=" if sim_time <= target_time else ">"

    two_phase_summary_lines: list[str] = []
    segmented_summary_lines: list[str] = []
    fire_case_summary_lines: list[str] = []

    if engine_name == TWO_PHASE_ENGINE_NAME and "quality" in sim_df.columns:
        q_min = float(np.min(np.asarray(sim_df["quality"], dtype=float)))
        q_max = float(np.max(np.asarray(sim_df["quality"], dtype=float)))
        dominant_regime = "N/A"
        if "flow_regime" in sim_df.columns and len(sim_df["flow_regime"]) > 0:
            dominant_regime = str(sim_df["flow_regime"].mode().iloc[0])
        two_phase_summary_lines = [
            "",
            "[Ek Screening] Two-Phase Summary",
            f"Quality min / max             : {q_min:.3f} / {q_max:.3f}",
            f"Dominant flow regime          : {dominant_regime}",
            "Method note                  : Bu motor screening-seviyesi homogeneous-equilibrium yaklaşımı kullanır.",
        ]
        blowdown_warnings.append(
            "Two-Phase Screening motoru, tam API 520/521 two-phase sizing veya validated HEM/DI cozumleri yerine on screening amaclidir."
        )
        if q_min == 1.0 and q_max == 1.0:
            blowdown_warnings.append(
                "Two-Phase Screening sonucu bu vakada fiilen tek-faz gaz davranisi gosterdi; iki-faz olusumu saptanmadi."
            )

    if engine_name == SEGMENTED_ENGINE_NAME:
        segmented_summary_lines = [
            "",
            "[Ek Screening] Segmented Pipeline",
            f"Segment count                 : {int(screening_inputs.get('segment_count', 0))}",
            f"Friction model                : {sim_df.attrs.get('friction_model', 'N/A')}",
            f"Upstream final pressure       : {float(sim_df['p_upstream'].iloc[-1]) / 1e5:.3f} bara",
            f"Terminal final pressure       : {float(sim_df['p_terminal'].iloc[-1]) / 1e5:.3f} bara",
            f"Average final pressure        : {float(sim_df['p_avg'].iloc[-1]) / 1e5:.3f} bara",
        ]
        if "segment_re" in sim_df.columns:
            segmented_summary_lines.append(f"Average intersegment Re       : {float(sim_df['segment_re'].iloc[-1]):.3e}")
        if "segment_f" in sim_df.columns:
            segmented_summary_lines.append(f"Average Darcy friction f      : {float(sim_df['segment_f'].iloc[-1]):.4f}")

    if screening_inputs.get("fire_case"):
        fire_case_summary_lines = [
            "",
            "[API 521 Fire Case Screening]",
            f"Design pressure              : {screening_inputs['design_pressure_pa'] / 1e5:.3f} bara",
            f"Target pressure              : {screening_inputs['fire_case_target_pressure_pa'] / 1e5:.3f} bara",
            f"Target time                  : {screening_inputs['fire_case_target_time_s']:.0f} s",
            f"Scenario                     : {screening_inputs.get('fire_case_scenario', 'N/A')}",
            f"Environment factor (F)       : {screening_inputs.get('fire_environment_factor', 1.0):.3f}",
        ]
        if screening_inputs.get("fire_wetted_area_m2") is not None:
            fire_case_summary_lines.append(
                f"Estimated wetted area        : {screening_inputs['fire_wetted_area_m2']:.2f} m2"
            )
        if screening_inputs.get("fire_heat_input_w") is not None:
            fire_case_summary_lines.append(
                f"Estimated heat input         : {screening_inputs['fire_heat_input_w'] / 1000.0:,.1f} kW"
            )

    pipe_d_mm = parse_outlet_diameter_mm(selected_valve.size_dn)
    screening_inputs.setdefault("pipe_diameter_mm", pipe_d_mm)
    screening_inputs.setdefault("pipe_length_m", 5.0)
    screening_inputs.setdefault("elbow_count", 2)
    screening_inputs.setdefault("tee_count", 0)
    screening_inputs.setdefault("globe_valve_count", 0)
    screening_inputs.setdefault("check_valve_count", 0)
    screening_inputs.setdefault("butterfly_valve_count", 0)

    discharge_summary_lines: list[str] = []
    acoustic_summary_lines: list[str] = []
    peak_mach = None

    try:
        peak_mdot_kg_s = float(np.max(np.asarray(sim_df["mdot_kg_s"], dtype=float)))
        initial_pressure_pa = float(sim_df["p_sys"].iloc[0])
        initial_temperature_k = float(sim_df["T_sys"].iloc[0])
        initial_density_kg_m3 = float(sim_df["rho_g"].iloc[0])

        state_screen = CP.AbstractState("HEOS", "&".join(screening_inputs["composition"].keys()))
        state_screen.set_mole_fractions(list(screening_inputs["composition"].values()))
        state_screen.update(CP.PT_INPUTS, initial_pressure_pa, initial_temperature_k)
        gas_viscosity_pa_s = state_screen.viscosity()
        acoustic_velocity_m_s = calculate_acoustic_velocity(
            screening_inputs["composition"],
            initial_pressure_pa,
            initial_temperature_k,
        )
        discharge_velocity_m_s = calculate_discharge_velocity(
            peak_mdot_kg_s,
            initial_density_kg_m3,
            pipe_d_mm,
        )

        piping_loss = calculate_discharge_piping_loss(
            pipe_length_m=screening_inputs["pipe_length_m"],
            pipe_diameter_mm=pipe_d_mm,
            elbow_count=screening_inputs["elbow_count"],
            tee_count=screening_inputs["tee_count"],
            globe_valve_count=screening_inputs["globe_valve_count"],
            check_valve_count=screening_inputs["check_valve_count"],
            butterfly_valve_count=screening_inputs["butterfly_valve_count"],
            mass_flow_kg_s=peak_mdot_kg_s,
            gas_density_kg_m3=initial_density_kg_m3,
            gas_viscosity_pa_s=gas_viscosity_pa_s,
        )
        screening_inputs["discharge_piping"] = piping_loss
        screening_inputs["discharge_K"] = piping_loss["total_K"]
        screening_inputs["acoustic_velocity"] = acoustic_velocity_m_s
        screening_inputs["discharge_velocity"] = discharge_velocity_m_s

        discharge_area_m2 = np.pi * ((pipe_d_mm / 1000.0) / 2.0) ** 2
        sim_df["mach_number"] = np.asarray(sim_df["mdot_kg_s"], dtype=float) / (
            np.maximum(np.asarray(sim_df["rho_g"], dtype=float), 1e-12)
            * max(discharge_area_m2, 1e-12)
            * max(acoustic_velocity_m_s, 1e-12)
        )
        peak_mach = float(np.max(np.asarray(sim_df["mach_number"], dtype=float)))
        acoustic_result = check_acoustic_fatigue(
            discharge_velocity_m_s=discharge_velocity_m_s,
            acoustic_velocity_m_s=acoustic_velocity_m_s,
            pipe_diameter_mm=pipe_d_mm,
            gas_density_kg_m3=initial_density_kg_m3,
        )
        aiv_result = calculate_aiv_vibration(
            mach_number=peak_mach,
            pipe_diameter_mm=pipe_d_mm,
        )
        screening_inputs["acoustic_screening"] = acoustic_result
        screening_inputs["aiv_screening"] = aiv_result

        discharge_summary_lines = [
            "",
            "[Ek Screening] Discharge Piping",
            f"Assumed discharge line         : {screening_inputs['pipe_length_m']:.1f} m, DN{pipe_d_mm:.0f}, {screening_inputs['elbow_count']} elbow",
            f"Reynolds sayisi               : {piping_loss['reynolds_number']:.3e}",
            f"Darcy friction factor         : {piping_loss['friction_factor']:.4f}",
            f"Toplam K                      : {piping_loss['total_K']:.3f}",
            f"Equivalent length             : {piping_loss['equivalent_length_m']:.2f} m",
        ]
        acoustic_summary_lines = [
            "",
            "[Ek Screening] Acoustic / Mach",
            f"Peak discharge velocity       : {discharge_velocity_m_s:.2f} m/s",
            f"Acoustic velocity             : {acoustic_velocity_m_s:.2f} m/s",
            f"Peak Mach screening           : {peak_mach:.3f}",
            f"Jet mechanical power          : {float(acoustic_result['jet_mechanical_power_w']) / 1000.0:.2f} kW",
            f"Estimated sound power level   : {float(acoustic_result['sound_power_level_db']):.1f} dB ref 1pW",
            f"Acoustic fatigue risk         : {acoustic_result['fatigue_risk']}",
            f"AIV screening index           : {float(aiv_result['aiv_screening_index']):.3f}",
            f"AIV screening risk            : {aiv_result['aiv_risk']}",
        ]
        if acoustic_result["fatigue_risk"] in {"HIGH", "CRITICAL"}:
            blowdown_warnings.append(
                f"Acoustic screening: {acoustic_result['fatigue_risk']} risk. Estimated PWL = {float(acoustic_result['sound_power_level_db']):.1f} dB; ayrintili API 521 / EI acoustic fatigue analizi gerekir."
            )
        elif acoustic_result["fatigue_risk"] == "MODERATE":
            blowdown_warnings.append(
                f"Acoustic screening: MODERATE risk. Estimated PWL = {float(acoustic_result['sound_power_level_db']):.1f} dB; discharge geometry ve branch detaylari gozden gecirilmeli."
            )
        if aiv_result["aiv_risk"] in {"HIGH", "CRITICAL"}:
            blowdown_warnings.append(
                f"AIV screening: {aiv_result['aiv_risk']} risk. Screening index = {float(aiv_result['aiv_screening_index']):.3f}; baglanti/branch detaylari ve destekleme kontrol edilmeli."
            )
        if aiv_result["resonance_risk"]:
            blowdown_warnings.append(
                f"AIV screening: tahmini dogal frekans ({float(aiv_result['natural_frequency_hz']):.0f} Hz) screening frekansina yakin; rezonans riski dusunulmeli."
            )
    except Exception as exc:
        blowdown_warnings.append(
            f"Discharge/acoustic screening tamamlanamadi; yalniz ana blowdown sonucu gosteriliyor. Ayrinti: {exc}"
        )

    pressure_series_bara = np.asarray(sim_df["p_sys"], dtype=float) / 1e5
    temperature_series_c = np.asarray(sim_df["T_sys"], dtype=float) - 273.15
    wall_temperature_series_c = np.asarray(sim_df["T_wall"], dtype=float) - 273.15
    mass_series_kg = np.asarray(sim_df["m_sys"], dtype=float)
    density_series = np.asarray(sim_df["rho_g"], dtype=float)
    h_in_series = np.asarray(sim_df["h_in"], dtype=float)
    mdot_series_kg_h = np.asarray(sim_df["mdot_kg_s"], dtype=float) * 3600.0
    volumetric_flow_m3_h = mdot_series_kg_h / np.maximum(density_series, 1e-12)

    initial_pressure_bara = float(pressure_series_bara[0])
    final_pressure_bara = float(pressure_series_bara[-1])
    min_pressure_bara = float(np.min(pressure_series_bara))
    target_pressure_bara = float(screening_inputs["p_target_blowdown_pa"] / 1e5)

    initial_temperature_c = float(temperature_series_c[0])
    final_temperature_c = float(temperature_series_c[-1])
    min_temperature_c = float(np.min(temperature_series_c))
    initial_wall_temperature_c = float(wall_temperature_series_c[0])
    final_wall_temperature_c = float(wall_temperature_series_c[-1])
    min_wall_temperature_c = float(np.min(wall_temperature_series_c))

    initial_mass_kg = float(mass_series_kg[0])
    final_mass_kg = float(mass_series_kg[-1])
    discharged_mass_kg = initial_mass_kg - final_mass_kg
    initial_density = float(density_series[0])
    final_density = float(density_series[-1])

    max_mass_flow_kg_h = float(np.max(mdot_series_kg_h))
    final_mass_flow_kg_h = float(mdot_series_kg_h[-1])
    max_volumetric_flow_m3_h = float(np.max(volumetric_flow_m3_h))
    final_volumetric_flow_m3_h = float(volumetric_flow_m3_h[-1])
    min_h_in = float(np.min(h_in_series))
    avg_h_in = float(np.mean(h_in_series))
    max_h_in = float(np.max(h_in_series))
    composition_lines = [
        f"  - {name}: {fraction * 100.0:.3f}%"
        for name, fraction in sorted(screening_inputs["composition"].items())
    ]

    report_lines = [
        "BLOWDOWN ANALİZ RAPORU",
        "======================",
        f"Tarih                         : {generated_on}",
        f"Yazılım                       : {software_version}",
        "",
        "[1] Analiz Özeti",
        f"Hesap motoru                  : {engine_name}",
        f"Sistem tipi                   : {screening_inputs.get('system_type', 'N/A')}",
        f"Vana standardı                : {valve_type_description}",
        f"Sonuç                         : {verdict}",
        f"Gerçekleşen süre              : {sim_time:.1f} s",
        f"Hedef süre                    : {target_time:.1f} s",
        f"Süre karşılaştırması          : {sim_time:.1f} s {operator} {target_time:.1f} s",
        "Gaz kompozisyonu              :",
        *composition_lines,
        "",
        "[2] Vana ve Alan Seçimi",
        f"Vana sayısı                   : {valve_count}",
        f"Seçilen vana                  : {valve_type_label}",
        f"Tek vana alanı                : {selected_valve.area_mm2:,.1f} mm2",
        f"Toplam gerekli alan           : {required_area_m2:.6e} m2",
        f"Toplam seçilen alan           : {total_selected_area_m2:.6e} m2",
        f"Alan marjı                    : {margin:.1f} %",
        "",
        "[3] Basınç Sonuçları",
        f"Başlangıç basıncı             : {initial_pressure_bara:.3f} bara",
        f"Hedef basınç                  : {target_pressure_bara:.3f} bara",
        f"Son basınç                    : {final_pressure_bara:.3f} bara",
        f"Minimum basınç                : {min_pressure_bara:.3f} bara",
        "",
        "[4] Sıcaklık Sonuçları",
        f"Başlangıç gaz sıcaklığı       : {initial_temperature_c:.2f} °C",
        f"Son gaz sıcaklığı             : {final_temperature_c:.2f} °C",
        f"Minimum gaz sıcaklığı         : {min_temperature_c:.2f} °C",
        f"Başlangıç duvar sıcaklığı     : {initial_wall_temperature_c:.2f} °C",
        f"Son duvar sıcaklığı           : {final_wall_temperature_c:.2f} °C",
        f"Minimum duvar sıcaklığı       : {min_wall_temperature_c:.2f} °C",
        "",
        "[5] Kütle ve Debi Sonuçları",
        f"Başlangıç sistem kütlesi      : {initial_mass_kg:,.3f} kg",
        f"Son sistem kütlesi            : {final_mass_kg:,.3f} kg",
        f"Toplam tahliye edilen kütle   : {discharged_mass_kg:,.3f} kg",
        f"Başlangıç yoğunluk            : {initial_density:,.3f} kg/m3",
        f"Son yoğunluk                  : {final_density:,.3f} kg/m3",
        f"Maksimum kütlesel debi        : {max_mass_flow_kg_h:,.2f} kg/h",
        f"Son kütlesel debi             : {final_mass_flow_kg_h:,.2f} kg/h",
        f"Maksimum hacimsel debi        : {max_volumetric_flow_m3_h:,.2f} m3/h",
        f"Son hacimsel debi             : {final_volumetric_flow_m3_h:,.2f} m3/h",
        "",
        "[6] Isıl Sonuçlar",
        f"Minimum iç ısı transfer kats. : {min_h_in:,.2f} W/m2K",
        f"Ortalama iç ısı transfer kats.: {avg_h_in:,.2f} W/m2K",
        f"Maksimum iç ısı transfer kats.: {max_h_in:,.2f} W/m2K",
    ]
    if fire_case_summary_lines:
        report_lines.extend(fire_case_summary_lines)
    if segmented_summary_lines:
        report_lines.extend(segmented_summary_lines)
    if two_phase_summary_lines:
        report_lines.extend(two_phase_summary_lines)
    if discharge_summary_lines:
        report_lines.extend(discharge_summary_lines)
    if acoustic_summary_lines:
        report_lines.extend(acoustic_summary_lines)
    if blowdown_warnings:
        report_lines.extend(["", "[Uyarılar]"])
        report_lines.extend(f"- {item}" for item in blowdown_warnings)

    summary_rows = [
        ("Tarih", generated_on),
        ("Yazılım", software_version),
        ("Hesap Motoru", engine_name),
        ("Sistem Tipi", str(screening_inputs.get("system_type", "N/A"))),
        ("Sonuç", verdict),
        ("Gerçekleşen Süre (s)", f"{sim_time:.1f}"),
        ("Hedef Süre (s)", f"{target_time:.1f}"),
        ("Vana Standardı", valve_type_description),
        ("Seçilen Vana", valve_type_label),
        ("Vana Sayısı", f"{valve_count}"),
        ("Tek Vana Alanı (mm2)", f"{selected_valve.area_mm2:,.1f}"),
        ("Toplam Gerekli Alan (m2)", f"{required_area_m2:.6e}"),
        ("Toplam Seçilen Alan (m2)", f"{total_selected_area_m2:.6e}"),
        ("Alan Marjı (%)", f"{margin:.1f}"),
        ("Başlangıç Basıncı (bara)", f"{initial_pressure_bara:.3f}"),
        ("Hedef Basınç (bara)", f"{target_pressure_bara:.3f}"),
        ("Son Basınç (bara)", f"{final_pressure_bara:.3f}"),
        ("Minimum Basınç (bara)", f"{min_pressure_bara:.3f}"),
        ("Başlangıç Gaz Sıcaklığı (°C)", f"{initial_temperature_c:.2f}"),
        ("Son Gaz Sıcaklığı (°C)", f"{final_temperature_c:.2f}"),
        ("Minimum Gaz Sıcaklığı (°C)", f"{min_temperature_c:.2f}"),
        ("Başlangıç Duvar Sıcaklığı (°C)", f"{initial_wall_temperature_c:.2f}"),
        ("Son Duvar Sıcaklığı (°C)", f"{final_wall_temperature_c:.2f}"),
        ("Minimum Duvar Sıcaklığı (°C)", f"{min_wall_temperature_c:.2f}"),
        ("Başlangıç Sistem Kütlesi (kg)", f"{initial_mass_kg:,.3f}"),
        ("Son Sistem Kütlesi (kg)", f"{final_mass_kg:,.3f}"),
        ("Tahliye Edilen Kütle (kg)", f"{discharged_mass_kg:,.3f}"),
        ("Maksimum Kütlesel Debi (kg/h)", f"{max_mass_flow_kg_h:,.2f}"),
        ("Son Kütlesel Debi (kg/h)", f"{final_mass_flow_kg_h:,.2f}"),
        ("Maksimum Hacimsel Debi (m3/h)", f"{max_volumetric_flow_m3_h:,.2f}"),
        ("Son Hacimsel Debi (m3/h)", f"{final_volumetric_flow_m3_h:,.2f}"),
        ("Min İç Isı Transfer Katsayısı (W/m2K)", f"{min_h_in:,.2f}"),
        ("Ort İç Isı Transfer Katsayısı (W/m2K)", f"{avg_h_in:,.2f}"),
        ("Maks İç Isı Transfer Katsayısı (W/m2K)", f"{max_h_in:,.2f}"),
        ("Gaz Kompozisyonu", " | ".join(f"{name}={fraction * 100.0:.3f}%" for name, fraction in sorted(screening_inputs["composition"].items()))),
    ]
    if peak_mach is not None:
        summary_rows.append(("Peak Mach Screening", f"{peak_mach:.3f}"))
    for idx, warning in enumerate(blowdown_warnings, start=1):
        summary_rows.append((f"Uyarı {idx}", warning))

    report_bundle = BlowdownReportBundle(
        title="Blowdown Analiz Raporu",
        text="\n".join(report_lines) + "\n",
        summary_rows=summary_rows,
        generated_on=generated_on,
        software_version=software_version,
    )

    return {
        "report_text": report_bundle.text,
        "report_bundle": report_bundle,
        "screening_inputs": screening_inputs,
        "margin_pct": margin,
        "sim_time_s": sim_time,
        "target_time_s": target_time,
        "verdict": verdict,
        "peak_mach": peak_mach,
    }
