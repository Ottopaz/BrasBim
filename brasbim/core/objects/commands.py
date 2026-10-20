# SPDX-License-Identifier: LGPL-3.0-or-later
"""Comandos dos objetos paramétricos: montam as transações (``objeto-parametrico.md`` §4 e
§5). Sem Qt; usados pela interface, pelo assistente e pelos testes."""

from __future__ import annotations

import copy

import ifcopenshell.util.element

from brasbim.core import display_layers, guid
from brasbim.core.document import Document, OpError
from brasbim.core.objects import definition as od
from brasbim.core.objects import elements
from brasbim.core.objects import formula as fm
from brasbim.core.objects import types as ot
from brasbim.core.ops import Op, Transaction

LAYER_BY_CATEGORY = {"furniture": "Mobiliário", "vegetation": "Vegetação",
                     "sanitary": "Equipamentos", "appliance": "Equipamentos",
                     "proxy": "Equipamentos"}
LAYER_GROUP = {"Mobiliário": "Interiores", "Equipamentos": "Interiores",
               "Vegetação": "Entorno"}


def kind(category: str) -> str:
    """Chave da camada padrão (spec/ui 18 §3.2) da categoria."""
    return f"object:{category}"


def _gid(x) -> str:
    return x if isinstance(x, str) else x.GlobalId


# --- tipos ------------------------------------------------------------------------------


def type_state(definition: dict, name: str, values: dict | None = None,
               defaults: dict | None = None, library: dict | None = None) -> dict:
    defn = od.normalized(definition)
    return {"name": name, "definition": defn,
            "values": ot.stored_values(defn, values or {}, "type"),
            "defaults": ot.stored_values(defn, defaults or {}, "occurrence"),
            "library": copy.deepcopy(library)}


def free_name(doc: Document, name: str, type_class: str, taken=()) -> str:
    """Nome livre na classe: repetido ganha " (2)", " (3)"… (§4.3)."""
    used = {(t.Name or "").casefold() for t in doc.ifc.by_type(type_class)}
    used |= {n.casefold() for n in taken}
    if name.casefold() not in used:
        return name
    n = 2
    while f"{name} ({n})".casefold() in used:
        n += 1
    return f"{name} ({n})"


def layer_ops(doc: Document, category: str) -> list[Op]:
    """Camada padrão da categoria (§2.5): a camada Equipamentos (e o padrão das categorias
    dela) é criada na primeira vez em que é usada."""
    config = display_layers.read_config(doc)
    if config is None or config["defaults"].get(kind(category)):
        return []
    name = LAYER_BY_CATEGORY[category]
    layer = next((x for x in config["layers"] if x["name"].casefold() == name.casefold()), None)
    ops = []
    if layer is None:
        group = next((g["id"] for g in config["groups"] if g["name"] == LAYER_GROUP[name]),
                     None)
        lid = guid.derived(doc.project.GlobalId, f"layer/{name}")
        ops.append(Op("layer.create", lid, data={"name": name, "group": group}))
    else:
        lid = layer["id"]
    kinds = [kind(c) for c, n in LAYER_BY_CATEGORY.items() if n == name
             and not config["defaults"].get(kind(c))]
    ops.append(Op("layer.defaults", doc.project.GlobalId,
                  before={k: None for k in kinds}, after={k: lid for k in kinds}))
    return ops


def create_type(doc: Document, definition: dict, name: str, values=None, defaults=None,
                library=None, gid: str | None = None) -> Transaction:
    state = type_state(definition, name, values, defaults, library)
    _, type_class = od.classes(state["definition"])
    state["name"] = free_name(doc, name, type_class)
    ops = layer_ops(doc, state["definition"]["category"])
    ops.append(Op("object_type.create", gid or guid.new(), data=state))
    return Transaction(f"Criar tipo {state['name']}", ops)


def _type(doc: Document, element_type):
    entity = doc.get(_gid(element_type), "IfcTypeObject")
    if not ot.is_object_type(entity):
        raise OpError(f"{entity.GlobalId} não é tipo de objeto paramétrico")
    return entity


