# SPDX-License-Identifier: LGPL-3.0-or-later
"""Efeitos derivados de pilar, viga e laje, recalculados por quem aplica as operações.

- Pilar: ``Axis``, ``Body`` e ``Qto_ColumnBaseQuantities`` (pilar.md §2.3, §8)
- Viga: posicionamento (cota do topo), ``Body`` e ``Qto_BeamBaseQuantities`` (viga.md §2.3,
  §8)
- Laje: ``Body`` (espessura do tipo) e ``Qto_SlabBaseQuantities`` (laje.md §2.2, §8)
- Recortes por prioridade (spec/ui 12 §2, ``cuts``): o corpo vira ``Clipping``, o
  ``NetVolume`` desconta a parte retirada e a ``IfcRelInterferesElements`` é refeita.
  Quando um elemento muda, os que ele corta (antes e agora) também são refeitos, inclusive
  as paredes.

Elementos de outra origem não são refeitos (corpo preservado).
"""

from __future__ import annotations

import math

import ifcopenshell.util.element

from brasbim.core import profile_defs, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import register_derive
from brasbim.core.structure import beams, columns, cuts, profiles, roofs, slab_openings, slabs
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
    kind = "Clipping" if solid.is_a("IfcBooleanClippingResult") else "SweptSolid"
    rep = doc.ifc.createIfcShapeRepresentation(doc.body_context, "Body", kind, [solid])
    props.replace_representation(doc, element, "Body", rep)


def _elevation(doc: Document, state: dict) -> float:
    return float(doc.get(state["storey"], "IfcBuildingStorey").Elevation or 0.0)


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
    solid = _solid(doc, st_types.profile(column_type), insertion, h)
    own = cuts.piece(doc, column)
    found = cuts.cuts_of(doc, column, own) if own is not None else []
    if found:
        frame = cuts.Frame(ifc, state["point"], math.radians(state["angle"]),
                           _elevation(doc, state) + state["base_offset"])
        solid = cuts.clipped(ifc, solid, frame, found, own)
    _body(doc, column, solid)
    cuts.sync_relations(doc, column, found)
    a, p = profiles.area(section), profiles.perimeter(section)
    net = a * h - (cuts.removed_volume(own, found) if own is not None else 0.0)
    props.write_qto(doc, column, "Qto_ColumnBaseQuantities", {
        "Length": h, "CrossSectionArea": a, "OuterSurfaceArea": p * h,
        "GrossVolume": a * h, "NetVolume": net})


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
    solid = _solid(doc, st_types.profile(beam_type), insertion, length)
    own = cuts.piece(doc, beam)
    found = cuts.cuts_of(doc, beam, own) if own is not None else []
    if found:
        (x0, y0), (x1, y1) = state["start"], state["end"]
        frame = cuts.Frame(doc.ifc, (x0, y0), math.atan2(y1 - y0, x1 - x0),
                           _elevation(doc, state) + beams.top_z(doc, state), beam=True)
        solid = cuts.clipped(doc.ifc, solid, frame, found, own)
    _body(doc, beam, solid)
    cuts.sync_relations(doc, beam, found)
    a, p = profiles.area(section), profiles.perimeter(section)
    net = a * length - (cuts.removed_volume(own, found) if own is not None else 0.0)
    props.write_qto(doc, beam, "Qto_BeamBaseQuantities", {
        "Length": length, "CrossSectionArea": a, "OuterSurfaceArea": p * length,
        "GrossVolume": a * length, "NetVolume": net})


def rebuild_slab(doc: Document, slab) -> None:
    state = slabs.read_state(doc, slab)
    if state["foreign"] is not None:
        return
    doc.changed.add(slab.GlobalId)
    t = slabs.thickness(doc, state)
    outline = state["outline"]
    body = slabs.solid(doc, outline, t)
    own = cuts.piece(doc, slab)
    found = cuts.cuts_of(doc, slab, own) if own is not None else []
    if found:
        frame = cuts.Frame(doc.ifc, outline[0], 0.0,
                           _elevation(doc, state) + state["top_offset"])
        body = cuts.clipped(doc.ifc, body, frame, found, own)
    slabs.set_body(doc, slab, outline, t, body)
    cuts.sync_relations(doc, slab, found)
    slab_openings.refresh(doc, slab, outline[0], t)
    holes = [slab_openings.read_state(o)["outline"] for o in slab_openings.of_slab(slab)]
    a, p = slabs.area(outline), slabs.perimeter(outline)
    removed = cuts.removed_volume(own, found, holes=holes) if own is not None else 0.0
    area_out = cuts.removed_area(own, found, holes) if own is not None else 0.0
    quantities = {"Width": t, "Perimeter": p, "GrossArea": a, "NetArea": a - area_out,
                  "GrossVolume": a * t, "NetVolume": a * t - removed}
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
            if not roofs.is_part(entity):
                found[gid] = entity
        elif cls in _TYPE_CLASSES:
            # As águas da cobertura são refeitas por ``roofs.derive``.
            found.update({e.GlobalId: e for e in ifcopenshell.util.element.get_types(entity)
                          if not roofs.is_part(e)})
        elif cls == "IfcBuildingStorey":
            for ifc_class in _REBUILD:
                found.update({e.GlobalId: e for e in doc.ifc.by_type(ifc_class)
                              if not roofs.is_part(e) and _linked(e, gid)})
    return sorted(found.values(), key=lambda e: e.GlobalId)


def derive(doc: Document, dirty: set[str]) -> None:
    """Refaz os elementos alterados e, depois, os que eles cortam (de maior para menor
    prioridade, para que o recorte veja o estado novo de quem corta)."""
    from brasbim.core.walls import rebuild as wall_rebuild  # evita import circular

    changed = affected(doc, dirty)
    for element in changed:
        _REBUILD[element.is_a()](doc, element)
    victims = {}
    for element in changed:
        for other in cuts.cut_by(doc, element):
            victims[other.GlobalId] = other
    # Quem um elemento excluído cortava (guardado por ``common.remove``).
    for gid in sorted(doc.cut_victims):
        found = doc.find(gid)
        if found is not None:
            victims[gid] = found
    doc.cut_victims.clear()
    order = sorted(victims.values(), key=lambda e: (-cuts.PRIORITY[e.is_a()], e.GlobalId))
    done = {e.GlobalId for e in changed}
    for element in order:
        if element.GlobalId in done or doc.find(element.GlobalId) is None:
            continue
        if element.is_a("IfcWall"):
            wall_rebuild.rebuild_wall(doc, element)
        else:
            _REBUILD[element.is_a()](doc, element)
    # Perfis trocados nos tipos; o composto do perfil do projeto leva as partes junto.
    orphans, doc.orphan_profiles[:] = list(doc.orphan_profiles), []
    profile_defs.drop_profiles(doc, orphans)


register_derive(derive)
