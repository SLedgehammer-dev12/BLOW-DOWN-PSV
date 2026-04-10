from __future__ import annotations


def carbon_steel_cp_j_kgk(temperature_k: float) -> float:
    """
    Screening-level temperature-dependent specific heat for carbon steel.

    Piecewise-linear fit intended for blowdown wall thermal inertia estimates.
    The curve is conservative at cryogenic temperatures compared with a flat
    480 J/kg.K assumption and remains smooth across typical operating ranges.
    """
    anchors = (
        (80.0, 260.0),
        (150.0, 330.0),
        (200.0, 380.0),
        (250.0, 430.0),
        (300.0, 470.0),
        (350.0, 510.0),
        (400.0, 550.0),
        (500.0, 610.0),
        (700.0, 700.0),
    )

    if temperature_k <= anchors[0][0]:
        return anchors[0][1]
    if temperature_k >= anchors[-1][0]:
        return anchors[-1][1]

    for (t0, cp0), (t1, cp1) in zip(anchors, anchors[1:]):
        if t0 <= temperature_k <= t1:
            frac = (temperature_k - t0) / (t1 - t0)
            return cp0 + frac * (cp1 - cp0)
    return anchors[-1][1]
