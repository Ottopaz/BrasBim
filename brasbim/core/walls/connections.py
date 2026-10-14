# SPDX-License-Identifier: LGPL-3.0-or-later
"""Junções entre paredes como ``IfcRelConnectsPathElements`` (spec §2.5, §6.2).

Operações: ``path_connection.create`` / ``path_connection.delete``, com ``id`` = GlobalId
da relação e ``data``::

    {"relating": "<GlobalId>", "related": "<GlobalId>",
     "relating_type": "ATEND", "related_type": "ATSTART"}

O recorte dos corpos é efeito derivado (``rebuild``). ``sync_ops`` compara as junções
detectadas com as existentes e gera as operações que as igualam; os comandos o usam.
"""

from __future__ import annotations

import ifcopenshell.api.root

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, register_inverse_pair
from brasbim.core.walls import joins

REL = "IfcRelConnectsPathElements"
TYPES = ("ATSTART", "ATEND", "ATPATH")


def read(rel) -> dict:
    return {
        "relating": rel.RelatingElement.GlobalId,
        "related": rel.RelatedElement.GlobalId,
        "relating_type": rel.RelatingConnectionType,
        "related_type": rel.RelatedConnectionType,
    }


def of_wall(wall) -> list:
    """Relações de junção da parede, em ordem de GlobalId."""
    rels = [r for r in (*wall.ConnectedTo, *wall.ConnectedFrom) if r.is_a(REL)]
    return sorted(rels, key=lambda r: r.GlobalId)


def neighbors(wall) -> list:
    out = []
    for rel in of_wall(wall):
        other = rel.RelatedElement if rel.RelatingElement == wall else rel.RelatingElement
        out.append(other)
    return out


# --- operações -----------------------------------------------------------------


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    d = op.data
    if d["relating"] == d["related"]:
        raise OpError("uma parede não se liga a si mesma")
    for key in ("relating_type", "related_type"):
        if d[key] not in TYPES:
            raise OpError(f"tipo de conexão inválido: {d[key]!r}")
    relating = doc.get(d["relating"], "IfcWall")
    related = doc.get(d["related"], "IfcWall")
    rel = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class=REL)
    rel.GlobalId = op.id
    rel.RelatingElement = relating
    rel.RelatedElement = related
    rel.RelatingPriorities = []
    rel.RelatedPriorities = []
    rel.RelatingConnectionType = d["relating_type"]
    rel.RelatedConnectionType = d["related_type"]
    return {relating.GlobalId, related.GlobalId}


def _delete(doc: Document, op: Op) -> set[str]:
    rel = doc.get(op.id, REL)
    if read(rel) != op.data:
        raise OpError(f"path_connection.delete {op.id}: relação diferente da registrada")
    doc.ifc.remove(rel)
    return {op.data["relating"], op.data["related"]}


register_inverse_pair("path_connection.create", _create, "path_connection.delete", _delete)


# --- sincronização (usada pelos comandos) ------------------------------------------


def _key(a: str, ta: str, b: str, tb: str) -> frozenset:
    return frozenset({(a, ta), (b, tb)})


def _roles(first: str, tf: str, second: str, ts: str) -> tuple[str, str, str, str]:
    """(relating, related, tipo relating, tipo related) conforme a tabela da spec §6.2.

    ``first`` é a parede que já existia (ou foi criada antes na mesma ação).
    """
    if ts == "ATPATH" and tf != "ATPATH":
        return second, first, ts, tf
    if tf == "ATSTART" and ts == "ATEND":
        return second, first, ts, tf
    return first, second, tf, ts


def sync_ops(doc: Document, changed: dict[str, dict | None]) -> list[Op]:
    """Operações que deixam as junções das paredes ``changed`` iguais às detectadas.

    ``changed``: GlobalId → estado futuro da parede (``None`` = será excluída), em ordem de
    criação. Paredes novas ainda não estão no modelo.
    """
    from brasbim.core.walls import rebuild
    from brasbim.core.walls.wall import read_state

    existing = sorted(doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId)
    order = [w.GlobalId for w in existing] + [g for g in changed if doc.find(g) is None]
    states = {}
    for wall in existing:
        if wall.GlobalId in changed:
            continue
        try:
            states[wall.GlobalId] = read_state(doc, wall)
        except OpError:
            continue  # parede sem estado legível (ex.: sem tipo) não participa
    states.update({g: s for g, s in changed.items() if s is not None})
    index = {g: i for i, g in enumerate(order)}

    def info(state):
        from brasbim.core.geom2d import path_from_dict

        base = rebuild.elevation(doc, state["storey"]) + state["base_offset"]
        return state["storey"], base, base + rebuild.height(doc, state), path_from_dict(
            state["path"]
        )

    cache = {g: info(s) for g, s in states.items()}
    desired: dict[frozenset, dict] = {}
    for c in changed:
        if c not in states:
            continue
        sc, bc, tc, pc = cache[c]
        for g in order:
            if g == c or g not in states:
                continue
            sg, bg, tg, pg = cache[g]
            if sg != sc or min(tc, tg) - max(bc, bg) <= 1e-6:
                continue
            for type_c, type_g in joins.detect(pc, pg):
                key = _key(c, type_c, g, type_g)
                if key in desired:
                    continue
                if index[c] < index[g]:
                    roles = _roles(c, type_c, g, type_g)
                else:
                    roles = _roles(g, type_g, c, type_c)
                desired[key] = dict(zip(("relating", "related", "relating_type",
                                         "related_type"), roles))

    current: dict[frozenset, object] = {}
    for g in changed:
        wall = doc.find(g)
        if wall is None:
            continue
        for rel in of_wall(wall):
            d = read(rel)
            current[_key(d["relating"], d["relating_type"], d["related"], d["related_type"])] = rel

    ops = [Op("path_connection.delete", rel.GlobalId, data=read(rel))
           for key, rel in sorted(current.items(), key=lambda kv: kv[1].GlobalId)
           if key not in desired]
    ops += [Op("path_connection.create", guid.new(), data=data)
            for key, data in desired.items() if key not in current]
    return ops
