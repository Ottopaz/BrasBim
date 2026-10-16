# SPDX-License-Identifier: LGPL-3.0-or-later
"""Vistas de corte e de fachada (``IfcAnnotation`` na edificação), spec/ui 14 §2–§3, §6.

Operações: ``view.create`` / ``view.delete`` (data: estado completo) e ``view.edit``
(before/after: campos alterados).

Estado::

    {"name": "Corte A", "letter": "A", "kind": "section" | "elevation",
     "a": [3, -1], "b": [3, 5], "side": "left" | "right", "depth": None,
     "zmin": None, "zmax": None, "scale": 50}

``side``: o lado olhado, à esquerda ou à direita de quem anda de A para B. Os parâmetros
ficam em JSON no Pset ``BrasBim_Vista``; a representação ``Annotation`` (contexto
``Plan``) é o símbolo da vista, refeito a cada gravação. O desenho do corte não é gravado
(``section.draw``).
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props, storeys
from brasbim.core.annotations import prims
from brasbim.core.annotations.prims import Prims, Stroke, Text
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Vista"
OBJECT_TYPES = {"section": "VistaDeCorte", "elevation": "VistaDeFachada"}
KINDS = tuple(OBJECT_TYPES)
SIDES = ("left", "right")
STATE_KEYS = ("name", "letter", "kind", "a", "b", "side", "depth", "zmin", "zmax", "scale")
SYMBOL_MM = 8.0  # tamanho da seta (mm de papel), §6 (CG)


def default_state() -> dict:
    return {"name": None, "letter": None, "kind": "section", "side": "left", "depth": None,
            "zmin": None, "zmax": None, "scale": storeys.DEFAULT_SCALE}


def is_view(entity) -> bool:
    return (entity is not None and entity.is_a("IfcAnnotation")
            and entity.ObjectType in OBJECT_TYPES.values())


def all_views(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcAnnotation") if is_view(e)),
                  key=lambda e: (read_state(e)["name"] or "", e.GlobalId))


def read_state(view) -> dict:
    values = ifcopenshell.util.element.get_pset(view, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"vista {view.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


def frame(state: dict) -> tuple[tuple, tuple, tuple]:
    """(origem A, direção A→B, direção olhada) em planta."""
    (ax, ay), (bx, by) = state["a"], state["b"]
    n = math.hypot(bx - ax, by - ay)
    d = ((bx - ax) / n, (by - ay) / n)
    left = (-d[1], d[0])
    look = left if state["side"] == "left" else (-left[0], -left[1])
    return (ax, ay), d, look


def next_letter(doc: Document) -> str:
    used = {read_state(v)["letter"] for v in all_views(doc)}
    for k in range(26 * 26):
        letter = chr(65 + k % 26) * (1 + k // 26)
        if letter not in used:
            return letter
    return "Z"


def next_elevation_name(doc: Document) -> str:
    used = {read_state(v)["name"] for v in all_views(doc)}
    n = 1
    while f"Fachada {n}" in used:
        n += 1
    return f"Fachada {n}"


def _validate(state: dict) -> None:
    if state["kind"] not in KINDS:
        raise OpError(f"tipo de vista inválido: {state['kind']!r}")
    if state["side"] not in SIDES:
        raise OpError(f"lado inválido: {state['side']!r}")
    if math.dist(state["a"], state["b"]) < 0.01:
        raise OpError("a linha da vista precisa de dois pontos distintos")
    if int(state["scale"]) not in storeys.SCALES:
        raise OpError(f"escala inválida: 1:{state['scale']}")


# --- símbolo (§6) ------------------------------------------------------------------------


def symbol(state: dict) -> Prims:
    """Símbolo na planta: corte em traço e ponto com setas e letra; fachada, uma seta com o
    nome (spec/ui 14 §6)."""
    k = state["scale"] / 1000.0  # m por mm de papel
    a, d, look = frame(state)
    b = tuple(state["b"])
    size = SYMBOL_MM * k
    out = Prims()

    def arrow(at):
        tip = (at[0] + look[0] * size, at[1] + look[1] * size)
        head = 0.35 * size
        back = (tip[0] - look[0] * head, tip[1] - look[1] * head)
        out.strokes.append(Stroke((at, tip), False, 0.35))
        out.strokes.append(Stroke(((back[0] + d[0] * head / 2, back[1] + d[1] * head / 2), tip,
                                   (back[0] - d[0] * head / 2, back[1] - d[1] * head / 2)),
                                  True, 0.35))
        return tip

    if state["kind"] == "section":
        length = math.dist(a, b)
        stub = min(size * 1.2, length / 3)
        ends = [(a, (a[0] + d[0] * stub, a[1] + d[1] * stub)),
                (b, (b[0] - d[0] * stub, b[1] - d[1] * stub))]
        for p, q in ends:
            out.strokes.append(Stroke((p, q), False, 0.5))
        out.strokes.append(Stroke((ends[0][1], ends[1][1]), False, 0.13, "dashdot"))
        for p in (a, b):
            tip = arrow(p)
            out.texts.append(Text((tip[0] + look[0] * 0.4 * size, tip[1] + look[1] * 0.4 * size),
                                  state["letter"] or "", 4.0 * k, 0.0, "center", "middle"))
    else:
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        start = (mid[0] - look[0] * size, mid[1] - look[1] * size)
        arrow(start)
        out.texts.append(Text((start[0] - look[0] * 0.5 * size, start[1] - look[1] * 0.5 * size),
                              state["name"] or "", 3.0 * k, 0.0, "center", "middle"))
    return out


def shown_on(state: dict, storey) -> bool:
    """O símbolo aparece na planta deste pavimento? (corte: os que a faixa de cotas
    atravessa; sem faixa, todos)."""
    z = float(storey.Elevation or 0.0)
    if state["zmin"] is not None and z < state["zmin"] - 1e-6:
        return False
    return not (state["zmax"] is not None and z > state["zmax"] + 1e-6)


# --- gravação ----------------------------------------------------------------------------


def _write(doc: Document, view, state: dict) -> None:
    _validate(state)
    building = doc.building
    view.ObjectType = OBJECT_TYPES[state["kind"]]
    view.Name = state["name"]
    if ifcopenshell.util.element.get_container(view) != building:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[view],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    if view.ObjectPlacement is None:
        view.ObjectPlacement = local_placement(doc.ifc, building.ObjectPlacement)
    props.write_pset(doc, view, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        state, sort_keys=True, ensure_ascii=False))})
    prims.write(doc, view, symbol(state))


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    view = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
    view.GlobalId = op.id
    view.PredefinedType = "USERDEFINED"
    try:
        _write(doc, view, {**default_state(), **copy.deepcopy(op.data)})
    except Exception:
        remove(doc, view)
        raise
    return {op.id}


def remove(doc: Document, view) -> None:
    prims._drop(doc, view)
    ifcopenshell.api.root.remove_product(doc.ifc, product=view)


def _delete(doc: Document, op: Op) -> set[str]:
    remove(doc, doc.get(op.id, "IfcAnnotation"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    view = doc.get(op.id, "IfcAnnotation")
    state = read_state(view)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"view.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    _write(doc, view, state)
    return {op.id}


register_inverse_pair("view.create", _create, "view.delete", _delete)
register("view.edit", _edit, invert_swap)
