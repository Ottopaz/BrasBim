# SPDX-License-Identifier: LGPL-3.0-or-later
"""Quadro de áreas do projeto legal (``spec/ui/31-projeto-legal.md`` §5), sem Qt.

- **Classificação de área** de cada ambiente: computável, não computável (com o motivo),
  descoberta, permeável ou fora do total. Guardada no estado do ambiente (``area_class``,
  ``area_reason``, Pset ``BrasBim_QuadroDeAreas``); sem ela vale a regra do perfil
  municipal pelo nome do ambiente (``classify``).
- **Dados do lote** no ``IfcSite`` (Pset ``BrasBim_Lote``, JSON): área de escritura e os
  limites do zoneamento (TO e CA máximos, taxa de permeabilidade mínima), em fração.
  Operação ``lot.edit`` (before/after: campos alterados).
- ``compute`` monta as linhas (por pavimento e situação, totais, terreno, projeção,
  índices), cada uma com os ambientes e a **memória de cálculo**.

Área construída de um pavimento = união da face externa das paredes com os ambientes
cobertos (computáveis e não computáveis). Ela é repartida por situação: primeiro pelos
ambientes, depois pelas paredes; o que sobra (cômodo sem ambiente) fica com a situação
predominante das paredes. "A demolir" e "temporário" aparecem, mas não somam.
"""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from dataclasses import dataclass, field

import ifcopenshell.util.element

from brasbim.core import clip, intervention, props
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register

CLASSES = (("COMPUTAVEL", "Computável"), ("NAO_COMPUTAVEL", "Não computável"),
           ("DESCOBERTA", "Descoberta"), ("PERMEAVEL", "Permeável"),
           ("FORA_DO_TOTAL", "Fora do total"))
CLASS_LABEL = dict(CLASSES)
DEFAULT_CLASS = "COMPUTAVEL"
COVERED = ("COMPUTAVEL", "NAO_COMPUTAVEL")  # entram na área construída e na projeção
NOT_SUMMED = ("A_DEMOLIR", "TEMPORARIO")  # aparecem no quadro, fora do total
INDICES = {"TO": "Taxa de ocupação (TO)", "CA": "Coeficiente de aproveitamento (CA)",
           "TP": "Taxa de permeabilidade (TP)"}

LOT_PSET = "BrasBim_Lote"
LOT_KEYS = ("deed_area", "to_max", "ca_max", "tp_min")
_TINY = 1e-6  # m²


def check_class(code: str) -> str:
    if code not in CLASS_LABEL:
        raise OpError(f"classificação de área inválida: {code!r}")
    return code


# --- classificação --------------------------------------------------------------------------


def rules(profile: dict) -> list[dict]:
    """Regras do perfil, com a da piscina à parte quando o perfil pede (Jacareí)."""
    settings = profile.get("quadro_de_areas") or {}
    out = list(settings.get("regras") or [])
    if settings.get("piscina_a_parte"):
        out.insert(0, {"nomes": ["Piscina"], "classe": "FORA_DO_TOTAL",
                       "motivo": "piscina"})
    return out


def _matches(name: str, names) -> bool:
    name = (name or "").strip().casefold()
    return any(name == n.casefold() or name.startswith(n.casefold() + " ") for n in names)


def classify(profile: dict, state: dict, area: float | None = None
             ) -> tuple[str, str | None, str]:
    """(classe, motivo, origem) do ambiente; origem: ``ambiente`` (escolhida nele),
    ``perfil`` (regra pelo nome) ou ``padrão``."""
    if state.get("area_class"):
        return state["area_class"], state.get("area_reason") or None, "ambiente"
    for rule in rules(profile):
        limit = rule.get("ate_m2")
        if _matches(state.get("name"), rule.get("nomes") or ()) and (
                limit is None or area is None or area <= float(limit) + _TINY):
            return rule["classe"], rule.get("motivo"), "perfil"
    return DEFAULT_CLASS, None, "padrão"


def validate_rules(settings: dict) -> None:
    for rule in settings.get("regras") or []:
        if not isinstance(rule, dict) or not rule.get("nomes"):
            raise OpError(f"regra de área sem nomes: {rule!r}")
        check_class(rule.get("classe"))
        limit = rule.get("ate_m2")
        if limit is not None and not float(limit) > 0:
            raise OpError(f"limite de área inválido na regra {rule['nomes']}")
    for key in settings.get("indices") or []:
        if key not in INDICES:
            raise OpError(f"índice desconhecido no perfil: {key!r}")


# --- lote ------------------------------------------------------------------------------------


def _site(doc: Document):
    found = doc.ifc.by_type("IfcSite")
    if not found:
        raise OpError("o projeto não tem sítio")
    return found[0]


