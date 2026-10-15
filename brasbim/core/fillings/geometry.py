# SPDX-License-Identifier: LGPL-3.0-or-later
"""Peças do corpo das esquadrias como caixas no sistema local (``porta.md`` §6.2).

Sistema local da porta: x ao longo do vão (0 a largura), y atravessando a parede (o marco
ocupa 0 a ``d``; a folha abre para +y), z para cima a partir da base do vão. Uma caixa é
``(x0, x1, y0, y1, z0, z1)``.
"""

from __future__ import annotations

from brasbim.core.fillings import params

Box = tuple[float, float, float, float, float, float]

# Folhas desenhadas fechadas: em que lado da profundidade do marco ficam.
_FLUSH_OPENING_SIDE = ("SWINGING", "FIXEDPANEL", "FOLDING", "ROLLINGUP")


def _valid(box: Box) -> bool:
    x0, x1, y0, y1, z0, z1 = box
    return x1 - x0 > 1e-9 and y1 - y0 > 1e-9 and z1 - z0 > 1e-9


def door_boxes(width: float, height: float, depth: float, faces: tuple[float, float],
               lining: dict, panels: list[dict]) -> list[Box]:
    """Marco, soleira, guarnições e folhas de uma porta (só as caixas)."""
    return [box for box, _ in door_parts(width, height, depth, faces, lining, panels)]


def door_parts(width: float, height: float, depth: float, faces: tuple[float, float],
               lining: dict, panels: list[dict]) -> list[tuple[Box, str]]:
    """Marco, soleira, guarnições (papel ``lining``) e folhas (``framing``) de uma porta.

    ``depth``: profundidade do marco. ``faces``: y das duas faces da parede no sistema da
    porta (a guarnição encosta nelas, por fora do vão).
    """
    w, h, d = width, height, depth
    t = lining.get("thickness") or 0.0
    tt = lining.get("threshold_thickness") or 0.0
    boxes: list[Box] = []
    if t > 0:
        boxes += [(0, t, 0, d, 0, h), (w - t, w, 0, d, 0, h), (t, w - t, 0, d, h - t, h)]
        if tt > 0:
            boxes.append((t, w - t, 0, d, 0, tt))
        ct, cd = lining.get("casing_thickness"), lining.get("casing_depth")
        if ct and cd:
            for y0, y1 in ((faces[0] - cd, faces[0]), (faces[1], faces[1] + cd)):
                boxes += [(-ct, 0, y0, y1, 0, h), (w, w + ct, y0, y1, 0, h),
                          (-ct, w + ct, y0, y1, h, h + ct)]
    parts = [(b, "lining") for b in boxes]
    x, x_end = t, w - t
    z0, z1 = tt, h - t
    clear = x_end - x
    casing_out = faces[1] + (lining.get("casing_depth") or 0.0)
    for panel in panels:
        pw, pd = panel["width"] * clear, panel["depth"]
        if panel["operation"] in _FLUSH_OPENING_SIDE:
            y0, y1 = d - pd, d
        elif panel["operation"] == "SLIDING":
            y0, y1 = casing_out, casing_out + pd  # corre por fora da parede
        else:  # vaivém: no meio do marco
            y0, y1 = (d - pd) / 2, (d + pd) / 2
        parts.append(((x, x + pw, y0, y1, z0, z1), "framing"))
        x += pw
    return [(tuple(float(v) for v in b), role) for b, role in parts if _valid(b)]


# --- janela (``janela.md`` §6.2) ------------------------------------------------------


def _cells(lo: float, hi: float, total: float, offsets: list[float], bar: float,
           sliding: list[bool]) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Faixas dos caixilhos e dos montantes (ou travessas) entre ``lo`` e ``hi``.

    ``offsets``: centro de cada montante, em fração de ``total``. Entre dois caixilhos de
    correr não há montante: eles se sobrepõem na largura dele (janela §6.2).
    """
    centers = [f * total for f in offsets]
    cells, bars = [], []
    start = lo
    for i, c in enumerate(centers):
        if sliding[i] and sliding[i + 1]:
            cells.append((start, c + bar / 2))
            start = c - bar / 2
        else:
            cells.append((start, c - bar / 2))
            bars.append((c - bar / 2, c + bar / 2))
            start = c + bar / 2
    cells.append((start, hi))
    return cells, bars


def window_parts(width: float, height: float, state: dict) -> list[tuple[Box, str]]:
    """Marco, montantes e travessas (``lining``), perfis dos caixilhos (``framing``) e
    vidros (``glazing``) de uma janela, desenhados fechados.

    ``state``: estado do tipo (``window_types``). O marco ocupa y de 0 a ``LiningDepth``.
    Caixilhos de correr ficam em trilhos paralelos, alternados, no meio do marco.
    """
    w, h = width, height
    lining = state["lining"]
    d, t = lining["depth"], lining["thickness"] or 0.0
    parts: list[tuple[Box, str]] = []
    if t > 0:
        parts += [((0, t, 0, d, 0, h), "lining"), ((w - t, w, 0, d, 0, h), "lining"),
                  ((t, w - t, 0, d, 0, t), "lining"), ((t, w - t, 0, d, h - t, h), "lining")]
    panels = state["panels"]
    vertical = params.is_vertical(state["partitioning"])
    slide = "SLIDINGHORIZONTAL" if vertical else "SLIDINGVERTICAL"
    sliding = [p["operation"] == slide for p in panels]
    if vertical:
        cells, bars = _cells(t, w - t, w, lining["mullion_offsets"],
                             lining["mullion_thickness"] or 0.0, sliding)
        parts += [((a, b, 0, d, t, h - t), "lining") for a, b in bars]
        boxes = [(a, b, t, h - t) for a, b in cells]
    else:
        # Travessas contadas da base; caixilhos na ordem de cima para baixo.
        cells, bars = _cells(t, h - t, h, lining["transom_offsets"],
                             lining["transom_thickness"] or 0.0, list(reversed(sliding)))
        parts += [((t, w - t, 0, d, a, b), "lining") for a, b in bars]
        boxes = [(t, w - t, a, b) for a, b in reversed(cells)]
    track = 0
    for panel, (x0, x1, z0, z1) in zip(panels, boxes):
        fd, ft = panel["frame_depth"], panel["frame_thickness"] or 0.0
        if panel["operation"] in params.WINDOW_SLIDES:
            y0 = max(0.0, d / 2 - fd) if track % 2 == 0 else min(d - fd, d / 2)
            track += 1
        else:
            y0 = (d - fd) / 2
        y1 = y0 + fd
        if ft > 0:
            parts += [((x0, x0 + ft, y0, y1, z0, z1), "framing"),
                      ((x1 - ft, x1, y0, y1, z0, z1), "framing"),
                      ((x0 + ft, x1 - ft, y0, y1, z0, z0 + ft), "framing"),
                      ((x0 + ft, x1 - ft, y0, y1, z1 - ft, z1), "framing")]
        g, yc = params.GLASS_THICKNESS, (y0 + y1) / 2
        parts.append(((x0 + ft, x1 - ft, yc - g / 2, yc + g / 2, z0 + ft, z1 - ft), "glazing"))
    return [(tuple(float(v) for v in b), role) for b, role in parts if _valid(b)]
