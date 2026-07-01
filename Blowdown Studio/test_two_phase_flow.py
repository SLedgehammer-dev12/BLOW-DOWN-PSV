import os
import sys

import CoolProp.CoolProp as CP

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from two_phase_flow import (
    _forced_density,
    calculate_mixture_properties,
    find_two_phase_blowdown_area,
    run_two_phase_blowdown_simulation,
)


# ── C. Two-Phase PT Flash Stability Tests ─────────────────────────────────

def test_forced_density_pq_inputs_fallback():
    """_forced_density PT basarisizsa PQ fallback'i calistirmali."""
    rho_v = _forced_density({"Water": 1.0}, 101325.0, 373.15, CP.iphase_gas)
    rho_l = _forced_density({"Water": 1.0}, 101325.0, 373.15, CP.iphase_liquid)
    assert rho_v is not None, "Saf su 2-faz bolgesinde rho_v uretilemedi."
    assert rho_l is not None, "Saf su 2-faz bolgesinde rho_l uretilemedi."
    assert rho_l > rho_v, f"Sivi yogunlugu ({rho_l:.3f}) buhar yogunlugundan ({rho_v:.3f}) buyuk olmali."
    # Fiziksel deger araligi: atmosferik su/buhar
    assert 0.5 < rho_v < 1.0, f"Atmosferik buhar yogunlugu 0.5-1.0 arasi: {rho_v:.3f}"
    assert 900 < rho_l < 1000, f"Atmosferik su yogunlugu 900-1000 arasi: {rho_l:.3f}"


def test_mixture_properties_saturated_water():
    """Atmosferik kaynama sartinda 2-faz ozellikleri fiziksel olmali."""
    props = calculate_mixture_properties(
        gas_mole_fraction=0.5,
        liquid_mole_fraction=0.5,
        pressure_pa=101325.0,
        temperature_k=373.15,
        components={"Water": 1.0},
    )
    print(f"Saturated water phase: {props['phase_label']}")
    print(f"Quality: {props['quality']:.4f}")
    print(f"rho_v: {props['vapor_density']:.3f}, rho_l: {props['liquid_density']:.3f}")
    assert props["vapor_density"] > 0.0
    assert props["liquid_density"] > props["vapor_density"]
    assert 0.0 <= props["quality"] <= 1.0


def test_mixture_properties_pure_methane_twophase():
    """Saf metan 2-faz bolgesinde (P=3MPa, T=180K) crash olmamali."""
    props = calculate_mixture_properties(
        gas_mole_fraction=0.5,
        liquid_mole_fraction=0.5,
        pressure_pa=3e6,
        temperature_k=180.0,
        components={"Methane": 1.0},
    )
    assert props["vapor_density"] > 0.0
    assert props["liquid_density"] > 0.0


def test_calculate_mixture_properties_twophase_consistency():
    """Iki-faz ciktisinda rho_l >> rho_v olmali."""
    props = calculate_mixture_properties(
        gas_mole_fraction=0.5,
        liquid_mole_fraction=0.5,
        pressure_pa=5e5,
        temperature_k=300.0,
        components={"Methane": 1.0},
    )
    assert props["liquid_density"] > props["vapor_density"] * 1.5, (
        f"rho_l ({props['liquid_density']:.1f}) >> rho_v ({props['vapor_density']:.1f}) olmali."
    )


def test_mixture_properties_screening():
    print("--- Two-Phase Property Screening Test ---")
    props = calculate_mixture_properties(
        gas_mole_fraction=1.0,
        liquid_mole_fraction=0.0,
        pressure_pa=101325.0,
        temperature_k=298.15,
        components={"Methane": 1.0},
    )
    print(f"Phase: {props['phase_label']}")
    print(f"Quality: {props['quality']:.3f}")
    print(f"Flow regime: {props['flow_regime']}")
    assert 0.0 <= props["quality"] <= 1.0
    assert props["mixture_density"] > 0.0


def test_two_phase_screening_simulation():
    print("--- Two-Phase Blowdown Screening Test ---")
    inputs = {
        "composition": {"Methane": 1.0},
        "V_sys": 5.0,
        "p0_pa": 101325.0 + 20e5,
        "T0_k": 280.15,
        "p_target_blowdown_pa": 101325.0 + 5e5,
        "t_target_sec": 120.0,
        "p_downstream": 101325.0,
        "Cd_valve": 0.8,
        "HT_enabled": False,
        "A_inner": 10.0,
        "M_steel": 500.0,
        "D_in_m": 0.5,
    }
    df = run_two_phase_blowdown_simulation(inputs, area_m2=2.5e-4)
    print(f"Rows: {len(df)}")
    print(f"Final pressure: {df['p_sys'].iloc[-1] / 1e5:.2f} bara")
    print(f"Quality min/max: {df['quality'].min():.3f} / {df['quality'].max():.3f}")
    assert len(df) > 5
    assert "quality" in df.columns
    assert df["quality"].between(0.0, 1.0).all()
    assert df.attrs["engine"] == "Two-Phase HEM Screening"

    sized_area = find_two_phase_blowdown_area(inputs)
    print(f"Sized area: {sized_area:.9f} m2")
    assert sized_area > 0.0

    print("TEST COMPLETED")


if __name__ == "__main__":
    test_mixture_properties_screening()
    test_two_phase_screening_simulation()
