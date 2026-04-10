from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Iterable

import CoolProp.CoolProp as CP

from api520_steam_ksh import lookup_superheat_correction_factor_si
from constants import P_ATM, R_U


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
    service_type: str = "Gas/Vapor"

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


@dataclass
class PSVSteamSizingResult:
    A_req_m2: float
    relieving_pressure_pa: float
    relieving_temperature_k: float
    backpressure_pa: float
    set_pressure_pa: float
    overpressure_pct: float
    Kd: float
    Kc: float
    Kb_used: float
    KN: float | None
    KSH: float | None
    equation_id: str
    warnings: list[str] = field(default_factory=list)
    rho_relieving_kg_m3: float | None = None
    h_relieving_j_kg: float | None = None
    MW_kg_kmol: float = 18.01528
    k_real: float | None = None
    k_ideal: float | None = None
    Z: float | None = None
    critical_pressure_ratio: float | None = None
    is_critical: bool = True
    service_type: str = "Steam"

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


@dataclass
class PSVLiquidSizingResult:
    A_req_m2: float
    relieving_pressure_pa: float
    relieving_temperature_k: float
    backpressure_pa: float
    set_pressure_pa: float
    overpressure_pct: float
    Kd: float
    Kc: float
    Kw_used: float
    Kv_used: float
    specific_gravity: float
    viscosity_cp: float
    rho_relieving_kg_m3: float
    Q_relieving_l_min: float
    W_req_kg_h: float
    reynolds: float | None
    selected_area_mm2: float
    equation_id: str
    warnings: list[str] = field(default_factory=list)
    service_type: str = "Liquid"

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


def napier_correction_kn_si(relieving_pressure_pa: float) -> float:
    p1_kpa = relieving_pressure_pa / 1000.0
    if p1_kpa <= 10339.0:
        return 1.0
    if p1_kpa <= 22057.0:
        return (0.02764 * p1_kpa - 1000.0) / (0.03324 * p1_kpa - 1061.0)
    raise ValueError("Napier KN only applies up to 22,057 kPa relieving pressure.")


def liquid_viscosity_correction_kv(reynolds: float) -> float:
    if reynolds <= 0.0:
        raise ValueError("Liquid Reynolds number must be positive.")
    return 1.0 / math.sqrt(1.0 + 170.0 / reynolds)


def _ideal_gas_k_from_state(state: CP.AbstractState) -> float:
    cp0_molar = state.cp0molar()
    cv0_molar = cp0_molar - 8.314462618
    return cp0_molar / cv0_molar


def _build_state(composition: Dict[str, float], pressure_pa: float, temperature_k: float) -> CP.AbstractState:
    comp = normalize_composition(composition)
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    return state


def _state_from_composition(
    composition: Dict[str, float], pressure_pa: float, temperature_k: float
) -> tuple[CP.AbstractState, float, float, float, float]:
    state = _build_state(composition, pressure_pa, temperature_k)
    state.specify_phase(CP.iphase_gas)
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    k_real = state.cpmass() / state.cvmass()
    k_ideal = _ideal_gas_k_from_state(state)
    Z = state.compressibility_factor()
    MW_kg_kmol = state.molar_mass() * 1000.0
    return state, k_ideal, k_real, Z, MW_kg_kmol


def _liquid_state_from_composition(
    composition: Dict[str, float], pressure_pa: float, temperature_k: float
) -> CP.AbstractState:
    comp = normalize_composition(composition)
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    try:
        state.specify_phase(CP.iphase_liquid)
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    except Exception:
        state.unspecify_phase()
        state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    return state


def _steam_state(pressure_pa: float, temperature_k: float) -> tuple[CP.AbstractState, float, float, float, float]:
    state = CP.AbstractState("HEOS", "Water")
    state.specify_phase(CP.iphase_gas)
    state.update(CP.PT_INPUTS, pressure_pa, temperature_k)
    k_real = state.cpmass() / state.cvmass()
    k_ideal = _ideal_gas_k_from_state(state)
    Z = state.compressibility_factor()
    MW_kg_kmol = state.molar_mass() * 1000.0
    return state, k_ideal, k_real, Z, MW_kg_kmol


