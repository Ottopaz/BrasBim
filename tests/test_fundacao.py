# SPDX-License-Identifier: LGPL-3.0-or-later
"""Testes da fundação: o núcleo é independente de Qt e o IFC 4.3 faz ida e volta."""

import subprocess
import sys

import ifcopenshell
import ifcopenshell.api.project
import ifcopenshell.api.root

from brasbim.core import IFC_SCHEMA


def test_core_nao_importa_qt():
    codigo = (
        "import sys, brasbim.core; "
        "proibidos = [m for m in sys.modules if m.startswith(('PySide6', 'brasbim.ui'))]; "
        "assert not proibidos, proibidos"
    )
    subprocess.run([sys.executable, "-c", codigo], check=True)


def test_ifc43_ida_e_volta(tmp_path):
    modelo = ifcopenshell.api.project.create_file(version=IFC_SCHEMA)
    projeto = ifcopenshell.api.root.create_entity(modelo, ifc_class="IfcProject", name="Teste")
    caminho = tmp_path / "teste.ifc"
    modelo.write(str(caminho))

    lido = ifcopenshell.open(str(caminho))
    assert lido.schema_identifier == IFC_SCHEMA
    (projeto_lido,) = lido.by_type("IfcProject")
    assert projeto_lido.GlobalId == projeto.GlobalId
    assert projeto_lido.Name == "Teste"
