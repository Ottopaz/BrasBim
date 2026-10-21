# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho importado (DXF/DWG) como referência 2D na planta
(``spec/ui/22-importar-desenho.md`` §3).

Uma anotação por camada do arquivo de origem, com as linhas já em metros e no sistema do
pavimento::

    {"name": "Levantamento – CURVAS", "source": "topo.dwg", "layer": "CURVAS",
     "lines": [{"points": [[x, y], ...], "closed": false, "z": 101.0 | null}, ...],
     "texts": [{"at": [x, y], "text": "101,50", "height": 0.25, "angle": 0.0}, ...],
     "points": [{"at": [x, y], "z": 101.5 | null}, ...]}

``z`` é a cota que a linha (ou o ponto) trazia no arquivo, quando constante: as curvas
de nível de um levantamento costumam vir com ela (§4).
"""

from __future__ import annotations

import itertools
import math

from brasbim.core.annotations import base
from brasbim.core.annotations.prims import Prims, Stroke, Text
from brasbim.core.document import OpError

WEIGHT = 0.13  # mm: traço fino da referência
CROSS = 1.0  # mm de papel: meia cruz do ponto


def _validate(state) -> None:
    for line in state["lines"]:
        if len(line["points"]) < 2:
            raise OpError("linha do desenho importado com menos de 2 pontos")


def _build(doc, storey, state) -> Prims:
    from brasbim.core import storeys

    out = Prims()
    for line in state["lines"]:
        out.strokes.append(Stroke(tuple(tuple(p) for p in line["points"]), line["closed"],
                                  WEIGHT))
    for t in state["texts"]:
        out.texts.append(Text(tuple(t["at"]), t["text"], t["height"], t["angle"], "left",
                              "bottom"))
    k = storeys.paper(storey, CROSS)
    for p in state["points"]:
        x, y = p["at"]
        out.strokes += [Stroke(((x - k, y), (x + k, y)), False, WEIGHT),
                        Stroke(((x, y - k), (x, y + k)), False, WEIGHT)]
    return out


def _mapped(state, fn, turn, mirrored, moving) -> dict:
    def m(p):
        q = fn(tuple(p))
        return [float(q[0]), float(q[1])]

    return {
        "lines": [{**line, "points": [m(p) for p in line["points"]]}
                  for line in state["lines"]],
        "texts": [{**t, "at": m(t["at"]),
                   "angle": (-t["angle"] + turn) % 360.0 if mirrored
                   else (t["angle"] + turn) % 360.0} for t in state["texts"]],
        "points": [{**p, "at": m(p["at"])} for p in state["points"]],
    }


REFERENCE = base.Kind("reference2d", "desenho importado", None, "DesenhoImportado",
                      {"name": "Desenho importado", "source": "", "layer": "",
                       "lines": [], "texts": [], "points": []},
                      _build, _mapped, validate=_validate, compact=True)
base.register_kind(REFERENCE)


def is_reference(element) -> bool:
    kind = base.kind_of(element)
    return kind is not None and kind.prefix == "reference2d"


def lines_near(owners, p, tol: float) -> list[tuple[float, str, int, dict]]:
    """Linhas de desenho importado perto de ``p``, da mais próxima: (distância,
    GlobalId, índice, linha). ``owners``: [(GlobalId, estado)]."""
    out = []
    for gid, state in owners:
        for i, line in enumerate(state["lines"]):
            pts = line["points"]
            segs = list(itertools.pairwise(pts))
            if line["closed"]:
                segs.append((pts[-1], pts[0]))
            d = min((_seg_dist(p, a, b) for a, b in segs), default=math.inf)
            if d <= tol:
                out.append((d, gid, i, line))
    return sorted(out, key=lambda e: e[0])


def _seg_dist(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 < 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * dx
                                                       + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
