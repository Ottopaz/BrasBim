# SPDX-License-Identifier: GPL-3.0-or-later
# Receita do PyInstaller (spec/ui 49 §4): o BrasBim congelado numa pasta, sem console.
# Uso, na raiz do repositório: python instalador/construir.py (chama esta receita).
# -*- mode: python -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821 (definido pelo PyInstaller)
PKG = ROOT / "brasbim"

datas, binaries, hidden = [], [], []
# O núcleo carrega as operações pelo nome (ops.base._ensure_loaded): todos os módulos.
hidden += collect_submodules("brasbim")
for name in ("ifcopenshell", "ezdxf", "pyclipr", "shapely"):
    d, b, h = collect_all(name)
    datas += d
    binaries += b
    hidden += h
hidden += collect_submodules("OpenGL")

# Recursos do pacote (achados pelo caminho do módulo: ficam no mesmo lugar relativo).
for folder in ("ui/icons", "ui/fonts", "ui/logo", "library", "perfis", "vendor"):
    source = PKG / folder
    if source.exists():
        for f in source.rglob("*"):
            if f.is_file() and f.suffix not in (".py", ".pyc"):
                datas.append((str(f), str(f.parent.relative_to(ROOT))))

# Módulos do Qt que o BrasBim não usa (o pacote fica bem menor).
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
    icon=str(PKG / "ui" / "logo" / "brasbim.ico"),
    version=str(ROOT / "build" / "versao.txt"),
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BrasBim",
)
