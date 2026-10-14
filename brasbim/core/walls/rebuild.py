# SPDX-License-Identifier: LGPL-3.0-or-later
"""Efeitos derivados da parede, recalculados por quem aplica as operações (spec §5.2).

- ``IfcMaterialLayerSetUsage`` (sentido e afastamento, spec §3.2)
- Representação ``Body`` (spec §2.2, §6.1), com o recorte das junções (spec §6.2)
- ``Qto_WallBaseQuantities`` (spec §8)
"""

from __future__ import annotations

import logging

import ifcopenshell.api.pset
import ifcopenshell.util.element

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import register_derive
from brasbim.core.walls import connections, joins, params
from brasbim.core.walls import types as wall_types

log = logging.getLogger(__name__)

QTO = "Qto_WallBaseQuantities"
_ORDER = ("Axis", "Body")


# --- representações ------------------------------------------------------------


def _replace_representation(doc: Document, wall, identifier: str, new_rep) -> None:
    shape = wall.Representation
    if shape is None:
        wall.Representation = doc.ifc.createIfcProductDefinitionShape(None, None, [new_rep])
        return
    reps = [r for r in shape.Representations if r.RepresentationIdentifier != identifier]
    old = [r for r in shape.Representations if r.RepresentationIdentifier == identifier]
    reps.append(new_rep)
    reps.sort(key=lambda r: _ORDER.index(r.RepresentationIdentifier)
              if r.RepresentationIdentifier in _ORDER else len(_ORDER))
    shape.Representations = reps
    keep = {doc.axis_context, doc.body_context}
    for rep in old:
        ifcopenshell.util.element.remove_deep2(doc.ifc, rep, do_not_delete=keep)


def _point(doc: Document, p):
    return doc.ifc.createIfcCartesianPoint((float(p[0]), float(p[1])))


def set_axis(doc: Document, wall, path: geom2d.Path) -> None:
    ifc = doc.ifc
    if isinstance(path, geom2d.LinePath):
        curve = ifc.createIfcPolyline([_point(doc, (0.0, 0.0)), _point(doc, path.local_end())])
    else:
        circle = ifc.createIfcCircle(
            ifc.createIfcAxis2Placement2D(_point(doc, path.local_center()), None), path.radius
        )
        curve = ifc.createIfcTrimmedCurve(
            circle,
            [_point(doc, (0.0, 0.0))],
            [_point(doc, path.local_end())],
            path.ccw,
            "CARTESIAN",
        )
    rep = ifc.createIfcShapeRepresentation(doc.axis_context, "Axis", "Curve2D", [curve])
    _replace_representation(doc, wall, "Axis", rep)


def _indexed_curve(doc: Document, segments: list[geom2d.Segment]):
    points = [segments[0].p0]
    indices = []
    for k, seg in enumerate(segments):
        last = k == len(segments) - 1
        start = len(points)
        if isinstance(seg, geom2d.Arc):
            points.append(seg.pm)
            mid = len(points)
            end = 1 if last else (points.append(seg.p1) or len(points))
            indices.append(doc.ifc.createIfcArcIndex((start, mid, end)))
        else:
            end = 1 if last else (points.append(seg.p1) or len(points))
            indices.append(doc.ifc.createIfcLineIndex((start, end)))
    plist = doc.ifc.createIfcCartesianPointList2D([(float(x), float(y)) for x, y in points])
    return doc.ifc.createIfcIndexedPolyCurve(plist, indices, False)


def set_body(doc: Document, wall, segments: list[geom2d.Segment], height: float) -> None:
    ifc = doc.ifc
    profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None, _indexed_curve(doc, segments))
    solid = ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)),
        float(height),
    )
    rep = ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", [solid])
    _replace_representation(doc, wall, "Body", rep)


# --- cálculo -------------------------------------------------------------------


def elevation(doc: Document, storey_id: str) -> float:
    return float(doc.get(storey_id, "IfcBuildingStorey").Elevation or 0.0)


def height(doc: Document, state: dict) -> float:
    if state["top_mode"] == "fixed":
        return float(state["fixed_height"])
    top = elevation(doc, state["top_storey"]) + state["top_offset"]
    return top - (elevation(doc, state["storey"]) + state["base_offset"])


def band(doc: Document, state: dict) -> joins.Band:
    thickness = wall_types.thickness(doc.get(state["type"], "IfcWallType"))
    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], thickness)
    return joins.Band(geom2d.path_from_dict(state["path"]), *params.band(sense, offset, thickness))


