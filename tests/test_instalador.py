# SPDX-License-Identifier: GPL-3.0-or-later
"""Instalador para Windows (spec/ui 49, IN01–IN02). A montagem em si (IN03) é manual:
``python instalador/construir.py``."""

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_in01_verificacao_do_programa(app, tmp_path):
    from brasbim.ui import app as entry

    assert entry.verify(tmp_path) == 0
    assert (tmp_path / "verificar.ifc").exists() and (tmp_path / "verificar.glb").exists()


def test_in02_receitas_apontam_para_o_que_existe(tmp_path):
    from brasbim import __version__

    iss = (ROOT / "instalador" / "brasbim.iss").read_text(encoding="utf-8")
    for name in re.findall(r'\{#Raiz\}\\([^"\s*]+)', iss):
        if not name.startswith("dist"):
            assert (ROOT / name.replace("\\", "/")).exists(), name
    assert "PrivilegesRequired=lowest" in iss and "BrazilianPortuguese" in iss
    spec = (ROOT / "instalador" / "brasbim.spec").read_text(encoding="utf-8")
    assert "brasbim.ico" in spec and (ROOT / "brasbim/ui/logo/brasbim.ico").exists()
    import importlib.util

    loader = importlib.util.spec_from_file_location("construir",
                                                    ROOT / "instalador" / "construir.py")
    construir = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(construir)
    assert construir.version() == __version__
    path = tmp_path / "versao.txt"
    construir.version_file(path, __version__)
    assert f"'ProductVersion', '{__version__}'" in path.read_text(encoding="utf-8")
    pytest.importorskip("PyInstaller")


def _load(name):
    import importlib.util

    loader = importlib.util.spec_from_file_location(name, ROOT / "instalador" / f"{name}.py")
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def test_in04_receita_do_mac(tmp_path):
    """spec/ui 50: receita, nome do .dmg, LEIA-ME e ícone .icns."""
    import struct

    from brasbim import __version__

    spec = (ROOT / "instalador" / "brasbim_mac.spec").read_text(encoding="utf-8")
    assert "BUNDLE(" in spec and "brasbim.icns" in spec and "io.github.ottopaz.brasbim" in spec
    folders = next(ln for ln in spec.splitlines() if ln.startswith('for folder in ("ui/icons"'))
    assert '"vendor"' not in folders  # LibreDWG é só do Windows
    for name in ("instalador/iniciar.py", "COPYING", "COPYING.LESSER",
                 "THIRD_PARTY_NOTICES.md", "README.md"):
        assert (ROOT / name).exists(), name

    mac = _load("construir_mac")
    assert mac.version() == __version__
    assert mac.dmg_name("1.2.3", "arm64") == "BrasBim-1.2.3-macOS-apple-silicon.dmg"
    assert mac.dmg_name("1.2.3", "x86_64") == "BrasBim-1.2.3-macOS-intel.dmg"
    text = mac.readme("1.2.3", "arm64")
    assert "Apple Silicon" in text and "Abrir Mesmo Assim" in text and "DXF" in text

    data = (ROOT / "brasbim" / "ui" / "logo" / "brasbim.icns").read_bytes()
    assert data[:4] == b"icns" and struct.unpack(">I", data[4:8])[0] == len(data)
    kinds, pos = [], 8
    while pos < len(data):
        kind, size = data[pos:pos + 4], struct.unpack(">I", data[pos + 4:pos + 8])[0]
        assert data[pos + 8:pos + 16] == b"\x89PNG\r\n\x1a\n"
        kinds.append(kind)
        pos += size
    assert pos == len(data)
    assert kinds == [b"icp4", b"icp5", b"icp6", b"ic07", b"ic08", b"ic09"]