def _steam_backpressure_factor(
    valve_design: str,
    backpressure_pa: float,
    kb_input: float | None,
    warnings: list[str],
) -> float:
    design_key = valve_design.strip().lower()
    if design_key == "balanced bellows":
        if kb_input is None and backpressure_pa > P_ATM * 1.001:
            warnings.append(
                "Balanced bellows steam service için Kb girilmedi; preliminary sizing Kb=1.0 varsayımı ile yapıldı. "
                "Final seçim için üretici eğrisi gerekli."
            )
        return 1.0 if kb_input is None else kb_input
    return 1.0


def _liquid_backpressure_factor(
    valve_design: str,
    backpressure_pa: float,
    kw_input: float | None,
    warnings: list[str],
) -> float:
    design_key = valve_design.strip().lower()
    if backpressure_pa <= P_ATM * 1.001:
        return 1.0
    if design_key == "balanced bellows":
        if kw_input is None:
            warnings.append(
                "Liquid service balanced bellows için Figure 32 / vendor Kw gerekli. Preliminary sizing geçici olarak Kw=1.0 ile yapıldı."
            )
            return 1.0
        return kw_input
    return 1.0


def _coerce_water_composition(raw_composition: Dict[str, float] | None) -> tuple[Dict[str, float], list[str]]:
    warnings: list[str] = []
    if not raw_composition:
        warnings.append("Steam service için kompozisyon girilmedi; pure water/steam varsayıldı.")
        return {"Water": 1.0}, warnings
    norm = normalize_composition(raw_composition)
    if len(norm) != 1 or "Water" not in norm:
        warnings.append("Steam service için girilen kompozisyon göz ardı edildi; pure water/steam kullanıldı.")
        return {"Water": 1.0}, warnings
    return {"Water": 1.0}, warnings


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


