# Changelog

All notable changes to Blowdown Studio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.5.0] - 2026-08-19

### Added
- API 526 / API 6D valve data centralized in `valve_catalog_data.py` (single source of truth)
- Vendor catalog schema validation with Cerberus (`_VENDOR_RECORD_SCHEMA`)
- Proprietary `LICENSE`, `pyproject.toml`, pre-commit hooks, and a CI test job
- Edition reference constants in `constants.py` (`API520_EDITION`, `API521_EDITION`, `API2000_EDITION`, `ASME_XIII_EDITION`)
- Standard reference line in PSV reports; DCMR Rijnmond citation in methodology
- 12 new engineering regression tests (`test_engineering_refinements.py`); full suite: 186 passed, 1 skipped

### Fixed
- API 520-1 liquid viscosity correction rewritten per Figure 34: correct Reynolds formula
  (`Re = 18800 * Q_gpm * G / (mu * sqrt(A))`) and Kv table applied when Re < 100
- Native blowdown engine `NameError` when the time loop never runs (`dm_kg_s`, `h_in` uninitialized)
- Removed dead `converged` variable in `find_native_blowdown_area`
- API 2000 liquid movement pump factors corrected to 7th edition (pump-in 1.01/2.02, pump-out 0.94/2.02)
- API 2000 wetted area height limit documented to 9.14 m (30 ft)
- HydDown multicomponent PH-solver skipped on numpy >= 2 (incompatible third-party dependency)

### Changed
- PSV reports honor user unit preferences end-to-end (`blowdown_studio` → `execution_ui_actions` → `psv_workflow` → `psv_reporting`)
- Unit conversion constants centralized (`T_REF_NORMAL`, `T_REF_STANDARD_15C`, `T_REF_STANDARD_60F`, `SCMH_PER_SCFM`, `SCMH_PER_MMSCFD`); dead `flow_rate_map`/`mass_flow_units` removed
- `requirements.txt` pinned (`~=`) and trimmed; `hyddown==0.16.2`, `cerberus` added; unused `psvpy`/`tqdm` dropped
- `psv_preliminary.py` no longer uses the legacy `1/sqrt(1+170/Re)` approximation
- README updated for v2.5.0 and current test counts

## [v2.4.9] - 2026-07-06

### Fixed
- Unit preferences dialog missing import fixed; dialog enlarged
- Expanded test coverage: 20 new unit_preferences tests, temperature/imperial/blowdown report tests, and zero valve-count tests

## [v2.4.8] - 2026-07-05

### Fixed
- Temperature formatting fixed: Kelvin to Celsius/Fahrenheit conversion now correct (611 °C bug resolved)
- Zero value handling for valve count / pole count fields (`or` vs `is None` fix)

### Added
- Velocity (m/s, ft/s), power (kW, MW, HP, BTU/s), and sound level (dB) unit options
- Acoustic/discharge piping report lines now render dynamically per selected units

## [v2.4.7] - 2026-07-04

### Added
- Discharge piping (API 521) input fields: pipe length, inner diameter, elbow/tee/valve counts, roughness
- User-supplied piping parameters now used directly; blank fields fall back to defaults
- Roughness and fitting details shown separately in the report

### Fixed
- HydDown `numpy.testing` import error resolved (build.spec)

## [v2.4.6] - 2026-07-03

### Added
- Plug Valve (Blowdown) valve type; default Cd 0.80
- Unit preferences dialog for pressure, temperature, mass, flow rate, and volumetric flow units
- Report and plot axis labels updated dynamically per selected units
- Unit preferences persisted to and restored from settings files

## [v2.4.5] - 2026-07-02

### Added
- Modern interface themes: Modern Light, Modern Dark, and Performance (default) modes via new "Görünüm" menu
- Tooltip (ⓘ) icons on every input field — hover or click for engineering explanations, value ranges, and unit info
- Theme-aware widget styling via ttk.Style with platform-specific font detection (Segoe UI / SF Pro / Sans)

## [v2.4.4] - 2026-07-02

### Added
- GitHub Actions CI/CD workflow for automatic Windows EXE builds
- Dynamic version reading via `build.spec` (no more version-specific spec files needed)

### Changed
- Removed old version-specific spec files (`blowdown_studio_v2.4.1.spec`, `v2.4.2.spec`, `v2.4.3.spec`)
- Workflow permissions fixed for release asset upload

## [v2.4.3] - 2026-07-02

### Added
- DCMR Rijnmond analytical blowdown engine — closed-form adiabatic isentropic method from DCMR Milieudienst Rijnmond (NL). Instant single-step calculation (no iteration needed). Reference method for Dutch VR safety reports.
- Horizontal and vertical scrollbars to Blowdown Analysis tab for better usability across different screen resolutions
- PanedWindow between main settings and gas composition sections, allowing users to resize columns
- macOS trackpad and Linux mouse wheel compatibility
- Shift+MouseWheel support for horizontal scrolling
- Bisection convergence warning when native engine sizing exceeds max iterations without 2% tolerance
- Bisection upper bound capped with pipe cross-sectional area for faster convergence
- 12+ new tests covering DCMR engine, UI scroll, and update mechanism changes

