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