def read_lot(doc: Document) -> dict:
    found = doc.ifc.by_type("IfcSite")
    values = (ifcopenshell.util.element.get_pset(found[0], LOT_PSET, should_inherit=False)
              or {}) if found else {}
    data = json.loads(values["Parametros"]) if "Parametros" in values else {}
    return {key: data.get(key) for key in LOT_KEYS}


def _check_lot(lot: dict) -> None:
    for key in LOT_KEYS:
        value = lot.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or value <= 0:
            raise OpError(f"valor do lote inválido: {key}")
    for key in ("to_max", "tp_min"):
        if lot.get(key) is not None and lot[key] > 1:
            raise OpError("TO e taxa de permeabilidade vão de 0 a 100 %")


def _lot_edit(doc: Document, op: Op) -> set[str]:
    site = _site(doc)
    lot = read_lot(doc)
    check_before(op, lot)
    unknown = set(op.after or {}) - set(LOT_KEYS)
    if unknown:
        raise OpError(f"lot.edit: campos desconhecidos {sorted(unknown)}")
    lot.update(op.after or {})
    _check_lot(lot)
    kept = {k: v for k, v in lot.items() if v is not None}
    if kept:
        props.write_pset(doc, site, LOT_PSET, {"Parametros": doc.ifc.createIfcText(
            json.dumps(kept, sort_keys=True))})
    else:
        props.remove_pset(doc, site, LOT_PSET)
    return {site.GlobalId}


register("lot.edit", _lot_edit, invert_swap)


