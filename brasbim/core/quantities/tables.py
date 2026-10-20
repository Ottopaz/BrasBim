# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tabelas de quantitativos (spec/ui 17): quadro de esquadrias, quadro de áreas e tabelas
montadas pelo usuário, sem Qt.

Operações: ``table.create`` / ``.delete`` / ``.edit``.

Tabela = ``IfcAnnotation`` "Tabela" na edificação, com a definição em JSON no Pset
``BrasBim_Tabela`` (§4)::

    {"name": "Quadro de esquadrias", "category": "fillings",
     "columns": [{"field": "code"}, {"field": "count", "title": "Qtd."}],
     "storeys": [], "types": [], "group_by": "type", "rows": "group",
     "sort": {"field": "width", "descending": true}, "totals": true,
     "built_area": false}

``storeys`` e ``types`` vazios = todos. ``title`` ausente = título padrão do campo.
Os valores não são gravados: ``compute`` os lê das quantidades dos elementos
(``Qto_*BaseQuantities``) a cada chamada.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.util.element

from brasbim.core import clip, guid, props
from brasbim.core.document import Document, OpError, local_placement
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register, register_inverse_pair

PSET = "BrasBim_Tabela"
OBJECT_TYPE = "Tabela"
MIXED = "vários"
STATE_KEYS = ("name", "category", "columns", "storeys", "types", "group_by", "rows", "sort",
              "totals", "built_area")
ROWS = ("element", "group")


@dataclass(frozen=True)
class Category:
    label: str
    classes: tuple[str, ...]
    type_classes: tuple[str, ...]  # tipos que o filtro oferece


CATEGORIES = {
    "walls": Category("Paredes", ("IfcWall",), ("IfcWallType",)),
    "doors": Category("Portas", ("IfcDoor",), ("IfcDoorType",)),
    "windows": Category("Janelas", ("IfcWindow",), ("IfcWindowType",)),
    "fillings": Category("Esquadrias", ("IfcDoor", "IfcWindow"),
                         ("IfcDoorType", "IfcWindowType")),
    "slabs": Category("Lajes", ("IfcSlab",), ("IfcSlabType",)),
    "columns": Category("Pilares", ("IfcColumn",), ("IfcColumnType",)),
    "beams": Category("Vigas", ("IfcBeam",), ("IfcBeamType",)),
    "roofs": Category("Coberturas", ("IfcRoof",), ("IfcSlabType",)),
    "spaces": Category("Ambientes", ("IfcSpace",), ()),
    # objetos paramétricos (objeto-parametrico.md §8)
    "furniture": Category("Mobiliário", ("IfcFurniture",), ("IfcFurnitureType",)),
    "sanitary": Category("Louças e metais", ("IfcSanitaryTerminal",),
                         ("IfcSanitaryTerminalType",)),
    "appliances": Category("Eletrodomésticos", ("IfcElectricAppliance",),
                           ("IfcElectricApplianceType",)),
    "vegetation": Category("Vegetação", ("IfcGeographicElement",),
                           ("IfcGeographicElementType",)),
    "objects": Category("Objetos", ("IfcFurniture", "IfcSanitaryTerminal",
                                    "IfcElectricAppliance", "IfcGeographicElement",
                                    "IfcBuildingElementProxy"),
                        ("IfcFurnitureType", "IfcSanitaryTerminalType",
                         "IfcElectricApplianceType", "IfcGeographicElementType",
                         "IfcBuildingElementProxyType")),
}
OBJECT_CATEGORIES = ("furniture", "sanitary", "appliances", "vegetation", "objects")
PARAM_PREFIX = "param:"


# --- leitura dos elementos ---------------------------------------------------------------


