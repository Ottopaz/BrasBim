# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pranchas (spec/ui 15): formato, margens, carimbo, marcas de dobra e as vistas postas
nelas, sem Qt. O desenho no papel é feito pela interface (tela e PDF).

Operações: ``sheet.create`` / ``.delete`` / ``.edit`` e ``project.edit``.

Prancha = ``IfcAnnotation`` "Prancha" na edificação, com o estado em JSON no Pset
``BrasBim_Prancha``::

    {"number": "01", "title": "Planta baixa", "format": "A3",
     "orientation": "landscape", "master": None,
     "views": [{"kind": "plan", "storey": "<GlobalId>", "at": [150.0, 160.0]},
               {"kind": "view", "view": "<GlobalId>", "at": [300.0, 160.0]},
               {"kind": "saved", "saved": "<GlobalId>", "at": [150.0, 60.0]}]}

``saved``: vista salva (spec/ui 25), com a escala, as camadas e o recorte dela; a vista
3D leva também ``width`` (mm de papel).

Limite e moldura de cada desenho (spec/ui 29 §3–4): ``limit`` = [x0, y0, x1, y1] em m do
desenho (ausente = acompanha o desenho; não vale na vista 3D) e ``frame`` = {"show",
"dash", "pen"} (moldura impressa; ausente = sem moldura).

