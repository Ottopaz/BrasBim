# SPDX-License-Identifier: LGPL-3.0-or-later
"""Porta (``spec/elementos/porta.md``), etapa 3b: dobradiças e sentido (PO08, PO09),
mover (PO10, PO11), dividir a parede (PO16), IFC de outra origem (PO18) e parede em
arco (PO19)."""

import json

import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import ifcopenshell.validate
import numpy as np
import pytest
from conftest import PROJECT_ID, Model, _value, snapshot
from test_divisao_e_importacao import _foreign_ifc

from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd

W, H = 0.86, 2.13


def _door_type(model, name="P1", operation_type="SINGLE_SWING_LEFT", **options):
    tx = model.commit(fc.create_door_type(model.doc, name, operation_type, **options))
    return model.doc.get(tx.ops[0].id)


def _door(model, wall, distance=1.0, door_type=None, **options):
    door_type = door_type or _door_type(model)
    tx = model.commit(fc.create_door(model.doc, door_type, wall, distance, **options))
    return model.doc.get(next(op.id for op in tx.ops if op.op == "door.create"))


def _world(element):
    return ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)


def _ops(tx):
    return [op.op for op in tx.ops]


def _body(door):
    (body,) = [r for r in door.Representation.Representations
               if r.RepresentationIdentifier == "Body"]
    return _value(body)


# --- PO08, PO09 ------------------------------------------------------------------------


def test_po08_inverter_dobradicas_usa_a_variante(model):
    wall = model.wall()
    p1 = _door_type(model)
    door = _door(model, wall, door_type=p1)
    placement, body = _world(door), _body(door)
    before = snapshot(model.doc.ifc)

    tx = model.commit(fc.flip_hinges(model.doc, door))
    assert _ops(tx) == ["door_type.create", "door_type.edit", "door.edit"]
    variant = ue.get_type(door)
    assert (variant.Name, variant.OperationType) == ("P1 (D)", "SINGLE_SWING_RIGHT")
    assert ue.get_pset(variant, params.TYPE_PSET)["Variante"] == p1.GlobalId
    assert ue.get_pset(p1, params.TYPE_PSET)["Variante"] == variant.GlobalId
    # Nada mais muda: posição, corpo e código da etiqueta.
    assert np.allclose(_world(door), placement)
    assert _body(door) == body
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "P1"

    assert _ops(model.commit(fc.flip_hinges(model.doc, door))) == ["door.edit"]
    assert ue.get_type(door) == p1
    assert _ops(model.commit(fc.flip_hinges(model.doc, door))) == ["door.edit"]
    assert ue.get_type(door) == variant
    assert len(model.doc.ifc.by_type("IfcDoorType")) == 2

    # Criar com as dobradiças à direita reaproveita a variante.
    tx = model.commit(fc.create_door(model.doc, p1, wall, 3.0, hinges="right"))
    assert _ops(tx) == ["opening.create", "door.create", "filling.attach"]
    assert tx.ops[1].data["type"] == variant.GlobalId

    for _ in range(4):
        model.history.undo()
    assert snapshot(model.doc.ifc) == before


def test_variante_de_tipo_com_folha_fixa():
    state = door_types.default_state("SWING_FIXED_LEFT")
    state["name"] = "PF"
    state["panels"][0]["width"] = 0.7
    state["panels"][1]["width"] = 0.3
    mirror = door_types.mirrored(state, "X")
    assert mirror["operation_type"] == "SWING_FIXED_RIGHT"
    assert mirror["name"] == "PF (D)"
    assert [(p["operation"], p["position"], p["width"]) for p in mirror["panels"]] == [
        ("FIXEDPANEL", "LEFT", 0.3), ("SWINGING", "RIGHT", 0.7)]
    door_types.validate(mirror)
    assert door_types.mirrored(mirror, "Y")["name"] == "PF (E)"


def test_tipo_sem_mao_nao_inverte_dobradicas(model):
    double = _door_type(model, "P2", "DOUBLE_DOOR_SINGLE_SWING")
    door = _door(model, model.wall(), door_type=double, width=1.26)
    with pytest.raises(OpError, match="dobradiças"):
        fc.flip_hinges(model.doc, door)


