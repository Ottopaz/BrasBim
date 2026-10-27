# SPDX-License-Identifier: LGPL-3.0-or-later
"""Derivação dos ambientes e das anotações (spec/ui 13): roda depois da derivação dos
elementos, para ver a geometria nova deles (``doc.changed``).

- Ambiente: refeito quando ele muda, ou quando muda uma laje, um tipo de laje ou um
  pavimento (o pé-direito calculado depende deles), ou uma parede ou um pilar (área
  líquida). O ambiente pelo cômodo (com ``seed``) refaz antes o contorno pelas paredes.
- Anotação: refeita quando ela muda, quando muda a escala ou a cota do pavimento dela,
  quando muda um elemento a que uma cota está presa (``depends``) e, na cota de nível,
  quando muda uma laje.
"""

from __future__ import annotations

import ifcopenshell.util.element

from brasbim.core.annotations import base, dimensions, spaces
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import register_derive

_SLAB_LIKE = ("IfcSlab", "IfcSlabType", "IfcBuildingStorey")
_WALL_LIKE = ("IfcWall", "IfcWallType", "IfcColumn", "IfcColumnType")


def derive(doc: Document, dirty: set[str]) -> None:
    touched = set(dirty) | set(doc.changed)
    entities = [doc.find(g) for g in sorted(touched)]
    # Um GlobalId que sumiu pode ser de uma laje excluída: na dúvida, refaz.
    slabs_changed = any(e is None or any(e.is_a(c) for c in _SLAB_LIKE) for e in entities)
    walls_changed = any(e is None or any(e.is_a(c) for c in _WALL_LIKE) for e in entities)
    walls = {}  # pavimento → rooms.walls_of, calculado uma vez
    for space in sorted(doc.ifc.by_type("IfcSpace"), key=lambda s: s.GlobalId):
        if space.GlobalId in touched or slabs_changed or walls_changed:
            try:
                storey = spaces.storey_of(space)
                if storey is not None and spaces.read_state(space)["seed"] is not None:
                    from brasbim.core.structure import rooms

                    if storey.GlobalId not in walls:
                        walls[storey.GlobalId] = rooms.walls_of(doc, storey)
                    spaces.refit(doc, space, walls[storey.GlobalId])
                spaces.rebuild(doc, space)
            except OpError:
                continue
    storeys_touched = {g for g in touched
                       if (e := doc.find(g)) is not None and e.is_a("IfcBuildingStorey")}
    for element in sorted(doc.ifc.by_type("IfcAnnotation"), key=lambda e: e.GlobalId):
        kind = base.kind_of(element)
        if kind is None:
            continue
        if kind.compact:  # desenho importado: não depende de nada além do pavimento, e a
            # criação/edição já gravou a geometria (o estado pode ter muitos MB)
            storey = ifcopenshell.util.element.get_container(element)
            if storey is not None and storey.GlobalId in storeys_touched:
                base.rebuild(doc, element)
            continue
        state = base.read_state(element)
        needed = (element.GlobalId in touched or state["storey"] in storeys_touched
                  or bool(kind.depends(state) & touched)
                  or (kind.prefix == "level_mark" and slabs_changed))
        if not needed:
            continue
        if kind.prefix == "dimension":
            dimensions.refresh(doc, element)
        elif kind.prefix == "radius_dim":
            from brasbim.core.annotations import drawing2d

            drawing2d.refresh_radius(doc, element)
        base.rebuild(doc, element)


def annotations_of(storey) -> list:
    """Anotações e ambientes do pavimento, em ordem de GlobalId."""
    return sorted((e for e in ifcopenshell.util.element.get_decomposition(storey)
                   if e.is_a("IfcAnnotation") or e.is_a("IfcSpace")),
                  key=lambda e: e.GlobalId)


register_derive(derive)
