from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Iterable

import CoolProp.CoolProp as CP


R_U = 8314.462618
P_ATM = 101325.0


@dataclass
class PSVGasSizingResult:
    A_req_m2: float
    relieving_pressure_pa: float
    relieving_temperature_k: float
    backpressure_pa: float
    set_pressure_pa: float
    overpressure_pct: float
    flow_regime: str
    is_critical: bool
    k_ideal: float
    k_real: float
    Z: float
    MW_kg_kmol: float
    Kd: float
    Kc: float
    Kb_used: float
    F2: float | None
    equation_id: str
    critical_pressure_ratio: float
    warnings: list[str] = field(default_factory=list)
    rho_relieving_kg_m3: float | None = None
    h_relieving_j_kg: float | None = None

    @property
    def A_req_mm2(self) -> float:
        return self.A_req_m2 * 1e6

    @property
    def set_pressure_gauge_pa(self) -> float:
        return max(self.set_pressure_pa - P_ATM, 0.0)

    @property
    def backpressure_gauge_pa(self) -> float:
        return max(self.backpressure_pa - P_ATM, 0.0)

    @property
    def backpressure_pct_of_set(self) -> float:
        if self.set_pressure_gauge_pa <= 0.0:
            return 0.0
        return (self.backpressure_gauge_pa / self.set_pressure_gauge_pa) * 100.0


def normalize_composition(composition: Dict[str, float]) -> Dict[str, float]:
    total = sum(composition.values())
    if total <= 0.0:
        raise ValueError("Kompozisyon toplamı sıfır veya negatif olamaz.")
    return {name: frac / total for name, frac in composition.items()}


def relieving_pressure_from_set_pressure(set_pressure_pa: float, overpressure_pct: float) -> float:
    set_pressure_gauge_pa = max(set_pressure_pa - P_ATM, 0.0)
    return set_pressure_pa + set_pressure_gauge_pa * overpressure_pct / 100.0


def critical_pressure_ratio(k_ideal: float) -> float:
    return (2.0 / (k_ideal + 1.0)) ** (k_ideal / (k_ideal - 1.0))


def coefficient_c_si(k_ideal: float) -> float:
    return 0.03948 * math.sqrt(k_ideal * (2.0 / (k_ideal + 1.0)) ** ((k_ideal + 1.0) / (k_ideal - 1.0)))


def coefficient_f2(k_ideal: float, pressure_ratio: float) -> float:
    if pressure_ratio <= 0.0 or pressure_ratio >= 1.0:
        raise ValueError("Subkritik akış için P2/P1 oranı 0 ile 1 arasında olmalıdır.")
    numerator = (k_ideal / (k_ideal - 1.0)) * (pressure_ratio ** (2.0 / k_ideal))
    bracket = (1.0 - pressure_ratio ** ((k_ideal - 1.0) / k_ideal)) / (1.0 - pressure_ratio)
    return math.sqrt(numerator * bracket)


def _ideal_gas_k_from_state(state: CP.AbstractState) -> float:
    cp0_molar = state.cp0molar()
    cv0_molar = cp0_molar - 8.314462618
    return cp0_molar / cv0_molar


def _state_from_composition(
    composition: Dict[str, float], pressure_pa: float, temperature_k: float
) -> tuple[CP.AbstractState, float, float, float, float]:
    comp = normalize_composition(composition)
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.specify_phase(CP.iphase_gas)
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    k_real = state.cpmass() / state.cvmass()
    k_ideal = _ideal_gas_k_from_state(state)
    Z = state.compressibility_factor()
    MW_kg_kmol = state.molar_mass() * 1000.0
    return state, k_ideal, k_real, Z, MW_kg_kmol


