# SPDX-License-Identifier: LGPL-3.0-or-later
"""Efeitos derivados da parede, recalculados por quem aplica as operações (spec §5.2).

- ``IfcMaterialLayerSetUsage`` (sentido e afastamento, spec §3.2)
- Representação ``Body`` (spec §2.2, §6.1), com o recorte das junções (spec §6.2)
- ``Qto_WallBaseQuantities`` (spec §8)
"""

from __future__ import annotations

import logging
import math

import ifcopenshell.util.element

from brasbim.core import geom2d, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import register_derive
from brasbim.core.walls import connections, joins, openings, params, top
from brasbim.core.walls import types as wall_types

log = logging.getLogger(__name__)

QTO = "Qto_WallBaseQuantities"


# --- representações ------------------------------------------------------------


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
    props.replace_representation(doc, wall, "Axis", rep)


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


def _point3(doc: Document, p):
    return doc.ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _top_cut(doc: Document, x0: float, x1: float, a, b, y0: float, y1: float):
    """Semiespaço acima do trecho de topo ``a``–``b`` ([posição, altura]), limitado na
    planta pelo retângulo ``[x0, x1] × [y0, y1]`` (spec/ui 08 §4.2, [IFC-PBHS])."""
    ifc = doc.ifc
    dx, dz = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dz)
    plane = ifc.createIfcPlane(ifc.createIfcAxis2Placement3D(
        _point3(doc, (a[0], 0.0, a[1])),
        ifc.createIfcDirection((-dz / n, 0.0, dx / n)),  # normal para cima
        ifc.createIfcDirection((dx / n, 0.0, dz / n)),
    ))
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    boundary = ifc.createIfcPolyline([_point(doc, c) for c in corners])
    # AgreementFlag falso: o semiespaço fica do lado para onde a normal aponta (acima do
    # topo), e é ele que a diferença retira.
    return ifc.createIfcPolygonalBoundedHalfSpace(
        plane, False,
        ifc.createIfcAxis2Placement3D(_point3(doc, (0.0, 0.0, 0.0)), None, None), boundary)


def set_body(doc: Document, wall, segments: list[geom2d.Segment], height: float,
             profile=None, tilt: float = 0.0, cut=None) -> None:
    """Corpo: extrusão da planta (vertical, ou inclinada na parede tombada) e, com topo
    inclinado, recorte por um semiespaço limitado por trecho (spec/ui 08 §4.2, §5.2).
    ``cut`` = (referencial, recortes, prisma) dos recortes por prioridade (spec/ui 12 §2)."""
    ifc = doc.ifc
    area = ifc.createIfcArbitraryClosedProfileDef("AREA", None, _indexed_curve(doc, segments))
    t = math.radians(tilt)
    solid = ifc.createIfcExtrudedAreaSolid(
        area,
        ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
        ifc.createIfcDirection((0.0, math.sin(t), math.cos(t)) if tilt else (0.0, 0.0, 1.0)),
        float(height) / math.cos(t),
    )
    kind = "SweptSolid"
    if profile:
        pts = geom2d.polygon(segments)
        margin = 1.0 + float(height) * abs(math.tan(t))
        xmin, xmax = min(p[0] for p in pts) - 1.0, max(p[0] for p in pts) + 1.0
        ymin, ymax = min(p[1] for p in pts) - margin, max(p[1] for p in pts) + margin
        xs = [xmin, *(x for x, _ in profile[1:-1]), xmax]
        for k in range(len(profile) - 1):
            solid = ifc.createIfcBooleanClippingResult(
                "DIFFERENCE", solid,
                _top_cut(doc, xs[k], xs[k + 1], profile[k], profile[k + 1], ymin, ymax))
        kind = "Clipping"
    if cut is not None:
        from brasbim.core.structure import cuts  # evita import circular

        frame, found, own = cut
        solid = cuts.clipped(ifc, solid, frame, found, own)
        kind = "Clipping"
    rep = ifc.createIfcShapeRepresentation(doc.body_context, "Body", kind, [solid])
    props.replace_representation(doc, wall, "Body", rep)


# --- cálculo -------------------------------------------------------------------


def elevation(doc: Document, storey_id: str) -> float:
    return float(doc.get(storey_id, "IfcBuildingStorey").Elevation or 0.0)


