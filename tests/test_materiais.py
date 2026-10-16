# SPDX-License-Identifier: LGPL-3.0-or-later
"""Estilos de material (``spec/ui/06-planta-por-camadas.md`` §4; UI56, UI57, UI59)."""

import math

import ifcopenshell
import ifcopenshell.validate
import pytest
from conftest import snapshot

from brasbim.core import materials
from brasbim.core.ops import Transaction


def _edit(model, name, style):
    return model.commit(Transaction("Editar material",
                                    [materials.edit_op(model.doc, name, style)]))


def _styles(ifc, name):
    (mat,) = [m for m in ifc.by_type("IfcMaterial") if m.Name == name]
    (definition,) = mat.HasRepresentation
    out = {}
    for rep in definition.Representations:
        ctx = rep.ContextOfItems
        out[(ctx.ContextType, ctx.ContextIdentifier)] = [
            s for item in rep.Items for s in item.Styles]
    return out


def test_ui59_biblioteca_gravada(model, tmp_path):
    ifc = model.reopen(tmp_path)
    styles = _styles(ifc, "Bloco cerâmico")
    (surface,) = styles[("Model", "Body")]
    assert surface.is_a("IfcSurfaceStyle") and surface.Side == "BOTH"
    (fill,) = styles[("Plan", "Body")]
    assert fill.ModelOrDraughting is True
    (hatch,) = fill.FillStyles
    assert hatch.StartOfNextHatchLine.wrappedValue == pytest.approx(0.03)
    reboco = _styles(ifc, "Reboco")
    assert list(reboco) == [("Model", "Body")]  # corte "Nenhum": sem representação Plan
    assert materials.style(model.doc, "Bloco cerâmico") == {
        **materials.LIBRARY["Bloco cerâmico"], "default": False}


def test_ui56_editar_estilo(model, tmp_path):
    before = snapshot(model.doc.ifc)
    old = materials.state(model.doc, "Bloco cerâmico")["style"]
    new = {"color": "#AA5533", "cut": {"pattern": "cross", "background": None, "angle": 30.0,
                                        "spacing": 0.04, "line_color": "#2B2A27"}}
    _edit(model, "Bloco cerâmico", new)
    assert materials.state(model.doc, "Bloco cerâmico")["style"] == new
    ifc = model.reopen(tmp_path)
    styles = _styles(ifc, "Bloco cerâmico")
    (surface,) = styles[("Model", "Body")]
    colour = surface.Styles[0].SurfaceColour
    assert (round(colour.Red * 255), round(colour.Green * 255), round(colour.Blue * 255)) \
        == (0xAA, 0x55, 0x33)
    (fill,) = styles[("Plan", "Body")]
    hatches = [h for h in fill.FillStyles if h.is_a("IfcFillAreaStyleHatching")]
    assert sorted(round(math.degrees(h.HatchLineAngle), 6) for h in hatches) == [30, 120]
    assert all(h.StartOfNextHatchLine.wrappedValue == pytest.approx(0.04) for h in hatches)
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger)
    assert logger.statements == []
    model.history.undo()
    assert materials.state(model.doc, "Bloco cerâmico")["style"] == old
    assert snapshot(model.doc.ifc) == before
    model.history.redo()
    assert materials.state(model.doc, "Bloco cerâmico")["style"] == new


def test_sem_estilo_e_padrao(model):
    _edit(model, "Reboco", None)
    found = materials.style(model.doc, "Reboco")
    assert found["default"] and found["color"] == materials.LIBRARY["Reboco"]["color"]
    assert not model.doc.ifc.by_type("IfcMaterial")[0].HasRepresentation or \
        materials.state(model.doc, "Reboco")["style"] is None


def test_ui57_material_de_outra_origem_com_textura(model):
    f = model.doc.ifc
    mat = f.createIfcMaterial("Pedra")
    texture = f.createIfcImageTexture(True, True, None, None, None, "pedra.png")
    rendering = f.createIfcSurfaceStyleRendering(f.createIfcColourRgb(None, 0.5, 0.4, 0.3),
                                                 0.0, None, None, None, None, None, None,
                                                 "NOTDEFINED")
    surface = f.createIfcSurfaceStyle("Pedra", "BOTH",
                                      [rendering, f.createIfcSurfaceStyleWithTextures([texture])])
    rep = f.createIfcStyledRepresentation(model.doc.body_context, "Body", None,
                                          [f.createIfcStyledItem(None, [surface], None)])
    f.createIfcMaterialDefinitionRepresentation(None, None, [rep], mat)
    found = materials.style(model.doc, "Pedra")
    assert found["color"] == "#80664C" and not found["default"]
    new = {"color": found["color"],
           "cut": {**materials.DEFAULT_CUT, "pattern": "lines", "spacing": 0.02}}
    _edit(model, "Pedra", new)
    assert any(s.is_a("IfcSurfaceStyleWithTextures") for s in surface.Styles)
    assert materials.style(model.doc, "Pedra")["cut"]["pattern"] == "lines"


@pytest.mark.parametrize("name", ["Concreto", "Vidro", "Alumínio"])
def test_corte_solido_da_biblioteca_lido_de_volta(model, name):
    """O fundo sólido do corte volta como gravado (o ``IfcColour`` é um SELECT; antes o
    corte sólido voltava como "nenhum")."""
    from brasbim.core.walls import types as wall_types

    material = wall_types.material_named(model.doc, name)
    assert materials.read_style(material)["cut"] == materials.LIBRARY[name]["cut"]
