# SPDX-License-Identifier: LGPL-3.0-or-later
"""Folhas mestras (spec/ui 26): papel, margens, quadro, marcas de dobra e o desenho do
carimbo (linhas e textos com campos) que se repete nas pranchas que a usam. Sem Qt.

Operações: ``sheet_master.create`` / ``.delete`` (data: estado completo) e
``sheet_master.edit`` (before/after: campos alterados).

Folha mestra = ``IfcAnnotation`` "FolhaMestra" na edificação, sem representação, com o
estado em JSON no Pset ``BrasBim_FolhaMestra``::

    {"name": "A3 escritório", "format": "A3", "orientation": "landscape",
     "size": None, "margins": [25, 7, 7, 7], "frame": True, "fold_marks": True,
     "items": [{"kind": "line", "points": [[x, y], ...], "closed": False,
                "weight": 0.25},
               {"kind": "text", "at": [x, y], "text": "{projeto}", "height": 5.0,
                "align": "left", "bold": False}]}

``format`` ``custom`` usa ``size`` (largura, altura em mm). ``margins``: esquerda,
inferior, direita, superior. Coordenadas em mm do papel, a partir do canto inferior
esquerdo.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import guid, props
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_FolhaMestra"
OBJECT_TYPE = "FolhaMestra"
# Formato → (largura, altura) na horizontal e margens (esquerda, demais), em mm (spec/ui 15
# §2, CG).
FORMATS = {"A0": ((1189, 841), (25, 10)), "A1": ((841, 594), (25, 10)),
           "A2": ((594, 420), (25, 7)), "A3": ((420, 297), (25, 7)),
           "A4": ((297, 210), (25, 7))}
CUSTOM = "custom"
ORIENTATIONS = ("landscape", "portrait")
STATE_KEYS = ("name", "format", "orientation", "size", "margins", "frame", "fold_marks",
              "items")
ALIGNS = ("left", "center", "right")
FRAME_WEIGHT = 0.5  # mm: quadro na linha das margens
TITLE_WIDTH = 178.0  # mm: carimbo padrão à vista na folha dobrada em A4 (spec/ui 15 §2)
# Linhas do carimbo padrão: (texto com campos, altura do texto, altura da linha) em mm.
TITLE_ROWS = (("{projeto}", 5.0, 14.0), ("{endereco}", 2.5, 7.0),
              ("Proprietário: {proprietario}", 2.5, 7.0),
              ("Responsável técnico: {responsavel_tecnico}", 2.5, 7.0),
              ("{titulo}", 3.5, 9.0),
              ("Escala {escala}    {data}    Folha {folha}/{total}", 2.5, 7.0))
FIELDS = {"projeto": "Nome do projeto", "endereco": "Endereço da obra",
          "proprietario": "Proprietário", "responsavel": "Responsável técnico",
          "registro": "Registro (CAU/CREA)",
          "responsavel_tecnico": "Responsável · registro", "numero": "Número da prancha",
          "titulo": "Título da prancha", "escala": "Escalas das vistas",
          "data": "Data", "folha": "Número da folha", "total": "Total de folhas"}
_FIELD = re.compile(r"\{(\w+)\}")


@dataclass
class Layout:
    """O papel de uma prancha: tamanho, quadro (dentro das margens) e o desenho fixo."""

    size: tuple[float, float]
    frame: tuple[float, float, float, float]
    frame_on: bool = True
    fold_on: bool = True
    items: list = field(default_factory=list)


def standard_margins(fmt: str) -> list[float]:
    _, (left, other) = FORMATS.get(fmt, FORMATS["A3"])
    return [float(left), float(other), float(other), float(other)]


def paper_size(state: dict) -> tuple[float, float]:
    """(largura, altura) em mm do papel da folha mestra (ou do formato padrão)."""
    if state["format"] == CUSTOM:
        w, h = state["size"]
        return float(w), float(h)
    (w, h), _ = FORMATS[state["format"]]
    return (float(h), float(w)) if state["orientation"] == "portrait" else (float(w), float(h))


def frame_of(size, margins) -> tuple[float, float, float, float]:
    w, h = size
    left, bottom, right, top = margins
    return float(left), float(bottom), w - float(right), h - float(top)


def default_items(frame) -> list[dict]:
    """Carimbo padrão do BrasBim (spec/ui 15 §2) como linhas e textos com campos: no canto
    inferior direito do quadro, 178 mm de largura."""
    x0, y0, x1, _ = frame
    tx0, tx1 = max(x0, x1 - TITLE_WIDTH), x1
    ty0 = y0
    ty1 = ty0 + sum(row[2] for row in TITLE_ROWS)
    items = [{"kind": "line", "points": [[tx0, ty0], [tx1, ty0], [tx1, ty1], [tx0, ty1]],
              "closed": True, "weight": FRAME_WEIGHT}]
    y = ty1
    for text, size, height in TITLE_ROWS:
        y -= height
        if y > ty0 + 1e-6:
            items.append({"kind": "line", "points": [[tx0, y], [tx1, y]], "closed": False,
                          "weight": 0.25})
        items.append({"kind": "text", "at": [tx0 + 3.0, round(y + (height - size) / 2, 3)],
                      "text": text, "height": size, "align": "left", "bold": False})
    return items


def default_state(fmt: str = "A3", orientation: str = "landscape",
                  size=None) -> dict:
    state = {"name": "", "format": fmt, "orientation": orientation,
             "size": list(size) if size else None,
             "margins": standard_margins(fmt if fmt in FORMATS else "A3"), "frame": True,
             "fold_marks": True, "items": []}
    state["items"] = default_items(frame_of(paper_size(state), state["margins"]))
    return state


def layout_of(state: dict) -> Layout:
    size = paper_size(state)
    return Layout(size, frame_of(size, state["margins"]), bool(state["frame"]),
                  bool(state["fold_marks"]), copy.deepcopy(state["items"]))


def standard_layout(fmt: str, orientation: str) -> Layout:
    """Prancha sem folha mestra: formato da série A com o carimbo padrão."""
    state = default_state(fmt, orientation)
    return layout_of(state)


def items_bounds(items) -> tuple[float, float, float, float] | None:
    """Retângulo (mm) do desenho; o texto conta pela âncora e pela altura."""
    xs, ys = [], []
    for item in items:
        if item["kind"] == "line":
            xs += [p[0] for p in item["points"]]
            ys += [p[1] for p in item["points"]]
        else:
            xs.append(item["at"][0])
            ys += [item["at"][1], item["at"][1] + item["height"]]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# --- campos -----------------------------------------------------------------------------


def fields_in(text: str) -> list[str]:
    return [m for m in _FIELD.findall(text) if m in FIELDS]


def fill(text: str, values: dict) -> str | None:
    """Troca os campos pelos valores; ``None`` se o texto tem campos e todos ficaram
    vazios (o texto some, §2)."""
    names = fields_in(text)
    if names and not any(values.get(n) for n in names):
        return None
    return _FIELD.sub(lambda m: str(values.get(m.group(1)) or "")
                      if m.group(1) in FIELDS else m.group(0), text)


# --- leitura ----------------------------------------------------------------------------


def is_master(entity) -> bool:
    return (entity is not None and entity.is_a("IfcAnnotation")
            and entity.ObjectType == OBJECT_TYPE)


def all_masters(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcAnnotation") if is_master(e)),
                  key=lambda e: (read_state(e)["name"].lower(), e.GlobalId))


def read_state(entity) -> dict:
    values = ifcopenshell.util.element.get_pset(entity, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"folha mestra {entity.GlobalId} sem os parâmetros do BrasBim")
    return json.loads(values["Parametros"])


def describe(state: dict) -> str:
    """"A3 horizontal", "500 × 700 mm"."""
    if state["format"] == CUSTOM:
        w, h = state["size"]
        return f"{w:g} × {h:g} mm"
    orientation = "vertical" if state["orientation"] == "portrait" else "horizontal"
    return f"{state['format']} {orientation}"


def suggest_name(doc: Document, state: dict) -> str:
    used = {read_state(m)["name"] for m in all_masters(doc)}
    base = describe(state)
    name, n = base, 2
    while name in used:
        name, n = f"{base} ({n})", n + 1
    return name


# --- operações ---------------------------------------------------------------------------


def _validate(state: dict) -> None:
    if not (state.get("name") or "").strip():
        raise OpError("a folha mestra precisa de um nome")
    if state["format"] not in (*FORMATS, CUSTOM):
        raise OpError(f"formato inválido: {state['format']!r}")
    if state["orientation"] not in ORIENTATIONS:
        raise OpError(f"orientação inválida: {state['orientation']!r}")
    if state["format"] == CUSTOM:
        size = state.get("size") or ()
        if len(size) != 2 or min(size) < 50 or max(size) > 5000:
            raise OpError("papel personalizado: largura e altura entre 50 e 5000 mm")
    w, h = paper_size(state)
    margins = state.get("margins") or ()
    if len(margins) != 4 or min(margins) < 0:
        raise OpError("margens inválidas")
    x0, y0, x1, y1 = frame_of((w, h), margins)
    if x1 - x0 < 20 or y1 - y0 < 20:
        raise OpError("as margens não deixam espaço no papel")
    for item in state.get("items") or []:
        if item.get("kind") == "line":
            if len(item.get("points") or ()) < 2 or float(item.get("weight", 0)) <= 0:
                raise OpError("linha inválida na folha mestra")
        elif item.get("kind") == "text":
            if float(item.get("height", 0)) <= 0 or item.get("align") not in ALIGNS:
                raise OpError("texto inválido na folha mestra")
        else:
            raise OpError(f"item inválido na folha mestra: {item!r}")


def _write(doc: Document, entity, state: dict) -> None:
    _validate(state)
    building = doc.building
    entity.ObjectType = OBJECT_TYPE
    entity.Name = state["name"]
    if ifcopenshell.util.element.get_container(entity) != building:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[entity],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    if entity.ObjectPlacement is None:
        entity.ObjectPlacement = local_placement(doc.ifc, building.ObjectPlacement)
    props.write_pset(doc, entity, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        state, sort_keys=True, ensure_ascii=False))})


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    entity = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
    entity.GlobalId = op.id
    entity.PredefinedType = "USERDEFINED"
    try:
        _write(doc, entity, copy.deepcopy(op.data))
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=entity)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    ifcopenshell.api.root.remove_product(doc.ifc, product=doc.get(op.id, "IfcAnnotation"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    entity = doc.get(op.id, "IfcAnnotation")
    state = read_state(entity)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"sheet_master.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    _write(doc, entity, state)
    return {op.id}


register_inverse_pair("sheet_master.create", _create, "sheet_master.delete", _delete)
register("sheet_master.edit", _edit, invert_swap)


# --- comandos ----------------------------------------------------------------------------


def create_master(doc: Document, name: str = "", fmt: str = "A3",
                  orientation: str = "landscape", size=None, **changes) -> Transaction:
    """Folha mestra nova com o carimbo padrão (§3)."""
    if fmt not in (*FORMATS, CUSTOM):
        raise OpError(f"formato inválido: {fmt!r}")
    if fmt == CUSTOM and not size:
        raise OpError("papel personalizado precisa do tamanho")
    state = default_state(fmt, orientation, size)
    unknown = set(changes) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    state.update(copy.deepcopy(changes))
    state["name"] = (name or "").strip() or suggest_name(doc, state)
    _validate(state)
    return Transaction("Criar folha mestra", [Op("sheet_master.create", guid.new(),
                                                 data=state)])


def duplicate_master(doc: Document, master) -> Transaction:
    entity = doc.get(master if isinstance(master, str) else master.GlobalId, "IfcAnnotation")
    state = read_state(entity)
    used = {read_state(m)["name"] for m in all_masters(doc)}
    name, n = f"{state['name']} (cópia)", 2
    while name in used:
        name, n = f"{state['name']} (cópia {n})", n + 1
    data = {**copy.deepcopy(state), "name": name}
    return Transaction("Duplicar folha mestra", [Op("sheet_master.create", guid.new(),
                                                    data=data)])


def edit_master(doc: Document, master, label: str = "Editar folha mestra",
                **changes) -> Transaction:
    entity = doc.get(master if isinstance(master, str) else master.GlobalId, "IfcAnnotation")
    state = read_state(entity)
    unknown = set(changes) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    if changes.get("format") == CUSTOM and not (changes.get("size") or state.get("size")):
        changes["size"] = list(paper_size(state))
    _validate({**state, **changes})
    changes = {k: v for k, v in changes.items() if v != state.get(k)}
    if not changes:
        return Transaction(label, [])
    return Transaction(label, [Op("sheet_master.edit", entity.GlobalId,
                                  before={k: copy.deepcopy(state.get(k)) for k in changes},
                                  after=copy.deepcopy(changes))])


def delete_master(doc: Document, master) -> Transaction:
    """Exclui; as pranchas que a usavam ficam sem folha mestra, com o formato dela (§4)."""
    from brasbim.core.drawings import sheets

    entity = doc.get(master if isinstance(master, str) else master.GlobalId, "IfcAnnotation")
    state = read_state(entity)
    fmt = state["format"] if state["format"] in FORMATS else "A3"
    ops = []
    for sheet in sheets.all_sheets(doc):
        current = sheets.read_state(sheet)
        if current.get("master") != entity.GlobalId:
            continue
        after = {"master": None, "format": fmt, "orientation": state["orientation"]}
        ops.append(Op("sheet.edit", sheet.GlobalId,
                      before={k: current.get(k) for k in after}, after=after))
    ops.append(Op("sheet_master.delete", entity.GlobalId, data=state))
    return Transaction("Excluir folha mestra", ops)