### Fixed
- Critical mass-floor bug in native blowdown engine: large orifice areas (1.0 m2) caused energy balance division by 1e-7, producing negative internal energy (-8e15 J/kg) and RuntimeError during bisection. Fixed by detecting mass depletion and breaking early instead of clamping.
- API 521 fire case heat input now properly applied to wall energy balance (previously computed but never used in simulation)
- Input fields under "Temel Girdiler" section now remain visible after mode changes
- Update notification no longer appears for draft/prerelease versions
- Two-phase flow engine now uses temperature-dependent carbon steel Cp (carbon_steel_cp_j_kgk) instead of constant 480 J/kg.K

### Changed
- Scrollregion now automatically refreshes after mode changes to ensure input field visibility
- GitHub update check now filters out draft and prerelease versions
- test_native_blowdown_api521.py now imports directly from native_blowdown_engine (avoids tkinter hang on headless)
- test_app_metadata.py updated to v2.4.3

## [v2.4.2] - 2026-04-13

### Added
- Optional `psvpy` cross-check support for Steam and Liquid PSV sizing services
- Native API 520 sizing engine remains the primary calculation source
- `psvpy` provider, required area, and native sizing delta added as separate sections in PSV reports
- `psvpy cross-check` option in PSV settings (persisted to settings file)
- MIT-licensed `psvpy` subset isolated under `third_party/` with vendor structure
- "About / Update History" dialog added to help menu

### Changed
- Tk/Tcl regression tests hardened to skip cleanly in environments without Tk support

## [v2.4.1] - 2026-04-09

### Changed
- Packaging simplified; unnecessary test, notebook, and optional backend loads excluded from exe
- Windows version metadata added
- Release build regenerated

## [v2.4.0] - 2026-04-09

### Added
- Valve count field made visible again in both Blowdown and PSV modes
- PSV sizing flow now calculates required area per valve and selects appropriate valve size based on user's valve count selection

### Changed
- Main interface ratios updated: "Temel Girdiler" 35%, "Gaz Kompozisyonu" 15%, "Analiz Raporu" 50%

## [v2.3.1] - 2026-04-06

### Fixed
- HydDown import path corrected in packaged exe
- Blowdown and PSV graph sets restored to previous expected coverage
- New tag format applied to allow updater to detect this hotfix from v2.3

## [v2.3.0] - 2026-04-03

### Added
- API 2000 tank venting screening workflow
- API 521 fire case screening with pool fire depressuring
- ASME Section XIII screening support
- Vendor catalog import (JSON/CSV) with trim, set-pressure, code-stamp, material fields
- Optional exact vendor filters in PSV interface (trim code, code stamp, body/trim material, inlet/outlet rating class)
- PSV reporting with vendor screening details
- Methodology documentation dialog (API 520/521/2000)

### Changed
- Application name standardized to "Blowdown Studio"
- Main entry file changed to `blowdown_studio.py`
- Legacy files moved to `legacy/` directory

## [v2.2.0] - 2026-03-28

### Added
- HydDown as second calculation engine
- Two-Phase Screening engine with HEM-like approach
- Segmented Pipeline engine with line-pack behavior
- Real gas EOS with energy balance
- Wall-gas heat transfer
- Phase boundary screening warnings

## [v2.1.0] - 2026-03-20

### Added
- Native blowdown engine (displayed as "Yerel Çözücü")
- PSV vendor catalog model with actual area, certified gas Kd, and Kb curve
- Default PSV catalog with official screening data
- Vendor model supports vendor size labels beyond API 526 letters

## [v2.0.0] - 2026-03-15

### Added
- Initial Blowdown Studio release
- API 520-1 gas/vapor preliminary sizing
- API 520-1 steam preliminary sizing
- API 520-1 liquid preliminary sizing
- API 521 fire-case screening
- Vendor screening catalog model
- Vendor final selection readiness screening
- Blowdown and PSV reporting (CSV/PDF export)
- Settings save/load functionality
- Auto-update check from GitHub releases
- Composition management with CoolProp fluid list
- Unit conversion for pressure, temperature, length, volume, and flow rates

[v2.5.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.9...v2.5.0
[v2.4.9]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.8...v2.4.9
[v2.4.8]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.7...v2.4.8
[v2.4.7]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.6...v2.4.7
[v2.4.6]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.5...v2.4.6
[v2.4.5]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.4...v2.4.5
[v2.4.4]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.3...v2.4.4
[v2.4.3]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.2...v2.4.3
[v2.4.2]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.1...v2.4.2
[v2.4.1]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.4.0...v2.4.1
[v2.4.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.3.1...v2.4.0
[v2.3.1]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.3.0...v2.3.1
[v2.3.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.2.0...v2.3.0
[v2.2.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.1.0...v2.2.0
[v2.1.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/compare/v2.0.0...v2.1.0
[v2.0.0]: https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/releases/tag/v2.0.0
