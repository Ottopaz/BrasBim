# SPDX-License-Identifier: LGPL-3.0-or-later
"""Selecionar semelhantes por critério IFC (``spec/ui/23-precisao.md`` §7), sem Qt."""

from __future__ import annotations

import ifcopenshell.util.element

from brasbim.core import display_layers, intervention
from brasbim.core.document import Document

# (chave, rótulo do menu)
CRITERIA = (
    ("class", "Mesma classe IFC"),
    ("type", "Mesmo tipo"),
    ("predefined", "Mesma classe e tipo predefinido"),
    ("material", "Mesmo material"),
    ("layer", "Mesma camada"),
    ("situation", "Mesma situação"),  # spec/ui 31 §2
)


def _candidates(storey) -> list:
    out = []
    for e in ifcopenshell.util.element.get_decomposition(storey):
        if e.is_a("IfcOpeningElement") or not (
                e.is_a("IfcElement") or e.is_a("IfcAnnotation") or e.is_a("IfcSpace")):
            continue
        out.append(e)
    return out


def _material(element) -> str | None:
    found = ifcopenshell.util.element.get_materials(element)
    return found[0].Name if found else None


def value(doc: Document, element, criterion: str):
    """Valor do critério para o elemento (None: o elemento não tem)."""
    if criterion == "class":
        return element.is_a()
    if criterion == "type":
        t = ifcopenshell.util.element.get_type(element)
        return t.GlobalId if t is not None else None
    if criterion == "predefined":
        predefined = ifcopenshell.util.element.get_predefined_type(element)
        return (element.is_a(), predefined)
    if criterion == "material":
        return _material(element)
    if criterion == "layer":
        return display_layers.layer_of(doc, element)
    if criterion == "situation":
        return intervention.situation_of(doc, element)             if intervention.situable(display_layers.owner(element)) else None
    raise ValueError(f"critério desconhecido: {criterion!r}")


def similar(doc: Document, storey, seeds, criterion: str) -> list[str]:
    """GlobalIds dos elementos visíveis e não bloqueados do pavimento com o mesmo valor
    do critério que algum dos ``seeds`` (união dos valores)."""
    wanted = {value(doc, doc.get(g), criterion) for g in seeds} - {None}
    if not wanted:
        return []
    hidden = display_layers.hidden_ids(doc) | display_layers.locked_ids(doc)
    return sorted(e.GlobalId for e in _candidates(storey)
                  if e.GlobalId not in hidden and value(doc, e, criterion) in wanted)
