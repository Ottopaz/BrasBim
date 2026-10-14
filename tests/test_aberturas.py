# SPDX-License-Identifier: LGPL-3.0-or-later
"""Aberturas, preenchimentos e exclusão em cascata (spec §6.3, §6.4, §8; P08 a P11)."""

import ifcopenshell.api.root
import ifcopenshell.util.element as ue
import ifcopenshell.validate
import pytest
from conftest import snapshot

from brasbim.core.document import OpError
from brasbim.core.walls import commands as cmd

T = 0.14
H = 2.8


def _qto(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")


def _opening(model, wall, *args, **kwargs):
    tx = model.commit(cmd.create_opening(model.doc, wall, *args, **kwargs))
    return model.doc.get(tx.ops[0].id)


def _door(model):
    # A porta ainda não tem spec (RF-ELE-05); aqui ela é só o elemento que preenche.
    return ifcopenshell.api.root.create_entity(model.doc.ifc, ifc_class="IfcDoor", name="P1")


def test_p08_abertura(model, tmp_path):
    wall = model.wall((0, 0), (5, 0))
    opening = _opening(model, wall, 1.0, 0.9, 2.1)
    ifc = model.reopen(tmp_path)
    (o,) = ifc.by_type("IfcOpeningElement")
    (w,) = ifc.by_type("IfcWall")
    assert o.GlobalId == opening.GlobalId
    assert o.PredefinedType == "OPENING"
    assert not o.ContainedInStructure
    assert o.ObjectPlacement.PlacementRelTo == w.ObjectPlacement
    assert o.ObjectPlacement.RelativePlacement.Location.Coordinates == pytest.approx((1, 0, 0))
    (rel,) = ifc.by_type("IfcRelVoidsElement")
    assert rel.RelatingBuildingElement == w and rel.RelatedOpeningElement == o
    solid = o.Representation.Representations[0].Items[0]
    assert solid.SweptArea.is_a("IfcRectangleProfileDef")
    assert (solid.SweptArea.XDim, solid.SweptArea.YDim) == pytest.approx((0.9, 2.1))
    assert solid.Depth == pytest.approx(T + 0.02)
    q = _qto(w)
    assert q["NetSideArea"] == pytest.approx(5 * 2.8 - 0.9 * 2.1)
    assert q["GrossSideArea"] == pytest.approx(5 * 2.8)
    assert q["NetVolume"] == pytest.approx((5 * 2.8 - 0.9 * 2.1) * T)
    assert q["NetFootprintArea"] == pytest.approx((5 - 0.9) * T)


def test_p09_porta_preenche_abertura(model, tmp_path):
    wall = model.wall()
    opening = _opening(model, wall, 1.0, 0.9, 2.1)
    door = _door(model)
    tx = model.commit(cmd.attach_filling(model.doc, opening, door))
    assert [op.op for op in tx.ops] == ["filling.attach"]
    ifc = model.reopen(tmp_path)
    (rel,) = ifc.by_type("IfcRelFillsElement")
    assert rel.RelatingOpeningElement.GlobalId == opening.GlobalId
    assert rel.RelatedBuildingElement.GlobalId == door.GlobalId
    model.history.undo()
    assert not model.doc.ifc.by_type("IfcRelFillsElement")


def test_p10_nicho(model):
    wall = model.wall()
    _opening(model, wall, 2.0, 0.6, 0.6, sill=1.0, kind="RECESS", depth=0.05, side="right")
    q = _qto(wall)
    assert q["NetSideArea"] == pytest.approx(5 * H)
    assert q["NetVolume"] == pytest.approx(5 * T * H - 0.6 * 0.6 * 0.05)
    (o,) = model.doc.ifc.by_type("IfcOpeningElement")
    assert o.PredefinedType == "RECESS"
    assert o.Representation.Representations[0].Items[0].Depth == pytest.approx(0.05)


def test_nicho_mais_fundo_que_a_parede_e_rejeitado(model):
    wall = model.wall()
    with pytest.raises(OpError):
        model.commit(cmd.create_opening(model.doc, wall, 1, 0.6, 0.6, kind="RECESS", depth=0.2))
    assert not model.doc.ifc.by_type("IfcOpeningElement")


@pytest.mark.parametrize("args", [(4.5, 0.9, 2.1, 0.0), (1.0, 0.9, 2.1, 1.0), (-0.1, 0.9, 2.1, 0)])
def test_abertura_fora_dos_limites_e_rejeitada(model, args):
    wall = model.wall()
    with pytest.raises(OpError):
        model.commit(cmd.create_opening(model.doc, wall, *args))
    assert not model.doc.ifc.by_type("IfcOpeningElement")
    assert not model.doc.ifc.by_type("IfcRelVoidsElement")


def test_abertura_em_parede_curva_e_v1(model):
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                          (2, 0), (0, 2), (-2, 0)))
    with pytest.raises(OpError):
        model.commit(cmd.create_opening(model.doc, tx.ops[0].id, 0.5, 0.9, 2.1))


