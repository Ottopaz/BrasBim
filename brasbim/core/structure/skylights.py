# SPDX-License-Identifier: LGPL-3.0-or-later
"""Claraboia (``IfcWindow`` ``SKYLIGHT``), ``spec/ui/20-eixos-vaos-claraboia.md`` §4.

Operações: ``skylight.create`` / ``skylight.delete`` (data: estado completo) e
``skylight.edit`` (before/after: campos de ``STATE_KEYS``).

Estado::

    {"code": "CL1", "storey": "<GlobalId>", "host": "<GlobalId da laje ou da cobertura>",
     "center": [3.0, 2.0], "width": 0.8, "length": 1.2, "angle": 0.0, "frame": 0.06}

A claraboia preenche (``IfcRelFillsElement``) um vão (``IfcOpeningElement`` com o Pset
``BrasBim_VaoClaraboia``) que fura a laje ou a água da cobertura que contém o centro.
Corpo, vão e posicionamento ficam no plano do topo dessa laje ou água e são refeitos
quando ela muda (``derive``). Tudo posicionado em relação ao pavimento.
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, materials, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import (
    Op,
    check_before,
    invert_swap,
    register,
    register_derive,
    register_inverse_pair,
)

PSET = "BrasBim_Claraboia"
OPENING_PSET = "BrasBim_VaoClaraboia"
STATE_KEYS = ("code", "storey", "host", "center", "width", "length", "angle", "frame")
FRAME_HEIGHT = 0.10  # m: altura do caixilho acima do topo
GLASS = 0.01
CLEARANCE = 0.02


def default_state() -> dict:
    return {"code": "CL1", "storey": None, "host": None, "center": [0.0, 0.0],
            "width": 0.8, "length": 1.2, "angle": 0.0, "frame": 0.06}


def is_skylight(entity) -> bool:
    return (entity is not None and entity.is_a("IfcWindow") and bool(
        ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False)))


def is_skylight_opening(entity) -> bool:
    return entity is not None and entity.is_a("IfcOpeningElement") and bool(
        ifcopenshell.util.element.get_pset(entity, OPENING_PSET, should_inherit=False))


def all_skylights(doc: Document) -> list:
    return sorted((w for w in doc.ifc.by_type("IfcWindow") if is_skylight(w)),
                  key=lambda w: w.GlobalId)


def read_state(window) -> dict:
    values = ifcopenshell.util.element.get_pset(window, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"claraboia {window.GlobalId} sem os parâmetros do BrasBim")
    state = {**default_state(), **json.loads(values["Parametros"])}
    storey = ifcopenshell.util.element.get_container(window)
    state["storey"] = storey.GlobalId if storey else state["storey"]
    return state


def opening_id(gid: str) -> str:
    return guid.derived(gid, "opening")


# --- plano de apoio -----------------------------------------------------------------------


def _inside(ring, p) -> bool:
    inside = False
    for i in range(len(ring)):
        (x0, y0), (x1, y1) = ring[i - 1], ring[i]
        if (y0 > p[1]) != (y1 > p[1]) and p[0] < x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def support(doc: Document, state: dict) -> dict:
    """Onde a claraboia se apoia: a peça furada (laje ou água), a espessura e o plano
    (origem no topo sob o centro, eixos ``u`` e ``v`` no plano e a normal ``n``)."""
    from brasbim.core.structure import roofs, slabs

    host = doc.get(state["host"])
    center = tuple(state["center"])
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    if host.is_a("IfcRoof"):
        rstate = roofs.read_state(doc, host)
        faces = roofs.faces(rstate)
        parts = roofs.parts_of(host)
        found = [i for i, f in enumerate(faces) if _inside(f.ring, center)]
        if not found or len(parts) != len(faces):
            raise OpError(f"a claraboia {state['code']} ficaria fora da cobertura")
        face = faces[found[0]]
        t = roofs.thickness(doc, rstate)
        top, _, _, n = roofs._part_frame(rstate, face, t)
        origin = top(center)
        part = parts[found[0]]
    elif host.is_a("IfcSlab") and not roofs.is_part(host):
        sstate = slabs.read_state(doc, host)
        if not _inside(sstate["outline"], center):
            raise OpError(f"a claraboia {state['code']} ficaria fora da laje")
        t = slabs.thickness(doc, sstate)
        origin = (center[0], center[1], float(sstate["top_offset"]))
        n = (0.0, 0.0, 1.0)
        part = host
    else:
        raise OpError("a claraboia vai numa laje ou numa cobertura")
    # x da claraboia: a direção do ângulo em planta, levada ao plano
    w = -(c * n[0] + s * n[1]) / n[2]
    length = math.sqrt(c * c + s * s + w * w)
    u = (c / length, s / length, w / length)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])
    return {"part": part, "thickness": t, "origin": origin, "u": u, "v": v, "n": n}


def outline(state: dict) -> list[tuple[float, float]]:
    """Contorno do caixilho em planta (projeção), anti-horário."""
    a = math.radians(state["angle"])
    c, s = math.cos(a), math.sin(a)
    w, h = state["width"] / 2, state["length"] / 2
    cx, cy = state["center"]
    return [(cx + c * x - s * y, cy + s * x + c * y) for x, y in ((-w, -h), (w, -h), (w, h),
                                                                  (-w, h))]


# --- gravação -------------------------------------------------------------------------------


def _pt(ifc, p):
    return ifc.createIfcCartesianPoint(tuple(float(c) for c in p))


def _placement(doc: Document, element, storey, frame: dict) -> None:
    ifc = doc.ifc
    rp = ifc.createIfcAxis2Placement3D(_pt(ifc, frame["origin"]),
                                       ifc.createIfcDirection(frame["n"]),
                                       ifc.createIfcDirection(frame["u"]))
    old = element.ObjectPlacement
    element.ObjectPlacement = ifc.createIfcLocalPlacement(storey.ObjectPlacement, rp)
    if old is not None:
        ifcopenshell.util.element.remove_deep2(ifc, old)


def _box(ifc, x0, x1, y0, y1, z0, z1):
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None, ifc.createIfcAxis2Placement2D(_pt(ifc, ((x0 + x1) / 2, (y0 + y1) / 2)),
                                                    None), x1 - x0, y1 - y0)
    return ifc.createIfcExtrudedAreaSolid(
        profile, ifc.createIfcAxis2Placement3D(_pt(ifc, (0.0, 0.0, z0)), None, None),
        ifc.createIfcDirection((0.0, 0.0, 1.0)), z1 - z0)


def _clear_styles(doc: Document, element) -> None:
    rep = props.representation(element, "Body")
    for item in (rep.Items if rep is not None else []) or []:
        for styled in [i for i in doc.ifc.get_inverse(item) if i.is_a("IfcStyledItem")]:
            doc.ifc.remove(styled)


def _body(doc: Document, window, state: dict) -> None:
    from brasbim.core.walls.types import material_named

    ifc = doc.ifc
    w, h, f = state["width"] / 2, state["length"] / 2, state["frame"]
    z1 = FRAME_HEIGHT
    bars = [(-w, w, -h, -h + f), (-w, w, h - f, h), (-w, -w + f, -h + f, h - f),
            (w - f, w, -h + f, h - f)]
    _clear_styles(doc, window)
    for name in ("Alumínio", "Vidro"):
        material_named(doc, name)
        materials.ensure_style(doc, name)
    items = []
    frame_style = materials.surface_style(doc, "Alumínio")
    for x0, x1, y0, y1 in bars:
        item = _box(ifc, x0, x1, y0, y1, 0.0, z1)
        if frame_style is not None:
            ifc.createIfcStyledItem(item, [frame_style], None)
        items.append(item)
    glass = _box(ifc, -w + f, w - f, -h + f, h - f, z1 - 0.02, z1 - 0.02 + GLASS)
    glass_style = materials.surface_style(doc, "Vidro")
    if glass_style is not None:
        ifc.createIfcStyledItem(glass, [glass_style], None)
    items.append(glass)
    props.replace_representation(doc, window, "Body", ifc.createIfcShapeRepresentation(
        doc.body_context, "Body", "SweptSolid", items))


def _opening(doc: Document, window, storey, state: dict, frame: dict):
    ifc = doc.ifc
    gid = opening_id(window.GlobalId)
    opening = doc.find(gid)
    if opening is None:
        opening = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcOpeningElement",
                                                      predefined_type="OPENING")
        opening.GlobalId = gid
    opening.Name = f"Vão da claraboia {state['code']}"
    _placement(doc, opening, storey, frame)
    w, h = state["width"] / 2, state["length"] / 2
    profile = ifc.createIfcRectangleProfileDef(
        "AREA", None, ifc.createIfcAxis2Placement2D(_pt(ifc, (0.0, 0.0)), None), 2 * w, 2 * h)
    solid = ifc.createIfcExtrudedAreaSolid(
        profile, ifc.createIfcAxis2Placement3D(_pt(ifc, (0.0, 0.0, CLEARANCE)), None, None),
        ifc.createIfcDirection((0.0, 0.0, -1.0)), frame["thickness"] + 3 * CLEARANCE)
    props.replace_representation(doc, opening, "Body", ifc.createIfcShapeRepresentation(
        doc.body_context, "Body", "SweptSolid", [solid]))
    props.write_pset(doc, opening, OPENING_PSET, {
        "Claraboia": ifc.createIfcIdentifier(window.GlobalId)})
    part = frame["part"]
    rels = opening.VoidsElements
    if not rels or rels[0].RelatingBuildingElement != part:
        for rel in rels:
            doc.changed.add(rel.RelatingBuildingElement.GlobalId)
            ifc.remove(rel)
        ifc.create_entity("IfcRelVoidsElement", GlobalId=guid.derived(gid, "voids"),
                          RelatingBuildingElement=part, RelatedOpeningElement=opening)
        doc.changed.add(part.GlobalId)
    if not window.FillsVoids:
        ifc.create_entity("IfcRelFillsElement", GlobalId=guid.derived(window.GlobalId,
                                                                      "fills"),
                          RelatingOpeningElement=opening, RelatedBuildingElement=window)
    return opening


def validate(state: dict) -> None:
    if state["width"] <= 0.1 or state["length"] <= 0.1:
        raise OpError("a claraboia precisa de pelo menos 10 cm de lado")
    if not 0 < state["frame"] < min(state["width"], state["length"]) / 2:
        raise OpError("o caixilho da claraboia é largo demais")
    if not str(state["code"]).strip():
        raise OpError("a claraboia precisa de um código")


def write(doc: Document, window, state: dict) -> None:
    state = {**default_state(), **state}
    validate(state)
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    frame = support(doc, state)
    window.PredefinedType = "SKYLIGHT"
    window.Name = state["code"]
    window.OverallWidth, window.OverallHeight = state["width"], state["length"]
    if ifcopenshell.util.element.get_container(window) != storey:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[window],
                                                        relating_structure=storey)
        guid.stamp(rel, storey.GlobalId, "contains")
    _placement(doc, window, storey, frame)
    _body(doc, window, state)
    _opening(doc, window, storey, state, frame)
    props.write_pset(doc, window, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        {k: state[k] for k in STATE_KEYS if k != "storey"}, ensure_ascii=False,
        sort_keys=True))})
    props.write_pset(doc, window, "Pset_WindowCommon", {"Reference": state["code"],
                                                        "IsExternal": True})
    area = state["width"] * state["length"]
    props.write_qto(doc, window, "Qto_WindowBaseQuantities", {
        "Width": state["width"], "Height": state["length"], "Area": area,
        "Perimeter": 2 * (state["width"] + state["length"])})
    doc.changed.add(window.GlobalId)


def remove(doc: Document, window) -> set[str]:
    gone = {window.GlobalId}
    for rel in list(window.FillsVoids or ()):
        doc.ifc.remove(rel)
    opening = doc.find(opening_id(window.GlobalId))
    if opening is not None:
        for rel in list(opening.VoidsElements):
            gone.add(rel.RelatingBuildingElement.GlobalId)
            doc.ifc.remove(rel)
        props.remove_pset(doc, opening, OPENING_PSET)
        _remove_product(doc, opening)
    _clear_styles(doc, window)
    _remove_product(doc, window)
    return gone


def _remove_product(doc: Document, element) -> None:
    from brasbim.core import fragment

    shape = element.Representation
    element.Representation = None
    ifcopenshell.api.root.remove_product(doc.ifc, product=element)
    if shape is not None:
        fragment.remove(doc.ifc, shape)


# --- operações ---------------------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    window = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcWindow")
    window.GlobalId = op.id
    try:
        write(doc, window, copy.deepcopy(op.data))
    except Exception:
        remove(doc, window)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    return remove(doc, doc.get(op.id, "IfcWindow"))


def _edit(doc: Document, op: Op) -> set[str]:
    window = doc.get(op.id, "IfcWindow")
    state = read_state(window)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"skylight.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    write(doc, window, state)
    return {op.id}


register_inverse_pair("skylight.create", _create, "skylight.delete", _delete)
register("skylight.edit", _edit, invert_swap)


def hosted_by(doc: Document, host_gid: str) -> list:
    return [w for w in all_skylights(doc) if read_state(w)["host"] == host_gid]


def derive(doc: Document, dirty: set[str]) -> None:
    """A laje, a cobertura (ou uma água dela) ou o tipo que mudou refaz a claraboia."""
    from brasbim.core.structure import roofs

    found = {}
    touched = set(dirty) | set(doc.changed)
    for w in all_skylights(doc):
        if w.GlobalId in dirty:
            continue
        state = read_state(w)
        host = doc.find(state["host"])
        if host is None:
            continue
        related = {host.GlobalId}
        if host.is_a("IfcRoof"):
            related |= {p.GlobalId for p in roofs.parts_of(host)}
        t = ifcopenshell.util.element.get_type(roofs.parts_of(host)[0] if host.is_a(
            "IfcRoof") and roofs.parts_of(host) else host)
        if t is not None:
            related.add(t.GlobalId)
        if related & touched:
            found[w.GlobalId] = (w, state)
    for gid in sorted(found):
        w, state = found[gid]
        write(doc, w, state)


register_derive(derive)


# --- comandos ------------------------------------------------------------------------------


def next_code(doc: Document) -> str:
    used = {read_state(w)["code"] for w in all_skylights(doc)}
    n = 1
    while f"CL{n}" in used:
        n += 1
    return f"CL{n}"


def host_at(doc: Document, storey, point):
    """A cobertura ou a laje do pavimento sob o ponto (a cobertura primeiro)."""
    from brasbim.core.structure import roofs, slabs

    decomposition = ifcopenshell.util.element.get_decomposition(storey)
    for e in sorted(decomposition, key=lambda x: x.GlobalId):
        if e.is_a("IfcRoof") and roofs.is_roof(e) and any(
                _inside(f.ring, point) for f in roofs.faces(roofs.read_state(doc, e))):
            return e
    for e in sorted(decomposition, key=lambda x: x.GlobalId):
        if e.is_a("IfcSlab") and not roofs.is_part(e):
            try:
                if _inside(slabs.read_state(doc, e)["outline"], point):
                    return e
            except OpError:
                continue
    return None


def create_skylight(doc: Document, storey, point, width: float = 0.8, length: float = 1.2,
                    angle: float = 0.0, host=None, code: str | None = None):
    from brasbim.core.ops import Transaction

    storey = doc.get(storey if isinstance(storey, str) else storey.GlobalId)
    host = host or host_at(doc, storey, point)
    if host is None:
        raise OpError("clique sobre uma laje ou uma cobertura")
    host = doc.get(host if isinstance(host, str) else host.GlobalId)
    state = {**default_state(), "storey": storey.GlobalId, "host": host.GlobalId,
             "center": [float(point[0]), float(point[1])], "width": float(width),
             "length": float(length), "angle": float(angle), "code": code or next_code(doc)}
    validate(state)
    support(doc, state)  # recusa fora da laje ou da cobertura
    return Transaction("Criar claraboia", [Op("skylight.create", guid.new(), data=state)])


def edit_skylight(doc: Document, window, **changes):
    from brasbim.core.ops import Transaction

    window = doc.get(window if isinstance(window, str) else window.GlobalId, "IfcWindow")
    state = read_state(window)
    after = {k: copy.deepcopy(v) for k, v in changes.items() if state.get(k) != v}
    unknown = set(after) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    new = {**state, **after}
    validate(new)
    support(doc, new)
    if not after:
        return Transaction("Editar claraboia", [])
    return Transaction("Editar claraboia", [Op(
        "skylight.edit", window.GlobalId, before={k: copy.deepcopy(state[k]) for k in after},
        after=after)])


def delete_ops(doc: Document, window) -> list[Op]:
    return [Op("skylight.delete", window.GlobalId, data=read_state(window))]
