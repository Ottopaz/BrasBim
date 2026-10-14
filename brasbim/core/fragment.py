# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cópia de um pedaço do grafo IFC em JSON, para guardar dentro de uma operação.

Serve para dados de outra origem que o BrasBim não sabe regenerar, mas que uma operação
apaga e o desfazer precisa restaurar sem perda (ex.: o corpo de uma porta importada que
é convertida em paramétrica, ``porta.md`` §6.6).

A cópia segue as referências diretas e para nas entidades compartilhadas (``_SHARED``:
objetos com GlobalId, contextos, mapas de representação, posicionamentos de outros
produtos e estilos), que são gravadas pelo número da entidade no arquivo e continuam
existindo. Os ``IfcStyledItem`` que apontam para um item copiado vão junto com ele.

Formato: entidade = ``{"class": ..., "attributes": {...}, "styles": [...]}``; entidade
compartilhada = ``{"ref": número}``; valor tipado = ``{"type": ..., "value": ...}``;
agregados = listas.
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.util.element

_SHARED = ("IfcRoot", "IfcRepresentationContext", "IfcRepresentationMap",
           "IfcObjectPlacement", "IfcPresentationStyle", "IfcOwnerHistory")


def _shared(entity) -> bool:
    return any(entity.is_a(c) for c in _SHARED)


def _explicit(ifc, entity) -> list[str]:
    decl = ifcopenshell.schema_by_name(ifc.schema).declaration_by_name(entity.is_a())
    return [a.name() for a, derived in zip(decl.all_attributes(), decl.derived(), strict=True)
            if not derived]


def dump(ifc, value):
    """Valor ou entidade → estrutura JSON."""
    if isinstance(value, ifcopenshell.entity_instance):
        if value.id() == 0:  # tipo definido dentro de um SELECT, ex.: IfcLengthMeasure
            return {"type": value.is_a(), "value": dump(ifc, value.wrappedValue)}
        if _shared(value):
            return {"ref": value.id()}
        node = {"class": value.is_a(),
                "attributes": {n: dump(ifc, getattr(value, n)) for n in _explicit(ifc, value)}}
        styled = getattr(value, "StyledByItem", None) or []
        if styled:
            node["styles"] = [{"name": s.Name, "styles": dump(ifc, s.Styles)} for s in styled]
        return node
    if isinstance(value, (list, tuple)):
        return [dump(ifc, v) for v in value]
    return value


def load(ifc, data):
    """Recria no arquivo o que ``dump`` gravou; devolve a entidade (ou o valor)."""
    if isinstance(data, list):
        return [load(ifc, v) for v in data]
    if not isinstance(data, dict):
        return data
    if "ref" in data:
        return ifc.by_id(data["ref"])
    if "type" in data:
        return ifc.create_entity(data["type"], load(ifc, data["value"]))
    entity = ifc.create_entity(data["class"], **{k: load(ifc, v)
                                                  for k, v in data["attributes"].items()})
    for s in data.get("styles", []):
        ifc.create_entity("IfcStyledItem", Item=entity, Styles=load(ifc, s["styles"]),
                          Name=s["name"])
    return entity


def _own(ifc, entity, found: list) -> None:
    """Entidades não compartilhadas alcançáveis a partir de ``entity``."""
    if _shared(entity) or entity in found:
        return
    found.append(entity)
    for value in entity:
        stack = [value]
        while stack:
            v = stack.pop()
            if isinstance(v, (list, tuple)):
                stack.extend(v)
            elif isinstance(v, ifcopenshell.entity_instance) and v.id() != 0:
                _own(ifc, v, found)


def remove(ifc, entity) -> None:
    """Apaga ``entity`` e o que só ela usa, com os estilos dos itens, sem tocar no que é
    compartilhado."""
    own: list = []
    _own(ifc, entity, own)
    for e in own:
        for styled in getattr(e, "StyledByItem", None) or []:
            ifc.remove(styled)
    keep = {e for e in ifc.traverse(entity) if _shared(e)}
    ifcopenshell.util.element.remove_deep2(ifc, entity, do_not_delete=keep)