class _Reader:
    """Lê os valores dos elementos, guardando o que é caro (estado dos tipos)."""

    def __init__(self, doc: Document):
        self.doc = doc
        self._types: dict[str, dict] = {}
        self._built: dict[str, object] = {}

    def storey(self, element):
        current = element
        for _ in range(8):
            found = (ifcopenshell.util.element.get_container(current)
                     or ifcopenshell.util.element.get_aggregate(current))
            if found is None or found.is_a("IfcBuildingStorey"):
                return found
            current = found
        return None

    def element_type(self, element):
        if element.is_a("IfcRoof"):
            from brasbim.core.structure import roofs

            if roofs.is_roof(element):
                return self.doc.find(roofs.read_state(self.doc, element)["type"] or "")
        return ifcopenshell.util.element.get_type(element)

    def built(self, element):
        """Cálculo do objeto paramétrico (de primeiro nível ou aninhado), guardado."""
        from brasbim.core.objects import elements as objects

        gid = element.GlobalId
        if gid not in self._built:
            try:
                self._built[gid] = objects.built_of(self.doc, element)
            except (OpError, KeyError, TypeError, ValueError):
                self._built[gid] = None
        return self._built[gid]

    def type_state(self, element_type) -> dict:
        gid = element_type.GlobalId
        if gid not in self._types:
            from brasbim.core.fillings import door_types, window_types
            from brasbim.core.structure import types as structure_types

            if element_type.is_a("IfcDoorType"):
                state = door_types.read(element_type)
            elif element_type.is_a("IfcWindowType"):
                state = window_types.read(element_type)
            else:
                try:
                    state = {"section": structure_types.section(element_type)}
                except (OpError, AttributeError, TypeError):
                    state = {}
            self._types[gid] = state
        return self._types[gid]


def _q(element, qto: str, name: str):
    values = ifcopenshell.util.element.get_pset(element, qto, should_inherit=False) or {}
    value = values.get(name)
    return float(value) if isinstance(value, (int, float)) else None


def _filling_qto(element) -> str:
    return ("Qto_WindowBaseQuantities" if element.is_a("IfcWindow")
            else "Qto_DoorBaseQuantities")


def _code(r: _Reader, e):
    from brasbim.core.fillings import params

    pset = "Pset_WindowCommon" if e.is_a("IfcWindow") else "Pset_DoorCommon"
    values = ifcopenshell.util.element.get_pset(e, pset) or {}
    if values.get("Reference"):
        return values["Reference"]
    t = r.element_type(e)
    return params.base_name(t.Name) if t is not None and t.Name else None


def _sill(r: _Reader, e):
    from brasbim.core.fillings import commands as fc
    from brasbim.core.walls import openings

    opening = fc.opening_of(e)
    if opening is None:
        return None
    try:
        return float(openings.read_state(opening)["sill"])
    except (OpError, KeyError, TypeError, AttributeError):
        return None


def _operation(r: _Reader, e):
    from brasbim.core.fillings import params

    t = r.element_type(e)
    if t is None:
        return None
    state = r.type_state(t)
    if t.is_a("IfcDoorType"):
        labels = {v: k for k, v in params.DOOR_OPERATION_LABELS}
        return labels.get(state.get("operation_type"), state.get("operation_type"))
    labels = {v: k for k, v in params.WINDOW_OPERATION_LABELS}
    ops = list(dict.fromkeys(p["operation"] for p in state.get("panels", [])))
    return " + ".join(labels.get(op, op) for op in ops) or None


def _section(r: _Reader, e):
    from brasbim.core.structure import profiles

    t = r.element_type(e)
    section = r.type_state(t).get("section") if t is not None else None
    return profiles.label(section) if section else None


def _roof(r: _Reader, e, key: str):
    from brasbim.core.structure import roofs

    if not roofs.is_roof(e):
        return None
    state = roofs.read_state(r.doc, e)
    if key == "shape":
        return roofs.SHAPE_NAMES[state["shape"]].capitalize()
    return None if state["shape"] == "flat" else float(state["slope"])


def _plan_area(r: _Reader, e):
    from brasbim.core.structure import roofs

    values = ifcopenshell.util.element.get_pset(e, roofs.PSET, should_inherit=False) or {}
    value = values.get("AreaProjecao")
    return float(value) if isinstance(value, (int, float)) else None


@dataclass(frozen=True)
class Field:
    key: str
    title: str
    unit: str | None
    sums: bool
    get: Callable[[_Reader, object], object]
    order: Callable[[_Reader, object], object] | None = None  # valor para ordenar

    @property
    def heading(self) -> str:
        return f"{self.title} ({self.unit})" if self.unit else self.title