def end_cuts(doc: Document, wall, own: joins.Band) -> dict[str, geom2d.Curve]:
    """Curva de corte (coordenadas do pavimento) de cada extremidade com junção.

    Se mais de uma junção chega à mesma extremidade, vale a primeira em ordem de GlobalId
    (decisão do projeto); as outras ficam só como relação.
    """
    from brasbim.core.walls.wall import read_state  # evita import circular

    cuts: dict[str, geom2d.Curve] = {}
    for rel in connections.of_wall(wall):
        if rel.RelatingElement == wall:
            mine, other, theirs = (rel.RelatingConnectionType, rel.RelatedElement,
                                   rel.RelatedConnectionType)
        else:
            mine, other, theirs = (rel.RelatedConnectionType, rel.RelatingElement,
                                   rel.RelatingConnectionType)
        if mine not in joins.ENDS:
            continue
        if mine in cuts:
            log.warning("parede %s: mais de uma junção em %s; %s ignorada no recorte",
                        wall.GlobalId, mine, rel.GlobalId)
            continue
        try:
            other_band = band(doc, read_state(doc, other))
        except OpError:
            continue
        if theirs == "ATPATH":
            cut = joins.t_cut(own, mine, other_band)
        else:
            cut = joins.l_cuts(own, mine, other_band, theirs)[0]
        if cut is not None:
            cuts[mine] = cut
    return cuts


def profile(doc: Document, wall, own: joins.Band) -> list[geom2d.Segment]:
    """Perfil do corpo em coordenadas locais, com as junções resolvidas.

    Se um corte não for possível (face que não alcança o corte, cortes que se cruzam), a
    extremidade fica reta e a relação é mantida.
    """
    to_local = own.frame.curve_to_local
    cuts = {end: to_local(c) for end, c in end_cuts(doc, wall, own).items()}
    attempts = [cuts] + [{e: c} for e, c in cuts.items()] if cuts else []
    for attempt in attempts:
        try:
            return geom2d.band_profile(own.path, own.ymin, own.ymax,
                                       attempt.get("ATSTART"), attempt.get("ATEND"))
        except ValueError as e:
            log.warning("parede %s: recorte de junção não aplicado (%s)", wall.GlobalId, e)
    return geom2d.band_profile(own.path, own.ymin, own.ymax)


def rebuild_wall(doc: Document, wall) -> None:
    from brasbim.core.walls.wall import read_state  # evita import circular

    state = read_state(doc, wall)
    wall_type = doc.get(state["type"], "IfcWallType")
    thickness = wall_types.thickness(wall_type)
    path = geom2d.path_from_dict(state["path"])

    h = height(doc, state)
    if h <= 0:
        raise OpError(f"parede {wall.GlobalId}: altura resultante {h:.3f} m não é positiva")

    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], thickness)
    usage = ifcopenshell.util.element.get_material(wall, should_inherit=False)
    usage.LayerSetDirection = "AXIS2"
    usage.DirectionSense = sense
    usage.OffsetFromReferenceLine = offset

    ymin, ymax = params.band(sense, offset, thickness)
    try:
        segments = profile(doc, wall, joins.Band(path, ymin, ymax))
    except ValueError as e:
        raise OpError(f"parede {wall.GlobalId}: {e}") from e
    set_body(doc, wall, segments, h)

    length = path.centerline_length((ymin + ymax) / 2)
    footprint = geom2d.area(segments)
    _write_qto(
        doc,
        wall,
        {
            "Length": length,
            "Width": thickness,
            "Height": h,
            "GrossFootprintArea": length * thickness,
            "NetFootprintArea": footprint,
            "GrossSideArea": length * h,
            "NetSideArea": length * h,
            "GrossVolume": length * thickness * h,
            "NetVolume": footprint * h,
        },
    )


def _write_qto(doc: Document, wall, quantities: dict) -> None:
    found = ifcopenshell.util.element.get_pset(wall, QTO, should_inherit=False)
    if found:
        qto = doc.ifc.by_id(found["id"])
    else:
        qto = ifcopenshell.api.pset.add_qto(doc.ifc, product=wall, name=QTO)
        guid.stamp(qto, wall.GlobalId, f"qto/{QTO}")
        guid.stamp(qto.DefinesOccurrence[0], wall.GlobalId, f"rel/{QTO}")
    ifcopenshell.api.pset.edit_qto(doc.ifc, qto=qto, properties=quantities)


# --- registro ------------------------------------------------------------------


def affected_walls(doc: Document, dirty: set[str]) -> list:
    walls = {}
    for gid in dirty:
        entity = doc.find(gid)
        if entity is None:
            continue
        if entity.is_a("IfcWall"):
            walls[gid] = entity
        elif entity.is_a("IfcWallType"):
            walls.update({w.GlobalId: w for w in ifcopenshell.util.element.get_types(entity)})
        elif entity.is_a("IfcBuildingStorey"):
            for wall in doc.ifc.by_type("IfcWall"):
                values = ifcopenshell.util.element.get_pset(wall, params.PSET) or {}
                if ifcopenshell.util.element.get_container(wall) == entity or (
                    values.get("PavimentoTopo") == gid
                ):
                    walls[wall.GlobalId] = wall
    # O recorte das vizinhas depende da geometria desta parede.
    for wall in list(walls.values()):
        walls.update({n.GlobalId: n for n in connections.neighbors(wall)})
    return sorted(walls.values(), key=lambda w: w.GlobalId)


def derive(doc: Document, dirty: set[str]) -> None:
    for wall in affected_walls(doc, dirty):
        rebuild_wall(doc, wall)


register_derive(derive)
