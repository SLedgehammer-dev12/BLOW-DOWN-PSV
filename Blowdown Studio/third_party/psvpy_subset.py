"""Subset of kevindorma/psvpy vendored under the MIT license.

This file intentionally carries only the small function set used by Blowdown
Studio for optional cross-checking and helper calculations:

- steam sizing
- liquid sizing
- thermal expansion / vaporization / pool-fire helper rates

Upstream source:
https://github.com/kevindorma/psvpy
"""

from __future__ import annotations

import math


_KSH_T_C: tuple[float, ...] = (
    93.33333333,
    148.8888889,
    204.4444444,
    260.0,
    315.5555556,
    371.1111111,
    426.6666667,
    482.2222222,
    537.7777778,
    565.5555556,
)

_KSH_P_KPA: tuple[float, ...] = (
    137.8951817,
    344.7379543,
    689.4759087,
    1034.213863,
    1378.951817,
    1723.689772,
    2068.427726,
    2413.16568,
    2757.903635,
    3102.641589,
    3447.379543,
    3792.117498,
    4136.855452,
    4826.331361,
    5515.807269,
    6205.283178,
    6894.759087,
    7584.234995,
    8273.710904,
    8963.186813,
    9652.662721,
    10342.13863,
    12065.8284,
    13789.51817,
    17236.89772,
    20684.27726,
)

_KSH_TABLE: tuple[tuple[float, ...], ...] = (
    (1.0, 0.99455814, 0.987, 0.93, 0.882, 0.841, 0.805, 0.774, 0.745, 0.732),
    (1.0, 0.997925224, 0.987, 0.93, 0.882, 0.841, 0.805, 0.774, 0.745, 0.732),
    (1.0, 1.0, 0.998, 0.935, 0.885, 0.843, 0.807, 0.775, 0.746, 0.733),
    (1.0, 1.0, 0.984, 0.94, 0.888, 0.846, 0.808, 0.776, 0.747, 0.733),
    (1.0, 1.0, 0.979, 0.945, 0.892, 0.848, 0.81, 0.777, 0.748, 0.734),
    (1.0, 1.0, 1.0, 0.951, 0.895, 0.85, 0.812, 0.778, 0.749, 0.735),
    (1.0, 1.0, 1.0, 0.957, 0.898, 0.852, 0.813, 0.78, 0.75, 0.736),
    (1.0, 1.0, 1.0, 0.963, 0.902, 0.854, 0.815, 0.781, 0.75, 0.736),
    (1.0, 1.0, 1.0, 0.963, 0.906, 0.857, 0.816, 0.782, 0.751, 0.737),
    (1.0, 1.0, 1.0, 0.961, 0.909, 0.859, 0.818, 0.783, 0.752, 0.738),
    (1.0, 1.0, 1.0, 0.961, 0.914, 0.862, 0.82, 0.784, 0.753, 0.739),
    (1.0, 1.0, 1.0, 0.962, 0.918, 0.864, 0.822, 0.785, 0.754, 0.74),
    (1.0, 1.0, 1.0, 0.964, 0.922, 0.867, 0.823, 0.787, 0.755, 0.74),
    (1.0, 1.0, 1.0, 1.0, 0.931, 0.872, 0.827, 0.789, 0.757, 0.742),
    (1.0, 1.0, 1.0, 1.0, 0.942, 0.878, 0.83, 0.792, 0.759, 0.744),
    (1.0, 1.0, 1.0, 1.0, 0.953, 0.883, 0.834, 0.794, 0.76, 0.745),
    (1.0, 1.0, 1.0, 1.0, 0.959, 0.89, 0.838, 0.797, 0.762, 0.747),
    (1.0, 1.0, 1.0, 1.0, 0.962, 0.896, 0.842, 0.8, 0.764, 0.749),
    (1.0, 1.0, 1.0, 1.0, 0.966, 0.903, 0.846, 0.802, 0.766, 0.75),
    (1.0, 1.0, 1.0, 1.0, 0.973, 0.91, 0.85, 0.805, 0.768, 0.752),
    (1.0, 1.0, 1.0, 1.0, 0.982, 0.918, 0.854, 0.808, 0.77, 0.754),
    (1.0, 1.0, 1.0, 1.0, 0.993, 0.926, 0.859, 0.811, 0.772, 0.755),
    (1.0, 1.0, 1.0, 1.0, 1.0, 0.94, 0.862, 0.81, 0.77, 0.752),
    (1.0, 1.0, 1.0, 1.0, 1.0, 0.952, 0.861, 0.805, 0.762, 0.744),
    (1.0, 1.0, 1.0, 1.0, 1.0, 0.951, 0.852, 0.787, 0.74, 0.721),
    (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.831, 0.753, 0.704, 0.684),
)


