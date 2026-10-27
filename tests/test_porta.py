# SPDX-License-Identifier: LGPL-3.0-or-later
"""Porta (``spec/elementos/porta.md``), etapa 3a: PO01 a PO07, PO12, PO13, exclusão
(PO14, PO15), operações (PO17) e validação (PO20)."""

import json

import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import ifcopenshell.validate
import numpy as np
import pytest
from conftest import PROJECT_ID, Model, snapshot

from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import geometry
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd

T = 0.14
W, H = 0.86, 2.13


def _door_type(model, name="P1", operation_type="SINGLE_SWING_LEFT", **options):
    tx = model.commit(fc.create_door_type(model.doc, name, operation_type, **options))
    return model.doc.get(tx.ops[0].id)


def _door(model, wall, distance=1.0, door_type=None, **options):
    door_type = door_type or _door_type(model)
    tx = model.commit(fc.create_door(model.doc, door_type, wall, distance, **options))
    return model.doc.get(tx.ops[1].id)


def _world(element):
    return ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)


def _body_items(door):
    (body,) = [r for r in door.Representation.Representations
               if r.RepresentationIdentifier == "Body"]
    return body.Items


def test_po01_porta_no_vao(model, tmp_path):
    wall = model.wall()
    door = _door(model, wall)
    ifc = model.reopen(tmp_path)
    (d,) = ifc.by_type("IfcDoor")
    (o,) = ifc.by_type("IfcOpeningElement")
    assert d.GlobalId == door.GlobalId
    assert (d.OverallWidth, d.OverallHeight) == pytest.approx((W, H))
    profile = o.Representation.Representations[0].Items[0].SweptArea
    assert o.PredefinedType == "OPENING"
    assert (profile.XDim, profile.YDim) == pytest.approx((W, H))
    (voids,) = ifc.by_type("IfcRelVoidsElement")
    (fills,) = ifc.by_type("IfcRelFillsElement")
    assert voids.RelatedOpeningElement == o and voids.RelatingBuildingElement.is_a("IfcWall")
    assert fills.RelatingOpeningElement == o and fills.RelatedBuildingElement == d
    assert ue.get_container(d).GlobalId == model.terreo.GlobalId
    assert ue.get_container(d) == ue.get_container(voids.RelatingBuildingElement)


def test_po02_tipo(model, tmp_path):
    _door(model, model.wall())
    ifc = model.reopen(tmp_path)
    (t,) = ifc.by_type("IfcDoorType")
    (d,) = ifc.by_type("IfcDoor")
    assert (t.PredefinedType, t.OperationType) == ("DOOR", "SINGLE_SWING_LEFT")
    assert t.ParameterTakesPrecedence is True
    assert d.PredefinedType is None and d.OperationType is None
    assert ue.get_type(d) == t
    material = ue.get_material(t)
    assert material.is_a("IfcMaterialConstituentSet")
    assert [c.Name for c in material.MaterialConstituents] == ["Lining"]


def test_po03_marco_e_folhas(model, tmp_path):
    _door_type(model)
    _door_type(model, "P2", "DOUBLE_DOOR_SINGLE_SWING", defaults={"width": 1.26})
    ifc = model.reopen(tmp_path)
    p1, p2 = sorted(ifc.by_type("IfcDoorType"), key=lambda t: t.Name)
    (lining,) = [p for p in p1.HasPropertySets if p.is_a("IfcDoorLiningProperties")]
    assert lining.LiningDepth is None
    assert lining.LiningThickness == pytest.approx(0.03)
    (panel,) = [p for p in p1.HasPropertySets if p.is_a("IfcDoorPanelProperties")]
    assert panel.PanelOperation == "SWINGING"
    panels = [p for p in p2.HasPropertySets if p.is_a("IfcDoorPanelProperties")]
    assert sorted(p.PanelPosition for p in panels) == ["LEFT", "RIGHT"]
    assert sum(p.PanelWidth for p in panels) == pytest.approx(1)
    assert ue.get_pset(p2, "BrasBim_EsquadriaTipo")["LarguraPadrao"] == pytest.approx(1.26)


def test_tipo_com_folhas_incoerentes_e_rejeitado(model):
    bad = [{"operation": "SLIDING", "position": "MIDDLE", "width": 1.0, "depth": 0.035}]
    with pytest.raises(OpError):
        fc.create_door_type(model.doc, "X", "SINGLE_SWING_LEFT", panels=bad)
    with pytest.raises(OpError):
        fc.create_door_type(model.doc, "X", lining={"casing_depth": None})


@pytest.mark.parametrize("opens_to", ["left", "right"])
def test_po04_posicionamento_e_sentido(model, opens_to):
    wall = model.wall(ref_line="axis")
    door = _door(model, wall, opens_to=opens_to)
    (opening,) = model.doc.ifc.by_type("IfcOpeningElement")
    assert door.ObjectPlacement.PlacementRelTo == opening.ObjectPlacement
    m_door, m_wall = _world(door), _world(wall)
    door_y, wall_y = m_door[:3, 1], m_wall[:3, 1]
    assert np.dot(door_y, wall_y) == pytest.approx(1 if opens_to == "left" else -1)
    # Origem: começo do vão (esquerda) ou fim do vão (direita), na face oposta à abertura.
    local = np.linalg.inv(m_wall) @ m_door[:, 3]
    if opens_to == "left":
        assert local[:3] == pytest.approx((1.0, -T / 2, 0))
    else:
        assert local[:3] == pytest.approx((1.0 + W, T / 2, 0))


