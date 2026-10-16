# SPDX-License-Identifier: LGPL-3.0-or-later
"""Ferramentas do assistente (spec/ui 16 §4): o que uma IA pode fazer no modelo.

Cada ferramenta tem nome (identificador em inglês), descrição em pt‑BR para a IA,
esquema JSON dos argumentos e uma função ``fn(ctx, args)``. As que alteram o modelo
montam transações com os comandos de sempre e as aplicam por ``ctx.commit``, uma por
chamada: cada uma entra no histórico e aparece na tela na hora. Coordenadas em metros,
no sistema do pavimento; as paredes são dadas pelo **eixo**.

A função devolve um ``dict`` (vira texto JSON para a IA) ou uma lista de blocos de
conteúdo MCP (imagem). Recusa do núcleo (``OpError``) volta para a IA como erro, com o
texto, para ela corrigir.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import ifcopenshell.util.element

from brasbim.core import geom2d
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import spaces
from brasbim.core.assistant import layout
from brasbim.core.delete import delete_elements
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.structure import slabs
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings, params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state as read_wall


@dataclass
class Context:
    """Onde a ferramenta trabalha: documento, como aplicar e o pavimento ativo."""

    doc: Document
    commit: Callable[[Transaction], None]
    storey_id: str | None = None


@dataclass
class Tool:
    name: str
    title: str  # o que o painel mostra ("Criando paredes")
    description: str
    schema: dict
    fn: Callable[[Context, dict], dict | list]
    changes: bool = True  # altera o modelo

    def spec(self) -> dict:
        return {"name": self.name, "title": self.title, "description": self.description,
                "inputSchema": self.schema}


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def add(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def specs(self) -> list[dict]:
        return [t.spec() for t in self.tools.values()]

    def call(self, ctx: Context, name: str, args: dict | None) -> dict:
        """Resultado MCP (``content`` e ``isError``) da ferramenta ``name``."""
        tool = self.tools.get(name)
        if tool is None:
            return _error(f"ferramenta desconhecida: {name}")
        try:
            out = tool.fn(ctx, dict(args or {}))
        except OpError as e:
            return _error(str(e))
        except (KeyError, TypeError, ValueError, IndexError) as e:
            return _error(f"argumentos inválidos: {e}")
        if isinstance(out, list):
            return {"content": out, "isError": False}
        return {"content": [_text(out)], "isError": False}


def _text(data) -> dict:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return {"type": "text", "text": text}


def _error(text: str) -> dict:
    return {"content": [_text(text)], "isError": True}


# --- auxiliares ---------------------------------------------------------------------------


def _r(v: float) -> float:
    return round(float(v), 3)


def _pt(p) -> list[float]:
    return [_r(p[0]), _r(p[1])]


def _point(value, what: str) -> tuple[float, float]:
    try:
        x, y = value
        return float(x), float(y)
    except (TypeError, ValueError):
        raise OpError(f"{what}: informe [x, y] em metros") from None


def _storey(ctx: Context, args: dict):
    ref = args.get("storey")
    if ref:
        for s in ctx.doc.storeys():
            if ref in (s.GlobalId, s.Name):
                return s
        names = ", ".join(s.Name for s in ctx.doc.storeys())
        raise OpError(f"pavimento {ref!r} não existe (há: {names})")
    storey = ctx.doc.find(ctx.storey_id) if ctx.storey_id else None
    if storey is None:
        storeys = ctx.doc.storeys()
        if not storeys:
            raise OpError("o projeto não tem pavimentos")
        storey = storeys[0]
    return storey


def _type(doc: Document, ifc_class: str, name: str | None, what: str):
    """Tipo pelo nome (exato, sem caixa, ou pelo começo: "P1", "J2"); o primeiro se
    ``name`` vazio."""
    found = sorted(doc.ifc.by_type(ifc_class), key=lambda t: t.Name or "")
    if not found:
        raise OpError(f"o projeto não tem tipos de {what}")
    if not name:
        return found[0]
    low = name.strip().lower()
    for test in (lambda n: n == low, lambda n: n.startswith(low), lambda n: low in n):
        hits = [t for t in found if test((t.Name or "").lower())]
        if hits:
            return hits[0]
    names = "; ".join(t.Name for t in found)
    raise OpError(f"tipo de {what} {name!r} não existe (há: {names})")


def _contained(storey, ifc_class: str) -> list:
    return [e for e in ifcopenshell.util.element.get_decomposition(storey) if e.is_a(ifc_class)]


def _wall_info(doc: Document, wall) -> dict | None:
    """Caminho, faixa ocupada (no sistema local do caminho) e espessura."""
    try:
        state = read_wall(doc, wall)
        path = geom2d.path_from_dict(state["path"])
        wtype = doc.find(state["type"]) if state["type"] else None
        t = wall_types.thickness(wtype) if wtype is not None else 0.0
    except (OpError, ValueError, KeyError):
        return None
    sense, offset = params.layer_usage(state["ref_line"], state["flip_layers"], t)
    ymin, ymax = params.band(sense, offset, t)
    return {"state": state, "path": path, "frame": geom2d.frame(path), "thickness": t,
            "band": (ymin, ymax)}


def _wall_at(doc: Document, storey, p, gid: str | None = None):
    """Parede que passa pelo ponto ``p`` (ou a ``gid``) e onde: (parede, info, posição ao
    longo do caminho, y local)."""
    best = None
    walls = [doc.get(gid, "IfcWall")] if gid else _contained(storey, "IfcWall")
    for wall in walls:
        info = _wall_info(doc, wall)
        if info is None:
            continue
        local = info["frame"].to_local(p)
        path = info["path"]
        t, y = path.param(local), path.offset(local)
        if not (-1e-6 <= path.arc_length(t) <= path.length + 1e-6):
            continue
        ymin, ymax = info["band"]
        mid = (ymin + ymax) / 2
        gap = abs(y - mid)
        tol = (ymax - ymin) / 2 + 0.25
        if gap <= tol and (best is None or gap < best[0]):
            best = (gap, wall, info, path.arc_length(t), y)
    if best is None:
        raise OpError(f"nenhuma parede passa por {_pt(p)} (tolerância de 25 cm além da face)")
    return best[1:]


# --- leitura ------------------------------------------------------------------------------


def describe_model(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    walls, fillings = [], []
    for wall in _contained(storey, "IfcWall"):
        info = _wall_info(doc, wall)
        if info is None:
            walls.append({"id": wall.GlobalId, "nome": wall.Name, "outra_origem": True})
            continue
        state, path = info["state"], info["path"]
        wtype = doc.find(state["type"]) if state["type"] else None
        start = info["frame"].to_global(path.point(0.0, 0.0))
        end = info["frame"].to_global(path.point(0.0, path.t_end))
        walls.append({"id": wall.GlobalId, "tipo": wtype.Name if wtype else None,
                      "inicio": _pt(start), "fim": _pt(end), "linha_ref": state["ref_line"],
                      "espessura": _r(info["thickness"]), "comprimento": _r(path.length)})
        for opening in openings.of_wall(wall):
            o = openings.read_state(opening)
            for rel in opening.HasFillings:
                el = rel.RelatedBuildingElement
                etype = ifcopenshell.util.element.get_type(el)
                mid_t = o["distance"] + o["width"] / 2
                center = info["frame"].to_global(path.point(sum(info["band"]) / 2, mid_t))
                fillings.append({
                    "id": el.GlobalId,
                    "classe": "janela" if el.is_a("IfcWindow") else "porta",
                    "tipo": etype.Name if etype else None, "parede": wall.GlobalId,
                    "centro": _pt(center), "largura": _r(o["width"]),
                    "altura": _r(o["height"]), "peitoril": _r(o["sill"])})
    rooms = []
    for space in [e for e in doc.ifc.by_type("IfcSpace") if spaces.storey_of(e) == storey]:
        state = spaces.read_state(space)
        if state["outline"]:
            rooms.append({"id": space.GlobalId, "numero": state["number"],
                          "nome": state["name"], "area": _r(spaces.area(state["outline"])),
                          "contorno": [_pt(p) for p in state["outline"]]})
    slab_list = []
    for slab in _contained(storey, "IfcSlab"):
        try:
            state = slabs.read_state(doc, slab)
        except (OpError, ValueError, KeyError):
            continue
        stype = doc.find(state["type"]) if state.get("type") else None
        slab_list.append({"id": slab.GlobalId, "tipo": stype.Name if stype else None,
                          "contorno": [_pt(p) for p in state["outline"]]})
    def names(cls):
        return [t.Name for t in sorted(doc.ifc.by_type(cls), key=lambda t: t.Name or "")]

    return {
        "pavimento": {"id": storey.GlobalId, "nome": storey.Name,
                      "cota": _r(storey.Elevation or 0.0)},
        "pavimentos": [{"nome": s.Name, "cota": _r(s.Elevation or 0.0)}
                       for s in doc.storeys()],
        "tipos": {"parede": [f"{t.Name} ({_r(wall_types.thickness(t) * 100):g} cm)"
                             for t in sorted(doc.ifc.by_type("IfcWallType"),
                                             key=lambda t: t.Name or "")],
                  "porta": names("IfcDoorType"), "janela": names("IfcWindowType"),
                  "laje": names("IfcSlabType")},
        "paredes": walls, "esquadrias": fillings, "ambientes": rooms, "lajes": slab_list,
    }


# --- criação ------------------------------------------------------------------------------


def _wall_options(args: dict) -> dict:
    options = {"ref_line": args.get("ref_line") or "axis"}
    if options["ref_line"] not in params.REF_LINES:
        raise OpError(f"linha de referência inválida (use {', '.join(params.REF_LINES)})")
    if args.get("height") is not None:
        options.update(top_mode="fixed", fixed_height=float(args["height"]))
    return options


def _created(tx: Transaction, prefix: str) -> list[str]:
    return [op.id for op in tx.ops if op.op == f"{prefix}.create"]


def create_walls(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    wtype = _type(doc, "IfcWallType", args.get("type"), "parede")
    items = args["walls"]
    if not items:
        raise OpError("informe ao menos uma parede")
    segments = []
    for i, w in enumerate(items):
        a, b = _point(w["start"], f"parede {i + 1}"), _point(w["end"], f"parede {i + 1}")
        if math.dist(a, b) < 0.05:
            raise OpError(f"parede {i + 1}: comprimento menor que 5 cm")
        segments.append((a, b))
    tx = cmd.create_walls(doc, wtype, storey, segments, **_wall_options(args))
    ctx.commit(tx)
    return {"paredes": _created(tx, "wall"), "tipo": wtype.Name,
            "juncoes": len(_created(tx, "path_connection"))}


def layout_rooms(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    rooms = layout.rooms_from(args["rooms"])
    open_between = [tuple(p) for p in args.get("open_between") or []]
    names = {r.name for r in rooms}
    for pair in open_between:
        if len(pair) != 2 or not set(pair) <= names:
            raise OpError(f"open_between: par {list(pair)} não confere com os nomes")
    ext = _type(doc, "IfcWallType", args.get("exterior_type"), "parede")
    inner = _type(doc, "IfcWallType", args.get("interior_type") or args.get("exterior_type"),
                  "parede")
    segs = layout.segments(rooms, open_between)
    if ext == inner:
        segs = layout.merge_kinds(segs)
    options = _wall_options({**args, "ref_line": "axis"})
    ops, made = [], []
    for kind, wtype in (("exterior", ext), ("interior", inner)):
        group = [(s.start, s.end) for s in segs if s.kind == kind]
        if group:
            # cada grupo vê os anteriores já criados para achar as junções
            tx = cmd.create_walls(doc, wtype, storey, group, **options)
            ctx.commit(tx)
            ops += tx.ops
            made += [{"id": gid, "tipo": wtype.Name, "inicio": _pt(s.start),
                      "fim": _pt(s.end), "lado": "externa" if kind == "exterior" else "interna"}
                     for gid, s in zip(_created(tx, "wall"),
                                       [s for s in segs if s.kind == kind], strict=True)]
    half = {"exterior": wall_types.thickness(ext) / 2, "interior": wall_types.thickness(inner) / 2}
    room_out = []
    if args.get("spaces", True):
        for r in rooms:
            outline = layout.inner_outline(r, segs, half)
            tx = ac.create_space(doc, storey, outline, name=r.name)
            ctx.commit(tx)
            room_out.append({"id": tx.ops[0].id, "nome": r.name,
                             "area_util": _r(spaces.area(outline))})
    outer = layout.outer_outline(rooms, half["exterior"])
    return {"paredes": made, "ambientes": room_out,
            "area_construida": _r(geom2d.polygon_area(outer)) if outer else None,
            "contorno_externo": outer}


def _filling(ctx: Context, args: dict, ifc_class: str, what: str) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    etype = _type(doc, ifc_class, args.get("type"), what)
    center = _point(args["at"], "at")
    wall, info, along, _ = _wall_at(doc, storey, center, args.get("wall"))
    k = fc.kind(etype)
    defaults = k.types.read(etype)["defaults"]
    width = float(args.get("width") or defaults["width"])
    distance = along - width / 2
    options = {}
    if args.get("opens_toward") is not None and ifc_class == "IfcDoorType":
        local = info["frame"].to_local(_point(args["opens_toward"], "opens_toward"))
        mid = sum(info["band"]) / 2
        options["opens_to"] = "left" if info["path"].offset(local) > mid else "right"
    hinges = args.get("hinges")
    if hinges is not None and hinges not in ("left", "right"):
        raise OpError("hinges: use left ou right")
    base = args.get("sill") if ifc_class == "IfcWindowType" else None
    tx = fc.create_door(doc, etype, wall, distance, width=width, height=args.get("height"),
                        base=base, hinges=hinges, **options)
    ctx.commit(tx)
    gid = next(op.id for op in tx.ops if op.op == f"{k.prefix}.create")
    return {"id": gid, "tipo": etype.Name, "parede": wall.GlobalId,
            "distancia_do_inicio": _r(distance), "largura": _r(width)}


def insert_door(ctx: Context, args: dict) -> dict:
    return _filling(ctx, args, "IfcDoorType", "porta")


def insert_window(ctx: Context, args: dict) -> dict:
    return _filling(ctx, args, "IfcWindowType", "janela")


def create_slab(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    stype = _type(doc, "IfcSlabType", args.get("type"), "laje")
    outline = [_point(p, "contorno") for p in args["outline"]]
    tx = sc.create_slab(doc, stype, storey, outline)
    ctx.commit(tx)
    return {"id": tx.ops[-1].id, "tipo": stype.Name,
            "area": _r(abs(geom2d.polygon_area(outline)))}


def create_space(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    name = args.get("name") or spaces.DEFAULT_NAME
    if args.get("outline"):
        tx = ac.create_space(doc, storey, [_point(p, "contorno") for p in args["outline"]],
                             name=name)
    else:
        tx = ac.create_space_in_room(doc, storey, _point(args["at"], "at"), name=name)
    ctx.commit(tx)
    state = tx.ops[0].data
    return {"id": tx.ops[0].id, "nome": name, "area": _r(spaces.area(state["outline"]))}


def delete(ctx: Context, args: dict) -> dict:
    ids = list(args["ids"])
    missing = [g for g in ids if ctx.doc.find(g) is None]
    if missing:
        raise OpError(f"não existem: {', '.join(missing)}")
    tx, cascade = delete_elements(ctx.doc, ids)
    if not tx.ops:
        raise OpError("nada a excluir com esses ids")
    ctx.commit(tx)
    return {"excluidos": ids, "portas_junto": cascade["IfcDoor"],
            "janelas_junto": cascade["IfcWindow"]}


# --- registro -----------------------------------------------------------------------------

_XY = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
       "description": "[x, y] em metros, no sistema do pavimento"}
_STOREY = {"type": "string", "description": "nome do pavimento (padrão: o ativo na tela)"}


def _obj(props: dict, required=()) -> dict:
    return {"type": "object", "properties": props, "required": list(required)}


def default_registry() -> Registry:
    reg = Registry()
    reg.add(Tool(
        "describe_model", "Lendo o modelo",
        "Descreve o pavimento: tipos disponíveis (parede, porta, janela, laje), paredes "
        "(eixo, espessura), portas e janelas (centro, largura), ambientes (nome, área útil "
        "em m²) e lajes. Use no começo e para conferir o resultado.",
        _obj({"storey": _STOREY}), describe_model, changes=False))
    reg.add(Tool(
        "layout_rooms", "Desenhando os ambientes",
        "Planta por ambientes: cada cômodo é um retângulo medido pelo EIXO das paredes "
        "(x, y = canto inferior esquerdo; width no eixo x, depth no eixo y). Cria as "
        "paredes externas e internas (bordas compartilhadas viram uma parede só, sem "
        "duplicar) e os ambientes (IfcSpace) com o nome. Os retângulos não podem se "
        "sobrepor; encoste os cômodos vizinhos (mesma coordenada na borda comum). "
        "open_between lista pares de cômodos integrados, sem parede entre eles. "
        "Devolve a área útil de cada ambiente e o contorno externo (para o piso).",
        _obj({
            "rooms": {"type": "array", "items": _obj({
                "name": {"type": "string"}, "x": {"type": "number"},
                "y": {"type": "number"}, "width": {"type": "number"},
                "depth": {"type": "number"}}, ["name", "x", "y", "width", "depth"])},
            "open_between": {"type": "array", "items": {
                "type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}},
            "exterior_type": {"type": "string", "description": "tipo de parede externa"},
            "interior_type": {"type": "string", "description": "tipo de parede interna"},
            "height": {"type": "number", "description": "altura fixa das paredes (m); "
                       "sem ela, vão até o pavimento de cima"},
            "spaces": {"type": "boolean", "description": "criar os ambientes (padrão sim)"},
            "storey": _STOREY}, ["rooms"]),
        layout_rooms))
    reg.add(Tool(
        "create_walls", "Criando paredes",
        "Cria paredes retas de start a end (pelo eixo, a menos que ref_line diga outra "
        "coisa). Junções em L, T e X são feitas sozinhas quando as pontas se encontram.",
        _obj({"walls": {"type": "array", "items": _obj({"start": _XY, "end": _XY},
                                                        ["start", "end"])},
              "type": {"type": "string", "description": "nome do tipo de parede"},
              "ref_line": {"type": "string", "enum": list(params.REF_LINES)},
              "height": {"type": "number"}, "storey": _STOREY}, ["walls"]),
        create_walls))
    reg.add(Tool(
        "insert_door", "Inserindo porta",
        "Insere uma porta na parede que passa por 'at' (o centro da porta). type: nome ou "
        "começo do nome do tipo (ex.: 'P1'). opens_toward: um ponto do lado para onde a "
        "folha abre (ex.: o centro do cômodo). hinges: left ou right.",
        _obj({"at": _XY, "type": {"type": "string"}, "width": {"type": "number"},
              "height": {"type": "number"}, "opens_toward": _XY,
              "hinges": {"type": "string", "enum": ["left", "right"]},
              "wall": {"type": "string", "description": "id da parede, se ambíguo"},
              "storey": _STOREY}, ["at"]),
        insert_door))
    reg.add(Tool(
        "insert_window", "Inserindo janela",
        "Insere uma janela na parede que passa por 'at' (o centro da janela). type: nome "
        "ou código (ex.: 'J1'); sill: peitoril em metros.",
        _obj({"at": _XY, "type": {"type": "string"}, "width": {"type": "number"},
              "height": {"type": "number"}, "sill": {"type": "number"},
              "wall": {"type": "string"}, "storey": _STOREY}, ["at"]),
        insert_window))
    reg.add(Tool(
        "create_slab", "Criando laje",
        "Cria uma laje (piso) pelo contorno, lista de pontos [x, y].",
        _obj({"outline": {"type": "array", "items": _XY, "minItems": 3},
              "type": {"type": "string"}, "storey": _STOREY}, ["outline"]),
        create_slab))
    reg.add(Tool(
        "create_space", "Criando ambiente",
        "Cria um ambiente (IfcSpace) com nome: pelo cômodo fechado por paredes que contém "
        "'at', ou por um contorno dado.",
        _obj({"name": {"type": "string"}, "at": _XY,
              "outline": {"type": "array", "items": _XY}, "storey": _STOREY}, ["name"]),
        create_space))
    reg.add(Tool(
        "delete_elements", "Excluindo",
        "Exclui elementos pelos ids (paredes levam junto as portas e janelas delas).",
        _obj({"ids": {"type": "array", "items": {"type": "string"}}}, ["ids"]),
        delete))
    return reg
