# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exclusão de vários elementos numa transação (spec/ui 01 §5.1, spec/ui 10 §4.1)."""

from __future__ import annotations

from brasbim.core.annotations import commands as ac
from brasbim.core.document import Document
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import doors
from brasbim.core.ops import Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.structure import slab_openings
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings


def delete_elements(doc: Document, gids) -> tuple[Transaction, dict[str, int]]:
    """Esquadrias antes das paredes, depois pilares, vigas, lajes e anotações; operações
    repetidas (abertura, junção entre duas paredes excluídas) entram uma vez. Devolve a
    transação e quantas portas e janelas saem junto com as paredes
    (``{"IfcDoor": n, "IfcWindow": m}``)."""
    entities = [doc.find(g) for g in sorted(gids)]
    entities = [e for e in entities if e is not None]
    door_list = [e for e in entities if e.is_a("IfcDoor") or e.is_a("IfcWindow")]
    wall_list = [e for e in entities if e.is_a("IfcWall")]
    ops, seen, cascade = [], set(), {"IfcDoor": 0, "IfcWindow": 0}

    def add(op_list) -> None:
        for op in op_list:
            if (op.op, op.id) not in seen:
                seen.add((op.op, op.id))
                ops.append(op)

    for door in door_list:
        add(fc.delete_door(doc, door).ops)
    for wall in wall_list:
        for opening in openings.of_wall(wall):
            for r in opening.HasFillings:
                element = r.RelatedBuildingElement
                cls = doors.kind_of(element)[0] if (element.is_a("IfcDoor")
                                                     or element.is_a("IfcWindow")) else None
                if cls and element not in door_list and doors.is_parametric(element):
                    cascade[cls] += 1
        add(cmd.delete_wall(doc, wall).ops)
    for element in entities:
        if ac.is_annotation(element):
            ops += ac.delete_ops(doc, element)
        elif sc.is_structure(element) or slab_openings.is_slab_opening(element):
            add(sc.delete_ops(doc, element))  # a laje já leva as aberturas dela
    label = "Excluir"
    if len(entities) == 1 and door_list:
        label = f"Excluir {fc.kind(door_list[0]).noun}"
    elif len(entities) == 1 and sc.is_structure(entities[0]):
        label = f"Excluir {sc.ELEMENTS[entities[0].is_a()][2]}"
    return Transaction(label, ops), cascade
