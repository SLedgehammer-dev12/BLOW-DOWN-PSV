# Vendor Data

This folder stores PSV vendor screening data used by `psv_vendor_catalog.py`.

## Files

- `psv_vendor_catalog_official.json`
  - Default screening catalog loaded by the application.
  - Built from official manufacturer publications downloaded into `source_docs/`.
  - Now also contains a `manufacturer_directory` section for official regional coverage tracking beyond the currently normalized screening models.
- `source_docs/`
  - Archived source PDFs used to build the screening dataset.
- `GLOBAL_VENDOR_DIRECTORY.md`
  - Region-oriented view of official manufacturers tracked across the Americas, Europe, and Asia.

## Current scope

- Curtiss-Wright Farris 2600 Series
  - API D-T actual areas
  - Gas actual-area coefficient `K = 0.858`
  - BalanSeal `Kb` curve approximated from the published 10% overpressure chart
- Baker Hughes Consolidated
  - 1900 Series conventional
  - 1900 Series bellows
  - 3900 Series pilot-operated
  - API D-T actual areas
  - Gas actual-area `K` factors from the official sizing rules document
  - Bellows `Kb` curve approximated from the published 10% overpressure chart
- LESER Type 526
  - API D-T actual areas
  - ASME gas coefficient `K = 0.801`
  - Balanced-bellows `Kb` graph is published, but its pressure-ratio basis is not yet normalized into the current code path
- Flow Safe F84/F85
  - Partial integration via explicit vendor size labels
  - Gas-service `Kd = 0.878`
  - Vendor size labels `-6`, `-8`, `-F`, `-G`, `-H`, `-J`
  - Treated as `Balanced Spring` screening models
- Spirax Sarco SV418 and SV5708
  - Explicit D-J vendor models
  - ASME Section VIII / NB air-gas capacity tables and published flow areas archived in `source_docs/`
  - Gas-service `Kd` values inferred from official air-capacity tables for screening use
- Goetze Series 461
  - Explicit DN8, DN10, DN15 vendor models
  - ISO 4126-1 / AD2000 A2 `Kdr` values and capacity tables
  - Non-API small-size screening models with clear non-ASME warning
- HEROSE Type 06120 / 06121
  - Explicit DN15 through DN100 vendor models
  - Official AD2000 datasheet publishes `A0` flow areas and gas/vapour discharge coefficients
  - Added as explicit non-ASME conventional screening models
- VYC Industrial Models 285 / 286
  - Explicit 1/2" x 1" through 1 1/4" x 2" vendor models
  - Official ASME/API 520 brochure publishes `A0` flow areas and gas/steam `Kdr` values
  - Added as explicit conventional models for Europe-origin ASME/USCS product coverage

## Manufacturer directory coverage

- Americas, Europe, and Asia are now tracked explicitly in `manufacturer_directory`.
- Directory entries distinguish between:
  - `screening_models_included = true`
  - `screening_models_included = false`
- This allows the app to show broader official vendor coverage without pretending every manufacturer already has normalized certified sizing data in the selection engine.

## Additional researched catalogs

- Flow Safe F84/F85 and F80
  - Official catalogs downloaded into `source_docs/`
  - Publish gas-service sizing equations, ASME `Kd = 0.878`, and orifice areas
  - Integrated as explicit vendor models rather than strict API 526 family records
- Spirax Sarco SV418 and SV5708
  - Official technical information sheets downloaded into `source_docs/`
  - Publish NB air/gas capacities and flow areas for D-J sizes
  - Added as explicit vendor models with screening-level inferred gas `Kd`
- Goetze Series 461
  - Official datasheet downloaded into `source_docs/`
  - Publishes ISO 4126-1 / AD2000 gas `Kdr`, `d0`, and air-capacity tables
  - Added as explicit non-API vendor models for small-size screening
- IMI Si 830
  - Public brochure URL currently resolves to a site shell in this environment rather than a direct PDF
  - Needs site-specific retrieval or a different official document link before extraction
- HEROSE Type 06120 / 06121
  - Official datasheet downloaded into `source_docs/herose_06120_06121_datasheet_en.pdf`
  - Publishes `A0`, gas/vapour discharge coefficient, DN range, and set-pressure window
  - Added as explicit AD2000-based conventional screening models
- VYC Industrial Models 285 / 286
  - Official brochure downloaded into `source_docs/vyc_285_286_asme_uscs.pdf`
  - Publishes `A0`, `Kdr`, pressure ranges, material options, and ASME/API 520 basis
  - Added as explicit conventional screening models

## Limits

- This is a screening dataset, not a final certified selection database.
- Digitized `Kb` points should be treated as approximate until replaced by exact vendor data or vendor software.
- Inferred gas `Kd` values from vendor air-capacity tables are screening approximations, even when the source publication itself is official.
- ISO 4126 / AD2000 entries are useful for comparison and early sizing, but they are not a substitute for ASME/NB certified capacity verification.
- Final valve selection still requires the exact vendor trim, set pressure, overpressure, backpressure, certified capacity, and code-mark verification.
- `manufacturer_directory` broadens market coverage, but directory-only manufacturers are not yet part of the automatic technical sizing comparison.
