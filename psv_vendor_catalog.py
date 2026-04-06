from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import sys
from typing import Iterable

from psv_preliminary import PSVGasSizingResult, coefficient_c_si, coefficient_f2


def _resource_base_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


DEFAULT_VENDOR_CATALOG_PATH = _resource_base_dir() / "vendor_data" / "psv_vendor_catalog_official.json"


@dataclass(frozen=True)
class KbCurvePoint:
    backpressure_pct_of_set: float
    kb: float


@dataclass(frozen=True)
class VendorPSVModel:
    catalog_name: str
    manufacturer: str
    series: str
    model_code: str
    design_type: str
    orifice_letter: str
    size_label: str
    api526_equivalent: str
    inlet_outlet_size_in: str
    inlet_outlet_size_dn: str
    effective_area_mm2: float
    actual_area_mm2: float
    certified_kd_gas: float
    kb_curve_points: tuple[KbCurvePoint, ...] = ()
    source: str = ""
    notes: str = ""
    is_sample_data: bool = True

    @property
    def display_size(self) -> str:
        if self.api526_equivalent and self.api526_equivalent != self.size_label:
            return f"{self.size_label} (API {self.api526_equivalent} eq.)"
        return self.size_label


@dataclass
class VendorPSVSelection:
    model: VendorPSVModel
    required_flow_kg_h: float
    required_effective_area_mm2: float
    certified_capacity_kg_h: float
    certified_capacity_margin_pct: float
    effective_area_margin_pct: float
    kb_used: float
    kb_source: str
    meets_required_effective_area: bool
    meets_required_capacity: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class VendorCatalogEvaluation:
    catalog_name: str
    selected: VendorPSVSelection | None
    evaluated: list[VendorPSVSelection]


def default_vendor_catalog_path() -> Path:
    return DEFAULT_VENDOR_CATALOG_PATH


def _api526_effective_orifices() -> list[tuple[str, float, str, str]]:
    return [
        ("D", 71.0, '1" x 2"', "DN25 x DN50"),
        ("E", 126.5, '1" x 2" / 1.5" x 2.5"', "DN25 x DN50 / DN40 x DN65"),
        ("F", 198.1, '1.5" x 2.5" / 2" x 3"', "DN40 x DN65 / DN50 x DN80"),
        ("G", 324.5, '2" x 3"', "DN50 x DN80"),
        ("H", 506.5, '2" x 3" / 3" x 4"', "DN50 x DN80 / DN80 x DN100"),
        ("J", 830.3, '3" x 4"', "DN80 x DN100"),
        ("K", 1185.8, '3" x 4" / 4" x 6"', "DN80 x DN100 / DN100 x DN150"),
        ("L", 1840.6, '4" x 6"', "DN100 x DN150"),
        ("M", 2322.6, '4" x 6"', "DN100 x DN150"),
        ("N", 2800.0, '4" x 6"', "DN100 x DN150"),
        ("P", 4116.1, '4" x 6" / 6" x 8"', "DN100 x DN150 / DN150 x DN200"),
        ("Q", 7129.0, '6" x 8" / 8" x 10"', "DN150 x DN200 / DN200 x DN250"),
        ("R", 10322.6, '6" x 8" / 8" x 10"', "DN150 x DN200 / DN200 x DN250"),
        ("T", 16774.2, '8" x 10"', "DN200 x DN250"),
    ]


def _balanced_bellows_curve() -> tuple[KbCurvePoint, ...]:
    return (
        KbCurvePoint(0.0, 1.00),
        KbCurvePoint(10.0, 1.00),
        KbCurvePoint(20.0, 0.99),
        KbCurvePoint(30.0, 0.97),
        KbCurvePoint(40.0, 0.94),
        KbCurvePoint(50.0, 0.90),
    )


