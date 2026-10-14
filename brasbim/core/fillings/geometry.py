# SPDX-License-Identifier: LGPL-3.0-or-later
"""Peças do corpo das esquadrias como caixas no sistema local (``porta.md`` §6.2).

Sistema local da porta: x ao longo do vão (0 a largura), y atravessando a parede (o marco
ocupa 0 a ``d``; a folha abre para +y), z para cima a partir da base do vão. Uma caixa é
``(x0, x1, y0, y1, z0, z1)``.
"""

from __future__ import annotations

Box = tuple[float, float, float, float, float, float]

# Folhas desenhadas fechadas: em que lado da profundidade do marco ficam.
_FLUSH_OPENING_SIDE = ("SWINGING", "FIXEDPANEL", "FOLDING", "ROLLINGUP")


def _valid(box: Box) -> bool:
    x0, x1, y0, y1, z0, z1 = box
    return x1 - x0 > 1e-9 and y1 - y0 > 1e-9 and z1 - z0 > 1e-9


def door_boxes(width: float, height: float, depth: float, faces: tuple[float, float],
               lining: dict, panels: list[dict]) -> list[Box]:
    """Marco, soleira, guarnições e folhas de uma porta.

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
        boxes.append((x, x + pw, y0, y1, z0, z1))
        x += pw
    return [tuple(float(v) for v in b) for b in boxes if _valid(b)]
