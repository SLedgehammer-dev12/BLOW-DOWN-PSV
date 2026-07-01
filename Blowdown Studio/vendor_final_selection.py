from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VendorFinalSelectionReadiness:
    status: str
    readiness_score_pct: float
    summary_lines: list[str]
    confirmed_items: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    caution_items: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_vendor_final_selection_readiness(
    *,
    service_type: str,
    valve_type: str,
    vendor_selection=None,
    set_pressure_pa: float | None = None,
) -> VendorFinalSelectionReadiness:
    summary_lines = ["[6] Vendor Final Selection Readiness"]
    confirmed_items: list[str] = []
    missing_items: list[str] = []
    caution_items: list[str] = []
    warnings: list[str] = []

    if service_type != "Gas/Vapor" or "API 526" not in valve_type:
        summary_lines.extend(
            [
                "Durum                         : LIMITED",
                "Aciklama                      : Bu readiness kontrolu yalniz Gas/Vapor + vendor certified-capacity secimi icin aktif.",
            ]
        )
        warnings.append("Steam/Liquid veya nominal-bore secimlerde final vendor readiness ayri datasheet incelemesi gerektirir.")
        return VendorFinalSelectionReadiness(
            status="LIMITED",
            readiness_score_pct=0.0,
            summary_lines=summary_lines,
            confirmed_items=confirmed_items,
            missing_items=missing_items,
            caution_items=caution_items,
            warnings=warnings,
        )

    if vendor_selection is None:
        summary_lines.extend(
            [
                "Durum                         : FAIL",
                "Aciklama                      : Secilmis vendor modeli olmadan final selection readiness degerlendirilemez.",
            ]
        )
        warnings.append("Final selection readiness icin belirli bir vendor modeli secilmelidir.")
        return VendorFinalSelectionReadiness(
            status="FAIL",
            readiness_score_pct=0.0,
            summary_lines=summary_lines,
            confirmed_items=confirmed_items,
            missing_items=missing_items,
            caution_items=caution_items,
            warnings=warnings,
        )

    model = vendor_selection.model
    notes_lower = getattr(model, "notes", "").lower()

    confirmed_items.extend(
        [
            f"Manufacturer / series identified: {model.manufacturer} / {model.series}",
            f"Model code identified: {model.model_code}",
            f"Actual area available: {model.actual_area_mm2:,.1f} mm2",
            f"Certified gas Kd available: {model.certified_kd_gas:.3f}",
            f"Certified capacity screened: {vendor_selection.certified_capacity_kg_h:,.2f} kg/h",
        ]
    )

    if vendor_selection.kb_source.lower().startswith("vendor"):
        confirmed_items.append(f"Model-specific Kb screening used: {vendor_selection.kb_used:.3f}")
    else:
        caution_items.append(f"Kb exact vendor confirmation still required: current source = {vendor_selection.kb_source}")

    code_stamp = getattr(model, "code_stamp", "")
    trim_code = getattr(model, "trim_code", "")
    body_material = getattr(model, "body_material", "")
    trim_material = getattr(model, "trim_material", "")
    set_pressure_min_pa = getattr(model, "set_pressure_min_pa", None)
    set_pressure_max_pa = getattr(model, "set_pressure_max_pa", None)
    inlet_rating_class = getattr(model, "inlet_rating_class", "")
    outlet_rating_class = getattr(model, "outlet_rating_class", "")

    if code_stamp:
        confirmed_items.append(f"Code stamp field present: {code_stamp}")
    else:
        caution_items.append("Code-stamp field is not present in the catalog record.")

    if trim_code:
        confirmed_items.append(f"Trim / nozzle code present: {trim_code}")
    else:
        caution_items.append("Trim / nozzle code is not present in the catalog record.")

    if body_material:
        confirmed_items.append(f"Body material field present: {body_material}")
    else:
        caution_items.append("Body material field is not present in the catalog record.")

    if trim_material:
        confirmed_items.append(f"Trim material field present: {trim_material}")
    else:
        caution_items.append("Trim material field is not present in the catalog record.")

    if inlet_rating_class or outlet_rating_class:
        confirmed_items.append(
            f"Rating class fields present: inlet={inlet_rating_class or 'N/A'}, outlet={outlet_rating_class or 'N/A'}"
        )
    else:
        caution_items.append("Inlet / outlet rating fields are not present in the catalog record.")

    if set_pressure_pa is not None:
        if set_pressure_min_pa is not None and set_pressure_max_pa is not None:
            if set_pressure_min_pa <= set_pressure_pa <= set_pressure_max_pa:
                confirmed_items.append(
                    f"Set pressure falls inside published model range: {set_pressure_min_pa / 1e5:.1f}-{set_pressure_max_pa / 1e5:.1f} bara"
                )
            else:
                caution_items.append(
                    f"Set pressure is outside the published catalog range: {set_pressure_min_pa / 1e5:.1f}-{set_pressure_max_pa / 1e5:.1f} bara"
                )
        else:
            caution_items.append("Set-pressure min/max range is not present in the catalog record.")

    missing_items.extend(
        [
            "Exact set pressure / trim combination confirmation",
            "Nameplate / code-stamp (UV/NB or equivalent) confirmation",
            "Body / trim / seat material confirmation for service and MDMT",
            "Inlet / outlet rating and facing confirmation",
            "Overpressure case and certified capacity sheet for exact order code",
            "Backpressure applicability confirmation for exact valve build",
        ]
    )

    if getattr(model, "is_sample_data", False):
        caution_items.append("Built-in sample data is active; real vendor datasheet is mandatory.")
    if "iso 4126" in notes_lower or "ad2000" in notes_lower:
        caution_items.append("Selected model is based on ISO 4126 / AD2000 data, not direct ASME/NB certified capacity.")
    if "inferred gas kd" in notes_lower:
        caution_items.append("Certified gas Kd was inferred from official capacity tables and still needs direct vendor confirmation.")
    if "digitized" in notes_lower:
        caution_items.append("Kb curve contains digitized screening points; exact vendor software/datasheet check is still required.")

    raw_score = 100.0
    raw_score -= 8.0 * len(missing_items)
    raw_score -= 6.0 * len(caution_items)
    if getattr(model, "is_sample_data", False):
        raw_score -= 20.0
    readiness_score_pct = max(0.0, min(100.0, raw_score))

    if getattr(model, "is_sample_data", False):
        status = "SCREENING_ONLY"
    elif readiness_score_pct >= 70.0 and not caution_items:
        status = "READY_FOR_VENDOR_RFQ"
    elif readiness_score_pct >= 20.0:
        status = "LIMITED"
    else:
        status = "SCREENING_ONLY"

    summary_lines.extend(
        [
            f"Durum                         : {status}",
            f"Readiness score               : %{readiness_score_pct:.1f}",
            f"Confirmed items               : {len(confirmed_items)}",
            f"Missing confirmations         : {len(missing_items)}",
            f"Caution items                 : {len(caution_items)}",
            "Not                           : Bu adim final vendor purchase / datasheet onayi yerine gecmez.",
        ]
    )
    warnings.extend(f"Vendor final selection: {item}" for item in caution_items)
    return VendorFinalSelectionReadiness(
        status=status,
        readiness_score_pct=readiness_score_pct,
        summary_lines=summary_lines,
        confirmed_items=confirmed_items,
        missing_items=missing_items,
        caution_items=caution_items,
        warnings=warnings,
    )