Coordenadas do papel em milímetros, a partir do canto inferior esquerdo da folha.
``master``: folha mestra (spec/ui 26) com o papel, as margens e o carimbo; sem ela, o
formato e a orientação com o carimbo padrão.
Dados do projeto para o carimbo: Pset ``BrasBim_Projeto`` no ``IfcProject``.
"""

from __future__ import annotations

import copy
import json
import math

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props, storeys
from brasbim.core.annotations.prims import DASHES, Stroke, Text
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.drawings import masters
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair
from brasbim.core.pens import MAX_PENS as MAX_PEN

PSET = "BrasBim_Prancha"
PROJECT_PSET = "BrasBim_Projeto"
OBJECT_TYPE = "Prancha"
# Formato → (largura, altura) na horizontal e margens (esquerda, demais), em mm (§2, CG).
FORMATS = masters.FORMATS  # formato → (tamanho na horizontal, margens), §2 (CG)
ORIENTATIONS = ("landscape", "portrait")
STATE_KEYS = ("number", "title", "format", "orientation", "views", "master")
PROJECT_KEYS = {"name": None, "address": "Endereco", "owner": "Proprietario",
                "responsible": "Responsavel", "registration": "Registro"}
TITLE_WIDTH = masters.TITLE_WIDTH
GAP = 10.0  # mm entre vistas postas sozinhas


def default_state() -> dict:
    return {"number": None, "title": "", "format": "A3", "orientation": "landscape",
            "views": [], "master": None}


def is_sheet(entity) -> bool:
    return (entity is not None and entity.is_a("IfcAnnotation")
            and entity.ObjectType == OBJECT_TYPE)


def all_sheets(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcAnnotation") if is_sheet(e)),
                  key=lambda e: (read_state(e)["number"] or "", e.GlobalId))


def read_state(sheet) -> dict:
    values = ifcopenshell.util.element.get_pset(sheet, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"prancha {sheet.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


def next_number(doc: Document) -> str:
    used = {read_state(s)["number"] for s in all_sheets(doc)}
    n = 1
    while f"{n:02d}" in used:
        n += 1
    return f"{n:02d}"


# --- papel -----------------------------------------------------------------------------


def paper(state: dict) -> tuple[float, float]:
    """Papel do formato padrão (sem folha mestra)."""
    return masters.paper_size({**state, "format": state["format"], "size": None})


def frame(state: dict) -> tuple[float, float, float, float]:
    """Quadro (x0, y0, x1, y1) dentro das margens padrão do formato."""
    return masters.frame_of(paper(state), masters.standard_margins(state["format"]))


def layout(doc: Document, state: dict) -> masters.Layout:
    """Papel, quadro e desenho fixo da prancha: os da folha mestra, ou o formato com o
    carimbo padrão (spec/ui 26 §3)."""
    master = doc.find(state["master"]) if state.get("master") else None
    if master is not None and masters.is_master(master):
        return masters.layout_of(masters.read_state(master))
    return masters.standard_layout(state["format"], state["orientation"])


def paper_of(doc: Document, state: dict) -> tuple[float, float]:
    return layout(doc, state).size


def fold_marks(state_or_size) -> list[Stroke]:
    """Traços na borda do papel para dobrar em A4 (190 mm a partir da direita; a primeira
    dobra horizontal a 297 mm de baixo), §2 (CG). Aceita o estado da prancha (formato
    padrão) ou o tamanho do papel."""
    w, h = paper(state_or_size) if isinstance(state_or_size, dict) else state_or_size
    out, length = [], 5.0
    x = w - 190.0
    while x > 25.0:
        out += [Stroke(((x, 0.0), (x, length)), False, 0.25),
                Stroke(((x, h), (x, h - length)), False, 0.25)]
        x -= 190.0
    if h > 297.0 + 1e-6:
        out += [Stroke(((0.0, 297.0), (length, 297.0)), False, 0.25),
                Stroke(((w, 297.0), (w - length, 297.0)), False, 0.25)]
    return out


def item_key(item: dict) -> str | None:
    """GlobalId do que o item mostra (pavimento, corte ou vista salva)."""
    return item.get("storey") or item.get("view") or item.get("saved")


def saved_state(doc: Document, item: dict) -> dict | None:
    """Estado da vista salva do item, ou ``None``."""
    from brasbim.core.drawings import saved_views

    entity = doc.find(item["saved"]) if item.get("kind") == "saved" else None
    return saved_views.read_state(entity) if entity is not None else None


def scale_of(doc: Document, item: dict) -> int | None:
    """Escala do item; ``None`` na vista 3D (perspectiva)."""
    if item["kind"] == "saved":
        state = saved_state(doc, item)
        if state is None:
            return storeys.DEFAULT_SCALE
        return None if state["kind"] == "3d" else state["scale"]
    if item["kind"] == "plan":
        storey = doc.find(item["storey"])
        return storeys.stored_scale(storey) if storey is not None else storeys.DEFAULT_SCALE
    from brasbim.core.drawings import views

    view = doc.find(item["view"])
    return views.read_state(view)["scale"] if view is not None else storeys.DEFAULT_SCALE


def field_values(doc: Document, sheet, date: str) -> dict:
    """Valores dos campos do carimbo (spec/ui 26 §2) para a prancha."""
    state = read_state(sheet)
    info = read_project(doc)
    sheets = all_sheets(doc)
    index = sheets.index(sheet) + 1 if sheet in sheets else 1
    scales = sorted({scale_of(doc, item) for item in state["views"]} - {None})
    return {"projeto": info["name"] or "", "endereco": info["address"] or "",
            "proprietario": info["owner"] or "", "responsavel": info["responsible"] or "",
            "registro": info["registration"] or "",
            "responsavel_tecnico": " · ".join(v for v in (info["responsible"],
                                                          info["registration"]) if v),
            "numero": state["number"] or "", "titulo": state["title"] or "",
            "escala": " / ".join(f"1:{s}" for s in scales) or "—", "data": date,
            "folha": f"{index:02d}", "total": f"{len(sheets):02d}"}


def title_items(doc: Document, sheet, date: str) -> tuple[list[Stroke], list[Text]]:
    """Quadro, desenho da folha mestra (ou carimbo padrão) com os campos preenchidos e
    marcas de dobra: linhas e textos em mm do papel."""
    paper_layout = layout(doc, read_state(sheet))
    values = field_values(doc, sheet, date)
    strokes, texts = [], []
    if paper_layout.frame_on:
        x0, y0, x1, y1 = paper_layout.frame
        strokes.append(Stroke(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), True,
                              masters.FRAME_WEIGHT))
    for item in paper_layout.items:
        if item["kind"] == "line":
            strokes.append(Stroke(tuple(tuple(p) for p in item["points"]), item["closed"],
                                  item["weight"]))
            continue
        text = masters.fill(item["text"], values)
        if text:
            texts.append(Text(tuple(item["at"]), text, item["height"], 0.0, item["align"],
                              "bottom", bool(item.get("bold"))))
    if paper_layout.fold_on:
        strokes += fold_marks(paper_layout.size)
    return strokes, texts


# --- vistas na prancha --------------------------------------------------------------------


def item_display(doc: Document, item: dict):
    """Contexto de desenho da vista da prancha: com ``combination`` (spec/ui 18 §6.2), os
    estados daquela combinação, sem mudar a janela; sem ela, a exibição atual. A vista
    salva leva as camadas e a escala dela (spec/ui 25 §5); a planta do pavimento, a escala
    gravada no pavimento (não a da janela)."""
    import contextlib

    from brasbim.core import display_layers

    if item["kind"] == "saved":
        from brasbim.core.drawings import saved_views

        state = saved_state(doc, item)
        return saved_views.drawing(doc, state) if state is not None \
            else contextlib.nullcontext()
    stack = contextlib.ExitStack()
    if item["kind"] == "plan":
        stack.enter_context(storeys.using_scale(item["storey"], None))
    comb = display_layers.combination(doc, item["combination"]) \
        if item.get("combination") else None
    if comb is not None:
        stack.enter_context(display_layers.using(doc, display_layers.display_of(
            comb["states"])))
    return stack


def view_bounds(doc: Document, item: dict):
    """Retângulo do desenho (m) da planta ou da vista, ou ``None``."""
    with item_display(doc, item):
        return _view_bounds(doc, item)


def _drawing_bounds(drawing):
    box = drawing.bounds()
    if box is None:
        return None
    pts = [t.at for t in drawing.texts]
    u0, v0, u1, v1 = box
    return (min([u0, *(p[0] for p in pts)]), min([v0, *(p[1] for p in pts)]),
            max([u1, *(p[0] for p in pts)]), max([v1, *(p[1] for p in pts)]))


def is_3d(doc: Document, item: dict) -> bool:
    saved = saved_state(doc, item) if item["kind"] == "saved" else None
    return saved is not None and saved["kind"] == "3d"


def _view_bounds(doc: Document, item: dict):
    from brasbim.core.drawings import section

    if item.get("limit") and not is_3d(doc, item):
        return tuple(item["limit"])  # limite recortado pela alça (spec/ui 29 §3)
    if item["kind"] == "saved":
        from brasbim.core.drawings import saved_views

        state = saved_state(doc, item)
        if state is None or state["kind"] == "3d":
            return None
        if state["kind"] == "plan":
            turn = math.radians(saved_views.options(state)["rotation"])
            if state.get("crop"):
                return tuple(state["crop"])  # girada: já nos eixos da vista
            drawn = saved_views.plan_of(doc, state)
            if drawn is None or not turn:
                return drawn.bounds() if drawn is not None else None
            from brasbim.core.snap import rotate

            # Girada (spec/ui 39 §3): retângulo nos eixos da vista.
            pts = [rotate(p, -turn) for s in drawn.shapes if s.role != "below"
                   for p in s.points]
            if not pts:
                return None
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            return min(xs), min(ys), max(xs), max(ys)
        view = doc.find(state["view"])
        return _drawing_bounds(section.draw(doc, view, state["scale"])) if view else None
    if item["kind"] == "plan":
        from brasbim.core import plan

        storey = doc.find(item["storey"])
        return plan.storey_plan(doc, storey).bounds() if storey is not None else None
    view = doc.find(item["view"])
    return _drawing_bounds(section.draw(doc, view)) if view is not None else None


def view_size(doc: Document, item: dict) -> tuple[float, float]:
    """Largura e altura (mm de papel) da vista na escala dela; a vista 3D, pela largura
    dada no item."""
    if item["kind"] == "saved":
        state = saved_state(doc, item)
        if state is not None and state["kind"] == "3d":
            from brasbim.core.drawings import saved_views

            return saved_views.size_3d(state, item.get("width"))
    box = view_bounds(doc, item)
    if box is None:
        return 0.0, 0.0
    k = 1000.0 / scale_of(doc, item)
    return (box[2] - box[0]) * k, (box[3] - box[1]) * k


def item_rect(doc: Document, item: dict) -> tuple[float, float, float, float]:
    """Limite do desenho no papel (mm): (x0, y0, x1, y1) em volta do centro ``at``."""
    w, h = view_size(doc, item)
    x, y = item["at"]
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


MIN_LIMIT_MM = 5.0  # menor lado do limite recortado
HANDLES = {"sw": (0, 0), "s": (0.5, 0), "se": (1, 0), "e": (1, 0.5), "ne": (1, 1),
           "n": (0.5, 1), "nw": (0, 1), "w": (0, 0.5)}  # alça → posição relativa


def handle_points(doc: Document, item: dict) -> dict[str, tuple[float, float]]:
    """Alças do limite (mm do papel); a vista 3D não tem recorte (§3)."""
    if is_3d(doc, item) or view_bounds(doc, item) is None:
        return {}
    x0, y0, x1, y1 = item_rect(doc, item)
    return {k: (x0 + u * (x1 - x0), y0 + v * (y1 - y0)) for k, (u, v) in HANDLES.items()}


def limit_from_handle(doc: Document, item: dict, handle: str, p) -> tuple[list, list]:
    """Novo ``limit`` (m do desenho) e novo centro ``at`` (mm) ao levar a alça ``handle``
    ao ponto ``p`` do papel; o lado oposto fica parado (§3)."""
    box = view_bounds(doc, item)
    if box is None or is_3d(doc, item):
        raise OpError("este desenho não tem limite para recortar")
    k = 1000.0 / scale_of(doc, item)  # mm de papel por m
    x0, y0, x1, y1 = item_rect(doc, item)
    u, v = HANDLES[handle]
    if u == 0:
        x0 = min(p[0], x1 - MIN_LIMIT_MM)
    elif u == 1:
        x1 = max(p[0], x0 + MIN_LIMIT_MM)
    if v == 0:
        y0 = min(p[1], y1 - MIN_LIMIT_MM)
    elif v == 1:
        y1 = max(p[1], y0 + MIN_LIMIT_MM)
    rx0, ry0, _, _ = item_rect(doc, item)
    limit = [round(box[0] + (x0 - rx0) / k, 4), round(box[1] + (y0 - ry0) / k, 4),
             round(box[0] + (x1 - rx0) / k, 4), round(box[1] + (y1 - ry0) / k, 4)]
    return limit, [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]


def free_spot(doc: Document, state: dict, size: tuple[float, float]) -> list[float]:
    """Centro da vista nova: à direita das que já estão, acima do desenho do carimbo que
    fica na metade de baixo do quadro."""
    paper_layout = layout(doc, state)
    x0, y0, x1, y1 = paper_layout.frame
    low = [it for it in paper_layout.items
           if (box := masters.items_bounds([it])) is not None and box[1] < (y0 + y1) / 2]
    box = masters.items_bounds(low)
    top = box[3] if box is not None else y0
    right = x0 + GAP
    for item in state["views"]:
        w, _ = view_size(doc, item)
        right = max(right, item["at"][0] + w / 2 + GAP)
    cx = min(right + size[0] / 2, x1 - size[0] / 2)
    cy = (max(top, y0) + y1) / 2
    return [round(cx, 3), round(cy, 3)]


# --- dados do projeto ----------------------------------------------------------------------


def read_project(doc: Document) -> dict:
    project = doc.project
    values = ifcopenshell.util.element.get_pset(project, PROJECT_PSET,
                                                should_inherit=False) or {}
    out = {"name": project.Name}
    for key, prop in PROJECT_KEYS.items():
        if prop:
            out[key] = values.get(prop)
    return out


def _project_edit(doc: Document, op: Op) -> set[str]:
    state = read_project(doc)
    check_before(op, state)
    state.update(op.after or {})
    project = doc.project
    project.Name = state["name"]
    values = {prop: doc.ifc.createIfcLabel(state[key]) for key, prop in PROJECT_KEYS.items()
              if prop and state.get(key)}
    if values:
        props.write_pset(doc, project, PROJECT_PSET, values)
    else:
        props.remove_pset(doc, project, PROJECT_PSET)
    return {project.GlobalId}


register("project.edit", _project_edit, invert_swap)


# --- operações da prancha -------------------------------------------------------------------


def _validate(state: dict) -> None:
    if state["format"] not in FORMATS:
        raise OpError(f"formato inválido: {state['format']!r}")
    if state["orientation"] not in ORIENTATIONS:
        raise OpError(f"orientação inválida: {state['orientation']!r}")
    for item in state["views"]:
        if item.get("kind") not in ("plan", "view", "saved"):
            raise OpError(f"vista de prancha inválida: {item!r}")
        limit = item.get("limit")
        if limit is not None and (len(limit) != 4 or not (limit[0] < limit[2]
                                                         and limit[1] < limit[3])):
            raise OpError(f"limite de desenho inválido: {limit!r}")
        frame_ = item.get("frame")
        if frame_ is not None:
            if set(frame_) != {"show", "dash", "pen"} or frame_["dash"] not in DASHES:
                raise OpError(f"moldura inválida: {frame_!r}")
            if not isinstance(frame_["pen"], int) or not 1 <= frame_["pen"] <= MAX_PEN:
                raise OpError(f"pena da moldura inválida: {frame_['pen']!r}")


def _write(doc: Document, sheet, state: dict) -> None:
    _validate(state)
    if state.get("master") and not masters.is_master(doc.find(state["master"])):
        raise OpError("a folha mestra não existe")
    building = doc.building
    sheet.ObjectType = OBJECT_TYPE
    sheet.Name = f"Prancha {state['number']}"
    sheet.Description = state["title"] or None
    if ifcopenshell.util.element.get_container(sheet) != building:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[sheet],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    if sheet.ObjectPlacement is None:
        sheet.ObjectPlacement = local_placement(doc.ifc, building.ObjectPlacement)
    props.write_pset(doc, sheet, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        state, sort_keys=True, ensure_ascii=False))})


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    sheet = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
    sheet.GlobalId = op.id
    sheet.PredefinedType = "USERDEFINED"
    try:
        _write(doc, sheet, {**default_state(), **copy.deepcopy(op.data)})
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=sheet)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    ifcopenshell.api.root.remove_product(doc.ifc, product=doc.get(op.id, "IfcAnnotation"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    sheet = doc.get(op.id, "IfcAnnotation")
    state = read_state(sheet)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"sheet.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    _write(doc, sheet, state)
    return {op.id}


register_inverse_pair("sheet.create", _create, "sheet.delete", _delete)
register("sheet.edit", _edit, invert_swap)


def refs_removed_ops(doc: Document, gid: str, cascade: bool = True) -> list[Op]:
    """``sheet.edit`` que tiram das pranchas a planta do pavimento, a vista ou a vista
    salva ``gid`` que vai ser excluída (§4). Com ``cascade``, as vistas salvas que dependem
    de ``gid`` saem das pranchas e são excluídas também (spec/ui 25 §4)."""
    from brasbim.core.drawings import saved_views

    dependents = saved_views.dependents(doc, gid) if cascade else []
    gone = {gid, *(v.GlobalId for v in dependents)}
    ops = []
    for sheet in all_sheets(doc):
        state = read_state(sheet)
        kept = [it for it in state["views"] if item_key(it) not in gone]
        if len(kept) != len(state["views"]):
            ops.append(Op("sheet.edit", sheet.GlobalId,
                          before={"views": copy.deepcopy(state["views"])},
                          after={"views": copy.deepcopy(kept)}))
    ops += [Op("saved_view.delete", v.GlobalId, data=saved_views.read_state(v))
            for v in dependents]
    return ops


# --- comandos ----------------------------------------------------------------------------


def create_sheet(doc: Document, title: str = "", fmt: str = "A3",
                 orientation: str = "landscape", master: str | None = None) -> Transaction:
    """Prancha nova com a folha mestra ``master`` (spec/ui 26) ou o formato padrão."""
    if master is not None and not masters.is_master(doc.find(master)):
        raise OpError("a folha mestra não existe")
    data = {**default_state(), "number": next_number(doc), "title": title, "format": fmt,
            "orientation": orientation, "master": master}
    _validate(data)
    return Transaction("Criar prancha", [Op("sheet.create", guid.new(), data=data)])


def edit_sheet(doc: Document, sheet, **changes) -> Transaction:
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    state = read_state(sheet)
    unknown = set(changes) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    _validate({**state, **changes})
    changes = {k: v for k, v in changes.items() if v != state[k]}
    if not changes:
        return Transaction("Editar prancha", [])
    return Transaction("Editar prancha", [Op(
        "sheet.edit", sheet.GlobalId, before={k: copy.deepcopy(state[k]) for k in changes},
        after=copy.deepcopy(changes))])


def add_to_sheet(doc: Document, sheet, item: dict, at=None) -> Transaction:
    """Põe a planta de um pavimento (``{"kind": "plan", "storey": gid}``), um corte/fachada
    (``{"kind": "view", "view": gid}``) ou uma vista salva (``{"kind": "saved", "saved":
    gid}``) na prancha, com o centro em ``at`` ou no primeiro lugar livre (§3)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    state = read_state(sheet)
    item = {k: v for k, v in item.items() if k != "at"}
    key = item_key(item)
    if key is None or doc.find(key) is None:
        raise OpError("a vista não existe mais")
    if any(item_key(it) == key for it in state["views"]):
        raise OpError("esta vista já está na prancha")
    spot = list(at) if at is not None else free_spot(doc, state, view_size(doc, item))
    tx = edit_sheet(doc, sheet, views=[*state["views"], {**item, "at": [float(spot[0]),
                                                                         float(spot[1])]}])
    tx.label = "Pôr na prancha"
    return tx


