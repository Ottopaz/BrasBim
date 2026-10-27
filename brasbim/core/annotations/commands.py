# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre ambientes e anotações (spec/ui 13), cada uma uma
``Transaction``. Como nos outros comandos, aqui só se lê o modelo."""

from __future__ import annotations

import copy
import math

import ifcopenshell.util.element

from brasbim.core import geom2d, guid, storeys
from brasbim.core.annotations import base, dimensions, drafting, spaces  # noqa: F401
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def is_annotation(entity) -> bool:
    """Ambiente, anotação ou vista (corte, fachada) do BrasBim."""
    from brasbim.core.drawings import views

    return entity is not None and (entity.is_a("IfcSpace") or base.kind_of(entity) is not None
                                   or views.is_view(entity))


def read_state(doc: Document, element) -> dict:
    from brasbim.core.drawings import views

    if element.is_a("IfcSpace"):
        return spaces.read_state(element)
    return views.read_state(element) if views.is_view(element) else base.read_state(element)


def prefix_of(element) -> str:
    from brasbim.core.drawings import views

    if element.is_a("IfcSpace"):
        return "space"
    return "view" if views.is_view(element) else base.kind_of(element).prefix


def noun_of(element) -> str:
    from brasbim.core.drawings import views

    if element.is_a("IfcSpace"):
        return "ambiente"
    return "vista" if views.is_view(element) else base.kind_of(element).noun


# --- ambientes -------------------------------------------------------------------------


def create_space(doc: Document, storey, outline, number: str | None = None,
                 name: str = spaces.DEFAULT_NAME, height: float | None = None,
                 seed=None) -> Transaction:
    from brasbim.core.structure import slabs

    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    data = {"storey": storey.GlobalId, "outline": slabs.clean(outline),
            "number": number or spaces.next_number(doc, storey), "name": name,
            "height": None if height is None else float(height), "label_at": None,
            "seed": None if seed is None else [float(seed[0]), float(seed[1])]}
    return Transaction("Criar ambiente", [Op("space.create", guid.new(), data=data)])


def create_space_in_room(doc: Document, storey, point, **options) -> Transaction:
    """Ambiente pelo cômodo: contorno na face interna das paredes (spec/ui 13 §3.3), que
    acompanha as paredes depois (``seed``)."""
    from brasbim.core.structure import rooms

    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    return create_space(doc, storey, rooms.room_outline(doc, storey, point, "inner"),
                        seed=point, **options)


# --- anotações -------------------------------------------------------------------------


def create_annotation(doc: Document, prefix: str, storey, **fields) -> Transaction:
    kind = base.KINDS[prefix]
    unknown = set(fields) - set(kind.defaults)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data = {**copy.deepcopy(kind.defaults), **copy.deepcopy(fields),
            "storey": doc.get(_gid(storey), "IfcBuildingStorey").GlobalId}
    _clean(prefix, data)
    kind.validate(data)
    return Transaction(f"Criar {kind.noun}", [Op(f"{prefix}.create", guid.new(), data=data)])


def _clean(prefix: str, data: dict) -> None:
    """Contornos limpos e anti-horários (hachura) e pontos em listas de floats."""
    from brasbim.core.structure import slabs

    if prefix == "hatch" and data.get("outline"):
        data["outline"] = slabs.clean(data["outline"])
    for key in ("at", "label_at"):
        if data.get(key) is not None:
            data[key] = [float(data[key][0]), float(data[key][1])]
    if prefix == "line2d":
        data["points"] = [[float(p[0]), float(p[1])] for p in data["points"]]


def dimension_points(items) -> list[dict]:
    """Pontos da cota a partir de pontos soltos ou pares (ponto, referência)."""
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(copy.deepcopy(item))
            continue
        p, ref = (item if len(item) == 2 and isinstance(item[1], (dict, type(None)))
                  else (item, None))
        out.append({"at": [float(p[0]), float(p[1])], "ref": copy.deepcopy(ref)})
    return out


def create_dimension(doc: Document, storey, points, direction: str = "aligned",
                     angle: float = 0.0, offset: float = 0.0) -> Transaction:
    """Cota pelos ``points`` (soltos ou ``(ponto, referência)``, spec/ui 13 §4)."""
    return create_annotation(doc, "dimension", storey, points=dimension_points(points),
                             direction=direction, angle=float(angle), offset=float(offset))


def edit_element(doc: Document, element, **changes) -> Transaction:
    """Altera campos do estado do ambiente ou da anotação."""
    element = doc.get(_gid(element))
    if not is_annotation(element):
        raise OpError(f"{element.GlobalId} não é ambiente nem anotação")
    from brasbim.core.drawings import views

    state = read_state(doc, element)
    prefix = prefix_of(element)
    keys = (spaces.STATE_KEYS if prefix == "space" else views.STATE_KEYS if prefix == "view"
            else (*base.KINDS[prefix].defaults, "storey"))
    unknown = set(changes) - set(keys)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if prefix == "space" and "outline" in changes:
        from brasbim.core.structure import slabs

        changes["outline"] = slabs.clean(changes["outline"])
        changes.setdefault("seed", None)  # contorno à mão deixa de seguir as paredes
    if prefix == "space" and changes.get("seed") is not None:
        changes["seed"] = [float(changes["seed"][0]), float(changes["seed"][1])]
    _clean(prefix, changes)
    if prefix not in ("space", "view"):
        base.KINDS[prefix].validate({**state, **changes})
    changes = {k: v for k, v in changes.items() if v != state.get(k)}
    noun = noun_of(element)
    if not changes:
        return Transaction(f"Editar {noun}", [])
    return Transaction(f"Editar {noun}", [Op(f"{prefix}.edit", element.GlobalId,
                                             before={k: copy.deepcopy(state[k])
                                                     for k in changes},
                                             after=copy.deepcopy(changes))])


def delete_ops(doc: Document, element) -> list[Op]:
    """Exclusão; a vista sai antes das pranchas em que está (spec/ui 15 §4)."""
    from brasbim.core.drawings import sheets

    element = doc.get(_gid(element))
    ops = sheets.refs_removed_ops(doc, element.GlobalId) if prefix_of(element) == "view"         else []
    return ops + [Op(f"{prefix_of(element)}.delete", element.GlobalId,
                     data=read_state(doc, element))]


def delete_element(doc: Document, element) -> Transaction:
    element = doc.get(_gid(element))
    return Transaction(f"Excluir {noun_of(element)}", delete_ops(doc, element))


# --- vistas (spec/ui 14) -----------------------------------------------------------------


def create_view(doc: Document, kind: str, a, b, side: str = "left",
                **options) -> Transaction:
    """Corte ou fachada pela linha ``a``–``b``, olhando para ``side`` (spec/ui 14 §2)."""
    from brasbim.core.drawings import views

    data = {**views.default_state(), "kind": kind, "a": [float(a[0]), float(a[1])],
            "b": [float(b[0]), float(b[1])], "side": side, **options}
    if data["kind"] == "section" and not data.get("letter"):
        data["letter"] = views.next_letter(doc)
    if not data.get("name"):
        data["name"] = (f"Corte {data['letter']}" if data["kind"] == "section"
                        else views.next_elevation_name(doc))
    views._validate(data)
    noun = "corte" if kind == "section" else "fachada"
    return Transaction(f"Criar {noun}", [Op("view.create", guid.new(), data=data)])


# --- transformações (spec/ui 13 §6) -----------------------------------------------------


def mapped(doc: Document, element, fn, turn, mirrored: bool, moving: set[str]) -> dict:
    """Campos do estado levados pela transformação da planta."""
    state = read_state(doc, element)
    if prefix_of(element) == "view":
        out = {"a": list(fn(tuple(state["a"]))), "b": list(fn(tuple(state["b"])))}
        if mirrored:  # o lado olhado continua o mesmo em relação ao edifício
            out["side"] = "right" if state["side"] == "left" else "left"
        return out
    if element.is_a("IfcSpace"):
        out = {}
        if state["label_at"] is not None:
            out["label_at"] = list(fn(tuple(state["label_at"])))
        if state["seed"] is not None:
            # O contorno do ambiente pelo cômodo é refeito pelas paredes na derivação: a
            # operação leva só o ponto, se as paredes vão junto ou se ele cai num cômodo.
            # Senão o ambiente passa a ter contorno à mão (o ponto é apagado).
            seed = list(fn(tuple(state["seed"])))
            if any(doc.find(g) is not None and doc.find(g).is_a("IfcWall") for g in moving)                     or _in_room(doc, state["storey"], seed):
                return {**out, "seed": seed}
            out["seed"] = None
        out["outline"] = [list(fn(tuple(p))) for p in state["outline"]]
        return out
    return base.kind_of(element).mapped(state, fn, turn, mirrored, moving)


def _in_room(doc: Document, storey, point) -> bool:
    from brasbim.core.structure import rooms

    try:
        rooms.room_ring(doc, doc.get(storey, "IfcBuildingStorey"), tuple(point))
    except OpError:
        return False
    return True


# --- cota automática da parede (spec/ui 13 §4.5) ------------------------------------------


def auto_dimension_wall(doc: Document, wall) -> Transaction:
    """Cota em cadeia na face externa da parede reta: pontas e bordas dos vãos, afastada
    12 mm de papel. A face externa é a do lado oposto ao centro das paredes do pavimento."""
    from brasbim.core.walls import openings, rebuild
    from brasbim.core.walls.wall import read_state as read_wall

    wall = doc.get(_gid(wall), "IfcWall")
    state = read_wall(doc, wall)
    band = rebuild.band(doc, state)
    path = band.path
    if not isinstance(path, geom2d.LinePath):
        raise OpError("a cota automática é só para parede reta")
    storey = doc.get(state["storey"], "IfcBuildingStorey")
    mids = []
    for other in ifcopenshell.util.element.get_decomposition(storey):
        if other.is_a("IfcWall"):
            try:
                p = geom2d.path_from_dict(read_wall(doc, other)["path"])
            except (OpError, ValueError):
                continue
            mids.append(geom2d.path_midpoint(p))
    cx = sum(p[0] for p in mids) / len(mids)
    cy = sum(p[1] for p in mids) / len(mids)
    mid = geom2d.path_midpoint(path)
    n = band.frame.vector_to_global((0.0, 1.0))
    inward = (cx - mid[0]) * n[0] + (cy - mid[1]) * n[1]
    face = "right" if inward > 1e-9 else "left"  # o centro fica à esquerda: externa é a direita
    refs = [{"kind": "wall", "gid": wall.GlobalId, "end": "start", "face": face}]
    for opening in sorted(openings.of_wall(wall),
                          key=lambda o: openings.read_state(o)["distance"]):
        refs += [{"kind": "opening", "gid": opening.GlobalId, "edge": edge, "face": face}
                 for edge in ("start", "end")]
    refs.append({"kind": "wall", "gid": wall.GlobalId, "end": "end", "face": face})
    items, last = [], None
    for ref in refs:
        p = dimensions.resolve(doc, ref)
        if p is None or (last is not None and math.dist(p, last) < 1e-6):
            continue
        items.append((p, ref))
        last = p
    if len(items) < 2:
        raise OpError("não há o que cotar nesta parede")
    offset = storeys.paper(storey, dimensions.AUTO_OFFSET) * (1.0 if face == "left" else -1.0)
    tx = create_dimension(doc, storey, items, "aligned", 0.0, offset)
    tx.label = "Cotar parede"
    return tx
