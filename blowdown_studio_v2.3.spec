# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all


PROJECT_DIR = Path.cwd()
HYDDOWN_SRC = PROJECT_DIR.parent / "HydDown" / "src"
VENDOR_DATA_DIR = PROJECT_DIR / "vendor_data"

datas = []
binaries = []
hiddenimports = []

for package_name in ("numpy", "pandas", "scipy", "reportlab", "matplotlib", "CoolProp"):
    tmp_ret = collect_all(package_name)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

pathex = []
if HYDDOWN_SRC.exists():
    sys.path.insert(0, str(HYDDOWN_SRC))
    pathex.append(str(HYDDOWN_SRC))
    tmp_ret = collect_all("hyddown")
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
    hiddenimports += [
        "hyddown",
        "hyddown.fire",
        "hyddown.hdclass",
        "hyddown.transport",
        "hyddown.validator",
    ]

if VENDOR_DATA_DIR.exists():
    for path in VENDOR_DATA_DIR.rglob("*"):
        if path.is_file():
            datas.append((str(path), str(path.relative_to(PROJECT_DIR))))


a = Analysis(
    ["blowdown_studio.py"],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Blowdown Studio_v2.3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
