# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre portas e janelas, cada uma convertida em uma ``Transaction``.

Como nos comandos da parede, aqui só se lê o modelo para montar as operações de
``porta.md`` §5.2 e ``janela.md`` §5.2; quem altera o modelo é ``History.commit``.
As funções ``*_door`` valem também para janelas (a classe do elemento escolhe as
operações ``window.*``); ``create_window`` e ``*_window_type`` são as da janela.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from types import ModuleType

import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, params, window_types
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.base import same_value
from brasbim.core.ops.history import combine
from brasbim.core.walls import commands as wall_cmd
from brasbim.core.walls import openings

log = logging.getLogger(__name__)

# Campos da esquadria que pertencem à abertura (porta §3.1) → campo da abertura.
_OPENING_KEYS = {"wall": "wall", "distance": "distance", "width": "width", "height": "height",
                 "base": "sill"}
# Mudanças que convertem uma esquadria de outra origem em paramétrica (porta §6.6).
_CONVERTS = ("width", "height", "type", "opens_to", "align", "offset", "hinges")


@dataclass(frozen=True)
class _Kind:
    ifc_class: str
    type_class: str
    prefix: str  # das operações: door / window
    types: ModuleType
    noun: str
    plural: str
    shared: tuple[str, ...]  # campos do tipo iguais nas duas variantes de mão

    def hand(self, state: dict) -> str | None:
        if self.prefix == "door":
            return params.hand_of(state["operation_type"])
        return window_types.hand(state)

    def mirror_fields(self, state: dict) -> dict:
        if self.prefix == "door":
            mirror = door_types.mirrored(state, None)
            return {"operation_type": mirror["operation_type"], "panels": mirror["panels"]}
        return window_types.mirror_fields(state)


DOOR = _Kind("IfcDoor", "IfcDoorType", "door", door_types, "porta", "portas",
             ("lining", "materials", "defaults"))
WINDOW = _Kind("IfcWindow", "IfcWindowType", "window", window_types, "janela", "janelas",
               ("materials", "defaults", "code"))
# Campos do tipo que, mudando, mudam também (espelhados) na variante.
_MIRRORED = {"door": ("operation_type", "panels"), "window": ("partitioning", "lining", "panels")}


def kind(entity) -> _Kind:
    """Porta ou janela, pelo elemento ou pelo tipo."""
    return WINDOW if entity.is_a("IfcWindow") or entity.is_a("IfcWindowType") else DOOR


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def _element(doc: Document, element):
    element = doc.get(_gid(element), "IfcElement")
    if not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
        raise OpError(f"{element.GlobalId} não é porta nem janela")
    return element


def _type(doc: Document, element_type):
    element_type = doc.get(_gid(element_type), "IfcTypeObject")
    if not (element_type.is_a("IfcDoorType") or element_type.is_a("IfcWindowType")):
        raise OpError(f"{element_type.GlobalId} não é tipo de porta nem de janela")
    return element_type


# --- tipos -------------------------------------------------------------------------


def create_door_type(doc: Document, name: str, operation_type: str = "SINGLE_SWING_LEFT",
                     **options) -> Transaction:
    """Tipo de porta. ``lining`` e ``defaults`` podem ser parciais (completam o padrão);
    sem ``panels``, as folhas vêm da operação, com a espessura ``panel_depth``."""
    data = door_types.default_state(operation_type)
    depth = options.pop("panel_depth", params.DEFAULT_PANEL_DEPTH)
    data["panels"] = params.default_panels(operation_type, depth)
    for key in ("lining", "defaults", "materials"):
        data[key].update(options.pop(key, {}))
    unknown = set(options) - set(door_types.STATE_KEYS) - {"predefined_type"}
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data.update(options, name=name)
    door_types.validate(data)
    return Transaction("Criar tipo de porta", [Op("door_type.create", guid.new(), data=data)])