def size_liquid_area_api520(
    *,
    Q_req_l_min: float,
    relieving_pressure_pa: float,
    backpressure_pa: float,
    specific_gravity: float,
    viscosity_cp: float,
    valve_design: str,
    Kd: float = 0.65,
    Kc: float = 1.0,
    Kw: float | None = None,
    set_pressure_pa: float | None = None,
    overpressure_pct: float | None = None,
    relieving_temperature_k: float | None = None,
    rho_relieving_kg_m3: float | None = None,
    W_req_kg_h: float | None = None,
    standard_orifice_areas_mm2: Iterable[float] | None = None,
) -> PSVLiquidSizingResult:
    if Q_req_l_min <= 0.0:
        raise ValueError("Liquid relieving capacity must be positive.")
    if specific_gravity <= 0.0:
        raise ValueError("Liquid specific gravity must be positive.")

    p1_kpag = max(relieving_pressure_pa - P_ATM, 0.0) / 1000.0
    p2_kpag = max(backpressure_pa - P_ATM, 0.0) / 1000.0
    if p1_kpag <= p2_kpag:
        raise ValueError("Liquid service için relieving pressure gauge, total backpressure'dan büyük olmalıdır.")

    warnings: list[str] = []
    kw_used = _liquid_backpressure_factor(valve_design, backpressure_pa, Kw, warnings)
    delta_p_kpa = p1_kpag - p2_kpag
    preliminary_area_mm2 = 11.78 * Q_req_l_min * math.sqrt(specific_gravity / delta_p_kpa) / (Kd * kw_used * Kc)

    standard_areas = sorted(float(area) for area in standard_orifice_areas_mm2) if standard_orifice_areas_mm2 else []
    kv_used = 1.0
    reynolds = None
    selected_area_mm2 = preliminary_area_mm2
    corrected_area_mm2 = preliminary_area_mm2

    if viscosity_cp > 100.0:
        if standard_areas:
            selected_area_mm2 = next((area for area in standard_areas if area >= preliminary_area_mm2), standard_areas[-1])
        for _ in range(12):
            reynolds = 18800.0 * Q_req_l_min * specific_gravity / max(viscosity_cp * selected_area_mm2, 1e-12)
            if reynolds < 80.0:
                warnings.append("Liquid Reynolds number 80'in altında; API 520 Eq. (34) screening dışına çıkıyor.")
            kv_used = liquid_viscosity_correction_kv(max(reynolds, 1e-6))
            corrected_area_mm2 = preliminary_area_mm2 / max(kv_used, 1e-12)
            if not standard_areas:
                selected_area_mm2 = corrected_area_mm2
                break
            if corrected_area_mm2 <= selected_area_mm2 + 1e-9:
                break
            next_area = next((area for area in standard_areas if area > selected_area_mm2), standard_areas[-1])
            if next_area <= selected_area_mm2 + 1e-9:
                break
            selected_area_mm2 = next_area
    else:
        reynolds = 18800.0 * Q_req_l_min * specific_gravity / max(viscosity_cp * max(selected_area_mm2, 1e-9), 1e-12)

    if W_req_kg_h is None and rho_relieving_kg_m3 is not None:
        W_req_kg_h = Q_req_l_min / 1000.0 * rho_relieving_kg_m3 * 60.0
    if W_req_kg_h is None:
        W_req_kg_h = 0.0

    return PSVLiquidSizingResult(
        A_req_m2=corrected_area_mm2 / 1e6,
        relieving_pressure_pa=relieving_pressure_pa,
        relieving_temperature_k=relieving_temperature_k if relieving_temperature_k is not None else 298.15,
        backpressure_pa=backpressure_pa,
        set_pressure_pa=set_pressure_pa if set_pressure_pa is not None else relieving_pressure_pa,
        overpressure_pct=overpressure_pct if overpressure_pct is not None else 0.0,
        Kd=Kd,
        Kc=Kc,
        Kw_used=kw_used,
        Kv_used=kv_used,
        specific_gravity=specific_gravity,
        viscosity_cp=viscosity_cp,
        rho_relieving_kg_m3=rho_relieving_kg_m3 if rho_relieving_kg_m3 is not None else specific_gravity * 1000.0,
        Q_relieving_l_min=Q_req_l_min,
        W_req_kg_h=W_req_kg_h,
        reynolds=reynolds,
        selected_area_mm2=selected_area_mm2,
        equation_id="API 520-1 Eq. (33) + Eq. (34)/(37)",
        warnings=warnings,
    )