def edit_type(doc: Document, element_type, **changes) -> Transaction:
    """``name``, ``values`` (só os que mudam; juntados aos atuais), ``defaults``,
    ``library``. A definição muda por ``edit_definition``."""
    element_type = _type(doc, element_type)
    state = ot.read(element_type)
    after = {}
    if "name" in changes and changes["name"] != state["name"]:
        after["name"] = changes["name"].strip()
    for key in ("values", "defaults"):
        if key in changes:
            merged = {**state[key], **changes[key]}
            level = "type" if key == "values" else "occurrence"
            merged = ot.stored_values(state["definition"], merged, level)
            if merged != state[key]:
                after[key] = merged
    if "library" in changes and changes["library"] != state["library"]:
        after["library"] = changes["library"]
    if not after:
        return Transaction("Editar tipo", [])
    before = {k: copy.deepcopy(state[k]) for k in after}
    return Transaction(f"Editar tipo {state['name']}",
                       [Op("object_type.edit", element_type.GlobalId, before=before,
                           after=after)])


def edit_definition(doc: Document, object_id: str, definition: dict,
                    keep_version: bool = False) -> Transaction:
    """Grava a definição em todos os tipos dela (versão + 1, §5.3) e acerta os valores
    guardados: o que tem o mesmo identificador e tipo do valor fica; o novo recebe o
    padrão (§4.3)."""
    found = ot.types_of_definition(doc, object_id)
    if not found:
        raise OpError("nenhum tipo do projeto usa esta definição")
    new = od.normalized(definition)
    new["object_id"] = object_id
    od.validate(new)
    old_version = ot.read(found[0])["definition"]["version"]
    if not keep_version:
        new["version"] = int(old_version) + 1
    ops = []
    for t in found:
        state = ot.read(t)
        after = {"definition": new,
                 "values": _kept(state["definition"], new, state["values"], "type"),
                 "defaults": _kept(state["definition"], new, state["defaults"], "occurrence")}
        ops.append(Op("object_type.edit", t.GlobalId,
                      before={k: copy.deepcopy(state[k]) for k in after}, after=after))
        for e in ifcopenshell.util.element.get_types(t):
            if not elements.is_object(e):
                continue
            occ = elements.read_state(doc, e)
            values = _kept(state["definition"], new, occ["values"], "occurrence")
            if values != occ["values"]:
                ops.append(Op("object.edit", e.GlobalId, before={"values": occ["values"]},
                              after={"values": values}))
    return Transaction(f"Editar objeto {new['name']}", ops)


def _kept(old: dict, new: dict, values: dict, level: str) -> dict:
    """Valores que continuam válidos na definição nova (mesmo identificador, mesmo tipo do
    valor e o mesmo nível)."""
    out = {}
    for name, value in values.items():
        p_old, p_new = od.param(old, name), od.param(new, name)
        if p_new is None or p_new["level"] != level or not od.editable(p_new):
            continue
        if p_old is not None and p_old["kind"] != p_new["kind"]:
            continue
        if p_new["kind"] == "choice" and value not in (p_new.get("options") or []):
            continue
        out[p_new["name"]] = value
    return out


def delete_type(doc: Document, element_type, replacement=None) -> Transaction:
    """Exclui o tipo; em uso, as ocorrências passam para ``replacement`` (§5.4)."""
    element_type = _type(doc, element_type)
    users = [e for e in ifcopenshell.util.element.get_types(element_type)
             if elements.is_object(e)]
    nested_users = [e for e in ifcopenshell.util.element.get_types(element_type)
                    if elements.is_part(e)]
    ops = []
    if users or nested_users:
        if replacement is None:
            raise OpError(f"o tipo {element_type.Name} está em uso: escolha o substituto")
        ops += change_type(doc, users, replacement).ops if users else []
        if nested_users:
            raise OpError(f"o tipo {element_type.Name} está dentro de outro objeto")
    ops.append(Op("object_type.delete", element_type.GlobalId, data=ot.read(element_type)))
    return Transaction(f"Excluir tipo {element_type.Name}", ops)


def delete_definition(doc: Document, object_id: str, replacement=None) -> Transaction:
    ops = []
    for t in ot.types_of_definition(doc, object_id):
        ops += delete_type(doc, t, replacement).ops
    return Transaction("Excluir objeto", ops)


