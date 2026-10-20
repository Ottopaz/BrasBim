# SPDX-License-Identifier: LGPL-3.0-or-later
"""Terreno por pontos com cota (``IfcGeographicElement`` ``TERRAIN``),
``spec/elementos/escada-terreno.md`` §4.

Operações: ``terrain.create`` / ``terrain.delete`` (data: estado completo) e
``terrain.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": "Terreno", "points": [[x, y, z], ...], "interval": 1.0}

Cotas absolutas (as dos pavimentos). O corpo é a triangulação de Delaunay
(Bowyer–Watson, CG) num ``IfcTriangulatedFaceSet``; o terreno fica no sítio. As curvas de
nível saem das arestas dos triângulos a cada ``interval``.
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, materials, props, storeys
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Terreno"
STATE_KEYS = ("name", "points", "interval")
MATERIAL = "Terra"


def default_state() -> dict:
    return {"name": "Terreno", "points": [], "interval": 1.0}


def is_terrain(entity) -> bool:
    return entity is not None and entity.is_a("IfcGeographicElement") and bool(
        ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False))


def all_terrains(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcGeographicElement") if is_terrain(e)),
                  key=lambda e: e.GlobalId)


def read_state(element) -> dict:
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"terreno {element.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


# --- triangulação ----------------------------------------------------------------------------


def _circumcircle(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-12:
        return None
    ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1])
          + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
    uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0])
          + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
    return (ux, uy), (ux - a[0]) ** 2 + (uy - a[1]) ** 2


def delaunay(points) -> list[tuple[int, int, int]]:
    """Triângulos (índices, anti-horário) da triangulação de Delaunay (Bowyer–Watson)."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if len(pts) < 3:
        return []
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * 20
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    work = pts + [(cx - span, cy - span), (cx + span, cy - span), (cx, cy + span)]
    n = len(pts)
    tris = [(n, n + 1, n + 2)]
    for i, p in enumerate(pts):
        bad = []
        for t in tris:
            cc = _circumcircle(work[t[0]], work[t[1]], work[t[2]])
            if cc is not None and (p[0] - cc[0][0]) ** 2 + (p[1] - cc[0][1]) ** 2 < cc[1] - 1e-12:
                bad.append(t)
        edges = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                key = tuple(sorted(e))
                edges[key] = edges.get(key, 0) + 1
        tris = [t for t in tris if t not in bad]
        for (a, b), count in edges.items():
            if count == 1:
                tris.append((a, b, i))
    out = []
    for t in tris:
        if max(t) >= n:
            continue
        a, b, c = (work[k] for k in t)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-12:
            continue
        out.append(t if area > 0 else (t[0], t[2], t[1]))
    return sorted(out)


def hull(points) -> list[tuple[float, float]]:
    from brasbim.core import geom2d

    return geom2d.convex_hull([(float(p[0]), float(p[1])) for p in points])


def contours(state: dict) -> list[tuple[float, list[tuple[tuple, tuple]]]]:
    """(cota, segmentos) das curvas de nível a cada ``interval``."""
    pts = state["points"]
    tris = delaunay(pts)
    if not tris:
        return []
    zs = [p[2] for p in pts]
    step = float(state["interval"])
    first = math.ceil(min(zs) / step - 1e-9) * step
    levels = []
    z = first
    while z <= max(zs) + 1e-9 and len(levels) < 400:
        levels.append(round(z, 6))
        z += step
    out = []
    for level in levels:
        segs = []
        for t in tris:
            cut = []
            for i, j in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                a, b = pts[i], pts[j]
                if (a[2] - level) * (b[2] - level) < 0 or (
                        abs(a[2] - level) < 1e-9 and abs(b[2] - level) > 1e-9):
                    k = (level - a[2]) / (b[2] - a[2])
                    cut.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            if len(cut) >= 2:
                segs.append((cut[0], cut[1]))
        if segs:
            out.append((level, segs))
    return out


def height_at(state: dict, p) -> float | None:
    """Cota do terreno no ponto (interpolação no triângulo), ou None fora dele."""
    pts = state["points"]
    for t in delaunay(pts):
        a, b, c = (pts[k] for k in t)
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / det
        l2 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / det
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-9:
            return l1 * a[2] + l2 * b[2] + l3 * c[2]
    return None


# --- gravação ------------------------------------------------------------------------------


def validate(state: dict) -> None:
    pts = state["points"]
    if len(pts) < 3 or any(len(p) != 3 for p in pts):
        raise OpError("o terreno precisa de pelo menos 3 pontos com cota (x, y, z)")
    if not delaunay(pts):
        raise OpError("os pontos do terreno estão alinhados")
    if state["interval"] <= 0:
        raise OpError("o intervalo das curvas de nível deve ser positivo")


