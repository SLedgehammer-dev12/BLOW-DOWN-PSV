from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SectionXIIIValidationResult:
    status: str
    summary_lines: list[str]
    warnings: list[str] = field(default_factory=list)


def validate_section_xiii_screening(
    *,
    service_type: str,
    valve_type: str,
    vendor_selection=None,
    vendor_evaluation=None,
) -> SectionXIIIValidationResult:
    summary_lines = ["[5] ASME Section XIII Screening"]
    warnings: list[str] = []

    if service_type != "Gas/Vapor":
        summary_lines.extend(
            [
                "Durum                         : LIMITED",
                "Aciklama                      : Bu surumde ASME Section XIII screening dogrulamasi yalniz Gas/Vapor + vendor certified-capacity yolu icin aktiftir.",
            ]
        )
        warnings.append("Steam/Liquid servis icin final certified-capacity ve code-mark dogrulamasi ayri vendor datasheet ile yapilmalidir.")
        return SectionXIIIValidationResult(status="LIMITED", summary_lines=summary_lines, warnings=warnings)

    if "API 526" not in valve_type:
        summary_lines.extend(
            [
                "Durum                         : LIMITED",
                "Aciklama                      : API 6D / nominal-bore karsilastirmasi ASME Section XIII certified-capacity kontrolunun yerine gecmez.",
            ]
        )
        warnings.append("ASME Section XIII screening yalniz vendor certified-capacity verisi olan PSV modeli ile anlamlidir.")
        return SectionXIIIValidationResult(status="LIMITED", summary_lines=summary_lines, warnings=warnings)

    if vendor_selection is None:
        if vendor_evaluation is not None and vendor_evaluation.evaluated:
            summary_lines.extend(
                [
                    "Durum                         : FAIL",
                    "Aciklama                      : Evaluated vendor modelleri icinde hem efektif alan hem certified-capacity kosulunu saglayan secim bulunamadi.",
                ]
            )
            warnings.append("Current vendor screening sonucu ASME Section XIII on-secim kosullarini saglayan model bulunamadi.")
            return SectionXIIIValidationResult(status="FAIL", summary_lines=summary_lines, warnings=warnings)
        summary_lines.extend(
            [
                "Durum                         : LIMITED",
                "Aciklama                      : Vendor certified-capacity modeli olmadan Section XIII screening tamamlanamaz.",
            ]
        )
        warnings.append("Vendor selection olmadan final ASME/NB sertifikali kapasite dogrulamasi yapilamaz.")
        return SectionXIIIValidationResult(status="LIMITED", summary_lines=summary_lines, warnings=warnings)

    model = vendor_selection.model
    notes_lower = model.notes.lower()
    status = "PASS"
    if model.is_sample_data:
        status = "LIMITED"
        warnings.append("Built-in sample catalog final ASME Section XIII dogrulamasi yerine kullanilamaz.")
    if "iso 4126" in notes_lower or "ad2000" in notes_lower:
        status = "LIMITED"
        warnings.append("Secilen model ISO 4126 / AD2000 bazlidir; ASME/NB certified capacity ile bire bir esdeger degildir.")
    if "inferred gas kd" in notes_lower:
        status = "LIMITED"
        warnings.append("Certified Kd resmi kapasite tablosundan screening amacli turetilmistir; vendor sertifikali degerle teyit edilmelidir.")
    if vendor_selection.kb_source.lower().startswith("preliminary") or vendor_selection.kb_source.lower().startswith("assumed"):
        status = "LIMITED"
        warnings.append("Model-specific backpressure curve eksik oldugu icin Kb/Kw screening varsayimi kullanildi.")
    if not vendor_selection.meets_required_effective_area or not vendor_selection.meets_required_capacity:
        status = "FAIL"
        warnings.append("Secilen model gerekli efektif alan veya certified-capacity kosulunu saglamiyor.")

    summary_lines.extend(
        [
            f"Durum                         : {status}",
            f"Uretici / seri                : {model.manufacturer} / {model.series}",
            f"Model                         : {model.model_code}",
            f"Actual area                   : {model.actual_area_mm2:,.1f} mm2",
            f"Certified gas Kd              : {model.certified_kd_gas:.3f}",
            f"Required flow / valve         : {vendor_selection.required_flow_kg_h:,.2f} kg/h",
            f"Certified capacity / valve    : {vendor_selection.certified_capacity_kg_h:,.2f} kg/h",
            f"Area margin                   : %{vendor_selection.effective_area_margin_pct:.1f}",
            f"Capacity margin               : %{vendor_selection.certified_capacity_margin_pct:.1f}",
            f"Data source                   : {model.source or 'N/A'}",
            "Not                           : Bu adim screening seviyesindedir; UV/NB mark, set pressure trim, malzeme ve nameplate teyidi ayrica gerekir.",
        ]
    )
    return SectionXIIIValidationResult(status=status, summary_lines=summary_lines, warnings=warnings)
