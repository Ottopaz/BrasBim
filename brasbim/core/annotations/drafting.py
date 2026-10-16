# SPDX-License-Identifier: LGPL-3.0-or-later
"""Texto, linha, hachura, norte e cota de nível (spec/ui 13 §5–§7).

Tamanhos em milímetros de papel, convertidos para o modelo pela escala do pavimento
(``storeys.paper``). ``mapped`` recebe ``fn`` (pontos) e ``turn`` (ângulos absolutos, em
graus) da transformação da planta; o texto espelhado continua legível.
"""

from __future__ import annotations

import math

from brasbim.core import storeys
from brasbim.core.annotations import base, prims
from brasbim.core.annotations.prims import Fill, Prims, Stroke, Text
from brasbim.core.document import OpError

TEXT_SIZES = (2.0, 2.5, 3.0, 3.5, 5.0)  # mm de papel (spec/ui 13 §6)
LINE_WEIGHTS = (0.13, 0.18, 0.25, 0.35, 0.5, 0.7)  # mm (NBR 8403, spec/ui 13 §8)
HATCH_PATTERNS = ("solid", "lines", "cross")
NORTH_SIZE = 15.0  # mm de papel (spec/ui 13 §7)
LEVEL_SIZE = 3.0  # mm: lado do triângulo da cota de nível (§5)
LEVEL_TEXT = 2.5


def fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def signed(value: float) -> str:
    """"+2,80", "−0,15" (cota de nível, spec/ui 13 §5)."""
    value = 0.0 if abs(value) < 5e-4 else value
    return f"{'+' if value >= 0 else '−'}{fmt(abs(value))}"


def _p(fn, p) -> list[float]:
    q = fn(tuple(p))
    return [float(q[0]), float(q[1])]


# --- texto -------------------------------------------------------------------------------


def _text_build(doc, storey, state) -> Prims:
    h = storeys.paper(storey, state["size"])
    a = math.radians(state["angle"])
    down = (math.sin(a), -math.cos(a))  # perpendicular, para baixo do texto
    out = Prims()
    for i, line in enumerate(state["text"].split("\n")):
        at = (state["at"][0] + down[0] * 1.4 * h * i, state["at"][1] + down[1] * 1.4 * h * i)
        out.texts.append(Text(at, line, h, state["angle"], state["align"], "bottom"))
    return out


def _text_validate(state) -> None:
    if not state["text"].strip():
        raise OpError("o texto está vazio")
    if state["size"] <= 0:
        raise OpError("a altura do texto deve ser positiva")
    if state["align"] not in prims.HALIGN:
        raise OpError(f"alinhamento inválido: {state['align']!r}")


def _text_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"at": _p(fn, state["at"]), "angle": prims.readable(turn(state["angle"]))}


TEXT = base.Kind("text", "texto", "TEXT", None,
                 {"at": [0.0, 0.0], "text": "", "size": 2.5, "angle": 0.0, "align": "left"},
                 _text_build, _text_mapped, validate=_text_validate)


# --- linha -------------------------------------------------------------------------------


def _line_build(doc, storey, state) -> Prims:
    return Prims(strokes=[Stroke(tuple(tuple(p) for p in state["points"]), state["closed"],
                                 state["weight"], state["dash"])])


def _line_validate(state) -> None:
    if len(state["points"]) < 2:
        raise OpError("a linha precisa de pelo menos 2 pontos")
    if state["dash"] not in prims.DASHES:
        raise OpError(f"tipo de linha inválido: {state['dash']!r}")
    if state["weight"] <= 0:
        raise OpError("a espessura deve ser positiva")


def _line_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"points": [_p(fn, p) for p in state["points"]]}


LINE = base.Kind("line2d", "linha", None, "Linha",
                 {"points": [], "closed": False, "weight": 0.25, "dash": "solid"},
                 _line_build, _line_mapped, validate=_line_validate)


# --- hachura -----------------------------------------------------------------------------


def _hatch_build(doc, storey, state) -> Prims:
    color = state["color"]
    fill = {"pattern": state["pattern"],
            "background": color if state["pattern"] == "solid" else None,
            "angle": state["angle"], "spacing": storeys.paper(storey, state["spacing"]),
            "line_color": color, "source": "material"}
    return Prims(fills=[Fill((tuple(tuple(p) for p in state["outline"]),), fill)])


