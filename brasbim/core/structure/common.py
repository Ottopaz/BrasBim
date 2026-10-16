# SPDX-License-Identifier: LGPL-3.0-or-later
"""O que pilar, viga e laje fazem do mesmo jeito: tipo e material, pavimento, Pset comum,
topo ligado a pavimento e elementos de outra origem.

**Outra origem** (sem o Pset próprio do BrasBim; laje.md §3.1, pilar.md PI13, viga.md
VI12): o corpo não é refeito. ``foreign`` guarda a representação (``fragment.dump``) e
``placement`` o posicionamento (``rel``: a quem é relativo; ``location``, ``axis`` e
``ref``: o ``IfcAxis2Placement3D``), para que excluir e desfazer restaure o elemento e
para que mover e girar troquem só o posicionamento. Nos elementos do BrasBim, os dois
são ``None``.
"""

from __future__ import annotations

import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
import ifcopenshell.util.element

from brasbim.core import fragment, guid, props
from brasbim.core.document import Document, OpError

TOP_MODES = ("storey", "fixed")
DEFAULT_TOP = 2.80  # altura fixa do pilar e cota fixa da viga (pilar.md §3.1, viga.md §3.1)
_PSET_TOP = {"storey": "PAVIMENTO", "fixed": "FIXO"}


def gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def elevation(doc: Document, storey_id: str) -> float:
    return float(doc.get(storey_id, "IfcBuildingStorey").Elevation or 0.0)


def top_from_pset(value: str | None) -> str:
    return {v: k for k, v in _PSET_TOP.items()}.get(value, "fixed")


def top_to_pset(mode: str) -> str:
    return _PSET_TOP[mode]


def validate_top(state: dict) -> None:
    if state["top_mode"] not in TOP_MODES:
        raise OpError(f"tipo de topo inválido: {state['top_mode']!r}")
    if state["top_mode"] == "storey" and not state.get("top_storey"):
        raise OpError("topo ligado a pavimento exige o pavimento do topo")


def default_top(doc: Document, storey_id: str) -> dict:
    """Topo no pavimento imediatamente acima, se houver (pilar.md §3.1, viga.md §3.1)."""
    above = doc.storey_above(doc.get(storey_id, "IfcBuildingStorey"))
    if above is None:
        return {"top_mode": "fixed", "top_storey": None}
    return {"top_mode": "storey", "top_storey": above.GlobalId}


# --- tipo, pavimento e Psets -------------------------------------------------------------


def assign_type(doc: Document, element, element_type) -> None:
    if ifcopenshell.util.element.get_type(element) != element_type:
        rel = ifcopenshell.api.type.assign_type(
            doc.ifc, related_objects=[element], relating_type=element_type)
        guid.stamp(rel, element_type.GlobalId, "types")


