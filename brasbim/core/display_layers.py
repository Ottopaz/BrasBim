# SPDX-License-Identifier: LGPL-3.0-or-later
"""Camadas de organização (spec/ui 18): grupos, camada de cada elemento, combinações.

- **Definições** (camadas, grupos, combinações, camada padrão por ferramenta) ficam em
  JSON no Pset ``BrasBim_Camadas`` do ``IfcProject`` (``Parametros``), editadas por
  operações.
- **Camada de um elemento** = ``IfcPresentationLayerWithStyle`` com ``Identifier`` = código
  da camada e as representações do elemento em ``AssignedItems``. O IFC exige ao menos um
  item: a entidade nasce com o primeiro elemento e é apagada com o último (``sync``).
- ``Document.element_layers`` lembra a camada de cada elemento já visto, inclusive dos
  excluídos: desfazer a exclusão devolve o elemento à camada que ele tinha. Elemento novo
  vai para a camada padrão da ferramenta (``defaults``).
- **Exibição** (oculta, bloqueada) não é operação (§5.1): ``Display`` em
  ``Document.display``, gravada no arquivo só ao salvar (``write_display``, propriedade
  ``Exibicao`` e ``LayerOn``/``LayerBlocked``).
"""

from __future__ import annotations

import contextlib
import copy
import json
from dataclasses import dataclass, field

import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import (
    Op,
    check_before,
    invert_swap,
    register,
    register_derive,
    register_inverse_pair,
)

PSET = "BrasBim_Camadas"
NONE = "none"  # pseudo-camada "Sem camada" (§2): só no JSON
NONE_NAME = "Sem camada"
IMPORTED_GROUP = "Importadas"

# Ferramentas (tipos de elemento do BrasBim) que têm camada padrão (§3.2).
KINDS = ("wall", "door", "window", "slab", "roof", "space", "column", "beam", "dimension",
         "text", "line2d", "hatch", "level_mark", "north", "view", "circle2d", "arc2d",
         "spline2d", "radius_dim", "angle_dim", "label", "revision", "grid", "stair",
         "railing", "terrain", "reference2d",
         "object:furniture",
         "object:sanitary", "object:appliance", "object:vegetation", "object:proxy")

# Conjunto inicial (§3.1): grupo → [(camada, ferramentas que vão para ela)].
INITIAL = (
    ("Arquitetura", (("Paredes", ("wall",)), ("Esquadrias", ("door", "window")),
                     ("Pisos e lajes", ("slab", "stair", "railing")),
                     ("Cobertura", ("roof",)),
                     ("Ambientes", ("space",)))),
    ("Estrutura", (("Pilares", ("column",)), ("Vigas", ("beam",)),
                   ("Lajes estruturais", ()))),
    ("Documentação", (("Cotas", ("dimension", "radius_dim", "angle_dim")),
                      ("Textos e rótulos", ("text", "label")),
                      ("Linhas e hachuras", ("line2d", "hatch", "circle2d", "arc2d",
                                             "spline2d")),
                      ("Símbolos", ("level_mark", "north", "view", "revision",
                                    "grid")))),
    ("Entorno", (("Terreno", ("terrain",)), ("Vegetação", ("object:vegetation",)),
                 ("Levantamento", ("reference2d",)))),
    # Equipamentos (louças, eletrodomésticos) nasce no primeiro uso (objeto-parametrico §2.5).
    ("Interiores", (("Mobiliário", ("object:furniture",)),)),
)
# Combinações iniciais (§6.1): nome → (grupos ocultos, camadas ocultas, camadas visíveis
# apesar do grupo).
INITIAL_COMBINATIONS = (
    ("Tudo", (), (), ()),
    ("Arquitetura", ("Estrutura", "Documentação"), (), ()),
    ("Estrutura", ("Arquitetura", "Documentação", "Entorno", "Interiores"), (), ("Cotas",)),
    ("Apresentação", ("Documentação",), ("Ambientes",), ()),
)


# --- definições -----------------------------------------------------------------------------


def empty_config() -> dict:
    return {"groups": [], "layers": [], "combinations": [], "defaults": {}}


