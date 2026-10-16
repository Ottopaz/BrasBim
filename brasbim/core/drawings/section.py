# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho de corte e de fachada a partir das malhas do modelo (spec/ui 14 §4–§5), sem Qt.

Sistema da vista: *u* ao longo de A→B, *v* = cota da edificação, *w* = profundidade para
o lado olhado. O que tem *w* < 0 (atrás de quem olha) não aparece.

1. Seção (só no corte): a interseção dos triângulos com o plano *w* = 0 dá os contornos
   cortados, preenchidos com o estilo de corte do material (parede por camadas, laje por
   camadas na altura) e com contorno grosso.
2. Vista: os triângulos com *w* ≥ 0 são preenchidos de branco e as arestas do sólido são
   traçadas, tudo do mais longe para o mais perto (algoritmo do pintor).
3. Linha de piso, cotas de nível dos pavimentos e título.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np

from brasbim.core import clip, materials
from brasbim.core.annotations.drafting import signed
from brasbim.core.annotations.prims import Text
from brasbim.core.document import Document, OpError
from brasbim.core.drawings import views

CLASSES = ("IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcDoor", "IfcWindow")
CUT_WEIGHT, VIEW_WEIGHT, OPENING_WEIGHT = 0.5, 0.18, 0.25  # mm (spec/ui 13 §8)
_EPS = 1e-6
_FAR = 1e4


@dataclass
class Item:
    """Peça do desenho, na ordem de pintura: ``face`` (preenchida de branco, sem traço),
    ``edge`` (traço), ``cut`` (região cortada com o estilo do material e contorno) e
    ``line`` (traço de anotação)."""

    kind: str
    points: tuple = ()
    rings: list = field(default_factory=list)
    owner: str | None = None
    fill: dict | None = None
    weight: float = VIEW_WEIGHT
    dash: str = "solid"


@dataclass
class Drawing:
    items: list[Item] = field(default_factory=list)
    texts: list[Text] = field(default_factory=list)

    def bounds(self):
        pts = [p for it in self.items for p in (it.points or [q for r in it.rings for q in r])]
        if not pts:
            return None
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        return min(us), min(vs), max(us), max(vs)

    def cuts(self, owner: str | None = None) -> list[Item]:
        return [it for it in self.items if it.kind == "cut"
                and (owner is None or it.owner == owner)]

    def pick(self, p) -> str | None:
        """Elemento sob o ponto: o de cima primeiro (cortes, depois o mais perto)."""
        for it in reversed(self.items):
            if it.owner is None or it.kind not in ("cut", "face"):
                continue
            rings = it.rings if it.kind == "cut" else [it.points]
            if any(len(r) >= 3 and _inside(r, p) for r in rings):
                return it.owner
        return None


def _inside(ring, p) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        (x0, y0), (x1, y1) = ring[i - 1], ring[i]
        if (y0 > p[1]) != (y1 > p[1]):
            x = x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0)
            if x > p[0]:
                inside = not inside
    return inside


# --- malhas no sistema da vista ----------------------------------------------------------