def move_on_sheet(doc: Document, sheet, index: int, at) -> Transaction:
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    views_[index]["at"] = [round(float(at[0]), 3), round(float(at[1]), 3)]
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Mover vista na prancha"
    return tx


def set_item_width(doc: Document, sheet, index: int, width: float) -> Transaction:
    """Largura no papel (mm) da vista 3D posta na prancha (spec/ui 25 §5)."""
    if width <= 0:
        raise OpError("a largura precisa ser positiva")
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    views_[index]["width"] = round(float(width), 3)
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Largura da vista na prancha"
    return tx


def remove_many_from_sheet(doc: Document, sheet, indices) -> Transaction:
    """Tira da prancha os desenhos ``indices`` numa transação (spec/ui 29 §2)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    chosen = set(indices)
    views_ = [it for i, it in enumerate(copy.deepcopy(read_state(sheet)["views"]))
              if i not in chosen]
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Tirar da prancha"
    return tx


def move_many_on_sheet(doc: Document, sheet, indices, delta) -> Transaction:
    """Leva os desenhos ``indices`` por ``delta`` (mm) numa transação (spec/ui 29 §2)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    for i in set(indices):
        x, y = views_[i]["at"]
        views_[i]["at"] = [round(x + delta[0], 3), round(y + delta[1], 3)]
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Mover na prancha"
    return tx


