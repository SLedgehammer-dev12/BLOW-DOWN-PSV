# Blowdown Studio v2.4.3 Release Notes

**Release Date:** July 2, 2026
**Version:** v2.4.3
**Previous Version:** v2.4.2

## Overview

This is a major release featuring a **new calculation engine** (DCMR Rijnmond analytical method), **critical bug fixes** in the blowdown simulation, and **significant UI improvements** for usability across different screen resolutions. The release also improves the update mechanism and adds comprehensive test coverage.

## Key Features

### 1. New Engine: DCMR Rijnmond (Analytical Blowdown)

The DCMR Milieudienst Rijnmond analytical blowdown method has been integrated as a new calculation engine.

- **Closed-form formula** — single-step evaluation, no iteration required (< 0.01 second)
- **Reference standard** for Dutch VR (Veiligheidsrapport / Safety Report) submissions
- **Conservative results** — assumes adiabatic isentropic expansion and continuous choked flow, giving larger (safer) orifice areas
- Uses real gas properties (k, Z, M) from CoolProp at initial conditions
- Includes sub-sonic regime warning when target pressure approaches critical ratio
- Added as the first option in the engine selector dropdown, defaulting to Native engine

**Method Details:**
```
A_req = V_sys * 2 / ((k-1) * Cd * Kb * C_crit * t_target) * ((P0/P2)^((k-1)/(2k)) - 1) * sqrt(M / (Z * R * T0))
```

### 2. Critical Bug Fix: Mass-Floor Clamp in Blowdown Simulation

**Severity: Critical — caused bisection crash and inflated orifice areas.**

The native blowdown engine clamped remaining fluid mass to `1e-7` when a time step depleted the vessel completely. This caused:
- Energy balance division by 1e-7 → negative internal energy (-8e15 J/kg)
- CoolProp flash failure → RuntimeError during area sizing
- For cases where it didn't crash, the bisection converged to unrealistically large areas

**Fix:** Instead of clamping, the engine now detects mass depletion (`actual_dm >= old_m`) and gracefully breaks the simulation loop, returning the correct blowdown time. The bisection upper bound is also capped with the pipe cross-sectional area for faster convergence.

**Before:** 50-barg vessel crash or 200x oversized area
**After:** Correct area found in < 0.2 seconds

### 3. Bug Fix: API 521 Fire Case Heat Input

Fire case heat input (`fire_heat_input_w`) from API 521 pool-fire calculations was computed and stored in the inputs dictionary but **never applied** to the simulation energy balance. 

**Fix:** Fire heat input now properly added to the wall energy balance:
- With HT enabled: fire heat heats the wall, wall convects to gas
- With HT disabled: fire heat applied directly to gas energy balance

### 4. Enhanced Scroll Support

- Added horizontal scrollbar to the Blowdown Analysis tab (previously vertical-only)
- Canvas window width no longer forced to match viewport — content wider than screen triggers horizontal scroll
- macOS trackpad delta normalization (`abs(delta) > 10` → divide by 120)
- Linux mouse wheel support via Button-4/Button-5 events
- Shift+MouseWheel for horizontal scrolling
- Mouse wheel bound to left pane via Enter/Leave events (no longer steals events from other widgets)

### 5. Resizable Interface Columns

- Main settings and gas composition sections now separated by a dragable PanedWindow sash
- Users can resize columns by dragging the divider left or right (7:3 initial ratio)
- Resizing persists during session

### 6. Improved Input Field Visibility

- Scroll region automatically refreshes after mode changes (Blowdown ↔ PSV)
- `app.after(20, scrollregion_refresh)` called after `apply_mode_change`
- Input fields under "Temel Girdiler" remain visible after mode switching

### 7. Smarter Version Checking

- GitHub update check filters out draft and prerelease versions
- Only stable, published releases are considered for update notifications

### 8. Two-Phase Flow: Temperature-Dependent Steel Cp

- Two-phase engine now uses `carbon_steel_cp_j_kgk(T_wall)` instead of constant `Cp_steel = 480.0 J/kg.K`
- Consistent with Native and Segmented Pipeline engines

## Technical Changes

### Modified Files

