# SPDX-License-Identifier: LGPL-3.0-or-later
"""Espessura livre de parede e laje (``spec/ui/43-estilos-3d-e-espessura-livre.md`` §3).

Digitar uma espessura diferente da do tipo dá ao elemento uma **variante** do tipo: um
``IfcWallType``/``IfcSlabType`` de verdade, com o próprio ``IfcMaterialLayerSet``, igual ao
tipo de origem a não ser pela **camada que estica** (a estrutural, ``LoadBearing``; sem
ela, a mais grossa). Assim quem lê o IFC vê a espessura e as camadas certas.

A variante guarda a origem no Pset ``BrasBim_Variante`` (``Origem`` = GlobalId do tipo de
origem, ``Espessura``). Mudar as camadas, os materiais, o nome ou o estilo de planta do
tipo de origem refaz as variantes (derivação, mantendo a espessura delas). A variante que
fica sem elemento sai na mesma transação.

Operação: ``type_variant.set`` (``id`` = tipo; ``before``/``after`` = {"origin",
"thickness"} ou ``None``), que grava ou apaga o Pset.
"""

from __future__ import annotations

import copy

import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, invert_swap, register, register_derive

PSET = "BrasBim_Variante"
MIN_LAYER = 0.01  # m: a camada que estica não fica mais fina que isto
_TOL = 1e-6


# --- tipos de parede e de laje ---------------------------------------------------------


class _Kind:
    def __init__(self, ifc_class, prefix, read, write_layers, layer_set):
        self.ifc_class, self.prefix = ifc_class, prefix
        self.read, self.write_layers, self.layer_set = read, write_layers, layer_set


def _kind(element_type) -> _Kind:
    from brasbim.core.structure import types as st_types
    from brasbim.core.walls import types as wall_types

    if element_type.is_a("IfcWallType"):
        return _Kind("IfcWallType", "wall_type", wall_types.read, wall_types._write_layers,
                     wall_types.layer_set)
    if element_type.is_a("IfcSlabType"):
        return _Kind("IfcSlabType", "slab_type", st_types.read_slab_type,
                     st_types._write_slab_layers, st_types.layer_set)
    raise OpError("só parede e laje têm espessura livre")


def type_thickness(element_type) -> float:
    return sum(float(x.LayerThickness) for x in _kind(element_type).layer_set(
        element_type).MaterialLayers)


def read(element_type) -> dict | None:
    """{"origin", "thickness"} da variante, ou ``None`` num tipo comum."""
    values = ifcopenshell.util.element.get_pset(element_type, PSET, should_inherit=False)
    if not values or not values.get("Origem"):
        return None
    return {"origin": values["Origem"], "thickness": float(values.get("Espessura") or 0.0)}


def origin_of(doc: Document, element_type):
    """O tipo de origem (o próprio tipo, se não é variante)."""
    info = read(element_type)
    found = doc.find(info["origin"]) if info else None
    return found if found is not None else element_type


def variants_of(doc: Document, origin) -> list:
    out = []
    for t in doc.ifc.by_type(origin.is_a()):
        info = read(t)
        if info and info["origin"] == origin.GlobalId:
            out.append(t)
    return sorted(out, key=lambda t: read(t)["thickness"])


def is_variant(element_type) -> bool:
    return read(element_type) is not None


def _cm(value: float) -> str:
    text = f"{value * 100:.1f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def variant_name(origin_name: str, thickness: float) -> str:
    return f"{origin_name} · {_cm(thickness)} cm"


def stretch_index(layers: list[dict]) -> int:
    """A camada que estica: a primeira estrutural; sem ela, a mais grossa."""
    for i, layer in enumerate(layers):
        if layer.get("category") == "LoadBearing":
            return i
    return max(range(len(layers)), key=lambda i: (layers[i]["thickness"], -i))


def stretched(layers: list[dict], thickness: float) -> list[dict]:
    """Camadas com a soma ``thickness``: a diferença vai toda para a camada que estica."""
    layers = copy.deepcopy(layers)
    i = stretch_index(layers)
    total = sum(x["thickness"] for x in layers)
    value = layers[i]["thickness"] + (thickness - total)
    if value < MIN_LAYER - _TOL:
        name = layers[i].get("material") or "a camada estrutural"
        raise OpError(f"espessura pequena demais: {name} ficaria com menos de "
                      f"{_cm(MIN_LAYER)} cm (mínimo {_cm(total - layers[i]['thickness'] + MIN_LAYER)} cm)")
    layers[i]["thickness"] = round(value, 9)
    return layers


