# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pavimentos (``IfcBuildingStorey``).

PROVISÓRIO: o pavimento ainda não tem spec própria. Estas operações existem para que a
parede (RF-ELE-01) possa ser criada, testada e reaplicada (critérios P04 e P15).

Operações: ``storey.create`` / ``storey.delete`` (data: name, elevation, cut_height) e
``storey.edit`` (before/after: name, elevation, cut_height).

``cut_height`` é a altura do plano de corte da planta acima da cota do pavimento
(spec/ui 06 §3.1), no Pset ``BrasBim_Pavimento``; ``None`` = padrão (1,50 m), sem gravar.
``scale`` é o denominador da escala de desenho da planta (spec/ui 13 §2), no mesmo Pset
(``Escala``); ``None`` = padrão (1:50), sem gravar.
"""

from __future__ import annotations

import contextlib

import ifcopenshell.api.aggregate
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError, axis_placement, local_placement
from brasbim.core.ops.base import (
    Op,
    check_before,
    invert_swap,
    register,
    register_inverse_pair,
)

PSET = "BrasBim_Pavimento"
DEFAULT_CUT_HEIGHT = 1.50  # parede §7, a confirmar na NBR 6492
DEFAULT_SCALE = 50  # spec/ui 13 §2
SCALES = (20, 25, 50, 75, 100, 200, 500)


def read(storey) -> dict:
    values = ifcopenshell.util.element.get_pset(storey, PSET) or {}
    cut, scale_ = values.get("AlturaPlanoCorte"), values.get("Escala")
    return {"name": storey.Name, "elevation": float(storey.Elevation or 0.0),
            "cut_height": None if cut is None else float(cut),
            "scale": None if scale_ is None else int(scale_)}


# Escala que vale no lugar da gravada, por pavimento (spec/ui 25 §4): a da vista salva
# aberta na janela, ou a de uma vista salva sendo desenhada na prancha.
_scale_override: dict[str, int | None] = {}


def scale(storey) -> int:
    """Denominador da escala de desenho da planta do pavimento (spec/ui 13 §2)."""
    if storey is not None and _scale_override.get(storey.GlobalId):
        return _scale_override[storey.GlobalId]
    return stored_scale(storey)


def stored_scale(storey) -> int:
    """Escala gravada no pavimento, sem a da janela."""
    value = read(storey)["scale"] if storey is not None else None
    return DEFAULT_SCALE if value is None else value


def set_scale_override(storey_id: str, value: int | None) -> None:
    """Escala da janela para o pavimento (``None`` volta à gravada), sem transação."""
    if value is None:
        _scale_override.pop(storey_id, None)
    else:
        _scale_override[storey_id] = int(value)


def clear_scale_overrides() -> None:
    _scale_override.clear()


@contextlib.contextmanager
def using_scale(storey_id: str, value: int | None):
    """Desenha o pavimento com a escala ``value`` (``None``: a gravada)."""
    had, previous = storey_id in _scale_override, _scale_override.get(storey_id)
    _scale_override[storey_id] = None if value is None else int(value)
    try:
        yield
    finally:
        if had:
            _scale_override[storey_id] = previous
        else:
            _scale_override.pop(storey_id, None)


def paper(storey, mm: float) -> float:
    """Tamanho no modelo (m) de ``mm`` milímetros de papel na escala do pavimento."""
    return mm * scale(storey) / 1000.0


def cut_height(storey) -> float:
    """Plano de corte da planta, acima da cota do pavimento (spec/ui 06 §3.1)."""
    value = read(storey)["cut_height"]
    return DEFAULT_CUT_HEIGHT if value is None else value


def _write_pset(doc: Document, storey, cut, scale_) -> None:
    """Plano de corte e escala; o que é padrão (``None``) não é gravado."""
    if cut is not None and cut <= 0:
        raise OpError("o plano de corte deve ficar acima da cota do pavimento")
    if scale_ is not None and int(scale_) not in SCALES:
        raise OpError(f"escala inválida: 1:{scale_}")
    values = {}
    if cut is not None:
        values["AlturaPlanoCorte"] = doc.ifc.createIfcPositiveLengthMeasure(float(cut))
    if scale_ is not None:
        values["Escala"] = doc.ifc.createIfcInteger(int(scale_))
    if not values:
        props.remove_pset(doc, storey, PSET)
        return
    props.write_pset(doc, storey, PSET, values)


def _write(doc: Document, storey, state: dict) -> None:
    if "cut_height" in state or "scale" in state:
        _write_pset(doc, storey, state.get("cut_height"), state.get("scale"))
    storey.Name = state["name"]
    storey.Elevation = float(state["elevation"])
    old = storey.ObjectPlacement
    if old is not None:
        rel = old.RelativePlacement
        old.RelativePlacement = axis_placement(doc.ifc, (0.0, 0.0), storey.Elevation, (1.0, 0.0))
        ifcopenshell.util.element.remove_deep2(doc.ifc, rel)
    else:
        storey.ObjectPlacement = local_placement(
            doc.ifc, doc.building.ObjectPlacement, storey.Elevation
        )


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    storey = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcBuildingStorey")
    storey.GlobalId = op.id
    _write(doc, storey, op.data)
    building = doc.building
    rel = ifcopenshell.api.aggregate.assign_object(
        doc.ifc, products=[storey], relating_object=building
    )
    guid.stamp(rel, building.GlobalId, "aggregates")
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    storey = doc.get(op.id, "IfcBuildingStorey")
    if ifcopenshell.util.element.get_contained(storey):
        raise OpError("o pavimento contém elementos")
    ifcopenshell.api.root.remove_product(doc.ifc, product=storey)
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    storey = doc.get(op.id, "IfcBuildingStorey")
    state = read(storey)
    check_before(op, state)
    state.update(op.after or {})
    _write(doc, storey, state)
    return {op.id}


register_inverse_pair("storey.create", _create, "storey.delete", _delete)
register("storey.edit", _edit, invert_swap)