def set_item_limit(doc: Document, sheet, index: int, limit, at=None) -> Transaction:
    """Limite recortado do desenho (m do desenho) e, se dado, o centro novo; ``limit``
    ``None`` volta a acompanhar o desenho (spec/ui 29 §3)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    item = views_[index]
    if limit is None:
        cut = item.pop("limit", None)
        full = view_bounds(doc, item)
        if at is not None:
            item["at"] = [float(at[0]), float(at[1])]
        elif cut and full is not None:  # o desenho inteiro volta alinhado com o recorte
            k = 1000.0 / scale_of(doc, item)
            dx = ((full[0] + full[2]) - (cut[0] + cut[2])) / 2 * k
            dy = ((full[1] + full[3]) - (cut[1] + cut[3])) / 2 * k
            item["at"] = [round(item["at"][0] + dx, 3), round(item["at"][1] + dy, 3)]
    else:
        item["limit"] = [float(v) for v in limit]
        if at is not None:
            item["at"] = [float(at[0]), float(at[1])]
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Limite do desenho" if limit is not None else "Ajustar o limite ao desenho"
    return tx


def set_item_frame(doc: Document, sheet, indices, show: bool, dash: str = "solid",
                   pen: int = 3) -> Transaction:
    """Moldura impressa dos desenhos ``indices`` (spec/ui 29 §4)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    for i in set(indices):
        views_[i]["frame"] = {"show": bool(show), "dash": dash, "pen": int(pen)}
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Moldura do desenho"
    return tx


def delete_sheet(doc: Document, sheet) -> Transaction:
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    return Transaction("Excluir prancha", [Op("sheet.delete", sheet.GlobalId,
                                              data=read_state(sheet))])


def edit_project(doc: Document, **changes) -> Transaction:
    """Dados do carimbo (§4): nome, endereço, proprietário, responsável, registro."""
    state = read_project(doc)
    unknown = set(changes) - set(PROJECT_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    changes = {k: (v or None) for k, v in changes.items() if (v or None) != state.get(k)}
    if not changes:
        return Transaction("Editar dados do projeto", [])
    return Transaction("Editar dados do projeto", [Op(
        "project.edit", doc.project.GlobalId, before={k: state.get(k) for k in changes},
        after=changes)])
