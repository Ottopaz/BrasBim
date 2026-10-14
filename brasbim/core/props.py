# SPDX-License-Identifier: LGPL-3.0-or-later
"""Psets, quantidades e representações de um produto, com GlobalIds derivados.

Usado por todos os elementos: cada Pset/Qto recebe GlobalId determinístico a partir do
dono (``guid.derived``), para que refazer e reaplicar operações produzam o mesmo IFC.
"""

from __future__ import annotations

import ifcopenshell.api.pset
import ifcopenshell.util.element

from brasbim.core import guid

# Ordem das representações dentro de IfcProductDefinitionShape. Body vem antes de Profile:
# leitores que pegam a primeira representação 3D (ex.: ifcopenshell.geom) usam o corpo.
_ORDER = ("Axis", "Body", "Profile", "FootPrint")


def ensure_pset(doc, product, name: str):
    """Pset ``name`` do próprio produto (ocorrência ou tipo), criado se faltar."""
    found = ifcopenshell.util.element.get_pset(product, name, should_inherit=False)
    if found:
        return doc.ifc.by_id(found["id"])
    pset = ifcopenshell.api.pset.add_pset(doc.ifc, product=product, name=name)
    guid.stamp(pset, product.GlobalId, f"pset/{name}")
    if pset.DefinesOccurrence:
        guid.stamp(pset.DefinesOccurrence[0], product.GlobalId, f"rel/{name}")
    return pset


def write_pset(doc, product, name: str, values: dict) -> None:
    """Grava ``values`` no Pset e apaga as propriedades que não estão em ``values``."""
    pset = ensure_pset(doc, product, name)
    current = ifcopenshell.util.element.get_pset(product, name, should_inherit=False) or {}
    stale = {k: None for k in current if k not in ("id", *values)}
    ifcopenshell.api.pset.edit_pset(doc.ifc, pset=pset, properties={**stale, **values})


def write_qto(doc, product, name: str, quantities: dict) -> None:
    found = ifcopenshell.util.element.get_pset(product, name, should_inherit=False)
    if found:
        qto = doc.ifc.by_id(found["id"])
    else:
        qto = ifcopenshell.api.pset.add_qto(doc.ifc, product=product, name=name)
        guid.stamp(qto, product.GlobalId, f"qto/{name}")
        guid.stamp(qto.DefinesOccurrence[0], product.GlobalId, f"rel/{name}")
    ifcopenshell.api.pset.edit_qto(doc.ifc, qto=qto, properties=quantities)


def representation(product, identifier: str):
    if product.Representation is None:
        return None
    for rep in product.Representation.Representations:
        if rep.RepresentationIdentifier == identifier:
            return rep
    return None


def replace_representation(doc, product, identifier: str, new_rep) -> None:
    """Troca (ou acrescenta) a representação ``identifier`` e apaga a antiga."""
    shape = product.Representation
    if shape is None:
        product.Representation = doc.ifc.createIfcProductDefinitionShape(None, None, [new_rep])
        return
    reps = [r for r in shape.Representations if r.RepresentationIdentifier != identifier]
    old = [r for r in shape.Representations if r.RepresentationIdentifier == identifier]
    reps.append(new_rep)
    reps.sort(key=lambda r: _ORDER.index(r.RepresentationIdentifier)
              if r.RepresentationIdentifier in _ORDER else len(_ORDER))
    shape.Representations = reps
    keep = set(doc.ifc.by_type("IfcGeometricRepresentationContext"))
    for rep in old:
        ifcopenshell.util.element.remove_deep2(doc.ifc, rep, do_not_delete=keep)
