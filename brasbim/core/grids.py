# SPDX-License-Identifier: LGPL-3.0-or-later
"""Eixos de projeto (``IfcGrid``), ``spec/ui/20-eixos-vaos-claraboia.md`` §2.

Operações: ``grid.create`` / ``grid.delete`` (data: estado completo) e ``grid.edit``
(before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": "Eixos", "origin": [0.0, 0.0], "angle": 0.0,
     "u": [{"tag": "1", "offset": 0.0}, {"tag": "2", "offset": 5.0}],
     "v": [{"tag": "A", "offset": 0.0}, {"tag": "B", "offset": 4.0}],
     "extent": 1.5, "bubbles": "both"}

``u``: eixos paralelos ao y do eixo, afastados em x; ``v``: paralelos ao x, afastados em
y. ``extent``: quanto a linha passa do primeiro e do último eixo cruzado. O ``IfcGrid``
fica na edificação (todos os pavimentos).
"""

from __future__ import annotations

import copy
import itertools
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props, storeys
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Eixos"
STATE_KEYS = ("name", "origin", "angle", "u", "v", "extent", "bubbles")
BUBBLES = ("both", "start", "end", "none")
BUBBLE_MM = 8.0  # diâmetro do círculo no papel
TEXT_MM = 3.5
WEIGHT = 0.13


def default_state() -> dict:
    return {"name": "Eixos", "origin": [0.0, 0.0], "angle": 0.0, "u": [], "v": [],
            "extent": 1.5, "bubbles": "both"}


def letters(n: int) -> str:
    """0 → A, 25 → Z, 26 → AA."""
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(ord("A") + r) + out
    return out


def axes_from_spacings(spacings: list[float], first: str = "1") -> list[dict]:
    """Eixos a partir dos espaçamentos ("5; 4; 4" → 4 eixos), com nomes seguidos: números
    a partir de ``first`` se for número; letras a partir de ``first`` se for letra."""
    offsets = [0.0]
    for s in spacings:
        if s <= 0:
            raise OpError("os espaçamentos dos eixos devem ser positivos")
        offsets.append(offsets[-1] + float(s))
    out = []
    for i, off in enumerate(offsets):
        if first.isdigit():
            tag = str(int(first) + i)
        else:
            start = 0
            for ch in first.upper():
                start = start * 26 + (ord(ch) - ord("A") + 1)
            tag = letters(start - 1 + i)
        out.append({"tag": tag, "offset": off})
    return out


def spacings(axes: list[dict]) -> list[float]:
    offs = [a["offset"] for a in axes]
    return [b - a for a, b in itertools.pairwise(offs)]


def all_grids(doc: Document) -> list:
    return sorted(doc.ifc.by_type("IfcGrid"), key=lambda g: g.GlobalId)