def build_builtin_vendor_catalog() -> list[VendorPSVModel]:
    catalog_name = "Built-in Sample Section XIII Data Model"
    family_curves = {
        "Conventional": (),
        "Balanced Bellows": _balanced_bellows_curve(),
        "Balanced Spring": (),
        "Pilot-Operated": (),
    }
    family_series = {
        "Conventional": ("SampleVendor", "SV-C"),
        "Balanced Bellows": ("SampleVendor", "SV-BB"),
        "Balanced Spring": ("SampleVendor", "SV-BS"),
        "Pilot-Operated": ("SampleVendor", "SV-PO"),
    }
    models: list[VendorPSVModel] = []

    for design_type, kb_curve in family_curves.items():
        manufacturer, series = family_series[design_type]
        for letter, effective_area_mm2, size_in, size_dn in _api526_effective_orifices():
            certified_kd_gas = 0.975
            actual_area_mm2 = effective_area_mm2 / certified_kd_gas
            model_code = f"{series}-{letter}"
            models.append(
                VendorPSVModel(
                    catalog_name=catalog_name,
                    manufacturer=manufacturer,
                    series=series,
                    model_code=model_code,
                    design_type=design_type,
                    orifice_letter=letter,
                    size_label=letter,
                    api526_equivalent=letter,
                    inlet_outlet_size_in=size_in,
                    inlet_outlet_size_dn=size_dn,
                    effective_area_mm2=effective_area_mm2,
                    actual_area_mm2=actual_area_mm2,
                    certified_kd_gas=certified_kd_gas,
                    kb_curve_points=kb_curve,
                    source="Illustrative built-in catalog",
                    notes="Sample data only. Use real vendor documentation before final certified selection.",
                    is_sample_data=True,
                )
            )
    return models


def _curve_from_payload(points: Iterable[dict]) -> tuple[KbCurvePoint, ...]:
    return tuple(
        sorted(
            (
                KbCurvePoint(
                    backpressure_pct_of_set=float(point["backpressure_pct_of_set"]),
                    kb=float(point["kb"]),
                )
                for point in points
            ),
            key=lambda item: item.backpressure_pct_of_set,
        )
    )


def _family_records_from_payload(payload: dict, catalog_name: str) -> list[dict]:
    size_map = {letter: (effective_area_mm2, size_in, size_dn) for letter, effective_area_mm2, size_in, size_dn in _api526_effective_orifices()}
    records: list[dict] = []

    for family in payload.get("families", []):
        actual_area_map = family.get("actual_area_mm2_by_orifice", {})
        model_prefix = str(family.get("model_code_prefix", family["series"]))
        kb_curve_points = family.get("kb_curve_points", [])

        for letter, actual_area_mm2 in actual_area_map.items():
            if letter not in size_map:
                continue
            effective_area_mm2, size_in, size_dn = size_map[letter]
            records.append(
                {
                    "catalog_name": family.get("catalog_name", catalog_name),
                    "manufacturer": family["manufacturer"],
                    "series": family["series"],
                    "model_code": f"{model_prefix}-{letter}",
                    "design_type": family["design_type"],
                    "orifice_letter": letter,
                    "size_label": letter,
                    "api526_equivalent": letter,
                    "inlet_outlet_size_in": size_in,
                    "inlet_outlet_size_dn": size_dn,
                    "effective_area_mm2": effective_area_mm2,
                    "actual_area_mm2": actual_area_mm2,
                    "certified_kd_gas": family["certified_kd_gas"],
                    "kb_curve_points": kb_curve_points,
                    "source": family.get("source", ""),
                    "notes": family.get("notes", ""),
                    "is_sample_data": bool(family.get("is_sample_data", False)),
                }
            )

    return records


def _records_from_payload(payload: list[dict] | dict, source_path: Path) -> tuple[str, list[dict]]:
    if isinstance(payload, dict):
        catalog_name = str(payload.get("catalog_name", source_path.stem))
        records = list(payload.get("models", []))
        if "families" in payload:
            records.extend(_family_records_from_payload(payload, catalog_name))
        return catalog_name, records
    return source_path.stem, list(payload)


