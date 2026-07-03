from __future__ import annotations

DEFAULT_UNIT_PREFS = {
    "pressure": "barg",
    "temperature": "C",
    "mass": "kg",
    "mass_flow": "kg/h",
    "vol_flow": "m3/h",
    "area_small": "mm2",
    "area_large": "m2",
    "length": "m",
    "htc": "W/m2K",
    "time": "s",
    "velocity": "m/s",
    "power": "kW",
    "sound_level": "dB",
}

VALID_UNITS = {
    "pressure": ["barg", "bara", "psig", "psia", "MPa", "kPa", "atm"],
    "temperature": ["C", "K", "F"],
    "mass": ["kg", "lb", "ton"],
    "mass_flow": ["kg/h", "lb/h", "kg/s"],
    "vol_flow": ["m3/h", "ft3/min", "SCFM", "MMSCFD", "Nm3/h"],
    "area_small": ["mm2", "cm2", "in2"],
    "area_large": ["m2", "ft2"],
    "length": ["m", "mm", "ft", "in"],
    "htc": ["W/m2K"],
    "time": ["s", "min"],
    "velocity": ["m/s", "ft/s"],
    "power": ["kW", "MW", "HP", "BTU/s"],
    "sound_level": ["dB"],
}

UNIT_LABELS = {
    "pressure": "Basinc",
    "temperature": "Sicaklik",
    "mass": "Kutle",
    "mass_flow": "Kutlesel Debi",
    "vol_flow": "Hacimsel Debi",
    "area_small": "Kucuk Alan",
    "area_large": "Buyuk Alan",
    "length": "Uzunluk",
    "htc": "Isi Transferi",
    "time": "Sure",
    "velocity": "Hiz",
    "power": "Guc",
    "sound_level": "Ses Seviyesi",
}

LENGTH_UNIT_MAP = {"m": 1.0, "mm": 0.001, "cm": 0.01, "in": 0.0254, "ft": 0.3048}
AREA_UNIT_MAP = {"m2": 1.0, "mm2": 1e-6, "cm2": 1e-4, "in2": 0.00064516, "ft2": 0.092903}
HTC_UNIT_MAP = {"W/m2K": 1.0, "BTU/hr·ft2·F": 5.678263}


def format_pressure(value_pa: float, unit: str, converter) -> str:
    val = converter.convert_pressure_from_pa(value_pa, unit)
    return f"{val:.3f} {unit}"


def format_temperature(value_k: float, unit: str, converter=None) -> str:
    if unit == "C":
        val = value_k - 273.15
        return f"{val:.2f} °C"
    if unit == "F":
        val = (value_k - 273.15) * 9.0 / 5.0 + 32.0
        return f"{val:.2f} °F"
    return f"{value_k:.2f} K"


def format_mass(value_kg: float, unit: str, converter) -> str:
    val = converter.convert_mass(value_kg, unit)
    return f"{val:,.3f} {unit}"


def format_mass_flow(value_kg_h: float, unit: str, converter) -> str:
    if unit == "kg/h":
        return f"{value_kg_h:,.2f} kg/h"
    if unit == "lb/h":
        return f"{value_kg_h / 0.453592:,.2f} lb/h"
    if unit == "kg/s":
        return f"{value_kg_h / 3600.0:,.4f} kg/s"
    return f"{value_kg_h:,.2f} kg/h"


def format_vol_flow(value_m3_h: float, unit: str) -> str:
    if unit == "m3/h":
        return f"{value_m3_h:,.2f} m3/h"
    if unit == "ft3/min":
        return f"{value_m3_h * 0.5886:,.2f} ft3/min"
    if unit == "MMSCFD":
        return f"{value_m3_h * 0.0008476:,.3f} MMSCFD"
    return f"{value_m3_h:,.2f} m3/h"


def format_area(value_m2: float, unit: str) -> str:
    factor = AREA_UNIT_MAP.get(unit, 1.0)
    val = value_m2 / factor
    if unit == "mm2":
        return f"{val:,.1f} mm2"
    return f"{val:.6f} {unit}"


def format_length(value_m: float, unit: str) -> str:
    factor = LENGTH_UNIT_MAP.get(unit, 1.0)
    val = value_m / factor
    if unit == "mm":
        return f"{val:.0f} mm"
    return f"{val:.2f} {unit}"


def format_htc(value_wm2k: float, unit: str) -> str:
    factor = HTC_UNIT_MAP.get(unit, 1.0)
    val = value_wm2k / factor
    return f"{val:,.2f} {unit}"


def format_time(value_s: float, unit: str) -> str:
    if unit == "min":
        return f"{value_s / 60.0:.1f} min"
    return f"{value_s:.1f} s"


def format_velocity(value_m_s: float, unit: str) -> str:
    if unit == "ft/s":
        return f"{value_m_s / 0.3048:.2f} ft/s"
    return f"{value_m_s:.2f} m/s"


def format_power(value_w: float, unit: str) -> str:
    if unit == "MW":
        return f"{value_w / 1e6:.3f} MW"
    if unit == "HP":
        return f"{value_w / 745.7:.2f} HP"
    if unit == "BTU/s":
        return f"{value_w / 1055.06:.2f} BTU/s"
    return f"{value_w / 1000.0:.2f} kW"


def format_sound_level(value_db: float, unit: str) -> str:
    return f"{value_db:.1f} {unit} ref 1pW"
