# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ocorrência de viga (``IfcBeam``), ``viga.md`` §2.3, §3.1 e §5.2.

Operações: ``beam.create`` / ``beam.delete`` (data: estado completo) e ``beam.edit``
(before/after: campos de ``STATE_KEYS`` alterados).

Estado::

    {"name": "V1", "type": "<GlobalId do IfcBeamType>", "storey": "<GlobalId>",
     "start": [0.0, 0.0], "end": [5.0, 0.0], "ref_line": "axis",
     "top_mode": "storey", "top_storey": "<GlobalId>", "top_offset": 0.0,
     "top_elevation": 2.80, "common": {}, "foreign": None, "placement": None}

``top_elevation``: cota fixa do topo, em relação ao pavimento da viga. Posicionamento:
origem no ponto inicial, na cota do topo; z local = direção da viga, x local = à esquerda
de quem anda do início para o fim, y local = para cima. O comprimento vem do ``Axis``.
"""

from __future__ import annotations

import math

import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.structure import common
from brasbim.core.structure import types as st_types

PSET = "BrasBim_Viga"
COMMON_PSET = "Pset_BeamCommon"
MIN_LENGTH = 0.01  # m (viga.md §3.1)
REF_LINES = ("axis", "left_face", "right_face")
# Linha de referência → CardinalPoint (viga.md §2.4): o topo fica sempre na cota.
CARDINAL = {"left_face": 7, "axis": 8, "right_face": 9}
_PSET_REF = {"axis": "EIXO", "left_face": "FACE_ESQUERDA", "right_face": "FACE_DIREITA"}
STATE_KEYS = ("name", "type", "storey", "start", "end", "ref_line", "top_mode", "top_storey",
              "top_offset", "top_elevation", "common", "foreign", "placement")


def default_state() -> dict:
    return {"name": None, "ref_line": "axis", "top_mode": "fixed", "top_storey": None,
            "top_offset": 0.0, "top_elevation": common.DEFAULT_TOP, "common": {},
            "foreign": None, "placement": None}


def is_parametric(beam) -> bool:
    return bool(ifcopenshell.util.element.get_pset(beam, PSET, should_inherit=False))


# --- leitura -----------------------------------------------------------------------------


def _usage(beam):
    usage = ifcopenshell.util.element.get_material(beam, should_inherit=False)
    return usage if usage is not None and usage.is_a("IfcMaterialProfileSetUsage") else None


def _length(beam) -> float | None:
    axis = props.representation(beam, "Axis")
    if axis is None or not axis.Items or not axis.Items[0].is_a("IfcPolyline"):
        return None
    pts = [p.Coordinates for p in axis.Items[0].Points]
    return math.dist(pts[0], pts[-1])


def read_state(doc: Document, beam) -> dict:
    state = default_state()
    beam_type = ifcopenshell.util.element.get_type(beam)
    container = ifcopenshell.util.element.get_container(beam)
    state.update(name=beam.Name, type=beam_type.GlobalId if beam_type else None,
                 storey=container.GlobalId if container else None)
    placement = common.read_placement(beam)
    values = ifcopenshell.util.element.get_pset(beam, PSET, should_inherit=False)
    foreign = not values
    if foreign:
        state["foreign"] = common.read_foreign(beam)
        state["placement"] = placement
    else:
        x, y, _ = placement["location"]
        d = placement["axis"]
        n = math.hypot(d[0], d[1])
        length = _length(beam) or 0.0
        state.update(start=[x, y], end=[x + d[0] / n * length, y + d[1] / n * length],
                     ref_line={v: k for k, v in _PSET_REF.items()}[values["LinhaReferencia"]],
                     top_mode=common.top_from_pset(values.get("TipoTopo")),
                     top_storey=values.get("PavimentoTopo"),
                     top_offset=float(values.get("DeslocamentoTopo") or 0.0),
                     top_elevation=float(values.get("CotaFixa") or common.DEFAULT_TOP))
    state["common"] = common.read_common(beam, COMMON_PSET, beam_type, foreign)
    return state


# --- cálculo -----------------------------------------------------------------------------


def top_z(doc: Document, state: dict) -> float:
    """Cota do topo em relação ao pavimento da viga."""
    if state["top_mode"] == "fixed":
        return float(state["top_elevation"])
    return (common.elevation(doc, state["top_storey"]) + state["top_offset"]
            - common.elevation(doc, state["storey"]))


def length(state: dict) -> float:
    return math.dist(state["start"], state["end"])


def section(doc: Document, state: dict) -> dict:
    return st_types.section(doc.get(state["type"], "IfcBeamType"))


def faces(doc: Document, state: dict, sec: dict | None = None) -> tuple[float, float]:
    """(y da face direita, y da face esquerda) em relação à linha desenhada, com y para a
    esquerda de quem anda do início para o fim."""
    b = (sec or section(doc, state))["b"]
    return {"axis": (-b / 2, b / 2), "left_face": (-b, 0.0),
            "right_face": (0.0, b)}[state["ref_line"]]


def outline(doc: Document, state: dict, sec: dict | None = None) -> list[tuple[float, float]]:
    """Faixa da viga no pavimento (anti-horário); ``sec`` no lugar da do tipo."""
    (x0, y0), (x1, y1) = state["start"], state["end"]
    n = length(state)
    ux, uy = (x1 - x0) / n, (y1 - y0) / n
    lx, ly = -uy, ux
    right, left = faces(doc, state, sec)
    return [(x0 + lx * right, y0 + ly * right), (x1 + lx * right, y1 + ly * right),
            (x1 + lx * left, y1 + ly * left), (x0 + lx * left, y0 + ly * left)]


# --- gravação ----------------------------------------------------------------------------


def _validate(doc: Document, state: dict) -> None:
    if state["foreign"] is not None:
        return
    common.validate_top(state)
    if state["ref_line"] not in REF_LINES:
        raise OpError(f"linha de referência inválida: {state['ref_line']!r}")
    if length(state) <= MIN_LENGTH:
        raise OpError(f"a viga precisa ter mais de {MIN_LENGTH:.2f} m")


def place(doc: Document, beam, state: dict) -> None:
    """Posicionamento na cota do topo (refeito também quando o pavimento muda)."""
    (x0, y0), (x1, y1) = state["start"], state["end"]
    n = length(state)
    ux, uy = (x1 - x0) / n, (y1 - y0) / n
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    common.write_placement(doc, beam, {
        "rel": {"ref": storey.ObjectPlacement.id()},
        "location": [float(x0), float(y0), top_z(doc, state)],
        "axis": [ux, uy, 0.0], "ref": [-uy, ux, 0.0]})


def _assign_material(doc: Document, beam, beam_type, cardinal: int) -> None:
    pset = st_types.profile_set(beam_type)
    usage = _usage(beam)
    if usage is None or usage.ForProfileSet != pset:
        if ifcopenshell.util.element.get_material(beam, should_inherit=False) is not None:
            ifcopenshell.api.material.unassign_material(doc.ifc, products=[beam])
        usage = doc.ifc.createIfcMaterialProfileSetUsage(pset, cardinal, None)
        doc.ifc.create_entity("IfcRelAssociatesMaterial",
                              GlobalId=guid.derived(beam.GlobalId, "material"),
                              RelatedObjects=[beam], RelatingMaterial=usage)
    usage.CardinalPoint = cardinal
    common.stamp_material(beam)


def write_state(doc: Document, beam, state: dict) -> None:
    _validate(doc, state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    beam_type = doc.find(state["type"]) if state["type"] else None
    beam.Name = state["name"]
    if beam_type is not None:
        common.assign_type(doc, beam, beam_type)
    common.assign_container(doc, beam, storey)
    foreign = state["foreign"] is not None
    if foreign:
        common.write_foreign(doc, beam, state)
    else:
        if state["top_mode"] == "storey":
            doc.get(state["top_storey"], "IfcBuildingStorey")
        _assign_material(doc, beam, beam_type, CARDINAL[state["ref_line"]])
        place(doc, beam, state)
        # O comprimento faz parte do estado: o eixo é gravado aqui (o corpo é derivado).
        set_axis(doc, beam, length(state))
        f = doc.ifc
        props.write_pset(doc, beam, PSET, {
            "LinhaReferencia": f.createIfcLabel(_PSET_REF[state["ref_line"]]),
            "TipoTopo": f.createIfcLabel(common.top_to_pset(state["top_mode"])),
            "PavimentoTopo": (f.createIfcIdentifier(state["top_storey"])
                              if state["top_mode"] == "storey" else None),
            "DeslocamentoTopo": f.createIfcLengthMeasure(float(state["top_offset"])),
            "CotaFixa": f.createIfcLengthMeasure(float(state["top_elevation"])),
        })
    common.write_common(doc, beam, COMMON_PSET, beam_type, state["common"], foreign)


def set_axis(doc: Document, beam, length_: float) -> None:
    ifc = doc.ifc
    curve = ifc.createIfcPolyline([ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)),
                                   ifc.createIfcCartesianPoint((0.0, 0.0, float(length_)))])
    rep = ifc.createIfcShapeRepresentation(doc.model_axis_context, "Axis", "Curve3D", [curve])
    props.replace_representation(doc, beam, "Axis", rep)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    beam = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcBeam")
    beam.GlobalId = op.id
    try:
        write_state(doc, beam, {**default_state(), **op.data})
    except Exception:
        common.remove(doc, beam)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    common.remove(doc, doc.get(op.id, "IfcBeam"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    beam = doc.get(op.id, "IfcBeam")
    state = read_state(doc, beam)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"beam.edit: campos desconhecidos {sorted(unknown)}")
    state.update(op.after or {})
    write_state(doc, beam, state)
    return {op.id}


register_inverse_pair("beam.create", _create, "beam.delete", _delete)
register("beam.edit", _edit, invert_swap)