def waterTsat(P_kPa: float) -> float:
    ln_p = math.log(P_kPa)
    inv_t = 0.00379302 + (-0.000220828 * ln_p) + (-0.000425693 / ln_p)
    return (1.0 / inv_t) - 273.15


def waterPsat(T_c: float) -> float:
    t_k = T_c + 273.15
    ln_psat = 116.6408494 + (-8572.035364 / t_k) + (0.013736471 * t_k) + (-14.73621925 * math.log(t_k))
    return math.exp(ln_psat) / 1000.0


def _interp_linear(x0: float, x1: float, y0: float, y1: float, x: float) -> float:
    if abs(x1 - x0) < 1e-12:
        return y0
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))


def _find_bracket(points: tuple[float, ...], value: float) -> tuple[int, int]:
    if value < points[0] or value > points[-1]:
        raise ValueError("Value is outside the psvpy interpolation table.")
    for idx in range(len(points) - 1):
        if points[idx] <= value <= points[idx + 1]:
            return idx, idx + 1
    return len(points) - 2, len(points) - 1


def getKsh(PkPa: float, State: float | str) -> float:
    if not isinstance(State, (float, int)):
        return 1.0

    state_c = float(State)
    if waterPsat(state_c) < PkPa:
        raise ValueError("Temperature is in subcooled region.")

    temp_idx0, temp_idx1 = _find_bracket(_KSH_T_C, state_c)
    pres_idx0, pres_idx1 = _find_bracket(_KSH_P_KPA, PkPa)

    t0 = _KSH_T_C[temp_idx0]
    t1 = _KSH_T_C[temp_idx1]
    p0 = _KSH_P_KPA[pres_idx0]
    p1 = _KSH_P_KPA[pres_idx1]

    q11 = _KSH_TABLE[pres_idx0][temp_idx0]
    q21 = _KSH_TABLE[pres_idx0][temp_idx1]
    q12 = _KSH_TABLE[pres_idx1][temp_idx0]
    q22 = _KSH_TABLE[pres_idx1][temp_idx1]

    at_p0 = _interp_linear(t0, t1, q11, q21, state_c)
    at_p1 = _interp_linear(t0, t1, q12, q22, state_c)
    return _interp_linear(p0, p1, at_p0, at_p1, PkPa)


def thermExpansionRate(heat: float, alpha: float, heatCap: float) -> float:
    return 3600.0 * alpha * heat / heatCap


def liquidVaporizeReliefRate(heat: float, latent: float) -> float:
    return heat * (1.0 / latent) * 3600.0


def poolFireReliefRate(wettedAreaM2: float, latent: float, prompt: str) -> float:
    c1 = 43200.0 if prompt == "prompt" else 70900.0
    heat_w = c1 * wettedAreaM2**0.82
    return (heat_w / 1000.0) * (1.0 / latent) * 3600.0


def PSVsteamFlux(Pkpa: float, State: float | str) -> float:
    c_napier = 51.45
    kd = 0.975
    ksh = getKsh(Pkpa, State)
    kb = 1.0
    kn = 1.0
    if Pkpa > 10300.0:
        kn = (2.7644 * Pkpa / 100.0 - 1000.0) / (3.3242 * Pkpa / 100.0 - 1061.0)
    p_psi = Pkpa * (14.503773800721813 / 100.0)
    return c_napier * kd * p_psi * ksh * kb * kn / (2.205 * 25.4**2)


def PSVsteamSize(Wkg: float, Pkpa: float, State: float | str) -> float:
    if Wkg <= 0.0:
        raise ValueError("Steam flow must be positive.")
    return Wkg / PSVsteamFlux(Pkpa, State)


def PSVliquidSize(W: float, P: float, Pback: float, d: float, mu: float) -> float:
    if W <= 0.0:
        raise ValueError("Liquid flow must be positive.")
    if P <= Pback:
        raise ValueError("Liquid inlet pressure must exceed backpressure.")
    if d <= 0.0 or mu <= 0.0:
        raise ValueError("Liquid density and viscosity must be positive.")

    converge_eps = 1.0e-4
    coeff_si = 11.78
    q_l_min = 1000.0 * W / (d * 60.0)
    specific_gravity = d / 1000.0

    kd = 0.65
    kw = 1.0
    kc = 1.0
    kv = 1.0

    area_mm2 = 0.0
    err_converge = 1.0
    iteration = 1
    while err_converge > converge_eps and iteration < 10:
        root_term = math.sqrt(specific_gravity / (P - Pback))
        coeff_term = coeff_si * q_l_min / (kd * kw * kc * kv)
        area_mm2 = coeff_term * root_term
        reynolds = q_l_min * 18800.0 * specific_gravity / (mu * math.sqrt(area_mm2))
        old_kv = kv
        kv = 1.0 / (0.9935 + 2.878 / math.sqrt(reynolds) + 342.75 / (reynolds**1.5))
        err_converge = abs(old_kv - kv)
        iteration += 1
    return area_mm2
