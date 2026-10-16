# SPDX-License-Identifier: LGPL-3.0-or-later
"""Efeitos derivados de pilar, viga e laje, recalculados por quem aplica as operações.

- Pilar: ``Axis``, ``Body`` e ``Qto_ColumnBaseQuantities`` (pilar.md §2.3, §8)
- Viga: posicionamento (cota do topo), ``Body`` e ``Qto_BeamBaseQuantities`` (viga.md §2.3,
  §8)
- Laje: ``Body`` (espessura do tipo) e ``Qto_SlabBaseQuantities`` (laje.md §2.2, §8)

Elementos de outra origem não são refeitos (corpo preservado).
"""

from __future__ import annotations

import ifcopenshell.util.element

from brasbim.core import props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import register_derive
from brasbim.core.structure import beams, columns, profiles, slabs
from brasbim.core.structure import types as st_types

_CLASSES = {"IfcColumn": columns, "IfcBeam": beams, "IfcSlab": slabs}
_TYPE_CLASSES = ("IfcColumnType", "IfcBeamType", "IfcSlabType")


def _solid(doc: Document, profile, insertion, depth: float):
    ifc = doc.ifc
    return ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((-float(insertion[0]), -float(insertion[1]), 0.0)),
            None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), float(depth))


def _body(doc: Document, element, solid) -> None:
    rep = doc.ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", [solid])
    props.replace_representation(doc, element, "Body", rep)


def rebuild_column(doc: Document, column) -> None:
    state = columns.read_state(doc, column)
    if state["foreign"] is not None:
        return
    doc.changed.add(column.GlobalId)
    h = columns.height(doc, state)
    if h <= 0:
        raise OpError(f"pilar {column.GlobalId}: o topo ficaria abaixo da base")
    column_type = doc.get(state["type"], "IfcColumnType")
    section = st_types.section(column_type)
    ifc = doc.ifc
    curve = ifc.createIfcPolyline([ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                                   ifc.createIfcCartesianPoint((0.0, 0.0, float(h)))])
    props.replace_representation(doc, column, "Axis", ifc.createIfcShapeRepresentation(
        doc.model_axis_context, "Axis", "Curve3D", [curve]))
    insertion = profiles.insertion(section, state["cardinal"])
    _body(doc, column, _solid(doc, st_types.profile(column_type), insertion, h))
    a, p = profiles.area(section), profiles.perimeter(section)
    props.write_qto(doc, column, "Qto_ColumnBaseQuantities", {
        "Length": h, "CrossSectionArea": a, "OuterSurfaceArea": p * h,
        "GrossVolume": a * h, "NetVolume": a * h})


def rebuild_beam(doc: Document, beam) -> None:
    state = beams.read_state(doc, beam)
    if state["foreign"] is not None:
        return
    doc.changed.add(beam.GlobalId)
    beams.place(doc, beam, state)
    beam_type = doc.get(state["type"], "IfcBeamType")
    section = st_types.section(beam_type)
    length = beams.length(state)
    insertion = profiles.insertion(section, beams.CARDINAL[state["ref_line"]])
    _body(doc, beam, _solid(doc, st_types.profile(beam_type), insertion, length))
    a, p = profiles.area(section), profiles.perimeter(section)
    props.write_qto(doc, beam, "Qto_BeamBaseQuantities", {
        "Length": length, "CrossSectionArea": a, "OuterSurfaceArea": p * length,
        "GrossVolume": a * length, "NetVolume": a * length})


def rebuild_slab(doc: Document, slab) -> None:
    state = slabs.read_state(doc, slab)
    if state["foreign"] is not None:
        return
    doc.changed.add(slab.GlobalId)
    t = slabs.thickness(doc, state)
    outline = state["outline"]
    slabs.set_body(doc, slab, outline, t)
    a, p = slabs.area(outline), slabs.perimeter(outline)
    quantities = {"Width": t, "Perimeter": p, "GrossArea": a, "NetArea": a,
                  "GrossVolume": a * t, "NetVolume": a * t}
    sides = slabs.rectangle_sides(outline)
    quantities.update({"Length": sides[0], "Depth": sides[1]} if sides
                      else {"Length": None, "Depth": None})
    props.write_qto(doc, slab, "Qto_SlabBaseQuantities", quantities)


_REBUILD = {"IfcColumn": rebuild_column, "IfcBeam": rebuild_beam, "IfcSlab": rebuild_slab}


def _linked(element, storey_id: str) -> bool:
    module = _CLASSES[element.is_a()]
    values = ifcopenshell.util.element.get_pset(element, module.PSET,
                                                should_inherit=False) or {}
    container = ifcopenshell.util.element.get_container(element)
    return (container is not None and container.GlobalId == storey_id) or (
        values.get("PavimentoTopo") == storey_id)


def affected(doc: Document, dirty: set[str]) -> list:
    found = {}
    for gid in dirty:
        entity = doc.find(gid)
        if entity is None:
            continue
        cls = entity.is_a()
        if cls in _REBUILD:
            found[gid] = entity
        elif cls in _TYPE_CLASSES:
            found.update({e.GlobalId: e for e in ifcopenshell.util.element.get_types(entity)})
        elif cls == "IfcBuildingStorey":
            for ifc_class in _REBUILD:
                found.update({e.GlobalId: e for e in doc.ifc.by_type(ifc_class)
                              if _linked(e, gid)})
    return sorted(found.values(), key=lambda e: e.GlobalId)


def derive(doc: Document, dirty: set[str]) -> None:
    for element in affected(doc, dirty):
        _REBUILD[element.is_a()](doc, element)
    while doc.orphan_profiles:
        profile = doc.orphan_profiles.pop()
        if profile.id() and not doc.ifc.get_total_inverses(profile):
            doc.ifc.remove(profile)


register_derive(derive)