def size_gas_or_vapor_area_api520(
    *,
    W_req_kg_h: float,
    relieving_pressure_pa: float,
    backpressure_pa: float,
    relieving_temperature_k: float,
    k_ideal: float,
    Z: float,
    MW_kg_kmol: float,
    valve_design: str,
    Kd: float = 0.975,
    Kc: float = 1.0,
    Kb: float | None = None,
    set_pressure_pa: float | None = None,
    overpressure_pct: float | None = None,
    k_real: float | None = None,
    rho_relieving_kg_m3: float | None = None,
    h_relieving_j_kg: float | None = None,
) -> PSVGasSizingResult:
    design_key = valve_design.strip().lower()
    if design_key not in {"conventional", "balanced bellows", "balanced spring", "pilot-operated"}:
        raise ValueError(f"Desteklenmeyen vana tasarım tipi: {valve_design}")

    if relieving_pressure_pa <= backpressure_pa:
        raise ValueError("Toplam backpressure, relieving pressure'dan küçük olmalıdır.")
    if relieving_temperature_k <= 0.0:
        raise ValueError("Relieving sıcaklığı mutlak sıfırın üzerinde olmalıdır.")

    pressure_ratio = backpressure_pa / relieving_pressure_pa
    pr_crit = critical_pressure_ratio(k_ideal)
    is_critical = pressure_ratio <= pr_crit
    warnings: list[str] = []
    F2 = None

    if is_critical:
        if design_key == "balanced bellows":
            kb_used = 1.0 if Kb is None else Kb
            if Kb is None and backpressure_pa > P_ATM * 1.001:
                warnings.append(
                    "Balanced bellows vana için Kb girilmedi; kritik akışta ön boyutlandırma Kb=1.0 varsayımı ile yapıldı. "
                    "Final seçim için üretici eğrisi gerekli."
                )
        else:
            kb_used = 1.0

        C = coefficient_c_si(k_ideal)
        area_mm2 = (
            W_req_kg_h
            * math.sqrt(relieving_temperature_k * Z / MW_kg_kmol)
            / (C * Kd * kb_used * Kc * (relieving_pressure_pa / 1000.0))
        )
        equation_id = "API 520-1 Eq. (9)"
        flow_regime = "Kritik"
    else:
        if design_key == "balanced bellows":
            if Kb is None:
                raise ValueError(
                    "Balanced bellows PRV için subkritik/backpressure servisinde üretici Kb değeri zorunludur."
                )
            kb_used = Kb
            C = coefficient_c_si(k_ideal)
            area_mm2 = (
                W_req_kg_h
                * math.sqrt(relieving_temperature_k * Z / MW_kg_kmol)
                / (C * Kd * kb_used * Kc * (relieving_pressure_pa / 1000.0))
            )
            equation_id = "API 520-1 Eq. (9) + üretici Kb"
        else:
            kb_used = 1.0
            F2 = coefficient_f2(k_ideal, pressure_ratio)
            p1_kpa = relieving_pressure_pa / 1000.0
            p2_kpa = backpressure_pa / 1000.0
            area_mm2 = (
                17.9
                * W_req_kg_h
                * math.sqrt(relieving_temperature_k * Z / (MW_kg_kmol * p1_kpa * (p1_kpa - p2_kpa)))
                / (F2 * Kd * Kc)
            )
            equation_id = "API 520-1 Eq. (19) + Eq. (22)"
        flow_regime = "Subkritik"

    result = PSVGasSizingResult(
        A_req_m2=area_mm2 / 1e6,
        relieving_pressure_pa=relieving_pressure_pa,
        relieving_temperature_k=relieving_temperature_k,
        backpressure_pa=backpressure_pa,
        set_pressure_pa=set_pressure_pa if set_pressure_pa is not None else relieving_pressure_pa,
        overpressure_pct=overpressure_pct if overpressure_pct is not None else 0.0,
        flow_regime=flow_regime,
        is_critical=is_critical,
        k_ideal=k_ideal,
        k_real=k_real if k_real is not None else k_ideal,
        Z=Z,
        MW_kg_kmol=MW_kg_kmol,
        Kd=Kd,
        Kc=Kc,
        Kb_used=kb_used,
        F2=F2,
        equation_id=equation_id,
        critical_pressure_ratio=pr_crit,
        warnings=warnings,
        rho_relieving_kg_m3=rho_relieving_kg_m3,
        h_relieving_j_kg=h_relieving_j_kg,
    )

    set_pressure_gauge_pa = max(result.set_pressure_pa - P_ATM, 0.0)
    if set_pressure_gauge_pa > 0.0 and result.backpressure_gauge_pa > 0.5 * set_pressure_gauge_pa:
        warnings.append(
            "Toplam backpressure, set pressure'ın %50'sini aşıyor. Üretici limiti ve özel backpressure kısıtları doğrulanmalıdır."
        )
    return result


