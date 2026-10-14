# SPDX-License-Identifier: LGPL-3.0-or-later
"""Dividir parede (spec §5.1) e IFC de outra origem (P16)."""

import json
import math

import ifcopenshell
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
import ifcopenshell.util.element as ue
import numpy as np
import pytest
from conftest import PROJECT_ID, snapshot

from brasbim.core import IFC_SCHEMA
from brasbim.core.document import Document, OpError
from brasbim.core.ops import History, Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls.wall import read_state

T = 0.14


def _qto(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")


def _rels(ifc):
    return ifc.by_type("IfcRelConnectsPathElements")


def _new_wall(model, tx):
    return model.doc.get(next(op for op in tx.ops if op.op == "wall.split").data["new"])


def test_dividir_parede_reta(model):
    wall = model.wall((0, 0), (5, 0))
    before = snapshot(model.doc.ifc)
    tx = model.commit(cmd.split_wall(model.doc, wall, (2, 0)))
    assert [op.op for op in tx.ops] == ["wall.split", "path_connection.create"]
    new = _new_wall(model, tx)
    assert _qto(wall)["Length"] == pytest.approx(2)
    assert _qto(new)["Length"] == pytest.approx(3)
    assert _qto(wall)["NetFootprintArea"] + _qto(new)["NetFootprintArea"] == pytest.approx(5 * T)
    (rel,) = _rels(model.doc.ifc)
    assert (rel.RelatingElement, rel.RelatedElement) == (wall, new)
    assert (rel.RelatingConnectionType, rel.RelatedConnectionType) == ("ATEND", "ATSTART")
    assert ue.get_type(new) == model.type14
    assert ue.get_container(new) == model.terreo

    model.history.undo()
    assert snapshot(model.doc.ifc) == before


def test_dividir_leva_aberturas_e_juncoes_para_a_nova_parede(model):
    tx = model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                       [(0, 0), (6, 0), (6, 3)]))
    a, b = (model.doc.get(op.id) for op in tx.ops if op.op == "wall.create")
    t = model.wall((1, 0), (1, -2), ref_line="axis")  # T no começo de a
    o1 = model.commit(cmd.create_opening(model.doc, a, 2.0, 0.9, 2.1)).ops[0].id
    o2 = model.commit(cmd.create_opening(model.doc, a, 4.0, 0.9, 2.1)).ops[0].id

    with pytest.raises(OpError, match="abertura"):
        cmd.split_wall(model.doc, a, (2.5, 0))

    tx = model.commit(cmd.split_wall(model.doc, a, (3, 0)))
    new = _new_wall(model, tx)
    moved = model.doc.get(o2)
    assert moved.VoidsElements[0].RelatingBuildingElement == new
    assert moved.ObjectPlacement.RelativePlacement.Location.Coordinates[0] == pytest.approx(1.0)
    assert model.doc.get(o1).VoidsElements[0].RelatingBuildingElement == a
    pairs = {(r.RelatingElement, r.RelatedElement, r.RelatingConnectionType,
              r.RelatedConnectionType) for r in _rels(model.doc.ifc)}
    assert pairs == {(a, t, "ATPATH", "ATSTART"), (a, new, "ATEND", "ATSTART"),
                     (new, b, "ATEND", "ATSTART")}
    assert _qto(new)["NetSideArea"] == pytest.approx(3 * 2.8 - 0.9 * 2.1)


def test_dividir_parede_em_arco(model):
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                          (2, 0), (0, 2), (-2, 0), ref_line="axis"))
    wall = model.doc.get(tx.ops[0].id)
    tx = model.commit(cmd.split_wall(model.doc, wall, (2 * math.cos(1), 2 * math.sin(1))))
    new = _new_wall(model, tx)
    assert _qto(wall)["Length"] == pytest.approx(2 * 1)
    assert _qto(new)["Length"] == pytest.approx(2 * (math.pi - 1))
    assert len(_rels(model.doc.ifc)) == 1


