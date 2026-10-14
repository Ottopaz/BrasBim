# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pavimentos (``IfcBuildingStorey``).

PROVISÓRIO: o pavimento ainda não tem spec própria. Estas operações existem para que a
parede (RF-ELE-01) possa ser criada, testada e reaplicada (critérios P04 e P15).

Operações: ``storey.create`` / ``storey.delete`` (data: name, elevation) e
``storey.edit`` (before/after: name, elevation).
"""

from __future__ import annotations

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import (
    Op,
    check_before,
    invert_swap,
    register,
    register_inverse_pair,
)


def read(storey) -> dict:
    return {"name": storey.Name, "elevation": float(storey.Elevation or 0.0)}


def _write(doc: Document, storey, state: dict) -> None:
    storey.Name = state["name"]
    storey.Elevation = float(state["elevation"])
    old = storey.ObjectPlacement
    if old is not None:
        rel = old.RelativePlacement
        old.RelativePlacement = axis_placement(doc.ifc, (0.0, 0.0), storey.Elevation, (1.0, 0.0))
        ifcopenshell.util.element.remove_deep2(doc.ifc, rel)
    else:
        storey.ObjectPlacement = local_placement(
            doc.ifc, doc.building.ObjectPlacement, storey.Elevation
        )


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    storey = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcBuildingStorey")
    storey.GlobalId = op.id
    _write(doc, storey, op.data)
    building = doc.building
    rel = ifcopenshell.api.aggregate.assign_object(
        doc.ifc, products=[storey], relating_object=building
    )
    guid.stamp(rel, building.GlobalId, "aggregates")
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    storey = doc.get(op.id, "IfcBuildingStorey")
    if ifcopenshell.util.element.get_contained(storey):
        raise OpError("o pavimento contém elementos")
    ifcopenshell.api.root.remove_product(doc.ifc, product=storey)
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    storey = doc.get(op.id, "IfcBuildingStorey")
    state = read(storey)
    check_before(op, state)
    state.update(op.after or {})
    _write(doc, storey, state)
    return {op.id}


register_inverse_pair("storey.create", _create, "storey.delete", _delete)
register("storey.edit", _edit, invert_swap)