def _object_value(r: _Reader, e, what: str):
    built = r.built(e)
    if built is None:
        return None
    if what == "object":
        return built.definition["name"]
    if what == "code":
        return built.type_state["values"].get("codigo") or None
    if what in ("length", "depth", "height"):
        box = built.box
        if box is None:
            return None
        return {"length": box[1] - box[0], "depth": box[3] - box[2],
                "height": box[5] - box[4]}[what]
    return None


def _part_of(r: _Reader, e):
    from brasbim.core.objects import elements as objects

    if not objects.is_part(e):
        return None
    return objects.parent_of(e).Name


def _object_category(r: _Reader, e):
    from brasbim.core.objects import definition as od

    built = r.built(e)
    return od.CATEGORIES[built.definition["category"]][3] if built is not None else None


def _param_field(key: str, p: dict | None = None):
    """Coluna de um parâmetro do objeto (§8): ``param:<identificador>``."""
    from brasbim.core.objects import formula as fm

    name = key[len(PARAM_PREFIX):]
    title = (p or {}).get("label") or name
    unit = {"length": "m", "angle": "°"}.get((p or {}).get("kind"))

    def get(r: _Reader, e):
        built = r.built(e)
        if built is None:
            return None
        value = built.values.get(fm.key(name))
        if isinstance(value, bool):
            return "sim" if value else "não"
        return value

    return Field(key, title, unit, False, get)


class _Fields(dict):
    """Campos da categoria; nos objetos, ``param:<identificador>`` vale sempre."""

    def __init__(self, items, objects: bool):
        super().__init__(items)
        self.objects = objects

    def __missing__(self, key):
        if self.objects and isinstance(key, str) and key.startswith(PARAM_PREFIX):
            return _param_field(key)
        raise KeyError(key)

    def __contains__(self, key):
        return super().__contains__(key) or (
            self.objects and isinstance(key, str) and key.startswith(PARAM_PREFIX)
            and len(key) > len(PARAM_PREFIX))


def _storey_name(r: _Reader, e):
    storey = r.storey(e)
    return storey.Name if storey is not None else None


def _storey_order(r: _Reader, e):
    storey = r.storey(e)
    return float(storey.Elevation or 0.0) if storey is not None else None


def _type_name(r: _Reader, e):
    t = r.element_type(e)
    return t.Name if t is not None else None


