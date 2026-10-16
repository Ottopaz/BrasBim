# SPDX-License-Identifier: LGPL-3.0-or-later
"""Planta por ambientes (spec/ui 16 §4.2): retângulos de cômodos → paredes.

Cada cômodo é um retângulo medido **pelo eixo das paredes** ({"name", "x", "y",
"width", "depth"}; x, y = canto de menor x e menor y). As bordas dos retângulos viram
paredes: a borda de um cômodo só é **externa**; a que dois cômodos dividem é **interna**
e entra uma vez. Pares em ``open_between`` não ganham parede entre si (sala e cozinha
integradas). Trechos alinhados e contíguos do mesmo tipo viram uma parede só, que passa
direto pelas junções em T.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from brasbim.core.document import OpError

EPS = 1e-6


@dataclass(frozen=True)
class Room:
    name: str
    x: float
    y: float
    width: float
    depth: float

    @property
    def x1(self) -> float:
        return self.x + self.width

    @property
    def y1(self) -> float:
        return self.y + self.depth

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.depth / 2)


@dataclass(frozen=True)
class Segment:
    """Parede a criar: de ``start`` a ``end`` pelo eixo; ``kind`` externa ou interna."""

    start: tuple[float, float]
    end: tuple[float, float]
    kind: str  # "exterior" | "interior"


def rooms_from(data: list[dict]) -> list[Room]:
    rooms = []
    for i, d in enumerate(data):
        try:
            room = Room(str(d.get("name") or f"Ambiente {i + 1}"), float(d["x"]),
                        float(d["y"]), float(d["width"]), float(d["depth"]))
        except (KeyError, TypeError, ValueError):
            raise OpError(f"ambiente {i + 1}: informe x, y, largura e profundidade") from None
        if room.width < 0.5 or room.depth < 0.5:
            raise OpError(f"{room.name}: largura e profundidade precisam de pelo menos 0,50 m")
        rooms.append(room)
    names = [r.name for r in rooms]
    if len(set(names)) != len(names):
        raise OpError("os nomes dos ambientes precisam ser diferentes")
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            dx = min(a.x1, b.x1) - max(a.x, b.x)
            dy = min(a.y1, b.y1) - max(a.y, b.y)
            if dx > EPS and dy > EPS:
                raise OpError(f"{a.name} e {b.name} se sobrepõem ({dx:.2f} × {dy:.2f} m)")
    return rooms


def _key(v: float) -> float:
    return round(v, 6)


def segments(rooms: list[Room], open_between=()) -> list[Segment]:
    """Paredes pelo eixo, já juntas por alinhamento (ver o cabeçalho do módulo)."""
    open_pairs = {frozenset(p) for p in open_between}
    # Para cada linha (horizontal em y, vertical em x): trechos (a, b, cômodo, lado).
    lines: dict[tuple[str, float], list[tuple[float, float, str, int]]] = {}
    for r in rooms:
        lines.setdefault(("h", _key(r.y)), []).append((r.x, r.x1, r.name, +1))   # cômodo acima
        lines.setdefault(("h", _key(r.y1)), []).append((r.x, r.x1, r.name, -1))  # abaixo
        lines.setdefault(("v", _key(r.x)), []).append((r.y, r.y1, r.name, +1))   # à direita
        lines.setdefault(("v", _key(r.x1)), []).append((r.y, r.y1, r.name, -1))  # à esquerda
    out: list[Segment] = []
    for (axis, c), spans in sorted(lines.items()):
        cuts = sorted({_key(v) for a, b, _, _ in spans for v in (a, b)})
        pieces: list[tuple[float, float, str]] = []
        for a, b in itertools.pairwise(cuts):
            mid = (a + b) / 2
            sides = {side: name for s0, s1, name, side in spans if s0 - EPS < mid < s1 + EPS}
            if not sides:
                continue
            if len(sides) == 2:
                if frozenset(sides.values()) in open_pairs:
                    continue
                kind = "interior"
            else:
                kind = "exterior"
            pieces.append((a, b, kind))
        merged: list[list] = []
        for a, b, kind in pieces:
            if merged and abs(merged[-1][1] - a) < EPS and merged[-1][2] == kind:
                merged[-1][1] = b
            else:
                merged.append([a, b, kind])
        for a, b, kind in merged:
            if axis == "h":
                out.append(Segment((a, c), (b, c), kind))
            else:
                out.append(Segment((c, a), (c, b), kind))
    return out


def merge_kinds(segs: list[Segment]) -> list[Segment]:
    """Junta trechos alinhados e contíguos de tipos diferentes (quando externas e
    internas usam o mesmo tipo de parede, ficam paredes inteiras)."""
    groups: dict[tuple[str, float], list[Segment]] = {}
    for s in segs:
        horizontal = abs(s.start[1] - s.end[1]) < EPS
        key = ("h", _key(s.start[1])) if horizontal else ("v", _key(s.start[0]))
        groups.setdefault(key, []).append(s)
    out = []
    for (axis, _), group in sorted(groups.items()):
        i = 0 if axis == "h" else 1
        group.sort(key=lambda s: s.start[i])
        current = group[0]
        for s in group[1:]:
            if abs(s.start[i] - current.end[i]) < EPS:
                kind = "exterior" if "exterior" in (current.kind, s.kind) else "interior"
                current = Segment(current.start, s.end, kind)
            else:
                out.append(current)
                current = s
        out.append(current)
    return out


def inner_outline(room: Room, segs: list[Segment], half: dict[str, float]) -> list:
    """Contorno do ambiente na face interna: o retângulo recuado, em cada lado, da meia
    espessura da parede que está nele (``half`` por ``kind``; 0 onde não há parede)."""

    def inset(axis: str, c: float, a: float, b: float) -> float:
        for s in segs:
            if axis == "h" and abs(s.start[1] - c) < EPS and abs(s.end[1] - c) < EPS:
                lo, hi = sorted((s.start[0], s.end[0]))
            elif axis == "v" and abs(s.start[0] - c) < EPS and abs(s.end[0] - c) < EPS:
                lo, hi = sorted((s.start[1], s.end[1]))
            else:
                continue
            if lo < (a + b) / 2 < hi:
                return half[s.kind]
        return 0.0

    bottom = inset("h", room.y, room.x, room.x1)
    top = inset("h", room.y1, room.x, room.x1)
    left = inset("v", room.x, room.y, room.y1)
    right = inset("v", room.x1, room.y, room.y1)
    x0, x1 = room.x + left, room.x1 - right
    y0, y1 = room.y + bottom, room.y1 - top
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def outer_outline(rooms: list[Room], half: float) -> list | None:
    """Contorno externo (face de fora das paredes externas) quando os cômodos formam um
    retângulo só; ``None`` se não formam (aí o piso é desenhado pelo contorno dado)."""
    x0 = min(r.x for r in rooms)
    y0 = min(r.y for r in rooms)
    x1 = max(r.x1 for r in rooms)
    y1 = max(r.y1 for r in rooms)
    if abs(sum(r.width * r.depth for r in rooms) - (x1 - x0) * (y1 - y0)) > 1e-4:
        return None
    return [[x0 - half, y0 - half], [x1 + half, y0 - half], [x1 + half, y1 + half],
            [x0 - half, y1 + half]]
