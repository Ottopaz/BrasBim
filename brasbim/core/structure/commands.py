# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre pilares, vigas e lajes, cada uma convertida em uma
``Transaction`` (``laje.md`` §5.2, ``pilar.md`` §5.2, ``viga.md`` §5.2).

Como nos comandos da parede, aqui só se lê o modelo para montar as operações; quem
altera o modelo é ``History.commit``.

Pilar e viga com as dimensões escolhidas na hora (decisão do revisor, 2026‑10‑16;
spec/ui 10 §3): ``section=`` em criar e editar acha o tipo com essa seção (e o material e
a representação do tipo de partida) ou cria um na mesma transação, com o nome "Pilar
25×60". O IFC continua com um ``IfcColumnType``/``IfcBeamType`` por seção, e os elementos
iguais dividem o mesmo perfil.
"""

from __future__ import annotations

import copy
import itertools
import math

import ifcopenshell.util.element

from brasbim.core import guid, profile_defs
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.base import same_value
from brasbim.core.ops.history import combine
from brasbim.core.structure import beams, columns, common, profiles, roofs, slab_openings, slabs
from brasbim.core.structure import types as st_types

gid = common.gid

# Classe → (módulo, prefixo das operações, substantivo, plural).
ELEMENTS = {
    "IfcColumn": (columns, "column", "pilar", "pilares"),
    "IfcBeam": (beams, "beam", "viga", "vigas"),
    "IfcSlab": (slabs, "slab", "laje", "lajes"),
    "IfcRoof": (roofs, "roof", "cobertura", "coberturas"),
}
TYPE_CLASSES = {"IfcColumnType": "column", "IfcBeamType": "beam", "IfcSlabType": "slab"}


def is_structure(entity) -> bool:
    """Pilar, viga, laje ou cobertura do BrasBim. A peça (água) da cobertura não conta:
    quem se seleciona, move e exclui é a cobertura (cobertura.md §5)."""
    if entity.is_a() not in ELEMENTS:
        return False
    if entity.is_a("IfcRoof"):
        return roofs.is_roof(entity)
    return not (entity.is_a("IfcSlab") and roofs.is_part(entity))


def module_of(entity):
    return ELEMENTS[entity.is_a()][0]


def read_state(doc: Document, element) -> dict:
    return module_of(element).read_state(doc, element)


def _element(doc: Document, element, ifc_class: str | None = None):
    element = doc.get(gid(element), ifc_class)
    if not is_structure(element):
        raise OpError(f"{element.GlobalId} não é pilar, viga, laje nem cobertura")
    return element


# --- tipos -----------------------------------------------------------------------------


def create_column_type(doc: Document, name: str, section: dict, material: str = "Concreto",
                       plan_style: dict | None = None) -> Transaction:
    data = {"name": name, "predefined_type": "COLUMN", "section": dict(section),
            "material": material, "plan_style": plan_style}
    return Transaction("Criar tipo de pilar", [Op("column_type.create", guid.new(), data=data)])


def create_beam_type(doc: Document, name: str, b: float, h: float, material: str = "Concreto",
                     plan_style: dict | None = None, section: dict | None = None) -> Transaction:
    """Tipo de viga retangular b × h, ou com ``section`` (ex.: perfil do projeto)."""
    data = {"name": name, "predefined_type": "BEAM",
            "section": dict(section) if section is not None
            else {"shape": "rect", "b": float(b), "h": float(h)},
            "material": material, "plan_style": plan_style}
    return Transaction("Criar tipo de viga", [Op("beam_type.create", guid.new(), data=data)])


def create_slab_type(doc: Document, name: str, layers: list[dict],
                     predefined_type: str = "FLOOR",
                     plan_style: dict | None = None) -> Transaction:
    """``layers`` de cima para baixo (laje.md §2.3)."""
    data = {"name": name, "predefined_type": predefined_type,
            "layers": [{"material": layer["material"], "thickness": float(layer["thickness"])}
                       for layer in layers],
            "plan_style": plan_style}
    return Transaction("Criar tipo de laje", [Op("slab_type.create", guid.new(), data=data)])


def read_type(element_type) -> dict:
    if element_type.is_a("IfcSlabType"):
        return st_types.read_slab_type(element_type)
    return st_types.read_profile_type(element_type)


def _type(doc: Document, element_type):
    element_type = doc.get(gid(element_type), "IfcTypeObject")
    if element_type.is_a() not in TYPE_CLASSES:
        raise OpError(f"{element_type.GlobalId} não é tipo de pilar, viga nem laje")
    return element_type


_TYPE_NOUN = {"column": "pilar", "beam": "viga", "slab": "laje"}


def edit_type(doc: Document, element_type, **changes) -> Transaction:
    element_type = _type(doc, element_type)
    prefix = TYPE_CLASSES[element_type.is_a()]
    state = read_type(element_type)
    unknown = set(changes) - set(state)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    before = {k: state[k] for k in changes}
    return Transaction(f"Editar tipo de {_TYPE_NOUN[prefix]}",
                       [Op(f"{prefix}_type.edit", element_type.GlobalId, before=before,
                           after=copy.deepcopy(changes))])


def delete_type(doc: Document, element_type, replacement=None) -> Transaction:
    """Exclui o tipo. Em uso, os elementos passam para ``replacement`` (spec/ui 10 §5)."""
    element_type = _type(doc, element_type)
    prefix = TYPE_CLASSES[element_type.is_a()]
    owners = {}
    for e in ifcopenshell.util.element.get_types(element_type):
        owner = roofs.roof_of(e) or e  # as águas trocam de tipo pela cobertura
        owners[owner.GlobalId] = owner
    used = [owners[g] for g in sorted(owners)]
    ops = []
    if used:
        if replacement is None:
            raise OpError(f"o tipo {element_type.Name} é usado por {len(used)} elemento(s)")
        other = _type(doc, replacement)
        if other.is_a() != element_type.is_a() or other == element_type:
            raise OpError("escolha outro tipo do mesmo elemento")
        if any(e.is_a("IfcRoof") for e in used) and other.PredefinedType != "ROOF":
            raise OpError("as coberturas precisam de um tipo de cobertura")
        ops = [op for e in used for op in edit_element(doc, e, type=other.GlobalId).ops]
    from brasbim.core.quantities import tables  # o tipo sai do filtro das tabelas

    ops += tables.refs_removed_ops(doc, element_type.GlobalId)
    ops.append(Op(f"{prefix}_type.delete", element_type.GlobalId, data=read_type(element_type)))
    return Transaction(f"Excluir tipo de {_TYPE_NOUN[prefix]}", ops)


# --- tipo pela seção (spec/ui 10 §3) ----------------------------------------------------

_PROFILE_TYPES = {"column": ("IfcColumnType", "Pilar", st_types.COLUMN),
                  "beam": ("IfcBeamType", "Viga", st_types.BEAM)}


def section_name(prefix: str, section: dict) -> str:
    """"Pilar 25×60", "Pilar Ø35", "Viga 14×40" (dimensões em centímetros)."""
    word = _PROFILE_TYPES[prefix][1]
    if section.get("shape") == profiles.CUSTOM:
        cm = profiles.label({"shape": "rect", "b": section["b"], "h": section["h"]})
        return f"{word} {section.get('name') or 'perfil'} {cm.replace(' × ', '×')}"
    return f"{word} {profiles.label(section).replace(' × ', '×').replace('Ø ', 'Ø')}"


def section_type(doc: Document, prefix: str, section: dict, base=None) -> tuple[str, list[Op]]:
    """(GlobalId do tipo com esta seção, operações para criá-lo se faltar). Material e
    representação na planta vêm de ``base`` (o tipo atual), senão Concreto e o padrão."""
    type_class, _, kind = _PROFILE_TYPES[prefix]
    section = {k: (v if k in ("shape", "profile") else float(v))
               for k, v in st_types.stored_section(section).items()}
    try:
        profiles.validate(section, kind.shapes)
    except (ValueError, KeyError) as e:
        raise OpError(str(e)) from e
    custom = section["shape"] == profiles.CUSTOM
    base = doc.find(gid(base)) if base is not None else None
    base_state = st_types.read_profile_type(base) if base is not None else None
    material = None if custom else (base_state["material"] if base_state
                                     and base_state["material"] else "Concreto")
    plan_style = base_state["plan_style"] if base_state else None
    found = []
    for t in sorted(doc.ifc.by_type(type_class), key=lambda t: t.GlobalId):
        try:
            state = st_types.read_profile_type(t)
        except OpError:
            continue
        if (same_value(state["section"], section) and state["material"] == material
                and state["plan_style"] == plan_style):
            found.append(t)
    label = dict(section, name=profile_defs.state(doc, section["profile"])["name"]) \
        if custom else section
    name = section_name(prefix, label)
    if found:  # o de nome padrão primeiro (o da biblioteca)
        return min(found, key=lambda t: (t.Name != name, t.Name or "")).GlobalId, []
    names = {t.Name for t in doc.ifc.by_type(type_class)}
    unique, n = name, 2
    while unique in names:
        unique = f"{name} ({n})"
        n += 1
    data = {"name": unique, "predefined_type": kind.predefined_types[0], "section": section,
            "material": material, "plan_style": plan_style}
    new = guid.new()
    return new, [Op(f"{prefix}_type.create", new, data=data)]


# --- criação ---------------------------------------------------------------------------


def _with_options(state: dict, options: dict, keys) -> dict:
    unknown = set(options) - set(keys)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    for key in ("type", "storey", "top_storey"):
        if options.get(key) is not None:
            options[key] = gid(options[key])
    state.update(options)
    return state


def column_data(doc: Document, column_type, storey, point, **options) -> dict:
    storey_id = gid(storey)
    data = {**columns.default_state(), **common.default_top(doc, storey_id),
            "type": gid(column_type), "storey": storey_id,
            "point": [float(point[0]), float(point[1])]}
    data = _with_options(data, options, columns.STATE_KEYS)
    if data["name"] is None:
        data["name"] = common.next_name(doc, "IfcColumn", "P")
    return data


def create_column(doc: Document, column_type, storey, point, section: dict | None = None,
                  **options) -> Transaction:
    """Pilar no ponto de inserção ``point`` (pilar.md §4). Com ``section``, o tipo é o
    dessa seção (criado se faltar)."""
    ops = []
    if section is not None:
        column_type, ops = section_type(doc, "column", section, column_type)
        if section["shape"] == "circle":
            options["cardinal"] = 5
    data = column_data(doc, column_type, storey, point, **options)
    return Transaction("Criar pilar", [*ops, Op("column.create", guid.new(), data=data)])


def _beam_ops(doc: Document, beam_type, storey, segments, options) -> list[Op]:
    ops, names = [], set()
    storey_id = gid(storey)
    for start, end in segments:
        data = {**beams.default_state(), **common.default_top(doc, storey_id),
                "type": gid(beam_type), "storey": storey_id,
                "start": [float(start[0]), float(start[1])],
                "end": [float(end[0]), float(end[1])]}
        data = _with_options(data, dict(options), beams.STATE_KEYS)
        if data["name"] is None:
            used = {e.Name for e in doc.ifc.by_type("IfcBeam")} | names
            n = next(k for k in itertools.count(1) if f"V{k}" not in used)
            data["name"] = f"V{n}"
        names.add(data["name"])
        if math.dist(start, end) <= beams.MIN_LENGTH:
            raise OpError(f"a viga precisa ter mais de {beams.MIN_LENGTH:.2f} m")
        ops.append(Op("beam.create", guid.new(), data=data))
    return ops


def create_beam(doc: Document, beam_type, storey, start, end, section: dict | None = None,
                **options) -> Transaction:
    """Viga reta de ``start`` a ``end`` (viga.md §4). Com ``section``, o tipo é o dessa
    seção (criado se faltar)."""
    return create_beam_chain(doc, beam_type, storey, [start, end], section, **options)


def create_beam_chain(doc: Document, beam_type, storey, points, section: dict | None = None,
                      **options) -> Transaction:
    """Vigas em cadeia pelos ``points``."""
    pts = [tuple(p) for p in points]
    if len(pts) < 2:
        raise OpError("a cadeia precisa de pelo menos 2 pontos")
    ops = []
    if section is not None:
        beam_type, ops = section_type(doc, "beam", section, beam_type)
    segments = list(itertools.pairwise(pts))
    return Transaction("Criar viga" if len(segments) == 1 else "Criar vigas",
                       ops + _beam_ops(doc, beam_type, storey, segments, options))


def create_slab(doc: Document, slab_type, storey, outline, **options) -> Transaction:
    """Laje pelo contorno (laje.md §4); o sentido é corrigido para anti-horário."""
    data = {**slabs.default_state(), "type": gid(slab_type), "storey": gid(storey),
            "outline": slabs.clean(outline)}
    data = _with_options(data, options, slabs.STATE_KEYS)
    return Transaction("Criar laje", [Op("slab.create", guid.new(), data=data)])


def create_slab_in_room(doc: Document, slab_type, storey, point, boundary: str = "outer",
                        **options) -> Transaction:
    """Laje do cômodo fechado por paredes que contém ``point`` (spec/ui 12 §4)."""
    from brasbim.core.structure import rooms

    outline = rooms.room_outline(doc, doc.get(gid(storey), "IfcBuildingStorey"), point,
                                 boundary)
    return create_slab(doc, slab_type, storey, outline, **options)


def create_slab_rectangle(doc: Document, slab_type, storey, corner, opposite, **options):
    (x0, x1), (y0, y1) = sorted((corner[0], opposite[0])), sorted((corner[1], opposite[1]))
    return create_slab(doc, slab_type, storey, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                       **options)


def create_roof(doc: Document, slab_type, storey, outline, shape: str = "gable",
                slope: float = roofs.DEFAULT_SLOPE, overhang: float = roofs.DEFAULT_OVERHANG,
                base_height: float | None = None, side: int | None = None,
                name: str | None = None) -> Transaction:
    """Cobertura pelo contorno de apoio (cobertura.md §4); sem ``base_height``, no topo
    das paredes do pavimento; sem ``side``, o lado maior."""
    storey = doc.get(gid(storey), "IfcBuildingStorey")
    if shape not in roofs.SHAPES:
        raise OpError(f"forma de cobertura inválida: {shape!r}")
    data = {**roofs.default_state(), "type": gid(slab_type), "storey": storey.GlobalId,
            "outline": roofs.clean(outline), "shape": shape, "slope": float(slope),
            "overhang": float(overhang),
            "base_height": float(roofs.wall_top(doc, storey) if base_height is None
                                 else base_height),
            "side": side, "parts": roofs.part_ids(shape),
            "name": name or next_roof_name(doc)}
    data = roofs.normalized(data)
    roofs.validate(data)
    if doc.get(data["type"], "IfcSlabType").PredefinedType != "ROOF":
        raise OpError("escolha um tipo de cobertura")
    return Transaction("Criar cobertura", [Op("roof.create", guid.new(), data=data)])


def next_roof_name(doc: Document, taken=()) -> str:
    used = {e.Name for e in doc.ifc.by_type("IfcRoof")} | set(taken)
    return next(f"Cobertura {n}" for n in itertools.count(1)
                if f"Cobertura {n}" not in used)


def create_roof_over_walls(doc: Document, slab_type, storey, point=None,
                           **options) -> Transaction:
    """Cobertura sobre o contorno externo das paredes em volta de ``point`` (§4); sem
    ``point``, sobre a maior edificação do pavimento."""
    from brasbim.core.structure import rooms

    outline = rooms.building_outline(doc, doc.get(gid(storey), "IfcBuildingStorey"), point)
    return create_roof(doc, slab_type, storey, outline, **options)


# --- edição ----------------------------------------------------------------------------


def edit_element(doc: Document, element, **changes) -> Transaction:
    """Altera campos do estado (``STATE_KEYS`` do elemento). Em pilar e viga,
    ``section=`` troca só este elemento para o tipo dessa seção (criado se faltar)."""
    element = _element(doc, element)
    module, prefix, noun, _ = ELEMENTS[element.is_a()]
    state = module.read_state(doc, element)
    section = changes.pop("section", None)
    pre: list[Op] = []
    if section is not None:
        if prefix == "slab":
            raise OpError("a laje não tem seção; troque o tipo")
        if state["foreign"] is not None:
            raise OpError(f"{noun} de outra origem: a seção vem do corpo original")
        changes["type"], pre = section_type(doc, prefix, section, state["type"])
        if prefix == "column" and section["shape"] == "circle":
            changes.setdefault("cardinal", 5)
    for key in ("type", "storey", "top_storey"):
        if changes.get(key) is not None:
            changes[key] = gid(changes[key])
    unknown = set(changes) - set(module.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if "outline" in changes:
        changes["outline"] = (roofs.clean if prefix == "roof" else slabs.clean)(
            changes["outline"])
    if prefix == "roof":
        if "shape" in changes and "parts" not in changes:
            changes["parts"] = roofs.part_ids(changes["shape"], state["parts"])
        for key in ("slope", "overhang", "base_height"):
            if key in changes:
                changes[key] = float(changes[key])
        new = roofs.normalized({**state, **changes})
        roofs.validate(new)
        if "type" in changes and doc.get(changes["type"]).PredefinedType != "ROOF":
            raise OpError("escolha um tipo de cobertura")
        if new["side"] != state["side"]:
            changes["side"] = new["side"]
    # O pilar circular só tem o centro como ponto de inserção (pilar.md §3.1).
    if (element.is_a("IfcColumn") and changes.get("type") and not pre
            and state["foreign"] is None
            and st_types.section(doc.get(changes["type"]))["shape"] == "circle"):
        changes.setdefault("cardinal", 5)
    for key in ("point", "start", "end"):
        if key in changes:
            changes[key] = [float(changes[key][0]), float(changes[key][1])]
    if "top_mode" in changes and "top_storey" not in changes:
        # Levar o pavimento junto permite desfazer a troca para altura (cota) fixa.
        if changes["top_mode"] == "storey":
            changes["top_storey"] = state["top_storey"] or common.default_top(
                doc, state["storey"])["top_storey"]
        else:
            changes["top_storey"] = None
    changes = {k: v for k, v in changes.items() if v != state.get(k)}
    if not changes:
        return Transaction(f"Editar {noun}", [])
    before = {k: copy.deepcopy(state[k]) for k in changes}
    return Transaction(f"Editar {noun}", [*pre, Op(f"{prefix}.edit", element.GlobalId,
                                                   before=before,
                                                   after=copy.deepcopy(changes))])


def edit_elements(doc: Document, elements, **changes) -> Transaction:
    """Edição em lote (spec/ui 02 §9): a mesma mudança em cada elemento."""
    elements = list(elements)
    if len(elements) == 1:
        return edit_element(doc, elements[0], **changes)
    return combine(doc, f"Editar {len(elements)} elementos",
                   [lambda e=e: edit_element(doc, e, **copy.deepcopy(changes))
                    for e in elements])


def delete_ops(doc: Document, element) -> list[Op]:
    """Exclusão; a laje leva antes as aberturas dela (spec/ui 12 §3.2)."""
    entity = doc.get(gid(element))
    if slab_openings.is_slab_opening(entity):
        return [Op("slab_opening.delete", entity.GlobalId,
                   data=slab_openings.read_state(entity))]
    element = _element(doc, element)
    module, prefix, _, _ = ELEMENTS[element.is_a()]
    ops = []
    if element.is_a("IfcSlab"):
        ops = [op for o in slab_openings.of_slab(element) for op in delete_ops(doc, o)]
    return ops + [Op(f"{prefix}.delete", element.GlobalId,
                     data=module.read_state(doc, element))]


def delete_element(doc: Document, element) -> Transaction:
    entity = doc.get(gid(element))
    if slab_openings.is_slab_opening(entity):
        return Transaction("Excluir abertura na laje", delete_ops(doc, entity))
    element = _element(doc, element)
    return Transaction(f"Excluir {ELEMENTS[element.is_a()][2]}", delete_ops(doc, element))


# --- aberturas na laje (spec/ui 12 §3) ---------------------------------------------------


def create_slab_opening(doc: Document, slab, outline) -> Transaction:
    """Abertura na laje pelo contorno (coordenadas do pavimento)."""
    slab = _element(doc, slab, "IfcSlab")
    state = {"slab": slab.GlobalId, "outline": outline}
    state["outline"] = slab_openings.check(doc, state)
    return Transaction("Criar abertura na laje",
                       [Op("slab_opening.create", guid.new(), data=state)])


def create_slab_opening_rectangle(doc: Document, slab, corner, opposite) -> Transaction:
    (x0, x1), (y0, y1) = sorted((corner[0], opposite[0])), sorted((corner[1], opposite[1]))
    return create_slab_opening(doc, slab, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def edit_slab_opening(doc: Document, opening, outline) -> Transaction:
    opening = doc.get(gid(opening), "IfcOpeningElement")
    state = slab_openings.read_state(opening)
    new = slab_openings.check(doc, {**state, "outline": outline})
    if new == state["outline"]:
        return Transaction("Editar abertura na laje", [])
    return Transaction("Editar abertura na laje", [
        Op("slab_opening.edit", opening.GlobalId, before={"outline": state["outline"]},
           after={"outline": new})])


def outline_of(doc: Document, element) -> list:
    """Contorno de laje, de abertura na laje ou de ambiente (as alças são as mesmas)."""
    entity = doc.get(gid(element))
    if slab_openings.is_slab_opening(entity):
        return slab_openings.read_state(entity)["outline"]
    if entity.is_a("IfcSpace"):
        from brasbim.core.annotations import spaces

        return spaces.read_state(entity)["outline"]
    if entity.is_a("IfcRoof"):
        return roofs.read_state(doc, entity)["outline"]
    return slabs.read_state(doc, _element(doc, entity, "IfcSlab"))["outline"]


def edit_outline(doc: Document, element, outline) -> Transaction:
    entity = doc.get(gid(element))
    if slab_openings.is_slab_opening(entity):
        return edit_slab_opening(doc, entity, outline)
    if entity.is_a("IfcSpace"):
        from brasbim.core.annotations import commands as anno_cmd

        return anno_cmd.edit_element(doc, entity, outline=outline)
    if entity.is_a("IfcRoof"):  # o lado escolhido segue o mesmo índice (cobertura.md §5)
        return edit_element(doc, entity, outline=outline)
    outline = slabs.clean(outline)
    for opening in slab_openings.of_slab(entity):  # spec/ui 12 §3.2
        if not slab_openings.inside(slab_openings.read_state(opening)["outline"], outline):
            raise OpError("uma abertura ficaria fora da laje")
    return edit_element(doc, entity, outline=outline)


# --- alças (spec/ui 10 §4.1) -------------------------------------------------------------


def move_beam_end(doc: Document, beam, end: str, point) -> Transaction:
    """Estica ou encurta a viga pela ponta ``end`` (``start``/``end``)."""
    if end not in ("start", "end"):
        raise OpError(f"ponta inválida: {end!r}")
    tx = edit_element(doc, _element(doc, beam, "IfcBeam"), **{end: point})
    tx.label = "Esticar viga"
    return tx


def move_slab_vertex(doc: Document, slab, index: int, point) -> Transaction:
    """Alça de vértice da laje ou da abertura na laje."""
    outline = copy.deepcopy(outline_of(doc, slab))
    outline[index] = [float(point[0]), float(point[1])]
    tx = edit_outline(doc, slab, outline)
    tx.label = "Mover vértice"
    return tx


def offset_slab_edge(doc: Document, slab, index: int, distance: float) -> Transaction:
    """Desloca o lado ``index`` (do vértice ``index`` ao seguinte) paralelamente,
    ``distance`` para fora da laje (negativo: para dentro). Os lados vizinhos esticam
    ou encurtam pela própria direção. Vale também para a abertura na laje."""
    pts = [tuple(p) for p in outline_of(doc, slab)]
    n = len(pts)
    a, b = pts[index], pts[(index + 1) % n]
    length = math.dist(a, b)
    # Contorno anti-horário: a normal para fora fica à direita do lado.
    nx, ny = (b[1] - a[1]) / length, -(b[0] - a[0]) / length
    shift = (nx * distance, ny * distance)
    na, nb = (a[0] + shift[0], a[1] + shift[1]), (b[0] + shift[0], b[1] + shift[1])

    def meet(p, q, origin, direction):
        """Cruzamento da reta ``p``–``q`` com a reta por ``origin`` na ``direction``."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        det = dx * direction[1] - dy * direction[0]
        if abs(det) < 1e-12:
            return None
        t = ((origin[0] - p[0]) * direction[1] - (origin[1] - p[1]) * direction[0]) / det
        return (p[0] + t * dx, p[1] + t * dy)

    d = (b[0] - a[0], b[1] - a[1])
    prev, nxt = pts[index - 1], pts[(index + 2) % n]
    new = list(pts)
    new[index] = meet(prev, a, na, d) or na
    new[(index + 1) % n] = meet(nxt, b, nb, d) or nb
    tx = edit_outline(doc, slab, new)
    tx.label = "Deslocar lado"
    return tx


