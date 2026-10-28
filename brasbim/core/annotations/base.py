# SPDX-License-Identifier: LGPL-3.0-or-later
"""Anotações da planta (``IfcAnnotation``, spec/ui 13 §4–§7): o que todas têm em comum.

Cada tipo (``Kind``) tem um prefixo de operações (``dimension``, ``level_mark``, ``text``,
``line2d``, ``hatch``, ``north``), o ``PredefinedType``/``ObjectType`` do IFC, os campos
padrão e duas funções: ``build`` (estado → primitivas, ``prims``) e ``mapped`` (estado
levado por uma transformação da planta).

Operações: ``<prefixo>.create`` / ``.delete`` (data: estado completo) e ``<prefixo>.edit``
(before/after: campos alterados). O estado fica no Pset ``BrasBim_Anotacao``
(``Tipo`` e ``Parametros``, este em JSON); ``storey`` é a contenção. A geometria
(representação ``Annotation``) é derivada e refeita por ``rebuild``.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.annotations import prims
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Anotacao"


@dataclass(frozen=True)
class Kind:
    prefix: str
    noun: str
    predefined: str | None
    object_type: str | None
    defaults: dict
    build: Callable  # (doc, storey, state) -> prims.Prims
    mapped: Callable  # (state, fn, angle_deg, mirrored, moving: set[str]) -> dict
    depends: Callable = field(default=lambda state: set())  # GlobalIds anotados
    validate: Callable = field(default=lambda state: None)
    # Linhas como IfcIndexedPolyCurve (desenho importado, com milhares de vértices).
    compact: bool = False


KINDS: dict[str, Kind] = {}


def register_kind(kind: Kind) -> None:
    KINDS[kind.prefix] = kind

    def create(doc: Document, op: Op) -> set[str]:
        if doc.find(op.id) is not None:
            raise OpError(f"GlobalId {op.id} já existe")
        element = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
        element.GlobalId = op.id
        element.PredefinedType = kind.predefined
        element.ObjectType = kind.object_type
        try:
            write(doc, element, kind, {**copy.deepcopy(kind.defaults), **op.data})
        except Exception:
            remove(doc, element)
            raise
        return {op.id}

    def delete(doc: Document, op: Op) -> set[str]:
        remove(doc, doc.get(op.id, "IfcAnnotation"))
        return {op.id}

    def edit(doc: Document, op: Op) -> set[str]:
        element = doc.get(op.id, "IfcAnnotation")
        state = read_state(element)
        check_before(op, state)
        state.update(copy.deepcopy(op.after or {}))
        write(doc, element, kind, state)
        return {op.id}

    register_inverse_pair(f"{kind.prefix}.create", create, f"{kind.prefix}.delete", delete)
    register(f"{kind.prefix}.edit", edit, invert_swap)


def kind_of(element) -> Kind | None:
    if element is None or not element.is_a("IfcAnnotation"):
        return None
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    return KINDS.get(values.get("Tipo"))


def read_state(element) -> dict:
    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"anotação {element.GlobalId} sem os parâmetros do BrasBim")
    storey = ifcopenshell.util.element.get_container(element)
    return {"storey": storey.GlobalId if storey else None, **json.loads(values["Parametros"])}


def _dump(state: dict) -> str:
    return json.dumps({k: v for k, v in state.items() if k != "storey"}, sort_keys=True,
                      ensure_ascii=False)


def write(doc: Document, element, kind: Kind, state: dict) -> None:
    kind.validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    if ifcopenshell.util.element.get_container(element) != storey:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[element],
                                                        relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")
    if element.ObjectPlacement is None or element.ObjectPlacement.PlacementRelTo \
            != storey.ObjectPlacement:
        old = element.ObjectPlacement
        element.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement)
        if old is not None:
            ifcopenshell.util.element.remove_deep2(doc.ifc, old)
    props.write_pset(doc, element, PSET, {
        "Tipo": doc.ifc.createIfcLabel(kind.prefix),
        "Parametros": doc.ifc.createIfcText(_dump(state))})
    rebuild(doc, element)


def rebuild(doc: Document, element) -> None:
    """Geometria a partir do estado (o que é anotado pode ter mudado)."""
    kind = kind_of(element)
    if kind is None:
        return
    state = read_state(element)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    prims.write(doc, element, kind.build(doc, storey, state), compact=kind.compact)
    doc.changed.add(element.GlobalId)


# Tipos cujas primitivas só dependem dos próprios parâmetros e da escala do pavimento:
# guardadas entre uma montagem da planta e a outra (desenho importado com dezenas de
# milhares de linhas, spec/ui 22 §7). Cotas, etiquetas e afins leem o resto do modelo.
CACHED = {"reference2d"}


def build(doc: Document, element) -> prims.Prims:
    """Primitivas da anotação, para a planta."""
    kind = kind_of(element)
    if kind is None:
        return prims.Prims()
    if kind.prefix not in CACHED:
        state = read_state(element)
        return kind.build(doc, doc.get(state["storey"], "IfcBuildingStorey"), state)
    from brasbim.core import storeys

    values = ifcopenshell.util.element.get_pset(element, PSET, should_inherit=False) or {}
    storey = ifcopenshell.util.element.get_container(element)
    key = (values.get("Parametros"), storey.GlobalId if storey else None,
           storeys.scale(storey) if storey else None)
    cache = doc.__dict__.setdefault("_prims_cache", {})
    found = cache.get(element.GlobalId)
    if found is None or found[0] != key:
        state = read_state(element)
        found = cache[element.GlobalId] = (key, kind.build(
            doc, doc.get(state["storey"], "IfcBuildingStorey"), state))
    return found[1]


def remove(doc: Document, element) -> None:
    prims._drop(doc, element)
    ifcopenshell.api.root.remove_product(doc.ifc, product=element)


def set_cache(doc: Document, element, state: dict) -> None:
    """Grava no Pset campos derivados (ex.: a última posição de um ponto preso, §4.3),
    sem operação; a derivação é a mesma em qualquer reaplicação."""
    pset = props.ensure_pset(doc, element, PSET)
    for prop in pset.HasProperties or ():
        if prop.Name == "Parametros":
            prop.NominalValue = doc.ifc.createIfcText(_dump(state))
