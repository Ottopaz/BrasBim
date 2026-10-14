# SPDX-License-Identifier: LGPL-3.0-or-later
"""Efeitos derivados das esquadrias, recalculados por quem aplica as operações.

- Posicionamento relativo à abertura e sentido de abertura (``porta.md`` §6.1)
- ``OverallWidth``/``OverallHeight`` copiados da abertura (§3.1)
- Representações ``Profile`` e ``Body`` (§2.3, §6.2)
- Contenção no pavimento da parede (§2.7, §6.3)
- ``Qto_DoorBaseQuantities`` (§8)

Portas de outra origem (sem ``BrasBim_Esquadria``) mantêm o corpo (§6.6).
"""

from __future__ import annotations

import logging

import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document
from brasbim.core.fillings import door_types, doors, geometry, params
from brasbim.core.ops.base import register_derive
from brasbim.core.walls import openings

log = logging.getLogger(__name__)


# --- representações ------------------------------------------------------------


def _set_profile(doc: Document, door, width: float, height: float) -> None:
    ifc = doc.ifc
    corners = [(0.0, 0.0, 0.0), (width, 0.0, 0.0), (width, 0.0, height), (0.0, 0.0, height)]
    points = [ifc.createIfcCartesianPoint(c) for c in corners]
    curve = ifc.createIfcPolyline(points + [points[0]])
    rep = ifc.createIfcShapeRepresentation(doc.profile_context, "Profile", "Curve3D", [curve])
    props.replace_representation(doc, door, "Profile", rep)


def _box_solid(ifc, box):
    x0, x1, y0, y1, z0, z1 = box
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None,
        ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint(((x0 + x1) / 2, (y0 + y1) / 2)), None),
        x1 - x0, y1 - y0)
    return ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, z0)), None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), z1 - z0)


def _set_body(doc: Document, door, boxes) -> None:
    solids = [_box_solid(doc.ifc, b) for b in boxes]
    rep = doc.ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", solids)
    props.replace_representation(doc, door, "Body", rep)


# --- posição ---------------------------------------------------------------------


def _place(doc: Document, element, opening, opens_to: str, width: float, a: float, b: float):
    """Posiciona a esquadria relativa à abertura (``porta.md`` §6.1, passo 2)."""
    ifc = doc.ifc
    if opens_to == "left":
        location, x = (0.0, a, 0.0), 1.0
    else:
        location, x = (width, b, 0.0), -1.0
    placement = element.ObjectPlacement
    old = placement.RelativePlacement
    placement.PlacementRelTo = opening.ObjectPlacement
    placement.RelativePlacement = ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint(location), ifc.createIfcDirection((0.0, 0.0, 1.0)),
        ifc.createIfcDirection((x, 0.0, 0.0)))
    ifcopenshell.util.element.remove_deep2(ifc, old)


def _contain(doc: Document, element, wall) -> None:
    storey = ifcopenshell.util.element.get_container(wall)
    if storey is not None and ifcopenshell.util.element.get_container(element) != storey:
        rel = ifcopenshell.api.spatial.assign_container(
            doc.ifc, products=[element], relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")


def rebuild_door(doc: Document, door) -> None:
    doc.changed.add(door.GlobalId)
    if not door.FillsVoids:
        return  # sem abertura não há posição (porta independente é V1)
    opening = door.FillsVoids[0].RelatingOpeningElement
    wall = openings.host(opening)
    if wall is None:
        return
    _contain(doc, door, wall)
    if not doors.is_parametric(door):
        return
    o = openings.read_state(opening)
    band, _ = openings.wall_info(doc, wall)
    state = doors.read_state(door)
    tstate = door_types.read(doc.get(state["type"], "IfcDoorType"))
    lining = tstate["lining"]
    thickness = band.ymax - band.ymin
    depth = lining["depth"] or thickness
    if depth > thickness + 1e-6:
        log.warning("porta %s: marco (%.3f m) mais profundo que a parede (%.3f m)",
                    door.GlobalId, depth, thickness)
    a, b = params.lining_band(state["align"], state["offset"], depth, band.ymin, band.ymax)
    w, h = o["width"], o["height"]
    _place(doc, door, opening, state["opens_to"], w, a, b)
    # Faces da parede no sistema da porta (+y da porta = lado para onde abre).
    if state["opens_to"] == "left":
        faces = (band.ymin - a, band.ymax - a)
    else:
        faces = (b - band.ymax, b - band.ymin)
    door.OverallWidth, door.OverallHeight = w, h
    _set_profile(doc, door, w, h)
    _set_body(doc, door, geometry.door_boxes(w, h, depth, faces, lining, tstate["panels"]))
    props.write_qto(doc, door, params.QTO, {
        "Width": w, "Height": h, "Area": w * h, "Perimeter": 2 * (w + h)})


# --- registro ------------------------------------------------------------------


def _fillings(opening) -> list:
    return [r.RelatedBuildingElement for r in opening.HasFillings]


def affected_doors(doc: Document, dirty: set[str]) -> list:
    found = {}
    for gid in dirty:
        entity = doc.find(gid)
        if entity is None:
            continue
        if entity.is_a("IfcDoor"):
            found[gid] = entity
        elif entity.is_a("IfcDoorType"):
            found.update({d.GlobalId: d for d in ifcopenshell.util.element.get_types(entity)})
        elif entity.is_a("IfcWall"):
            for opening in openings.of_wall(entity):
                found.update({e.GlobalId: e for e in _fillings(opening) if e.is_a("IfcDoor")})
    return sorted(found.values(), key=lambda d: d.GlobalId)


def derive(doc: Document, dirty: set[str]) -> None:
    for door in affected_doors(doc, dirty):
        rebuild_door(doc, door)


register_derive(derive)