def height(doc: Document, state: dict) -> float:
    """Altura da parede; com topo inclinado, a maior altura do perfil (spec/ui 08 §4.2)."""
    if state.get("top_profile"):
        return top.highest(state["top_profile"])
    if state["top_mode"] == "fixed":
        return float(state["fixed_height"])
    z_top = elevation(doc, state["top_storey"]) + state["top_offset"]
    return z_top - (elevation(doc, state["storey"]) + state["base_offset"])


def widening(state: dict) -> float:
    """Parede tombada: a planta da base é alargada por 1/cos θ, para a espessura medida
    perpendicular às faces ser a das camadas (spec/ui 08 §5.2)."""
    return 1.0 / math.cos(math.radians(state.get("tilt") or 0.0))


def band(doc: Document, state: dict) -> joins.Band:
    """Faixa da parede na base (alargada na parede tombada)."""
    thickness = wall_types.thickness(doc.get(state["type"], "IfcWallType"))
    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], thickness)
    k = widening(state)
    ymin, ymax = params.band(sense, offset, thickness)
    return joins.Band(geom2d.path_from_dict(state["path"]), ymin * k, ymax * k)


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

    doc.changed.add(wall.GlobalId)
    state = read_state(doc, wall)
    wall_type = doc.get(state["type"], "IfcWallType")
    thickness = wall_types.thickness(wall_type)
    path = geom2d.path_from_dict(state["path"])

    h = height(doc, state)
    if h <= 0:
        raise OpError(f"parede {wall.GlobalId}: altura resultante {h:.3f} m não é positiva")

    tilt = float(state["tilt"])
    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], thickness)
    if not tilt:
        usage = ifcopenshell.util.element.get_material(wall, should_inherit=False)
        usage.LayerSetDirection = "AXIS2"
        usage.DirectionSense = sense
        usage.OffsetFromReferenceLine = offset

    own = band(doc, state)
    try:
        segments = profile(doc, wall, own)
    except ValueError as e:
        raise OpError(f"parede {wall.GlobalId}: {e}") from e
    top_profile = state["top_profile"]
    # Recortes por pilar, viga e laje (spec/ui 12 §2); topo inclinado e parede tombada
    # ficam sem (``cuts.piece`` devolve None).
    from brasbim.core.structure import cuts  # evita import circular

    prism = cuts.piece(doc, wall)
    found = cuts.cuts_of(doc, wall, prism) if prism is not None else []
    cut = None
    if found:
        storey = doc.get(state["storey"], "IfcBuildingStorey")
        z = float(storey.Elevation or 0.0) + state["base_offset"]
        cut = (cuts.Frame(doc.ifc, own.frame.origin, own.frame.angle, z), found, prism)
    set_body(doc, wall, segments, h, top_profile, tilt, cut)
    cuts.sync_relations(doc, wall, found)
    openings.refresh(doc, wall, own, h, top_profile)
    cut = openings.deductions(wall, own, h, segments)
    if tilt:
        _warn_tilt_joins(doc, wall, tilt)

    # Parede tombada: faces e volume medidos na inclinação (k = 1/cos θ).
    k = widening(state)
    length = path.centerline_length((own.ymin + own.ymax) / 2)
    footprint = geom2d.area(segments)
    if top_profile:
        side = top.side_area(top_profile, 0.0, length)
        net_volume = top.volume(geom2d.polygon(segments), top_profile)
    else:
        side, net_volume = length * h, footprint * h
    if found:
        net_volume -= cuts.removed_volume(prism, found)
    props.write_qto(
        doc,
        wall,
        QTO,
        {
            "Length": length,
            "Width": thickness,
            "Height": h,
            "GrossFootprintArea": length * thickness * k,
            "NetFootprintArea": footprint - cut["footprint"],
            "GrossSideArea": side * k,
            "NetSideArea": side * k - cut["side"],
            "GrossVolume": side * thickness * k,
            "NetVolume": net_volume - cut["volume"],
        },
    )


def _warn_tilt_joins(doc: Document, wall, tilt: float) -> None:
    """Junções de paredes tombadas são resolvidas só na base (spec/ui 08 §5.1)."""
    from brasbim.core.walls.wall import read_state  # evita import circular

    for other in connections.neighbors(wall):
        try:
            other_tilt = read_state(doc, other)["tilt"]
        except OpError:
            continue
        if abs(other_tilt - tilt) > 1e-6:
            log.warning("paredes %s e %s unidas com inclinações diferentes: o topo não "
                        "fica casado", wall.GlobalId, other.GlobalId)


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