def size_steam_area_api520(
    *,
    W_req_kg_h: float,
    relieving_pressure_pa: float,
    backpressure_pa: float,
    relieving_temperature_k: float,
    valve_design: str,
    Kd: float = 0.975,
    Kc: float = 1.0,
    Kb: float | None = None,
    set_pressure_pa: float | None = None,
    overpressure_pct: float | None = None,
) -> PSVSteamSizingResult:
    warnings: list[str] = []
    state, k_ideal, k_real, Z, MW_kg_kmol = _steam_state(relieving_pressure_pa, relieving_temperature_k)
    pressure_ratio = backpressure_pa / relieving_pressure_pa
    pr_crit = critical_pressure_ratio(k_ideal)
    kb_used = _steam_backpressure_factor(valve_design, backpressure_pa, Kb, warnings)

    def steam_from_gas_fallback(reason: str, kn_used: float | None = None) -> PSVSteamSizingResult:
        warnings.append(reason)
        gas_fallback = size_gas_or_vapor_area_api520(
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
        warnings.extend(gas_fallback.warnings)
        return PSVSteamSizingResult(
            A_req_m2=gas_fallback.A_req_m2,
            relieving_pressure_pa=gas_fallback.relieving_pressure_pa,
            relieving_temperature_k=gas_fallback.relieving_temperature_k,
            backpressure_pa=gas_fallback.backpressure_pa,
            set_pressure_pa=gas_fallback.set_pressure_pa,
            overpressure_pct=gas_fallback.overpressure_pct,
            Kd=gas_fallback.Kd,
            Kc=gas_fallback.Kc,
            Kb_used=gas_fallback.Kb_used,
            KN=kn_used,
            KSH=None,
            equation_id=f"{gas_fallback.equation_id} (steam fallback)",
            warnings=warnings,
            rho_relieving_kg_m3=gas_fallback.rho_relieving_kg_m3,
            h_relieving_j_kg=gas_fallback.h_relieving_j_kg,
            MW_kg_kmol=gas_fallback.MW_kg_kmol,
            k_real=gas_fallback.k_real,
            k_ideal=gas_fallback.k_ideal,
            Z=gas_fallback.Z,
            critical_pressure_ratio=gas_fallback.critical_pressure_ratio,
            is_critical=gas_fallback.is_critical,
        )

    if pressure_ratio > pr_crit:
        return steam_from_gas_fallback(
            "Steam service kritik akış koşulunu sağlamıyor; API 520 steam Napier denklemi yerine gas/vapor fallback sizing kullanıldı."
        )

    tsat_k = CP.PropsSI("T", "P", relieving_pressure_pa, "Q", 1, "Water")
    superheat_c = relieving_temperature_k - tsat_k
    kn = napier_correction_kn_si(relieving_pressure_pa)
    if superheat_c <= 1.0:
        ksh = 1.0
        equation_id = "API 520-1 Eq. (26), saturated steam"
    else:
        ksh = lookup_superheat_correction_factor_si(relieving_pressure_pa / 1e6, relieving_temperature_k - 273.15)
        if ksh is None:
            return steam_from_gas_fallback(
                "Steam superheat Table 13 aralığı dışına çıkıldı; API 520 gas/vapor fallback sizing kullanıldı.",
                kn_used=kn,
            )
        equation_id = "API 520-1 Eq. (26) + KN + KSH"

    area_mm2 = 190.5 * W_req_kg_h / ((relieving_pressure_pa / 1000.0) * Kd * kb_used * Kc * kn * ksh)
    result = PSVSteamSizingResult(
        A_req_m2=area_mm2 / 1e6,
        relieving_pressure_pa=relieving_pressure_pa,
        relieving_temperature_k=relieving_temperature_k,
        backpressure_pa=backpressure_pa,
        set_pressure_pa=set_pressure_pa if set_pressure_pa is not None else relieving_pressure_pa,
        overpressure_pct=overpressure_pct if overpressure_pct is not None else 0.0,
        Kd=Kd,
        Kc=Kc,
        Kb_used=kb_used,
        KN=kn,
        KSH=ksh,
        equation_id=equation_id,
        warnings=warnings,
        rho_relieving_kg_m3=state.rhomass(),
        h_relieving_j_kg=state.hmass(),
        MW_kg_kmol=MW_kg_kmol,
        k_real=k_real,
        k_ideal=k_ideal,
        Z=Z,
        critical_pressure_ratio=pr_crit,
        is_critical=True,
    )
    if result.backpressure_pct_of_set > 10.0 and valve_design.strip().lower() == "conventional":
        result.warnings.append(
            "Conventional steam PRV için total backpressure, set pressure'ın %10 screening seviyesini aşıyor."
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
    Kd = float(inputs.get("Kd_api520", inputs.get("Kd", 0.975)))  # type: ignore[arg-type]
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


def calculate_preliminary_steam_psv_area(
    inputs: Dict[str, float | Dict[str, float] | str | None]
) -> PSVSteamSizingResult:
    composition, composition_warnings = _coerce_water_composition(inputs.get("composition"))  # type: ignore[arg-type]
    set_pressure_pa = float(inputs["set_pressure_pa"])  # type: ignore[index]
    overpressure_pct = float(inputs.get("overpressure_pct", 10.0))  # type: ignore[arg-type]
    relieving_temperature_k = float(inputs["relieving_temperature_k"])  # type: ignore[index]
    backpressure_pa = float(inputs.get("p_total_backpressure_pa", P_ATM))  # type: ignore[arg-type]
    valve_design = str(inputs.get("prv_design", "Conventional"))
    Kd = float(inputs.get("Kd_api520", inputs.get("Kd", 0.975)))  # type: ignore[arg-type]
    Kc = float(inputs.get("Kc", 1.0))  # type: ignore[arg-type]
    Kb_raw = inputs.get("Kb")
    Kb = None if Kb_raw in (None, "") else float(Kb_raw)  # type: ignore[arg-type]
    W_req_kg_h = float(inputs["W_req_kg_h"])  # type: ignore[index]

    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, overpressure_pct)
    result = size_steam_area_api520(
        W_req_kg_h=W_req_kg_h,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=backpressure_pa,
        relieving_temperature_k=relieving_temperature_k,
        valve_design=valve_design,
        Kd=Kd,
        Kc=Kc,
        Kb=Kb,
        set_pressure_pa=set_pressure_pa,
        overpressure_pct=overpressure_pct,
    )
    result.warnings.extend(composition_warnings)
    if composition != {"Water": 1.0}:
        result.warnings.append("Steam service ön boyutlandırması pure water/steam varsayar.")
    return result


def calculate_preliminary_liquid_psv_area(
    inputs: Dict[str, float | Dict[str, float] | str | None],
    standard_orifice_areas_mm2: Iterable[float] | None = None,
) -> PSVLiquidSizingResult:
    composition = normalize_composition(inputs["composition"])  # type: ignore[index]
    set_pressure_pa = float(inputs["set_pressure_pa"])  # type: ignore[index]
    overpressure_pct = float(inputs.get("overpressure_pct", 10.0))  # type: ignore[arg-type]
    relieving_temperature_k = float(inputs["relieving_temperature_k"])  # type: ignore[index]
    backpressure_pa = float(inputs.get("p_total_backpressure_pa", P_ATM))  # type: ignore[arg-type]
    valve_design = str(inputs.get("prv_design", "Conventional"))
    Kd = float(inputs.get("Kd_api520", inputs.get("Kd", 0.65)))  # type: ignore[arg-type]
    Kc = float(inputs.get("Kc", 1.0))  # type: ignore[arg-type]
    Kw_raw = inputs.get("Kw", inputs.get("Kb"))
    Kw = None if Kw_raw in (None, "") else float(Kw_raw)  # type: ignore[arg-type]

    relieving_pressure_pa = relieving_pressure_from_set_pressure(set_pressure_pa, overpressure_pct)
    state = _liquid_state_from_composition(composition, relieving_pressure_pa, relieving_temperature_k)
    rho = state.rhomass()
    mu_cp = state.viscosity() * 1000.0
    sg = rho / 1000.0

    q_l_min_raw = inputs.get("Q_req_l_min")
    w_req_kg_h_raw = inputs.get("W_req_kg_h")
    if q_l_min_raw not in (None, ""):
        Q_req_l_min = float(q_l_min_raw)  # type: ignore[arg-type]
        W_req_kg_h = Q_req_l_min / 1000.0 * rho * 60.0
    elif w_req_kg_h_raw not in (None, ""):
        W_req_kg_h = float(w_req_kg_h_raw)  # type: ignore[arg-type]
        Q_req_l_min = W_req_kg_h / max(rho, 1e-12) * 1000.0 / 60.0
    else:
        raise ValueError("Liquid PSV sizing için kütlesel veya hacimsel relief capacity zorunludur.")

    result = size_liquid_area_api520(
        Q_req_l_min=Q_req_l_min,
        relieving_pressure_pa=relieving_pressure_pa,
        backpressure_pa=backpressure_pa,
        specific_gravity=sg,
        viscosity_cp=mu_cp,
        valve_design=valve_design,
        Kd=Kd,
        Kc=Kc,
        Kw=Kw,
        set_pressure_pa=set_pressure_pa,
        overpressure_pct=overpressure_pct,
        relieving_temperature_k=relieving_temperature_k,
        rho_relieving_kg_m3=rho,
        W_req_kg_h=W_req_kg_h,
        standard_orifice_areas_mm2=standard_orifice_areas_mm2,
    )

    if len(composition) > 1:
        result.warnings.append(
            "Liquid property estimate, CoolProp mixture sıvı özellikleri ile screening seviyesinde yapıldı; çok bileşenli servis için vendor/process datasheet doğrulaması gerekir."
        )
    return result
