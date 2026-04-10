# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


PROJECT_DIR = Path.cwd()
HYDDOWN_SRC = PROJECT_DIR.parent / "HydDown" / "src"
VENDOR_DATA_DIR = PROJECT_DIR / "vendor_data"
VERSION_FILE = PROJECT_DIR / "blowdown_studio_version_info.txt"

datas = []
binaries = []
hiddenimports = [
    "hyddown",
    "hyddown.fire",
    "hyddown.hdclass",
    "hyddown.transport",
    "hyddown.validator",
]

# Keep only runtime assets that are actually needed. Avoid bundling test suites,
# notebooks, sample apps, and optional GUI stacks that inflate the executable and
# tend to trigger reputation-based false positives.
binaries += collect_dynamic_libs("numpy")
binaries += collect_dynamic_libs("pandas")
binaries += collect_dynamic_libs("scipy")
binaries += collect_dynamic_libs("CoolProp")

datas += collect_data_files(
    "matplotlib",
    includes=["mpl-data/**"],
)
datas += collect_data_files(
    "reportlab",
    excludes=["**/tests/**", "**/docs/**", "**/demos/**", "**/tools/**"],
)

pathex = []
if HYDDOWN_SRC.exists():
    sys.path.insert(0, str(HYDDOWN_SRC))
    pathex.append(str(HYDDOWN_SRC))

if VENDOR_DATA_DIR.exists():
    for path in VENDOR_DATA_DIR.rglob("*"):
        if path.is_file():
            datas.append((str(path), str(path.parent.relative_to(PROJECT_DIR))))

hiddenimports = list(dict.fromkeys(hiddenimports))

excludes = [
    "pytest",
    "_pytest",
    "IPython",
    "ipykernel",
    "ipywidgets",
    "jupyter_client",
    "jupyter_core",
    "nose",
    "hypothesis",
    "numpy.tests",
    "numpy.testing",
    "numpy.array_api.tests",
    "pandas.tests",
    "scipy.tests",
    "matplotlib.tests",
    "matplotlib.testing",
    "matplotlib.sphinxext",
    "matplotlib.backends.backend_nbagg",
    "matplotlib.backends.backend_webagg",
    "matplotlib.backends.backend_webagg_core",
    "matplotlib.backends.backend_macosx",
    "matplotlib.backends.backend_qt",
    "matplotlib.backends.backend_qt5",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_qt5cairo",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_qtcairo",
    "matplotlib.backends.backend_wx",
    "matplotlib.backends.backend_wxagg",
    "matplotlib.backends.backend_wxcairo",
    "matplotlib.backends.backend_gtk3",
    "matplotlib.backends.backend_gtk3agg",
    "matplotlib.backends.backend_gtk3cairo",
    "matplotlib.backends.backend_gtk4",
    "matplotlib.backends.backend_gtk4agg",
    "matplotlib.backends.backend_gtk4cairo",
    "CoolProp.GUI",
    "CoolProp.tests",
]

a = Analysis(
    ["blowdown_studio.py"],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name="Blowdown Studio_v2.4.1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
