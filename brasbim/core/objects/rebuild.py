# SPDX-License-Identifier: LGPL-3.0-or-later
"""Derivação dos objetos paramétricos (``spec/elementos/objeto-parametrico.md`` §5.2).

O tipo que mudou refaz as ocorrências dele (as aninhadas refazem o objeto de fora); a
parede que mudou refaz os objetos presos a ela. Uma ocorrência que não aceita os valores
novos recusa a transação inteira.
"""

from __future__ import annotations

import ifcopenshell.util.element

from brasbim.core.document import Document
from brasbim.core.objects import elements, hosting
from brasbim.core.objects import types as ot
from brasbim.core.ops.base import register_derive


def affected(doc: Document, dirty: set[str]) -> list:
    found = {}
    for gid in dirty:
        entity = doc.find(gid)
        if entity is None:
            continue
        if ot.is_object_type(entity):
            for e in ifcopenshell.util.element.get_types(entity):
                top = elements.parent_of(e)
                if elements.is_object(top) and top.GlobalId not in dirty:
                    found[top.GlobalId] = top
        elif entity.is_a("IfcWall"):
            for e in hosting.hosted_by(doc, entity):
                if e.GlobalId not in dirty:
                    found[e.GlobalId] = e
    return [found[g] for g in sorted(found)]


def derive(doc: Document, dirty: set[str]) -> None:
    for element in affected(doc, dirty):
        elements.write_state(doc, element, elements.read_state(doc, element))


register_derive(derive)