_COMMON = [
    Field("storey", "Pavimento", None, False, _storey_name, _storey_order),
    Field("type", "Tipo", None, False, _type_name),
    Field("name", "Nome", None, False, lambda r, e: e.Name),
    Field("count", "Contagem", None, True, lambda r, e: 1),
    Field("guid", "GlobalId", None, False, lambda r, e: e.GlobalId),
]
_W = "Qto_WallBaseQuantities"
_FILLINGS = [
    Field("code", "Código", None, False, _code),
    Field("class", "Classe", None, False,
          lambda r, e: "Janela" if e.is_a("IfcWindow") else "Porta"),
    Field("width", "Largura", "m", False, lambda r, e: _q(e, _filling_qto(e), "Width")),
    Field("height", "Altura", "m", False, lambda r, e: _q(e, _filling_qto(e), "Height")),
    Field("sill", "Peitoril", "m", False, _sill),
    Field("area", "Área do vão", "m²", True, lambda r, e: _q(e, _filling_qto(e), "Area")),
    Field("operation", "Operação", None, False, _operation),
]
_S = "Qto_SlabBaseQuantities"
_C = "Qto_ColumnBaseQuantities"
_B = "Qto_BeamBaseQuantities"
_SP = "Qto_SpaceBaseQuantities"
_OWN = {
    "walls": [
        Field("length", "Comprimento", "m", True, lambda r, e: _q(e, _W, "Length")),
        Field("thickness", "Espessura", "m", False, lambda r, e: _q(e, _W, "Width")),
        Field("height", "Altura", "m", False, lambda r, e: _q(e, _W, "Height")),
        Field("side_area", "Área lateral", "m²", True, lambda r, e: _q(e, _W, "NetSideArea")),
        Field("gross_side_area", "Área lateral bruta", "m²", True,
              lambda r, e: _q(e, _W, "GrossSideArea")),
        Field("volume", "Volume", "m³", True, lambda r, e: _q(e, _W, "NetVolume")),
    ],
    "doors": _FILLINGS,
    "windows": _FILLINGS,
    "fillings": _FILLINGS,
    "slabs": [
        Field("area", "Área", "m²", True, lambda r, e: _q(e, _S, "NetArea")),
        Field("perimeter", "Perímetro", "m", True, lambda r, e: _q(e, _S, "Perimeter")),
        Field("thickness", "Espessura", "m", False, lambda r, e: _q(e, _S, "Width")),
        Field("volume", "Volume", "m³", True, lambda r, e: _q(e, _S, "NetVolume")),
    ],
    "columns": [
        Field("section", "Seção", "cm", False, _section),
        Field("height", "Altura", "m", False, lambda r, e: _q(e, _C, "Length")),
        Field("volume", "Volume", "m³", True, lambda r, e: _q(e, _C, "NetVolume")),
    ],
    "beams": [
        Field("section", "Seção", "cm", False, _section),
        Field("length", "Comprimento", "m", True, lambda r, e: _q(e, _B, "Length")),
        Field("volume", "Volume", "m³", True, lambda r, e: _q(e, _B, "NetVolume")),
    ],
    "roofs": [
        Field("shape", "Forma", None, False, lambda r, e: _roof(r, e, "shape")),
        Field("slope", "Inclinação", "%", False, lambda r, e: _roof(r, e, "slope")),
        Field("roof_area", "Área do telhado", "m²", True,
              lambda r, e: _q(e, "Qto_RoofBaseQuantities", "NetArea")),
        Field("plan_area", "Área em planta", "m²", True, _plan_area),
    ],
    **{k: [
        Field("code", "Código", None, False, lambda r, e: _object_value(r, e, "code")),
        Field("object", "Objeto", None, False, lambda r, e: _object_value(r, e, "object")),
        Field("class", "Categoria", None, False, _object_category),
        Field("part_of", "Parte de", None, False, _part_of),
        Field("length", "Largura", "m", False, lambda r, e: _object_value(r, e, "length")),
        Field("depth", "Profundidade", "m", False,
              lambda r, e: _object_value(r, e, "depth")),
        Field("height", "Altura", "m", False, lambda r, e: _object_value(r, e, "height")),
    ] for k in OBJECT_CATEGORIES},
    "spaces": [
        Field("number", "Número", None, False, lambda r, e: e.Name),
        Field("space_name", "Nome do ambiente", None, False, lambda r, e: e.LongName),
        Field("floor_area", "Área útil", "m²", True, lambda r, e: _q(e, _SP, "NetFloorArea")),
        Field("perimeter", "Perímetro", "m", True, lambda r, e: _q(e, _SP, "GrossPerimeter")),
        Field("height", "Pé-direito", "m", False, lambda r, e: _q(e, _SP, "Height")),
    ],
}
# Desempate da ordem (§3.1: "depois o código").
_NATURAL = {"doors": "code", "windows": "code", "fillings": "code", "spaces": "number"}


def fields_of(category: str, doc: Document | None = None) -> dict[str, Field]:
    """Campos da categoria. Nos objetos, com ``doc``, também os parâmetros dos tipos do
    projeto daquela categoria (§8)."""
    if category not in CATEGORIES:
        raise OpError(f"categoria de tabela inválida: {category!r}")
    out = _Fields({f.key: f for f in (*_COMMON, *_OWN[category])},
                  category in OBJECT_CATEGORIES)
    if doc is not None and category in OBJECT_CATEGORIES:
        from brasbim.core.objects import definition as od
        from brasbim.core.objects import types as ot

        classes = CATEGORIES[category].type_classes
        for t in ot.all_types(doc):
            if not any(t.is_a(c) for c in classes):
                continue
            for p in ot.definition_of(t)["params"]:
                if od.is_builtin(p):
                    continue
                key = PARAM_PREFIX + p["name"]
                if key not in dict.keys(out):
                    out[key] = _param_field(key, p)
    return out