def test_dividir_e_reaplicar_diario(model):
    wall = model.wall((0, 0), (5, 0))
    model.commit(cmd.create_opening(model.doc, wall, 3.5, 0.9, 2.1))
    model.commit(cmd.split_wall(model.doc, wall, (2, 0)))
    model.history.undo()
    model.history.redo()
    journal = json.loads(json.dumps([tx.to_dict() for tx in model.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(model.doc.ifc)


# --- P16 -------------------------------------------------------------------------------


def _foreign_ifc(path):
    """IFC montado direto com o IfcOpenShell, sem o Pset BrasBim_Parede."""
    f = ifcopenshell.api.project.create_file(version=IFC_SCHEMA)
    project = ifcopenshell.api.root.create_entity(f, ifc_class="IfcProject", name="Outro")
    project.UnitsInContext = f.createIfcUnitAssignment(
        [f.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE")]
    )
    model_ctx = ifcopenshell.api.context.add_context(f, context_type="Model")
    body = ifcopenshell.api.context.add_context(f, context_type="Model", context_identifier="Body",
                                                target_view="MODEL_VIEW", parent=model_ctx)
    plan = ifcopenshell.api.context.add_context(f, context_type="Plan")
    axis = ifcopenshell.api.context.add_context(f, context_type="Plan", context_identifier="Axis",
                                                target_view="GRAPH_VIEW", parent=plan)
    building = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuilding")
    storey = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuildingStorey", name="P1")
    storey.Elevation = 0.0
    ifcopenshell.api.aggregate.assign_object(f, products=[building], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(f, products=[storey], relating_object=building)
    ifcopenshell.api.geometry.edit_object_placement(f, product=building)
    ifcopenshell.api.geometry.edit_object_placement(f, product=storey)

    wall_type = ifcopenshell.api.root.create_entity(f, ifc_class="IfcWallType", name="Ext 20",
                                                    predefined_type="SOLIDWALL")
    lset = ifcopenshell.api.material.add_material_set(f, name="Ext 20", set_type="IfcMaterialLayerSet")
    concrete = ifcopenshell.api.material.add_material(f, name="Concreto")
    layer = ifcopenshell.api.material.add_layer(f, layer_set=lset, material=concrete)
    layer.LayerThickness = 0.2
    ifcopenshell.api.material.assign_material(f, products=[wall_type], material=lset)

    wall = ifcopenshell.api.root.create_entity(f, ifc_class="IfcWall", name="Importada")
    wall.Description = "parede de outro programa"
    ifcopenshell.api.spatial.assign_container(f, products=[wall], relating_structure=storey)
    ifcopenshell.api.type.assign_type(f, related_objects=[wall], relating_type=wall_type)
    ifcopenshell.api.material.assign_material(f, products=[wall], type="IfcMaterialLayerSetUsage",
                                              material=lset)
    matrix = np.identity(4)
    matrix[:3, 3] = (1.0, 2.0, 0.0)
    ifcopenshell.api.geometry.edit_object_placement(f, product=wall, matrix=matrix)
    ifcopenshell.api.geometry.assign_representation(
        f, product=wall,
        representation=ifcopenshell.api.geometry.add_axis_representation(
            f, context=axis, axis=((0.0, 0.0), (4.0, 0.0))),
    )
    ifcopenshell.api.geometry.assign_representation(
        f, product=wall,
        representation=ifcopenshell.api.geometry.add_wall_representation(
            f, context=body, length=4.0, height=2.5, thickness=0.2),
    )
    pset = ifcopenshell.api.pset.add_pset(f, product=wall, name="Fabricante_Dados")
    ifcopenshell.api.pset.edit_pset(f, pset=pset, properties={"Codigo": "X1"})
    f.write(str(path))
    return wall.GlobalId


def test_p16_ifc_sem_pset_proprio(tmp_path):
    src = tmp_path / "outro.ifc"
    gid = _foreign_ifc(src)
    doc = Document.open(str(src))
    wall = doc.get(gid, "IfcWall")
    state = read_state(doc, wall)
    assert state["top_mode"] == "fixed"
    assert state["fixed_height"] == pytest.approx(2.5)
    assert state["ref_line"] == "right_face"
    assert state["path"] == {"kind": "line", "start": [1.0, 2.0], "end": [5.0, 2.0]}

    history = History(doc)
    history.commit(cmd.edit_wall(doc, wall, fixed_height=3.0))
    out = tmp_path / "gravado.ifc"
    doc.save(str(out))

    ifc = ifcopenshell.open(str(out))
    w = ifc.by_guid(gid)
    assert w.Name == "Importada"
    assert w.Description == "parede de outro programa"
    assert ue.get_pset(w, "Fabricante_Dados")["Codigo"] == "X1"
    assert ue.get_type(w).Name == "Ext 20"
    usage = ue.get_material(w, should_inherit=False)
    assert usage.is_a("IfcMaterialLayerSetUsage") and usage.ForLayerSet.LayerSetName == "Ext 20"
    assert ue.get_pset(w, "BrasBim_Parede")["TipoTopo"] == "ALTURA_FIXA"
    assert ue.get_pset(w, "Qto_WallBaseQuantities")["Height"] == pytest.approx(3.0)
    assert ue.get_pset(w, "Qto_WallBaseQuantities")["Length"] == pytest.approx(4.0)
