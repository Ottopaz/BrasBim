# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de laje (``IfcSlab``), ``laje.md`` §2.2, §3.1 e §5.2.

Operações: ``slab.create`` / ``slab.delete`` (data: estado completo) e ``slab.edit``
(before/after: campos de ``STATE_KEYS`` alterados).

Estado::

    {"name": None, "type": "<GlobalId do IfcSlabType>", "storey": "<GlobalId>",
     "outline": [[0, 0], [5, 0], [5, 4], [0, 4]], "top_offset": 0.0, "common": {},
     "foreign": None, "placement": None}

O contorno é gravado anti-horário, sem pontos repetidos nem alinhados (``clean``).
Posicionamento: origem no primeiro vértice, z = face superior; o sólido desce a espessura
do tipo a partir dela. O contorno é lido do perfil do corpo (é o estado); o corpo é
regravado por ``rebuild`` quando a espessura do tipo muda.
"""

from __future__ import annotations

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import clip, geom2d, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common
from brasbim.core.structure import types as st_types

PSET = "BrasBim_Laje"
COMMON_PSET = "Pset_SlabCommon"
MIN_AREA = 0.0001  # m² (laje.md §3.1)
_TOL = 1e-6
STATE_KEYS = ("name", "type", "storey", "outline", "top_offset", "common", "foreign",
              "placement")


def default_state() -> dict:
    return {"name": None, "top_offset": 0.0, "common": {}, "foreign": None,
            "placement": None}


def is_parametric(slab) -> bool:
    return bool(ifcopenshell.util.element.get_pset(slab, PSET, should_inherit=False))


# --- contorno ----------------------------------------------------------------------------


def _segments_cross(p, q, r, s) -> bool:
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = side(r, s, p), side(r, s, q)
    d3, d4 = side(p, q, r), side(p, q, s)
    return d1 * d2 < -_TOL * _TOL and d3 * d4 < -_TOL * _TOL


def self_intersects(points) -> bool:
    n = len(points)
    edges = [(points[i], points[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _segments_cross(*edges[i], *edges[j]):
                return True
    return False


def clean(points) -> list[list[float]]:
    """Contorno sem pontos repetidos nem alinhados, anti-horário (laje.md §3.1). Recusa
    contorno com menos de 3 pontos, que se cruza ou de área nula."""
    pts = [(float(x), float(y)) for x, y in points]
    out: list[tuple[float, float]] = []
    for p in pts:
        if not out or geom2d._dist(out[-1], p) > _TOL:
            out.append(p)
    if len(out) > 1 and geom2d._dist(out[0], out[-1]) <= _TOL:
        out.pop()
    changed = True
    while changed and len(out) >= 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if abs(geom2d._cross(geom2d._sub(b, a), geom2d._sub(c, b))) <= _TOL * _TOL \
                    and (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) >= 0:
                out.pop(i)
                changed = True
                break
    if len(out) < 3:
        raise OpError("o contorno da laje precisa de pelo menos 3 pontos")
    if self_intersects(out):
        raise OpError("o contorno da laje se cruza")
    signed = clip.signed_area(out)
    if abs(signed) <= MIN_AREA:
        raise OpError("o contorno da laje não tem área")
    if signed < 0:
        out.reverse()
    return [[x, y] for x, y in out]


def area(outline) -> float:
    return geom2d.polygon_area([tuple(p) for p in outline])


def perimeter(outline) -> float:
    n = len(outline)
    return sum(geom2d._dist(outline[i], outline[(i + 1) % n]) for i in range(n))


def rectangle_sides(outline) -> tuple[float, float] | None:
    """(lado maior, lado menor) se o contorno é um retângulo; senão ``None``."""
    if len(outline) != 4:
        return None
    sides = [geom2d._dist(outline[i], outline[(i + 1) % 4]) for i in range(4)]
    a, b = outline[0], outline[2]
    c, d = outline[1], outline[3]
    if abs(sides[0] - sides[2]) > _TOL or abs(sides[1] - sides[3]) > _TOL \
            or abs(geom2d._dist(a, b) - geom2d._dist(c, d)) > _TOL:
        return None
    return max(sides[0], sides[1]), min(sides[0], sides[1])


# --- leitura -----------------------------------------------------------------------------


def _read_outline(slab, placement: dict) -> list[list[float]] | None:
    body = props.representation(slab, "Body")
    if body is None or not body.Items:
        return None
    item = body.Items[0]
    while item.is_a("IfcBooleanResult"):  # recortes (spec/ui 12 §2.3)
        item = item.FirstOperand
    if not item.is_a("IfcExtrudedAreaSolid"):
        return None
    area_ = item.SweptArea
    if not area_.is_a("IfcArbitraryClosedProfileDef") or not area_.OuterCurve.is_a(
            "IfcPolyline"):
        return None
    ox, oy, _ = placement["location"]
    pts = [p.Coordinates for p in area_.OuterCurve.Points]
    if len(pts) > 1 and geom2d._dist(pts[0][:2], pts[-1][:2]) <= _TOL:
        pts = pts[:-1]
    return [[ox + p[0], oy + p[1]] for p in pts]


def read_state(doc: Document, slab) -> dict:
    state = default_state()
    slab_type = ifcopenshell.util.element.get_type(slab)
    container = ifcopenshell.util.element.get_container(slab)
    state.update(name=slab.Name, type=slab_type.GlobalId if slab_type else None,
                 storey=container.GlobalId if container else None)
    placement = common.read_placement(slab)
    values = ifcopenshell.util.element.get_pset(slab, PSET, should_inherit=False)
    foreign = not values
    if foreign:
        state["foreign"] = common.read_foreign(slab)
        state["placement"] = placement
    else:
        state["outline"] = _read_outline(slab, placement)
        state["top_offset"] = float(values.get("DeslocamentoTopo") or 0.0)
    state["common"] = common.read_common(slab, COMMON_PSET, slab_type, foreign)
    return state


def thickness(doc: Document, state: dict) -> float:
    return st_types.slab_thickness(doc.get(state["type"], "IfcSlabType"))


# --- gravação ----------------------------------------------------------------------------


def _place(doc: Document, slab, storey, origin, z: float) -> None:
    placement = slab.ObjectPlacement
    if placement is None:
        slab.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement, z, origin)
        return
    old = placement.RelativePlacement
    placement.PlacementRelTo = storey.ObjectPlacement
    placement.RelativePlacement = axis_placement(doc.ifc, origin, z, (1.0, 0.0))
    ifcopenshell.util.element.remove_deep2(doc.ifc, old)


def solid(doc: Document, outline, depth: float):
    """Contorno extrudado para cima a partir de z = −espessura (topo em z = 0)."""
    ifc = doc.ifc
    ox, oy = outline[0]
    pts = [ifc.createIfcCartesianPoint((float(x - ox), float(y - oy))) for x, y in outline]
    curve = ifc.createIfcPolyline([*pts, pts[0]])
    profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None, curve)
    return ifc.createIfcExtrudedAreaSolid(
        profile,
        ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, -float(depth))),
                                      None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), float(depth))


def set_body(doc: Document, slab, outline, depth: float, body=None) -> None:
    """Corpo da laje; ``body`` é o sólido já recortado (spec/ui 12 §2.3), se houver."""
    item = body if body is not None else solid(doc, outline, depth)
    kind = "Clipping" if item.is_a("IfcBooleanClippingResult") else "SweptSolid"
    rep = doc.ifc.createIfcShapeRepresentation(doc.body_context, "Body", kind, [item])
    props.replace_representation(doc, slab, "Body", rep)


def _assign_material(doc: Document, slab, slab_type) -> None:
    lset = st_types.layer_set(slab_type)
    usage = ifcopenshell.util.element.get_material(slab, should_inherit=False)
    if usage is None or not usage.is_a("IfcMaterialLayerSetUsage") \
            or usage.ForLayerSet != lset:
        if usage is not None:
            ifcopenshell.api.material.unassign_material(doc.ifc, products=[slab])
        ifcopenshell.api.material.assign_material(
            doc.ifc, products=[slab], type="IfcMaterialLayerSetUsage", material=lset)
        usage = ifcopenshell.util.element.get_material(slab, should_inherit=False)
    common.stamp_material(slab)
    usage.LayerSetDirection = "AXIS3"
    usage.DirectionSense = "POSITIVE"
    usage.OffsetFromReferenceLine = 0.0


def write_state(doc: Document, slab, state: dict) -> None:
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    slab_type = doc.find(state["type"]) if state["type"] else None
    slab.Name = state["name"]
    if slab_type is not None:
        common.assign_type(doc, slab, slab_type)
    common.assign_container(doc, slab, storey)
    foreign = state["foreign"] is not None
    if foreign:
        common.write_foreign(doc, slab, state)
    else:
        outline = clean(state["outline"])
        _assign_material(doc, slab, slab_type)
        _place(doc, slab, storey, outline[0], float(state["top_offset"]))
        set_body(doc, slab, outline, st_types.slab_thickness(slab_type))
        props.write_pset(doc, slab, PSET, {
            "DeslocamentoTopo": doc.ifc.createIfcLengthMeasure(float(state["top_offset"]))})
    common.write_common(doc, slab, COMMON_PSET, slab_type, state["common"], foreign)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    slab = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcSlab")
    slab.GlobalId = op.id
    try:
        write_state(doc, slab, {**default_state(), **op.data})
    except Exception:
        common.remove(doc, slab)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    common.remove(doc, doc.get(op.id, "IfcSlab"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    slab = doc.get(op.id, "IfcSlab")
    state = read_state(doc, slab)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"slab.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write_state(doc, slab, state)
    return {op.id}


register_inverse_pair("slab.create", _create, "slab.delete", _delete)
register("slab.edit", _edit, invert_swap)
