# SPDX-License-Identifier: LGPL-3.0-or-later
"""Divisão das paredes em regiões por camada, com a prioridade nas junções
(``spec/ui/06-planta-por-camadas.md`` §2.3, ``parede.md`` §6.2). Sem Qt e sem IFC novo:
só desenho (planta por camadas e cor por camada no 3D).

Regra (decisão do projeto, aprovada em 2026-10-14):

- **Base** de cada camada: a faixa da camada (prolongada pela tangente nas pontas) ∩ as
  peças da própria parede.
- **Extensão** nas pontas com junção (ATSTART/ATEND): a faixa ∩ as peças da vizinha,
  cortada antes da primeira camada da vizinha com prioridade maior ou igual (a de menor
  projeção ao longo da tangente de saída, medida só dentro da faixa).
- Atribuição por prioridade decrescente; desempate: parede contínua (``RelatingElement``
  em ``ATPATH``), camada mais espessa, GlobalId, índice. Cada camada fica com
  (base ∪ extensão) − o que já foi atribuído. Prioridade vazia conta como 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from brasbim.core import clip, geom2d
from brasbim.core.clip import Rings
from brasbim.core.document import Document, OpError
from brasbim.core.walls import connections, joins, params, rebuild
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state as read_wall

_MIN_AREA = 1e-10  # m²: abaixo disto a região é resto numérico


@dataclass(frozen=True)
class Layer:
    """Camada de uma parede: faixa ``ymin..ymax`` no sistema local do caminho."""

    index: int
    material: str | None
    priority: int
    ymin: float
    ymax: float

    @property
    def thickness(self) -> float:
        return self.ymax - self.ymin


@dataclass
class LayerRegion:
    owner: str
    index: int
    material: str | None
    priority: int
    rings: Rings


_PART_PRIORITY = {"core": 50, "finish": 10}


def _profile_layers(doc: Document, state: dict) -> list[Layer] | None:
    """Parede de perfil (spec/ui 41 §4): as "camadas" são o corte do perfil no plano de
    corte da planta, um trecho por parte cruzada. ``None`` se o plano não corta a parede."""
    from shapely.geometry import LineString, Polygon

    from brasbim.core import profile_defs, storeys

    h = rebuild.height(doc, state)
    parts = rebuild.profile_parts(doc, state, h)
    z = storeys.cut_height(doc.get(state["storey"], "IfcBuildingStorey")) - state["base_offset"]
    x0, y0, x1, y1 = profile_defs.bounds(parts)
    if not y0 < z < y1:
        return None
    line = LineString([(x0 - 1.0, z), (x1 + 1.0, z)])
    out = []
    for part in parts:
        found = Polygon(part["outline"], part.get("holes") or []).intersection(line)
        pieces = getattr(found, "geoms", [found])
        for piece in pieces:
            if piece.is_empty or piece.length < 1e-9:
                continue
            xs = [c[0] for c in piece.coords]
            out.append(Layer(len(out), part["material"], _PART_PRIORITY[part["role"]],
                             min(xs), max(xs)))
    return out or None


def wall_layers(doc: Document, state: dict) -> list[Layer] | None:
    """Camadas da parede na ordem do conjunto, ou ``None`` sem ``IfcMaterialLayerSet``."""
    try:
        wall_type = doc.get(state["type"], "IfcWallType")
        if wall_types.profile_of(wall_type) is not None:
            return _profile_layers(doc, state)
        lset = wall_types.layer_set(wall_type)
    except OpError:
        return None
    items = list(lset.MaterialLayers or [])
    if not items:
        return None
    total = sum(float(i.LayerThickness) for i in items)
    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], total)
    k = rebuild.widening(state)
    out, y = [], 0.0
    for n, item in enumerate(items):
        t = float(item.LayerThickness)
        if sense == "POSITIVE":
            a, b = offset + y, offset + y + t
        else:
            a, b = offset - y - t, offset - y
        out.append(Layer(n, item.Material.Name if item.Material else None,
                         int(item.Priority or 0), a * k, b * k))
        y += t
    return out


def _end_rect(band: joins.Band, end: str, ya: float, yb: float, reach: float,
              back: float = 0.0) -> Rings:
    """Retângulo que prolonga a faixa ``ya..yb`` além da ponta, pela tangente (e ``back``
    para trás dela, para cobrir o trecho recortado pela junção)."""
    path, f = band.path, band.frame
    t = 0.0 if end == "ATSTART" else path.t_end
    a, b = f.to_global(path.point(ya, t)), f.to_global(path.point(yb, t))
    d = band.away(end)

    def at(p, s):
        return (p[0] - d[0] * s, p[1] - d[1] * s)

    return [[at(a, -back), at(b, -back), at(b, reach), at(a, reach)]]


def _strip(band: joins.Band, ya: float, yb: float, reach: float) -> Rings:
    body = [[band.frame.to_global(p) for p in geom2d.polygon(
        geom2d.band_profile(band.path, ya, yb))]]
    return clip.union(body, *(_end_rect(band, e, ya, yb, reach) for e in joins.ENDS))


def _continuous(wall) -> bool:
    return any(r.RelatingElement == wall and r.RelatingConnectionType == "ATPATH"
               for r in connections.of_wall(wall))


@dataclass
class _Wall:
    entity: object
    band: joins.Band
    layers: list[Layer]
    pieces: Rings
    bases: list[Rings]
    reach: float


def regions(doc: Document, walls: list, pieces: dict[str, Rings]) -> list[LayerRegion]:
    """Regiões por camada das paredes dadas, em coordenadas do pavimento.

    ``pieces``: área desenhada de cada parede (corpo com junções e vãos). Paredes sem
    camadas utilizáveis ficam de fora (quem desenha usa a mancha do tipo).
    """
    info: dict[str, _Wall] = {}
    for wall in walls:
        own = pieces.get(wall.GlobalId)
        if not own:
            continue
        try:
            state = read_wall(doc, wall)
            band = rebuild.band(doc, state)
        except (OpError, ValueError):
            continue
        layers = wall_layers(doc, state)
        if layers is None:
            continue
        info[wall.GlobalId] = _Wall(wall, band, layers, own, [], 0.0)
    if not info:
        return []
    widest = max(w.band.thickness for w in info.values())
    for w in info.values():
        w.reach = 4 * (w.band.thickness + widest) + 0.05
        w.bases = [clip.intersection(_strip(w.band, ly.ymin, ly.ymax, w.reach), w.pieces)
                   for ly in w.layers]

    candidates = []
    for gid, w in info.items():
        claims = {ly.index: list(w.bases[ly.index]) for ly in w.layers}
        for rel in connections.of_wall(w.entity):
            mine, other = ((rel.RelatingConnectionType, rel.RelatedElement)
                           if rel.RelatingElement == w.entity
                           else (rel.RelatedConnectionType, rel.RelatingElement))
            if mine not in joins.ENDS or other.GlobalId not in info:
                continue
            o = info[other.GlobalId]
            node = w.band.node(mine)
            away = w.band.away(mine)
            out = (-away[0], -away[1])
            for ly in w.layers:
                rect = _end_rect(w.band, mine, ly.ymin, ly.ymax, w.reach, w.reach)
                limit = min((clip.project_min(clip.intersection(rect, o.bases[j.index]),
                                              node, out)
                             for j in o.layers if j.priority >= ly.priority), default=None)
                ext = clip.intersection(rect, o.pieces)
                if limit is not None and limit < math.inf:
                    ext = clip.intersection(ext, [clip.halfplane(node, out, limit)])
                claims[ly.index] += ext
        cont = _continuous(w.entity)
        for ly in w.layers:
            key = (-ly.priority, not cont, -ly.thickness, gid, ly.index)
            candidates.append((key, gid, ly, claims[ly.index]))

    taken: Rings = []
    out_regions = []
    for _, gid, ly, claim in sorted(candidates, key=lambda c: c[0]):
        mine = clip.difference(clip.union(claim), taken)
        if clip.area(mine) > _MIN_AREA:
            out_regions.append(LayerRegion(gid, ly.index, ly.material, ly.priority, mine))
            taken = clip.union(taken, mine)
    return out_regions


def by_material(found: list[LayerRegion]) -> dict[str | None, Rings]:
    """União das regiões de cada material (faixas do mesmo material sem divisa)."""
    groups: dict[str | None, Rings] = {}
    for r in found:
        groups.setdefault(r.material, []).extend(r.rings)
    return {m: clip.union(rings) for m, rings in groups.items()}
