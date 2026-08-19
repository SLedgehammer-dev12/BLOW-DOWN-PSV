"""
Shared engineering constants used across Blowdown Studio modules.
"""

R_U = 8314.462618  # Universal gas constant (J/kmol.K)
P_ATM = 101325.0   # Standard atmospheric pressure (Pa)
T_STD = 288.7      # Standard temperature (K) ~= 60 F

# Standard volumetric-flow reference conditions (for gas flow conversions).
T_REF_NORMAL = 273.15       # 0 degC reference (Nm3/h, SCMH)
T_REF_STANDARD_15C = 288.15  # 15 degC reference (Sm3/h)
T_REF_STANDARD_60F = 288.71  # 60 degF reference (SCFM, MMSCFD)
SCMH_PER_SCFM = 1.6990       # standard m3/h per standard ft3/min (60 F)
SCMH_PER_MMSCFD = 1179.86    # standard m3/h per MMSCFD (60 F)

# Referenced standard editions. These anchor the equation identifiers and
# methodology text; final design work must always use the licensed standard.
API520_EDITION = "API Std 520 Pt. 1, 9th ed. (2014)"
API521_EDITION = "API Std 521, 6th ed. (2014)"
API2000_EDITION = "API Std 2000, 7th ed. (2014)"
ASME_XIII_EDITION = "ASME BPVC Section XIII"