def create_window_type(doc: Document, name: str, partitioning: str = "DOUBLE_PANEL_VERTICAL",
                       operations=None, **options) -> Transaction:
    """Tipo de janela (janela §3.2). ``operations``: uma por caixilho, na ordem das
    posições da divisão (padrão: de correr). ``lining``, ``defaults``, ``materials`` e
    ``frame`` (``frame_depth``, ``frame_thickness`` de todos os caixilhos) podem ser
    parciais."""
    if partitioning not in params.WINDOW_PARTITIONINGS:
        raise OpError(f"divisão de janela inválida: {partitioning!r}")
    data = window_types.default_state(partitioning, operations)
    frame = options.pop("frame", {})
    data["panels"] = [{**p, **frame} for p in data["panels"]]
    for key in ("lining", "defaults", "materials"):
        data[key].update(options.pop(key, {}))
    unknown = set(options) - set(window_types.STATE_KEYS) - {"predefined_type"}
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data.update(options, name=name)
    window_types.validate(data)
    return Transaction("Criar tipo de janela",
                       [Op("window_type.create", guid.new(), data=data)])


def _partner(doc: Document, state: dict):
    """Variante com a outra mão, se existir."""
    return doc.find(state["variant"]) if state["variant"] else None


def _partner_changes(k: _Kind, state: dict, partner_state: dict, changes: dict) -> dict:
    """O que muda na variante quando o tipo muda: os campos comuns, o nome (com o sufixo
    dela) e, espelhados, operação/divisão e caixilhos."""
    out = {key: changes[key] for key in k.shared if key in changes}
    new = {**state, **changes}
    if "name" in changes:
        hand = k.hand(partner_state)
        out["name"] = params.base_name(new["name"]) + params.HAND_SUFFIX[hand]
    if any(key in changes for key in _MIRRORED[k.prefix]):
        if k.hand(new) is None:
            raise OpError("um tipo com variante de mão só aceita caixilhos com mão")
        out.update(k.mirror_fields(new))
    return {key: v for key, v in out.items() if not same_value(partner_state[key], v)}


