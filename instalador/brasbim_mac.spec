# SPDX-License-Identifier: GPL-3.0-or-later
# Receita do PyInstaller para o macOS (spec/ui 50 §4): BrasBim.app, sem terminal.
# Uso, num Mac, na raiz do repositório: python instalador/construir_mac.py.
# -*- mode: python -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821 (definido pelo PyInstaller)
PKG = ROOT / "brasbim"
sys.path.insert(0, str(ROOT))
from brasbim import __version__  # noqa: E402

BUNDLE_ID = "io.github.ottopaz.brasbim"

datas, binaries, hidden = [], [], []
# O núcleo carrega as operações pelo nome (ops.base._ensure_loaded): todos os módulos.
hidden += collect_submodules("brasbim")
for name in ("ifcopenshell", "ezdxf", "pyclipr", "shapely"):
    d, b, h = collect_all(name)
    datas += d
    binaries += b
    hidden += h
hidden += collect_submodules("OpenGL")

# Recursos do pacote. Sem "vendor": o conversor de DWG (LibreDWG) é só para Windows.
for folder in ("ui/icons", "ui/fonts", "ui/logo", "library", "perfis"):
    source = PKG / folder
    if source.exists():
        for f in source.rglob("*"):
            if f.is_file() and f.suffix not in (".py", ".pyc"):
                datas.append((str(f), str(f.parent.relative_to(ROOT))))
for name in ("COPYING", "COPYING.LESSER", "THIRD_PARTY_NOTICES.md", "README.md"):
    datas.append((str(ROOT / name), "."))

# Os mesmos módulos do Qt que o instalador do Windows deixa de fora.
EXCLUDES = ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick",
            "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtBluetooth",
            "PySide6.QtNetworkAuth", "PySide6.QtSql", "PySide6.QtTest", "tkinter",
            "matplotlib", "pytest", "IPython"]

a = Analysis(  # noqa: F821
    [str(ROOT / "instalador" / "iniciar.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BrasBim",
    console=False,
    argv_emulation=False,
    icon=str(PKG / "ui" / "logo" / "brasbim.icns"),
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BrasBim",
)
app = BUNDLE(  # noqa: F821
    coll,
    name="BrasBim.app",
    icon=str(PKG / "ui" / "logo" / "brasbim.icns"),
    bundle_identifier=BUNDLE_ID,
    version=__version__,
    info_plist={
        "CFBundleName": "BrasBim",
        "CFBundleDisplayName": "BrasBim",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "CFBundleDevelopmentRegion": "pt_BR",
        "NSHumanReadableCopyright": "GPL-3.0-or-later / LGPL-3.0-or-later",
        "NSHighResolutionCapable": True,
        # Tema sempre claro (ui/theme.py): a barra de título não segue o modo escuro.
        "NSRequiresAquaSystemAppearance": True,
        "LSApplicationCategoryType": "public.app-category.graphics-design",
    },
)
