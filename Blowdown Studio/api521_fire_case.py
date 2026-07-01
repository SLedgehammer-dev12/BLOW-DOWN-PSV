from __future__ import annotations

from dataclasses import dataclass, field
import math

from constants import P_ATM


POOL_FIRE_COEFFICIENTS_SI = {
    "Adequate drainage + firefighting": 43200.0,
    "Poor drainage / limited firefighting": 70900.0,
}


@dataclass
class FireCaseSizingResult:
    design_pressure_pa: float
    target_pressure_pa: float
    target_time_s: float
    scenario: str
    environment_factor: float
    heat_input_w: float | None = None
    wetted_area_m2: float | None = None
    coefficient_si: float | None = None
    warnings: list[str] = field(default_factory=list)


def build_fire_case_target(
    *,
    design_pressure_pa: float,
    target_fraction_of_design_gauge: float = 0.5,
    target_time_s: float = 15.0 * 60.0,
) -> FireCaseSizingResult:
    if design_pressure_pa <= P_ATM:
        raise ValueError("Fire case icin design pressure atmosfer basincinin uzerinde olmalidir.")

    design_gauge_pa = max(design_pressure_pa - P_ATM, 0.0)
    target_pressure_pa = P_ATM + target_fraction_of_design_gauge * design_gauge_pa
    return FireCaseSizingResult(
        design_pressure_pa=design_pressure_pa,
        target_pressure_pa=target_pressure_pa,
        target_time_s=target_time_s,
        scenario="API 521 depressuring target",
        environment_factor=1.0,
    )


def estimate_cylindrical_wetted_area_m2(
    *,
    outer_diameter_m: float,
    length_m: float,
    include_ends: bool = True,
) -> float:
    if outer_diameter_m <= 0.0 or length_m <= 0.0:
        raise ValueError("Fire wetted area icin diameter ve length pozitif olmalidir.")
    area = math.pi * outer_diameter_m * length_m
    if include_ends:
        area += 0.5 * math.pi * outer_diameter_m**2
    return area


def calculate_pool_fire_heat_input_si(
    *,
    wetted_area_m2: float,
    environment_factor: float = 1.0,
    scenario: str = "Adequate drainage + firefighting",
) -> tuple[float, float]:
    if wetted_area_m2 <= 0.0:
        raise ValueError("Fire heat input icin wetted area pozitif olmalidir.")
    if environment_factor <= 0.0:
        raise ValueError("Environment factor pozitif olmalidir.")
    coefficient_si = POOL_FIRE_COEFFICIENTS_SI.get(scenario)
    if coefficient_si is None:
        raise ValueError(f"Desteklenmeyen fire case scenario: {scenario}")
    heat_input_w = coefficient_si * environment_factor * (wetted_area_m2 ** 0.82)
    return heat_input_w, coefficient_si


def build_pool_fire_case_screening(
    *,
    design_pressure_pa: float,
    outer_diameter_m: float | None = None,
    length_m: float | None = None,
    environment_factor: float = 1.0,
    scenario: str = "Adequate drainage + firefighting",
) -> FireCaseSizingResult:
    result = build_fire_case_target(design_pressure_pa=design_pressure_pa)
    result.scenario = scenario
    result.environment_factor = environment_factor

    if outer_diameter_m is None or length_m is None:
        result.warnings.append(
            "Geometri verilmedigi icin API 521 open-pool-fire heat input screening hesaplanamadi."
        )
        return result

    wetted_area_m2 = estimate_cylindrical_wetted_area_m2(
        outer_diameter_m=outer_diameter_m,
        length_m=length_m,
        include_ends=True,
    )
    heat_input_w, coefficient_si = calculate_pool_fire_heat_input_si(
        wetted_area_m2=wetted_area_m2,
        environment_factor=environment_factor,
        scenario=scenario,
    )
    result.wetted_area_m2 = wetted_area_m2
    result.heat_input_w = heat_input_w
    result.coefficient_si = coefficient_si
    result.warnings.append(
        "API 521 fire case bu surumde screening seviyesindedir; 50% design pressure / 15 min hedefi ve open-pool-fire heat input kabulu kullanildi."
    )
    return result