def edit_door_type(doc: Document, door_type, **changes) -> Transaction:
    """Altera o tipo de porta ou de janela; a variante com a outra mão acompanha
    (porta §2.2, janela §2.4)."""
    door_type = _type(doc, door_type)
    k = kind(door_type)
    state = k.types.read(door_type)
    unknown = set(changes) - set(k.types.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    k.types.validate({**state, **changes})
    before = {key: state[key] for key in changes}
    ops = [Op(f"{k.prefix}_type.edit", door_type.GlobalId, before=before, after=changes)]
    partner = _partner(doc, state)
    if partner is not None and "variant" not in changes:
        partner_state = k.types.read(partner)
        partner_changes = _partner_changes(k, state, partner_state, changes)
        if partner_changes:
            k.types.validate({**partner_state, **partner_changes})
            ops.append(Op(f"{k.prefix}_type.edit", partner.GlobalId,
                          before={key: partner_state[key] for key in partner_changes},
                          after=partner_changes))
    return Transaction(f"Editar tipo de {k.noun}", ops)


edit_window_type = edit_door_type


def delete_door_type(doc: Document, door_type) -> Transaction:
    """Exclui um tipo sem esquadrias (porta §6.4); a variante dele perde o vínculo."""
    door_type = _type(doc, door_type)
    k = kind(door_type)
    used = ifcopenshell.util.element.get_types(door_type)
    if used:
        raise OpError(f"o tipo {door_type.Name} é usado por {len(used)} {k.noun}(s)")
    state = k.types.read(door_type)
    ops = []
    partner = _partner(doc, state)
    if partner is not None and k.types.read(partner)["variant"] == door_type.GlobalId:
        ops.append(Op(f"{k.prefix}_type.edit", partner.GlobalId,
                      before={"variant": door_type.GlobalId}, after={"variant": None}))
    from brasbim.core.quantities import tables  # o tipo sai do filtro das tabelas

    ops += tables.refs_removed_ops(doc, door_type.GlobalId)
    ops.append(Op(f"{k.prefix}_type.delete", door_type.GlobalId, data=state))
    return Transaction(f"Excluir tipo de {k.noun}", ops)


delete_window_type = delete_door_type


def _hand_variant(doc: Document, k: _Kind, type_id: str, state: dict, hinges: str):
    """Tipo com a mão pedida: o próprio, a variante existente ou uma variante nova
    (``*_type.create`` + vínculo no original). Devolve (GlobalId, operações)."""
    if hinges not in params.HINGES:
        raise OpError(f"lado das dobradiças inválido: {hinges!r}")
    hand = k.hand(state)
    if hand is None:
        raise OpError(f"o tipo {state['name']} não tem mão (lado das dobradiças)")
    if hand == hinges:
        return type_id, []
    if state["variant"] and doc.find(state["variant"]) is not None:
        return state["variant"], []
    variant = guid.new()
    return variant, [
        Op(f"{k.prefix}_type.create", variant,
           data=copy.deepcopy(k.types.mirrored(state, type_id))),
        Op(f"{k.prefix}_type.edit", type_id, before={"variant": state["variant"]},
           after={"variant": variant}),
    ]


# --- esquadrias --------------------------------------------------------------------


def create_door(doc: Document, door_type, wall, distance: float, width: float | None = None,
                height: float | None = None, base: float | None = None,
                hinges: str | None = None, **options) -> Transaction:
    """Porta (ou janela, com um tipo de janela) num vão novo da parede, a ``distance``
    do início dela (porta §4, janela §4).

    Sem ``width``/``height``/``base``, valem as dimensões padrão do tipo (na janela,
    ``base`` é o peitoril). ``hinges`` (``left``/``right``) escolhe a variante de mão do
    tipo, criada se faltar. ``options``: ``opens_to``, ``align``, ``offset``, ``name``,
    ``common``.
    """
    door_type = _type(doc, door_type)
    k = kind(door_type)
    tstate = k.types.read(door_type)
    defaults = tstate["defaults"]
    opening_tx = wall_cmd.create_opening(
        doc, wall, distance,
        defaults["width"] if width is None else width,
        defaults["height"] if height is None else height,
        sill=defaults["base"] if base is None else base)
    unknown = set(options) - set(doors.STATE_KEYS) - {"foreign"}
    if unknown or "foreign" in options:
        raise OpError(f"parâmetros desconhecidos: {sorted(set(options) - set(doors.STATE_KEYS))}")
    type_id, type_ops = door_type.GlobalId, []
    if hinges is not None:
        type_id, type_ops = _hand_variant(doc, k, door_type.GlobalId, tstate, hinges)
    data = {**doors.default_state(), **options, "type": type_id}
    if data["opens_to"] not in params.OPENS_TO or data["align"] not in params.ALIGNS:
        raise OpError("sentido de abertura ou alinhamento inválido")
    opening_id, door_id = opening_tx.ops[0].id, guid.new()
    return Transaction(f"Criar {k.noun}", [
        *opening_tx.ops,
        *type_ops,
        Op(f"{k.prefix}.create", door_id, data=data),
        Op("filling.attach", door_id, data={"opening": opening_id}),
    ])


def create_window(doc: Document, window_type, wall, distance: float, width=None, height=None,
                  base=None, hinges=None, **options) -> Transaction:
    """Janela num vão novo (janela §4); ``base`` é o peitoril."""
    window_type = doc.get(_gid(window_type), "IfcWindowType")
    return create_door(doc, window_type, wall, distance, width, height, base, hinges,
                       **options)


def opening_of(door):
    rels = door.FillsVoids
    return rels[0].RelatingOpeningElement if rels else None


def _type_named(doc: Document, type_class: str, name: str):
    return next((t for t in doc.ifc.by_type(type_class) if t.Name == name), None)


def _converted_type(doc: Document, door, state: dict, opening: dict):
    """Tipo do BrasBim para uma esquadria de outra origem que vira paramétrica
    (porta §6.6): a operação (porta) ou a divisão (janela) vem da ocorrência ou do tipo
    de origem; o nome, do tipo de origem. Reaproveita o tipo já criado numa conversão
    anterior. Devolve (GlobalId, operações)."""
    k = kind(door)
    foreign = state["foreign"]
    source = ifcopenshell.util.element.get_type(door)
    name = (source.Name if source else None) or door.Name or k.noun.capitalize()
    found = _type_named(doc, k.type_class, name)
    if found is not None and found != source and ifcopenshell.util.element.get_pset(
            found, params.TYPE_PSET):
        return found.GlobalId, []
    if found is not None:
        name = f"{name} (BrasBim)"
        found = _type_named(doc, k.type_class, name)
        if found is not None:
            return found.GlobalId, []
    if k is DOOR:
        operation = foreign["operation_type"] or (source.OperationType if source else None)
        if operation not in params.DOOR_OPERATIONS or operation == "NOTDEFINED":
            operation = "SINGLE_SWING_LEFT"
        data = door_types.default_state(operation)
    else:
        partitioning = foreign["operation_type"] or (source.PartitioningType if source
                                                     else None)
        if partitioning not in params.WINDOW_PARTITIONINGS:
            partitioning = "SINGLE_PANEL"
        data = window_types.default_state(partitioning, ["FIXEDCASEMENT"])
    data["name"] = name
    data["defaults"].update(width=opening["width"], height=opening["height"],
                            base=opening["sill"])
    type_id = guid.new()
    return type_id, [Op(f"{k.prefix}_type.create", type_id, data=data)]


def edit_door(doc: Document, door, hinges: str | None = None, **changes) -> Transaction:
    """Altera a porta ou a janela. ``wall``, ``distance``, ``width``, ``height`` e
    ``base`` mudam a abertura (``opening.edit``); os demais, a esquadria
    (``door.edit``/``window.edit``). ``hinges`` troca o tipo pela variante com aquela mão
    (porta §2.2, janela §2.4).

    Esquadria de outra origem (porta §6.6): mover e mudar nome ou Psets preservam o
    corpo; as outras mudanças a convertem em esquadria paramétrica, com aviso.
    """
    door = _element(doc, door)
    k = kind(door)
    unknown = set(changes) - set(doors.STATE_KEYS) - set(_OPENING_KEYS)
    if unknown or "foreign" in changes:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown | ({'foreign'} & set(changes)))}")
    state = doors.read_state(door)
    opening = opening_of(door)
    convert = state["foreign"] is not None and (
        hinges is not None or any(key in changes for key in _CONVERTS))
    ops = []
    opening_changes = {_OPENING_KEYS[key]: changes.pop(key) for key in list(changes)
                       if key in _OPENING_KEYS}
    if opening_changes:
        if opening is None:
            raise OpError(f"{k.noun} {door.GlobalId} não está numa abertura")
        if (state["foreign"] is not None and not convert
                and door.ObjectPlacement.PlacementRelTo != opening.ObjectPlacement):
            raise OpError(f"a {k.noun} importada não está posicionada em relação à abertura "
                          "e não acompanharia o vão; mude o tamanho ou o tipo para convertê-la")
        ops += wall_cmd.edit_opening(doc, opening, **opening_changes).ops
    if changes.get("type") is not None:
        changes["type"] = doc.get(_gid(changes["type"]), k.type_class).GlobalId
    type_states = {}  # tipos criados nesta transação
    if convert:
        if opening is None:
            raise OpError(f"{k.noun} {door.GlobalId} não está numa abertura")
        if changes.get("type") is None:
            after_opening = {**openings.read_state(opening), **opening_changes}
            changes["type"], type_ops = _converted_type(doc, door, state, after_opening)
            ops += type_ops
            type_states.update({op.id: op.data for op in type_ops})
        if changes["type"] in type_states:
            new_type = {**k.types.default_state(), **type_states[changes["type"]]}
            defaults = ({"Reference": window_types.code(new_type), "Status": "NEW",
                         "IsExternal": True} if k is WINDOW
                        else doors.common_defaults(new_type["name"]))
        else:
            defaults = doors.type_common_defaults(doc.get(changes["type"]))
        changes.setdefault("common", {key: v for key, v in state["common"].items()
                                      if defaults.get(key) != v})
        changes["foreign"] = None
        log.warning("%s %s de outra origem convertida em %s paramétrica: o corpo original "
                    "será substituído", k.noun, door.GlobalId, k.noun)
    if hinges is not None:
        type_id = changes.get("type") or state["type"]
        tstate = type_states.get(type_id) or k.types.read(doc.get(type_id, k.type_class))
        changes["type"], variant_ops = _hand_variant(doc, k, type_id, tstate, hinges)
        ops += variant_ops
    changes = {key: v for key, v in changes.items() if not same_value(state[key], v)}
    if changes:
        before = {key: state[key] for key in changes}
        ops.append(Op(f"{k.prefix}.edit", door.GlobalId, before=before, after=changes))
    label = f"Converter e editar {k.noun}" if convert else f"Editar {k.noun}"
    return Transaction(label, ops)