def assign_container(doc: Document, element, storey) -> None:
    if ifcopenshell.util.element.get_container(element) != storey:
        rel = ifcopenshell.api.spatial.assign_container(
            doc.ifc, products=[element], relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")


def stamp_material(element) -> None:
    rel = next(r for r in element.HasAssociations if r.is_a("IfcRelAssociatesMaterial"))
    guid.stamp(rel, element.GlobalId, "material")


def common_defaults(element_type) -> dict:
    """``Pset_*Common`` padrão: código = nome do tipo, nova, estrutural, interna."""
    return {"Reference": element_type.Name if element_type else None, "Status": "NEW",
            "LoadBearing": True, "IsExternal": False}


def read_common(element, pset_name: str, element_type, foreign: bool) -> dict:
    """Pset comum sem o que é padrão (outra origem: o Pset inteiro, como está)."""
    values = ifcopenshell.util.element.get_pset(element, pset_name, should_inherit=False) or {}
    values = {k: v for k, v in values.items() if k != "id"}
    if isinstance(values.get("Status"), (list, tuple)):
        values["Status"] = values["Status"][0] if values["Status"] else None
    if foreign:
        return values
    defaults = common_defaults(element_type)
    return {k: v for k, v in values.items() if defaults.get(k) != v}


def write_common(doc: Document, element, pset_name: str, element_type, common: dict,
                 foreign: bool) -> None:
    values = dict(common or {}) if foreign else {**common_defaults(element_type),
                                                  **(common or {})}
    values = {k: v for k, v in values.items() if v is not None}
    if values.get("Status") is not None:
        values["Status"] = [values["Status"]]
    if values or ifcopenshell.util.element.get_pset(element, pset_name, should_inherit=False):
        props.write_pset(doc, element, pset_name, values)


def next_name(doc: Document, ifc_class: str, prefix: str) -> str:
    """Próximo nome livre: P1, P2… (pilar.md §3.1) ou V1, V2… (viga.md §3.1)."""
    used = {e.Name for e in doc.ifc.by_type(ifc_class)}
    n = 1
    while f"{prefix}{n}" in used:
        n += 1
    return f"{prefix}{n}"


# --- outra origem --------------------------------------------------------------------


def _vector(direction, default) -> list[float]:
    if direction is None:
        return list(default)
    return [float(c) for c in direction.DirectionRatios]


def read_placement(element) -> dict | None:
    placement = element.ObjectPlacement
    if placement is None or not placement.is_a("IfcLocalPlacement"):
        return None
    rp = placement.RelativePlacement
    return {"rel": fragment.dump(element.file, placement.PlacementRelTo),
            "location": [float(c) for c in rp.Location.Coordinates],
            "axis": _vector(rp.Axis, (0.0, 0.0, 1.0)),
            "ref": _vector(rp.RefDirection, (1.0, 0.0, 0.0))}


def read_foreign(element) -> dict:
    return {"shape": fragment.dump(element.file, element.Representation)}


def write_placement(doc: Document, element, placement: dict) -> None:
    ifc = doc.ifc
    location = [*placement["location"], 0.0, 0.0][:3]
    rp = ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint(tuple(float(c) for c in location)),
        ifc.createIfcDirection(tuple(float(c) for c in placement["axis"])),
        ifc.createIfcDirection(tuple(float(c) for c in placement["ref"])))
    rel = fragment.load(ifc, placement["rel"])
    old = element.ObjectPlacement
    if old is None:
        element.ObjectPlacement = ifc.createIfcLocalPlacement(rel, rp)
        return
    previous = old.RelativePlacement
    old.PlacementRelTo, old.RelativePlacement = rel, rp
    ifcopenshell.util.element.remove_deep2(ifc, previous)


def write_foreign(doc: Document, element, state: dict) -> None:
    """Grava o elemento de outra origem: corpo (só ao criar) e posicionamento."""
    if element.Representation is None and state["foreign"]["shape"] is not None:
        element.Representation = fragment.load(doc.ifc, state["foreign"]["shape"])
    if state.get("placement") is not None:
        write_placement(doc, element, state["placement"])


def remove(doc: Document, element) -> None:
    """Apaga o elemento. O corpo de outra origem sai com o que só ele usa, sem levar o
    perfil, que pode ser do tipo."""
    doc.cut_victims.update(r.RelatingElement.GlobalId
                           for r in getattr(element, "IsInterferedByElements", ()) or ()
                           if r.is_a("IfcRelInterferesElements"))
    for rel in list(getattr(element, "InterferesElements", ()) or ()) + list(
            getattr(element, "IsInterferedByElements", ()) or ()):
        doc.ifc.remove(rel)
    shape = element.Representation
    element.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=element)
    if shape is not None:
        fragment.remove(doc.ifc, shape)


def placement_moved(placement: dict, fn, angle: float = 0.0) -> dict:
    """Posicionamento levado por ``fn`` (translação ou rotação de ``angle`` radianos em
    planta). Vale para posicionamento relativo ao pavimento, sem rotação dele."""
    x, y, *z = placement["location"]
    nx, ny = fn((x, y))
    c, s = math.cos(angle), math.sin(angle)

    def turn(v):
        return [c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]]

    return {**placement, "location": [nx, ny, *z], "axis": turn(placement["axis"]),
            "ref": turn(placement["ref"])}


def relative_to_storey(element, storey) -> bool:
    placement = element.ObjectPlacement
    return (placement is not None and placement.is_a("IfcLocalPlacement")
            and placement.PlacementRelTo == storey.ObjectPlacement)