def elements_of(doc: Document, state: dict, reader: _Reader | None = None) -> list:
    """Elementos da categoria que passam no filtro (§3.1)."""
    from brasbim.core.structure import roofs

    reader = reader or _Reader(doc)
    category = CATEGORIES[state["category"]]
    found = {e.GlobalId: e for cls in category.classes for e in doc.ifc.by_type(cls)}
    out = []
    objects_only = state["category"] in OBJECT_CATEGORIES
    if objects_only:
        from brasbim.core.objects import elements as objects
    for e in found.values():
        if state["category"] == "slabs" and roofs.is_part(e):
            continue  # as águas entram pela cobertura
        if objects_only and not (objects.is_object(e) or objects.is_part(e)):
            continue  # só os objetos do BrasBim (e os aninhados, que contam por si)
        if state["storeys"]:
            storey = reader.storey(e)
            if storey is None or storey.GlobalId not in state["storeys"]:
                continue
        if state["types"]:
            t = reader.element_type(e)
            if t is None or t.GlobalId not in state["types"]:
                continue
        out.append(e)
    return out


def type_options(doc: Document, category: str) -> list:
    """Tipos que o filtro oferece para a categoria (cobertura: os tipos de telhado)."""
    out = []
    for cls in CATEGORIES[category].type_classes:
        for t in doc.ifc.by_type(cls):
            if cls == "IfcSlabType" and (t.PredefinedType == "ROOF") != (category == "roofs"):
                continue
            out.append(t)
    return sorted(out, key=lambda t: (natural_key(t.Name or ""), t.GlobalId))


# --- cálculo -------------------------------------------------------------------------------


@dataclass
class Column:
    field: str
    title: str
    sums: bool


@dataclass
class Row:
    """Linha calculada. ``kind``: ``element``, ``group`` (uma por grupo), ``subtotal``,
    ``built`` (área construída), ``total`` ou ``built_total``."""

    kind: str
    cells: list
    elements: list[str] = field(default_factory=list)

    @property
    def bold(self) -> bool:
        return self.kind not in ("element", "group")


@dataclass
class Result:
    name: str
    columns: list[Column]
    rows: list[Row]


def natural_key(text: str) -> tuple:
    """"J2" antes de "J10"."""
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                 for p in re.split(r"(\d+)", text.casefold()) if p)


def _order_key(value) -> tuple:
    if value is None:
        return (1, ())
    if isinstance(value, (int, float)):
        return (0, (float(value),))
    return (0, natural_key(str(value)))


def _merge(values: list, sums: bool, integer: bool = False):
    if sums:
        total = sum(v for v in values if isinstance(v, (int, float)))
        return int(total) if integer else float(total)
    distinct = list(dict.fromkeys(values))
    if len(distinct) == 1:
        return distinct[0]
    return MIXED if distinct else None


def built_area(doc: Document, storey) -> float:
    """Área construída do pavimento: dentro da face externa das paredes, com as paredes,
    somando as edificações (§3.3)."""
    from brasbim.core.structure import rooms

    return sum(abs(clip.signed_area(r)) for r in rooms.building_rings(doc, storey))