edit_window = edit_door


def _plural(doc: Document, door_list) -> str:
    kinds = {kind(_element(doc, d)) for d in door_list}
    return kinds.pop().plural if len(kinds) == 1 else "esquadrias"


def edit_doors(doc: Document, door_list, hinges: str | None = None, **changes) -> Transaction:
    """Edição em lote (spec/ui 02 §9): o mesmo ``edit_door`` em cada esquadria, numa
    transação só (a variante de mão criada para a primeira serve às outras)."""
    door_list = list(door_list)
    if len(door_list) == 1:
        return edit_door(doc, door_list[0], hinges=hinges, **changes)
    return combine(doc, f"Editar {len(door_list)} {_plural(doc, door_list)}",
                   [lambda d=d: edit_door(doc, d, hinges=hinges, **copy.deepcopy(changes))
                    for d in door_list])


edit_windows = edit_doors


def flip_each(doc: Document, door_list, flip) -> Transaction:
    """``flip_hinges`` ou ``flip_opening`` em cada esquadria, numa transação só."""
    door_list = list(door_list)
    if len(door_list) == 1:
        return flip(doc, door_list[0])
    tx = combine(doc, "", [lambda d=d: flip(doc, d) for d in door_list])
    tx.label = f"{flip(doc, door_list[0]).label} ({len(door_list)} {_plural(doc, door_list)})"
    return tx