def read_state(grid) -> dict:
    values = ifcopenshell.util.element.get_pset(grid, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"eixos {grid.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


def validate(state: dict) -> None:
    if not state["u"] or not state["v"]:
        raise OpError("os eixos precisam de pelo menos um eixo em cada direção")
    if state["bubbles"] not in BUBBLES:
        raise OpError(f"pontas inválidas: {state['bubbles']!r}")
    for key in ("u", "v"):
        tags = [a["tag"] for a in state[key]]
        if len(set(tags)) != len(tags) or not all(str(t).strip() for t in tags):
            raise OpError("os eixos precisam de nomes diferentes")
    if state["extent"] < 0:
        raise OpError("o prolongamento dos eixos não pode ser negativo")


# --- geometria ----------------------------------------------------------------------------


def lines(state: dict) -> list[tuple[str, str, tuple, tuple]]:
    """(direção u/v, nome, início, fim) de cada eixo, em coordenadas do pavimento."""
    us = [a["offset"] for a in state["u"]]
    vs = [a["offset"] for a in state["v"]]
    e = state["extent"]
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    ox, oy = state["origin"]

    def to_plan(x, y):
        return (ox + c * x - s * y, oy + s * x + c * y)

    out = []
    for ax in state["u"]:
        out.append(("u", ax["tag"], to_plan(ax["offset"], min(vs) - e),
                    to_plan(ax["offset"], max(vs) + e)))
    for ax in state["v"]:
        out.append(("v", ax["tag"], to_plan(min(us) - e, ax["offset"]),
                    to_plan(max(us) + e, ax["offset"])))
    return out


def intersections(state: dict) -> list[tuple[float, float]]:
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    ox, oy = state["origin"]
    return [(ox + c * u["offset"] - s * v["offset"], oy + s * u["offset"] + c * v["offset"])
            for u in state["u"] for v in state["v"]]


def prims(state: dict, storey):
    """Desenho na planta: traço e ponto, círculo e nome nas pontas."""
    from brasbim.core.annotations.prims import Prims, Stroke, Text

    k = storeys.paper(storey, 1.0)
    r = BUBBLE_MM * k / 2
    out = Prims()
    for _, tag, p0, p1 in lines(state):
        d = (p1[0] - p0[0], p1[1] - p0[1])
        n = math.hypot(*d) or 1.0
        d = (d[0] / n, d[1] / n)
        out.strokes.append(Stroke((p0, p1), False, WEIGHT, "dashdot"))
        ends = {"both": (p0, p1), "start": (p0,), "end": (p1,), "none": ()}[state["bubbles"]]
        for end in ends:
            sign = -1.0 if end is p0 else 1.0
            c = (end[0] + d[0] * r * sign, end[1] + d[1] * r * sign)
            ring = tuple((c[0] + r * math.cos(2 * math.pi * i / 32),
                          c[1] + r * math.sin(2 * math.pi * i / 32)) for i in range(32))
            out.strokes.append(Stroke(ring, True, 0.18))
            out.texts.append(Text(c, str(tag), TEXT_MM * k, 0.0, "center", "middle"))
    return out


# --- gravação -------------------------------------------------------------------------------


def _axis(ifc, tag: str, local0, local1):
    curve = ifc.createIfcPolyline([ifc.createIfcCartesianPoint(tuple(map(float, local0))),
                                   ifc.createIfcCartesianPoint(tuple(map(float, local1)))])
    return ifc.createIfcGridAxis(str(tag), curve, True)


def _clear(doc: Document, grid) -> None:
    keep = set(doc.ifc.by_type("IfcGeometricRepresentationContext"))
    shape = grid.Representation
    grid.Representation = None
    old = list(grid.UAxes or []) + list(grid.VAxes or []) + list(grid.WAxes or [])
    if shape is not None:
        ifcopenshell.util.element.remove_deep2(doc.ifc, shape, do_not_delete=keep)
    for axis in old:
        if axis.id():
            curve = axis.AxisCurve
            doc.ifc.remove(axis)
            if curve is not None and curve.id() and not doc.ifc.get_total_inverses(curve):
                ifcopenshell.util.element.remove_deep2(doc.ifc, curve)


def write(doc: Document, grid, state: dict) -> None:
    state = {**default_state(), **state}
    validate(state)
    ifc = doc.ifc
    building = doc.building
    grid.Name = state["name"]
    if ifcopenshell.util.element.get_container(grid) != building:
        rel = ifcopenshell.api.spatial.assign_container(ifc, products=[grid],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    a = math.radians(state["angle"])
    direction = (math.cos(a), math.sin(a))
    if grid.ObjectPlacement is None:
        grid.ObjectPlacement = local_placement(ifc, building.ObjectPlacement, 0.0,
                                               state["origin"], direction)
    else:
        old = grid.ObjectPlacement.RelativePlacement
        grid.ObjectPlacement.PlacementRelTo = building.ObjectPlacement
        grid.ObjectPlacement.RelativePlacement = axis_placement(ifc, state["origin"], 0.0,
                                                                direction)
        ifcopenshell.util.element.remove_deep2(ifc, old)
    _clear(doc, grid)
    us = [x["offset"] for x in state["u"]]
    vs = [x["offset"] for x in state["v"]]
    e = state["extent"]
    u_axes = [_axis(ifc, x["tag"], (x["offset"], min(vs) - e), (x["offset"], max(vs) + e))
              for x in state["u"]]
    v_axes = [_axis(ifc, x["tag"], (min(us) - e, x["offset"]), (max(us) + e, x["offset"]))
              for x in state["v"]]
    grid.UAxes, grid.VAxes = u_axes, v_axes
    curves = [axis.AxisCurve for axis in (*u_axes, *v_axes)]
    rep = ifc.createIfcShapeRepresentation(doc.footprint_context, "FootPrint",
                                           "GeometricCurveSet",
                                           [ifc.createIfcGeometricCurveSet(curves)])
    grid.Representation = ifc.createIfcProductDefinitionShape(None, None, [rep])
    props.write_pset(doc, grid, PSET, {"Parametros": ifc.createIfcText(json.dumps(
        {k: state[k] for k in STATE_KEYS}, ensure_ascii=False, sort_keys=True))})
    doc.changed.add(grid.GlobalId)


def remove(doc: Document, grid) -> None:
    _clear(doc, grid)
    ifcopenshell.api.root.remove_product(doc.ifc, product=grid)


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    grid = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcGrid")
    grid.GlobalId = op.id
    try:
        write(doc, grid, copy.deepcopy(op.data))
    except Exception:
        remove(doc, grid)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcGrid"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    grid = doc.get(op.id, "IfcGrid")
    state = read_state(grid)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"grid.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    write(doc, grid, state)
    return {op.id}


register_inverse_pair("grid.create", _create, "grid.delete", _delete)
register("grid.edit", _edit, invert_swap)


# --- comandos ------------------------------------------------------------------------------


def create_grid(doc: Document, origin, angle: float, u_spacings, v_spacings,
                first_number: str = "1", first_letter: str = "A", **options):
    from brasbim.core.ops import Transaction

    state = {**default_state(), "origin": [float(origin[0]), float(origin[1])],
             "angle": float(angle), "u": axes_from_spacings(list(u_spacings), first_number),
             "v": axes_from_spacings(list(v_spacings), first_letter), **options}
    validate(state)
    return Transaction("Criar eixos", [Op("grid.create", guid.new(), data=state)])


def edit_grid(doc: Document, grid, **changes):
    from brasbim.core.ops import Transaction

    grid = doc.get(grid if isinstance(grid, str) else grid.GlobalId, "IfcGrid")
    state = read_state(grid)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    unknown = set(after) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    validate({**state, **after})
    if not after:
        return Transaction("Editar eixos", [])
    return Transaction("Editar eixos", [Op("grid.edit", grid.GlobalId,
                                           before={k: copy.deepcopy(state[k]) for k in after},
                                           after=after)])


def delete_ops(doc: Document, grid) -> list[Op]:
    return [Op("grid.delete", grid.GlobalId, data=read_state(grid))]


def mapped(state: dict, fn, turn: float = 0.0, mirror_axis: float | None = None) -> dict:
    """Eixos levados por uma transformação da planta: mover (``fn``), girar (``turn``
    graus) ou espelhar pelo eixo de ``mirror_axis`` graus (o x local troca de sentido)."""
    origin = fn(tuple(state["origin"]))
    out = {"origin": [float(origin[0]), float(origin[1])]}
    if mirror_axis is None:
        out["angle"] = (state["angle"] + turn) % 360.0
    else:
        out["angle"] = (2 * mirror_axis - state["angle"] - 180.0) % 360.0
        out["u"] = [{**a, "offset": -a["offset"]} for a in state["u"]]
    return out
