"""
Acoustic and AIV screening utilities.

These functions provide screening-level calculations only. They are not a
replacement for a full API 521 / EI acoustic fatigue assessment.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

import CoolProp.CoolProp as CP


REFERENCE_SOUND_POWER_W = 1.0e-12


def calculate_acoustic_velocity(
    components: Dict[str, float],
    pressure_pa: float,
    temperature_k: float,
) -> float:
    """Return real-gas speed of sound from CoolProp."""
    state = CP.AbstractState("HEOS", "&".join(components.keys()))
    state.set_mole_fractions(list(components.values()))
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    return state.speed_sound()


def calculate_discharge_velocity(
    mass_flow_kg_s: float,
    gas_density_kg_m3: float,
    pipe_diameter_mm: float,
) -> float:
    """Return bulk discharge velocity in the line."""
    a_pipe_m2 = math.pi * ((pipe_diameter_mm / 1000.0) / 2.0) ** 2
    return mass_flow_kg_s / max(gas_density_kg_m3 * a_pipe_m2, 1e-12)


def check_acoustic_fatigue(
    discharge_velocity_m_s: float,
    acoustic_velocity_m_s: float,
    frequency_hz: float = 1000.0,
    pipe_diameter_mm: float = 100.0,
    gas_density_kg_m3: float = 1.0,
    acoustic_efficiency: Optional[float] = None,
) -> Dict[str, float | str]:
    """
    Screening-level acoustic fatigue indicator.

    Acoustic power is estimated from acoustic efficiency times jet mechanical
    power, using jet kinetic power as a screening proxy. This preserves
    dimensional consistency and is closer to published screening approaches
    than the legacy placeholder formula.
    """
    mach = discharge_velocity_m_s / max(acoustic_velocity_m_s, 1e-12)

    if acoustic_efficiency is None:
        if mach < 0.3:
            acoustic_efficiency = 1.0e-4
        elif mach < 0.5:
            acoustic_efficiency = 5.0e-4
        else:
            acoustic_efficiency = 1.0e-3

    a_pipe_m2 = math.pi * ((pipe_diameter_mm / 1000.0) / 2.0) ** 2
    mass_flow_kg_s = max(gas_density_kg_m3, 1e-9) * max(discharge_velocity_m_s, 0.0) * a_pipe_m2
    jet_mechanical_power_w = 0.5 * mass_flow_kg_s * (max(discharge_velocity_m_s, 0.0) ** 2)
    acoustic_power_w = acoustic_efficiency * jet_mechanical_power_w
    sound_power_level_db = 10.0 * math.log10(max(acoustic_power_w, REFERENCE_SOUND_POWER_W) / REFERENCE_SOUND_POWER_W)

    if mach < 0.3:
        risk = "LOW"
        recommendation = "Acoustic fatigue risk dusuk. Standart screening yeterli."
    elif mach < 0.5:
        risk = "MODERATE"
        recommendation = "Orta risk. Ayrintili AIV / acoustic fatigue analizi onerilir."
    elif mach < 0.7:
        risk = "HIGH"
        recommendation = "Yuksek risk. Acoustic fatigue ve branch screening gerekir."
    else:
        risk = "CRITICAL"
        recommendation = "Kritik risk. Boyut, discharge routing veya akustik koruma yeniden degerlendirilmeli."

    return {
        "status": "WARNING" if mach > 0.3 else "OK",
        "mach": mach,
        "jet_mechanical_power_w": jet_mechanical_power_w,
        "acoustic_power": acoustic_power_w,
        "sound_power_level_db": sound_power_level_db,
        "acoustic_efficiency": acoustic_efficiency,
        "fatigue_risk": risk,
        "recommendation": recommendation,
        "screening_frequency_hz": frequency_hz,
        "method_note": (
            "Screening sound power uses acoustic-efficiency x jet mechanical power; "
            "this is not a full API 521 / EI fatigue assessment."
        ),
    }


def calculate_aiv_vibration(
    mach_number: float,
    pipe_diameter_mm: float,
    frequency_hz: float = 1000.0,
) -> Dict[str, float | bool | str | None]:
    """
    Return a simple AIV screening indicator.

    The previous amplitude placeholder was removed because it had no valid
    engineering basis. This function now returns only a screening index and a
    resonance proximity flag.
    """
    natural_frequency_hz = 1000.0 / max(pipe_diameter_mm / 100.0, 1e-9)
    aiv_screening_index = mach_number * math.sqrt(max(pipe_diameter_mm, 1e-9) / 100.0)
    if aiv_screening_index < 0.30:
        aiv_risk = "LOW"
    elif aiv_screening_index < 0.50:
        aiv_risk = "MODERATE"
    elif aiv_screening_index < 0.70:
        aiv_risk = "HIGH"
    else:
        aiv_risk = "CRITICAL"
    return {
        "amplitude_mm": None,
        "natural_frequency_hz": natural_frequency_hz,
        "resonance_risk": abs(natural_frequency_hz - frequency_hz) < 50.0,
        "aiv_screening_index": aiv_screening_index,
        "aiv_risk": aiv_risk,
        "method_note": "Amplitude placeholder kaldirildi; bu cikti kalibre edilmemis screening indeksidir.",
    }


def estimate_acoustic_damping(
    pipe_diameter_mm: float,
    insulation_thickness_mm: float = 0.0,
) -> float:
    """
    Return a placeholder damping thickness estimate.

    This helper remains a simplified screening placeholder and should not be
    treated as a design calculation.
    """
    del pipe_diameter_mm
    if insulation_thickness_mm > 25.0:
        return 0.0
    if insulation_thickness_mm > 10.0:
        return 5.0
    return 10.0
