# SPDX-License-Identifier: LGPL-3.0-or-later
"""Guarda-corpo (``IfcRailing`` ``GUARDRAIL``), ``spec/elementos/escada-terreno.md`` §3.

Operações do guarda-corpo solto: ``railing.create`` / ``railing.delete`` (data: estado
completo) e ``railing.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"storey": "<GlobalId>", "points": [[0, 0], [4, 0]], "base": 0.0, "height": 1.10,
     "spacing": 1.20}

A geometria (``body_items``) serve também aos guarda-corpos da escada, que passam um
caminho 3D (a base sobe com os degraus). Montantes a cada ``spacing`` no máximo, corrimão
no topo e uma barra intermediária, todos de seção quadrada.
"""

from __future__ import annotations

import copy
import itertools
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, materials, props
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_GuardaCorpo"
STATE_KEYS = ("storey", "points", "base", "height", "spacing")
POST = 0.04  # m: lado do montante
RAIL = 0.05  # m: corrimão
BAR = 0.025  # m: barra intermediária
MATERIAL = "Alumínio"


def default_state() -> dict:
    return {"storey": None, "points": [], "base": 0.0, "height": 1.10, "spacing": 1.20}


def is_railing(entity) -> bool:
    return entity is not None and entity.is_a("IfcRailing") and bool(
        ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False))


def read_state(railing) -> dict:
    values = ifcopenshell.util.element.get_pset(railing, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"guarda-corpo {railing.GlobalId} sem os parâmetros do BrasBim")
    state = {**default_state(), **json.loads(values["Parametros"])}
    storey = ifcopenshell.util.element.get_container(railing)
    state["storey"] = storey.GlobalId if storey else state["storey"]
    return state


# --- geometria --------------------------------------------------------------------------------


def _pt(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _bar(ifc, a, b, size: float):
    """Barra de seção quadrada de ``a`` a ``b`` (pontos 3D)."""
    d = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(c * c for c in d))
    if length < 1e-6:
        return None
    axis = tuple(c / length for c in d)
    ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
    profile = ifc.createIfcRectangleProfileDef("AREA", None, None, size, size)
    position = ifc.createIfcAxis2Placement3D(_pt(ifc, a), ifc.createIfcDirection(axis),
                                             ifc.createIfcDirection(_perp(axis, ref)))
    return ifc.createIfcExtrudedAreaSolid(profile, position,
                                          ifc.createIfcDirection((0.0, 0.0, 1.0)), length)


def _perp(axis, ref):
    dot = sum(axis[i] * ref[i] for i in range(3))
    v = [ref[i] - dot * axis[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def posts(path3, spacing: float) -> list[tuple[float, float, float]]:
    """Pés dos montantes: as pontas, os vértices e a cada ``spacing`` no máximo."""
    out = [tuple(path3[0])]
    for a, b in itertools.pairwise(path3):
        length = math.dist(a[:2], b[:2])
        n = max(1, math.ceil(length / spacing - 1e-9))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))
    return out


def body_items(ifc, path3, height: float, spacing: float) -> list:
    """Montantes, corrimão e barra intermediária ao longo do caminho 3D (base)."""
    items = []
    for p in posts(path3, spacing):
        item = _bar(ifc, p, (p[0], p[1], p[2] + height - RAIL / 2), POST)
        if item is not None:
            items.append(item)
    for a, b in itertools.pairwise(path3):
        for z, size in ((height - RAIL / 2, RAIL), (height / 2, BAR)):
            item = _bar(ifc, (a[0], a[1], a[2] + z), (b[0], b[1], b[2] + z), size)
            if item is not None:
                items.append(item)
    return items


