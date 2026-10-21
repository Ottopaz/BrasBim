# SPDX-License-Identifier: LGPL-3.0-or-later
"""Terreno (``IfcGeographicElement`` ``TERRAIN``), ``spec/elementos/escada-terreno.md`` §4:
por contorno, curvas de nível e pontos com cota.

Operações: ``terrain.create`` / ``terrain.delete`` (data: estado completo) e
``terrain.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"name": "Terreno", "points": [[x, y, z], ...], "interval": 1.0,
     "boundary": [[x, y], ...] | None, "boundary_z": 100.0 | None,
     "curves": [{"points": [[x, y], ...], "closed": false, "z": 101.0 | None}, ...]}

Cotas absolutas (as dos pavimentos). Curva sem cota ainda não entra na superfície.
Contorno sem cota: a de cada ponto vem das curvas e pontos vizinhos. A superfície é a
triangulação de Delaunay das amostras (GEOS, pelo shapely) recortada pelo contorno, num
``IfcTriangulatedFaceSet``; o terreno fica no sítio. As curvas de nível finas saem das
arestas dos triângulos a cada ``interval``.
"""

from __future__ import annotations

import copy
import itertools
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element
import numpy as np
import shapely

from brasbim.core import guid, materials, props, storeys
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Terreno"
STATE_KEYS = ("name", "points", "interval", "boundary", "boundary_z", "curves")
MATERIAL = "Terra"
DENSIFY = 1.0  # m: distância máxima entre amostras ao longo das curvas e do contorno
FLAT_AREA = 0.05  # m²: patamar menor que isso (lasca ao longo da curva) fica
FLAT_PASSES = 4


def default_state() -> dict:
    return {"name": "Terreno", "points": [], "interval": 1.0, "boundary": None,
            "boundary_z": None, "curves": []}


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


# --- superfície (escada-terreno.md §4.2) -------------------------------------------------------


