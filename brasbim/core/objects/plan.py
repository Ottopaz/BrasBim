# SPDX-License-Identifier: LGPL-3.0-or-later
"""Objetos paramétricos na planta (``spec/elementos/objeto-parametrico.md`` §7), sem Qt.

Papéis (``plan.Shape.role``): ``object`` (traço do símbolo), ``object_fill`` (contorno
fechado com fundo, que cobre o que fica por baixo), ``object_above`` (objeto todo acima
do plano de corte: tracejado) e ``object_box`` (caixa que envolve, só para a escolha).
A vegetação usa ``plant`` e ``plant_fill`` e é desenhada por cima das paredes. Os
aninhados respondem pelo objeto de fora (``owner``).

O símbolo **automático** é, para cada peça, o contorno visto de cima; os contornos são
unidos por altura do topo e empilhados do mais baixo para o mais alto, cada um com fundo.
"""

from __future__ import annotations

import logging

import ifcopenshell.util.placement
import numpy as np

from brasbim.core import clip
from brasbim.core.document import OpError
from brasbim.core.objects import definition as od
from brasbim.core.objects import elements

log = logging.getLogger(__name__)

def _matrix(storey, element) -> np.ndarray:
    m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
    s = (ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)
         if storey.ObjectPlacement is not None else np.eye(4))
    return np.linalg.inv(s) @ m


def _apply(m: np.ndarray, points, mirror: bool):
    k = -1.0 if mirror else 1.0
    out = []
    for x, y in points:
        v = m @ np.array([k * x, y, 0.0, 1.0])
        out.append((float(v[0]), float(v[1])))
    return tuple(out)


def local_symbol(built) -> list[tuple[list, bool, bool]]:
    """(pontos, fechado, com fundo) no sistema local, antes do espelho."""
    defn = built.definition
    if (defn.get("symbol") or {}).get("mode") == "drawn":
        return [(st.points, st.closed, st.fill) for st in built.strokes]
    levels: dict[float, list] = {}
    for s in built.solids:
        if s.void:
            continue
        top = round(od.z_range(s)[1], 2)
        levels.setdefault(top, []).append(list(od.footprint(s)))
    out = []
    for top in sorted(levels):
        for ring in clip.union(levels[top]):
            out.append((ring, True, True))
    return out


def _z_min(m: np.ndarray, built) -> float | None:
    if built.box is None:
        return None
    return float(m[2, 3] + built.box[4])


def shapes(doc, element, storey, cut: float | None = None) -> list:
    """Formas do objeto (e dos aninhados) no pavimento."""
    from brasbim.core.plan import Shape

    owner = element.GlobalId
    out = []
    plant = elements.kind_of(element) == "object:vegetation"
    stack = [element]
    while stack:
        e = stack.pop(0)
        try:
            built = elements.built_of(doc, e)
        except OpError as error:  # objeto que não se calcula fica fora da planta
            log.warning("objeto %s sem planta: %s", e.GlobalId, error)
            continue
        m = _matrix(storey, e)
        z0 = _z_min(m, built)
        above = cut is not None and z0 is not None and z0 > cut + 1e-6
        for points, closed, fill in local_symbol(built):
            if above:
                role = "object_above"
            elif plant:
                role = "plant_fill" if fill and closed else "plant"
            else:
                role = "object_fill" if fill and closed else "object"
            out.append(Shape(owner, role, _apply(m, points, built.mirror), closed))
        if e is element and built.box is not None:
            x0, x1, y0, y1, _, _ = built.box
            box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            out.append(Shape(owner, "object_box", _apply(m, box, built.mirror), True))
        stack += elements.parts_of(e)
    return out


def label(doc, element, storey, height: float):
    """Etiqueta com o código do tipo no centro do objeto (Exibir > Etiquetas de objetos)."""
    from brasbim.core.plan import Label

    code = elements.code_of(doc, element)
    if not code:
        return None
    built = elements.built_of(doc, element)
    if built.box is None:
        return None
    x0, x1, y0, y1, _, _ = built.box
    (at,) = _apply(_matrix(storey, element), [((x0 + x1) / 2, (y0 + y1) / 2)], built.mirror)
    return Label(element.GlobalId, at, code, "", "object", 0.0, height)
