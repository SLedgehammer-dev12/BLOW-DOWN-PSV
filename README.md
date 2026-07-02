# Blowdown Studio

A comprehensive desktop application for API 520/521/2000 pressure safety valve (PSV) sizing and blowdown analysis.

## Overview

Blowdown Studio is an engineering tool designed for process safety engineers to perform:

- **Blowdown Analysis** - Time-dependent depressuring calculations per API 521
- **PSV Sizing** - Preliminary pressure safety valve sizing per API 520-1
- **Tank Venting** - Normal and emergency venting calculations per API 2000

The application provides multiple calculation engines, vendor catalog integration, and comprehensive reporting capabilities.

## Features

### Calculation Engines

- **Native Blowdown Engine** - Real gas EOS with energy balance and wall-gas heat transfer
- **HydDown Engine** - Alternative transient solver
- **Two-Phase Screening** - HEM-based two-phase flow screening
- **Segmented Pipeline Engine** - Line-pack behavior with Darcy-Weisbach friction model

### PSV Sizing Capabilities

- API 520-1 preliminary sizing for gas/vapor, steam, and liquid services
- Optional `psvpy` cross-check for steam and liquid services
- Vendor catalog screening with exact filtering
- Multi-valve sizing with per-valve area calculation
- ASME Section XIII screening support
- API 521 fire case screening

### Tank Venting

- API 2000 normal venting screening
- API 2000 emergency venting screening
- Latitude and insulation factor support

### User Interface

- **Resizable Columns** - Drag sash to adjust main settings and gas composition widths
- **Scrollable Interface** - Horizontal and vertical scrollbars for all screen resolutions
- **Cross-Platform Scrolling** - macOS trackpad, Linux mouse wheel, and Shift+scroll support
- **Mode Switching** - Seamless transition between Blowdown and PSV workflows
- **Settings Persistence** - Save/load configurations as JSON files

### Reporting & Export

- Detailed analysis reports with screening verdicts
- CSV and PDF export for blowdown and PSV results
- Comprehensive plotting (pressure, temperature, flow rate vs. time)
- Vendor selection recommendations with catalog matching

### Vendor Management

- Built-in vendor catalog with official screening data
- Import custom catalogs (JSON/CSV format)
- Filter by trim code, code stamp, materials, and rating classes
- Vendor final selection readiness screening

## Installation

### Windows (Recommended)

1. Download `Blowdown_Studio_v2.4.3.exe` from [Releases](https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/releases)
2. Run the executable (no installation required)
3. Launch and start analyzing

### From Source

```bash
git clone https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV.git
cd BLOW-DOWN-PSV
pip install -r requirements.txt
python blowdown_studio.py
```

### Requirements

- **Python:** 3.8 or higher
- **Dependencies:**
  - CoolProp (thermodynamic properties)
  - matplotlib (plotting)
  - numpy (numerical computing)
  - pandas (data handling)
  - tkinter (GUI framework, included with Python)

## Quick Start

### Blowdown Analysis

1. Select **"Zamana Bağlı Basınç Düşürme (Blowdown)"** mode
2. Choose system type: Pipeline or Tank/Vessel
3. Enter geometry (inner diameter, length, thickness) or total volume
4. Specify initial conditions (pressure, temperature)
5. Set target pressure and blowdown time
6. Configure valve parameters (count, discharge coefficient)
7. Add gas composition
8. Click **"v2.4.3 Blowdown Analizini Başlat"**

### PSV Sizing

1. Select **"Gerekli Debiye Göre Emniyet Vanası Çapı (PSV Sizing)"** mode
2. Enter required relief flow rate
3. Specify set pressure and relieving temperature
4. Choose service type (Gas/Vapor, Steam, or Liquid)
5. Configure backpressure and design parameters
6. Add gas composition
7. Click **"PSV Ön Boyutlandırmayı Hesapla (API 520-1)"**

### Tank Venting (API 2000)

1. Navigate to **"Tank Havalandırma (API 2000)"** tab
2. Enter tank volume and operating conditions
3. Configure latitude and insulation factors
4. Enable emergency venting if needed
5. Click **"API 2000 Hesabını Başlat"**

## Project Structure

```
BLOW-DOWN-PSV/
├── blowdown_studio.py          # Main application entry
├── app_metadata.py             # Version and metadata
├── ui_builders.py              # UI construction
├── ui_state_actions.py         # UI state management
├── update_actions.py           # Auto-update logic
├── native_blowdown_engine.py   # Primary calculation engine
├── psv_preliminary.py          # PSV sizing calculations
├── psv_vendor_catalog.py       # Vendor screening model
├── vendor_data/                # Vendor catalog files
├── third_party/                # Third-party libraries (psvpy)
├── legacy/                     # Historical versions
└── test_*.py                   # Test suite
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest test_*.py

# Run specific test suites
python test_update_actions.py
python test_ui_builders.py
python test_ui_state_actions.py
python test_psv_sizing.py
```

**Current Status:** 24 tests passing across 4 test files

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history
- **[RELEASE_v2.4.3.md](RELEASE_v2.4.3.md)** - Latest release notes
- **[PROJE_DURUMU.md](PROJE_DURUMU.md)** - Project status and architecture (Turkish)
- **[GELISIM_OZETI.md](GELISIM_OZETI.md)** - Development summary (Turkish)
- **[STANDARD_ALIGNMENT_ROADMAP.md](STANDARD_ALIGNMENT_ROADMAP.md)** - Future roadmap

## Methodology

### Blowdown Analysis
- Transient mass and energy balance
- Real gas properties via CoolProp equations of state
- Choked and subsonic flow regimes
- Heat transfer from vessel walls (optional)
- API 521 fire case screening with environment factors

### PSV Sizing
- API 520-1 Annex B methodology
- Isentropic expansion with real gas corrections
- Critical flow pressure ratio calculations
- Certified discharge coefficients (Kd)
- Backpressure correction factors (Kb, Kw)

### API 2000 Tank Venting
- Normal and emergency venting calculations
- Latitude-based solar radiation factors
- Insulation and wetted area considerations
- Latent heat and vapor molecular weight inputs

## Version History

**Latest:** v2.4.3 (July 2, 2026)

Key improvements in v2.4.3:
- Enhanced scroll support with horizontal/vertical scrollbars
- Resizable interface columns via PanedWindow
- Improved input field visibility
- Cross-platform mouse wheel support
- Smarter update mechanism (filters draft/prerelease)

See [CHANGELOG.md](CHANGELOG.md) for complete history.

## Known Limitations

- PanedWindow sash position is not persisted between sessions
- Acoustic/AIV screening is screening-level only (not final API 521/EI interpretation)
- Reaction force calculation uses single-section approach (not full API 520-2)
- Segmented pipeline uses Darcy-Weisbach screening (not full Fanno flow)
- Native and segmented blowdown engines are not fully validated two-phase solvers
- Vendor catalog metadata coverage is incomplete for some vendors

## Disclaimer

**Important:** Built-in vendor and screening results are engineering aids only. Final selection and compliance verification require:
- Vendor datasheets
- Applicable API standards (520, 521, 2000)
- Licensed professional engineer review

## Support

- **Issues:** [GitHub Issues](https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/issues)
- **Releases:** [GitHub Releases](https://github.com/SLedgehammer-dev12/BLOW-DOWN-PSV/releases)

## License

Proprietary license. See [LICENSE](LICENSE) file for details.

## Acknowledgments

- CoolProp for thermodynamic property calculations
- API standards committee for methodology guidance
- psvpy library (MIT-licensed subset included in third_party/)

---

**Blowdown Studio v2.4.3** - Process Safety Sizing Made Simple