def test_po05_profile(model):
    door = _door(model, model.wall())
    (rep,) = [r for r in door.Representation.Representations
              if r.RepresentationIdentifier == "Profile"]
    assert rep.RepresentationType == "Curve3D"
    assert rep.ContextOfItems.ContextIdentifier == "Profile"
    points = [p.Coordinates for p in rep.Items[0].Points]
    assert points[0] == points[-1]
    assert points[:4] == [(0, 0, 0), (W, 0, 0), (W, 0, H), (0, 0, H)]


def test_po06_corpo_acompanha_a_espessura_da_parede(model):
    wall = model.wall()
    door = _door(model, wall)
    gid = door.GlobalId
    jamb = _body_items(door)[0]
    assert jamb.SweptArea.YDim == pytest.approx(T)
    assert jamb.Depth == pytest.approx(H)

    model.commit(cmd.create_wall_type(model.doc, "Bloco 19", [{"material": "B",
                                                               "thickness": 0.19}]))
    t19 = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Bloco 19")
    model.commit(cmd.edit_wall(model.doc, wall, type=t19))
    door = model.doc.get(gid)
    assert _body_items(door)[0].SweptArea.YDim == pytest.approx(0.19)


def test_po07_alinhamento_na_espessura(model):
    wall = model.wall()  # linha de referência na face esquerda: faixa y de -0,14 a 0
    door_type = _door_type(model, lining={"depth": 0.07})
    door = _door(model, wall, door_type=door_type, align="left_face", offset=0.02)
    location = door.ObjectPlacement.RelativePlacement.Location.Coordinates
    assert location == pytest.approx((0, -0.09, 0))  # marco de -0,09 a -0,02
    assert _body_items(door)[0].SweptArea.YDim == pytest.approx(0.07)


def test_marco_mais_profundo_que_a_parede_avisa(model, caplog):
    door_type = _door_type(model, lining={"depth": 0.20})
    _door(model, model.wall(), door_type=door_type)
    assert "mais profundo que a parede" in caplog.text


def test_geometria_das_folhas():
    lining = {"thickness": 0.03, "casing_thickness": None, "casing_depth": None}
    panels = [{"operation": "SWINGING", "position": "LEFT", "width": 0.5, "depth": 0.035},
              {"operation": "SWINGING", "position": "RIGHT", "width": 0.5, "depth": 0.035}]
    boxes = geometry.door_boxes(1.26, 2.13, 0.14, (0.0, 0.14), lining, panels)
    assert len(boxes) == 3 + 2
    left, right = boxes[3], boxes[4]
    assert (left[0], left[1], right[0], right[1]) == pytest.approx((0.03, 0.63, 0.63, 1.23))
    assert (left[2], left[3]) == pytest.approx((0.14 - 0.035, 0.14))  # encostada em +y
    assert (left[4], left[5]) == pytest.approx((0, 2.10))


def test_po12_quantidades(model):
    door = _door(model, model.wall())
    q = ue.get_pset(door, "Qto_DoorBaseQuantities")
    assert (q["Width"], q["Height"]) == pytest.approx((W, H))
    assert q["Area"] == pytest.approx(W * H)
    assert q["Perimeter"] == pytest.approx(2 * (W + H))


def test_po13_psets(model):
    door = _door(model, model.wall())
    common = ue.get_pset(door, "Pset_DoorCommon")
    assert common["Status"] == "NEW" or common["Status"] == ["NEW"]
    assert common["Reference"] == "P1"
    own = ue.get_pset(door, "BrasBim_Esquadria")
    assert (own["Alinhamento"], own["Deslocamento"]) == ("EIXO", 0.0)
    t = ue.get_pset(ue.get_type(door), "BrasBim_EsquadriaTipo")
    assert (t["LarguraPadrao"], t["AlturaPadrao"], t["BasePadrao"]) == pytest.approx((W, H, 0))



def test_po21_codigo_curto(model, tmp_path):
    """Pente fino (2026-10-27): o tipo de porta tem código curto ("P1"), gravado no
    ``Reference`` do tipo e das portas, e passado à variante de mão."""
    from brasbim.core.fillings import door_types

    door_type = _door_type(model, "P1 – giro 80", code="P1")
    door = _door(model, model.wall(), door_type=door_type)
    assert ue.get_pset(door_type, "Pset_DoorCommon")["Reference"] == "P1"
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "P1"
    assert door_types.read(door_type)["code"] == "P1"
    model.commit(fc.edit_door_type(model.doc, door_type, code="PA"))
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "PA"
    model.history.undo()
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "P1"
    model.commit(fc.edit_door(model.doc, door, hinges="right"))
    variant = ue.get_type(door)
    assert variant != door_type and door_types.read(variant)["code"] == "P1"
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "P1"
    reopened = model.reopen(tmp_path)
    assert {t.Name: door_types.code(door_types.read(t))
            for t in reopened.by_type("IfcDoorType")}["P1 – giro 80"] == "P1"