def compute(doc: Document, table) -> Result:
    """Linhas da tabela (entidade ou estado), recalculadas do modelo (§3)."""
    state = read_state(table) if hasattr(table, "is_a") else {**default_state(), **table}
    validate(state)
    fields = fields_of(state["category"])
    columns = [Column(c["field"], c.get("title") or fields[c["field"]].heading,
                      fields[c["field"]].sums) for c in state["columns"]]
    reader = _Reader(doc)
    elements = elements_of(doc, state, reader)
    natural = fields[_NATURAL.get(state["category"], "name")]
    group = fields[state["group_by"]] if state["group_by"] else None
    sort = state["sort"]
    wanted = {c.field for c in columns}
    records = []
    for e in elements:
        values = {key: fields[key].get(reader, e) for key in wanted}
        keys = {"natural": _order_key(natural.get(reader, e))}
        if sort:
            f = fields[sort["field"]]
            keys["sort"] = _order_key((f.order or f.get)(reader, e))
        if group:
            keys["group"] = _order_key((group.order or group.get)(reader, e))
            values["_group"] = group.get(reader, e)
        records.append((e, values, keys))
    records.sort(key=lambda rec: (rec[2]["natural"], rec[0].GlobalId))
    if sort:
        records.sort(key=lambda rec: rec[2]["sort"], reverse=bool(sort.get("descending")))
    if group:
        records.sort(key=lambda rec: rec[2]["group"])
    groups: list[list] = []
    for rec in records:
        if group and groups and groups[-1][0][1]["_group"] == rec[1]["_group"]:
            groups[-1].append(rec)
        elif group or not groups:
            groups.append([rec])
        else:
            groups[-1].append(rec)

    def merged(recs) -> list:
        return [_merge([v[c.field] for _, v, _ in recs], c.sums, c.field == "count")
                for c in columns]

    def labelled(kind: str, label: str, recs, cells=None) -> Row:
        if cells is None:
            cells = [cell if c.sums else None for c, cell in zip(columns, merged(recs),
                                                                 strict=True)]
        if columns and not columns[0].sums:
            cells[0] = label
        return Row(kind, cells, [e.GlobalId for e, _, _ in recs])

    area_col = next((i for i, c in enumerate(columns) if c.field == "floor_area"), None)
    with_built = (state["built_area"] and state["category"] == "spaces"
                  and state["group_by"] == "storey" and area_col is not None)
    rows: list[Row] = []
    built_total = 0.0
    for recs in groups:
        text = format_value(recs[0][1]["_group"]) if group else ""
        if state["rows"] == "group":
            rows.append(Row("group", merged(recs), [e.GlobalId for e, _, _ in recs]))
        else:
            rows += [Row("element", [v[c.field] for c in columns], [e.GlobalId])
                     for e, v, _ in recs]
            if group and state["totals"]:
                rows.append(labelled("subtotal", f"Subtotal {text}".strip(), recs))
        if with_built:
            storey = reader.storey(recs[0][0])
            area = built_area(doc, storey) if storey is not None else 0.0
            built_total += area
            cells = [None] * len(columns)
            cells[area_col] = area
            rows.append(labelled("built", f"Área construída {text}".strip(), [], cells))
    if state["totals"] and any(c.sums for c in columns):
        rows.append(labelled("total", "Total", [rec for recs in groups for rec in recs]))
    if with_built and len(groups) > 1:
        cells = [None] * len(columns)
        cells[area_col] = built_total
        rows.append(labelled("built_total", "Área construída total", [], cells))
    return Result(state["name"], columns, rows)


