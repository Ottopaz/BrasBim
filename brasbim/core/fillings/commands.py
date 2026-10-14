# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre portas, cada uma convertida em uma ``Transaction``.

Como nos comandos da parede, aqui só se lê o modelo para montar as operações de
``porta.md`` §5.2; quem altera o modelo é ``History.commit``.
"""

from __future__ import annotations

import copy
import logging

import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.base import same_value
from brasbim.core.walls import commands as wall_cmd
from brasbim.core.walls import openings

log = logging.getLogger(__name__)

# Campos da porta que pertencem à abertura (porta §3.1) → campo da abertura.
_OPENING_KEYS = {"wall": "wall", "distance": "distance", "width": "width", "height": "height",
                 "base": "sill"}
# Mudanças que convertem uma porta de outra origem em porta paramétrica (porta §6.6).
_CONVERTS = ("width", "height", "type", "opens_to", "align", "offset", "hinges")
# Campos do tipo que valem para as duas variantes de mão (porta §2.2).
_SHARED_TYPE_KEYS = ("lining", "materials", "defaults")


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


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


def _partner(doc: Document, state: dict):
    """Variante com a outra mão, se existir."""
    return doc.find(state["variant"]) if state["variant"] else None


def _partner_changes(state: dict, partner_state: dict, changes: dict) -> dict:
    """O que muda na variante quando o tipo muda: marco, materiais, padrões, nome (com o
    sufixo dela) e, espelhadas, operação e folhas."""
    out = {k: changes[k] for k in _SHARED_TYPE_KEYS if k in changes}
    new = {**state, **changes}
    if "name" in changes:
        hand = params.hand_of(partner_state["operation_type"])
        out["name"] = params.base_name(new["name"]) + params.HAND_SUFFIX[hand]
    if "operation_type" in changes or "panels" in changes:
        if params.hand_of(new["operation_type"]) is None:
            raise OpError("um tipo com variante de mão só aceita operação com mão")
        mirror = door_types.mirrored(new, None)
        out["operation_type"], out["panels"] = mirror["operation_type"], mirror["panels"]
    return {k: v for k, v in out.items() if not same_value(partner_state[k], v)}


def edit_door_type(doc: Document, door_type, **changes) -> Transaction:
    """Altera o tipo; a variante com a outra mão acompanha (porta §2.2)."""
    door_type = doc.get(_gid(door_type), "IfcDoorType")
    state = door_types.read(door_type)
    unknown = set(changes) - set(door_types.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    door_types.validate({**state, **changes})
    before = {k: state[k] for k in changes}
    ops = [Op("door_type.edit", door_type.GlobalId, before=before, after=changes)]
    partner = _partner(doc, state)
    if partner is not None and "variant" not in changes:
        partner_state = door_types.read(partner)
        partner_changes = _partner_changes(state, partner_state, changes)
        if partner_changes:
            door_types.validate({**partner_state, **partner_changes})
            ops.append(Op("door_type.edit", partner.GlobalId,
                          before={k: partner_state[k] for k in partner_changes},
                          after=partner_changes))
    return Transaction("Editar tipo de porta", ops)


def delete_door_type(doc: Document, door_type) -> Transaction:
    """Exclui um tipo sem portas (porta §6.4); a variante dele perde o vínculo."""
    door_type = doc.get(_gid(door_type), "IfcDoorType")
    state = door_types.read(door_type)
    ops = []
    partner = _partner(doc, state)
    if partner is not None and door_types.read(partner)["variant"] == door_type.GlobalId:
        ops.append(Op("door_type.edit", partner.GlobalId, before={"variant": door_type.GlobalId},
                      after={"variant": None}))
    ops.append(Op("door_type.delete", door_type.GlobalId, data=state))
    return Transaction("Excluir tipo de porta", ops)


def _hand_variant(doc: Document, type_id: str, state: dict, hinges: str):
    """Tipo com as dobradiças pedidas: o próprio, a variante existente ou uma variante
    nova (``door_type.create`` + vínculo no original). Devolve (GlobalId, operações)."""
    if hinges not in params.HINGES:
        raise OpError(f"lado das dobradiças inválido: {hinges!r}")
    hand = params.hand_of(state["operation_type"])
    if hand is None:
        raise OpError(f"o tipo {state['name']} não tem lado de dobradiças "
                      f"({state['operation_type']})")
    if hand == hinges:
        return type_id, []
    if state["variant"] and doc.find(state["variant"]) is not None:
        return state["variant"], []
    variant = guid.new()
    return variant, [
        Op("door_type.create", variant, data=copy.deepcopy(door_types.mirrored(state, type_id))),
        Op("door_type.edit", type_id, before={"variant": state["variant"]},
           after={"variant": variant}),
    ]


# --- portas ------------------------------------------------------------------------


def create_door(doc: Document, door_type, wall, distance: float, width: float | None = None,
                height: float | None = None, base: float | None = None,
                hinges: str | None = None, **options) -> Transaction:
    """Porta num vão novo da parede, a ``distance`` do início dela (porta §4).

    Sem ``width``/``height``/``base``, valem as dimensões padrão do tipo. ``hinges``
    (``left``/``right``, vista de quem empurra) escolhe a variante de mão do tipo, criada
    se faltar. ``options``: ``opens_to``, ``align``, ``offset``, ``name``, ``common``.
    """
    door_type = doc.get(_gid(door_type), "IfcDoorType")
    tstate = door_types.read(door_type)
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
        type_id, type_ops = _hand_variant(doc, door_type.GlobalId, tstate, hinges)
    data = {**doors.default_state(), **options, "type": type_id}
    if data["opens_to"] not in params.OPENS_TO or data["align"] not in params.ALIGNS:
        raise OpError("sentido de abertura ou alinhamento inválido")
    opening_id, door_id = opening_tx.ops[0].id, guid.new()
    return Transaction("Criar porta", [
        *opening_tx.ops,
        *type_ops,
        Op("door.create", door_id, data=data),
        Op("filling.attach", door_id, data={"opening": opening_id}),
    ])


def opening_of(door):
    rels = door.FillsVoids
    return rels[0].RelatingOpeningElement if rels else None


def _type_named(doc: Document, name: str):
    return next((t for t in doc.ifc.by_type("IfcDoorType") if t.Name == name), None)


def _converted_type(doc: Document, door, state: dict, opening: dict):
    """Tipo do BrasBim para uma porta de outra origem que vira paramétrica (porta §6.6):
    a operação vem da ocorrência ou do tipo de origem; o nome, do tipo de origem.
    Reaproveita o tipo já criado numa conversão anterior. Devolve (GlobalId, operações)."""
    foreign = state["foreign"]
    source = ifcopenshell.util.element.get_type(door)
    operation = foreign["operation_type"] or (source.OperationType if source else None)
    if operation not in params.DOOR_OPERATIONS or operation == "NOTDEFINED":
        operation = "SINGLE_SWING_LEFT"
    name = (source.Name if source else None) or door.Name or "Porta"
    found = _type_named(doc, name)
    if found is not None and found != source and ifcopenshell.util.element.get_pset(
            found, params.TYPE_PSET):
        return found.GlobalId, []
    if found is not None:
        name = f"{name} (BrasBim)"
        found = _type_named(doc, name)
        if found is not None:
            return found.GlobalId, []
    data = door_types.default_state(operation)
    data["name"] = name
    data["defaults"].update(width=opening["width"], height=opening["height"],
                            base=opening["sill"])
    type_id = guid.new()
    return type_id, [Op("door_type.create", type_id, data=data)]


def edit_door(doc: Document, door, hinges: str | None = None, **changes) -> Transaction:
    """Altera a porta. ``wall``, ``distance``, ``width``, ``height`` e ``base`` mudam a
    abertura (``opening.edit``); os demais, a porta (``door.edit``). ``hinges`` troca o
    tipo pela variante com aquela mão (porta §2.2).

    Porta de outra origem (porta §6.6): mover e mudar nome ou Psets preservam o corpo;
    as outras mudanças a convertem em porta paramétrica, com aviso.
    """
    door = doc.get(_gid(door), "IfcDoor")
    unknown = set(changes) - set(doors.STATE_KEYS) - set(_OPENING_KEYS)
    if unknown or "foreign" in changes:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown | ({'foreign'} & set(changes)))}")
    state = doors.read_state(door)
    opening = opening_of(door)
    convert = state["foreign"] is not None and (
        hinges is not None or any(k in changes for k in _CONVERTS))
    ops = []
    opening_changes = {_OPENING_KEYS[k]: changes.pop(k) for k in list(changes)
                       if k in _OPENING_KEYS}
    if opening_changes:
        if opening is None:
            raise OpError(f"porta {door.GlobalId} não está numa abertura")
        if (state["foreign"] is not None and not convert
                and door.ObjectPlacement.PlacementRelTo != opening.ObjectPlacement):
            raise OpError("a porta importada não está posicionada em relação à abertura e "
                          "não acompanharia o vão; mude o tamanho ou o tipo para convertê-la")
        ops += wall_cmd.edit_opening(doc, opening, **opening_changes).ops
    if changes.get("type") is not None:
        changes["type"] = doc.get(_gid(changes["type"]), "IfcDoorType").GlobalId
    type_states = {}  # tipos criados nesta transação
    if convert:
        if opening is None:
            raise OpError(f"porta {door.GlobalId} não está numa abertura")
        if changes.get("type") is None:
            after_opening = {**openings.read_state(opening), **opening_changes}
            changes["type"], type_ops = _converted_type(doc, door, state, after_opening)
            ops += type_ops
            type_states.update({op.id: op.data for op in type_ops})
        name = (type_states[changes["type"]]["name"] if changes["type"] in type_states
                else doc.get(changes["type"]).Name)
        defaults = doors.common_defaults(name)
        changes.setdefault("common", {k: v for k, v in state["common"].items()
                                      if defaults.get(k) != v})
        changes["foreign"] = None
        log.warning("porta %s de outra origem convertida em porta paramétrica: o corpo "
                    "original será substituído", door.GlobalId)
    if hinges is not None:
        type_id = changes.get("type") or state["type"]
        tstate = type_states.get(type_id) or door_types.read(doc.get(type_id, "IfcDoorType"))
        changes["type"], variant_ops = _hand_variant(doc, type_id, tstate, hinges)
        ops += variant_ops
    changes = {k: v for k, v in changes.items() if not same_value(state[k], v)}
    if changes:
        before = {k: state[k] for k in changes}
        ops.append(Op("door.edit", door.GlobalId, before=before, after=changes))
    label = "Converter e editar porta" if convert else "Editar porta"
    return Transaction(label, ops)


def flip_hinges(doc: Document, door) -> Transaction:
    """Inverte o lado das dobradiças (porta §5.1): troca o tipo pela variante."""
    door = doc.get(_gid(door), "IfcDoor")
    state = doors.read_state(door)
    if state["foreign"] is not None:
        operation = state["foreign"]["operation_type"] or (
            state["type"] and doc.get(state["type"]).OperationType) or ""
    else:
        operation = door_types.read(doc.get(state["type"], "IfcDoorType"))["operation_type"]
    hand = params.hand_of(operation)
    if hand is None:
        raise OpError("a porta não tem lado de dobradiças para inverter")
    tx = edit_door(doc, door, hinges="right" if hand == "left" else "left")
    tx.label = "Inverter dobradiças"
    return tx


def flip_opening(doc: Document, door) -> Transaction:
    """Inverte o sentido de abertura (porta §5.1): só o posicionamento muda."""
    door = doc.get(_gid(door), "IfcDoor")
    opens_to = doors.read_state(door)["opens_to"]
    tx = edit_door(doc, door, opens_to="right" if opens_to == "left" else "left")
    tx.label = "Inverter sentido de abertura"
    return tx


def delete_ops(door) -> list[Op]:
    """Desliga a porta da abertura e exclui a porta (sem a abertura)."""
    ops = [Op("filling.detach", door.GlobalId,
              data={"opening": rel.RelatingOpeningElement.GlobalId}) for rel in door.FillsVoids]
    ops.append(Op("door.delete", door.GlobalId, data=doors.read_state(door)))
    return ops


def delete_door(doc: Document, door, keep_opening: bool = False) -> Transaction:
    """Exclui a porta e a abertura dela (porta §6.4); ``keep_opening`` mantém o vão."""
    door = doc.get(_gid(door), "IfcDoor")
    if not doors.is_parametric(door):
        raise OpError("excluir porta de outra origem ainda não é suportado; "
                      "converta-a antes (mude o tamanho ou o tipo)")
    opening = opening_of(door)
    ops = delete_ops(door)
    label = "Remover porta e manter vão" if keep_opening else "Excluir porta"
    if opening is not None and not keep_opening:
        ops.append(Op("opening.delete", opening.GlobalId, data=openings.read_state(opening)))
    return Transaction(label, ops)
