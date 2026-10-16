# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cotas lineares associativas (``IfcAnnotation`` ``DIMENSION``), spec/ui 13 §4.

Estado::

    {"storey": "<GlobalId>", "points": [{"at": [0, 0], "ref": {...} | None}, ...],
     "direction": "aligned" | "fixed", "angle": 0.0, "offset": -0.6}

``direction`` ``aligned``: paralela aos dois primeiros pontos; ``fixed``: no ``angle``
(0 = horizontal, 90 = vertical). ``offset``: afastamento da linha de cota em relação ao
primeiro ponto, perpendicular à direção (positivo para a esquerda dela).

Ponto preso (``ref``, §4.3): ``wall`` (``end`` start/end × ``face`` left/right/axis),
``opening`` (``edge`` × ``face``), ``column`` (``u``, ``v``: fração de b/2 e h/2 a partir
do centro da seção), ``beam`` (``end`` × ``face``) e ``vertex`` (``index`` no contorno de
laje ou ambiente). ``at`` guarda a última posição resolvida (refeita pela derivação): se
o elemento some, o ponto fica livre ali (aviso).
"""

from __future__ import annotations

import itertools
import logging
import math

from brasbim.core import geom2d, storeys
from brasbim.core.annotations import base, prims
from brasbim.core.annotations.prims import Prims, Stroke, Text
from brasbim.core.document import Document, OpError

log = logging.getLogger(__name__)

DIRECTIONS = ("aligned", "fixed")
TICK, GAP, OVER, TEXT, TEXT_GAP = 3.0, 2.0, 2.0, 2.5, 1.0  # mm de papel (§4.2)
WEIGHT = 0.13  # mm (§8)
AUTO_OFFSET = 12.0  # mm de papel: cota automática da parede (§4.5)


def fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


# --- pontos presos --------------------------------------------------------------------


def _wall_point(doc: Document, gid: str, end: str, face: str):
    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state

    wall = doc.find(gid)
    if wall is None or not wall.is_a("IfcWall"):
        return None
    state = read_state(doc, wall)
    band = rebuild.band(doc, state)
    if not isinstance(band.path, geom2d.LinePath):
        return None
    length = band.path.length
    if face == "axis":
        return band.path.start if end == "start" else band.path.end
    y = band.ymax if face == "left" else band.ymin
    try:
        pts = geom2d.polygon(rebuild.profile(doc, wall, band))
    except ValueError:
        pts = []
    on = [p for p in pts if abs(p[1] - y) < 1e-6]
    if on:
        x = min(p[0] for p in on) if end == "start" else max(p[0] for p in on)
    else:
        x = 0.0 if end == "start" else length
    return band.frame.to_global((x, y))


def _opening_point(doc: Document, gid: str, edge: str, face: str):
    from brasbim.core.walls import openings, rebuild
    from brasbim.core.walls.wall import read_state

    opening = doc.find(gid)
    if opening is None or not opening.is_a("IfcOpeningElement"):
        return None
    wall = openings.host(opening)
    if wall is None or not wall.is_a("IfcWall"):
        return None
    o = openings.read_state(opening)
    band = rebuild.band(doc, read_state(doc, wall))
    x = o["distance"] if edge == "start" else o["distance"] + o["width"]
    y = {"left": band.ymax, "right": band.ymin}.get(face, (band.ymin + band.ymax) / 2)
    return band.frame.to_global((x, y))


def _column_point(doc: Document, gid: str, u: float, v: float):
    from brasbim.core.structure import columns, profiles

    column = doc.find(gid)
    if column is None or not column.is_a("IfcColumn"):
        return None
    state = columns.read_state(doc, column)
    if state["foreign"] is not None:
        return None
    w, h = profiles.size(columns.section(doc, state))
    c = columns.center(doc, state)
    a = math.radians(state["angle"])
    x, y = u * w / 2, v * h / 2
    return (c[0] + math.cos(a) * x - math.sin(a) * y, c[1] + math.sin(a) * x + math.cos(a) * y)


def _beam_point(doc: Document, gid: str, end: str, face: str):
    from brasbim.core.structure import beams

    beam = doc.find(gid)
    if beam is None or not beam.is_a("IfcBeam"):
        return None
    state = beams.read_state(doc, beam)
    if state["foreign"] is not None:
        return None
    if face == "axis":
        return tuple(state["start"] if end == "start" else state["end"])
    ring = beams.outline(doc, state)  # direita: 0 → 1; esquerda: 3 → 2
    return {("start", "right"): ring[0], ("end", "right"): ring[1],
            ("end", "left"): ring[2], ("start", "left"): ring[3]}[(end, face)]


def _vertex_point(doc: Document, gid: str, index: int):
    from brasbim.core.annotations import spaces
    from brasbim.core.structure import slabs

    element = doc.find(gid)
    if element is None:
        return None
    if element.is_a("IfcSlab"):
        state = slabs.read_state(doc, element)
        outline = state["outline"] if state["foreign"] is None else None
    elif element.is_a("IfcSpace"):
        outline = spaces.read_state(element)["outline"]
    else:
        return None
    if not outline or not 0 <= index < len(outline):
        return None
    return tuple(outline[index])


def resolve(doc: Document, ref: dict):
    """Posição do ponto preso, ou ``None`` se o elemento não existe mais."""
    try:
        kind = ref["kind"]
        if kind == "wall":
            return _wall_point(doc, ref["gid"], ref["end"], ref["face"])
        if kind == "opening":
            return _opening_point(doc, ref["gid"], ref["edge"], ref["face"])
        if kind == "column":
            return _column_point(doc, ref["gid"], ref["u"], ref["v"])
        if kind == "beam":
            return _beam_point(doc, ref["gid"], ref["end"], ref["face"])
        if kind == "vertex":
            return _vertex_point(doc, ref["gid"], ref["index"])
    except (OpError, KeyError, ValueError, TypeError):
        return None
    return None


def candidates(doc: Document, storey) -> list[tuple[dict, tuple[float, float]]]:
    """Pontos que uma cota pode prender no pavimento: (referência, posição)."""
    import ifcopenshell.util.element

    from brasbim.core.structure import roofs
    from brasbim.core.walls import openings

    out = []
    for e in ifcopenshell.util.element.get_decomposition(storey):
        refs = []
        if roofs.is_part(e):
            continue
        if e.is_a("IfcWall"):
            refs = [{"kind": "wall", "gid": e.GlobalId, "end": end, "face": face}
                    for end in ("start", "end") for face in ("left", "right", "axis")]
            for o in openings.of_wall(e):
                refs += [{"kind": "opening", "gid": o.GlobalId, "edge": edge, "face": face}
                         for edge in ("start", "end") for face in ("left", "right")]
        elif e.is_a("IfcColumn"):
            refs = [{"kind": "column", "gid": e.GlobalId, "u": u, "v": v}
                    for u in (-1.0, 0.0, 1.0) for v in (-1.0, 0.0, 1.0)]
        elif e.is_a("IfcBeam"):
            refs = [{"kind": "beam", "gid": e.GlobalId, "end": end, "face": face}
                    for end in ("start", "end") for face in ("left", "right", "axis")]
        elif e.is_a("IfcSlab") or e.is_a("IfcSpace"):
            refs = [{"kind": "vertex", "gid": e.GlobalId, "index": i} for i in range(64)]
        for ref in refs:
            p = resolve(doc, ref)
            if p is not None:
                out.append((ref, (float(p[0]), float(p[1]))))
    return out


def ref_at(doc: Document, storey, p, tol: float) -> dict | None:
    """Referência do ponto de elemento mais perto de ``p`` (até ``tol``)."""
    near = [(math.dist(p, q), i, ref) for i, (ref, q) in enumerate(candidates(doc, storey))
            if math.dist(p, q) <= tol]
    return min(near, key=lambda n: (n[0], n[1]))[2] if near else None


# --- geometria -------------------------------------------------------------------------


def points(doc: Document, state: dict) -> list[tuple[float, float]]:
    out = []
    for item in state["points"]:
        p = resolve(doc, item["ref"]) if item.get("ref") else None
        out.append(tuple(p) if p is not None else tuple(item["at"]))
    return out


def frame(state: dict, pts) -> tuple[tuple, tuple]:
    """(direção, normal à esquerda) da linha de cota."""
    if state["direction"] == "aligned":
        dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        n = math.hypot(dx, dy)
        d = (dx / n, dy / n) if n > 1e-12 else (1.0, 0.0)
    else:
        a = math.radians(state["angle"])
        d = (math.cos(a), math.sin(a))
    return d, (-d[1], d[0])


def measures(doc: Document, state: dict) -> list[float]:
    """Medidas da cota, na ordem ao longo da linha."""
    pts = points(doc, state)
    d, _ = frame(state, pts)
    ts = sorted({round((p[0] - pts[0][0]) * d[0] + (p[1] - pts[0][1]) * d[1], 9)
                 for p in pts})
    return [b - a for a, b in itertools.pairwise(ts) if b - a > 1e-6]


def _build(doc: Document, storey, state: dict) -> Prims:
    k = storeys.paper(storey, 1.0)  # m por mm de papel
    pts = points(doc, state)
    d, n = frame(state, pts)
    p0 = pts[0]

    def at(t, s):
        return (p0[0] + d[0] * t + n[0] * s, p0[1] + d[1] * t + n[1] * s)

    ts = [(p[0] - p0[0]) * d[0] + (p[1] - p0[1]) * d[1] for p in pts]
    ss = [(p[0] - p0[0]) * n[0] + (p[1] - p0[1]) * n[1] for p in pts]
    off = state["offset"]
    out = Prims()
    out.strokes.append(Stroke((at(min(ts), off), at(max(ts), off)), False, WEIGHT))
    for t, s in zip(ts, ss, strict=True):
        if abs(off - s) > GAP * k:
            sign = 1.0 if off > s else -1.0
            out.strokes.append(Stroke((at(t, s + sign * GAP * k), at(t, off + sign * OVER * k)),
                                      False, WEIGHT))
        tick = ((d[0] + n[0]) / math.sqrt(2) * TICK * k / 2,
                (d[1] + n[1]) / math.sqrt(2) * TICK * k / 2)
        c = at(t, off)
        out.strokes.append(Stroke(((c[0] - tick[0], c[1] - tick[1]),
                                   (c[0] + tick[0], c[1] + tick[1])), False, WEIGHT))
    angle = math.degrees(math.atan2(d[1], d[0]))
    shown = prims.readable(angle)
    up = n if abs(((shown - angle) + 180.0) % 360.0 - 180.0) < 1.0 else (-n[0], -n[1])
    marks = sorted({round(t, 9) for t in ts})
    for a, b in itertools.pairwise(marks):
        if b - a <= 1e-6:
            continue
        c = at((a + b) / 2, off)
        out.texts.append(Text((c[0] + up[0] * TEXT_GAP * k, c[1] + up[1] * TEXT_GAP * k),
                              fmt(b - a), TEXT * k, shown, "center", "bottom"))
    return out


def _validate(state: dict) -> None:
    if len(state["points"]) < 2:
        raise OpError("a cota precisa de pelo menos 2 pontos")
    if state["direction"] not in DIRECTIONS:
        raise OpError(f"direção de cota inválida: {state['direction']!r}")


def _mapped(state, fn, turn, mirrored, moving) -> dict:
    """Pontos presos a elementos que se movem junto continuam presos; os outros ficam
    livres na posição levada."""
    out = []
    for item in state["points"]:
        q = fn(tuple(item["at"]))
        ref = item.get("ref")
        keep = ref if ref and ref.get("gid") in moving else None
        out.append({"at": [float(q[0]), float(q[1])], "ref": keep})
    changes = {"points": out, "angle": turn(state["angle"]) % 360.0}
    if mirrored:
        changes["offset"] = -state["offset"]
    return changes


def _depends(state: dict) -> set[str]:
    return {item["ref"]["gid"] for item in state["points"] if item.get("ref")}


DIMENSION = base.Kind("dimension", "cota", "DIMENSION", None,
                      {"points": [], "direction": "aligned", "angle": 0.0, "offset": 0.0},
                      _build, _mapped, _depends, _validate)
base.register_kind(DIMENSION)


def refresh(doc: Document, element) -> None:
    """Guarda a posição atual dos pontos presos (``at``) e avisa quando um elemento
    sumiu (spec/ui 13 §4.3)."""
    state = base.read_state(element)
    changed = False
    for item in state["points"]:
        ref = item.get("ref")
        if not ref:
            continue
        p = resolve(doc, ref)
        if p is None:
            if not item.get("lost"):
                log.warning("cota %s: o ponto preso perdeu o elemento e ficou livre",
                            element.GlobalId)
                item["lost"] = True
                changed = True
            continue
        p = [float(p[0]), float(p[1])]
        if item.get("lost") or any(abs(a - b) > 1e-9 for a, b in zip(p, item["at"],
                                                                       strict=True)):
            item["at"], changed = p, True
            item.pop("lost", None)
    if changed:
        base.set_cache(doc, element, state)