def write_body(doc: Document, railing, path3, height: float, spacing: float) -> None:
    """Corpo do guarda-corpo, com o estilo do alumínio em cada peça."""
    from brasbim.core.walls.types import material_named

    ifc = doc.ifc
    rep = props.representation(railing, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            ifc.remove(styled)
    material_named(doc, MATERIAL)
    materials.ensure_style(doc, MATERIAL)
    style = materials.surface_style(doc, MATERIAL)
    items = body_items(ifc, path3, height, spacing)
    for item in items:
        if style is not None:
            ifc.createIfcStyledItem(item, [style], None)
    if items:
        props.replace_representation(doc, railing, "Body", ifc.createIfcShapeRepresentation(
            doc.body_context, "Body", "SweptSolid", items))
    railing.PredefinedType = "GUARDRAIL"


# --- guarda-corpo solto ---------------------------------------------------------------------


def validate(state: dict) -> None:
    if len(state["points"]) < 2:
        raise OpError("o guarda-corpo precisa de pelo menos 2 pontos")
    if state["height"] <= 0 or state["spacing"] <= 0.1:
        raise OpError("altura e espaçamento do guarda-corpo devem ser positivos")


def write(doc: Document, railing, state: dict) -> None:
    state = {**default_state(), **state}
    validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    if ifcopenshell.util.element.get_container(railing) != storey:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[railing],
                                                        relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")
    if railing.ObjectPlacement is None or \
            railing.ObjectPlacement.PlacementRelTo != storey.ObjectPlacement:
        old = railing.ObjectPlacement
        railing.ObjectPlacement = local_placement(doc.ifc, storey.ObjectPlacement)
        if old is not None:
            ifcopenshell.util.element.remove_deep2(doc.ifc, old)
    path3 = [(p[0], p[1], state["base"]) for p in state["points"]]
    write_body(doc, railing, path3, state["height"], state["spacing"])
    length = sum(math.dist(a, b) for a, b in zip(state["points"], state["points"][1:],
                                                   strict=False))
    props.write_pset(doc, railing, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        {k: state[k] for k in STATE_KEYS if k != "storey"}, ensure_ascii=False,
        sort_keys=True))})
    props.write_pset(doc, railing, "Pset_RailingCommon", {"Height": state["height"]})
    props.write_qto(doc, railing, "Qto_RailingBaseQuantities", {"Length": length})
    doc.changed.add(railing.GlobalId)


def remove(doc: Document, railing) -> None:
    from brasbim.core import fragment

    rep = props.representation(railing, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)
    shape = railing.Representation
    railing.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=railing)
    if shape is not None:
        fragment.remove(doc.ifc, shape)


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    railing = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcRailing")
    railing.GlobalId = op.id
    try:
        write(doc, railing, copy.deepcopy(op.data))
    except Exception:
        remove(doc, railing)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcRailing"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    railing = doc.get(op.id, "IfcRailing")
    state = read_state(railing)
    check_before(op, state)
    state.update(copy.deepcopy(op.after or {}))
    write(doc, railing, state)
    return {op.id}


register_inverse_pair("railing.create", _create, "railing.delete", _delete)
register("railing.edit", _edit, invert_swap)


def create_railing(doc: Document, storey, points, base: float = 0.0, height: float = 1.10,
                   spacing: float = 1.20):
    from brasbim.core.ops import Transaction

    state = {**default_state(), "storey": storey if isinstance(storey, str) else
             storey.GlobalId, "points": [[float(x), float(y)] for x, y in points],
             "base": float(base), "height": float(height), "spacing": float(spacing)}
    validate(state)
    return Transaction("Criar guarda-corpo", [Op("railing.create", guid.new(), data=state)])


def edit_railing(doc: Document, railing, **changes):
    from brasbim.core.ops import Transaction

    railing = doc.get(railing if isinstance(railing, str) else railing.GlobalId)
    state = read_state(railing)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    validate({**state, **after})
    if not after:
        return Transaction("Editar guarda-corpo", [])
    return Transaction("Editar guarda-corpo", [Op(
        "railing.edit", railing.GlobalId, before={k: copy.deepcopy(state[k]) for k in after},
        after=after)])


def delete_ops(doc: Document, railing) -> list[Op]:
    return [Op("railing.delete", railing.GlobalId, data=read_state(railing))]


def plan_points(state: dict) -> list[tuple[float, float]]:
    return [tuple(p) for p in state["points"]]