def _hatch_validate(state) -> None:
    if len(state["outline"]) < 3:
        raise OpError("a hachura precisa de um contorno de pelo menos 3 pontos")
    if state["pattern"] not in HATCH_PATTERNS:
        raise OpError(f"padrão de hachura inválido: {state['pattern']!r}")
    if state["spacing"] <= 0:
        raise OpError("o espaçamento da hachura deve ser positivo")


def _hatch_mapped(state, fn, turn, mirrored, moving) -> dict:
    outline = [_p(fn, p) for p in state["outline"]]
    if mirrored:
        outline.reverse()
    return {"outline": outline, "angle": turn(state["angle"]) % 180.0}


HATCH = base.Kind("hatch", "hachura", None, "Hachura",
                  {"outline": [], "pattern": "solid", "color": "#B3B3AD", "angle": 45.0,
                   "spacing": 2.0},
                  _hatch_build, _hatch_mapped, validate=_hatch_validate)


# --- norte -------------------------------------------------------------------------------


def _north_build(doc, storey, state) -> Prims:
    size = storeys.paper(storey, NORTH_SIZE)
    a = math.radians(state["angle"])
    d, n = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    x, y = state["at"]
    tip = (x + d[0] * size, y + d[1] * size)
    head = 0.3 * size
    back = (tip[0] - d[0] * head, tip[1] - d[1] * head)
    arrow = ((back[0] + n[0] * head / 2, back[1] + n[1] * head / 2), tip,
             (back[0] - n[0] * head / 2, back[1] - n[1] * head / 2))
    letter = (tip[0] + d[0] * 0.15 * size, tip[1] + d[1] * 0.15 * size)
    return Prims(strokes=[Stroke(((x, y), tip), False, 0.25),
                          Stroke(arrow, True, 0.25)],
                 texts=[Text(letter, "N", storeys.paper(storey, 3.5), 0.0, "center",
                             "middle")])


def _north_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"at": _p(fn, state["at"]), "angle": turn(state["angle"])}


NORTH = base.Kind("north", "norte", "SYMBOL", "Norte", {"at": [0.0, 0.0], "angle": 90.0},
                  _north_build, _north_mapped)


# --- cota de nível -----------------------------------------------------------------------


def level_value(doc, storey, point) -> float:
    """Cota do pavimento + topo da laje do pavimento sob o ponto (a mais alta), spec/ui 13
    §5."""
    import ifcopenshell.util.element

    from brasbim.core.structure import slabs

    base_z = float(storey.Elevation or 0.0)
    tops = []
    for slab in ifcopenshell.util.element.get_decomposition(storey):
        if not slab.is_a("IfcSlab"):
            continue
        try:
            state = slabs.read_state(doc, slab)
        except OpError:
            continue
        if state["foreign"] is None and _inside(state["outline"], point):
            tops.append(state["top_offset"])
    return base_z + (max(tops) if tops else 0.0)


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


def level_text(doc, storey, state) -> str:
    return state["fixed"] or signed(level_value(doc, storey, state["at"]))


def _level_build(doc, storey, state) -> Prims:
    s = storeys.paper(storey, LEVEL_SIZE)
    x, y = state["at"]
    top = y + s * 0.866
    triangle = ((x, y), (x - s / 2, top), (x + s / 2, top))
    line = ((x - s, top), (x + s * 3.5, top))
    text = Text((x + s * 0.7, top + s * 0.15), level_text(doc, storey, state),
                storeys.paper(storey, LEVEL_TEXT), 0.0, "left", "bottom")
    return Prims(strokes=[Stroke(triangle, True, 0.18), Stroke(line, False, 0.18)],
                 texts=[text])


def _level_mapped(state, fn, turn, mirrored, moving) -> dict:
    return {"at": _p(fn, state["at"])}


LEVEL = base.Kind("level_mark", "cota de nível", "SYMBOL", "CotaDeNivel",
                  {"at": [0.0, 0.0], "fixed": None}, _level_build, _level_mapped)

for _kind in (TEXT, LINE, HATCH, NORTH, LEVEL):
    base.register_kind(_kind)