| File | Changes |
|------|---------|
| `native_blowdown_engine.py` | Mass-floor fix, fire heat input, bisection bounds, convergence warning, DCMR engine (7 new functions) |
| `two_phase_flow.py` | Temperature-dependent steel Cp via `carbon_steel_cp_j_kgk()` |
| `blowdown_workflow.py` | DCMR dispatch in `size_blowdown_area` and `run_blowdown_engine` |
| `blowdown_studio.py` | DCMR import and parameter passing |
| `ui_builders.py` | Horizontal scrollbar, PanedWindow, mousewheel handlers, DCMR engine option |
| `ui_state_actions.py` | Scrollregion refresh after mode changes |
| `ui_mode_logic.py` | DCMR button text and help description |
| `update_actions.py` | Draft/prerelease filtering in `fetch_latest_release()` |
| `methodology_content.py` | DCMR method documentation |
| `app_metadata.py` | Version bump to v2.4.3, release history |
| `blowdown_studio_version_info.txt` | Windows version metadata updated |
| `github_update_release.py` | TAG and EXE_PATH updated |

### New Files

| File | Description |
|------|-------------|
| `test_dcmr_engine.py` | 12 tests: formula correctness, reversibility, native consistency, monotonicity, fire case, dataframe format |
| `CHANGELOG.md` | Complete version history |
| `RELEASE_v2.4.3.md` | This release notes document |
| `README.md` | Project overview, features, installation, usage guide |
| `blowdown_studio_v2.4.3.spec` | PyInstaller spec for v2.4.3 build |

### Test Coverage

**12 New Tests (test_dcmr_engine.py):**
1. `test_dcmr_crit_factor` — Critical flow factor formula
2. `test_dcmr_pressure_ratio_term` — Pressure ratio term formula
3. `test_dcmr_gas_props` — Gas property extraction
4. `test_dcmr_formulas_reversible` — Area and time formulas are inverse of each other
5. `test_dcmr_find_area_smoke` — Area within reasonable range
6. `test_run_dcmr_silent` — Silent mode returns correct time
7. `test_run_dcmr_dataframe` — Dataframe output with correct structure
8. `test_dcmr_vs_native_consistency` — DCMR conservative vs native
9. `test_dcmr_larger_area_faster` — Monotonicity: larger area → shorter time
10. `test_dcmr_ethane_mixture` — Multi-component gas handling
11. `test_dcmr_fire_case_scenario` — Fire case inputs
12. `test_dcmr_high_pressure_ratio_warning` — Sub-sonic warning

**7 Added Tests (update + UI):**
- `test_fetch_latest_release_filters_draft`, `test_fetch_latest_release_filters_prerelease`, `test_fetch_latest_release_returns_stable`
- `test_build_application_shell_ui_has_horizontal_scrollbar`, `test_build_application_shell_ui_scrollregion_refresh`, `test_build_left_pane_ui_paned_window`
- `test_apply_mode_change_triggers_scrollregion_refresh`

**Updated Tests:**
- `test_build_left_pane_ui_smoke` — PanedWindow checks (was grid weights)
- `test_app_metadata.py` — v2.4.2 → v2.4.3 assertions
- `test_native_blowdown_api521.py` — Direct import (was tkinter-heavy importlib chain)
- `test_ui_builders.py`, `test_ui_state_actions.py`, `test_input_collection_actions.py`, `test_psv_ui_actions.py` — Added `dcmr_engine_name` parameter

**All 38+ tests passing across 12+ test files.**

## Upgrade Instructions

### From v2.4.2
1. Download `Blowdown_Studio_v2.4.3.exe` from the release assets
2. Replace your existing installation
3. No settings migration required — all settings files remain compatible

### New Engine Selection
After upgrade, open the Blowdown Analysis tab. The engine dropdown now shows:
1. **DCMR Rijnmond (Analitik)** — Instant analytical results, Dutch VR reference method
2. **Yerel Çözücü** — Full transient ODE with heat transfer (default)
3. Segmented Pipeline
4. Two-Phase Screening
5. HydDown

## Known Limitations

- DCMR engine assumes adiabatic conditions and continuously choked flow (conservative)
- DCMR sub-sonic warning at high P2/P0 ratios — use Native engine for those cases
- PanedWindow sash position is not persisted between sessions (resets on restart)
- Fire case heat input applied as single-node wall model (no radial gradient)
- acOS users: Natural scrolling direction is respected

## Compatibility

- **Settings Files:** Fully compatible with v2.4.0, v2.4.1, v2.4.2
- **Vendor Catalogs:** Compatible with all previous versions
- **Export Formats:** CSV/PDF exports unchanged

## Support

For issues, questions, or feedback:
- GitHub Issues: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/issues
- Documentation: See `PROJE_DURUMU.md`, `GELISIM_OZETI.md`, `CHANGELOG.md`

---

**Full Changelog:** See `CHANGELOG.md` for complete version history.
