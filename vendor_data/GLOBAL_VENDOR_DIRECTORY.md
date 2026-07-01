# Global Vendor Directory

This note complements `psv_vendor_catalog_official.json`.

- `screening-included` means the manufacturer already has normalized technical models that the application can compare during gas-service vendor screening.
- `directory-only` means the manufacturer is tracked from official sources, but its certified sizing data are not yet normalized into the current selection engine.

## Americas

| Manufacturer | Status | Official reference |
| --- | --- | --- |
| Curtiss-Wright Farris | screening-included | 2600 Series Product Catalog 2025 |
| Baker Hughes Consolidated | screening-included | Consolidated 1811 fact sheet + condensed catalog family |
| Emerson Crosby / Anderson Greenwood | directory-only | Emerson pressure-relief portfolio disclosures |
| Flow Safe | screening-included | Flow Safe F80 / F84 / F85 catalogs |

## Europe

| Manufacturer | Status | Official reference |
| --- | --- | --- |
| LESER | screening-included | API Extended Catalog US + LESER worldwide brochure |
| Goetze | screening-included | Series 461 datasheet + Goetze group brochure |
| VYC Industrial | screening-included | Models 285-286 ASME USCS brochure |
| HEROSE | screening-included | HEROSE Type 06120 / 06121 datasheet |
| Seetru | directory-only | LGS datasheet + Seetru safety valve brochure |
| ARI SAFE / REYCO | directory-only | SAFE/REYCO brochure |
| Spirax Sarco | screening-included | SV418 / SV5708 US technical sheets |

## Asia

| Manufacturer | Status | Official reference |
| --- | --- | --- |
| Curtiss-Wright Farris | screening-included | Official catalog lists China and India facilities |
| Emerson Crosby / Anderson Greenwood | directory-only | Emerson global pressure-relief portfolio |
| Baker Hughes Consolidated | screening-included | Baker Hughes global process-control business |
| LESER | screening-included | LESER worldwide literature |
| Goetze | screening-included | Official brochure cites China sales subsidiary |
| Spirax Sarco | screening-included | Global product family with Asian distribution footprint |
| HEROSE | screening-included | Official company literature + Type 06120 / 06121 datasheet |
| Yoshitake | directory-only | Official disclosures list overseas companies in Asia and the United States |

## Next normalization targets

1. Seetru LGS
2. ARI SAFE / REYCO API-oriented models
3. Emerson Crosby / Anderson Greenwood public brochures with exact `A0`, `Kd`, and pressure windows
4. Yoshitake safety valve families with published `A0` / capacity windows