@lru_cache(maxsize=8)
def _load_vendor_catalog_cached(path_key: str) -> tuple[VendorPSVModel, ...]:
    if path_key == "__default__":
        source_path = default_vendor_catalog_path()
        if not source_path.exists():
            return tuple(build_builtin_vendor_catalog())
    else:
        source_path = Path(path_key)
        if not source_path.exists():
            raise FileNotFoundError(f"Vendor catalog not found: {source_path}")

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    _, records = _records_from_payload(payload, source_path)

    models: list[VendorPSVModel] = []
    for record in records:
        models.append(
            VendorPSVModel(
                catalog_name=str(record.get("catalog_name", source_path.stem)),
                manufacturer=str(record["manufacturer"]),
                series=str(record["series"]),
                model_code=str(record["model_code"]),
                design_type=str(record["design_type"]),
                orifice_letter=str(record["orifice_letter"]),
                size_label=str(record.get("size_label", record["orifice_letter"])),
                api526_equivalent=str(record.get("api526_equivalent", record["orifice_letter"])),
                inlet_outlet_size_in=str(record["inlet_outlet_size_in"]),
                inlet_outlet_size_dn=str(record["inlet_outlet_size_dn"]),
                effective_area_mm2=float(record["effective_area_mm2"]),
                actual_area_mm2=float(record["actual_area_mm2"]),
                certified_kd_gas=float(record["certified_kd_gas"]),
                kb_curve_points=_curve_from_payload(record.get("kb_curve_points", [])),
                source=str(record.get("source", "")),
                notes=str(record.get("notes", "")),
                is_sample_data=bool(record.get("is_sample_data", False)),
            )
        )
    return tuple(models)


def load_vendor_catalog(path: str | Path | None = None) -> list[VendorPSVModel]:
    if path is None:
        return list(_load_vendor_catalog_cached("__default__"))
    return list(_load_vendor_catalog_cached(str(Path(path))))


def interpolate_kb_curve(points: tuple[KbCurvePoint, ...], backpressure_pct_of_set: float) -> tuple[float, list[str]]:
    warnings: list[str] = []
    if not points:
        return 1.0, warnings

    if backpressure_pct_of_set <= points[0].backpressure_pct_of_set:
        return points[0].kb, warnings
    if backpressure_pct_of_set >= points[-1].backpressure_pct_of_set:
        warnings.append(
            f"Backpressure {backpressure_pct_of_set:.1f}% is above the published Kb curve limit of {points[-1].backpressure_pct_of_set:.1f}%."
        )
        return points[-1].kb, warnings

    for left, right in zip(points, points[1:]):
        if left.backpressure_pct_of_set <= backpressure_pct_of_set <= right.backpressure_pct_of_set:
            span = right.backpressure_pct_of_set - left.backpressure_pct_of_set
            if span <= 1e-12:
                return right.kb, warnings
            frac = (backpressure_pct_of_set - left.backpressure_pct_of_set) / span
            return left.kb + frac * (right.kb - left.kb), warnings

    return points[-1].kb, warnings


def estimate_family_kb(
    design_type: str,
    backpressure_pct_of_set: float,
    catalog: list[VendorPSVModel] | None = None,
) -> tuple[float | None, str, list[str]]:
    models = catalog if catalog is not None else load_vendor_catalog()
    design_key = design_type.strip().lower()
    family_models = [model for model in models if model.design_type.strip().lower() == design_key and model.kb_curve_points]
    if not family_models:
        return None, "N/A", []

    kb_candidates: list[tuple[float, VendorPSVModel]] = []
    warnings: list[str] = []
    for model in family_models:
        kb, curve_warnings = interpolate_kb_curve(model.kb_curve_points, backpressure_pct_of_set)
        kb_candidates.append((kb, model))
        warnings.extend(f"{model.manufacturer} {model.series}: {warning}" for warning in curve_warnings)

    kb_value, controlling_model = min(kb_candidates, key=lambda item: item[0])
    source = f"Conservative vendor Kb envelope ({controlling_model.manufacturer} {controlling_model.series})"
    return kb_value, source, warnings


def _balanced_kb_for_model(model: VendorPSVModel, sizing: PSVGasSizingResult) -> tuple[float, str, list[str]]:
    if model.kb_curve_points:
        kb_used, warnings = interpolate_kb_curve(model.kb_curve_points, sizing.backpressure_pct_of_set)
        return kb_used, "Vendor Kb curve", warnings

    if sizing.Kb_used > 0.0:
        return sizing.Kb_used, "Preliminary Kb input", [
            "Model-specific Kb curve was not available; preliminary Kb value was reused for certified-capacity screening."
        ]

    return 1.0, "Assumed Kb=1.0", [
        "Model-specific Kb curve was not available; Kb=1.0 was assumed for screening."
    ]