def test_variante_acompanha_o_tipo(model):
    p1 = _door_type(model)
    door = _door(model, model.wall(), door_type=p1)
    model.commit(fc.flip_hinges(model.doc, door))
    variant = ue.get_type(door)
    lining = {**door_types.read(p1)["lining"], "thickness": 0.04}
    tx = model.commit(fc.edit_door_type(model.doc, p1, lining=lining, name="PA"))
    assert _ops(tx) == ["door_type.edit", "door_type.edit"]
    assert variant.Name == "PA (D)"
    assert door_types.read(variant)["lining"]["thickness"] == pytest.approx(0.04)
    assert ue.get_pset(door, "Pset_DoorCommon")["Reference"] == "P1"  # só muda ao editar

    # Excluir o tipo original (sem portas) desfaz o vínculo na variante.
    tx = model.commit(fc.delete_door_type(model.doc, p1))
    assert _ops(tx) == ["door_type.edit", "door_type.delete"]
    assert door_types.read(variant)["variant"] is None
    model.history.undo()
    assert door_types.read(variant)["variant"] == p1.GlobalId


def test_po09_inverter_sentido(model):
    door = _door(model, model.wall())
    door_type = ue.get_type(door)
    y = _world(door)[:3, 1]
    tx = model.commit(fc.flip_opening(model.doc, door))
    assert _ops(tx) == ["door.edit"]
    assert tx.ops[0].after == {"opens_to": "right"}
    assert ue.get_type(door) == door_type
    assert np.dot(_world(door)[:3, 1], y) == pytest.approx(-1)


# --- PO10, PO11 ------------------------------------------------------------------------


def test_po10_mover_ao_longo_da_parede(model):
    wall = model.wall()
    door = _door(model, wall)
    net = ue.get_pset(wall, "Qto_WallBaseQuantities")["NetSideArea"]
    tx = model.commit(fc.edit_door(model.doc, door, distance=2.0))
    assert _ops(tx) == ["opening.edit"]
    assert np.linalg.inv(_world(wall))[:3] @ _world(door)[:, 3] == pytest.approx(
        (2.0, -0.14, 0))  # marco na face direita (linha de referência na esquerda)
    assert ue.get_pset(wall, "Qto_WallBaseQuantities")["NetSideArea"] == pytest.approx(net)
    with pytest.raises(OpError, match="não cabe"):
        fc.edit_door(model.doc, door, distance=4.5)


def test_po11_mover_para_parede_de_outro_pavimento(model):
    a = model.wall()
    tx = model.commit(cmd.create_wall(model.doc, model.type14, model.superior, (0, 3), (5, 3)))
    b = model.doc.get(tx.ops[0].id)
    door = _door(model, a)
    before = snapshot(model.doc.ifc)

    model.commit(fc.edit_door(model.doc, door, wall=b, distance=2.5))
    (voids,) = model.doc.ifc.by_type("IfcRelVoidsElement")
    assert voids.RelatingBuildingElement == b
    assert ue.get_container(door) == model.superior
    assert _world(door)[:3, 3] == pytest.approx((2.5, 3 - 0.14, 2.8))
    qa, qb = (ue.get_pset(w, "Qto_WallBaseQuantities") for w in (a, b))
    assert qa["NetSideArea"] == pytest.approx(qa["GrossSideArea"])
    assert qb["NetSideArea"] == pytest.approx(qb["GrossSideArea"] - W * H)

    model.history.undo()
    assert snapshot(model.doc.ifc) == before


# --- PO16 --------------------------------------------------------------------------------


def test_po16_dividir_parede_com_porta(model):
    wall = model.wall((0, 0), (5, 0))
    door = _door(model, wall, 3.0)
    placement = _world(door)
    before = snapshot(model.doc.ifc)
    with pytest.raises(OpError, match="abertura"):
        cmd.split_wall(model.doc, wall, (3.4, 0))

    tx = model.commit(cmd.split_wall(model.doc, wall, (2, 0)))
    new = model.doc.get(next(op for op in tx.ops if op.op == "wall.split").data["new"])
    opening = fc.opening_of(door)
    assert opening.VoidsElements[0].RelatingBuildingElement == new
    assert np.allclose(_world(door), placement)
    assert ue.get_container(door) == model.terreo
    assert door.ObjectPlacement.PlacementRelTo == opening.ObjectPlacement

    model.history.undo()
    assert snapshot(model.doc.ifc) == before


