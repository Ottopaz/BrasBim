# SPDX-License-Identifier: LGPL-3.0-or-later
"""Aberturas na laje (``IfcOpeningElement`` + ``IfcRelVoidsElement``), spec/ui 12 §3.

Operações: ``slab_opening.create`` / ``.delete`` (data: estado completo) e
``slab_opening.edit`` (before/after: ``outline``).

Estado::

    {"slab": "<GlobalId da IfcSlab>", "outline": [[1, 1], [2, 1], [2, 3], [1, 3]]}

``outline`` em coordenadas do pavimento, anti-horário (``slabs.clean``), guardado no Pset
``BrasBim_AberturaLaje`` (listas ``ContornoX`` e ``ContornoY``). O corpo (o contorno
extrudado do fundo ao topo da laje, com 1 cm a mais de cada lado) e o posicionamento
(relativo ao da laje) são derivados: ``refresh`` os refaz quando a laje é refeita.
"""

from __future__ import annotations

import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import clip, guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_AberturaLaje"
CLEARANCE = 0.01  # m além do fundo e do topo da laje
_LISTS = ("ContornoX", "ContornoY")
STATE_KEYS = ("slab", "outline")


def of_slab(slab) -> list:
    """Aberturas da laje, em ordem de GlobalId (o vão da claraboia é da claraboia)."""
    from brasbim.core.structure import skylights

    return sorted((r.RelatedOpeningElement for r in slab.HasOpenings or ()
                   if not skylights.is_skylight_opening(r.RelatedOpeningElement)),
                  key=lambda o: o.GlobalId)


def host(opening):
    rels = opening.VoidsElements
    return rels[0].RelatingBuildingElement if rels else None


def is_slab_opening(entity) -> bool:
    from brasbim.core.structure import skylights

    if entity is None or not entity.is_a("IfcOpeningElement") or \
            skylights.is_skylight_opening(entity):
        return False
    found = host(entity)
    return found is not None and found.is_a("IfcSlab")


def read_state(opening) -> dict:
    values = ifcopenshell.util.element.get_pset(opening, PSET, should_inherit=False) or {}
    xs, ys = values.get("ContornoX"), values.get("ContornoY")
    if not xs or not ys:
        raise OpError(f"abertura {opening.GlobalId} sem contorno do BrasBim")
    slab = host(opening)
    return {"slab": slab.GlobalId if slab else None,
            "outline": [[float(x), float(y)] for x, y in zip(xs, ys, strict=True)]}


def inside(outline, slab_outline) -> bool:
    """O contorno cabe inteiro na laje?"""
    outside = clip.difference([list(map(tuple, outline))], [list(map(tuple, slab_outline))])
    return clip.area(outside) <= 1e-8


def check(doc: Document, state: dict) -> list[list[float]]:
    """Contorno limpo da abertura; recusa se sair da laje (spec/ui 12 §3.2)."""
    from brasbim.core.structure import slabs  # evita import circular

    outline = slabs.clean(state["outline"])
    slab = doc.get(state["slab"], "IfcSlab")
    slab_state = slabs.read_state(doc, slab)
    if slab_state["foreign"] is not None:
        raise OpError("abertura só em laje do BrasBim")
    if not inside(outline, slab_state["outline"]):
        raise OpError("a abertura precisa ficar inteira dentro da laje")
    return outline


# --- gravação ----------------------------------------------------------------------------


def _write_outline(doc: Document, opening, outline) -> None:
    pset = props.ensure_pset(doc, opening, PSET)
    old = [p for p in pset.HasProperties or [] if p.Name in _LISTS]
    if old:  # o IfcOpenShell não edita listas: são refeitas
        pset.HasProperties = [p for p in pset.HasProperties if p not in old]
        for prop in old:
            ifcopenshell.util.element.remove_deep2(doc.ifc, prop)
    pset.HasProperties = [*(pset.HasProperties or []), *(
        doc.ifc.create_entity("IfcPropertyListValue", Name=name, ListValues=[
            doc.ifc.createIfcLengthMeasure(float(p[k])) for p in outline])
        for k, name in enumerate(_LISTS))]


def _set_host(doc: Document, opening, slab) -> None:
    for rel in list(opening.VoidsElements):
        if rel.RelatingBuildingElement == slab:
            return
        doc.ifc.remove(rel)
    doc.ifc.create_entity("IfcRelVoidsElement", GlobalId=guid.derived(opening.GlobalId, "voids"),
                          RelatingBuildingElement=slab, RelatedOpeningElement=opening)


def place(doc: Document, opening, slab, slab_origin, thickness: float) -> None:
    """Corpo e posicionamento a partir do estado e da laje (derivados)."""
    ifc = doc.ifc
    outline = read_state(opening)["outline"]
    ox, oy = slab_origin
    location = ifc.createIfcAxis2Placement3D(
        ifc.createIfcCartesianPoint((0.0, 0.0, -float(thickness) - CLEARANCE)), None, None)
    old = opening.ObjectPlacement
    opening.ObjectPlacement = ifc.createIfcLocalPlacement(slab.ObjectPlacement, location)
    if old is not None:
        ifcopenshell.util.element.remove_deep2(ifc, old)
    pts = [ifc.createIfcCartesianPoint((float(x - ox), float(y - oy))) for x, y in outline]
    area = ifc.createIfcArbitraryClosedProfileDef("AREA", None,
                                                  ifc.createIfcPolyline([*pts, pts[0]]))
    solid = ifc.createIfcExtrudedAreaSolid(
        area, ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                                            None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), float(thickness) + 2 * CLEARANCE)
    rep = ifc.createIfcShapeRepresentation(doc.body_context, "Body", "SweptSolid", [solid])
    props.replace_representation(doc, opening, "Body", rep)


def refresh(doc: Document, slab, slab_origin, thickness: float) -> None:
    for opening in of_slab(slab):
        place(doc, opening, slab, slab_origin, thickness)
        doc.changed.add(opening.GlobalId)


def _write(doc: Document, opening, state: dict) -> None:
    slab = doc.get(state["slab"], "IfcSlab")
    _set_host(doc, opening, slab)
    _write_outline(doc, opening, state["outline"])


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    opening = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcOpeningElement",
                                                  predefined_type="OPENING")
    opening.GlobalId = op.id
    try:
        _write(doc, opening, op.data)
    except Exception:
        remove(doc, opening)
        raise
    return {op.id, op.data["slab"]}


def remove(doc: Document, opening) -> None:
    for rel in list(opening.VoidsElements):
        doc.ifc.remove(rel)
    ifcopenshell.api.root.remove_product(doc.ifc, product=opening)


def _delete(doc: Document, op: Op) -> set[str]:
    opening = doc.get(op.id, "IfcOpeningElement")
    slab = host(opening)
    remove(doc, opening)
    return {op.id} | ({slab.GlobalId} if slab is not None else set())


def _edit(doc: Document, op: Op) -> set[str]:
    opening = doc.get(op.id, "IfcOpeningElement")
    state = read_state(opening)
    check_before(op, state)
    state.update(op.after or {})
    _write(doc, opening, state)
    return {op.id, state["slab"]}


register_inverse_pair("slab_opening.create", _create, "slab_opening.delete", _delete)
register("slab_opening.edit", _edit, invert_swap)
