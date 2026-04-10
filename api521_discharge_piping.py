"""
API 521 discharge piping screening utilities.

The calculations here are screening-level only. They are intended to estimate
loss coefficients and pressure drop, not to replace a full API 520-2 / 521
outlet system analysis.
"""

from __future__ import annotations

import math
from typing import Dict


def calculate_discharge_piping_loss(
    pipe_length_m: float,
    pipe_diameter_mm: float,
    elbow_count: int = 0,
    tee_count: int = 0,
    valve_count: int = 0,
    globe_valve_count: int = 0,
    check_valve_count: int = 0,
    butterfly_valve_count: int = 0,
    roughness_mm: float = 0.045,
    mass_flow_kg_s: float | None = None,
    gas_density_kg_m3: float | None = None,
    gas_viscosity_pa_s: float | None = None,
    reynolds_number: float | None = None,
) -> Dict:
    """
    Return screening-level K factors and equivalent length for a discharge line.

    If mass flow, density, and viscosity are supplied, Reynolds number is
    calculated from the process conditions. Otherwise a conservative fallback
    Reynolds number is used.
    """
    d_m = pipe_diameter_mm / 1000.0
    if d_m <= 0.0:
        raise ValueError("Pipe diameter must be positive.")
    if pipe_length_m < 0.0:
        raise ValueError("Pipe length cannot be negative.")

    area_m2 = math.pi * (d_m ** 2) / 4.0
    velocity_m_s = None

    if reynolds_number is not None:
        Re = max(float(reynolds_number), 1.0)
    elif (
        mass_flow_kg_s is not None
        and gas_density_kg_m3 is not None
        and gas_viscosity_pa_s is not None
        and gas_density_kg_m3 > 0.0
        and gas_viscosity_pa_s > 0.0
    ):
        velocity_m_s = mass_flow_kg_s / max(gas_density_kg_m3 * area_m2, 1e-12)
        Re = max(gas_density_kg_m3 * velocity_m_s * d_m / gas_viscosity_pa_s, 1.0)
    else:
        Re = 1.0e5

    epsilon_over_d = roughness_mm / max(pipe_diameter_mm, 1e-12)
    friction_factor = (-2.0 * math.log10(epsilon_over_d / 3.7 + 5.74 / (Re ** 0.9))) ** -2
    pipe_friction_loss = friction_factor * (pipe_length_m / d_m)

    fitting_losses = {
        "90_degree_elbow": 0.30,
        "tee_straight": 0.20,
        "globe_valve": 10.0,
        "check_valve": 5.0,
        "butterfly_valve": 2.0,
        "generic_valve": 1.0,
    }

    fittings_K = (
        fitting_losses["90_degree_elbow"] * elbow_count
        + fitting_losses["tee_straight"] * tee_count
        + fitting_losses["globe_valve"] * globe_valve_count
        + fitting_losses["check_valve"] * check_valve_count
        + fitting_losses["butterfly_valve"] * butterfly_valve_count
        + fitting_losses["generic_valve"] * valve_count
    )

    total_K = pipe_friction_loss + fittings_K
    equivalent_length_m = total_K * d_m / max(friction_factor, 1e-12)

    return {
        "total_K": total_K,
        "pipe_friction_loss": pipe_friction_loss,
        "fittings_loss": fittings_K,
        "equivalent_length_m": equivalent_length_m,
        "friction_factor": friction_factor,
        "reynolds_number": Re,
        "velocity_m_s": velocity_m_s,
        "details": {
            "pipe": f"{pipe_length_m:.1f} m pipe",
            "elbows": f"{elbow_count} x 90 deg elbow",
            "tees": f"{tee_count} x tee",
            "globe_valves": f"{globe_valve_count} x globe valve",
            "check_valves": f"{check_valve_count} x check valve",
            "butterfly_valves": f"{butterfly_valve_count} x butterfly valve",
            "generic_valves": f"{valve_count} x generic valve",
            "roughness_mm": roughness_mm,
        },
    }


def estimate_discharge_piping_from_valve_size(
    valve_size_in: float,
    estimated_pipe_length_m: float = 5.0,
    elbow_count: int = 2,
    tee_count: int = 0,
    globe_valve_count: int = 0,
    check_valve_count: int = 1,
    butterfly_valve_count: int = 0,
) -> Dict:
    pipe_diameter_mm = valve_size_in * 25.4
    return calculate_discharge_piping_loss(
        pipe_length_m=estimated_pipe_length_m,
        pipe_diameter_mm=pipe_diameter_mm,
        elbow_count=elbow_count,
        tee_count=tee_count,
        globe_valve_count=globe_valve_count,
        check_valve_count=check_valve_count,
        butterfly_valve_count=butterfly_valve_count,
    )


def calculate_backpressure_drop(
    discharge_K: float,
    gas_density_kg_m3: float,
    velocity_m_s: float,
) -> float:
    return discharge_K * (gas_density_kg_m3 * velocity_m_s ** 2 / 2.0)