def read_config(doc: Document) -> dict | None:
    """Definições do projeto, ou None se o projeto ainda não foi organizado em camadas."""
    values = ifcopenshell.util.element.get_pset(doc.project, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        return None
    return {**empty_config(), **json.loads(values["Parametros"])}


def _write_config(doc: Document, config: dict) -> None:
    props.write_pset(doc, doc.project, PSET, {
        "Parametros": doc.ifc.createIfcText(json.dumps(config, ensure_ascii=False,
                                                       sort_keys=True)),
        **_display_value(doc)})


def _display_value(doc: Document) -> dict:
    values = ifcopenshell.util.element.get_pset(doc.project, PSET, should_inherit=False) or {}
    return {"Exibicao": doc.ifc.createIfcText(values["Exibicao"])} if "Exibicao" in values else {}


def _config(doc: Document) -> dict:
    config = read_config(doc)
    if config is None:
        raise OpError("o projeto não está organizado em camadas")
    return config


def _by_id(items: list[dict], item_id: str) -> dict | None:
    return next((x for x in items if x["id"] == item_id), None)


def layer(doc: Document, layer_id: str) -> dict | None:
    config = read_config(doc)
    return _by_id(config["layers"], layer_id) if config else None


def layer_name(doc: Document, layer_id: str | None) -> str:
    if layer_id in (None, NONE):
        return NONE_NAME
    found = layer(doc, layer_id)
    return found["name"] if found else NONE_NAME


def initial_config(project_id: str) -> dict:
    config = empty_config()
    names: dict[str, str] = {}
    for group_name, layers in INITIAL:
        gid = guid.derived(project_id, f"layer_group/{group_name}")
        config["groups"].append({"id": gid, "name": group_name})
        for name, kinds in layers:
            lid = guid.derived(project_id, f"layer/{name}")
            names[name] = lid
            config["layers"].append({"id": lid, "name": name, "group": gid})
            for kind in kinds:
                config["defaults"][kind] = lid
    by_group = {g["name"]: g["id"] for g in config["groups"]}
    for name, hidden_groups, hidden_layers, shown in INITIAL_COMBINATIONS:
        hidden = {by_group[g] for g in hidden_groups}
        states = {}
        for lay in config["layers"]:
            visible = ((lay["group"] not in hidden or lay["name"] in shown)
                       and lay["name"] not in hidden_layers)
            states[lay["id"]] = [visible, False]
        config["combinations"].append({"id": guid.derived(project_id, f"layer_combination/{name}"),
                                       "name": name, "states": states})
    return config


def setup(doc: Document) -> None:
    """Conjunto inicial num projeto novo (``Document.new``), sem operação."""
    _write_config(doc, initial_config(doc.project.GlobalId))


# --- elemento → camada -----------------------------------------------------------------------


def _roofs():
    from brasbim.core.structure import roofs

    return roofs


# Ferramenta parecida, para arquivo antigo sem a camada padrão das novas (spec/ui 19 §6).
FALLBACK = {"circle2d": "line2d", "arc2d": "line2d", "spline2d": "line2d",
            "radius_dim": "dimension", "angle_dim": "dimension", "label": "text",
            "revision": "north", "grid": "north", "stair": "slab", "railing": "slab",
            "reference2d": "line2d"}


def default_layer(config: dict, kind: str | None) -> str | None:
    """Camada padrão da ferramenta (ou da parecida, em arquivo antigo)."""
    found = config["defaults"].get(kind)
    if found is None and kind in FALLBACK:
        found = config["defaults"].get(FALLBACK[kind])
    return found


def kind_of(element) -> str | None:
    """Ferramenta do BrasBim que cria o elemento (chave de ``defaults``)."""
    if element is None:
        return None
    if element.is_a("IfcAnnotation"):
        from brasbim.core.annotations import base
        from brasbim.core.drawings import views

        if views.is_view(element):
            return "view"
        kind = base.kind_of(element)
        return kind.prefix if kind else None
    from brasbim.core.objects import elements as objects

    if objects.is_object(element) or objects.is_part(element):
        return objects.kind_of(element)
    if element.is_a("IfcGrid"):
        return "grid"
    from brasbim.core import terrain
    from brasbim.core.structure import railings, stairs

    if stairs.is_stair(element):
        return "stair"
    if railings.is_railing(element):
        return "railing"
    if terrain.is_terrain(element):
        return "terrain"
    for cls, kind in (("IfcWall", "wall"), ("IfcDoor", "door"), ("IfcWindow", "window"),
                      ("IfcColumn", "column"), ("IfcBeam", "beam"), ("IfcRoof", "roof"),
                      ("IfcSpace", "space"), ("IfcSlab", "slab")):
        if element.is_a(cls):
            return kind
    return None


def layerable(element) -> bool:
    """Elementos que ficam numa camada: produtos com desenho, menos vãos, águas da
    cobertura (seguem a cobertura), estrutura espacial, pranchas e tabelas."""
    if element is None or not element.is_a("IfcProduct"):
        return False
    if element.is_a("IfcFeatureElement") or (
            element.is_a("IfcSpatialStructureElement") and not element.is_a("IfcSpace")):
        return False
    if element.is_a("IfcAnnotation"):
        from brasbim.core.drawings import saved_views, sheets
        from brasbim.core.quantities import tables

        return not (sheets.is_sheet(element) or tables.is_table(element)
                    or saved_views.is_saved_view(element))
    if element.is_a("IfcRoof"):
        return True
    return not _roofs().is_part(element)


def owner(element):
    """Quem responde pela camada: a água da cobertura responde pela cobertura, e o objeto
    aninhado, pelo objeto de fora."""
    from brasbim.core.objects import elements as objects

    if objects.is_part(element):
        return objects.parent_of(element)
    from brasbim.core.structure import stairs

    stair = stairs.stair_of(element) if element is not None else None
    if stair is not None:
        return stair
    if element is not None and element.is_a("IfcSlab"):
        roof = _roofs().roof_of(element)
        if roof is not None:
            return roof
    return element


def _representations(element) -> list:
    if element.is_a("IfcRoof"):
        return [r for p in _roofs().parts_of(element) if p.Representation
                for r in p.Representation.Representations]
    if element.Representation is None:
        return []
    return list(element.Representation.Representations)


def _rep_layer(rep) -> str | None:
    for assignment in getattr(rep, "LayerAssignments", None) or ():
        if assignment.Identifier:
            return assignment.Identifier
    return None


def _ifc_layer_of(element) -> str | None:
    reps = _representations(element)
    reps.sort(key=lambda r: r.RepresentationIdentifier != "Body")
    for rep in reps:
        found = _rep_layer(rep)
        if found:
            return found
    return None


def _map(doc: Document, skip: set[str] = frozenset()) -> dict[str, str | None]:
    """``Document.element_layers``, montado do IFC na primeira vez. Elemento existente sem
    camada fica em ``None`` (Sem camada); ``skip`` são os que a transação em curso criou."""
    if doc.element_layers is None:
        found: dict[str, str | None] = {}
        for element in doc.ifc.by_type("IfcProduct"):
            if element.GlobalId not in skip and layerable(element):
                found[element.GlobalId] = _ifc_layer_of(element)
        doc.element_layers = found
    return doc.element_layers


def layer_of(doc: Document, element) -> str | None:
    """Camada do elemento (``None`` = Sem camada)."""
    element = owner(element)
    if element is None:
        return None
    return _map(doc).get(element.GlobalId, _ifc_layer_of(element))


def _entity(doc: Document, layer_id: str):
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        if assignment.Identifier == layer_id:
            return assignment
    return None


def _assign(doc: Document, element, layer_id: str | None, config: dict) -> None:
    """Põe todas as representações do elemento na camada (só nas do BrasBim)."""
    known = {x["id"] for x in config["layers"]}
    for rep in _representations(element):
        for assignment in list(rep.LayerAssignments or ()):
            if assignment.Identifier in known and assignment.Identifier != layer_id:
                assignment.AssignedItems = [i for i in assignment.AssignedItems if i != rep]
        if layer_id in (None, NONE) or layer_id not in known:
            continue
        target = _entity(doc, layer_id)
        if target is None:
            lay = _by_id(config["layers"], layer_id)
            doc.ifc.createIfcPresentationLayerWithStyle(
                lay["name"], None, [rep], layer_id, True, False, False, [])
        elif rep not in target.AssignedItems:
            target.AssignedItems = [*target.AssignedItems, rep]


def _cleanup(doc: Document, config: dict) -> None:
    """Representação que saiu do produto (corpo refeito, elemento excluído) não é apagada
    pelo ``remove_deep2`` enquanto a camada a cita: sai da camada e é apagada aqui. Camada
    sem itens perde a entidade."""
    known = {x["id"] for x in config["layers"]}
    keep = set(doc.ifc.by_type("IfcGeometricRepresentationContext"))
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        if assignment.Identifier not in known:
            continue
        items = list(assignment.AssignedItems)
        orphans = [r for r in items if r.is_a("IfcRepresentation")
                   and not r.OfProductRepresentation and not r.RepresentationMap]
        if orphans:
            assignment.AssignedItems = [r for r in items if r not in orphans]
            for rep in orphans:
                ifcopenshell.util.element.remove_deep2(doc.ifc, rep, do_not_delete=keep)
        if not assignment.AssignedItems:
            doc.ifc.remove(assignment)


def sync(doc: Document, dirty: set[str]) -> None:
    """Derivação (último passo de toda transação): elemento novo vai para a camada padrão,
    corpo refeito herda a camada, camada sem elementos perde a entidade IFC."""
    config = read_config(doc)
    if config is None:
        return
    gids = set(dirty) | doc.changed
    mapping = _map(doc, skip=gids)
    seen = set()
    for gid in sorted(gids):
        element = owner(doc.find(gid))
        if element is None or element.GlobalId in seen or not layerable(element):
            continue
        seen.add(element.GlobalId)
        key = element.GlobalId
        if key not in mapping:
            mapping[key] = _ifc_layer_of(element) or default_layer(config, kind_of(element))
        _assign(doc, element, mapping[key], config)
    _cleanup(doc, config)


register_derive(sync, last=True)


# --- operações --------------------------------------------------------------------------------


def _layer_create(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    if _by_id(config["layers"], op.id) or op.id == NONE:
        raise OpError(f"camada {op.id} já existe")
    data = op.data
    _check_name(config["layers"], data["name"], op.id)
    if data.get("group") and not _by_id(config["groups"], data["group"]):
        raise OpError("grupo de camadas não existe")
    index = data.get("index", len(config["layers"]))
    config["layers"].insert(index, {"id": op.id, "name": data["name"],
                                    "group": data.get("group")})
    _write_config(doc, config)
    # Camada que já estava no arquivo com o mesmo nome e sem código (outra origem): adotada.
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        if assignment.Identifier is None and assignment.Name == data["name"]:
            assignment.Identifier = op.id
            doc.element_layers = None
            break
    return {doc.project.GlobalId}


def _layer_delete(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["layers"], op.id)
    if found is None:
        raise OpError(f"camada {op.id} não existe")
    if members(doc, op.id):
        raise OpError(f"a camada {found['name']} ainda tem elementos")
    config["layers"].remove(found)
    config["defaults"] = {k: v for k, v in config["defaults"].items() if v != op.id}
    for combination in config["combinations"]:
        combination["states"].pop(op.id, None)
    _write_config(doc, config)
    entity = _entity(doc, op.id)
    if entity is not None:
        entity.Identifier = None  # adotada de outra origem e vazia de elementos do BrasBim
    return {doc.project.GlobalId}


def _check_name(items: list[dict], name: str, item_id: str) -> None:
    if not (name or "").strip():
        raise OpError("o nome não pode ficar vazio")
    for x in items:
        if x["id"] != item_id and x["name"].casefold() == name.strip().casefold():
            raise OpError(f"já existe {name!r}")


def _layer_edit(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["layers"], op.id)
    if found is None:
        raise OpError(f"camada {op.id} não existe")
    check_before(op, found)
    after = op.after or {}
    if "name" in after:
        _check_name(config["layers"], after["name"], op.id)
    if after.get("group") and not _by_id(config["groups"], after["group"]):
        raise OpError("grupo de camadas não existe")
    found.update(copy.deepcopy(after))
    _write_config(doc, config)
    entity = _entity(doc, op.id)
    if entity is not None and "name" in after:
        entity.Name = after["name"]
    return {doc.project.GlobalId}


def _group_create(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    if _by_id(config["groups"], op.id):
        raise OpError(f"grupo {op.id} já existe")
    _check_name(config["groups"], op.data["name"], op.id)
    index = op.data.get("index", len(config["groups"]))
    config["groups"].insert(index, {"id": op.id, "name": op.data["name"]})
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _group_delete(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["groups"], op.id)
    if found is None:
        raise OpError(f"grupo {op.id} não existe")
    if any(x["group"] == op.id for x in config["layers"]):
        raise OpError(f"o grupo {found['name']} ainda tem camadas")
    config["groups"].remove(found)
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _group_edit(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["groups"], op.id)
    if found is None:
        raise OpError(f"grupo {op.id} não existe")
    check_before(op, found)
    if "name" in (op.after or {}):
        _check_name(config["groups"], op.after["name"], op.id)
    found.update(copy.deepcopy(op.after or {}))
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _order(doc: Document, op: Op) -> set[str]:
    """``before``/``after``: ``layers`` e/ou ``groups``, listas de códigos na ordem nova."""
    config = _config(doc)
    current = {"layers": [x["id"] for x in config["layers"]],
               "groups": [x["id"] for x in config["groups"]]}
    check_before(op, current)
    for key, ids in (op.after or {}).items():
        items = {x["id"]: x for x in config[key]}
        if sorted(ids) != sorted(items):
            raise OpError("a ordem nova não tem as mesmas camadas")
        config[key] = [items[i] for i in ids]
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _assign_op(doc: Document, op: Op) -> set[str]:
    """``layer.assign``: ``before``/``after`` = {"layer": código ou None}."""
    config = _config(doc)
    element = doc.get(op.id)
    if not layerable(element):
        raise OpError(f"{op.id} não fica em camada")
    target = (op.after or {}).get("layer")
    if target not in (None, NONE) and not _by_id(config["layers"], target):
        raise OpError("camada não existe")
    mapping = _map(doc)
    check_before(op, {"layer": mapping.get(op.id, _ifc_layer_of(element))})
    mapping[op.id] = None if target == NONE else target
    _assign(doc, element, mapping[op.id], config)
    return {op.id}


def _combination_create(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    if _by_id(config["combinations"], op.id):
        raise OpError(f"combinação {op.id} já existe")
    _check_name(config["combinations"], op.data["name"], op.id)
    index = op.data.get("index", len(config["combinations"]))
    config["combinations"].insert(index, {"id": op.id, "name": op.data["name"],
                                          "states": copy.deepcopy(op.data.get("states", {}))})
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _combination_delete(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["combinations"], op.id)
    if found is None:
        raise OpError(f"combinação {op.id} não existe")
    config["combinations"].remove(found)
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _combination_edit(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    found = _by_id(config["combinations"], op.id)
    if found is None:
        raise OpError(f"combinação {op.id} não existe")
    check_before(op, found)
    if "name" in (op.after or {}):
        _check_name(config["combinations"], op.after["name"], op.id)
    found.update(copy.deepcopy(op.after or {}))
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _defaults(doc: Document, op: Op) -> set[str]:
    """``layer.defaults``: ``before``/``after`` = {ferramenta: código ou None}."""
    config = _config(doc)
    check_before(op, config["defaults"])
    for kind, value in (op.after or {}).items():
        if value is None:
            config["defaults"].pop(kind, None)
        elif not _by_id(config["layers"], value):
            raise OpError("camada não existe")
        else:
            config["defaults"][kind] = value
    _write_config(doc, config)
    return {doc.project.GlobalId}


def _setup(doc: Document, op: Op) -> set[str]:
    """``layers.setup``: organiza um projeto que ainda não tinha camadas (§3.1, arquivo
    antigo ou de outra origem). ``data`` = definições completas."""
    if read_config(doc) is not None:
        raise OpError("o projeto já está organizado em camadas")
    config = copy.deepcopy(op.data)
    _write_config(doc, config)
    names = {x["name"]: x["id"] for x in config["layers"] if x.get("imported")}
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        if assignment.Identifier is None and assignment.Name in names:
            assignment.Identifier = names[assignment.Name]
    doc.element_layers = None
    return {doc.project.GlobalId}


def _teardown(doc: Document, op: Op) -> set[str]:
    config = _config(doc)
    imported = {x["id"] for x in config["layers"] if x.get("imported")}
    known = {x["id"] for x in config["layers"]}
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        if assignment.Identifier in imported:
            assignment.Identifier = None
        elif assignment.Identifier in known:
            doc.ifc.remove(assignment)
    props.remove_pset(doc, doc.project, PSET)
    doc.element_layers = None
    return {doc.project.GlobalId}


register_inverse_pair("layer.create", _layer_create, "layer.delete", _layer_delete)
register("layer.edit", _layer_edit, invert_swap)
register_inverse_pair("layer_group.create", _group_create, "layer_group.delete", _group_delete)
register("layer_group.edit", _group_edit, invert_swap)
register("layer.order", _order, invert_swap)
register("layer.assign", _assign_op, invert_swap)
register_inverse_pair("layer_combination.create", _combination_create,
                      "layer_combination.delete", _combination_delete)
register("layer_combination.edit", _combination_edit, invert_swap)
register("layer.defaults", _defaults, invert_swap)
register_inverse_pair("layers.setup", _setup, "layers.teardown", _teardown)


# --- exibição (fora do desfazer, §5.1) ----------------------------------------------------------


@dataclass(frozen=True)
class Display:
    """Estado de exibição: códigos das camadas ocultas e das bloqueadas."""

    hidden: frozenset = field(default_factory=frozenset)
    locked: frozenset = field(default_factory=frozenset)

    def state(self, layer_id: str) -> tuple[bool, bool]:
        """(visível, bloqueada)."""
        return layer_id not in self.hidden, layer_id in self.locked

    def with_layer(self, layer_id: str, visible: bool | None = None,
                   locked: bool | None = None) -> Display:
        hidden, lock = set(self.hidden), set(self.locked)
        if visible is not None:
            (hidden.discard if visible else hidden.add)(layer_id)
        if locked is not None:
            (lock.add if locked else lock.discard)(layer_id)
        return Display(frozenset(hidden), frozenset(lock))


def display_of(states: dict) -> Display:
    """Display de uma combinação (``states`` = {camada: [visível, bloqueada]}); camada que
    não está na combinação fica visível e livre (§6.1)."""
    return Display(frozenset(k for k, (v, _) in states.items() if not v),
                   frozenset(k for k, (_, b) in states.items() if b))


def states_of(doc: Document, display: Display) -> dict:
    config = read_config(doc) or empty_config()
    return {x: list(display.state(x)) for x in [*(y["id"] for y in config["layers"]), NONE]}


def combination(doc: Document, combination_id: str) -> dict | None:
    config = read_config(doc)
    return _by_id(config["combinations"], combination_id) if config else None


def matching_combination(doc: Document, display: Display) -> dict | None:
    """Combinação cujo estado é o atual, ou None ("(alterada)")."""
    config = read_config(doc) or empty_config()
    for comb in config["combinations"]:
        if display_of(comb["states"]) == display:
            return comb
    return None


def _known(doc: Document) -> set[str]:
    config = read_config(doc)
    return {x["id"] for x in config["layers"]} if config else set()


def _effective(doc: Document, layer_id: str | None, known: set[str] | None = None) -> str:
    """Camada que vale para a exibição: código inexistente conta como Sem camada."""
    known = _known(doc) if known is None else known
    return layer_id if layer_id in known else NONE


def is_hidden(doc: Document, element) -> bool:
    """Oculto pela camada ou pelo filtro de situação da vista (spec/ui 31 §3)."""
    from brasbim.core import intervention

    if intervention.SHOWN.get(doc.situation_view) is not None and             owner(element) is not None and layerable(owner(element)) and             intervention.situation_of(doc, element) not in             intervention.SHOWN[doc.situation_view]:
        return True
    if not doc.display.hidden or read_config(doc) is None:
        return False
    return _effective(doc, layer_of(doc, element)) in doc.display.hidden


def is_locked(doc: Document, element) -> bool:
    if not doc.display.locked or read_config(doc) is None:
        return False
    return _effective(doc, layer_of(doc, element)) in doc.display.locked


def hidden_ids(doc: Document) -> set[str]:
    """GlobalIds dos elementos ocultos (as águas da cobertura junto com a cobertura): pela
    camada ou pelo filtro de situação da vista (spec/ui 31 §3)."""
    from brasbim.core import intervention

    extra = getattr(doc, "extra_hidden", None) or set()  # ocultos da janela (ui/39 §4)
    return _ids(doc, doc.display.hidden) | intervention.hidden_ids(doc) | extra


def filtering(doc: Document) -> bool:
    """Há algo oculto ou bloqueado (camadas ou filtro de situação)."""
    from brasbim.core import intervention

    return bool(doc.display.hidden or doc.display.locked
                or intervention.SHOWN.get(doc.situation_view) is not None)


def locked_ids(doc: Document) -> set[str]:
    return _ids(doc, doc.display.locked)


def _ids(doc: Document, layer_ids: frozenset) -> set[str]:
    if not layer_ids or read_config(doc) is None:
        return set()
    known = _known(doc)
    out = set()
    for gid, lay in _map(doc).items():
        if _effective(doc, lay, known) not in layer_ids:
            continue
        element = doc.find(gid)
        if element is not None:
            out.add(gid)
            if element.is_a("IfcRoof"):
                out |= {p.GlobalId for p in _roofs().parts_of(element)}
    return out


def members(doc: Document, layer_id: str) -> list[str]:
    """GlobalIds dos elementos (existentes) da camada."""
    known = _known(doc)
    return sorted(g for g, lay in _map(doc).items()
                  if _effective(doc, lay, known) == layer_id and doc.find(g) is not None)


@contextlib.contextmanager
def using(doc: Document, display: Display):
    """Desenha com outra exibição (vista de prancha com combinação, §6.2)."""
    previous = doc.display
    doc.display = display
    try:
        yield
    finally:
        doc.display = previous


def read_display(doc: Document) -> Display:
    """Exibição gravada no arquivo (``Exibicao``); sem ela, tudo visível e livre."""
    values = ifcopenshell.util.element.get_pset(doc.project, PSET, should_inherit=False) or {}
    if "Exibicao" not in values:
        return Display()
    return display_of(json.loads(values["Exibicao"]))


def write_display(doc: Document, display: Display) -> None:
    """Ao salvar (§5.1): ``Exibicao`` e ``LayerOn``/``LayerBlocked``, sem transação."""
    config = read_config(doc)
    if config is None:
        return
    props.write_pset(doc, doc.project, PSET, {
        "Parametros": doc.ifc.createIfcText(json.dumps(config, ensure_ascii=False,
                                                       sort_keys=True)),
        "Exibicao": doc.ifc.createIfcText(json.dumps(states_of(doc, display),
                                                     sort_keys=True))})
    for x in config["layers"]:
        entity = _entity(doc, x["id"])
        if entity is not None and entity.is_a("IfcPresentationLayerWithStyle"):
            visible, locked = display.state(x["id"])
            entity.LayerOn, entity.LayerBlocked = visible, locked


# --- comandos ---------------------------------------------------------------------------------


def organize_config(doc: Document) -> dict:
    """Definições para um projeto sem camadas: o conjunto inicial mais as camadas que já
    estavam no arquivo, no grupo "Importadas" (§2)."""
    pid = doc.project.GlobalId
    config = initial_config(pid)
    taken = {x["name"].casefold() for x in config["layers"]}
    imported = []
    for assignment in doc.ifc.by_type("IfcPresentationLayerAssignment"):
        name = assignment.Name or "Camada"
        if assignment.Identifier is not None or name.casefold() in taken:
            continue
        taken.add(name.casefold())
        imported.append({"id": guid.derived(pid, f"layer/import/{name}"), "name": name,
                         "imported": True})
    if imported:
        gid = guid.derived(pid, f"layer_group/{IMPORTED_GROUP}")
        config["groups"].append({"id": gid, "name": IMPORTED_GROUP})
        config["layers"] += [{**x, "group": gid} for x in imported]
    return config


def organize(doc: Document):
    """Transação "Organizar em camadas" para arquivo sem ``BrasBim_Camadas`` (§3.1, CM12):
    os elementos do BrasBim sem camada vão para a camada da sua ferramenta; os de outra
    origem ficam onde estavam (ou em Sem camada). None se já está organizado."""
    from brasbim.core.ops import Transaction

    if read_config(doc) is not None:
        return None
    config = organize_config(doc)
    ops = [Op("layers.setup", doc.project.GlobalId, data=config)]
    for element in sorted(doc.ifc.by_type("IfcProduct"), key=lambda e: e.GlobalId):
        if not layerable(element) or _ifc_layer_of(element) is not None \
                or element.Representation is None and not element.is_a("IfcRoof"):
            continue
        if _is_brasbim(element):
            target = config["defaults"].get(kind_of(element))
            if target:
                ops.append(Op("layer.assign", element.GlobalId, before={"layer": None},
                              after={"layer": target}))
    return Transaction("Organizar em camadas", ops)


def _is_brasbim(element) -> bool:
    """Elemento feito pelo BrasBim (tem algum Pset ``BrasBim_*``)."""
    return any(name.startswith("BrasBim_")
               for name in ifcopenshell.util.element.get_psets(element, should_inherit=False))


def new_id() -> str:
    return guid.new()


def create_layer(doc: Document, name: str, group: str | None = None):
    from brasbim.core.ops import Transaction

    return Transaction("Criar camada", [Op("layer.create", new_id(),
                                           data={"name": name.strip(), "group": group})])


def create_group(doc: Document, name: str):
    from brasbim.core.ops import Transaction

    return Transaction("Criar grupo de camadas",
                       [Op("layer_group.create", new_id(), data={"name": name.strip()})])


def _layer_data(config: dict, lay: dict) -> dict:
    return {"name": lay["name"], "group": lay.get("group"),
            "index": config["layers"].index(lay),
            **({"imported": True} if lay.get("imported") else {})}


def delete_layer(doc: Document, layer_id: str, move_to: str | None = None):
    """Excluir camada: os elementos vão para ``move_to`` (§5, CM08), na mesma transação;
    as ferramentas que a usavam como padrão perdem o padrão."""
    from brasbim.core.ops import Transaction

    config = _config(doc)
    lay = _by_id(config["layers"], layer_id)
    if lay is None:
        raise OpError("camada não existe")
    if move_to == layer_id:
        raise OpError("escolha outra camada para os elementos")
    ops = [Op("layer.assign", gid, before={"layer": layer_id}, after={"layer": move_to})
           for gid in members(doc, layer_id)]
    defaults = {k: v for k, v in config["defaults"].items() if v == layer_id}
    if defaults:
        ops.append(Op("layer.defaults", doc.project.GlobalId, before=defaults,
                      after={k: move_to if move_to not in (None, NONE) else None
                             for k in defaults}))
    for comb in config["combinations"]:
        if layer_id in comb["states"]:
            states = {k: v for k, v in comb["states"].items() if k != layer_id}
            ops.append(Op("layer_combination.edit", comb["id"],
                          before={"states": copy.deepcopy(comb["states"])},
                          after={"states": states}))
    ops.append(Op("layer.delete", layer_id, data=_layer_data(config, lay)))
    return Transaction("Excluir camada", ops)


def delete_group(doc: Document, group_id: str):
    """Excluir grupo: as camadas ficam sem grupo (§5)."""
    from brasbim.core.ops import Transaction

    config = _config(doc)
    group = _by_id(config["groups"], group_id)
    if group is None:
        raise OpError("grupo não existe")
    ops = [Op("layer.edit", x["id"], before={"group": group_id}, after={"group": None})
           for x in config["layers"] if x.get("group") == group_id]
    ops.append(Op("layer_group.delete", group_id,
                  data={"name": group["name"], "index": config["groups"].index(group)}))
    return Transaction("Excluir grupo de camadas", ops)


def edit_layer(doc: Document, layer_id: str, **changes):
    from brasbim.core.ops import Transaction

    lay = _by_id(_config(doc)["layers"], layer_id)
    if lay is None:
        raise OpError("camada não existe")
    if "name" in changes:
        changes["name"] = changes["name"].strip()
    before = {k: lay.get(k) for k in changes}
    return Transaction("Editar camada", [Op("layer.edit", layer_id, before=before,
                                            after=dict(changes))])


def rename_group(doc: Document, group_id: str, name: str):
    from brasbim.core.ops import Transaction

    group = _by_id(_config(doc)["groups"], group_id)
    if group is None:
        raise OpError("grupo não existe")
    return Transaction("Renomear grupo de camadas", [Op(
        "layer_group.edit", group_id, before={"name": group["name"]},
        after={"name": name.strip()})])


def reorder(doc: Document, layers: list[str] | None = None, groups: list[str] | None = None):
    from brasbim.core.ops import Transaction

    config = _config(doc)
    before, after = {}, {}
    if layers is not None:
        before["layers"], after["layers"] = [x["id"] for x in config["layers"]], list(layers)
    if groups is not None:
        before["groups"], after["groups"] = [x["id"] for x in config["groups"]], list(groups)
    return Transaction("Reordenar camadas", [Op("layer.order", doc.project.GlobalId,
                                                before=before, after=after)])


def assign(doc: Document, gids, layer_id: str | None):
    """Muda a camada de elementos (§5): uma transação só."""
    from brasbim.core.ops import Transaction

    if layer_id == NONE:
        layer_id = None
    ops = []
    for gid in gids:
        element = owner(doc.get(gid))
        current = layer_of(doc, element)
        if current != layer_id and element.GlobalId not in {o.id for o in ops}:
            ops.append(Op("layer.assign", element.GlobalId, before={"layer": current},
                          after={"layer": layer_id}))
    return Transaction("Mudar camada", ops)


def created(tx, doc: Document | None = None) -> list[tuple[str, str, str | None]]:
    """(ferramenta, GlobalId criado, GlobalId de origem conhecido) na ordem da transação."""
    out = []
    for op in tx.ops:
        prefix, _, action = op.op.rpartition(".")
        if op.op == "object.create" and doc is not None:
            from brasbim.core.objects import elements as objects

            found = objects.kind_of_type(doc.find(op.data.get("type") or ""))
            if found:
                out.append((found, op.id, None))
        elif action == "create" and prefix in KINDS:
            out.append((prefix, op.id, None))
        elif op.op == "wall.split":  # o trecho novo é da mesma camada (§5)
            out.append(("wall", op.data["new"], op.id))
    return out


def copies(doc: Document, tx, sources, value) -> list[tuple[str, str, object]]:
    """(ferramenta, GlobalId novo, valor do original) para cada elemento que ``tx`` cria a
    partir de ``sources`` (cópia, espelho com cópia, dividir); ``value(elemento)`` lê o
    valor. Origem e cópia são ligadas pela ferramenta e pela ordem; se a conta não fecha,
    vale o valor comum das origens (sem ele, o elemento fica de fora)."""
    by_kind: dict[str, list] = {}
    for gid in sources:
        element = owner(doc.find(gid if isinstance(gid, str) else gid.GlobalId))
        if element is None:
            continue
        by_kind.setdefault(kind_of(element), []).append(value(element))
        if element.is_a("IfcWall"):  # as esquadrias vêm junto com a parede copiada
            for opening in element.HasOpenings or ():
                for rel in opening.RelatedOpeningElement.HasFillings or ():
                    filling = rel.RelatedBuildingElement
                    by_kind.setdefault(kind_of(filling), []).append(value(filling))
    made = created(tx, doc)
    counts: dict[str, int] = {}
    for kind, _, _ in made:
        counts[kind] = counts.get(kind, 0) + 1
    out, seen = [], {}
    for kind, gid, origin in made:
        if origin is not None:
            out.append((kind, gid, value(doc.find(origin))))
            continue
        values = by_kind.get(kind, [])
        i = seen[kind] = seen.get(kind, -1) + 1
        if len(values) == counts[kind]:
            out.append((kind, gid, values[i]))
        elif values and all(v == values[0] for v in values):
            out.append((kind, gid, values[0]))
    return out


def inherit(doc: Document, tx, sources):
    """Acrescenta a ``tx`` (cópia, espelho com cópia, dividir) os ``layer.assign`` que põem
    cada elemento novo na camada do seu original (§5), pareados por ``copies``."""
    from brasbim.core.ops import Transaction

    config = read_config(doc)
    if config is None:
        return tx
    ops = [Op("layer.assign", gid, before={"layer": None}, after={"layer": target})
           for kind, gid, target in copies(doc, tx, sources, lambda e: layer_of(doc, e))
           if target != default_layer(config, kind)]
    return Transaction(tx.label, tx.ops + ops) if ops else tx


def set_default(doc: Document, kind: str, layer_id: str | None):
    from brasbim.core.ops import Transaction

    config = _config(doc)
    if layer_id == NONE:
        layer_id = None
    return Transaction("Camada padrão", [Op(
        "layer.defaults", doc.project.GlobalId,
        before={kind: config["defaults"].get(kind)}, after={kind: layer_id})])


def save_combination(doc: Document, name: str, display: Display):
    from brasbim.core.ops import Transaction

    return Transaction("Salvar combinação de camadas", [Op(
        "layer_combination.create", new_id(),
        data={"name": name.strip(), "states": states_of(doc, display)})])


def update_combination(doc: Document, combination_id: str, display: Display):
    from brasbim.core.ops import Transaction

    comb = combination(doc, combination_id)
    if comb is None:
        raise OpError("combinação não existe")
    return Transaction("Atualizar combinação de camadas", [Op(
        "layer_combination.edit", combination_id,
        before={"states": copy.deepcopy(comb["states"])},
        after={"states": states_of(doc, display)})])


def delete_combination(doc: Document, combination_id: str):
    from brasbim.core.ops import Transaction

    config = _config(doc)
    comb = _by_id(config["combinations"], combination_id)
    if comb is None:
        raise OpError("combinação não existe")
    return Transaction("Excluir combinação de camadas", [Op(
        "layer_combination.delete", combination_id,
        data={"name": comb["name"], "states": copy.deepcopy(comb["states"]),
              "index": config["combinations"].index(comb)})])


def rename_combination(doc: Document, combination_id: str, name: str):
    from brasbim.core.ops import Transaction

    comb = combination(doc, combination_id)
    if comb is None:
        raise OpError("combinação não existe")
    return Transaction("Renomear combinação de camadas", [Op(
        "layer_combination.edit", combination_id, before={"name": comb["name"]},
        after={"name": name.strip()})])


def group_state(doc: Document, display: Display, group_id: str) -> tuple[bool | None, bool | None]:
    """(visível, bloqueado) do grupo: None quando as camadas dele discordam ("misto")."""
    config = read_config(doc) or empty_config()
    states = [display.state(x["id"]) for x in config["layers"] if x.get("group") == group_id]
    if not states:
        return True, False
    vis = {s[0] for s in states}
    lock = {s[1] for s in states}
    return (vis.pop() if len(vis) == 1 else None), (lock.pop() if len(lock) == 1 else None)


def group_layers(doc: Document, group_id: str) -> list[str]:
    config = read_config(doc) or empty_config()
    return [x["id"] for x in config["layers"] if x.get("group") == group_id]


def choices(doc: Document) -> list[tuple[str, str]]:
    """(rótulo, código) de cada camada para as listas da interface, na ordem dos grupos:
    "Grupo › Camada"; as sem grupo no fim, e "Sem camada" por último."""
    config = read_config(doc) or empty_config()
    groups = {g["id"]: g["name"] for g in config["groups"]}
    order = {g["id"]: i for i, g in enumerate(config["groups"])}
    layers = sorted(config["layers"], key=lambda x: order.get(x.get("group"), len(order)))
    out = [(f"{groups[x['group']]} › {x['name']}" if x.get("group") in groups else x["name"],
            x["id"]) for x in layers]
    return [*out, (NONE_NAME, NONE)]


def counts(doc: Document) -> dict[str, int]:
    """Número de elementos (existentes) por camada, "Sem camada" em ``NONE``."""
    out: dict[str, int] = {}
    known = _known(doc)
    for gid, lay in _map(doc).items():
        if doc.find(gid) is not None:
            key = _effective(doc, lay, known)
            out[key] = out.get(key, 0) + 1
    return out