def _mesh(element, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
    except RuntimeError:
        return None
    g = shape.geometry
    verts = np.asarray(g.verts, dtype=float).reshape(-1, 3)
    faces = np.asarray(g.faces, dtype=np.int64).reshape(-1, 3)
    edges = np.asarray(g.edges, dtype=np.int64).reshape(-1, 2)
    return verts, faces, edges


def _to_view(verts, a, d, look):
    rel = verts[:, :2] - np.array(a)
    u = rel @ np.array(d)
    w = rel @ np.array(look)
    return np.c_[u, verts[:, 2], w]


def _clip_w(poly: list, lo: float, hi: float | None) -> list:
    """Polígono (u, v, w) cortado em ``lo ≤ w ≤ hi``."""
    def cut(points, value, keep_above):
        out = []
        for i, p in enumerate(points):
            q = points[(i + 1) % len(points)]
            p_in = p[2] >= value if keep_above else p[2] <= value
            q_in = q[2] >= value if keep_above else q[2] <= value
            if p_in:
                out.append(p)
            if p_in != q_in:
                t = (value - p[2]) / (q[2] - p[2])
                out.append(p + t * (q - p))
        return out

    poly = cut(poly, lo, True)
    if hi is not None and len(poly) >= 3:
        poly = cut(poly, hi, False)
    return poly


def _clip_segment(p, q, lo: float, hi: float | None):
    """Segmento (u, v, w) cortado em ``lo ≤ w ≤ hi``; ``None`` se não sobra nada."""
    t0, t1 = 0.0, 1.0
    dw = q[2] - p[2]
    for bound, keep_above in ((lo, True), (hi, False)):
        if bound is None:
            continue
        if abs(dw) < 1e-15:
            if (p[2] < bound) if keep_above else (p[2] > bound):
                return None
            continue
        t = (bound - p[2]) / dw
        if (dw > 0) == keep_above:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    if t1 - t0 < 1e-12:
        return None
    return p + t0 * (q - p), p + t1 * (q - p)


def _section_rings(uvw: np.ndarray, faces: np.ndarray) -> list:
    """Contornos da interseção do sólido com o plano w = 0, em (u, v)."""
    segments = []
    for tri in faces:
        p = uvw[tri]
        w = p[:, 2]
        if w.min() > 0 or w.max() < 0:
            continue
        crossing = []
        for i in range(3):
            a, b = p[i], p[(i + 1) % 3]
            if (a[2] < 0) != (b[2] < 0):
                t = -a[2] / (b[2] - a[2])
                q = a + t * (b - a)
                crossing.append((float(q[0]), float(q[1])))
        if len(crossing) == 2 and math.dist(*crossing) > _EPS:
            segments.append(tuple(crossing))
    return _chain(segments)


def _chain(segments) -> list:
    """Segmentos soltos → anéis fechados (pontas iguais a 1 µm)."""
    def key(p):
        return (round(p[0], 6), round(p[1], 6))

    nexts: dict = {}
    for a, b in segments:
        nexts.setdefault(key(a), []).append(b)
        nexts.setdefault(key(b), []).append(a)
    used: set = set()
    rings = []
    for a, b in segments:
        if (key(a), key(b)) in used:
            continue
        ring, prev, cur = [a], a, b
        used |= {(key(a), key(b)), (key(b), key(a))}
        while key(cur) != key(a) and len(ring) < 100000:
            ring.append(cur)
            options = [q for q in nexts.get(key(cur), []) if key(q) != key(prev)
                       and (key(cur), key(q)) not in used]
            if not options:
                break
            prev, cur = cur, options[0]
            used |= {(key(prev), key(cur)), (key(cur), key(prev))}
        if len(ring) >= 3:
            rings.append(ring)
    return clip.union(rings) if rings else []


# --- estilo do corte -----------------------------------------------------------------------


def _cut_fill(doc: Document, name: str | None) -> dict:
    return {**materials.style(doc, name)["cut"], "source": "material"}


def _material_name(element) -> str | None:
    material = ifcopenshell.util.element.get_material(element)
    if material is None:
        return None
    if material.is_a("IfcMaterialLayerSetUsage"):
        material = material.ForLayerSet
    if material.is_a("IfcMaterialProfileSetUsage"):
        material = material.ForProfileSet
    if material.is_a("IfcMaterialProfileSet"):
        profiles = [p for p in material.MaterialProfiles or [] if p.Material is not None]
        return profiles[0].Material.Name if profiles else None
    if material.is_a("IfcMaterialLayerSet"):
        layers = [la for la in material.MaterialLayers if la.Material is not None]
        return max(layers, key=lambda la: la.LayerThickness or 0).Material.Name if layers \
            else None
    return material.Name if material.is_a("IfcMaterial") else None


def _strip(u0, u1, v0=-_FAR, v1=_FAR):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def _wall_layers(doc: Document, wall, a, d) -> list[tuple[str | None, float, float]]:
    """(material, u0, u1) das camadas da parede ao longo da linha da vista."""
    from brasbim.core import layers

    storey = ifcopenshell.util.element.get_container(wall)
    if storey is None:
        return []
    from brasbim.core import geom2d
    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state

    walls, pieces = [], {}
    for other in ifcopenshell.util.element.get_decomposition(storey):
        if not other.is_a("IfcWall"):
            continue
        try:
            state = read_state(doc, other)
            band = rebuild.band(doc, state)
            segments = rebuild.profile(doc, other, band)
        except (OpError, ValueError):
            continue
        if state["top_profile"] or abs(state["tilt"] or 0.0) > 1e-9:
            continue
        walls.append(other)
        pieces[other.GlobalId] = [[band.frame.to_global(p) for p in geom2d.polygon(segments)]]
    found = []
    line = [[(a[0] - d[0] * _FAR, a[1] - d[1] * _FAR), (a[0] + d[0] * _FAR, a[1] + d[1] * _FAR)]]
    for region in layers.regions(doc, sorted(walls, key=lambda w: w.GlobalId), pieces):
        if region.owner != wall.GlobalId:
            continue
        for seg in clip.clip_lines(line, region.rings):
            us = [(p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1] for p in seg]
            found.append((region.material, min(us), max(us)))
    return found


def _slab_layers(doc: Document, slab) -> list[tuple[str | None, float, float]]:
    """(material, cota de baixo, cota de cima) das camadas da laje."""
    from brasbim.core.structure import slabs
    from brasbim.core.structure import types as st_types

    state = slabs.read_state(doc, slab)
    if state["foreign"] is not None:
        return []
    storey = doc.get(state["storey"])
    z = float(storey.Elevation or 0.0) + state["top_offset"] - slabs.thickness(doc, state)
    out = []
    for layer in st_types.layer_set(doc.get(state["type"])).MaterialLayers:
        t = float(layer.LayerThickness)
        out.append((layer.Material.Name if layer.Material else None, z, z + t))
        z += t
    return out


def _cut_items(doc: Document, element, rings: list, a, d) -> list[Item]:
    gid = element.GlobalId
    if element.is_a("IfcDoor") or element.is_a("IfcWindow"):
        return [Item("cut", rings=rings, owner=gid, fill={"pattern": "none", "source": "type"},
                     weight=OPENING_WEIGHT)]
    pieces: list[tuple[str | None, list]] = []
    if element.is_a("IfcWall"):
        for name, u0, u1 in _wall_layers(doc, element, a, d):
            part = clip.intersection(rings, [_strip(u0, u1)])
            if part:
                pieces.append((name, part))
    elif element.is_a("IfcSlab"):
        for name, z0, z1 in _slab_layers(doc, element):
            part = clip.intersection(rings, [_strip(-_FAR, _FAR, z0, z1)])
            if part:
                pieces.append((name, part))
    if not pieces:
        pieces = [(_material_name(element), rings)]
    out = [Item("cut", rings=part, owner=gid, fill=_cut_fill(doc, name), weight=0.0)
           for name, part in pieces]
    out.append(Item("cut", rings=rings, owner=gid, fill={"pattern": "none", "source": "type"},
                    weight=CUT_WEIGHT))  # o contorno por cima das camadas
    return out


# --- desenho ---------------------------------------------------------------------------------


def draw(doc: Document, view) -> Drawing:
    state = views.read_state(view)
    a, d, look = views.frame(state)
    section = state["kind"] == "section"
    depth = state["depth"]
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    painted: list[tuple[float, int, Item]] = []
    cut_items: list[Item] = []
    for cls in CLASSES:
        for element in sorted(doc.ifc.by_type(cls), key=lambda e: e.GlobalId):
            if element.Representation is None:
                continue
            mesh = _mesh(element, settings)
            if mesh is None:
                continue
            verts, faces, edges = mesh
            uvw = _to_view(verts, a, d, look)
            w = uvw[:, 2]
            if w.max() < 0 or (depth is not None and w.min() > depth):
                continue
            gid = element.GlobalId
            if section and w.min() < -_EPS and w.max() > _EPS:
                rings = _section_rings(uvw, faces)
                if rings:
                    cut_items += _cut_items(doc, element, rings, a, d)
            for tri in faces:
                poly = _clip_w(list(uvw[tri]), 0.0, depth)
                if len(poly) < 3:
                    continue
                pts = tuple((float(p[0]), float(p[1])) for p in poly)
                if abs(clip.signed_area(list(pts))) < 1e-10:
                    continue  # face de lado: só as arestas aparecem
                key = float(np.mean([p[2] for p in poly]))
                painted.append((key, 0, Item("face", pts, owner=gid)))
            for e in edges:
                ends = _clip_segment(uvw[e[0]], uvw[e[1]], 0.0, depth)
                if ends is None or np.linalg.norm(ends[0][:2] - ends[1][:2]) < _EPS:
                    continue
                key = float((ends[0][2] + ends[1][2]) / 2)
                painted.append((key, 1, Item("edge", ((float(ends[0][0]), float(ends[0][1])),
                                                      (float(ends[1][0]), float(ends[1][1]))),
                                             owner=gid, weight=VIEW_WEIGHT)))
    painted.sort(key=lambda t: (-t[0], t[1]))
    out = Drawing([it for _, _, it in painted] + cut_items)
    _annotate(doc, state, out)
    return out


def _annotate(doc: Document, state: dict, out: Drawing) -> None:
    """Linha de piso, cotas de nível dos pavimentos e título (spec/ui 14 §4–§5)."""
    box = out.bounds()
    if box is None:
        return
    umin, vmin, umax, vmax = box
    k = state["scale"] / 1000.0
    out.items.append(Item("line", ((umin - 5 * k, 0.0), (umax + 5 * k, 0.0)), weight=0.5))
    s = 3.0 * k
    x = umax + 10 * k
    for storey in doc.storeys():
        z = float(storey.Elevation or 0.0)
        if z < vmin - 1e-6 or z > vmax + 1e-6:
            continue
        top = z + s * 0.866
        out.items.append(Item("line", ((x, z), (x - s / 2, top), (x + s / 2, top), (x, z)),
                              weight=0.18))
        out.items.append(Item("line", ((x - s, top), (x + s * 9, top)), weight=0.18))
        out.texts.append(Text((x + s * 0.7, top + s * 0.15),
                              f"{signed(z)}  {storey.Name or ''}".strip(), 2.5 * k, 0.0,
                              "left", "bottom"))
    title = (f"CORTE {state['letter']}" if state["kind"] == "section" and state["letter"]
             else (state["name"] or "").upper())
    mid = (umin + umax) / 2
    out.texts.append(Text((mid, vmin - 14 * k), title, 5.0 * k, 0.0, "center", "bottom"))
    out.texts.append(Text((mid, vmin - 20 * k), f"ESC. 1:{state['scale']}", 3.0 * k, 0.0,
                          "center", "bottom"))
