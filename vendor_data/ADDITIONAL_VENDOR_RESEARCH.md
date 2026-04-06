# Additional Vendor Research

## Added this round

### Spirax Sarco

Downloaded official documents:

- `source_docs/spirax_sv418_ti_p273_01_us.pdf`
- `source_docs/spirax_sv5601_sv5708_ti_p272_01_us.pdf`
- `source_docs/spirax_sizing_safety_valves_ti_3_2121_us.pdf`

Useful extracted facts:

- `SV418` publishes Section VIII / NB air, steam, liquid capacities and D-J flow areas.
- `SV5708` publishes Section VIII / NB air/gas and steam capacities plus D-J flow areas.
- The official tables are rich enough to infer screening-level gas `Kd` from the published air-capacity points.

Current integration status:

- Added into the default JSON catalog as explicit D-J vendor models.
- `SV418` is carried with a conservative inferred gas `Kd = 0.864`.
- `SV5708` is carried with an inferred gas `Kd = 0.857`.
- Notes clearly state that these `Kd` values are inferred from official tables and remain screening-level.

### Goetze

Downloaded official document:

- `source_docs/goetze_461_datasheet_en.pdf`

Useful extracted facts:

- Series `461` publishes gas/vapour `Kdr` values on ISO 4126-1 / AD2000 basis.
- The same datasheet publishes `d0` flow diameters and air-capacity tables at 10% overpressure.
- Small sizes `DN8`, `DN10`, `DN15` are suitable as explicit non-API vendor models.

Current integration status:

- Added into the default JSON catalog as explicit vendor models.
- `DN8`, `DN10`, `DN15` use published ISO gas `Kdr` values.
- Application warnings now flag ISO / AD2000 entries as non-ASME screening data.

### Flow Safe

Downloaded official catalogs:

- `source_docs/flowsafe_f84_f85_catalog.pdf`
- `source_docs/flowsafe_f80_catalog.pdf`

Useful extracted facts:

- Gas sizing equations are published explicitly.
- ASME gas-service `Kd = 0.878` is published in the capacity tables.
- Published orifice areas include:
  - `-6 (D)` = `0.149 in2` (`96.1 mm2`)
  - `-8 (E)` = `0.261 in2` (`168 mm2`)
  - `-F` = `0.405 in2` (`261 mm2`)
  - `-G` = `0.664 in2` (`428 mm2`)
  - `-H` = `1.036 in2` (`668 mm2`)
  - `-J` = `1.689 in2` (`1089 mm2`)
- Catalog text states:
  - `-6` is equivalent to API 526 `D`
  - `-8` is equivalent to API 526 `E`

Current integration status:

- Added into the default JSON catalog.
- The schema was expanded to allow:
  - explicit vendor size labels
  - optional API 526 equivalent labels
  - a `Balanced Spring` design family
- Flow Safe models are now screened as explicit vendor entries rather than strict API 526 family records.

### IMI

Attempted source:

- `https://www.imi-critical.com/wp-content/uploads/2020/10/IMI_BR_PI_Si830_API_30_EN_Web.pdf`

Current result:

- In this environment the URL resolves to a site HTML shell, not a real PDF payload.
- Saved local artifact: `source_docs/imi_si830_api.pdf`
- That file is actually HTML, so no reliable extraction was performed.

Current integration status:

- Not usable yet.
- Needs a direct official PDF or a different official brochure link.

## Recommended next step

1. Add manufacturer and series filters to the UI so the user can narrow screening to a chosen vendor family.
2. Introduce trim- and pressure-class-specific imports where vendor data are available.
3. Add support for additional non-API families using the same explicit-model schema.