def site(doc: Document):
    found = doc.ifc.by_type("IfcSite")
    if not found:
        raise OpError("o projeto não tem sítio")
    return found[0]


def write(doc: Document, element, state: dict) -> None:
    from brasbim.core.walls.types import material_named

    state = {**default_state(), **state}
    validate(state)
    ifc = doc.ifc
    s = site(doc)
    element.Name = state["name"]
    element.PredefinedType = "TERRAIN"
    if ifcopenshell.util.element.get_container(element) != s:
        rel = ifcopenshell.api.spatial.assign_container(ifc, products=[element],
                                                        relating_structure=s)
        guid.stamp(rel, s.GlobalId, "contains")
    if element.ObjectPlacement is None:
        element.ObjectPlacement = local_placement(ifc, s.ObjectPlacement)
    pts = state["points"]
    tris = delaunay(pts)
    coords = ifc.createIfcCartesianPointList3D([tuple(float(c) for c in p) for p in pts])
    faces = ifc.createIfcTriangulatedFaceSet(coords, None, False,
                                             [tuple(k + 1 for k in t) for t in tris], None)
    rep_old = props.representation(element, "Body")
    for item in (rep_old.Items if rep_old is not None else []) or []:
        for styled in [i for i in ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            ifc.remove(styled)
    material_named(doc, MATERIAL)
    materials.ensure_style(doc, MATERIAL)
    style = materials.surface_style(doc, MATERIAL)
    if style is not None:
        ifc.createIfcStyledItem(faces, [style], None)
    props.replace_representation(doc, element, "Body", ifc.createIfcShapeRepresentation(
        doc.body_context, "Body", "Tessellation", [faces]))
    props.write_pset(doc, element, PSET, {"Parametros": ifc.createIfcText(json.dumps(
        {k: state[k] for k in STATE_KEYS}, ensure_ascii=False, sort_keys=True))})
    doc.changed.add(element.GlobalId)


def remove(doc: Document, element) -> None:
    from brasbim.core import fragment

    rep = props.representation(element, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)
    shape = element.Representation
    element.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=element)
    if shape is not None:
        fragment.remove(doc.ifc, shape)


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    element = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcGeographicElement")
    element.GlobalId = op.id
    try:
        write(doc, element, copy.deepcopy(op.data))
    except Exception:
        remove(doc, element)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcGeographicElement"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    element = doc.get(op.id, "IfcGeographicElement")
    state = read_state(element)
    check_before(op, state)
    state.update(copy.deepcopy(op.after or {}))
    write(doc, element, state)
    return {op.id}


register_inverse_pair("terrain.create", _create, "terrain.delete", _delete)
register("terrain.edit", _edit, invert_swap)


# --- planta -------------------------------------------------------------------------------------


def plan_prims(state: dict, storey):
    """Contorno e curvas de nível (a cada cinco, mais grossa e com a cota)."""
    from brasbim.core.annotations.prims import Prims, Stroke, Text

    k = storeys.paper(storey, 1.0)
    out = Prims(strokes=[Stroke(tuple(hull(state["points"])), True, 0.18, "dashed")])
    step = float(state["interval"])
    for level, segs in contours(state):
        major = abs(level / (5 * step) - round(level / (5 * step))) < 1e-6
        for a, b in segs:
            out.strokes.append(Stroke((a, b), False, 0.25 if major else 0.13))
        if major and segs:
            a, b = max(segs, key=lambda s: math.dist(*s))
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            out.texts.append(Text(mid, f"{level:.2f}".replace(".", ","), 2.0 * k,
                                  0.0, "center", "bottom"))
    return out


# --- comandos -----------------------------------------------------------------------------------


def create_terrain(doc: Document, points, interval: float = 1.0, name: str = "Terreno"):
    from brasbim.core.ops import Transaction

    state = {"name": name, "points": [[float(c) for c in p] for p in points],
             "interval": float(interval)}
    validate(state)
    return Transaction("Criar terreno", [Op("terrain.create", guid.new(), data=state)])


def edit_terrain(doc: Document, element, **changes):
    from brasbim.core.ops import Transaction

    element = doc.get(element if isinstance(element, str) else element.GlobalId)
    state = read_state(element)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    validate({**state, **after})
    if not after:
        return Transaction("Editar terreno", [])
    return Transaction("Editar terreno", [Op(
        "terrain.edit", element.GlobalId, before={k: copy.deepcopy(state[k]) for k in after},
        after=after)])


def delete_ops(doc: Document, element) -> list[Op]:
    return [Op("terrain.delete", element.GlobalId, data=read_state(element))]


def mapped(state: dict, fn) -> dict:
    return {"points": [[*fn((p[0], p[1])), p[2]] for p in state["points"]]}