# --- PO19 --------------------------------------------------------------------------------


def test_po19_parede_em_arco_e_recusada(model):
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                          (2, 0), (0, 2), (-2, 0)))
    arc = model.doc.get(tx.ops[0].id)
    door_type = _door_type(model)
    with pytest.raises(OpError, match="arco"):
        fc.create_door(model.doc, door_type, arc, 1.0)
    door = _door(model, model.wall(), door_type=door_type)
    with pytest.raises(OpError, match="arco"):
        fc.edit_door(model.doc, door, wall=arc)


# --- PO18 --------------------------------------------------------------------------------


def _foreign_door_ifc(path):
    """Parede, abertura e porta montadas direto no IfcOpenShell, como outro programa faria:
    porta sem tipo, com OperationType na ocorrência, corpo próprio com estilo e sem os
    Psets do BrasBim."""
    wall_id = _foreign_ifc(path)
    f = ifcopenshell.open(str(path))
    wall = f.by_guid(wall_id)
    storey = ue.get_container(wall)
    body_ctx = next(c for c in f.by_type("IfcGeometricRepresentationSubContext")
                    if c.ContextIdentifier == "Body")

    def point(*c):
        return f.createIfcCartesianPoint(tuple(float(v) for v in c))

    def axis(origin, z=None, x=None):
        return f.createIfcAxis2Placement3D(
            point(*origin), z and f.createIfcDirection(z), x and f.createIfcDirection(x))

    def box(origin, xdim, ydim, depth, position=None):
        profile = f.createIfcRectangleProfileDef(
            "AREA", None, f.createIfcAxis2Placement2D(point(*origin), None), xdim, ydim)
        return f.createIfcExtrudedAreaSolid(profile, position or axis((0, 0, 0)),
                                            f.createIfcDirection((0.0, 0.0, 1.0)), depth)

    opening = ifcopenshell.api.root.create_entity(f, ifc_class="IfcOpeningElement")
    opening.PredefinedType = "OPENING"
    opening.ObjectPlacement = f.createIfcLocalPlacement(wall.ObjectPlacement,
                                                        axis((1.0, 0.0, 0.0)))
    hole = box((0.45, 1.05), 0.9, 2.1, 0.3,
               axis((0.0, 0.25, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)))
    opening.Representation = f.createIfcProductDefinitionShape(None, None, [
        f.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [hole])])
    f.createIfcRelVoidsElement(ifcopenshell.guid.new(), None, None, None, wall, opening)

    door = ifcopenshell.api.root.create_entity(f, ifc_class="IfcDoor", name="Porta importada")
    door.Description = "porta de outro programa"
    door.PredefinedType = "DOOR"
    door.OperationType = "SINGLE_SWING_RIGHT"
    door.OverallWidth, door.OverallHeight = 0.9, 2.1
    door.ObjectPlacement = f.createIfcLocalPlacement(opening.ObjectPlacement,
                                                     axis((0.0, 0.08, 0.0)))
    leaf = box((0.45, 0.02), 0.9, 0.04, 2.1)
    color = f.createIfcColourRgb(None, 0.6, 0.4, 0.2)
    style = f.createIfcSurfaceStyle("Madeira", "BOTH", [
        f.createIfcSurfaceStyleShading(color, None)])
    f.createIfcStyledItem(leaf, [style], None)
    door.Representation = f.createIfcProductDefinitionShape(None, None, [
        f.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [leaf])])
    f.createIfcRelFillsElement(ifcopenshell.guid.new(), None, None, None, opening, door)
    ifcopenshell.api.spatial.assign_container(f, products=[door], relating_structure=storey)
    pset = ifcopenshell.api.pset.add_pset(f, product=door, name="Pset_DoorCommon")
    ifcopenshell.api.pset.edit_pset(f, pset=pset, properties={"Reference": "PX-01",
                                                              "FireRating": "EI30"})
    f.write(str(path))
    return door.GlobalId


