# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ações do usuário sobre paredes, cada uma convertida em uma ``Transaction``.

Os comandos só leem o modelo para montar as operações; quem altera o modelo é
``History.commit``. Assim, cada ação gera exatamente as operações de spec §5.2.
"""

from __future__ import annotations

from brasbim.core import geom2d, guid
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Op, Transaction
from brasbim.core.walls import params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state


def _gid(obj) -> str:
    return obj if isinstance(obj, str) else obj.GlobalId


def _wall_data(doc: Document, wall_type, storey, path: geom2d.Path, options: dict) -> dict:
    data = {
        **params.default_state(),
        "type": _gid(wall_type),
        "storey": _gid(storey),
        "path": path.to_dict(),
    }
    unknown = set(options) - set(params.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    data.update(options)
    if "top_mode" not in options:
        # Padrão (spec §3.1): topo ligado ao pavimento imediatamente acima, se houver.
        above = doc.storey_above(doc.get(data["storey"], "IfcBuildingStorey"))
        if above is not None:
            data["top_mode"], data["top_storey"] = "storey", above.GlobalId
    if data["top_mode"] == "storey" and data.get("top_storey"):
        data["top_storey"] = _gid(data["top_storey"])
    return data


def create_wall(doc: Document, wall_type, storey, start, end, **options) -> Transaction:
    """Parede reta de ``start`` a ``end`` (coordenadas do pavimento, em metros)."""
    path = geom2d.LinePath(tuple(start), tuple(end))
    data = _wall_data(doc, wall_type, storey, path, options)
    return Transaction("Criar parede", [Op("wall.create", guid.new(), data=data)])


def create_arc_wall(doc: Document, wall_type, storey, start, through, end, **options):
    """Parede em arco por 3 pontos: início, um ponto no arco e fim (spec §4)."""
    path = geom2d.arc_through(tuple(start), tuple(through), tuple(end))
    data = _wall_data(doc, wall_type, storey, path, options)
    return Transaction("Criar parede em arco", [Op("wall.create", guid.new(), data=data)])


def edit_wall(doc: Document, wall, **changes) -> Transaction:
    """Altera campos do estado da parede (``params.STATE_KEYS``)."""
    wall = doc.get(_gid(wall), "IfcWall")
    state = read_state(doc, wall)
    for key in ("type", "storey", "top_storey"):
        if changes.get(key) is not None:
            changes[key] = _gid(changes[key])
    if "path" in changes and not isinstance(changes["path"], dict):
        changes["path"] = changes["path"].to_dict()
    unknown = set(changes) - set(params.STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    before = {k: state[k] for k in changes}
    return Transaction(
        "Editar parede", [Op("wall.edit", wall.GlobalId, before=before, after=dict(changes))]
    )


def delete_wall(doc: Document, wall) -> Transaction:
    """Exclui a parede. A cascata (aberturas, preenchimentos, junções; spec §6.4) entra
    nesta mesma transação, antes do ``wall.delete``."""
    wall = doc.get(_gid(wall), "IfcWall")
    ops = [Op("wall.delete", wall.GlobalId, data=read_state(doc, wall))]
    return Transaction("Excluir parede", ops)


# --- tipos e pavimentos (provisório) -------------------------------------------------


def create_wall_type(doc: Document, name: str, layers: list[dict], predefined_type="SOLIDWALL",
                     object_type: str | None = None) -> Transaction:
    data = {"name": name, "predefined_type": predefined_type, "object_type": object_type,
            "layers": layers}
    return Transaction("Criar tipo de parede", [Op("wall_type.create", guid.new(), data=data)])


def edit_wall_type(doc: Document, wall_type, **changes) -> Transaction:
    state = wall_types.read(doc.get(_gid(wall_type), "IfcWallType"))
    before = {k: state[k] for k in changes}
    return Transaction(
        "Editar tipo de parede",
        [Op("wall_type.edit", _gid(wall_type), before=before, after=dict(changes))],
    )


def create_storey(doc: Document, name: str, elevation: float) -> Transaction:
    data = {"name": name, "elevation": float(elevation)}
    return Transaction("Criar pavimento", [Op("storey.create", guid.new(), data=data)])


def edit_storey(doc: Document, storey, **changes) -> Transaction:
    storey = doc.get(_gid(storey), "IfcBuildingStorey")
    current = {"name": storey.Name, "elevation": float(storey.Elevation or 0.0)}
    before = {k: current[k] for k in changes}
    return Transaction(
        "Editar pavimento", [Op("storey.edit", storey.GlobalId, before=before, after=changes)]
    )