def test_abertura_acompanha_a_parede(model, caplog):
    wall = model.wall(ref_line="axis")
    opening = _opening(model, wall, 1.0, 0.9, 2.1)
    model.commit(cmd.create_wall_type(model.doc, "Bloco 19", [{"material": "B",
                                                               "thickness": 0.19}]))
    t19 = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Bloco 19")
    model.commit(cmd.edit_wall(model.doc, wall, type=t19))
    solid = opening.Representation.Representations[0].Items[0]
    assert solid.Depth == pytest.approx(0.19 + 0.02)
    assert solid.Position.Location.Coordinates[1] == pytest.approx(0.095 + 0.01)

    # Encurtar a parede deixa a abertura fora: ela fica, com aviso (spec §6.3).
    model.commit(cmd.edit_wall(model.doc, wall, path={"kind": "line", "start": [0, 0],
                                                     "end": [1.5, 0]}))
    assert model.doc.find(opening.GlobalId) is not None
    assert "fora do comprimento" in caplog.text


def test_editar_abertura(model):
    wall = model.wall()
    opening = _opening(model, wall, 1.0, 0.9, 2.1)
    tx = model.commit(cmd.edit_opening(model.doc, opening, width=1.2, sill=0.5))
    assert tx.ops[0].before == {"width": 0.9, "sill": 0.0}
    assert _qto(wall)["NetSideArea"] == pytest.approx(5 * H - 1.2 * 2.1)
    assert _qto(wall)["NetFootprintArea"] == pytest.approx(5 * T)


def test_p11_excluir_parede_com_abertura(model):
    empty = len(list(model.doc.ifc))
    a = model.wall((0, 0), (5, 0))
    b = model.wall((5, 0), (5, 4))
    opening = _opening(model, a, 1.0, 0.9, 2.1)
    door = _door(model)
    model.commit(cmd.attach_filling(model.doc, opening, door))
    before = snapshot(model.doc.ifc)

    tx = model.commit(cmd.delete_wall(model.doc, a))
    assert [op.op for op in tx.ops] == ["filling.detach", "opening.delete",
                                        "path_connection.delete", "wall.delete"]
    ifc = model.doc.ifc
    for cls in ("IfcOpeningElement", "IfcRelVoidsElement", "IfcRelFillsElement",
                "IfcRelConnectsPathElements"):
        assert not ifc.by_type(cls), cls
    assert ifc.by_type("IfcDoor")  # a porta fica até existir door.delete (RF-ELE-05)
    assert _qto(b)["NetFootprintArea"] == pytest.approx(4 * T)

    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    model.history.redo()
    model.commit(cmd.delete_wall(model.doc, b))
    ifc.remove(ifc.by_guid(door.GlobalId))
    assert len(list(ifc)) == empty


def test_p17_validacao_com_aberturas(model, tmp_path):
    wall = model.wall()
    opening = _opening(model, wall, 1.0, 0.9, 2.1)
    _opening(model, wall, 3.0, 0.6, 0.6, sill=1.0, kind="RECESS", depth=0.05)
    model.commit(cmd.attach_filling(model.doc, opening, _door(model)))
    ifc = model.reopen(tmp_path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []
