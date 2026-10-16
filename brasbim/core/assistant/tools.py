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

from brasbim.core import geom2d, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import spaces
from brasbim.core.assistant import layout
from brasbim.core.delete import delete_elements
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.structure import roofs, slabs
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


def _type(doc: Document, ifc_class: str, name: str | None, what: str, where=None,
          default: str | None = None):
    """Tipo pelo nome (exato, sem caixa, ou pelo começo: "P1", "J2"); sem ``name``, o
    ``default`` ou o primeiro. ``where`` filtra (laje de piso ou de cobertura)."""
    found = sorted((t for t in doc.ifc.by_type(ifc_class) if where is None or where(t)),
                   key=lambda t: t.Name or "")
    if not name and default:
        name = default if any(t.Name == default for t in found) else None
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
    from brasbim.core.structure import roofs

    return [e for e in ifcopenshell.util.element.get_decomposition(storey)
            if e.is_a(ifc_class) and not roofs.is_part(e)]


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
    roof_list = []
    for roof in _contained(storey, "IfcRoof"):
        if not roofs.is_roof(roof):
            continue
        state = roofs.read_state(doc, roof)
        stype = doc.find(state["type"])
        q = ifcopenshell.util.element.get_pset(roof, "Qto_RoofBaseQuantities") or {}
        roof_list.append({"id": roof.GlobalId, "nome": state["name"],
                          "forma": state["shape"], "tipo": stype.Name if stype else None,
                          "inclinacao_pct": _r(state["slope"]),
                          "beiral": _r(state["overhang"]),
                          "altura_apoio": _r(state["base_height"]),
                          "lado": None if state["side"] is None else state["side"] + 1,
                          "contorno_apoio": [_pt(p) for p in state["outline"]],
                          "area_telhado": _r(q.get("NetArea", 0.0))})

    def names(cls, where=None):
        return [t.Name for t in sorted(doc.ifc.by_type(cls), key=lambda t: t.Name or "")
                if where is None or where(t)]

    return {
        "pavimento": {"id": storey.GlobalId, "nome": storey.Name,
                      "cota": _r(storey.Elevation or 0.0)},
        "pavimentos": [{"nome": s.Name, "cota": _r(s.Elevation or 0.0)}
                       for s in doc.storeys()],
        "tipos": {"parede": [f"{t.Name} ({_r(wall_types.thickness(t) * 100):g} cm)"
                             for t in sorted(doc.ifc.by_type("IfcWallType"),
                                             key=lambda t: t.Name or "")],
                  "porta": names("IfcDoorType"), "janela": names("IfcWindowType"),
                  "laje": names("IfcSlabType", _floor),
                  "cobertura": names("IfcSlabType", _roof_type)},
        "paredes": walls, "esquadrias": fillings, "ambientes": rooms, "lajes": slab_list,
        "coberturas": roof_list,
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


def _floor(t) -> bool:
    return t.PredefinedType != "ROOF"


def _roof_type(t) -> bool:
    return t.PredefinedType == "ROOF"


def create_slab(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    stype = _type(doc, "IfcSlabType", args.get("type"), "laje", _floor)
    outline = [_point(p, "contorno") for p in args["outline"]]
    tx = sc.create_slab(doc, stype, storey, outline)
    ctx.commit(tx)
    return {"id": tx.ops[-1].id, "tipo": stype.Name,
            "area": _r(abs(geom2d.polygon_area(outline)))}


def _roof_options(args: dict) -> dict:
    out = {}
    for key in ("shape", "slope", "overhang", "base_height", "side"):
        if args.get(key) is not None:
            out[key] = args[key]
    if "side" in out:
        out["side"] = int(out["side"]) - 1  # a IA conta os lados a partir de 1
    return out


def _roof_result(doc: Document, roof) -> dict:
    state = roofs.read_state(doc, roof)
    q = ifcopenshell.util.element.get_pset(roof, "Qto_RoofBaseQuantities") or {}
    own = ifcopenshell.util.element.get_pset(roof, roofs.PSET) or {}
    faces = roofs.faces(state)
    top = max(roofs.bottom_z(state, f, p) for f in faces for p in f.ring)
    low = min(roofs.bottom_z(state, f, p) for f in faces for p in f.ring)
    return {"id": roof.GlobalId, "forma": state["shape"], "aguas": len(state["parts"]),
            "contorno_apoio": [_pt(p) for p in state["outline"]],
            "cota_beiral": _r(low), "cota_cumeeira": _r(top),
            "area_telhado": _r(q.get("NetArea", 0.0)),
            "area_em_planta": _r(own.get("AreaProjecao", 0.0))}


def create_roof(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    storey = _storey(ctx, args)
    stype = _type(doc, "IfcSlabType", args.get("type"), "cobertura", _roof_type,
                  default="Telha cerâmica")
    options = _roof_options(args)
    if args.get("outline"):
        outline = [_point(p, "contorno") for p in args["outline"]]
        tx = sc.create_roof(doc, stype, storey, outline, **options)
    else:
        at = _point(args["at"], "at") if args.get("at") else None
        tx = sc.create_roof_over_walls(doc, stype, storey, at, **options)
    ctx.commit(tx)
    return _roof_result(doc, doc.get(tx.ops[-1].id))


def edit_roof(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    roof = doc.get(args["id"])
    if not roofs.is_roof(roof):
        raise OpError(f"{args['id']} não é uma cobertura")
    changes = _roof_options(args)
    if args.get("type"):
        changes["type"] = _type(doc, "IfcSlabType", args["type"], "cobertura",
                                _roof_type).GlobalId
    if args.get("outline"):
        changes["outline"] = [_point(p, "contorno") for p in args["outline"]]
    if not changes:
        raise OpError("nada a mudar")
    tx = sc.edit_element(doc, roof, **changes)
    if tx.ops:
        ctx.commit(tx)
    return _roof_result(doc, roof)


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


# --- edição (spec/ui 16 §4.3) -------------------------------------------------------------


def _existing(ctx: Context, ids) -> list[str]:
    ids = list(ids)
    if not ids:
        raise OpError("informe ao menos um id")
    missing = [g for g in ids if ctx.doc.find(g) is None]
    if missing:
        raise OpError(f"não existem: {', '.join(missing)}")
    return ids


def move_elements(ctx: Context, args: dict) -> dict:
    ids = _existing(ctx, args["ids"])
    vector = _point(args["vector"], "vector")
    if args.get("copy"):
        tx = transform.copy_elements(ctx.doc, ids, vector)
    else:
        tx = transform.move_elements(ctx.doc, ids, vector)
    ctx.commit(tx)
    new = [op.id for op in tx.ops if op.op.endswith(".create") and op.id not in ids]
    return {"movidos": [] if args.get("copy") else ids, "copias": new}


def rotate_elements(ctx: Context, args: dict) -> dict:
    ids = _existing(ctx, args["ids"])
    center = _point(args["center"], "center")
    ctx.commit(transform.rotate_elements(ctx.doc, ids, center,
                                         math.radians(float(args["angle"]))))
    return {"girados": ids}


def mirror_elements(ctx: Context, args: dict) -> dict:
    ids = _existing(ctx, args["ids"])
    a, b = _point(args["axis_start"], "axis_start"), _point(args["axis_end"], "axis_end")
    tx = transform.mirror_elements(ctx.doc, ids, a, b, keep=bool(args.get("copy")))
    ctx.commit(tx)
    return {"espelhados": ids,
            "copias": [op.id for op in tx.ops if op.op.endswith(".create") and op.id not in ids]}


def _side(info: dict, p) -> str:
    """Lado da parede onde fica o ponto: ``left`` (à esquerda de quem anda do início
    para o fim) ou ``right``."""
    local = info["frame"].to_local(p)
    return "left" if info["path"].offset(local) > sum(info["band"]) / 2 else "right"


def _faces_spaces(ctx: Context, storey, info: dict, shift) -> list:
    """Operações que levam junto os vértices dos ambientes que estão nas faces da
    parede (ambientes não seguem as paredes sozinhos)."""
    t = info["band"][1] - info["band"][0]
    mid = sum(info["band"]) / 2
    path, frame = info["path"], info["frame"]
    ops = []
    for space in [e for e in ctx.doc.ifc.by_type("IfcSpace") if spaces.storey_of(e) == storey]:
        state = spaces.read_state(space)
        if not state["outline"]:
            continue
        moved, changed = [], False
        for p in state["outline"]:
            local = frame.to_local(tuple(p))
            along = path.arc_length(path.param(local))
            on_face = (abs(path.offset(local) - mid) <= t / 2 + 0.005
                       and -t <= along <= path.length + t)
            moved.append(list(shift(tuple(p))) if on_face else list(p))
            changed |= on_face
        if changed:
            ops += ac.edit_element(ctx.doc, space, outline=moved).ops
    return ops


def move_wall(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    wall = doc.get(args["id"], "IfcWall")
    info = _wall_info(doc, wall)
    if info is None or not isinstance(info["path"], geom2d.LinePath):
        raise OpError("só a parede reta do BrasBim se desloca")
    distance = abs(float(args["distance"]))
    if distance < 1e-4:
        raise OpError("distância nula")
    toward = _point(args["toward"], "toward")
    sign = 1.0 if _side(info, toward) == "left" else -1.0
    storey = doc.get(info["state"]["storey"], "IfcBuildingStorey")
    n = info["frame"].vector_to_global((0.0, 1.0))
    shift = geom2d.translation((n[0] * distance * sign, n[1] * distance * sign))
    tx = cmd.offset_wall(doc, wall, distance * sign, carry=args.get("carry", True))
    if args.get("spaces", True):
        tx.ops += _faces_spaces(ctx, storey, info, shift)
    ctx.commit(tx)
    out = _wall_info(doc, wall)
    rooms = [{"id": op.id, "nome": spaces.read_state(doc.get(op.id))["name"],
              "area": _r(spaces.area(op.after["outline"]))}
             for op in tx.ops if op.op == "space.edit"]
    return {"parede": wall.GlobalId,
            "inicio": _pt(out["frame"].to_global(out["path"].point(0.0, 0.0))),
            "fim": _pt(out["frame"].to_global(out["path"].point(0.0, out["path"].t_end))),
            "paredes_alteradas": sorted({op.id for op in tx.ops if op.op == "wall.edit"}),
            "ambientes_ajustados": rooms}


def edit_wall(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    wall = doc.get(args["id"], "IfcWall")
    done = []
    changes = {}
    if args.get("type"):
        changes["type"] = _type(doc, "IfcWallType", args["type"], "parede").GlobalId
    if args.get("height") is not None:
        changes.update(top_mode="fixed", fixed_height=float(args["height"]))
    if changes:
        ctx.commit(cmd.edit_wall(doc, wall, **changes))
        done += sorted(changes)
    for end in ("start", "end"):
        if args.get(end) is not None:
            ctx.commit(cmd.move_wall_end(doc, wall, end, _point(args[end], end),
                                         carry=args.get("carry", True)))
            done.append(end)
    if not done:
        raise OpError("nada a mudar: informe type, height, start ou end")
    info = _wall_info(doc, wall)
    return {"parede": wall.GlobalId, "mudou": done, "espessura": _r(info["thickness"]),
            "comprimento": _r(info["path"].length)}


def edit_opening(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    element = doc.get(args["id"])
    if not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
        raise OpError(f"{args['id']} não é porta nem janela")
    opening = fc.opening_of(element)
    if opening is None:
        raise OpError("a esquadria não está numa abertura")
    o = openings.read_state(opening)
    k = fc.kind(element)
    new_type = _type(doc, k.type_class, args["type"], k.noun) if args.get("type") else None
    if new_type is not None:
        # tipo novo sem medidas dadas: vale o tamanho padrão dele (o centro fica)
        defaults = k.types.read(new_type)["defaults"]
        args.setdefault("width", defaults["width"])
        args.setdefault("height", defaults["height"])
    width = float(args["width"]) if args.get("width") is not None else o["width"]
    changes: dict = {}
    if args.get("width") is not None and abs(width - o["width"]) > 1e-9:
        changes["width"] = width
    if args.get("at") is not None:
        storey = doc.get(read_wall(doc, doc.get(o["wall"]))["storey"])
        wall, _info, along, _ = _wall_at(doc, storey, _point(args["at"], "at"),
                                         args.get("wall"))
        changes.update(wall=wall.GlobalId, distance=along - width / 2)
    elif "width" in changes:  # o centro fica onde estava
        changes["distance"] = o["distance"] + o["width"] / 2 - width / 2
    if args.get("height") is not None and abs(float(args["height"]) - o["height"]) > 1e-9:
        changes["height"] = float(args["height"])
    if args.get("sill") is not None:
        changes["base"] = float(args["sill"])
    if new_type is not None:
        changes["type"] = new_type.GlobalId
    if args.get("opens_toward") is not None:
        info = _wall_info(doc, doc.get(changes.get("wall", o["wall"])))
        changes["opens_to"] = _side(info, _point(args["opens_toward"], "opens_toward"))
    hinges = args.get("hinges")
    if hinges is not None and hinges not in ("left", "right"):
        raise OpError("hinges: use left ou right")
    tx = fc.edit_door(doc, element, hinges=hinges, **changes)
    if not tx.ops:
        return {"id": element.GlobalId, "mudou": []}
    ctx.commit(tx)
    return {"id": element.GlobalId, "mudou": sorted([*changes, *(["hinges"] if hinges else [])])}


def edit_space(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    space = doc.get(args["id"], "IfcSpace")
    changes = {}
    if args.get("name"):
        changes["name"] = str(args["name"])
    if args.get("number"):
        changes["number"] = str(args["number"])
    if args.get("refit"):
        from brasbim.core.structure import rooms

        state = spaces.read_state(space)
        storey = spaces.storey_of(space)
        point = args.get("at") or spaces.center(state["outline"])
        changes["outline"] = rooms.room_outline(doc, storey, tuple(point), "inner")
    if not changes:
        raise OpError("nada a mudar: informe name, number ou refit")
    tx = ac.edit_element(doc, space, **changes)
    if tx.ops:
        ctx.commit(tx)
    state = spaces.read_state(space)
    return {"id": space.GlobalId, "nome": state["name"], "numero": state["number"],
            "area": _r(spaces.area(state["outline"]))}


_TYPE_CLASS = {"IfcWall": ("IfcWallType", "parede"), "IfcDoor": ("IfcDoorType", "porta"),
               "IfcWindow": ("IfcWindowType", "janela"), "IfcSlab": ("IfcSlabType", "laje"),
               "IfcColumn": ("IfcColumnType", "pilar"), "IfcBeam": ("IfcBeamType", "viga"),
               "IfcRoof": ("IfcSlabType", "cobertura")}


def set_type(ctx: Context, args: dict) -> dict:
    doc = ctx.doc
    ids = _existing(ctx, args["ids"])
    classes = {next((c for c in _TYPE_CLASS if doc.get(g).is_a(c)), None) for g in ids}
    if None in classes or len(classes) != 1:
        raise OpError("troque o tipo de uma classe por vez (só paredes, só portas, …)")
    cls = classes.pop()
    type_class, noun = _TYPE_CLASS[cls]
    where = {"IfcSlab": _floor, "IfcRoof": _roof_type}.get(cls)
    new = _type(doc, type_class, args["type"], noun, where)
    if cls == "IfcWall":
        tx = cmd.edit_walls(doc, ids, type=new.GlobalId)
    elif cls in ("IfcDoor", "IfcWindow"):
        tx = fc.edit_doors(doc, ids, type=new.GlobalId)
    else:
        tx = sc.edit_elements(doc, ids, type=new.GlobalId)
    if tx.ops:
        ctx.commit(tx)
    return {"ids": ids, "tipo": new.Name}


def selection_note(doc: Document, storey, selection) -> str:
    """Contexto que vai junto do pedido (spec/ui 16 §2.1): pavimento ativo e o que está
    selecionado na tela, para pedidos como "aumenta essa parede"."""
    parts = []
    for gid in sorted(selection):
        e = doc.find(gid)
        if e is None:
            continue
        etype = ifcopenshell.util.element.get_type(e)
        tname = f", tipo {etype.Name}" if etype is not None else ""
        if e.is_a("IfcWall"):
            info = _wall_info(doc, e)
            if info is not None:
                a = info["frame"].to_global(info["path"].point(0.0, 0.0))
                b = info["frame"].to_global(info["path"].point(0.0, info["path"].t_end))
                parts.append(f"parede {gid}{tname}, de {_pt(a)} a {_pt(b)}")
                continue
        if e.is_a("IfcSpace"):
            parts.append(f"ambiente {gid} ({spaces.read_state(e)['name']})")
        elif roofs.is_roof(e):
            state = roofs.read_state(doc, e)
            stype = doc.find(state["type"])
            parts.append(f"cobertura {gid} ({roofs.SHAPE_NAMES[state['shape']]}, "
                         f"{_r(state['slope']):g} %, tipo {stype.Name if stype else '?'})")
        elif e.is_a("IfcDoor") or e.is_a("IfcWindow"):
            parts.append(f"{'janela' if e.is_a('IfcWindow') else 'porta'} {gid}{tname}")
        else:
            parts.append(f"{e.is_a()} {gid}{tname}")
    head = f'Pavimento ativo: "{storey.Name}".' if storey is not None else ""
    if not parts:
        return f"[BrasBim] {head} Nada selecionado na tela."
    return f"[BrasBim] {head} Selecionado na tela: " + "; ".join(parts) + "."


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
        "Descreve o pavimento: tipos disponíveis (parede, porta, janela, laje, "
        "cobertura), paredes (eixo, espessura), portas e janelas (centro, largura), "
        "ambientes (nome, área útil em m²), lajes e coberturas. Use no começo e para "
        "conferir o resultado.",
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
    _ROOF = {
        "shape": {"type": "string", "enum": list(roofs.SHAPES),
                  "description": "flat (plana), shed (uma água), gable (duas águas), "
                                 "hip (quatro águas); duas e quatro só em retângulo"},
        "slope": {"type": "number", "description": "inclinação em % (padrão 30)"},
        "overhang": {"type": "number", "description": "beiral em m (padrão 0,60)"},
        "base_height": {"type": "number", "description": "cota da face de baixo sobre o "
                        "contorno de apoio, a partir do pavimento (padrão: topo das paredes)"},
        "side": {"type": "integer", "description": "lado do contorno de apoio, contado a "
                 "partir de 1 no sentido anti-horário: na uma água, o mais baixo; na duas "
                 "águas, um paralelo à cumeeira (padrão: o lado maior)"},
        "type": {"type": "string", "description": "tipo de cobertura (telha)"}}
    reg.add(Tool(
        "create_roof", "Criando cobertura",
        "Cria a cobertura (telhado). Sem outline, apoia no contorno externo das paredes "
        "do pavimento (da edificação que contém 'at', ou da maior). outline: contorno de "
        "apoio [x, y], normalmente a face externa das paredes; o beiral sai dele.",
        _obj({**_ROOF, "outline": {"type": "array", "items": _XY, "minItems": 3},
              "at": _XY, "storey": _STOREY}),
        create_roof))
    reg.add(Tool(
        "edit_roof", "Editando cobertura",
        "Muda forma, inclinação, beiral, altura de apoio, lado, tipo ou contorno de uma "
        "cobertura existente (mantém as peças quando a quantidade de águas não muda).",
        _obj({"id": {"type": "string"}, **_ROOF,
              "outline": {"type": "array", "items": _XY, "minItems": 3}}, ["id"]),
        edit_roof))
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
    _IDS = {"type": "array", "items": {"type": "string"}, "description": "ids (GlobalId)"}
    reg.add(Tool(
        "move_wall", "Deslocando parede",
        "Desloca uma parede reta paralela a si mesma, 'distance' metros na direção do "
        "ponto 'toward' (ex.: para aumentar a sala 50 cm para o norte, desloque a parede "
        "norte dela 0,5 com toward ao norte). As paredes vizinhas esticam ou encurtam "
        "junto (carry, padrão sim) e os ambientes dos dois lados acompanham.",
        _obj({"id": {"type": "string"}, "distance": {"type": "number"}, "toward": _XY,
              "carry": {"type": "boolean"}}, ["id", "distance", "toward"]),
        move_wall))
    reg.add(Tool(
        "edit_wall", "Editando parede",
        "Muda tipo, altura (fixa) ou as pontas (start/end, pelo eixo) de uma parede. Ao "
        "mover uma ponta, as paredes ligadas a ela vão junto (carry).",
        _obj({"id": {"type": "string"}, "type": {"type": "string"},
              "height": {"type": "number"}, "start": _XY, "end": _XY,
              "carry": {"type": "boolean"}}, ["id"]),
        edit_wall))
    reg.add(Tool(
        "edit_opening", "Editando esquadria",
        "Muda uma porta ou janela: posição ('at' = novo centro, pode ser em outra "
        "parede), largura (o centro fica), altura, peitoril (sill), tipo (sem largura e "
        "altura, valem as do tipo novo), lado para onde abre (opens_toward = um ponto "
        "daquele lado) e mão (hinges).",
        _obj({"id": {"type": "string"}, "at": _XY, "width": {"type": "number"},
              "height": {"type": "number"}, "sill": {"type": "number"},
              "type": {"type": "string"}, "opens_toward": _XY,
              "hinges": {"type": "string", "enum": ["left", "right"]},
              "wall": {"type": "string"}}, ["id"]),
        edit_opening))
    reg.add(Tool(
        "edit_space", "Editando ambiente",
        "Renomeia ou renumera um ambiente; refit=true redesenha o contorno pelas paredes "
        "em volta (depois de mudanças feitas à mão).",
        _obj({"id": {"type": "string"}, "name": {"type": "string"},
              "number": {"type": "string"}, "refit": {"type": "boolean"}, "at": _XY},
             ["id"]),
        edit_space))
    reg.add(Tool(
        "set_type", "Trocando tipo",
        "Troca o tipo de vários elementos da mesma classe (só paredes, só portas, só "
        "janelas, só lajes...). Ex.: paredes internas para drywall.",
        _obj({"ids": _IDS, "type": {"type": "string"}}, ["ids", "type"]),
        set_type))
    reg.add(Tool(
        "move_elements", "Movendo",
        "Move (ou copia, copy=true) elementos pelo vetor [dx, dy]. Portas e janelas "
        "andam ao longo da parede delas.",
        _obj({"ids": _IDS, "vector": _XY, "copy": {"type": "boolean"}}, ["ids", "vector"]),
        move_elements))
    reg.add(Tool(
        "rotate_elements", "Girando",
        "Gira elementos 'angle' graus (anti-horário) em torno de 'center'.",
        _obj({"ids": _IDS, "center": _XY, "angle": {"type": "number"}},
             ["ids", "center", "angle"]),
        rotate_elements))
    reg.add(Tool(
        "mirror_elements", "Espelhando",
        "Espelha elementos pelo eixo de axis_start a axis_end; copy=true espelha uma "
        "cópia e mantém o original.",
        _obj({"ids": _IDS, "axis_start": _XY, "axis_end": _XY, "copy": {"type": "boolean"}},
             ["ids", "axis_start", "axis_end"]),
        mirror_elements))
    return reg
