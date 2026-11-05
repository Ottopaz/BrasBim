# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exportar IFC 2x3 e IFC 4 (spec/ui 47, EX01–EX05)."""

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest
from casa_completa import build

from brasbim.core import ifc_export as ie
from brasbim.core.document import OpError


@pytest.fixture(scope="module")
def casa():
    return build()


def _gids(f, cls):
    return {e.GlobalId for e in f.by_type(cls)}


def test_ex01_ifc4_valido_com_os_mesmos_globalids(casa, tmp_path):
    path = tmp_path / "casa_ifc4.ifc"
    report = ie.export(casa.doc, str(path), ie.Options(version="IFC4"))
    f = ifcopenshell.open(str(path))
    assert f.schema == "IFC4" and not ie.errors(f)
    for cls in ("IfcWall", "IfcDoor", "IfcSlab", "IfcSpace", "IfcCovering"):
        assert _gids(f, cls) == _gids(casa.doc.ifc, cls)
    assert report.elements > 20 and not report.adapted
    assert not f.by_type("IfcAnnotation")  # desenhos 2D desligados por padrão


def test_ex02_ifc2x3_adaptado_e_valido(casa, tmp_path):
    path = tmp_path / "casa_2x3.ifc"
    report = ie.export(casa.doc, str(path))
    f = ifcopenshell.open(str(path))
    assert f.schema == "IFC2X3" and not ie.errors(f)
    walls = f.by_type("IfcWall")
    assert walls and all(w.is_a("IfcWallStandardCase") for w in walls)
    assert _gids(f, "IfcWall") == _gids(casa.doc.ifc, "IfcWall")
    (door,) = f.by_type("IfcDoor")
    style = ue.get_type(door)
    assert style.is_a("IfcDoorStyle") and style.OperationType == "SINGLE_SWING_LEFT"
    assert ue.get_type(f.by_type("IfcWindow")[0]).is_a("IfcWindowStyle")
    (column,) = f.by_type("IfcColumn")
    assert ue.get_material(column).is_a("IfcMaterial")
    assert f.by_type("IfcFurnishingElement") and f.by_type("IfcFlowTerminal")
    proxy = f.by_type("IfcBuildingElementProxy")
    assert [p.ObjectType for p in proxy] == ["GeographicElement"]
    assert all(e.OwnerHistory is not None for e in f.by_type("IfcRoot"))
    assert len(f.by_type("IfcOwnerHistory")) == 1
    assert not f.by_type("IfcAnnotation")
    assert report.adapted["paredes como IfcWallStandardCase"] == len(walls)
    assert "IFC 2x3" in report.text(str(path))
    # o projeto aberto não mudou
    assert casa.doc.ifc.schema.startswith("IFC4X3") and casa.doc.ifc.by_type("IfcAnnotation")


def test_ex03_destino_estrutura_e_instalacoes(casa):
    f, _ = ie.build(casa.doc, ie.Options(target="engineering"))
    assert not ie.errors(f)
    for cls in ("IfcFurnishingElement", "IfcFlowTerminal", "IfcCovering",
                "IfcBuildingElementProxy"):
        assert not f.by_type(cls), cls
    assert f.by_type("IfcWall") and f.by_type("IfcColumn") and f.by_type("IfcSpace")
    assert f.by_type("IfcDoor")


def test_ex04_so_o_visivel(casa):
    column = casa.doc.ifc.by_type("IfcColumn")[0]
    casa.doc.extra_hidden = {column.GlobalId}
    try:
        f, _ = ie.build(casa.doc, ie.Options(visible_only=True))
        assert not f.by_type("IfcColumn") and f.by_type("IfcBeam")
        f, _ = ie.build(casa.doc, ie.Options(visible_only=False))
        assert f.by_type("IfcColumn")
    finally:
        casa.doc.extra_hidden = None


def test_ex05_propriedades_e_desenhos(casa):
    f, _ = ie.build(casa.doc, ie.Options(own_properties=False))
    assert not ie.errors(f)
    assert not [p for p in f.by_type("IfcPropertySet") if p.Name.startswith("BrasBim_")]
    assert f.by_type("IfcElementQuantity")
    f, _ = ie.build(casa.doc, ie.Options(version="IFC4", drawings=True))
    assert f.by_type("IfcAnnotation") and not ie.errors(f)
    with pytest.raises(OpError, match="versão"):
        ie.build(casa.doc, ie.Options(version="IFC5"))