def _certified_capacity_kg_h(
    model: VendorPSVModel,
    sizing: PSVGasSizingResult,
    Kc: float,
) -> tuple[float, float, str, list[str]]:
    warnings: list[str] = []
    p1_kpa = sizing.relieving_pressure_pa / 1000.0
    p2_kpa = sizing.backpressure_pa / 1000.0
    kb_used = 1.0
    kb_source = "Fixed"

    if model.design_type == "Balanced Bellows":
        kb_used, kb_source, curve_warnings = _balanced_kb_for_model(model, sizing)
        warnings.extend(curve_warnings)

    if sizing.is_critical or model.design_type == "Balanced Bellows":
        C = coefficient_c_si(sizing.k_ideal)
        capacity = (
            model.actual_area_mm2
            * C
            * model.certified_kd_gas
            * kb_used
            * Kc
            * p1_kpa
            / ((sizing.relieving_temperature_k * sizing.Z / sizing.MW_kg_kmol) ** 0.5)
        )
    else:
        F2 = sizing.F2 if sizing.F2 is not None else coefficient_f2(sizing.k_ideal, sizing.backpressure_pa / sizing.relieving_pressure_pa)
        capacity = (
            model.actual_area_mm2
            * F2
            * model.certified_kd_gas
            * Kc
            / 17.9
        )
        capacity /= (
            (sizing.relieving_temperature_k * sizing.Z / (sizing.MW_kg_kmol * p1_kpa * (p1_kpa - p2_kpa))) ** 0.5
        )

    return capacity, kb_used, kb_source, warnings


def evaluate_vendor_models_for_gas_service(
    sizing: PSVGasSizingResult,
    required_flow_kg_h: float,
    valve_count: int,
    valve_design: str,
    Kc: float,
    catalog: list[VendorPSVModel] | None = None,
) -> VendorCatalogEvaluation:
    models = catalog if catalog is not None else load_vendor_catalog()
    design_key = valve_design.strip().lower()
    candidate_models = [model for model in models if model.design_type.strip().lower() == design_key]
    candidate_models.sort(key=lambda item: (item.effective_area_mm2, item.actual_area_mm2, item.manufacturer, item.series, item.size_label))

    required_flow_per_valve_kg_h = required_flow_kg_h / max(valve_count, 1)
    required_effective_area_per_valve_mm2 = sizing.A_req_mm2 / max(valve_count, 1)
    evaluated: list[VendorPSVSelection] = []

    for model in candidate_models:
        capacity_kg_h, kb_used, kb_source, warnings = _certified_capacity_kg_h(model, sizing, Kc)
        meets_effective_area = model.effective_area_mm2 >= required_effective_area_per_valve_mm2
        meets_capacity = capacity_kg_h >= required_flow_per_valve_kg_h

        if model.is_sample_data:
            warnings.append(
                "Built-in sample catalog is active. Use real vendor documentation before final certified selection."
            )
        notes_lower = model.notes.lower()
        if "digitized" in notes_lower:
            warnings.append("Balanced bellows Kb curve is a digitized approximation of the published vendor graph.")
        if "inferred gas kd" in notes_lower:
            warnings.append("Certified gas Kd was inferred from an official published air-capacity table and is screening-only.")
        if "iso 4126" in notes_lower or "ad2000" in notes_lower:
            warnings.append("This vendor model is based on ISO 4126 / AD2000 flow data, not ASME/NB certified capacity.")

        evaluated.append(
            VendorPSVSelection(
                model=model,
                required_flow_kg_h=required_flow_per_valve_kg_h,
                required_effective_area_mm2=required_effective_area_per_valve_mm2,
                certified_capacity_kg_h=capacity_kg_h,
                certified_capacity_margin_pct=((capacity_kg_h / required_flow_per_valve_kg_h) - 1.0) * 100.0,
                effective_area_margin_pct=((model.effective_area_mm2 / required_effective_area_per_valve_mm2) - 1.0) * 100.0,
                kb_used=kb_used,
                kb_source=kb_source,
                meets_required_effective_area=meets_effective_area,
                meets_required_capacity=meets_capacity,
                warnings=warnings,
            )
        )

    selected = next(
        (
            item
            for item in evaluated
            if item.meets_required_effective_area and item.meets_required_capacity
        ),
        None,
    )
    catalog_name = candidate_models[0].catalog_name if candidate_models else "Unknown catalog"
    return VendorCatalogEvaluation(catalog_name=catalog_name, selected=selected, evaluated=evaluated)