def variant_state(origin, thickness: float) -> dict:
    """Estado de criação do tipo variante (``wall_type.create``/``slab_type.create``)."""
    k = _kind(origin)
    state = copy.deepcopy(k.read(origin))
    state["layers"] = stretched(state["layers"], thickness)
    state["name"] = variant_name(origin.Name or "Tipo", thickness)
    return state


# --- comando ---------------------------------------------------------------------------


def _element_state(doc: Document, element):
    from brasbim.core.structure import slabs
    from brasbim.core.walls.wall import read_state as wall_state

    if element.is_a("IfcWall"):
        return wall_state(doc, element)
    if element.is_a("IfcSlab"):
        from brasbim.core.structure import roofs

        if roofs.is_part(element):
            raise OpError("a espessura da cobertura vem do tipo dela")
        state = slabs.read_state(doc, element)
        if state["foreign"] is not None:
            raise OpError("laje de outra origem: a espessura vem do corpo original")
        return state
    raise OpError("só parede e laje têm espessura livre")


def thickness_of(doc: Document, element) -> float:
    t = ifcopenshell.util.element.get_type(element)
    if t is None:
        raise OpError("elemento sem tipo")
    return type_thickness(t)


def _edit_type(doc: Document, element, type_id: str):
    if element.is_a("IfcWall"):
        from brasbim.core.walls.commands import edit_wall

        return edit_wall(doc, element, type=type_id)
    from brasbim.core.structure.commands import edit_element

    return edit_element(doc, element, type=type_id)


def ensure_type(doc: Document, type_id: str, thickness: float | None):
    """(GlobalId do tipo com essa espessura, transação que o cria se falta). O de origem,
    uma variante existente ou uma variante nova; ``thickness`` ``None`` = a do tipo."""
    from brasbim.core.ops.history import Transaction

    current = doc.get(type_id)
    if thickness is None:
        return current.GlobalId, Transaction("Espessura", [])
    thickness = float(thickness)
    if thickness <= 0:
        raise OpError("a espessura deve ser maior que zero")
    origin = origin_of(doc, current)
    k = _kind(origin)
    if abs(type_thickness(origin) - thickness) < _TOL:
        return origin.GlobalId, Transaction("Espessura", [])
    for v in variants_of(doc, origin):
        if abs(read(v)["thickness"] - thickness) < _TOL:
            return v.GlobalId, Transaction("Espessura", [])
    target = guid.new()
    return target, Transaction("Espessura", [
        Op(f"{k.prefix}.create", target, data=variant_state(origin, thickness)),
        Op("type_variant.set", target, before=None,
           after={"origin": origin.GlobalId, "thickness": thickness})])


def create_with(doc: Document, type_id: str, thickness: float | None, build):
    """``build(tipo)`` (criar parede ou laje) com o tipo dessa espessura; a variante nova,
    se precisar, entra na mesma transação (barra Opções, spec/ui 43 §3.1)."""
    from brasbim.core.ops.history import Transaction, combine

    target, pre = ensure_type(doc, type_id, thickness)
    if not pre.ops:
        return build(target)
    built = []
    tx = combine(doc, "", [lambda: pre, lambda: built.append(build(target)) or built[0]])
    return Transaction(built[0].label, tx.ops)


def _set_one(doc: Document, element, thickness: float):
    """Transação que troca o tipo do elemento pelo tipo com essa espessura."""
    from brasbim.core.ops.history import Transaction

    state = _element_state(doc, element)
    current = doc.get(state["type"])
    target, pre = ensure_type(doc, current.GlobalId, thickness)
    if target == current.GlobalId:
        return Transaction("Espessura", [])
    if pre.ops:  # o tipo novo tem de existir para a troca ser montada
        from brasbim.core.ops.history import combine

        return combine(doc, "Espessura", [lambda: pre,
                                          lambda: _edit_type(doc, element, target)])
    return Transaction("Espessura", _edit_type(doc, element, target).ops)