def test_editar_porta(model):
    wall = model.wall()
    door = _door(model, wall)
    tx = model.commit(fc.edit_door(model.doc, door, width=0.96, distance=2.0,
                                   common={"FireExit": True}))
    assert [op.op for op in tx.ops] == ["opening.edit", "door.edit"]
    assert door.OverallWidth == pytest.approx(0.96)
    assert ue.get_pset(door, "Pset_DoorCommon")["FireExit"] is True
    q = ue.get_pset(wall, "Qto_WallBaseQuantities")
    assert q["NetSideArea"] == pytest.approx(5 * 2.8 - 0.96 * H)
    with pytest.raises(OpError):
        fc.edit_door(model.doc, door, height=3.0)  # mais alta que a parede


def test_porta_mais_alta_que_a_parede_e_recusada(model):
    wall = model.wall()
    with pytest.raises(OpError):
        fc.create_door(model.doc, _door_type(model), wall, 1.0, height=3.0)


def test_po14_excluir_porta(model):
    wall = model.wall()
    empty = len(list(model.doc.ifc))
    door_type = _door_type(model)
    with_type = len(list(model.doc.ifc))
    door = _door(model, wall, door_type=door_type)
    tx = model.commit(fc.delete_door(model.doc, door))
    assert [op.op for op in tx.ops] == ["filling.detach", "door.delete", "opening.delete"]
    assert len(list(model.doc.ifc)) == with_type
    q = ue.get_pset(wall, "Qto_WallBaseQuantities")
    assert q["NetSideArea"] == pytest.approx(q["GrossSideArea"])

    door = _door(model, wall, door_type=door_type)
    model.commit(fc.delete_door(model.doc, door, keep_opening=True))
    assert not model.doc.ifc.by_type("IfcDoor")
    assert len(model.doc.ifc.by_type("IfcOpeningElement")) == 1
    model.commit(cmd.delete_opening(model.doc, model.doc.ifc.by_type("IfcOpeningElement")[0]))
    model.commit(fc.delete_door_type(model.doc, door_type))
    # O material continua no modelo (biblioteca, RF-TIP-03); só o conjunto sai com o tipo.
    assert [m.Name for m in model.doc.ifc.by_type("IfcMaterial")][-1] == "Madeira"
    # O material vem com o estilo da biblioteca (spec/ui 06 §4.4): mais 12 entidades.
    assert len(list(model.doc.ifc)) == empty + 1 + 12
    model.history.undo()
    assert len(list(model.doc.ifc)) == with_type


def test_tipo_em_uso_nao_pode_ser_excluido(model):
    door = _door(model, model.wall())
    door_type = ue.get_type(door)
    with pytest.raises(OpError):
        model.commit(fc.delete_door_type(model.doc, door_type))


def test_po15_excluir_parede_com_porta(model):
    a = model.wall((0, 0), (5, 0))
    model.wall((5, 0), (5, 4))
    _door(model, a)
    before = snapshot(model.doc.ifc)
    tx = model.commit(cmd.delete_wall(model.doc, a))
    assert [op.op for op in tx.ops] == ["filling.detach", "door.delete", "opening.delete",
                                        "path_connection.delete", "wall.delete"]
    for cls in ("IfcDoor", "IfcOpeningElement", "IfcRelFillsElement", "IfcRelVoidsElement"):
        assert not model.doc.ifc.by_type(cls), cls
    model.history.undo()
    assert snapshot(model.doc.ifc) == before


def _session(m: Model):
    wall = m.wall()
    door_type = _door_type(m)
    door = _door(m, wall, door_type=door_type)
    m.commit(fc.edit_door(m.doc, door, opens_to="right", align="right_face", offset=0.01))
    m.commit(fc.edit_door_type(m.doc, door_type, lining={**fc.door_types.read(door_type)[
        "lining"], "thickness": 0.04}))
    double = _door_type(m, "P2", "DOUBLE_DOOR_SLIDING")
    _door(m, wall, 3.0, door_type=double, width=1.2)
    m.commit(fc.delete_door(m.doc, door))


def test_po17_desfazer_refazer_e_reaplicar(model):
    states = [snapshot(model.doc.ifc)]
    m = model
    start = len(m.history.undo_stack)
    _session(m)
    count = len(m.history.undo_stack) - start
    for _ in range(count):
        m.history.undo()
    assert snapshot(m.doc.ifc) == states[0]
    for _ in range(count):
        m.history.redo()
    final = snapshot(m.doc.ifc)

    journal = json.loads(json.dumps([tx.to_dict() for tx in m.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == final


def test_po20_validacao(model, tmp_path):
    wall = model.wall()
    _door(model, wall)
    _door(model, wall, 3.0, door_type=_door_type(model, "P2", "DOUBLE_DOOR_SLIDING"),
          width=1.2, opens_to="right")
    ifc = model.reopen(tmp_path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []
