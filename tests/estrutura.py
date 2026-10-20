# SPDX-License-Identifier: LGPL-3.0-or-later
"""Utilitários dos testes de pilar, viga e laje."""

import json

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.geom
import ifcopenshell.util.element as ue
import ifcopenshell.validate
import numpy as np
from conftest import PROJECT_ID, snapshot

from brasbim.core import IFC_SCHEMA, props
from brasbim.core.document import Document
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import commands as sc

SLAB_145 = [{"material": "Contrapiso", "thickness": 0.03},
            {"material": "Concreto", "thickness": 0.10},
            {"material": "Reboco", "thickness": 0.015}]


def column_type(model, b=0.20, h=0.40, name=None):
    tx = model.commit(sc.create_column_type(
        model.doc, name or f"Pilar {round(b * 100)}×{round(h * 100)}",
        {"shape": "rect", "b": b, "h": h}))
    return model.doc.get(tx.ops[0].id)


def circle_type(model, d=0.30):
    tx = model.commit(sc.create_column_type(model.doc, f"Pilar Ø{round(d * 100)}",
                                            {"shape": "circle", "d": d}))
    return model.doc.get(tx.ops[0].id)


def beam_type(model, b=0.14, h=0.40):
    tx = model.commit(sc.create_beam_type(model.doc, f"Viga {round(b * 100)}×{round(h * 100)}",
                                          b, h))
    return model.doc.get(tx.ops[0].id)


def slab_type(model, name="Laje maciça 10 cm", layers=None, predefined_type="FLOOR"):
    tx = model.commit(sc.create_slab_type(model.doc, name, layers or [
        {"material": "Concreto", "thickness": 0.10}], predefined_type))
    return model.doc.get(tx.ops[0].id)


def created(model, tx):
    model.commit(tx)
    return model.doc.get(tx.ops[-1].id)


def bounds(element):
    """(mínimo, máximo) do corpo em coordenadas do mundo."""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = props.body_shape(settings, element)
    verts = np.array(shape.geometry.verts).reshape(-1, 3)
    return verts.min(axis=0), verts.max(axis=0)


def qto(element, name):
    return ue.get_pset(element, name)


def valid(ifc) -> bool:
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []
    return True


def check_history(model, action) -> None:
    """Desfazer/refazer ``action`` volta ao mesmo IFC, e o diário reaplicado num documento
    novo reproduz o IFC final."""
    before = snapshot(model.doc.ifc)
    start = len(model.history.undo_stack)
    action()
    count = len(model.history.undo_stack) - start
    final = snapshot(model.doc.ifc)
    for _ in range(count):
        model.history.undo()
    assert snapshot(model.doc.ifc) == before
    for _ in range(count):
        model.history.redo()
    assert snapshot(model.doc.ifc) == final
    journal = json.loads(json.dumps([tx.to_dict() for tx in model.history.journal]))
    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == final


def foreign_ifc(path, ifc_class: str):
    """IFC de outra origem com um elemento extrudado de 0,3 × 0,3 × 1, posicionado em
    (1, 2) relativo ao pavimento, sem o Pset do BrasBim."""
    f = ifcopenshell.api.project.create_file(version=IFC_SCHEMA)
    project = ifcopenshell.api.root.create_entity(f, ifc_class="IfcProject", name="Outro")
    project.UnitsInContext = f.createIfcUnitAssignment(
        [f.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE")])
    model_ctx = ifcopenshell.api.context.add_context(f, context_type="Model")
    body = ifcopenshell.api.context.add_context(f, context_type="Model", context_identifier="Body",
                                                target_view="MODEL_VIEW", parent=model_ctx)
    building = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuilding")
    storey = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuildingStorey", name="P1")
    storey.Elevation = 0.0
    ifcopenshell.api.aggregate.assign_object(f, products=[building], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(f, products=[storey], relating_object=building)
    origin = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None)
    building.ObjectPlacement = f.createIfcLocalPlacement(None, origin)
    storey.ObjectPlacement = f.createIfcLocalPlacement(building.ObjectPlacement, origin)
    element = ifcopenshell.api.root.create_entity(f, ifc_class=ifc_class, name="Importado")
    ifcopenshell.api.spatial.assign_container(f, products=[element], relating_structure=storey)
    element.ObjectPlacement = f.createIfcLocalPlacement(storey.ObjectPlacement,
                                                        f.createIfcAxis2Placement3D(
                                                            f.createIfcCartesianPoint((1.0, 2.0,
                                                                                       0.0)),
                                                            None, None))
    profile = f.createIfcRectangleProfileDef("AREA", None, None, 0.3, 0.3)
    solid = f.createIfcExtrudedAreaSolid(profile, None, f.createIfcDirection((0.0, 0.0, 1.0)),
                                         1.0)
    rep = f.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solid])
    element.Representation = f.createIfcProductDefinitionShape(None, None, [rep])
    f.write(str(path))
    return str(path)