def test_po18_porta_de_outra_origem(tmp_path, caplog):
    src = tmp_path / "outro.ifc"
    gid = _foreign_door_ifc(src)
    original = snapshot(ifcopenshell.open(str(src)))[gid]
    doc = Document.open(str(src))
    history = History(doc)
    door = doc.get(gid, "IfcDoor")
    assert not doors.is_parametric(door)
    state = doors.read_state(door)
    assert state["type"] is None and state["foreign"]["operation_type"] == "SINGLE_SWING_RIGHT"
    assert state["common"] == {"Reference": "PX-01", "FireRating": "EI30"}

    # Trocar Psets preserva tudo o mais, inclusive na regravação.
    tx = fc.edit_door(doc, door, common={**state["common"], "FireExit": True})
    assert _ops(tx) == ["door.edit"]
    history.commit(tx)
    doc.save(str(tmp_path / "psets.ifc"))
    saved = ifcopenshell.open(str(tmp_path / "psets.ifc"))
    assert snapshot(saved)[gid] == original
    assert ue.get_pset(saved.by_guid(gid), "Pset_DoorCommon")["FireExit"] is True
    assert not ue.get_pset(saved.by_guid(gid), params.PSET)

    # Mover: a abertura muda e a porta acompanha, com o corpo de origem.
    body = _body(door)
    start = _world(door)
    tx = fc.edit_door(doc, door, distance=2.0)
    assert _ops(tx) == ["opening.edit"]
    history.commit(tx)
    assert _world(door)[:3, 3] == pytest.approx(start[:3, 3] + (1.0, 0, 0))
    assert _body(door) == body
    assert not doors.is_parametric(door)
    moved = snapshot(doc.ifc)

    # Redimensionar converte em porta paramétrica, com aviso; desfazer volta sem perda.
    tx = fc.edit_door(doc, door, width=1.0)
    assert _ops(tx) == ["opening.edit", "door_type.create", "door.edit"]
    history.commit(tx)
    assert "convertida em porta paramétrica" in caplog.text
    assert doors.is_parametric(door)
    door_type = ue.get_type(door)
    assert (door_type.Name, door_type.OperationType) == ("Porta importada", "SINGLE_SWING_RIGHT")
    assert (door.OperationType, door.PredefinedType) == (None, None)
    assert door.OverallWidth == pytest.approx(1.0)
    assert {r.RepresentationIdentifier for r in door.Representation.Representations} == {
        "Body", "Profile"}
    common = ue.get_pset(door, "Pset_DoorCommon")
    assert (common["Reference"], common["FireRating"]) == ("PX-01", "EI30")
    assert ue.get_pset(door, params.QTO)["Width"] == pytest.approx(1.0)
    converted = snapshot(doc.ifc)

    history.undo()
    assert snapshot(doc.ifc) == moved
    history.redo()
    assert snapshot(doc.ifc) == converted

    path = tmp_path / "convertido.ifc"
    doc.save(str(path))
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifcopenshell.open(str(path)), log)
    assert log.statements == []


# --- PO17 (etapa 3b) ----------------------------------------------------------------------


def _session(m: Model):
    a = m.wall((0, 0), (5, 0))
    tx = m.commit(cmd.create_wall(m.doc, m.type14, m.superior, (0, 3), (5, 3)))
    b = m.doc.get(tx.ops[0].id)
    p1 = _door_type(m)
    door = _door(m, a, 3.0, door_type=p1, hinges="right")
    m.commit(fc.flip_opening(m.doc, door))
    m.commit(fc.flip_hinges(m.doc, door))
    m.commit(fc.edit_door(m.doc, door, distance=3.5))
    m.commit(cmd.split_wall(m.doc, a, (2, 0)))
    other = _door(m, b, 1.0, door_type=p1)
    m.commit(fc.edit_door(m.doc, other, wall=a, distance=0.5, hinges="right"))


def test_po17_etapa_3b_desfazer_refazer_e_reaplicar(model):
    initial = snapshot(model.doc.ifc)
    start = len(model.history.undo_stack)
    _session(model)
    count = len(model.history.undo_stack) - start
    for _ in range(count):
        model.history.undo()
    assert snapshot(model.doc.ifc) == initial
    for _ in range(count):
        model.history.redo()
    final = snapshot(model.doc.ifc)

    journal = json.loads(json.dumps([tx.to_dict() for tx in model.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == final