def densify(points, closed: bool, step: float = DENSIFY) -> list[tuple[float, float]]:
    """Pontos da linha com no máximo ``step`` entre um e outro."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    if closed and len(pts) > 2:
        pts = [*pts, pts[0]]
    out = [pts[0]] if pts else []
    for a, b in itertools.pairwise(pts):
        n = max(1, math.ceil(math.dist(a, b) / step - 1e-9))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                for k in range(1, n + 1)]
    if closed and len(out) > 1:
        out.pop()  # o fim é o começo
    return out


def _idw(xy: np.ndarray, z: np.ndarray, query: np.ndarray, k: int = 8) -> np.ndarray:
    """Cota nos pontos ``query`` pela média ponderada pelo inverso do quadrado da
    distância às ``k`` amostras mais próximas (CG)."""
    if not len(xy):
        return np.zeros(len(query))
    d2 = ((query[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2)
    k = min(k, len(xy))
    near = np.argpartition(d2, k - 1, axis=1)[:, :k]
    dn = np.take_along_axis(d2, near, axis=1)
    w = 1.0 / (dn + 1e-12)
    return (w * z[near]).sum(axis=1) / w.sum(axis=1)


def _samples(state: dict) -> list[tuple[float, float, float, int | None]]:
    """(x, y, z, curva de origem) das amostras: pontos cotados, curvas com cota
    (adensadas) e o contorno (cota dada ou calculada pelas outras amostras)."""
    out: list[tuple[float, float, float, int | None]] = []
    seen: set[tuple[float, float]] = set()

    def add(x, y, z, source):
        key = (round(x, 6), round(y, 6))
        if key not in seen:
            seen.add(key)
            out.append((float(x), float(y), float(z), source))

    region = (shapely.Polygon(state["boundary"]).buffer(1e-6) if state["boundary"]
              else None)

    def inside(x, y) -> bool:
        return region is None or bool(shapely.contains_xy(region, x, y))

    for p in state["points"]:
        if inside(p[0], p[1]):
            add(p[0], p[1], p[2], None)
    for i, curve in enumerate(state["curves"]):
        if curve["z"] is None:
            continue
        for q in densify(curve["points"], curve["closed"]):
            if inside(*q):
                add(q[0], q[1], curve["z"], i)
        if region is not None:  # onde a curva cruza o contorno, com a cota dela
            pts = [tuple(q) for q in curve["points"]]
            line = shapely.LinearRing(pts) if curve["closed"] else shapely.LineString(pts)
            cross = line.intersection(shapely.LinearRing(state["boundary"]))
            for q in shapely.get_coordinates(cross):
                add(q[0], q[1], curve["z"], i)
    if state["boundary"]:
        ring = densify(state["boundary"], True)
        if state["boundary_z"] is not None:
            zs = [float(state["boundary_z"])] * len(ring)
        else:
            known = np.array([(s[0], s[1]) for s in out]).reshape(-1, 2)
            zs = _idw(known, np.array([s[2] for s in out]), np.array(ring).reshape(-1, 2))
        for q, z in zip(ring, zs, strict=True):
            add(q[0], q[1], z, None)
    return out


def _triangulate(samples, boundary) -> list[tuple[int, int, int]]:
    """Delaunay das amostras (GEOS, pelo shapely), anti-horário, só dentro do contorno."""
    xy = [(s[0], s[1]) for s in samples]
    if len(xy) < 3:
        return []
    index = {(round(x, 6), round(y, 6)): i for i, (x, y) in enumerate(xy)}
    tris = []
    for poly in shapely.get_parts(shapely.delaunay_triangles(shapely.MultiPoint(xy))):
        ids = [index.get((round(x, 6), round(y, 6))) for x, y in poly.exterior.coords[:3]]
        if None in ids or len(set(ids)) < 3:
            continue
        a, b, c = (xy[i] for i in ids)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-10:
            continue
        tris.append(tuple(ids) if area > 0 else (ids[0], ids[2], ids[1]))
    if boundary and tris:
        region = shapely.Polygon(boundary).buffer(1e-6)
        cx = np.array([sum(xy[i][0] for i in t) / 3 for t in tris])
        cy = np.array([sum(xy[i][1] for i in t) / 3 for t in tris])
        inside = shapely.contains_xy(region, cx, cy)
        tris = [t for t, ok in zip(tris, inside, strict=True) if ok]
    return sorted(tris)


def _flat_fixes(samples, tris, curves) -> list[tuple[float, float, float, None]]:
    """Patamares falsos: triângulo com os três vértices na mesma curva ganha um ponto no
    meio. Com curvas vizinhas dos dois lados, a cota vem delas; só de um lado (bolsão de
    uma curva sinuosa), fica a meio caminho até elas. Dentro de uma curva fechada com as
    vizinhas todas de um lado (topo de morro, fundo de vale), o patamar é de verdade."""
    flats = [t for t in tris if samples[t[0]][3] is not None
             and samples[t[0]][3] == samples[t[1]][3] == samples[t[2]][3]
             and _area(samples, t) > FLAT_AREA]
    if not flats:
        return []
    xy = np.array([(s[0], s[1]) for s in samples])
    z = np.array([s[2] for s in samples])
    out = []
    for t in flats:
        level = samples[t[0]][2]
        c = xy[list(t)].mean(axis=0)
        other = np.abs(z - level) > 1e-6
        if not other.any():
            continue
        d2 = ((xy[other] - c) ** 2).sum(axis=1)
        near = np.argsort(d2)[:8]
        zs = z[other][near]
        value = float(_idw(xy[other], z[other], c.reshape(1, 2))[0])
        if (zs > level).all() or (zs < level).all():
            if curves[samples[t[0]][3]]["closed"]:
                continue
            value = (level + value) / 2
        out.append((float(c[0]), float(c[1]), value, None))
    return out


def _area(samples, t) -> float:
    a, b, c = (samples[i] for i in t)
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2


def surface(state: dict) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    """Vértices (x, y, z) e triângulos da superfície do terreno."""
    state = {**default_state(), **state}
    samples = _samples(state)
    tris = _triangulate(samples, state["boundary"])
    for _ in range(FLAT_PASSES):  # cada passada pode abrir patamares menores
        extra = _flat_fixes(samples, tris, state["curves"])
        if not extra:
            break
        samples = samples + extra
        tris = _triangulate(samples, state["boundary"])
    used = sorted({i for t in tris for i in t})
    renum = {old: new for new, old in enumerate(used)}
    verts = [samples[i][:3] for i in used]
    return verts, [tuple(renum[i] for i in t) for t in tris]


def delaunay(points) -> list[tuple[int, int, int]]:
    """Triângulos (índices, anti-horário) da triangulação de Delaunay dos pontos."""
    samples = [(float(p[0]), float(p[1]), 0.0, None) for p in points]
    return _triangulate(samples, None)


def hull(points) -> list[tuple[float, float]]:
    from brasbim.core import geom2d

    return geom2d.convex_hull([(float(p[0]), float(p[1])) for p in points])


def outline(state: dict) -> list[tuple[float, float]]:
    """Contorno desenhado, ou a envoltória dos pontos e das curvas."""
    state = {**default_state(), **state}
    if state["boundary"]:
        return [tuple(p) for p in state["boundary"]]
    pts = [p[:2] for p in state["points"]]
    pts += [q for c in state["curves"] if c["z"] is not None for q in c["points"]]
    return hull(pts) if len(pts) >= 3 else []


def contours(state: dict) -> list[tuple[float, list[tuple[tuple, tuple]]]]:
    """(cota, segmentos) das curvas de nível da superfície a cada ``interval``."""
    pts, tris = surface(state)
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
    pts, tris = surface(state)
    for t in tris:
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
    state = {**default_state(), **state}
    if any(len(p) != 3 for p in state["points"]):
        raise OpError("os pontos do terreno precisam de x, y e cota")
    for c in state["curves"]:
        if len(c["points"]) < (3 if c["closed"] else 2):
            raise OpError("curva de nível com pontos de menos")
    if state["boundary"] is not None and len(state["boundary"]) < 3:
        raise OpError("o contorno do terreno precisa de pelo menos 3 pontos")
    if state["interval"] <= 0:
        raise OpError("o intervalo das curvas de nível deve ser positivo")
    samples = _samples(state)
    if len(samples) < 3:
        raise OpError("o terreno precisa de um contorno ou de pelo menos 3 pontos com cota "
                      "(x, y, z)")
    if not _triangulate(samples, state["boundary"]):
        raise OpError("os pontos do terreno estão alinhados")


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
    pts, tris = surface(state)
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
    """Contorno, curvas desenhadas (tracejadas enquanto não têm cota) e as curvas finas da
    superfície (a cada cinco, mais grossa e com a cota)."""
    from brasbim.core.annotations.prims import Prims, Stroke, Text, readable

    state = {**default_state(), **state}
    k = storeys.paper(storey, 1.0)
    ring = outline(state)
    out = Prims()
    if len(ring) >= 3:
        out.strokes.append(Stroke(tuple(ring), True, 0.25 if state["boundary"] else 0.18,
                                  "solid" if state["boundary"] else "dashed"))
    drawn = set()
    for c in state["curves"]:
        pts = tuple(tuple(q) for q in c["points"])
        if c["z"] is None:
            out.strokes.append(Stroke(pts, c["closed"], 0.25, "dashed"))
        else:
            out.strokes.append(Stroke(pts, c["closed"], 0.25))
            drawn.add(round(float(c["z"]), 6))
    step = float(state["interval"])
    for level, segs in contours(state):
        if round(level, 6) in drawn:
            continue  # a curva desenhada já está lá
        major = abs(level / (5 * step) - round(level / (5 * step))) < 1e-6
        for a, b in segs:
            out.strokes.append(Stroke((a, b), False, 0.25 if major else 0.13))
        if major and segs:
            a, b = max(segs, key=lambda s: math.dist(*s))
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            out.texts.append(Text(mid, f"{level:.2f}".replace(".", ","), 2.0 * k,
                                  0.0, "center", "bottom"))
    for c in state["curves"]:  # cota de cada curva desenhada, no meio dela
        if c["z"] is not None and len(c["points"]) >= 2:
            pts = c["points"]
            i = len(pts) // 2
            a, b = pts[i - 1], pts[i]
            angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            out.texts.append(Text(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                                  f"{c['z']:.2f}".replace(".", ","), 2.0 * k,
                                  readable(angle), "center", "bottom"))
    return out


# --- comandos -----------------------------------------------------------------------------------


def _clean_curve(curve: dict) -> dict:
    return {"points": [[float(q[0]), float(q[1])] for q in curve["points"]],
            "closed": bool(curve.get("closed", False)),
            "z": None if curve.get("z") is None else float(curve["z"])}


def create_terrain(doc: Document, points=(), interval: float = 1.0, name: str = "Terreno",
                   boundary=None, boundary_z: float | None = None, curves=()):
    from brasbim.core.ops import Transaction

    state = {"name": name, "points": [[float(c) for c in p] for p in points],
             "interval": float(interval),
             "boundary": [[float(q[0]), float(q[1])] for q in boundary] if boundary else None,
             "boundary_z": None if boundary_z is None else float(boundary_z),
             "curves": [_clean_curve(c) for c in curves]}
    validate(state)
    return Transaction("Criar terreno", [Op("terrain.create", guid.new(), data=state)])


def edit_terrain(doc: Document, element, **changes):
    from brasbim.core.ops import Transaction

    element = doc.get(element if isinstance(element, str) else element.GlobalId)
    state = read_state(element)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    unknown = set(after) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    validate({**state, **after})
    if not after:
        return Transaction("Editar terreno", [])
    return Transaction("Editar terreno", [Op(
        "terrain.edit", element.GlobalId, before={k: copy.deepcopy(state[k]) for k in after},
        after=after)])


def add_curves(doc: Document, element, curves):
    """Põe linhas no terreno como curvas de nível (as repetidas ficam de fora)."""
    from brasbim.core.ops import Transaction

    element = doc.get(element if isinstance(element, str) else element.GlobalId)
    state = read_state(element)
    have = {json.dumps(c["points"]) for c in state["curves"]}
    new = []
    for c in curves:
        c = _clean_curve(c)
        key = json.dumps(c["points"])
        if key not in have:
            have.add(key)
            new.append(c)
    if not new:
        return Transaction("Pôr curvas no terreno", [])
    tx = edit_terrain(doc, element, curves=[*state["curves"], *new])
    return Transaction("Pôr curva no terreno" if len(new) == 1 else "Pôr curvas no terreno",
                       tx.ops)


def set_curve_level(doc: Document, element, index: int, z: float | None):
    from brasbim.core.ops import Transaction

    element = doc.get(element if isinstance(element, str) else element.GlobalId)
    curves = copy.deepcopy(read_state(element)["curves"])
    if not 0 <= index < len(curves):
        raise OpError("curva de nível inexistente")
    curves[index]["z"] = None if z is None else float(z)
    tx = edit_terrain(doc, element, curves=curves)
    return Transaction("Cota da curva de nível", tx.ops)


def remove_curve(doc: Document, element, index: int):
    from brasbim.core.ops import Transaction

    element = doc.get(element if isinstance(element, str) else element.GlobalId)
    curves = copy.deepcopy(read_state(element)["curves"])
    if not 0 <= index < len(curves):
        raise OpError("curva de nível inexistente")
    del curves[index]
    tx = edit_terrain(doc, element, curves=curves)
    return Transaction("Tirar curva do terreno", tx.ops)


def curve_near(state: dict, p, tol: float) -> int | None:
    """Índice da curva do terreno mais perto de ``p`` (dentro de ``tol``)."""
    from brasbim.core.annotations.reference import lines_near

    best = None
    for i, c in enumerate(state["curves"]):
        found = lines_near([("", {"lines": [c]})], p, tol)
        if found and (best is None or found[0][0] < best[0]):
            best = (found[0][0], i)
    return None if best is None else best[1]


def delete_ops(doc: Document, element) -> list[Op]:
    return [Op("terrain.delete", element.GlobalId, data=read_state(element))]


def mapped(state: dict, fn) -> dict:
    def m(q):
        r = fn((q[0], q[1]))
        return [float(r[0]), float(r[1])]

    out = {"points": [[*m(p), p[2]] for p in state["points"]],
           "curves": [{**c, "points": [m(q) for q in c["points"]]} for c in state["curves"]]}
    if state.get("boundary"):
        out["boundary"] = [m(q) for q in state["boundary"]]
    return out
