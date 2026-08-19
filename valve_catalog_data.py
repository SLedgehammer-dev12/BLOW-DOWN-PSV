"""
Single source of truth for standard valve orifice / bore data.

The API 526 orifice areas and the API 6D full-bore valve areas are defined
here once and shared by the PSV sizing workflow, the vendor catalog model and
the blowdown area-selection workflow. Keep this module in sync with the
applicable standard revision.
"""

from __future__ import annotations

from collections import namedtuple

API526_Orifice = namedtuple(
    "API526_Orifice", ["letter", "area_in2", "area_mm2", "size_in", "size_dn"]
)
API6D_Valve = namedtuple("API6D_Valve", ["size_in", "area_mm2", "size_dn"])


def load_api526_data():
    """Return standard API 526 orifice letter, area and size data.

    Columns: letter, area_in2, area_mm2, size_in, size_dn.
    Source: API Std 526 standard orifice areas.
    """
    return [
        API526_Orifice("D", 0.110, 71.0, '1" x 2"', "DN25 x DN50"),
        API526_Orifice("E", 0.196, 126.5, '1" x 2" / 1.5" x 2.5"', "DN25 x DN50 / DN40 x DN65"),
        API526_Orifice("F", 0.307, 198.1, '1.5" x 2.5" / 2" x 3"', "DN40 x DN65 / DN50 x DN80"),
        API526_Orifice("G", 0.503, 324.5, '2" x 3"', "DN50 x DN80"),
        API526_Orifice("H", 0.785, 506.5, '2" x 3" / 3" x 4"', "DN50 x DN80 / DN80 x DN100"),
        API526_Orifice("J", 1.287, 830.3, '3" x 4"', "DN80 x DN100"),
        API526_Orifice("K", 1.838, 1185.8, '3" x 4" / 4" x 6"', "DN80 x DN100 / DN100 x DN150"),
        API526_Orifice("L", 2.853, 1840.6, '4" x 6"', "DN100 x DN150"),
        API526_Orifice("M", 3.600, 2322.6, '4" x 6"', "DN100 x DN150"),
        API526_Orifice("N", 4.340, 2800.0, '4" x 6"', "DN100 x DN150"),
        API526_Orifice("P", 6.380, 4116.1, '4" x 6" / 6" x 8"', "DN100 x DN150 / DN150 x DN200"),
        API526_Orifice("Q", 11.050, 7129.0, '6" x 8" / 8" x 10"', "DN150 x DN200 / DN200 x DN250"),
        API526_Orifice("R", 16.000, 10322.6, '6" x 8" / 8" x 10"', "DN150 x DN200 / DN200 x DN250"),
        API526_Orifice("T", 26.000, 16774.2, '8" x 10"', "DN200 x DN250"),
    ]


def load_api6d_data():
    """Return standard API 6D full-bore ball valve areas.

    Columns: size_in, area_mm2, size_dn. Areas are approximate, based on
    nominal inside diameter (A = pi/4 * D^2).
    """
    return [
        API6D_Valve('1"', 506.7, "DN25"),
        API6D_Valve('1.5"', 1140.1, "DN40"),
        API6D_Valve('2"', 2026.8, "DN50"),
        API6D_Valve('3"', 4560.4, "DN80"),
        API6D_Valve('4"', 8107.3, "DN100"),
        API6D_Valve('6"', 18241.5, "DN150"),
        API6D_Valve('8"', 32429.3, "DN200"),
        API6D_Valve('10"', 50670.7, "DN250"),
        API6D_Valve('12"', 72965.9, "DN300"),
        API6D_Valve('14"', 100000.0, "DN350"),
        API6D_Valve('16"', 130000.0, "DN400"),
        API6D_Valve('18"', 165000.0, "DN450"),
        API6D_Valve('20"', 205000.0, "DN500"),
        API6D_Valve('24"', 295000.0, "DN600"),
    ]


def api526_effective_orifices():
    """Return (letter, effective_area_mm2, size_in, size_dn) tuples.

    The API 526 standard orifice area is used as the effective area for
    preliminary sizing and vendor screening.
    """
    return [
        (orifice.letter, orifice.area_mm2, orifice.size_in, orifice.size_dn)
        for orifice in load_api526_data()
    ]