def duplicate_type(doc: Document, element_type, name: str | None = None) -> Transaction:
    element_type = _type(doc, element_type)
    state = ot.read(element_type)
    state["name"] = free_name(doc, name or state["name"], element_type.is_a())
    state["library"] = None
    return Transaction(f"Duplicar tipo {element_type.Name}",
                       [Op("object_type.create", guid.new(), data=state)])


# --- ocorrências ---------------------------------------------------------------------------


def _element(doc: Document, element):
    entity = doc.get(_gid(element))
    if not elements.is_object(entity):
        raise OpError(f"{entity.GlobalId} não é objeto paramétrico")
    return entity


def create_object(doc: Document, element_type, storey, point, angle: float = 0.0,
                  mirror: bool = False, values: dict | None = None, host: dict | None = None,
                  gid: str | None = None) -> Transaction:
    element_type = _type(doc, element_type)
    tstate = ot.read(element_type)
    state = {**elements.default_state(), "type": element_type.GlobalId,
             "storey": _gid(storey), "point": [float(point[0]), float(point[1])],
             "angle": float(angle), "mirror": bool(mirror),
             "values": ot.stored_values(tstate["definition"],
                                        {**tstate["defaults"], **(values or {})},
                                        "occurrence"),
             "host": copy.deepcopy(host)}
    if host is not None:
        _check_host(doc, state)
    elif tstate["definition"]["hosting"] == "wall":
        raise OpError("este objeto se prende a uma parede: clique perto de uma parede")
    ops = layer_ops(doc, tstate["definition"]["category"])
    ops.append(Op("object.create", gid or guid.new(), data=state))
    return Transaction("Inserir objeto", ops)


def edit_object(doc: Document, element, **changes) -> Transaction:
    """Campos do estado (``values`` só com os que mudam, juntados aos atuais)."""
    element = _element(doc, element)
    state = elements.read_state(doc, element)
    after = {}
    for key, value in changes.items():
        if key not in elements.STATE_KEYS:
            raise OpError(f"campo desconhecido: {key}")
        if key == "values":
            tstate = ot.read(doc.get(changes.get("type", state["type"])))
            value = ot.stored_values(tstate["definition"], {**state["values"], **value},
                                     "occurrence")
        if value != state[key]:
            after[key] = copy.deepcopy(value)
    if not after:
        return Transaction("Editar objeto", [])
    new_state = {**state, **after}
    if new_state["host"] is not None and ({"host", "values", "type", "mirror"} & set(after)):
        _check_host(doc, new_state, exclude=hosting_opening(element))
    return Transaction("Editar objeto", [Op("object.edit", element.GlobalId,
                                            before={k: copy.deepcopy(state[k]) for k in after},
                                            after=after)])


def _check_host(doc: Document, state: dict, exclude: str | None = None) -> None:
    from brasbim.core.objects import hosting

    _, _, built = elements.resolve(doc, state)
    hosting.check(doc, state, built, exclude=exclude)


def hosting_opening(element) -> str:
    from brasbim.core.objects import hosting

    return hosting.opening_id(element)


def detach(doc: Document, element) -> Transaction:
    """Soltar da parede (§6.3): o objeto fica livre no mesmo lugar, sem o vão."""
    element = _element(doc, element)
    state = elements.read_state(doc, element)
    if state["host"] is None:
        return Transaction("Soltar da parede", [])
    tx = edit_object(doc, element, host=None, point=state["point"], angle=state["angle"])
    return Transaction("Soltar da parede", tx.ops)


def attach(doc: Document, element, wall, side: str, distance: float) -> Transaction:
    """Prender à parede (§6.3)."""
    element = _element(doc, element)
    tx = edit_object(doc, element, host={"wall": _gid(wall), "side": side,
                                         "distance": float(distance)})
    return Transaction("Prender à parede", tx.ops)


def edit_objects(doc: Document, gids, **changes) -> Transaction:
    ops = []
    for g in gids:
        ops += edit_object(doc, g, **copy.deepcopy(changes)).ops
    return Transaction("Editar objetos" if len(list(gids)) > 1 else "Editar objeto", ops)