def _cleanup(doc: Document, types: list):
    """Apaga as variantes que ficaram sem elemento."""
    from brasbim.core.ops.history import Transaction

    ops = []
    for t in types:
        t = doc.find(t)
        if t is None or not is_variant(t) or ifcopenshell.util.element.get_types(t):
            continue
        k = _kind(t)
        info = read(t)
        ops += [Op("type_variant.set", t.GlobalId, before=info, after=None),
                Op(f"{k.prefix}.delete", t.GlobalId, data=copy.deepcopy(k.read(t)))]
    return Transaction("Espessura", ops)


def set_thickness(doc: Document, elements, thickness: float):
    """Transação "Espessura": cada parede ou laje passa a ter a espessura ``thickness``
    (variante do tipo, criada se faltar; a espessura do tipo volta ao tipo de origem)."""
    from brasbim.core.ops.history import combine

    thickness = float(thickness)
    if thickness <= 0:
        raise OpError("a espessura deve ser maior que zero")
    elements = list(elements)
    if not elements:
        raise OpError("selecione paredes ou lajes")
    old_types = sorted({ifcopenshell.util.element.get_type(e).GlobalId for e in elements
                        if ifcopenshell.util.element.get_type(e) is not None})
    builders = [lambda e=e: _set_one(doc, e, thickness) for e in elements]
    builders.append(lambda: _cleanup(doc, old_types))
    label = "Espessura" if len(elements) == 1 else f"Espessura de {len(elements)} elementos"
    return combine(doc, label, builders)


# --- operação e derivação --------------------------------------------------------------


def _apply_set(doc: Document, op: Op) -> set[str]:
    t = doc.get(op.id)
    current = read(t)
    if current != op.before and not (
            current and op.before and current["origin"] == op.before["origin"]
            and abs(current["thickness"] - op.before["thickness"]) < _TOL):
        raise OpError(f"type_variant.set {op.id}: variante é {current!r}, "
                      f"esperado {op.before!r}")
    if op.after is None:
        props.remove_pset(doc, t, PSET)
    else:
        f = doc.ifc
        props.write_pset(doc, t, PSET, {
            "Origem": f.createIfcLabel(op.after["origin"]),
            "Espessura": f.createIfcPositiveLengthMeasure(float(op.after["thickness"]))})
    return {op.id}


register("type_variant.set", _apply_set, invert_swap)


def _same_layers(a: list[dict], b: list[dict]) -> bool:
    if len(a) != len(b):
        return False
    return all(x.get("material") == y.get("material")
               and abs(x["thickness"] - y["thickness"]) < _TOL
               and {k: v for k, v in x.items() if k not in ("material", "thickness")}
               == {k: v for k, v in y.items() if k not in ("material", "thickness")}
               for x, y in zip(a, b, strict=True))


def derive(doc: Document, dirty: set[str]) -> None:
    """O tipo de origem mudou: refaz camadas, nome e estilo das variantes dele e põe as
    variantes na lista suja (os corpos dos elementos são refeitos depois)."""
    from brasbim.core.walls import types as wall_types

    for gid in sorted(dirty):
        origin = doc.find(gid)
        if origin is None or not (origin.is_a("IfcWallType") or origin.is_a("IfcSlabType")) \
                or is_variant(origin):
            continue
        for variant in variants_of(doc, origin):
            k = _kind(variant)
            try:
                want = variant_state(origin, read(variant)["thickness"])
            except OpError:
                continue  # a camada que estica ficaria fina demais: mantém a variante
            have = k.read(variant)
            changed = False
            if not _same_layers(have["layers"], want["layers"]):
                k.write_layers(doc, k.layer_set(variant), want["layers"])
                changed = True
            if variant.Name != want["name"]:
                variant.Name = want["name"]
                k.layer_set(variant).LayerSetName = want["name"]
                changed = True
            if have.get("plan_style") != want.get("plan_style"):
                wall_types.write_plan_style(doc, variant, want.get("plan_style"))
                changed = True
            if changed:
                dirty.add(variant.GlobalId)


register_derive(derive, first=True)