def hand(doc: Document, door) -> str | None:
    """Mão (lado das dobradiças) da esquadria, ou ``None``."""
    door = _element(doc, door)
    k = kind(door)
    state = doors.read_state(door)
    if state["foreign"] is not None:
        if k is WINDOW:
            return None
        operation = state["foreign"]["operation_type"] or (
            state["type"] and doc.get(state["type"]).OperationType) or ""
        return params.hand_of(operation)
    return k.hand(k.types.read(doc.get(state["type"], k.type_class)))


def flip_hinges(doc: Document, door) -> Transaction:
    """Inverte a mão (porta §5.1, janela §2.4): troca o tipo pela variante."""
    door = _element(doc, door)
    current = hand(doc, door)
    if current is None:
        what = "lado de dobradiças" if kind(door) is DOOR else "mão"
        raise OpError(f"a {kind(door).noun} não tem {what} para inverter")
    tx = edit_door(doc, door, hinges="right" if current == "left" else "left")
    tx.label = "Inverter dobradiças" if kind(door) is DOOR else "Inverter mão"
    return tx


def flip_opening(doc: Document, door) -> Transaction:
    """Inverte o sentido de abertura (porta §5.1): só o posicionamento muda."""
    door = _element(doc, door)
    opens_to = doors.read_state(door)["opens_to"]
    tx = edit_door(doc, door, opens_to="right" if opens_to == "left" else "left")
    tx.label = "Inverter sentido de abertura"
    return tx


def delete_ops(door) -> list[Op]:
    """Desliga a esquadria da abertura e a exclui (sem a abertura)."""
    ops = [Op("filling.detach", door.GlobalId,
              data={"opening": rel.RelatingOpeningElement.GlobalId}) for rel in door.FillsVoids]
    ops.append(Op(f"{kind(door).prefix}.delete", door.GlobalId, data=doors.read_state(door)))
    return ops


def delete_door(doc: Document, door, keep_opening: bool = False) -> Transaction:
    """Exclui a esquadria e a abertura dela (porta §6.4); ``keep_opening`` mantém o vão."""
    door = _element(doc, door)
    k = kind(door)
    if not doors.is_parametric(door):
        raise OpError(f"excluir {k.noun} de outra origem ainda não é suportado; "
                      "converta-a antes (mude o tamanho ou o tipo)")
    opening = opening_of(door)
    ops = delete_ops(door)
    label = (f"Remover {k.noun} e manter vão" if keep_opening
             else f"Excluir {k.noun}")
    if opening is not None and not keep_opening:
        ops.append(Op("opening.delete", opening.GlobalId, data=openings.read_state(opening)))
    return Transaction(label, ops)


delete_window = delete_door