def size_gas_or_vapor_area_from_state(
    *,
    composition: Dict[str, float],
    set_pressure_pa: float,
    overpressure_pct: float,
    relieving_temperature_k: float,
    backpressure_pa: float,
    valve_design: str,
    Kd: float = 0.975,
    Kc: float = 1.0,
    Kb: float | None = None,
) -> PSVGasSizingResult:
    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, overpressure_pct)
    state, k_ideal, k_real, Z, MW_kg_kmol = _state_from_composition(
        composition, relieving_pressure_pa, relieving_temperature_k
    )

    return size_gas_or_vapor_area_api520(
        W_req_kg_h=0.0,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=backpressure_pa,
        relieving_temperature_k=relieving_temperature_k,
        k_ideal=k_ideal,
        Z=Z,
        MW_kg_kmol=MW_kg_kmol,
        valve_design=valve_design,
        Kd=Kd,
        Kc=Kc,
        Kb=Kb,
        set_pressure_pa=set_pressure_pa,
        overpressure_pct=overpressure_pct,
        k_real=k_real,
        rho_relieving_kg_m3=state.rhomass(),
        h_relieving_j_kg=state.hmass(),
    )


def calculate_preliminary_gas_psv_area(inputs: Dict[str, float | Dict[str, float] | str | None]) -> PSVGasSizingResult:
    composition = normalize_composition(inputs["composition"])  # type: ignore[index]
    set_pressure_pa = float(inputs["set_pressure_pa"])  # type: ignore[index]
    overpressure_pct = float(inputs.get("overpressure_pct", 10.0))  # type: ignore[arg-type]
    relieving_temperature_k = float(inputs["relieving_temperature_k"])  # type: ignore[index]
    backpressure_pa = float(inputs.get("p_total_backpressure_pa", P_ATM))  # type: ignore[arg-type]
    valve_design = str(inputs.get("prv_design", "Conventional"))
    Kd = float(inputs.get("Kd", 0.975))  # type: ignore[arg-type]
    Kc = float(inputs.get("Kc", 1.0))  # type: ignore[arg-type]
    Kb_raw = inputs.get("Kb")
    Kb = None if Kb_raw in (None, "") else float(Kb_raw)  # type: ignore[arg-type]
    W_req_kg_h = float(inputs["W_req_kg_h"])  # type: ignore[index]

    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, overpressure_pct)
    state, k_ideal, k_real, Z, MW_kg_kmol = _state_from_composition(
        composition, relieving_pressure_pa, relieving_temperature_k
    )
    result = size_gas_or_vapor_area_api520(
        W_req_kg_h=W_req_kg_h,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=backpressure_pa,
        relieving_temperature_k=relieving_temperature_k,
        k_ideal=k_ideal,
        Z=Z,
        MW_kg_kmol=MW_kg_kmol,
        valve_design=valve_design,
        Kd=Kd,
        Kc=Kc,
        Kb=Kb,
        set_pressure_pa=set_pressure_pa,
        overpressure_pct=overpressure_pct,
        k_real=k_real,
        rho_relieving_kg_m3=state.rhomass(),
        h_relieving_j_kg=state.hmass(),
    )

    mawp_pa = inputs.get("mawp_pa")
    if mawp_pa is not None:
        mawp_pa = float(mawp_pa)
        mawp_gauge_pa = max(mawp_pa - P_ATM, 0.0)
        set_gauge_pa = max(set_pressure_pa - P_ATM, 0.0)
        max_accumulated_pa = mawp_pa + mawp_gauge_pa * overpressure_pct / 100.0
        if set_gauge_pa > mawp_gauge_pa * 1.05 + 1.0:
            result.warnings.append("Set pressure, girilen MAWP/design pressure değerini aşıyor.")
        if relieving_pressure_pa > max_accumulated_pa + 1.0:
            result.warnings.append("Relieving pressure, girilen MAWP ve allowable overpressure kombinasyonuyla tutarsız.")

    if overpressure_pct not in {10.0, 16.0, 21.0}:
        result.warnings.append(
            "Allowable overpressure, API 520/ASME yaygın ön boyutlandırma değerleri olan %10, %16 veya %21 dışında."
        )
    if max(set_pressure_pa - P_ATM, 0.0) < 30.0 * 6894.76:
        result.warnings.append(
            "Düşük set pressure aralığında ASME'nin 3 psi / 4 psi özel kuralları ayrıca doğrulanmalıdır."
        )
    return result