def format_value(value) -> str:
    """Texto da célula: duas casas e vírgula decimal; a contagem sem casas (§3.2)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", ",").replace("-0,00", "0,00")
    return str(value)


# --- definição -----------------------------------------------------------------------------


def default_state() -> dict:
    return {"name": "", "category": "walls", "columns": [{"field": "type"},
                                                         {"field": "count"}],
            "storeys": [], "types": [], "group_by": None, "rows": "element", "sort": None,
            "totals": True, "built_area": False}


def is_table(entity) -> bool:
    return (entity is not None and entity.is_a("IfcAnnotation")
            and entity.ObjectType == OBJECT_TYPE)


def all_tables(doc: Document) -> list:
    return sorted((e for e in doc.ifc.by_type("IfcAnnotation") if is_table(e)),
                  key=lambda e: (natural_key(read_state(e)["name"]), e.GlobalId))


def read_state(table) -> dict:
    values = ifcopenshell.util.element.get_pset(table, PSET, should_inherit=False) or {}
    if "Parametros" not in values:
        raise OpError(f"tabela {table.GlobalId} sem os parâmetros do BrasBim")
    return {**default_state(), **json.loads(values["Parametros"])}


def validate(state: dict) -> None:
    fields = fields_of(state["category"])
    if not isinstance(state["name"], str):
        raise OpError("nome de tabela inválido")
    if not state["columns"]:
        raise OpError("a tabela precisa de ao menos uma coluna")
    for c in state["columns"]:
        if not isinstance(c, dict) or c.get("field") not in fields:
            raise OpError(f"coluna inválida para {CATEGORIES[state['category']].label}: {c!r}")
        if set(c) - {"field", "title"} or not isinstance(c.get("title", ""), str):
            raise OpError(f"coluna inválida: {c!r}")
    if len({c["field"] for c in state["columns"]}) != len(state["columns"]):
        raise OpError("coluna repetida na tabela")
    if state["group_by"] is not None and state["group_by"] not in fields:
        raise OpError(f"agrupamento inválido: {state['group_by']!r}")
    if state["rows"] not in ROWS:
        raise OpError(f"linhas inválidas: {state['rows']!r}")
    sort = state["sort"]
    if sort is not None and (not isinstance(sort, dict) or sort.get("field") not in fields
                             or set(sort) - {"field", "descending"}):
        raise OpError(f"ordem inválida: {sort!r}")
    for key in ("storeys", "types"):
        if not isinstance(state[key], list) or not all(isinstance(g, str) for g in state[key]):
            raise OpError(f"filtro inválido: {key}")


def fitted(state: dict) -> dict:
    """Definição ajustada a uma categoria nova: tira o que ela não tem (§3.1)."""
    out = copy.deepcopy(state)
    fields = fields_of(out["category"])
    out["columns"] = [c for c in out["columns"] if c.get("field") in fields] or \
        copy.deepcopy(default_state()["columns"])
    if out["group_by"] not in fields:
        out["group_by"] = None
    if out["sort"] and out["sort"].get("field") not in fields:
        out["sort"] = None
    if out["category"] != "spaces":
        out["built_area"] = False
    return out


def _write(doc: Document, table, state: dict) -> None:
    validate(state)
    building = doc.building
    table.ObjectType = OBJECT_TYPE
    table.Name = state["name"] or None
    if ifcopenshell.util.element.get_container(table) != building:
        rel = ifcopenshell.api.spatial.assign_container(doc.ifc, products=[table],
                                                        relating_structure=building)
        guid.stamp(rel, building.GlobalId, "contains")
    if table.ObjectPlacement is None:
        table.ObjectPlacement = local_placement(doc.ifc, building.ObjectPlacement)
    props.write_pset(doc, table, PSET, {"Parametros": doc.ifc.createIfcText(json.dumps(
        state, sort_keys=True, ensure_ascii=False))})


def _create(doc: Document, op: Op) -> set[str]:
    if doc.find(op.id) is not None:
        raise OpError(f"GlobalId {op.id} já existe")
    table = ifcopenshell.api.root.create_entity(doc.ifc, ifc_class="IfcAnnotation")
    table.GlobalId = op.id
    table.PredefinedType = "USERDEFINED"
    try:
        _write(doc, table, {**default_state(), **copy.deepcopy(op.data)})
    except Exception:
        ifcopenshell.api.root.remove_product(doc.ifc, product=table)
        raise
    return {op.id}


def _delete(doc: Document, op: Op) -> set[str]:
    ifcopenshell.api.root.remove_product(doc.ifc, product=doc.get(op.id, "IfcAnnotation"))
    return {op.id}


def _edit(doc: Document, op: Op) -> set[str]:
    table = doc.get(op.id, "IfcAnnotation")
    state = read_state(table)
    check_before(op, state)
    unknown = set(op.after or {}) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"table.edit: campos desconhecidos {sorted(unknown)}")
    state.update(copy.deepcopy(op.after or {}))
    _write(doc, table, state)
    return {op.id}


register_inverse_pair("table.create", _create, "table.delete", _delete)
register("table.edit", _edit, invert_swap)


def refs_removed_ops(doc: Document, gid: str) -> list[Op]:
    """``table.edit`` que tiram dos filtros o pavimento ou o tipo ``gid`` que vai ser
    excluído (§4); filtro vazio vale para todos."""
    ops = []
    for table in all_tables(doc):
        state = read_state(table)
        before, after = {}, {}
        for key in ("storeys", "types"):
            if gid in state[key]:
                before[key] = list(state[key])
                after[key] = [g for g in state[key] if g != gid]
        if after:
            ops.append(Op("table.edit", table.GlobalId, before=before, after=after))
    return ops


# --- modelos prontos (§3.3) ------------------------------------------------------------------


def _cols(*keys) -> list[dict]:
    return [{"field": k} for k in keys]


TEMPLATES = {
    "fillings": ("Quadro de esquadrias", [{
        "name": "Quadro de esquadrias", "category": "fillings",
        "columns": _cols("code", "type", "width", "height", "sill", "count"),
        "group_by": "type", "rows": "group"}]),
    "areas": ("Quadro de áreas", [{
        "name": "Quadro de áreas", "category": "spaces",
        "columns": _cols("number", "space_name", "floor_area", "perimeter"),
        "group_by": "storey", "rows": "element", "built_area": True}]),
    "walls": ("Paredes por tipo", [{
        "name": "Paredes por tipo", "category": "walls",
        "columns": _cols("type", "thickness", "length", "side_area", "volume"),
        "group_by": "type", "rows": "group"}]),
    "structure": ("Estrutura (concreto)", [
        {"name": "Estrutura: pilares", "category": "columns",
         "columns": _cols("type", "section", "count", "volume"), "group_by": "type",
         "rows": "group"},
        {"name": "Estrutura: vigas", "category": "beams",
         "columns": _cols("type", "section", "count", "volume"), "group_by": "type",
         "rows": "group"},
        {"name": "Estrutura: lajes", "category": "slabs",
         "columns": _cols("type", "count", "volume"), "group_by": "type",
         "rows": "group"}]),
    "objects": ("Lista de mobiliário e equipamentos", [{
        "name": "Lista de mobiliário e equipamentos", "category": "objects",
        "columns": _cols("code", "object", "type", "count"),
        "group_by": "type", "rows": "group"}]),
    "blank": ("Em branco", [{"category": None, "columns": _cols("type", "count")}]),
}


def _unique_name(used: set[str], base: str) -> str:
    if base not in used:
        return base
    n = 2
    while f"{base} {n}" in used:
        n += 1
    return f"{base} {n}"


def next_name(doc: Document) -> str:
    used = {read_state(t)["name"] for t in all_tables(doc)}
    n = 1
    while f"Tabela {n}" in used:
        n += 1
    return f"Tabela {n}"


# --- comandos --------------------------------------------------------------------------------


def _table(doc: Document, table):
    return doc.get(table if isinstance(table, str) else table.GlobalId, "IfcAnnotation")


def create_table(doc: Document, template: str = "blank", category: str = "walls",
                 name: str | None = None) -> Transaction:
    """Tabela nova a partir de um modelo (§3.3); "Estrutura" cria três. ``category`` vale
    para o modelo em branco."""
    if template not in TEMPLATES:
        raise OpError(f"modelo de tabela inválido: {template!r}")
    label, definitions = TEMPLATES[template]
    used = {read_state(t)["name"] for t in all_tables(doc)}
    ops = []
    for definition in definitions:
        data = {**default_state(), **copy.deepcopy(definition)}
        if data["category"] is None:
            data["category"] = category
            data["name"] = name or next_name(doc)
        elif name and len(definitions) == 1:
            data["name"] = name
        data["name"] = _unique_name(used, data["name"])
        used.add(data["name"])
        validate(data)
        ops.append(Op("table.create", guid.new(), data=data))
    return Transaction(f"Criar tabela ({label})" if template != "blank" else "Criar tabela",
                       ops)


def edit_table(doc: Document, table, **changes) -> Transaction:
    """Muda a definição (§5). Trocar a categoria tira as colunas, o agrupamento e a
    ordem que ela não tem."""
    table = _table(doc, table)
    state = read_state(table)
    unknown = set(changes) - set(STATE_KEYS)
    if unknown:
        raise OpError(f"parâmetros desconhecidos: {sorted(unknown)}")
    new = {**state, **copy.deepcopy(changes)}
    if "category" in changes and changes["category"] != state["category"]:
        if "types" not in changes:
            new["types"] = []
        new = fitted(new)
    validate(new)
    changed = {k: new[k] for k in STATE_KEYS if new[k] != state[k]}
    if not changed:
        return Transaction("Editar tabela", [])
    return Transaction("Editar tabela", [Op(
        "table.edit", table.GlobalId, before={k: copy.deepcopy(state[k]) for k in changed},
        after=copy.deepcopy(changed))])


def delete_table(doc: Document, table) -> Transaction:
    table = _table(doc, table)
    return Transaction("Excluir tabela", [Op("table.delete", table.GlobalId,
                                             data=read_state(table))])