def change_type(doc: Document, gids, new_type) -> Transaction:
    """Troca o tipo (§5.4): na mesma definição os valores ficam; em outra, passa o que
    tem o mesmo identificador e tipo do valor, e o resto recebe os padrões do tipo novo."""
    new_type = _type(doc, new_type)
    new_state = ot.read(new_type)
    ops = []
    for g in gids:
        element = _element(doc, g)
        state = elements.read_state(doc, element)
        if state["type"] == new_type.GlobalId:
            continue
        old_type = doc.get(state["type"])
        if not element.is_a(od.classes(new_state["definition"])[0]):
            raise OpError(f"{new_type.Name} é de outra classe ({new_type.is_a()})")
        old_defn = ot.read(old_type)["definition"]
        new_defn = new_state["definition"]
        if (old_defn["hosting"] == "wall") != (new_defn["hosting"] == "wall"):
            raise OpError("só se troca objeto preso à parede por outro preso à parede")
        if old_defn["object_id"] == new_defn["object_id"]:
            values = ot.stored_values(new_defn, state["values"], "occurrence")
        else:
            values = {**new_state["defaults"],
                      **_kept(old_defn, new_defn, state["values"], "occurrence")}
            values = ot.stored_values(new_defn, values, "occurrence")
        after = {"type": new_type.GlobalId}
        if values != state["values"]:
            after["values"] = values
        ops.append(Op("object.edit", element.GlobalId,
                      before={k: copy.deepcopy(state[k]) for k in after}, after=after))
    return Transaction(f"Trocar tipo para {new_type.Name}", ops)


def replace_all(doc: Document, old_type, new_type) -> Transaction:
    old_type = _type(doc, old_type)
    users = [e.GlobalId for e in ifcopenshell.util.element.get_types(old_type)
             if elements.is_object(e)]
    tx = change_type(doc, users, new_type)
    return Transaction(f"Substituir {old_type.Name}", tx.ops)


def delete_ops(doc: Document, element) -> list[Op]:
    element = _element(doc, element)
    return [Op("object.delete", element.GlobalId, data=elements.read_state(doc, element))]


def occurrences(doc: Document, element_type) -> list:
    return [e for e in ifcopenshell.util.element.get_types(_type(doc, element_type))
            if elements.is_object(e)]


def compatible_types(doc: Document, element) -> list:
    """Tipos para trocar (§5.1): da mesma classe IFC e com a mesma hospedagem."""
    element = _element(doc, element)
    current = ot.read(doc.get(elements.read_state(doc, element)["type"]))["definition"]
    occ_class = element.is_a()
    return [t for t in ot.all_types(doc)
            if od.classes(ot.definition_of(t))[0] == occ_class
            and ot.definition_of(t)["hosting"] == current["hosting"]]


def handle_value_ops(doc: Document, element, name: str, value: float) -> Transaction:
    """Alça (§5.1): muda o valor e desloca o ponto para o lado oposto ficar no lugar."""
    import math

    element = _element(doc, element)
    state = elements.read_state(doc, element)
    tstate = ot.read(doc.get(state["type"]))
    defn = tstate["definition"]
    occ = {**tstate["defaults"], **state["values"]}
    dx, dy, _ = od.handle_shift(defn, tstate["values"], occ, name, value)
    if state["mirror"]:
        dx = -dx
    a = math.radians(state["angle"])
    shift = (math.cos(a) * dx - math.sin(a) * dy, math.sin(a) * dx + math.cos(a) * dy)
    p = od.param(defn, name)
    changes = {"values": {p["name"]: float(value)}}
    if state["host"] is None and math.hypot(*shift) > 1e-9:
        changes["point"] = [state["point"][0] + shift[0], state["point"][1] + shift[1]]
    elif state["host"] is not None and abs(dx) > 1e-9:
        host = dict(state["host"])
        host["distance"] = float(host["distance"]) + (dx if host.get("side") != "right"
                                                      else -dx)
        changes["host"] = host
    return edit_object(doc, element, **changes)


def key(name: str) -> str:
    return fm.key(name)


def hosted_by(doc: Document, wall) -> list:
    from brasbim.core.objects import hosting

    return hosting.hosted_by(doc, wall)