def edit_lot(doc: Document, **changes) -> Transaction:
    """Área de escritura e limites do zoneamento (fração: 0,6 = 60 %); ``None`` apaga."""
    unknown = set(changes) - set(LOT_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    lot = read_lot(doc)
    changes = {k: None if v is None else float(v) for k, v in changes.items()}
    _check_lot({**lot, **changes})
    changed = {k: v for k, v in changes.items() if v != lot[k]}
    if not changed:
        return Transaction("Dados do lote", [])
    return Transaction("Dados do lote", [Op("lot.edit", _site(doc).GlobalId,
                                            before={k: lot[k] for k in changed},
                                            after=copy.deepcopy(changed))])


def terrain_area(doc: Document) -> float | None:
    """Área do lote levantada: contorno dos terrenos do projeto (escada-terreno.md §4)."""
    from brasbim.core import terrain

    rings = []
    for element in terrain.all_terrains(doc):
        ring = terrain.outline(terrain.read_state(element))
        if len(ring) >= 3:
            rings.append([tuple(p) for p in ring])
    return clip.area(clip.union(rings)) if rings else None


# --- cálculo ---------------------------------------------------------------------------------


@dataclass
class Line:
    """Linha do quadro. ``kind``: ``head`` (pavimento), ``item``, ``subtotal``,
    ``total`` ou ``index``."""

    kind: str
    label: str
    area: float | None = None
    index: str | None = None
    limit: str | None = None
    ok: bool | None = None
    spaces: list[str] = field(default_factory=list)
    memo: str = ""


def num(value: float, places: int = 2) -> str:
    return f"{value:.{places}f}".replace(".", ",").replace("-0,00", "0,00")


@dataclass
class _Space:
    gid: str
    text: str  # "01 Sala"
    ring: list
    area: float
    situation: str
    cls: str
    reason: str | None
    storey: str


def _spaces(doc: Document, profile: dict) -> list[_Space]:
    from brasbim.core.annotations import spaces

    out = []
    for space in doc.ifc.by_type("IfcSpace"):
        state = spaces.read_state(space)
        if state["outline"] is None or state["storey"] is None:
            continue
        ring = [tuple(p) for p in state["outline"]]
        area = spaces.area(state["outline"])
        cls, reason, _ = classify(profile, state, area)
        text = " ".join(t for t in (state["number"], state["name"]) if t)
        out.append(_Space(space.GlobalId, text or space.GlobalId, ring, area,
                          intervention.situation_of(doc, space), cls, reason,
                          state["storey"]))
    return out


def _sum_memo(parts: list[tuple[str, float]], total: float | None = None) -> str:
    parts = [(t, a) for t, a in parts if a > _TINY]
    if not parts:
        return "nada"
    total = sum(a for _, a in parts) if total is None else total
    body = " + ".join(f"{t} {num(a)}" for t, a in parts)
    return body if len(parts) == 1 else f"{body} = {num(total)}"


@dataclass
class _Storey:
    name: str
    by_situation: dict[str, float]
    memo: dict[str, list[tuple[str, float]]]
    spaces: dict[str, list[str]]
    after: list  # região construída depois da obra (sem a demolir/temporário)
    nc: float
    nc_items: list[tuple[str, float, str, str]]  # texto, área, motivo, GlobalId


def _storey(doc: Document, storey, items: list[_Space]) -> _Storey | None:
    from brasbim.core.structure import rooms

    walls = rooms.wall_rings(doc, storey)
    covered_spaces = [s for s in items if s.cls in COVERED]
    covered = clip.union(rooms.building_rings(doc, storey, [r for r, _, _ in walls]),
                         [s.ring for s in covered_spaces])
    if clip.area(covered) < _TINY:
        return None
    assigned: list = []
    by_situation: dict[str, float] = defaultdict(float)
    memo: dict[str, list] = defaultdict(list)
    gids: dict[str, list] = defaultdict(list)
    regions: dict[str, list] = defaultdict(list)

    def take(code: str, rings: list, text: str, gid: str | None = None) -> None:
        nonlocal assigned
        piece = clip.intersection(covered, rings)
        if assigned:
            piece = clip.difference(piece, assigned)
        a = clip.area(piece)
        if a <= _TINY:
            return
        assigned = clip.union(assigned, piece)
        by_situation[code] += a
        memo[code].append((text, a))
        regions[code] += piece
        if gid:
            gids[code].append(gid)

    for s in covered_spaces:
        take(s.situation, [s.ring], s.text, s.gid)
    wall_groups: dict[str, list] = defaultdict(list)
    for ring, _, wall in walls:
        wall_groups[intervention.situation_of(doc, wall)].append(ring)
    for code in intervention.CODES:
        if wall_groups.get(code):
            take(code, wall_groups[code], "paredes")
    # Cômodo sem ambiente: a situação das paredes em volta dele (a de maior área junto).
    rest = clip.difference(covered, assigned) if assigned else covered
    for ring in [r for r in rest if clip.signed_area(r) > 0]:
        around = clip.offset([ring], 0.05)
        weights = {code: clip.area(clip.intersection(around, rings))
                   for code, rings in wall_groups.items()}
        main = max(weights, key=weights.get) if weights else intervention.DEFAULT
        take(main, [ring], "sem ambiente")
    rest = clip.difference(covered, assigned) if assigned else covered
    if clip.area(rest) > _TINY:
        take(intervention.DEFAULT, rest, "sem ambiente")
    after = clip.union(*(regions[c] for c in regions if c not in NOT_SUMMED))
    nc_spaces = [s for s in covered_spaces
                 if s.cls == "NAO_COMPUTAVEL" and s.situation not in NOT_SUMMED]
    nc_items = []
    for s in nc_spaces:
        a = clip.area(clip.intersection(after, [s.ring]))
        if a > _TINY:
            nc_items.append((s.text, a, s.reason or CLASS_LABEL[s.cls].lower(), s.gid))
    nc = clip.area(clip.intersection(after, clip.union([s.ring for s in nc_spaces]))) \
        if nc_spaces else 0.0
    return _Storey(storey.Name or "Pavimento", dict(by_situation), dict(memo), dict(gids),
                   after, nc, nc_items)


def _label(code: str) -> str:
    text = intervention.LABEL[code]
    return f"{text} (não soma)" if code in NOT_SUMMED else text


def compute(doc: Document) -> list[Line]:
    """Linhas do quadro de áreas, recalculadas do modelo."""
    from brasbim.core import municipal

    profile = municipal.current(doc)
    settings = profile.get("quadro_de_areas") or {}
    all_spaces = _spaces(doc, profile)
    lines: list[Line] = []
    built_total = 0.0
    built_parts: list[tuple[str, float]] = []
    situation_total: dict[str, float] = defaultdict(float)
    situation_spaces: dict[str, list] = defaultdict(list)
    projection: list = []
    nc_total = 0.0
    nc_items: list = []
    built_gids: list[str] = []
    for storey in doc.storeys():
        items = [s for s in all_spaces if s.storey == storey.GlobalId]
        data = _storey(doc, storey, items)
        if data is None:
            continue
        lines.append(Line("head", data.name))
        built = 0.0
        parts = []
        for code in intervention.CODES:
            a = data.by_situation.get(code)
            if not a:
                continue
            gids = data.spaces.get(code, [])
            lines.append(Line("item", _label(code), a, spaces=gids,
                              memo=_sum_memo(data.memo[code], a)))
            situation_total[code] += a
            situation_spaces[code] += gids
            if code not in NOT_SUMMED:
                built += a
                parts.append((intervention.LABEL[code].lower(), a))
                built_gids += gids
        lines.append(Line("subtotal", f"Área construída: {data.name}", built,
                          spaces=[g for c in data.spaces if c not in NOT_SUMMED
                                  for g in data.spaces[c]],
                          memo=_sum_memo(parts, built)))
        built_total += built
        built_parts.append((data.name, built))
        projection = clip.union(projection, data.after)
        nc_total += data.nc
        nc_items += [(f"{data.name}: {t}", a, r, g) for t, a, r, g in data.nc_items]

    if len(situation_total) > 1 or len(built_parts) > 1:
        for code in intervention.CODES:
            if code in situation_total:
                lines.append(Line("total", f"Total {_label(code).lower()}",
                                  situation_total[code], spaces=situation_spaces[code],
                                  memo="soma dos pavimentos"))
    lines.append(Line("total", "Área construída total", built_total, spaces=built_gids,
                      memo=_sum_memo(built_parts, built_total)))
    nc_memo = " + ".join(f"{t} {num(a)} ({r})" for t, a, r, _ in nc_items) or "nada"
    lines.append(Line("total", "Área não computável", nc_total,
                      spaces=[g for *_, g in nc_items], memo=nc_memo))
    computable = built_total - nc_total
    lines.append(Line("total", "Área computável", computable, spaces=built_gids,
                      memo=f"construída {num(built_total)} − não computável "
                           f"{num(nc_total)} = {num(computable)}"))

    def listed(cls: str):
        found = [s for s in all_spaces if s.cls == cls and s.situation not in NOT_SUMMED]
        return found, clip.area(clip.union([s.ring for s in found])) if found else 0.0

    uncovered, uncovered_area = listed("DESCOBERTA")
    if uncovered:
        lines.append(Line("item", "Área descoberta", uncovered_area,
                          spaces=[s.gid for s in uncovered],
                          memo=_sum_memo([(s.text, s.area) for s in uncovered],
                                         uncovered_area)))
    apart, _ = listed("FORA_DO_TOTAL")
    by_reason: dict[str, list] = defaultdict(list)
    for s in apart:
        by_reason[s.reason or "outros"].append(s)
    for reason, found in by_reason.items():
        a = clip.area(clip.union([s.ring for s in found]))
        lines.append(Line("item", f"Fora do total: {reason}", a,
                          spaces=[s.gid for s in found],
                          memo=_sum_memo([(s.text, s.area) for s in found], a)))

    lot = read_lot(doc)
    real = terrain_area(doc)
    deed = lot["deed_area"]
    if real is not None:
        lines.append(Line("item", "Área do terreno (levantamento)", real,
                          memo="contorno do terreno do projeto"))
    if deed is not None:
        lines.append(Line("item", "Área do terreno (escritura)", deed,
                          memo="valor digitado nos dados do lote"))
    base = deed if deed is not None else real
    base_name = "escritura" if deed is not None else "levantamento"
    projected = clip.area(projection)
    lines.append(Line("total", "Projeção da edificação", projected, spaces=built_gids,
                      memo="união em planta das áreas construídas de todos os pavimentos "
                           f"(sem a demolir) = {num(projected)}"))
    permeable, permeable_area = listed("PERMEAVEL")
    if base is not None:
        free = base - projected
        lines.append(Line("total", "Área livre", free,
                          memo=f"terreno ({base_name}) {num(base)} − projeção "
                               f"{num(projected)} = {num(free)}"))
    lines.append(Line("total", "Área permeável", permeable_area,
                      spaces=[s.gid for s in permeable],
                      memo=_sum_memo([(s.text, s.area) for s in permeable], permeable_area)))

    values = {"TO": (projected, "projeção", lot["to_max"], "máx."),
              "CA": (computable, "computável", lot["ca_max"], "máx."),
              "TP": (permeable_area, "permeável", lot["tp_min"], "mín.")}
    for key in settings.get("indices") or ("TO", "CA", "TP"):
        area, name, limit, word = values[key]
        percent = key != "CA"
        if base is None or base <= 0:
            lines.append(Line("index", INDICES[key],
                              memo="sem a área do terreno: desenhe o terreno ou digite a "
                                   "área de escritura nos dados do lote"))
            continue
        value = area / base

        def shown(v: float, percent: bool = percent) -> str:
            return f"{num(v * 100)} %" if percent else num(v)

        ok = None
        limit_text = None
        verdict = ""
        if limit is not None:
            ok = value <= limit + 1e-9 if word == "máx." else value >= limit - 1e-9
            limit_text = f"{word} {shown(limit)}"
            verdict = f"; {limit_text} → {'atende' if ok else 'não atende'}"
        lines.append(Line("index", INDICES[key], index=shown(value), limit=limit_text,
                          ok=ok, memo=f"{name} {num(area)} / terreno ({base_name}) "
                                      f"{num(base)} = {num(value, 4)}{verdict}"))
    return lines
