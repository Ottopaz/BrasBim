# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre pilares, vigas e lajes, cada uma convertida em uma
``Transaction`` (``laje.md`` §5.2, ``pilar.md`` §5.2, ``viga.md`` §5.2).

Como nos comandos da parede, aqui só se lê o modelo para montar as operações; quem
altera o modelo é ``History.commit``.
"""

from __future__ import annotations

import copy
import itertools
import math

import ifcopenshell.util.element

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction
from brasbim.core.ops.history import combine
from brasbim.core.structure import beams, columns, common, slabs
from brasbim.core.structure import types as st_types

gid = common.gid

# Classe → (módulo, prefixo das operações, substantivo, plural).
ELEMENTS = {
    "IfcColumn": (columns, "column", "pilar", "pilares"),
    "IfcBeam": (beams, "beam", "viga", "vigas"),
    "IfcSlab": (slabs, "slab", "laje", "lajes"),
}
TYPE_CLASSES = {"IfcColumnType": "column", "IfcBeamType": "beam", "IfcSlabType": "slab"}


def is_structure(entity) -> bool:
    return entity.is_a() in ELEMENTS


def module_of(entity):
    return ELEMENTS[entity.is_a()][0]


def read_state(doc: Document, element) -> dict:
    return module_of(element).read_state(doc, element)


def _element(doc: Document, element, ifc_class: str | None = None):
    element = doc.get(gid(element), ifc_class)
    if not is_structure(element):
        raise OpError(f"{element.GlobalId} não é pilar, viga nem laje")
    return element


# --- tipos -----------------------------------------------------------------------------


def create_column_type(doc: Document, name: str, section: dict, material: str = "Concreto",
                       plan_style: dict | None = None) -> Transaction:
    data = {"name": name, "predefined_type": "COLUMN", "section": dict(section),
            "material": material, "plan_style": plan_style}
    return Transaction("Criar tipo de pilar", [Op("column_type.create", guid.new(), data=data)])


def create_beam_type(doc: Document, name: str, b: float, h: float, material: str = "Concreto",
                     plan_style: dict | None = None) -> Transaction:
    data = {"name": name, "predefined_type": "BEAM",
            "section": {"shape": "rect", "b": float(b), "h": float(h)},
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
    used = sorted(ifcopenshell.util.element.get_types(element_type), key=lambda e: e.GlobalId)
    ops = []
    if used:
        if replacement is None:
            raise OpError(f"o tipo {element_type.Name} é usado por {len(used)} elemento(s)")
        other = _type(doc, replacement)
        if other.is_a() != element_type.is_a() or other == element_type:
            raise OpError("escolha outro tipo do mesmo elemento")
        ops = [op for e in used for op in edit_element(doc, e, type=other.GlobalId).ops]
    ops.append(Op(f"{prefix}_type.delete", element_type.GlobalId, data=read_type(element_type)))
    return Transaction(f"Excluir tipo de {_TYPE_NOUN[prefix]}", ops)


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


def create_column(doc: Document, column_type, storey, point, **options) -> Transaction:
    """Pilar no ponto de inserção ``point`` (pilar.md §4)."""
    data = column_data(doc, column_type, storey, point, **options)
    return Transaction("Criar pilar", [Op("column.create", guid.new(), data=data)])


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


def create_beam(doc: Document, beam_type, storey, start, end, **options) -> Transaction:
    """Viga reta de ``start`` a ``end`` (viga.md §4)."""
    return Transaction("Criar viga", _beam_ops(doc, beam_type, storey, [(start, end)], options))


def create_beam_chain(doc: Document, beam_type, storey, points, **options) -> Transaction:
    """Vigas em cadeia pelos ``points``."""
    pts = [tuple(p) for p in points]
    if len(pts) < 2:
        raise OpError("a cadeia precisa de pelo menos 2 pontos")
    return Transaction("Criar vigas", _beam_ops(doc, beam_type, storey,
                                                list(itertools.pairwise(pts)), options))


def create_slab(doc: Document, slab_type, storey, outline, **options) -> Transaction:
    """Laje pelo contorno (laje.md §4); o sentido é corrigido para anti-horário."""
    data = {**slabs.default_state(), "type": gid(slab_type), "storey": gid(storey),
            "outline": slabs.clean(outline)}
    data = _with_options(data, options, slabs.STATE_KEYS)
    return Transaction("Criar laje", [Op("slab.create", guid.new(), data=data)])


def create_slab_rectangle(doc: Document, slab_type, storey, corner, opposite, **options):
    (x0, x1), (y0, y1) = sorted((corner[0], opposite[0])), sorted((corner[1], opposite[1]))
    return create_slab(doc, slab_type, storey, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                       **options)


# --- edição ----------------------------------------------------------------------------


def edit_element(doc: Document, element, **changes) -> Transaction:
    """Altera campos do estado (``STATE_KEYS`` do elemento)."""
    element = _element(doc, element)
    module, prefix, noun, _ = ELEMENTS[element.is_a()]
    state = module.read_state(doc, element)
    for key in ("type", "storey", "top_storey"):
        if changes.get(key) is not None:
            changes[key] = gid(changes[key])
    unknown = set(changes) - set(module.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if "outline" in changes:
        changes["outline"] = slabs.clean(changes["outline"])
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
    return Transaction(f"Editar {noun}", [Op(f"{prefix}.edit", element.GlobalId,
                                             before=before, after=copy.deepcopy(changes))])


def edit_elements(doc: Document, elements, **changes) -> Transaction:
    """Edição em lote (spec/ui 02 §9): a mesma mudança em cada elemento."""
    elements = list(elements)
    if len(elements) == 1:
        return edit_element(doc, elements[0], **changes)
    return combine(doc, f"Editar {len(elements)} elementos",
                   [lambda e=e: edit_element(doc, e, **copy.deepcopy(changes))
                    for e in elements])


def delete_ops(doc: Document, element) -> list[Op]:
    element = _element(doc, element)
    module, prefix, _, _ = ELEMENTS[element.is_a()]
    return [Op(f"{prefix}.delete", element.GlobalId, data=module.read_state(doc, element))]


def delete_element(doc: Document, element) -> Transaction:
    element = _element(doc, element)
    return Transaction(f"Excluir {ELEMENTS[element.is_a()][2]}", delete_ops(doc, element))


# --- alças (spec/ui 10 §4.1) -------------------------------------------------------------


def move_beam_end(doc: Document, beam, end: str, point) -> Transaction:
    """Estica ou encurta a viga pela ponta ``end`` (``start``/``end``)."""
    if end not in ("start", "end"):
        raise OpError(f"ponta inválida: {end!r}")
    tx = edit_element(doc, _element(doc, beam, "IfcBeam"), **{end: point})
    tx.label = "Esticar viga"
    return tx


def move_slab_vertex(doc: Document, slab, index: int, point) -> Transaction:
    slab = _element(doc, slab, "IfcSlab")
    outline = copy.deepcopy(slabs.read_state(doc, slab)["outline"])
    outline[index] = [float(point[0]), float(point[1])]
    tx = edit_element(doc, slab, outline=outline)
    tx.label = "Mover vértice da laje"
    return tx


def offset_slab_edge(doc: Document, slab, index: int, distance: float) -> Transaction:
    """Desloca o lado ``index`` (do vértice ``index`` ao seguinte) paralelamente,
    ``distance`` para fora da laje (negativo: para dentro). Os lados vizinhos esticam
    ou encurtam pela própria direção."""
    slab = _element(doc, slab, "IfcSlab")
    pts = [tuple(p) for p in slabs.read_state(doc, slab)["outline"]]
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
    tx = edit_element(doc, slab, outline=new)
    tx.label = "Deslocar lado da laje"
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