# --- pavimentos ------------------------------------------------------------------------


def storey_delete_ops(doc: Document, storey) -> list[Op]:
    """Pilares e vigas com topo no pavimento excluído passam a altura (cota) fixa, com a
    altura atual (spec/ui 10 §8)."""
    ops = []
    for column in sorted(doc.ifc.by_type("IfcColumn"), key=lambda e: e.GlobalId):
        state = columns.read_state(doc, column)
        if state["foreign"] is None and state["top_mode"] == "storey" \
                and state["top_storey"] == storey.GlobalId:
            keys = ("top_mode", "top_storey", "fixed_height")
            ops.append(Op("column.edit", column.GlobalId, before={k: state[k] for k in keys},
                          after={"top_mode": "fixed", "top_storey": None,
                                 "fixed_height": columns.height(doc, state)}))
    for beam in sorted(doc.ifc.by_type("IfcBeam"), key=lambda e: e.GlobalId):
        state = beams.read_state(doc, beam)
        if state["foreign"] is None and state["top_mode"] == "storey" \
                and state["top_storey"] == storey.GlobalId:
            keys = ("top_mode", "top_storey", "top_elevation")
            ops.append(Op("beam.edit", beam.GlobalId, before={k: state[k] for k in keys},
                          after={"top_mode": "fixed", "top_storey": None,
                                 "top_elevation": beams.top_z(doc, state)}))
    return ops
