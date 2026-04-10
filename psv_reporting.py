from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass
class PSVReportBundle:
    title: str
    text: str
    summary_rows: list[tuple[str, str]]
    generated_on: str
    software_version: str


def _fmt_optional(value, fmt: str, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    return format(value, fmt)


def _draw_page_decorations(canvas: Canvas, _doc, *, footer_text: str) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(36, 24, footer_text)
    canvas.drawRightString(A4[0] - 36, 24, f"Sayfa {canvas.getPageNumber()}")
    canvas.restoreState()


def build_psv_report_bundle(
    *,
    service_type: str,
    valve_type: str,
    prv_design: str,
    rupture_disk: str,
    inputs,
    sizing,
    mass_flow_kg_h: float,
    volumetric_flow_m3_h: float | None,
    valve_count: int,
    required_area_mm2: float,
    required_area_per_valve_mm2: float,
    preliminary_kb_source: str,
    force_n: float | None,
    force_kgf: float | None,
    mach_number: float | None,
    selected_valve,
    valve_data,
    vendor_selection,
    vendor_evaluation,
    warning_lines: Iterable[str],
    reaction_discharge_area_m2: float,
    section_xiii_validation=None,
    final_selection_readiness=None,
) -> PSVReportBundle:
    generated_on = datetime.now().strftime("%d.%m.%Y")
    software_version = "Blowdown Studio v2.4.0"
    report_title = f"PSV ÖN BOYUTLANDIRMA VE SCREENING RAPORU - {service_type}"
    composition_text = (
        " | ".join(f"{name}={fraction * 100.0:.3f}%" for name, fraction in sorted(inputs.get("composition", {}).items()))
        if inputs.get("composition")
        else "N/A"
    )
    report_lines = [
        report_title,
        "=" * len(report_title),
        f"Tarih                         : {generated_on}",
        f"Yazılım                       : {software_version}",
        "",
        "[1] Genel Sonuçlar",
        f"Servis tipi                   : {service_type}",
        f"Valf standardı                : {valve_type}",
        f"PRV tasarım tipi              : {prv_design}",
        f"Upstream rupture disk         : {rupture_disk}",
        f"Vana sayısı                   : {valve_count}",
        f"Gaz kompozisyonu              : {composition_text}",
        "",
        "[2] Basınç ve Relief Koşulları",
        f"Set pressure                  : {inputs['set_pressure_pa'] / 1e5:.3f} bara",
        f"MAWP / design pressure        : {inputs['mawp_pa'] / 1e5:.3f} bara",
        f"İzin verilen overpressure     : %{inputs['overpressure_pct']:.1f}",
        f"Relieving pressure (P1)       : {sizing.relieving_pressure_pa / 1e5:.3f} bara",
        f"Toplam backpressure (P2)      : {sizing.backpressure_pa / 1e5:.3f} bara",
        f"Relieving temperature         : {inputs['relieving_temperature_k'] - 273.15:.2f} °C",
    ]

    if service_type == "Liquid":
        report_lines.extend(
            [
                f"Sıvı tahliye debisi           : {sizing.Q_relieving_l_min:,.2f} L/min",
                f"Eşdeğer kütlesel debi         : {sizing.W_req_kg_h:,.2f} kg/h",
            ]
        )
    else:
        report_lines.append(f"Gerekli kütlesel debi         : {mass_flow_kg_h:,.2f} kg/h")
        if volumetric_flow_m3_h is not None:
            report_lines.append(f"Relieving hacimsel debi       : {volumetric_flow_m3_h:,.2f} m3/h")

    report_lines.extend(["", "[3] API 520 Ön Boyutlandırma"])
    if service_type == "Gas/Vapor":
        report_lines.extend(
            [
                f"Akış rejimi                   : {sizing.flow_regime}",
                f"Kullanılan denklem            : {sizing.equation_id}",
                f"Kritik basınç oranı           : {sizing.critical_pressure_ratio:.4f}",
                f"Gauge backpressure / set      : %{sizing.backpressure_pct_of_set:.2f}",
                f"k ideal                       : {sizing.k_ideal:.4f}",
                f"k real                        : {sizing.k_real:.4f}",
                f"Z faktörü                     : {sizing.Z:.4f}",
                f"MW                            : {sizing.MW_kg_kmol:.3f} kg/kmol",
                f"Kd                            : {sizing.Kd:.3f}",
                f"Kc                            : {sizing.Kc:.3f}",
                f"Kb kullanılan                 : {sizing.Kb_used:.3f}",
                f"Kb kaynağı                    : {preliminary_kb_source}",
            ]
        )
        if sizing.F2 is not None:
            report_lines.append(f"F2                            : {sizing.F2:.4f}")
    elif service_type == "Steam":
        report_lines.extend(
            [
                f"Kullanılan denklem            : {sizing.equation_id}",
                f"Gauge backpressure / set      : %{sizing.backpressure_pct_of_set:.2f}",
                f"Kd                            : {sizing.Kd:.3f}",
                f"Kc                            : {sizing.Kc:.3f}",
                f"Kb kullanılan                 : {sizing.Kb_used:.3f}",
                f"KN                            : {_fmt_optional(sizing.KN, '.4f')}",
                f"KSH                           : {_fmt_optional(sizing.KSH, '.4f', 'Fallback / N/A')}",
            ]
        )
    else:
        report_lines.extend(
            [
                f"Kullanılan denklem            : {sizing.equation_id}",
                f"Gauge backpressure / set      : %{sizing.backpressure_pct_of_set:.2f}",
                f"Kd                            : {sizing.Kd:.3f}",
                f"Kc                            : {sizing.Kc:.3f}",
                f"Kw kullanılan                 : {sizing.Kw_used:.3f}",
                f"Kv kullanılan                 : {sizing.Kv_used:.3f}",
                f"Specific gravity              : {sizing.specific_gravity:.4f}",
                f"Viskozite                     : {sizing.viscosity_cp:.2f} cP",
                f"Relieving density             : {sizing.rho_relieving_kg_m3:.2f} kg/m3",
                f"Reynolds                      : {_fmt_optional(sizing.reynolds, ',.0f')}",
                f"Viskozite kontrollü alan      : {sizing.selected_area_mm2:,.2f} mm2",
            ]
        )

    report_lines.extend(
        [
            f"Toplam gerekli alan           : {required_area_mm2:,.2f} mm2",
            f"Vana başına gerekli alan      : {required_area_per_valve_mm2:,.2f} mm2",
            "",
            "[4] Mekanik Screening",
        ]
    )
    if force_n is not None and force_kgf is not None:
        report_lines.extend(
            [
                f"Açık deşarj reaksiyon kuvveti : {force_n:,.0f} N ({force_kgf:,.1f} kgf) / vana",
                f"Reaksiyon discharge alanı     : {reaction_discharge_area_m2 * 1e6:,.1f} mm2",
                f"Çıkış Mach screening          : {_fmt_optional(mach_number, '.3f', 'Hesaplanamadı')}",
            ]
        )
    else:
        report_lines.append("Mekanik screening             : Bu servis tipi için aktif değil.")

    report_lines.extend(["", "[5] Vana Seçimi ve Vendor Screening"])
    if service_type == "Gas/Vapor" and "API 526" in valve_type and vendor_selection is not None:
        report_lines.extend(
            [
                f"Vendor katalog                : {vendor_evaluation.catalog_name if vendor_evaluation else 'N/A'}",
                f"Üretici / seri                : {vendor_selection.model.manufacturer} / {vendor_selection.model.series}",
                f"Model kodu                    : {vendor_selection.model.model_code}",
                f"Seçilen size / orifis         : {vendor_selection.model.display_size}",
                f"Giriş / çıkış bağlantısı      : {vendor_selection.model.inlet_outlet_size_in} ({vendor_selection.model.inlet_outlet_size_dn})",
                f"Efektif alan                  : {vendor_selection.model.effective_area_mm2:,.1f} mm2",
                f"Actual area                   : {vendor_selection.model.actual_area_mm2:,.1f} mm2",
                f"Certified gas Kd              : {vendor_selection.model.certified_kd_gas:.3f}",
                f"Trim kodu                     : {vendor_selection.model.trim_code or 'N/A'}",
                f"Code stamp                    : {vendor_selection.model.code_stamp or 'N/A'}",
                f"Gövde malzemesi               : {vendor_selection.model.body_material or 'N/A'}",
                f"Trim malzemesi                : {vendor_selection.model.trim_material or 'N/A'}",
                f"Giriş rating class            : {vendor_selection.model.inlet_rating_class or 'N/A'}",
                f"Çıkış rating class            : {vendor_selection.model.outlet_rating_class or 'N/A'}",
                f"Kullanılan Kb                 : {vendor_selection.kb_used:.3f} ({vendor_selection.kb_source})",
                f"Gerekli debi / vana           : {vendor_selection.required_flow_kg_h:,.2f} kg/h",
                f"Certified capacity / vana     : {vendor_selection.certified_capacity_kg_h:,.2f} kg/h",
                f"Efektif alan marjı            : %{vendor_selection.effective_area_margin_pct:.1f}",
                f"Capacity marjı                : %{vendor_selection.certified_capacity_margin_pct:.1f}",
                f"Veri kaynağı                  : {vendor_selection.model.source}",
            ]
        )
    elif service_type == "Gas/Vapor" and "API 526" in valve_type and vendor_evaluation is not None and vendor_evaluation.evaluated:
        largest_vendor = vendor_evaluation.evaluated[-1]
        report_lines.extend(
            [
                f"Vendor katalog                : {vendor_evaluation.catalog_name}",
                "Vendor sonucu                 : Uygun model bulunamadı",
                f"En büyük değerlendirilen model: {largest_vendor.model.model_code} / {largest_vendor.model.display_size}",
                f"Efektif alan                  : {largest_vendor.model.effective_area_mm2:,.1f} mm2",
                f"Actual area                   : {largest_vendor.model.actual_area_mm2:,.1f} mm2",
                f"Certified capacity / vana     : {largest_vendor.certified_capacity_kg_h:,.2f} kg/h",
            ]
        )
    elif selected_valve:
        margin_pct = ((selected_valve.area_mm2 * valve_count) - required_area_mm2) / max(required_area_mm2, 1e-12) * 100.0
        report_lines.extend(
            [
                f"Seçilen nominal vana          : {selected_valve.size_in} ({selected_valve.size_dn})",
                f"Nominal geçiş alanı           : {selected_valve.area_mm2:,.1f} mm2",
                f"Toplam alan marjı             : %{margin_pct:.1f}",
            ]
        )
    else:
        largest_valve = valve_data[-1] if valve_data else None
        report_lines.extend(
            [
                "Standart seçim                : Uygun vana bulunamadı",
                (
                    f"En büyük mevcut seçenek       : {largest_valve.size_in} ({largest_valve.size_dn}) / {largest_valve.area_mm2:,.1f} mm2"
                    if largest_valve
                    else "En büyük mevcut seçenek       : N/A"
                ),
            ]
        )

    if section_xiii_validation is not None:
        report_lines.extend(["", *section_xiii_validation.summary_lines])
    if final_selection_readiness is not None:
        report_lines.extend(["", *final_selection_readiness.summary_lines])
        if final_selection_readiness.confirmed_items:
            report_lines.extend("  + " + line for line in final_selection_readiness.confirmed_items)
        if final_selection_readiness.missing_items:
            report_lines.extend("  - " + line for line in final_selection_readiness.missing_items)
        if final_selection_readiness.caution_items:
            report_lines.extend("  ! " + line for line in final_selection_readiness.caution_items)

    warnings_list = list(warning_lines)
    if warnings_list:
        report_lines.extend(["", "[6] Uyarılar"])
        report_lines.extend(f"- {line}" for line in warnings_list)

    summary_rows = [
        ("Tarih", generated_on),
        ("Yazılım", software_version),
        ("Servis Tipi", service_type),
        ("Valf Standardı", valve_type),
        ("PRV Tasarım Tipi", prv_design),
        ("Gaz Kompozisyonu", composition_text),
        ("Set Pressure (bara)", f"{inputs['set_pressure_pa'] / 1e5:.3f}"),
        ("Relieving Pressure (bara)", f"{sizing.relieving_pressure_pa / 1e5:.3f}"),
        ("Backpressure (bara)", f"{sizing.backpressure_pa / 1e5:.3f}"),
        ("Relieving Temperature (°C)", f"{inputs['relieving_temperature_k'] - 273.15:.2f}"),
        ("Vana Sayısı", f"{valve_count}"),
        ("Toplam Gerekli Alan (mm2)", f"{required_area_mm2:,.2f}"),
        ("Vana Başına Gerekli Alan (mm2)", f"{required_area_per_valve_mm2:,.2f}"),
    ]

    if service_type == "Liquid":
        summary_rows.extend(
            [
                ("Sıvı Tahliye Debisi (L/min)", f"{sizing.Q_relieving_l_min:,.2f}"),
                ("Eşdeğer Kütlesel Debi (kg/h)", f"{sizing.W_req_kg_h:,.2f}"),
                ("Kw Used", f"{sizing.Kw_used:.3f}"),
                ("Kv Used", f"{sizing.Kv_used:.3f}"),
            ]
        )
    else:
        summary_rows.extend(
            [
                ("Gerekli Kütlesel Debi (kg/h)", f"{mass_flow_kg_h:,.2f}"),
                ("Relieving Hacimsel Debi (m3/h)", "" if volumetric_flow_m3_h is None else f"{volumetric_flow_m3_h:,.2f}"),
                ("Kd Used", f"{sizing.Kd:.3f}"),
                ("Kc Used", f"{sizing.Kc:.3f}"),
            ]
        )

    if force_n is not None:
        summary_rows.append(("Reaction Force (N/valve)", f"{force_n:,.0f}"))
    if mach_number is not None:
        summary_rows.append(("Exit Mach Screening", f"{mach_number:.3f}"))
    if selected_valve:
        summary_rows.append(("Seçilen Vana", f"{selected_valve.size_in} ({selected_valve.size_dn})"))
        summary_rows.append(("Seçilen Vana Alanı (mm2)", f"{selected_valve.area_mm2:,.1f}"))
    if vendor_selection is not None:
        summary_rows.append(("Vendor Model", f"{vendor_selection.model.manufacturer} / {vendor_selection.model.model_code}"))
        summary_rows.append(("Vendor Capacity Margin (%)", f"{vendor_selection.certified_capacity_margin_pct:.1f}"))
    if section_xiii_validation is not None:
        summary_rows.append(("ASME Section XIII Screening", section_xiii_validation.status))
    if final_selection_readiness is not None:
        summary_rows.append(("Vendor Final Selection Readiness", final_selection_readiness.status))
        summary_rows.append(("Vendor Readiness Score (%)", f"{final_selection_readiness.readiness_score_pct:.1f}"))
    for idx, warning in enumerate(warnings_list, start=1):
        summary_rows.append((f"Uyarı {idx}", warning))

    return PSVReportBundle(
        title=report_title,
        text="\n".join(report_lines),
        summary_rows=summary_rows,
        generated_on=generated_on,
        software_version=software_version,
    )


def export_psv_report_csv(path: str | Path, bundle: PSVReportBundle) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Field", "Value"])
        for key, value in bundle.summary_rows:
            writer.writerow([key, value])


def export_psv_report_pdf(path: str | Path, bundle: PSVReportBundle) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    footer_text = "Bu rapor screening amaçlıdır; son tasarım doğrulaması için API standartlarına başvurun."
    story = [
        Paragraph(escape(bundle.title), styles["Title"]),
        Spacer(1, 6),
        Paragraph(escape(f"Tarih: {bundle.generated_on} | {bundle.software_version}"), styles["Normal"]),
        Spacer(1, 12),
    ]
    table = Table([["Field", "Value"], *bundle.summary_rows], colWidths=[180, 340])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.extend([table, Spacer(1, 16), Paragraph("Detaylı Rapor", styles["Heading2"])])
    for line in bundle.text.splitlines():
        story.append(Paragraph(escape(line) or "&nbsp;", styles["Code"]))
    doc.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_decorations(canvas, doc, footer_text=footer_text),
        onLaterPages=lambda canvas, doc: _draw_page_decorations(canvas, doc, footer_text=footer_text),
    )
