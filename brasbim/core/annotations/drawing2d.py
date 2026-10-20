# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho 2D (``spec/ui/19-desenho-2d.md``): círculo, arco, curva livre, cota de raio,
cota de ângulo, rótulo e marcador de alteração.

São anotações como as da spec/ui 13 (``annotations.base``): estado em JSON no Pset
``BrasBim_Anotacao``, geometria refeita do estado. Tamanhos em mm de papel, convertidos
pela escala do pavimento (``storeys.paper``).
"""

from __future__ import annotations

import math

import ifcopenshell.util.element

from brasbim.core import geom2d, storeys
from brasbim.core.annotations import base, prims
from brasbim.core.annotations.prims import Prims, Stroke, Text
from brasbim.core.document import Document, OpError

CIRCLE_STEPS = 72
SPLINE_STEPS = 24
CURVE_WEIGHT = 0.18  # mm (§5)
DIM_WEIGHT = 0.13
ARROW = 2.5  # mm de papel: seta das cotas e do rótulo
TEXT = 2.5  # mm de papel
CLOUD_ARC = 4.0  # mm de papel: corda de cada arco da nuvem
TAG = 5.0  # mm de papel: lado do triângulo do marcador
LABEL_FIELDS = ("free", "type", "name", "code")


def fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _p(fn, p) -> list[float]:
    q = fn(tuple(p))
    return [float(q[0]), float(q[1])]


def _arc_points(center, radius: float, a0: float, a1: float, steps: int = CIRCLE_STEPS):
    """Pontos do arco de ``a0`` a ``a1`` graus (anti-horário)."""
    sweep = (a1 - a0) % 360.0 or 360.0
    n = max(2, math.ceil(steps * sweep / 360.0))
    return tuple((center[0] + radius * math.cos(math.radians(a0 + sweep * k / n)),
                  center[1] + radius * math.sin(math.radians(a0 + sweep * k / n)))
                 for k in range(n + 1))


def _check_line(state) -> None:
    if state["dash"] not in prims.DASHES:
        raise OpError(f"tipo de linha inválido: {state['dash']!r}")
    if state["weight"] <= 0:
        raise OpError("a espessura deve ser positiva")


# --- círculo -------------------------------------------------------------------------------


def _circle_build(doc, storey, state) -> Prims:
    pts = _arc_points(state["center"], state["radius"], 0.0, 360.0)[:-1]
    return Prims(strokes=[Stroke(pts, True, state["weight"], state["dash"])])


def _circle_validate(state) -> None:
    if state["radius"] <= 1e-6:
        raise OpError("o raio do círculo deve ser positivo")
    _check_line(state)


def _circle_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"center": _p(fn, state["center"])}


CIRCLE = base.Kind("circle2d", "círculo", None, "Circulo",
                   {"center": [0.0, 0.0], "radius": 1.0, "weight": CURVE_WEIGHT,
                    "dash": "solid"},
                   _circle_build, _circle_mapped, validate=_circle_validate)


# --- arco ------------------------------------------------------------------------------------


def arc_from_points(p0, pm, p1) -> dict:
    """Centro, raio e ângulos (anti-horário, passando por ``pm``) do arco por três pontos."""
    try:
        center, radius = geom2d.circle_through(tuple(p0), tuple(pm), tuple(p1))
    except ValueError:
        raise OpError("os três pontos estão alinhados: não há arco") from None

    def ang(p):
        return math.degrees(math.atan2(p[1] - center[1], p[0] - center[0])) % 360.0

    a0, am, a1 = ang(p0), ang(pm), ang(p1)
    if (am - a0) % 360.0 > (a1 - a0) % 360.0:  # o ponto do meio está do outro lado
        a0, a1 = a1, a0
    return {"center": [center[0], center[1]], "radius": radius, "start": a0, "end": a1}


def _arc_build(doc, storey, state) -> Prims:
    pts = _arc_points(state["center"], state["radius"], state["start"], state["end"])
    return Prims(strokes=[Stroke(pts, False, state["weight"], state["dash"])])


def _arc_validate(state) -> None:
    if state["radius"] <= 1e-6:
        raise OpError("o raio do arco deve ser positivo")
    if abs((state["end"] - state["start"]) % 360.0) < 1e-6:
        raise OpError("o arco precisa de dois ângulos diferentes")
    _check_line(state)


def _arc_mapped(state, fn, turn, mirrored, moving) -> dict:
    a, b = turn(state["start"]) % 360.0, turn(state["end"]) % 360.0
    if mirrored:  # o sentido inverte: o mesmo traço vai de b até a
        a, b = b, a
    return {"center": _p(fn, state["center"]), "start": a, "end": b}


ARC = base.Kind("arc2d", "arco", None, "Arco",
                {"center": [0.0, 0.0], "radius": 1.0, "start": 0.0, "end": 90.0,
                 "weight": CURVE_WEIGHT, "dash": "solid"},
                _arc_build, _arc_mapped, validate=_arc_validate)


# --- curva livre -----------------------------------------------------------------------------


def spline(points, closed: bool, steps: int = SPLINE_STEPS) -> list[tuple[float, float]]:
    """Curva de Catmull-Rom que passa por todos os pontos (CG)."""
    pts = [tuple(p) for p in points]
    if len(pts) < 3:
        return pts
    n = len(pts)

    def at(i):
        if closed:
            return pts[i % n]
        return pts[min(max(i, 0), n - 1)]

    out = []
    segments = n if closed else n - 1
    for i in range(segments):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t
                                    + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3)
                             for c in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def _spline_build(doc, storey, state) -> Prims:
    pts = tuple(spline(state["points"], state["closed"]))
    return Prims(strokes=[Stroke(pts, state["closed"], state["weight"], state["dash"])])


def _spline_validate(state) -> None:
    if len(state["points"]) < 2:
        raise OpError("a curva precisa de pelo menos 2 pontos")
    _check_line(state)


def _spline_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"points": [_p(fn, p) for p in state["points"]]}


SPLINE = base.Kind("spline2d", "curva", None, "Curva",
                   {"points": [], "closed": False, "weight": CURVE_WEIGHT, "dash": "solid"},
                   _spline_build, _spline_mapped, validate=_spline_validate)


# --- cota de raio ----------------------------------------------------------------------------


def curve_of(doc: Document, gid: str | None):
    """(centro, raio) do círculo, arco ou parede em arco (pelo eixo), ou None."""
    element = doc.find(gid) if gid else None
    if element is None:
        return None
    if element.is_a("IfcAnnotation"):
        kind = base.kind_of(element)
        if kind in (CIRCLE, ARC):
            state = base.read_state(element)
            return tuple(state["center"]), float(state["radius"])
        return None
    if element.is_a("IfcWall"):
        from brasbim.core.walls.wall import read_state as read_wall

        try:
            path = geom2d.path_from_dict(read_wall(doc, element)["path"])
        except (OpError, ValueError, KeyError):
            return None
        if isinstance(path, geom2d.LinePath):
            return None
        center = geom2d.frame(path).to_global(path.local_center())
        return (float(center[0]), float(center[1])), float(path.radius)
    return None


def curves_near(doc: Document, storey, p, tol: float) -> list[tuple[str, tuple, float]]:
    """Círculos, arcos e paredes em arco do pavimento cuja curva passa perto de ``p``."""
    out = []
    for e in ifcopenshell.util.element.get_decomposition(storey):
        if not (e.is_a("IfcAnnotation") or e.is_a("IfcWall")):
            continue
        found = curve_of(doc, e.GlobalId)
        if found is None:
            continue
        center, radius = found
        gap = abs(math.dist(center, p) - radius)
        if gap <= tol:
            out.append((gap, e.GlobalId, center, radius))
    return [(g, c, r) for _, g, c, r in sorted(out)]


def _arrow(tip, toward, k: float):
    """Seta cheia com a ponta em ``tip``, apontando para longe de ``toward``."""
    dx, dy = tip[0] - toward[0], tip[1] - toward[1]
    n = math.hypot(dx, dy) or 1.0
    d = (dx / n, dy / n)
    side = (-d[1], d[0])
    length, half = ARROW * k, ARROW * k * 0.3
    back = (tip[0] - d[0] * length, tip[1] - d[1] * length)
    return Stroke((tip, (back[0] + side[0] * half, back[1] + side[1] * half),
                   (back[0] - side[0] * half, back[1] - side[1] * half)), True, DIM_WEIGHT)


def _radius_state(doc, state) -> tuple[tuple, float]:
    found = curve_of(doc, state.get("ref")) if state.get("ref") else None
    if found is not None:
        return found
    return tuple(state["center"]), float(state["radius"])


def _radius_build(doc, storey, state) -> Prims:
    k = storeys.paper(storey, 1.0)
    center, radius = _radius_state(doc, state)
    a = math.radians(state["angle"])
    d = (math.cos(a), math.sin(a))
    tip = (center[0] + d[0] * radius, center[1] + d[1] * radius)
    out = Prims()
    if state["diameter"]:
        other = (center[0] - d[0] * radius, center[1] - d[1] * radius)
        out.strokes += [Stroke((other, tip), False, DIM_WEIGHT), _arrow(tip, center, k),
                        _arrow(other, center, k)]
        text = f"Ø {fmt(2 * radius)}"
        mid = center
    else:
        out.strokes += [Stroke((center, tip), False, DIM_WEIGHT), _arrow(tip, center, k)]
        text = f"R {fmt(radius)}"
        mid = ((center[0] + tip[0]) / 2, (center[1] + tip[1]) / 2)
    angle = prims.readable(state["angle"])
    up = (-math.sin(math.radians(angle)), math.cos(math.radians(angle)))
    out.texts.append(Text((mid[0] + up[0] * k, mid[1] + up[1] * k), text, TEXT * k, angle,
                          "center", "bottom"))
    return out


def _radius_validate(state) -> None:
    if state["radius"] <= 1e-6:
        raise OpError("o raio da cota deve ser positivo")


def _radius_mapped(state, fn, turn, mirrored, moving) -> dict:
    keep = state["ref"] if state.get("ref") in moving else None
    return {"center": _p(fn, state["center"]), "angle": turn(state["angle"]) % 360.0,
            "ref": keep}


def _radius_depends(state) -> set[str]:
    return {state["ref"]} if state.get("ref") else set()


RADIUS = base.Kind("radius_dim", "cota de raio", "DIMENSION", "CotaDeRaio",
                   {"center": [0.0, 0.0], "radius": 1.0, "angle": 45.0, "diameter": False,
                    "ref": None},
                   _radius_build, _radius_mapped, _radius_depends, _radius_validate)


def refresh_radius(doc: Document, element) -> None:
    """Guarda a última medida da cota presa (se o elemento sumir, fica livre ali)."""
    state = base.read_state(element)
    found = curve_of(doc, state.get("ref")) if state.get("ref") else None
    if found is None:
        return
    center, radius = found
    if math.dist(center, state["center"]) > 1e-9 or abs(radius - state["radius"]) > 1e-9:
        state["center"], state["radius"] = [center[0], center[1]], radius
        base.set_cache(doc, element, state)


# --- cota de ângulo -------------------------------------------------------------------------


def angle_value(state) -> float:
    """Ângulo de ``a`` até ``b`` em torno do vértice, de 0 a 180 graus."""
    v, a, b = state["vertex"], state["a"], state["b"]
    a0 = math.atan2(a[1] - v[1], a[0] - v[0])
    a1 = math.atan2(b[1] - v[1], b[0] - v[0])
    d = math.degrees((a1 - a0) % (2 * math.pi))
    return 360.0 - d if d > 180.0 else d


def _angle_build(doc, storey, state) -> Prims:
    k = storeys.paper(storey, 1.0)
    v, a, b = state["vertex"], state["a"], state["b"]
    r = state["radius"]
    a0 = math.degrees(math.atan2(a[1] - v[1], a[0] - v[0]))
    a1 = math.degrees(math.atan2(b[1] - v[1], b[0] - v[0]))
    if (a1 - a0) % 360.0 > 180.0:
        a0, a1 = a1, a0
    pts = _arc_points(v, r, a0, a1, 90)
    out = Prims(strokes=[Stroke(pts, False, DIM_WEIGHT)])
    for end, near in ((pts[0], pts[1]), (pts[-1], pts[-2])):
        out.strokes.append(_arrow(end, near, k))
    for p in (a, b):  # os lados, até o arco se precisar
        d = math.dist(v, p)
        if d < r:
            q = (v[0] + (p[0] - v[0]) * r / d, v[1] + (p[1] - v[1]) * r / d)
            out.strokes.append(Stroke((tuple(p), q), False, DIM_WEIGHT))
    mid_angle = math.radians(a0 + ((a1 - a0) % 360.0) / 2)
    at = (v[0] + (r + 1.5 * k) * math.cos(mid_angle), v[1] + (r + 1.5 * k) * math.sin(mid_angle))
    text = f"{angle_value(state):.1f}°".replace(".", ",")
    out.texts.append(Text(at, text, TEXT * k, 0.0, "center", "middle"))
    return out


def _angle_validate(state) -> None:
    v = state["vertex"]
    if math.dist(v, state["a"]) < 1e-6 or math.dist(v, state["b"]) < 1e-6:
        raise OpError("os pontos dos lados não podem ser o vértice")
    if state["radius"] <= 1e-6:
        raise OpError("o raio do arco da cota deve ser positivo")


def _angle_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"vertex": _p(fn, state["vertex"]), "a": _p(fn, state["a"]),
            "b": _p(fn, state["b"])}


ANGLE = base.Kind("angle_dim", "cota de ângulo", "DIMENSION", "CotaDeAngulo",
                  {"vertex": [0.0, 0.0], "a": [1.0, 0.0], "b": [0.0, 1.0], "radius": 0.5},
                  _angle_build, _angle_mapped, validate=_angle_validate)


# --- rótulo ------------------------------------------------------------------------------------


def label_text(doc: Document, state) -> str:
    """Texto do rótulo: o digitado, ou o dado do elemento apontado (§2)."""
    field = state["field"]
    element = doc.find(state["ref"]) if state.get("ref") else None
    if field == "free" or element is None:
        return state["text"] or "?"
    if field == "name":
        return element.Name or state["text"] or "?"
    t = ifcopenshell.util.element.get_type(element)
    if field == "code":
        for pset in ifcopenshell.util.element.get_psets(element).values():
            if pset.get("Reference"):
                return str(pset["Reference"])
        return (t.Name if t is not None else element.Name) or "?"
    return (t.Name if t is not None else element.Name) or state["text"] or "?"


def _label_build(doc, storey, state) -> Prims:
    k = storeys.paper(storey, 1.0)
    tip, at = tuple(state["at"]), tuple(state["text_at"])
    text = label_text(doc, state)
    h = TEXT * k
    width = len(text) * h * 0.62
    right = at[0] >= tip[0]
    end = (at[0] + width if right else at[0] - width, at[1])
    out = Prims(strokes=[Stroke((tip, at), False, DIM_WEIGHT), Stroke((at, end), False,
                                                                       DIM_WEIGHT),
                         _arrow(tip, at, k)])
    out.texts.append(Text((at[0] + (0.5 * k if right else -0.5 * k), at[1] + 0.6 * k), text,
                          h, 0.0, "left" if right else "right", "bottom"))
    return out


def _label_validate(state) -> None:
    if state["field"] not in LABEL_FIELDS:
        raise OpError(f"conteúdo de rótulo inválido: {state['field']!r}")
    if state["field"] == "free" and not str(state["text"] or "").strip():
        raise OpError("o rótulo está vazio")


def _label_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"at": _p(fn, state["at"]), "text_at": _p(fn, state["text_at"])}


def _label_depends(state) -> set[str]:
    return {state["ref"]} if state.get("ref") else set()


LABEL = base.Kind("label", "rótulo", "TEXT", "Rotulo",
                  {"at": [0.0, 0.0], "text_at": [1.0, 1.0], "text": "", "ref": None,
                   "field": "free"},
                  _label_build, _label_mapped, _label_depends, _label_validate)


# --- marcador de alteração ------------------------------------------------------------------------


def _cloud(outline, chord: float) -> list[tuple[float, float]]:
    """Nuvem: arcos para fora ao longo do contorno (anti-horário)."""
    ring = [tuple(p) for p in outline]
    if sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] *
           ring[i][1] for i in range(len(ring))) < 0:
        ring.reverse()
    out = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        length = math.dist(a, b)
        n = max(1, round(length / chord))
        d = ((b[0] - a[0]) / length, (b[1] - a[1]) / length) if length > 1e-9 else (1.0, 0.0)
        outward = (d[1], -d[0])  # à direita de quem anda no sentido anti-horário
        step = length / n
        for j in range(n):
            p = (a[0] + d[0] * step * j, a[1] + d[1] * step * j)
            for s in range(8):
                t = s / 8
                bulge = math.sin(math.pi * t) * step * 0.35
                out.append((p[0] + d[0] * step * t + outward[0] * bulge,
                            p[1] + d[1] * step * t + outward[1] * bulge))
    return out


def _revision_build(doc, storey, state) -> Prims:
    k = storeys.paper(storey, 1.0)
    out = Prims(strokes=[Stroke(tuple(_cloud(state["outline"], CLOUD_ARC * k)), True, 0.25)])
    x, y = state["outline"][0]
    s = TAG * k
    tri = ((x - s / 2, y), (x + s / 2, y), (x, y + s * 0.866))
    out.strokes.append(Stroke(tri, True, 0.25))
    out.texts.append(Text((x, y + s * 0.3), str(state["number"]), TEXT * k * 0.9, 0.0,
                          "center", "middle"))
    if state.get("note"):
        out.texts.append(Text((x + s * 0.7, y + s * 0.2), state["note"], TEXT * k, 0.0,
                              "left", "bottom"))
    return out


def _revision_validate(state) -> None:
    if len(state["outline"]) < 3:
        raise OpError("o marcador precisa de um contorno de pelo menos 3 pontos")
    if not str(state["number"]).strip():
        raise OpError("o marcador precisa de um número")


def _revision_mapped(state, fn, turn, mirrored, moving) -> dict:
    outline = [_p(fn, p) for p in state["outline"]]
    if mirrored:
        outline.reverse()
    return {"outline": outline}


REVISION = base.Kind("revision", "marcador de alteração", "SYMBOL", "Alteracao",
                     {"outline": [], "number": "1", "note": ""},
                     _revision_build, _revision_mapped, validate=_revision_validate)


def next_revision(doc: Document) -> str:
    """O próximo número livre dos marcadores (1, 2, 3…)."""
    used = set()
    for e in doc.ifc.by_type("IfcAnnotation"):
        if base.kind_of(e) is REVISION:
            used.add(str(base.read_state(e)["number"]))
    n = 1
    while str(n) in used:
        n += 1
    return str(n)


for _kind in (CIRCLE, ARC, SPLINE, RADIUS, ANGLE, LABEL, REVISION):
    base.register_kind(_kind)
