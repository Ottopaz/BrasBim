# SPDX-License-Identifier: LGPL-3.0-or-later
"""Forma livre na planta (``spec/elementos/forma-livre.md`` §7), sem Qt: a silhueta
gravada na representação ``FootPrint``, com os mesmos papéis dos objetos
(``objects/plan.py``): ``object_fill`` (contorno com fundo), ``object`` (furo),
``object_above`` (peça toda acima do plano de corte: tracejado), ``plant``/``plant_fill``
(vegetação) e ``object_box`` (caixa que envolve, só para a escolha).
"""

from __future__ import annotations

import ifcopenshell.util.placement
import numpy as np

from brasbim.core.freeform import elements, mesh


def _matrix(storey, element) -> np.ndarray:
    m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
    s = (ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)
         if storey.ObjectPlacement is not None else np.eye(4))
    return np.linalg.inv(s) @ m


def _apply(m: np.ndarray, points) -> tuple:
    return tuple((float(v[0]), float(v[1]))
                 for v in (m @ np.array([x, y, 0.0, 1.0]) for x, y in points))


def _signed_area(ring) -> float:
    return 0.5 * sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
                     - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))


def shapes(doc, element, storey, cut: float | None = None) -> list:
    """Formas da peça no pavimento. Contorno anti-horário é a silhueta (com fundo);
    horário é furo."""
    from brasbim.core.plan import Shape

    owner = element.GlobalId
    state = elements.read_state(doc, element)
    m = _matrix(storey, element)
    b = mesh.bounds(state["parts"])
    above = cut is not None and float(m[2, 3]) + b[4] > cut + 1e-6
    plant = state["category"] == "vegetation"
    out = []
    for ring in elements.footprint(element):
        solid = _signed_area(ring) > 0
        if above:
            role = "object_above"
        elif plant:
            role = "plant_fill" if solid else "plant"
        else:
            role = "object_fill" if solid else "object"
        out.append(Shape(owner, role, _apply(m, ring), True))
    box = [(b[0], b[2]), (b[1], b[2]), (b[1], b[3]), (b[0], b[3])]
    out.append(Shape(owner, "object_box", _apply(m, box), True))
    return out
