from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


P_ATM = 101325.0


def _import_hyddown():
    hyddown_src = Path(__file__).resolve().parent.parent / "HydDown" / "src"
    if str(hyddown_src) not in sys.path:
        sys.path.insert(0, str(hyddown_src))
    try:
        from hyddown import HydDown
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "HydDown import edilemedi. Gerekli bağımlılık eksik olabilir (ör. cerberus/scipy/tqdm)."
        ) from exc

    return HydDown


def _build_fluid_string(composition: dict[str, float]) -> str:
    if len(composition) == 1:
        return next(iter(composition.keys()))
    parts = [f"{name}[{fraction:.12g}]" for name, fraction in composition.items()]
    return "&".join(parts)


def build_hyddown_input(inputs: dict, area_m2: float) -> dict:
    if any(key not in inputs for key in ("D_in_m", "L_m", "t_m")):
        raise ValueError("HydDown motoru için geometrik giriş zorunludur: iç çap, uzunluk ve et kalınlığı girilmelidir.")

    system_type = inputs.get("system_type", "Boru Hattı (Pipeline)")
    orientation = "horizontal" if "Boru" in system_type else "vertical"
    time_step = max(0.25, min(5.0, inputs["t_target_sec"] / 500.0))

    hyddown_input = {
        "vessel": {
            "length": inputs["L_m"],
            "diameter": inputs["D_in_m"],
            "thickness": inputs["t_m"],
            "heat_capacity": 480.0,
            "density": 7850.0,
            "orientation": orientation,
        },
        "initial": {
            "temperature": inputs["T0_k"],
            "pressure": inputs["p0_pa"],
            "fluid": _build_fluid_string(inputs["composition"]),
        },
        "calculation": {
            "type": "energybalance",
            "time_step": time_step,
            "end_time": inputs["t_target_sec"] * 10.0,
        },
        "valve": {
            "flow": "discharge",
            "type": "orifice",
            "diameter": math.sqrt(4.0 * area_m2 / math.pi),
            "discharge_coef": inputs.get("Cd", 0.975) or 0.975,
            "back_pressure": inputs.get("p_downstream", P_ATM),
        },
    }

    if inputs.get("HT_enabled", True):
        hyddown_input["heat_transfer"] = {
            "type": "specified_h",
            "temp_ambient": inputs["T0_k"],
            "h_outer": 0.0,
            "h_inner": "calc",
        }
    else:
        hyddown_input["heat_transfer"] = {
            "type": "specified_Q",
            "Q_fix": 0.0,
        }

    return hyddown_input


def _time_to_target(time_array: np.ndarray, pressure_array: np.ndarray, target_pressure_pa: float) -> float:
    below_target = np.where(pressure_array <= target_pressure_pa)[0]
    if len(below_target) == 0:
        return float(time_array[-1])

    idx = int(below_target[0])
    if idx == 0:
        return float(time_array[0])

    t1 = float(time_array[idx - 1])
    t2 = float(time_array[idx])
    p1 = float(pressure_array[idx - 1])
    p2 = float(pressure_array[idx])
    if abs(p2 - p1) < 1e-12:
        return t2

    fraction = (target_pressure_pa - p1) / (p2 - p1)
    fraction = max(0.0, min(1.0, fraction))
    return t1 + fraction * (t2 - t1)


def run_hyddown_blowdown_simulation(
    inputs: dict,
    area_m2: float,
    progress_callback=None,
    abort_flag=None,
    silent: bool = False,
):
    if abort_flag and abort_flag.is_set():
        return None

    HydDown = _import_hyddown()
    model = HydDown(build_hyddown_input(inputs, area_m2))
    try:
        model.run(disable_pbar=True)
    except Exception as exc:
        raise RuntimeError(f"HydDown çözümü başarısız oldu (alan={area_m2:.6g} m²).") from exc

    if abort_flag and abort_flag.is_set():
        return None

    time_array = np.asarray(model.time_array, dtype=float)
    pressure_array = np.asarray(model.P, dtype=float)
    time_to_target = _time_to_target(time_array, pressure_array, inputs["p_target_blowdown_pa"])

    if silent:
        return time_to_target

    df = pd.DataFrame(
        {
            "t": time_array,
            "p_sys": pressure_array,
            "mdot_kg_s": np.asarray(model.mass_rate, dtype=float),
            "T_sys": np.asarray(model.T_fluid, dtype=float),
            "T_wall": np.asarray(model.T_vessel, dtype=float),
            "h_in": np.asarray(model.h_inside, dtype=float),
            "rho_g": np.asarray(model.rho, dtype=float),
            "m_sys": np.asarray(model.mass_fluid, dtype=float),
        }
    )
    df.attrs["engine"] = "HydDown"
    df.attrs["time_to_target"] = time_to_target
    return df


def _safe_hyddown_time(inputs: dict, area_m2: float, abort_flag=None) -> float | None:
    try:
        return run_hyddown_blowdown_simulation(inputs, area_m2, abort_flag=abort_flag, silent=True)
    except RuntimeError:
        return None


def find_hyddown_blowdown_area(inputs: dict, progress_callback=None, abort_flag=None) -> float | None:
    target_time = inputs["t_target_sec"]
    area_low_m2 = 1e-8
    area_high_m2 = max(1e-6, min(1e-3, math.pi * inputs["D_in_m"] ** 2 / 4.0))
    max_area_m2 = max(area_high_m2, math.pi * inputs["D_in_m"] ** 2 / 4.0)
    max_iter = 24
    area_mid_m2 = area_high_m2

    sim_time_high = _safe_hyddown_time(inputs, area_high_m2, abort_flag=abort_flag)
    expand_iter = 0
    while sim_time_high is not None and sim_time_high > target_time and area_high_m2 < max_area_m2:
        area_low_m2 = area_high_m2
        area_high_m2 = min(max_area_m2, area_high_m2 * 2.0)
        sim_time_high = _safe_hyddown_time(inputs, area_high_m2, abort_flag=abort_flag)
        expand_iter += 1
        if expand_iter > 20:
            break

    if sim_time_high is None:
        pass
    elif sim_time_high > target_time and area_high_m2 >= max_area_m2 * 0.999:
        raise ValueError("HydDown motoru ile hedef süreyi sağlayan alan, mevcut geometriye göre çok büyük görünüyor.")

    for i in range(max_iter):
        if abort_flag and abort_flag.is_set():
            return None
        if progress_callback:
            progress_callback(i, max_iter, text=f"HydDown boyutlandırma ({i + 1}/{max_iter})...")

        area_mid_m2 = 0.5 * (area_low_m2 + area_high_m2)
        sim_time = _safe_hyddown_time(inputs, area_mid_m2, abort_flag=abort_flag)
        if sim_time is None:
            area_high_m2 = area_mid_m2
            continue
        if abort_flag and abort_flag.is_set():
            return None

        if abs(sim_time - target_time) / max(target_time, 1e-9) < 0.02:
            return area_mid_m2
        if sim_time > target_time:
            area_low_m2 = area_mid_m2
        else:
            area_high_m2 = area_mid_m2

    return area_mid_m2
