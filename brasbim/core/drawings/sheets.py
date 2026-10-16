# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pranchas (spec/ui 15): formato, margens, carimbo, marcas de dobra e as vistas postas
nelas, sem Qt. O desenho no papel é feito pela interface (tela e PDF).

Operações: ``sheet.create`` / ``.delete`` / ``.edit`` e ``project.edit``.

Prancha = ``IfcAnnotation`` "Prancha" na edificação, com o estado em JSON no Pset
``BrasBim_Prancha``::

    {"number": "01", "title": "Planta baixa", "format": "A3",
     "orientation": "landscape",
     "views": [{"kind": "plan", "storey": "<GlobalId>", "at": [150.0, 160.0]},
               {"kind": "view", "view": "<GlobalId>", "at": [300.0, 160.0]}]}

Coordenadas do papel em milímetros, a partir do canto inferior esquerdo da folha.
Dados do projeto para o carimbo: Pset ``BrasBim_Projeto`` no ``IfcProject``.
"""

from __future__ import annotations

import copy
import json

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props, storeys
from brasbim.core.annotations.prims import Stroke, Text
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Prancha"
PROJECT_PSET = "BrasBim_Projeto"
OBJECT_TYPE = "Prancha"
# Formato → (largura, altura) na horizontal e margens (esquerda, demais), em mm (§2, CG).
FORMATS = {"A0": ((1189, 841), (25, 10)), "A1": ((841, 594), (25, 10)),
           "A2": ((594, 420), (25, 7)), "A3": ((420, 297), (25, 7)),
           "A4": ((297, 210), (25, 7))}
ORIENTATIONS = ("landscape", "portrait")
STATE_KEYS = ("number", "title", "format", "orientation", "views")
PROJECT_KEYS = {"name": None, "address": "Endereco", "owner": "Proprietario",
                "responsible": "Responsavel", "registration": "Registro"}
TITLE_WIDTH = 178.0  # mm: carimbo à vista na folha dobrada em A4 (§2)
_ROWS = (14.0, 7.0, 7.0, 7.0, 9.0, 7.0)  # alturas das linhas do carimbo (mm)
GAP = 10.0  # mm entre vistas postas sozinhas


def default_state() -> dict:
    return {"number": None, "title": "", "format": "A3", "orientation": "landscape",
            "views": []}


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
    (w, h), _ = FORMATS[state["format"]]
    return (float(h), float(w)) if state["orientation"] == "portrait" else (float(w), float(h))


def frame(state: dict) -> tuple[float, float, float, float]:
    """Quadro (x0, y0, x1, y1) dentro das margens."""
    w, h = paper(state)
    _, (left, other) = FORMATS[state["format"]]
    return left, other, w - other, h - other


def title_block(state: dict) -> tuple[float, float, float, float]:
    x0, y0, x1, _ = frame(state)
    return max(x0, x1 - TITLE_WIDTH), y0, x1, y0 + sum(_ROWS)


def fold_marks(state: dict) -> list[Stroke]:
    """Traços na borda do papel para dobrar em A4 (190 mm a partir da direita; a primeira
    dobra horizontal a 297 mm de baixo), §2 (CG)."""
    w, h = paper(state)
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


def scale_of(doc: Document, item: dict) -> int:
    if item["kind"] == "plan":
        storey = doc.find(item["storey"])
        return storeys.scale(storey) if storey is not None else storeys.DEFAULT_SCALE
    from brasbim.core.drawings import views

    view = doc.find(item["view"])
    return views.read_state(view)["scale"] if view is not None else storeys.DEFAULT_SCALE


def title_items(doc: Document, sheet, date: str) -> tuple[list[Stroke], list[Text]]:
    """Quadro e carimbo (§2): linhas e textos em mm do papel."""
    state = read_state(sheet)
    info = read_project(doc)
    x0, y0, x1, y1 = frame(state)
    tx0, ty0, tx1, ty1 = title_block(state)
    strokes = [Stroke(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), True, 0.5),
               Stroke(((tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)), True, 0.5)]
    sheets = all_sheets(doc)
    total = len(sheets)
    index = sheets.index(sheet) + 1 if sheet in sheets else 1
    scales = sorted({scale_of(doc, item) for item in state["views"]})
    responsible = " · ".join(v for v in (info["responsible"], info["registration"]) if v)
    rows = [(info["name"] or "", 5.0), (info["address"] or "", 2.5),
            (f"Proprietário: {info['owner']}" if info["owner"] else "", 2.5),
            (f"Responsável técnico: {responsible}" if responsible else "", 2.5),
            (state["title"] or "", 3.5),
            ((f"Escala {' / '.join(f'1:{s}' for s in scales) or '—'}    {date}    "
              f"Folha {index:02d}/{total:02d}"), 2.5)]
    texts = []
    y = ty1
    for (text, size), height in zip(rows, _ROWS, strict=True):
        y -= height
        if y > ty0 + 1e-6:
            strokes.append(Stroke(((tx0, y), (tx1, y)), False, 0.25))
        if text:
            texts.append(Text((tx0 + 3.0, y + (height - size) / 2), text, size, 0.0, "left",
                              "bottom"))
    return strokes + fold_marks(state), texts


# --- vistas na prancha --------------------------------------------------------------------


def view_bounds(doc: Document, item: dict):
    """Retângulo do desenho (m) da planta ou da vista, ou ``None``."""
    if item["kind"] == "plan":
        from brasbim.core import plan

        storey = doc.find(item["storey"])
        return plan.storey_plan(doc, storey).bounds() if storey is not None else None
    from brasbim.core.drawings import section

    view = doc.find(item["view"])
    if view is None:
        return None
    drawing = section.draw(doc, view)
    box = drawing.bounds()
    if box is None:
        return None
    pts = [t.at for t in drawing.texts]
    u0, v0, u1, v1 = box
    return (min([u0, *(p[0] for p in pts)]), min([v0, *(p[1] for p in pts)]),
            max([u1, *(p[0] for p in pts)]), max([v1, *(p[1] for p in pts)]))


def view_size(doc: Document, item: dict) -> tuple[float, float]:
    """Largura e altura (mm de papel) da vista na escala dela."""
    box = view_bounds(doc, item)
    if box is None:
        return 0.0, 0.0
    k = 1000.0 / scale_of(doc, item)
    return (box[2] - box[0]) * k, (box[3] - box[1]) * k


def free_spot(doc: Document, state: dict, size: tuple[float, float]) -> list[float]:
    """Centro da vista nova: à direita das que já estão, acima do carimbo."""
    x0, y0, x1, y1 = frame(state)
    _, _, _, top = title_block(state)
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
        if item.get("kind") not in ("plan", "view"):
            raise OpError(f"vista de prancha inválida: {item!r}")


def _write(doc: Document, sheet, state: dict) -> None:
    _validate(state)
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


def refs_removed_ops(doc: Document, gid: str) -> list[Op]:
    """``sheet.edit`` que tiram das pranchas a planta do pavimento ou a vista ``gid`` que
    vai ser excluída (§4)."""
    ops = []
    for sheet in all_sheets(doc):
        state = read_state(sheet)
        kept = [it for it in state["views"] if gid not in (it.get("storey"), it.get("view"))]
        if len(kept) != len(state["views"]):
            ops.append(Op("sheet.edit", sheet.GlobalId,
                          before={"views": copy.deepcopy(state["views"])},
                          after={"views": copy.deepcopy(kept)}))
    return ops


# --- comandos ----------------------------------------------------------------------------


def create_sheet(doc: Document, title: str = "", fmt: str = "A3",
                 orientation: str = "landscape") -> Transaction:
    data = {**default_state(), "number": next_number(doc), "title": title, "format": fmt,
            "orientation": orientation}
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
    """Põe a planta de um pavimento (``{"kind": "plan", "storey": gid}``) ou um corte/fachada
    (``{"kind": "view", "view": gid}``) na prancha, no primeiro lugar livre (§3)."""
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    state = read_state(sheet)
    item = {k: v for k, v in item.items() if k != "at"}
    key = item.get("storey") or item.get("view")
    if doc.find(key) is None:
        raise OpError("a vista não existe mais")
    if any(key in (it.get("storey"), it.get("view")) for it in state["views"]):
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


def remove_from_sheet(doc: Document, sheet, index: int) -> Transaction:
    sheet = doc.get(sheet if isinstance(sheet, str) else sheet.GlobalId, "IfcAnnotation")
    views_ = copy.deepcopy(read_state(sheet)["views"])
    del views_[index]
    tx = edit_sheet(doc, sheet, views=views_)
    tx.label = "Tirar da prancha"
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
