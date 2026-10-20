# SPDX-License-Identifier: LGPL-3.0-or-later
"""Definição de um objeto paramétrico (``spec/elementos/objeto-parametrico.md`` §3).

A definição é um dicionário (gravado em JSON no Pset ``BrasBim_DefinicaoObjeto`` de cada
tipo, §2.2)::

    {"object_id": "<22 caracteres>", "version": 1, "name": "Cama",
     "category": "furniture", "predefined_type": "BED", "element_type": None,
     "hosting": "free", "elevation": 0.0, "description": "",
     "params": [{"name": "largura", "label": "Largura", "kind": "length",
                 "level": "type", "value": 1.38, "formula": None, "min": 0.5, "max": None,
                 "group": "Dimensões", "options": None, "accepts": None, "handle": None}],
     "pieces": [{"kind": "box", "name": "Estrado", "x": 0, "y": 0, "z": 0,
                 "width": "largura", "depth": "comprimento", "height": 0.30,
                 "rotation": 0, "role": "Frame", "material": "Madeira",
                 "visible": None, "repeat": None, "void": False}],
     "symbol": {"mode": "auto", "items": []}}

Cada medida de peça é um número ou uma fórmula em texto (``formula``). Sem Qt e sem IFC:
aqui ficam a validação (``problems``), o cálculo dos valores (``evaluate``) e a expansão
das peças (``solids``, ``nested``, ``symbol_items``, ``bounds``).
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass, field

from brasbim.core.document import OpError
from brasbim.core.objects import formula as fm
from brasbim.core.objects.formula import BOOL, NUMBER, TEXT, FormulaError

# Categoria → (classe da ocorrência, classe do tipo, Pset comum, rótulo) (§2.1).
CATEGORIES = {
    "furniture": ("IfcFurniture", "IfcFurnitureType", "Pset_FurnitureTypeCommon",
                  "Mobiliário"),
    "sanitary": ("IfcSanitaryTerminal", "IfcSanitaryTerminalType",
                 "Pset_SanitaryTerminalTypeCommon", "Louças e metais"),
    "appliance": ("IfcElectricAppliance", "IfcElectricApplianceType",
                  "Pset_ElectricApplianceTypeCommon", "Eletrodomésticos"),
    "vegetation": ("IfcGeographicElement", "IfcGeographicElementType",
                   "Pset_VegetationCommon", "Vegetação"),
    "proxy": ("IfcBuildingElementProxy", "IfcBuildingElementProxyType", None, "Genérico"),
}
PREDEFINED = {
    "furniture": ("BED", "CHAIR", "TABLE", "DESK", "SOFA", "SHELF", "FILECABINET",
                  "TECHNICALCABINET", "USERDEFINED", "NOTDEFINED"),
    "sanitary": ("TOILETPAN", "WASHHANDBASIN", "SINK", "SHOWER", "BATH", "URINAL", "BIDET",
                 "CISTERN", "SANITARYFOUNTAIN", "USERDEFINED", "NOTDEFINED"),
    "appliance": ("REFRIGERATOR", "FRIDGE_FREEZER", "FREEZER", "ELECTRICCOOKER",
                  "MICROWAVE", "WASHINGMACHINE", "DISHWASHER", "TUMBLEDRYER",
                  "KITCHENMACHINE", "USERDEFINED", "NOTDEFINED"),
    "vegetation": ("VEGETATION",),
    "proxy": ("NOTDEFINED", "USERDEFINED"),
}
# Papéis de material (constituintes, §2.3).
ROLES = {
    "furniture": ("Frame", "Finish", "Hardware", "Padding", "Panel"),
    "sanitary": ("Body", "Finish"),
    "appliance": ("Body", "Finish"),
    "vegetation": ("Trunk", "Canopy"),
    "proxy": ("Body", "Finish"),
}
ROLE_LABELS = {"Frame": "Estrutura", "Finish": "Acabamento", "Hardware": "Ferragens",
               "Padding": "Estofado", "Panel": "Painéis e vidro", "Body": "Corpo",
               "Trunk": "Tronco", "Canopy": "Copa"}

# Tipo do valor → tipo nas fórmulas (§3.1).
KINDS = {"length": NUMBER, "angle": NUMBER, "number": NUMBER, "integer": NUMBER,
         "bool": BOOL, "text": TEXT, "choice": TEXT, "material": TEXT, "object_type": TEXT}
KIND_LABELS = {"length": "Comprimento", "angle": "Ângulo", "number": "Número",
               "integer": "Inteiro", "bool": "Sim/não", "text": "Texto", "choice": "Escolha",
               "material": "Material", "object_type": "Tipo de objeto"}
LEVELS = ("type", "occurrence")
GROUPS = ("Dimensões", "Materiais", "Visibilidade", "Outros")
HOSTING = ("free", "wall")
PIECE_KINDS = ("box", "cylinder", "extrusion", "revolution", "object")
SYMBOL_KINDS = ("line", "polyline", "rect", "circle", "arc")
SYMBOL_MODES = ("auto", "drawn")
PLANES = ("xy", "xz", "yz")
AXES = ("z", "x", "y")
HANDLE_SIDES = ("start", "end", "symmetric")
MAX_NESTING = 3

# Parâmetros que toda definição tem (§3.1): identificador → (rótulo, tipo, nível).
BUILTIN = {"elevacao": ("Elevação", "length", "occurrence"),
           "codigo": ("Código", "text", "type"),
           "descricao": ("Descrição", "text", "type")}

_NAME = re.compile(r"^[^\W\d_][\w]*$")
# Campos numéricos de cada peça: nome → padrão.
_PIECE_FIELDS = {
    "box": {"x": 0.0, "y": 0.0, "z": 0.0, "width": 0.5, "depth": 0.5, "height": 0.5,
            "rotation": 0.0},
    "cylinder": {"x": 0.0, "y": 0.0, "z": 0.0, "radius": 0.25, "height": 0.5},
    "extrusion": {"offset": 0.0, "thickness": 0.1},
    "revolution": {"x": 0.0, "y": 0.0, "z": 0.0, "angle": 360.0},
    "object": {"x": 0.0, "y": 0.0, "z": 0.0, "rotation": 0.0},
}
_SYMBOL_FIELDS = {
    "line": {}, "polyline": {},
    "rect": {"x": 0.0, "y": 0.0, "width": 0.5, "depth": 0.5, "rotation": 0.0},
    "circle": {"x": 0.0, "y": 0.0, "radius": 0.25},
    "arc": {"x": 0.0, "y": 0.0, "radius": 0.25, "start": 0.0, "end": 90.0},
}
_CIRCLE_STEPS = 48


@dataclass(frozen=True)
class Problem:
    """Erro de uma definição, com o lugar (para o editor marcar a linha, §5.3)."""
    where: tuple  # ("param", i) | ("piece", i, campo) | ("symbol", i, campo) | ("object", campo)
    message: str


# --- padrões ---------------------------------------------------------------------------


def new_param(name: str, kind: str = "length", level: str = "type", value=None,
              **extra) -> dict:
    label = extra.pop("label", None) or name.replace("_", " ").capitalize()
    param = {"name": name, "label": label, "kind": kind, "level": level, "value": value,
             "formula": None, "min": None, "max": None,
             "group": "Dimensões" if KINDS[kind] == NUMBER else (
                 "Materiais" if kind == "material" else (
                     "Visibilidade" if kind == "bool" else "Outros")),
             "options": None, "accepts": None, "handle": None}
    param.update(extra)
    if param["value"] is None and param["formula"] is None:
        param["value"] = default_value(param)
    return param


def default_value(param: dict):
    kind = param["kind"]
    if KINDS[kind] == NUMBER:
        return 0.0 if kind != "integer" else 1
    if kind == "bool":
        return False
    if kind == "choice":
        return (param.get("options") or [""])[0]
    return ""


def new_piece(kind: str, **values) -> dict:
    piece = {"kind": kind, "name": "", **copy.deepcopy(_PIECE_FIELDS[kind]),
             "role": None, "material": None, "visible": None, "repeat": None}
    if kind == "box":
        piece["void"] = False
    if kind == "cylinder":
        piece["axis"] = "z"
    if kind == "extrusion":
        piece.update(plane="xy", points=[[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5]])
    if kind == "revolution":
        piece["points"] = [[0, 0], [0.25, 0], [0.25, 0.5], [0, 0.5]]
    if kind == "object":
        piece.update(type=None, mirror=False, values={})
    piece.update(values)
    return piece


def new_symbol_item(kind: str, **values) -> dict:
    item = {"kind": kind, **copy.deepcopy(_SYMBOL_FIELDS[kind]), "fill": False,
            "visible": None, "repeat": None}
    if kind in ("line", "polyline"):
        item["points"] = [[0, 0], [0.5, 0]]
        item["closed"] = False
    item.update(values)
    return item


def new_definition(name: str, category: str = "furniture", **values) -> dict:
    from brasbim.core import guid

    defn = {"object_id": guid.new(), "version": 1, "name": name, "category": category,
            "predefined_type": PREDEFINED[category][-1] if category != "vegetation"
            else "VEGETATION", "element_type": None, "hosting": "free", "elevation": 0.0,
            "description": "", "params": [], "pieces": [],
            "symbol": {"mode": "auto", "items": []}}
    defn.update(values)
    return normalized(defn)


def normalized(defn: dict) -> dict:
    """Cópia com os parâmetros embutidos (§3.1) e os campos que faltam."""
    out = copy.deepcopy(defn)
    out.setdefault("version", 1)
    out.setdefault("element_type", None)
    out.setdefault("hosting", "free")
    out.setdefault("elevation", 0.0)
    out.setdefault("description", "")
    out.setdefault("symbol", {"mode": "auto", "items": []})
    params = out.setdefault("params", [])
    have = {fm.key(p["name"]) for p in params}
    for name, (label, kind, level) in BUILTIN.items():
        if name not in have:
            value = float(out["elevation"]) if name == "elevacao" else ""
            params.append(new_param(name, kind, level, value, label=label,
                                    group="Outros" if name != "elevacao" else "Dimensões"))
    for p in params:
        for k, v in new_param(p["name"], p["kind"], p["level"], p.get("value")).items():
            p.setdefault(k, v)
    for piece in out.setdefault("pieces", []):
        for k, v in new_piece(piece["kind"]).items():
            piece.setdefault(k, v)
    for item in out["symbol"].setdefault("items", []):
        for k, v in new_symbol_item(item["kind"]).items():
            item.setdefault(k, v)
    return out


def classes(defn: dict) -> tuple[str, str]:
    """(classe da ocorrência, classe do tipo)."""
    occ, typ, _, _ = CATEGORIES[defn["category"]]
    return occ, typ


def param(defn: dict, name: str) -> dict | None:
    k = fm.key(name)
    return next((p for p in defn["params"] if fm.key(p["name"]) == k), None)


def is_builtin(p: dict) -> bool:
    return fm.key(p["name"]) in BUILTIN


def type_params(defn: dict) -> list[dict]:
    return [p for p in defn["params"] if p["level"] == "type"]


def occurrence_params(defn: dict) -> list[dict]:
    return [p for p in defn["params"] if p["level"] == "occurrence"]


def editable(p: dict) -> bool:
    """Parâmetro com valor (sem fórmula): o tipo ou a ocorrência guardam o valor."""
    return not p.get("formula")


# --- validação -------------------------------------------------------------------------


def _field_text(value) -> str | None:
    """Texto da fórmula de um campo, ou ``None`` se for número (ou vazio)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None
    text = str(value).strip()
    return text or None


def _types(defn: dict) -> dict[str, str]:
    return {fm.key(p["name"]): KINDS[p["kind"]] for p in defn["params"]
            if p["kind"] in KINDS}


def _check_field(out: list, where: tuple, value, types: dict, want: str,
                 allow_empty: bool = False) -> set[str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        if not allow_empty:
            out.append(Problem(where, "campo vazio"))
        return set()
    if isinstance(value, bool):
        if want != BOOL:
            out.append(Problem(where, "esperado número ou fórmula"))
        return set()
    if isinstance(value, (int, float)):
        if want != NUMBER:
            out.append(Problem(where, "esperado sim/não ou fórmula"))
        return set()
    try:
        node = fm.parse(str(value))
        got = fm.infer(node, types)
    except FormulaError as e:
        out.append(Problem(where, str(e)))
        return set()
    if got != want:
        out.append(Problem(where, f"a fórmula dá {_noun(got)}, esperado {_noun(want)}"))
    return fm.names(node)


def _noun(kind: str) -> str:
    return {NUMBER: "número", BOOL: "sim/não", TEXT: "texto"}[kind]


def _value_ok(p: dict, value) -> str | None:
    kind = p["kind"]
    if KINDS[kind] == NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return "valor deve ser um número"
        if kind == "integer" and abs(value - round(value)) > 1e-9:
            return "valor deve ser inteiro"
        if p.get("min") is not None and value < p["min"] - 1e-9:
            return f"{p['label']}: {fmt(value)} abaixo do mínimo {fmt(p['min'])}"
        if p.get("max") is not None and value > p["max"] + 1e-9:
            return f"{p['label']}: {fmt(value)} acima do máximo {fmt(p['max'])}"
        return None
    if kind == "bool":
        return None if isinstance(value, bool) else "valor deve ser sim ou não"
    if not isinstance(value, str):
        return "valor deve ser texto"
    if kind == "choice" and value not in (p.get("options") or []):
        return f"{p['label']}: '{value}' não está nas opções"
    return None


def fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _cycles(deps: dict[str, set[str]]) -> list[list[str]]:
    """Ciclos de dependência (cada um uma vez, pelo primeiro nome em que é achado)."""
    state, stack, found = {}, [], []

    def visit(n):
        state[n] = 1
        stack.append(n)
        for m in sorted(deps.get(n, ())):
            if m not in deps:
                continue
            if state.get(m) == 1:
                found.append(stack[stack.index(m):] + [m])
            elif m not in state:
                visit(m)
        stack.pop()
        state[n] = 2

    for n in sorted(deps):
        if n not in state:
            visit(n)
    return found


def problems(defn: dict) -> list[Problem]:
    """Todos os erros da definição (vazio = válida)."""
    out: list[Problem] = []
    defn = normalized(defn)
    if not str(defn.get("name") or "").strip():
        out.append(Problem(("object", "name"), "o objeto precisa de um nome"))
    if defn["category"] not in CATEGORIES:
        out.append(Problem(("object", "category"), f"categoria inválida: {defn['category']}"))
        return out
    if defn["predefined_type"] not in PREDEFINED[defn["category"]]:
        out.append(Problem(("object", "predefined_type"),
                           f"tipo predefinido inválido: {defn['predefined_type']}"))
    if defn["hosting"] not in HOSTING:
        out.append(Problem(("object", "hosting"), f"hospedagem inválida: {defn['hosting']}"))
    seen, labels = {}, {}
    for i, p in enumerate(defn["params"]):
        name = str(p.get("name") or "")
        if not _NAME.match(name):
            out.append(Problem(("param", i), f"identificador inválido: '{name}' (letras, "
                                             "dígitos e _, começando por letra)"))
        elif fm.key(name) in fm._KEYWORDS or fm.key(name) in fm._LITERALS \
                or fm.key(name) in fm._FUNCTIONS:
            out.append(Problem(("param", i), f"'{name}' é palavra reservada das fórmulas"))
        elif fm.key(name) in seen:
            out.append(Problem(("param", i), f"identificador repetido: {name}"))
        seen.setdefault(fm.key(name), i)
        label = str(p.get("label") or "").strip()
        if not label:
            out.append(Problem(("param", i), "o parâmetro precisa de um rótulo"))
        elif label.casefold() in labels:
            out.append(Problem(("param", i), f"rótulo repetido: {label}"))
        labels.setdefault(label.casefold(), i)
        if p.get("kind") not in KINDS:
            out.append(Problem(("param", i), f"tipo de valor inválido: {p.get('kind')}"))
            continue
        if p.get("level") not in LEVELS:
            out.append(Problem(("param", i), f"nível inválido: {p.get('level')}"))
        if is_builtin(p):
            label_, kind, level = BUILTIN[fm.key(name)]
            if p["kind"] != kind or p["level"] != level:
                out.append(Problem(("param", i), f"{label_}: tipo e nível são fixos"))
        if p["kind"] == "choice" and not p.get("options"):
            out.append(Problem(("param", i), "a escolha precisa de pelo menos uma opção"))
        if p.get("handle"):
            h = p["handle"]
            if p["kind"] != "length" or p["level"] != "occurrence" or p.get("formula"):
                out.append(Problem(("param", i), "alça só em comprimento de ocorrência "
                                                 "sem fórmula"))
            elif h.get("axis") not in AXES or h.get("side") not in HANDLE_SIDES:
                out.append(Problem(("param", i), "alça inválida"))
    types = _types(defn)
    levels = {fm.key(p["name"]): p.get("level") for p in defn["params"]}
    deps: dict[str, set[str]] = {}
    for i, p in enumerate(defn["params"]):
        if p.get("kind") not in KINDS:
            continue
        k = fm.key(str(p.get("name") or ""))
        if p.get("formula"):
            before = len(out)
            used = _check_field(out, ("param", i), p["formula"], types, KINDS[p["kind"]])
            if len(out) > before:
                continue
            deps[k] = used
            if p["level"] == "type":
                bad = sorted(n for n in used if levels.get(n) == "occurrence")
                if bad:
                    out.append(Problem(("param", i), "parâmetro de tipo não pode depender de "
                                                     f"parâmetro de ocorrência ({bad[0]})"))
        else:
            deps[k] = set()
            message = _value_ok(p, p.get("value"))
            if message:
                out.append(Problem(("param", i), message))
    for cycle in _cycles(deps):
        index = seen.get(cycle[0], 0)
        out.append(Problem(("param", index), "ciclo nas fórmulas: " + " → ".join(cycle)))
    roles = ROLES[defn["category"]]
    for i, piece in enumerate(defn["pieces"]):
        kind = piece.get("kind")
        if kind not in PIECE_KINDS:
            out.append(Problem(("piece", i, "kind"), f"peça inválida: {kind}"))
            continue
        for name in _PIECE_FIELDS[kind]:
            _check_field(out, ("piece", i, name), piece.get(name), types, NUMBER)
        _check_field(out, ("piece", i, "visible"), piece.get("visible"), types, BOOL,
                     allow_empty=True)
        _check_repeat(out, ("piece", i), piece.get("repeat"), types)
        if kind in ("extrusion", "revolution"):
            _check_points(out, ("piece", i), piece.get("points"), types)
        if kind == "extrusion" and piece.get("plane") not in PLANES:
            out.append(Problem(("piece", i, "plane"), "plano inválido"))
        if kind == "cylinder" and piece.get("axis") not in AXES:
            out.append(Problem(("piece", i, "axis"), "eixo inválido"))
        if kind == "object":
            _check_nested(out, i, piece, defn, types)
            continue
        if piece.get("role") is not None and piece["role"] not in roles:
            out.append(Problem(("piece", i, "role"), f"papel inválido: {piece['role']}"))
        material = piece.get("material")
        if isinstance(material, dict):
            p = param(defn, material.get("param") or "")
            if p is None or p["kind"] != "material":
                out.append(Problem(("piece", i, "material"),
                                   "o material vem de um parâmetro do tipo material"))
        if piece.get("void"):
            if kind != "box":
                out.append(Problem(("piece", i, "void"), "só uma caixa pode ser o vão"))
            elif defn["hosting"] != "wall":
                out.append(Problem(("piece", i, "void"),
                                   "vão na parede só em objeto preso à parede"))
    symbol = defn.get("symbol") or {}
    if symbol.get("mode", "auto") not in SYMBOL_MODES:
        out.append(Problem(("object", "symbol"), "modo do símbolo inválido"))
    for i, item in enumerate(symbol.get("items") or []):
        kind = item.get("kind")
        if kind not in SYMBOL_KINDS:
            out.append(Problem(("symbol", i, "kind"), f"primitiva inválida: {kind}"))
            continue
        for name in _SYMBOL_FIELDS[kind]:
            _check_field(out, ("symbol", i, name), item.get(name), types, NUMBER)
        if kind in ("line", "polyline"):
            _check_points(out, ("symbol", i), item.get("points"), types, minimum=2)
        _check_field(out, ("symbol", i, "visible"), item.get("visible"), types, BOOL,
                     allow_empty=True)
        _check_repeat(out, ("symbol", i), item.get("repeat"), types)
    return out


def _check_points(out, where, points, types, minimum: int = 3) -> None:
    if not isinstance(points, list) or len(points) < minimum:
        out.append(Problem((*where, "points"), f"o perfil precisa de pelo menos {minimum} "
                                                "pontos"))
        return
    for j, pt in enumerate(points):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            out.append(Problem((*where, "points"), f"ponto {j + 1} inválido"))
            continue
        for c in pt:
            _check_field(out, (*where, "points"), c, types, NUMBER)


def _check_repeat(out, where, repeat, types) -> None:
    if not repeat:
        return
    for name in ("count", "dx", "dy", "dz", "length"):
        if name in repeat:
            _check_field(out, (*where, "repeat"), repeat[name], types, NUMBER,
                         allow_empty=name != "count")


def _check_nested(out, i, piece, defn, types) -> None:
    ref = piece.get("type")
    if isinstance(ref, dict):
        p = param(defn, ref.get("param") or "")
        if p is None or p["kind"] != "object_type":
            out.append(Problem(("piece", i, "type"),
                               "o tipo aninhado vem de um parâmetro do tipo 'tipo de objeto'"))
    elif not ref:
        out.append(Problem(("piece", i, "type"), "escolha o tipo do objeto aninhado"))
    for value in (piece.get("values") or {}).values():
        _check_field(out, ("piece", i, "values"), value, types,
                     BOOL if isinstance(value, bool) else NUMBER if isinstance(
                         value, (int, float)) else _guess(value, types))


def _guess(value, types) -> str:
    """Tipo de uma fórmula de ligação (o tipo certo é conferido ao montar o aninhado)."""
    try:
        return fm.infer(fm.parse(str(value)), types)
    except FormulaError:
        return NUMBER


def validate(defn: dict) -> None:
    found = problems(defn)
    if found:
        raise OpError(found[0].message)


# --- cálculo ---------------------------------------------------------------------------


def _coerce(p: dict, value):
    kind = p["kind"]
    if kind == "integer":
        return round(float(value))
    if KINDS[kind] == NUMBER:
        return float(value)
    if kind == "bool":
        return bool(value)
    return "" if value is None else str(value)


def _order(defn: dict, wanted: list[dict]) -> list[dict]:
    """Parâmetros em ordem de dependência (recusa ciclo)."""
    by_key = {fm.key(p["name"]): p for p in wanted}
    deps = {k: (fm.names(fm.parse(p["formula"])) & by_key.keys()) if p.get("formula")
            else set() for k, p in by_key.items()}
    cycles = _cycles(deps)
    if cycles:
        raise FormulaError("ciclo nas fórmulas: " + " → ".join(cycles[0]))
    done, out = set(), []

    def visit(k):
        if k in done:
            return
        done.add(k)
        for m in sorted(deps[k]):
            visit(m)
        out.append(by_key[k])

    for p in wanted:
        visit(fm.key(p["name"]))
    return out


def evaluate(defn: dict, type_values: dict | None = None,
             occurrence_values: dict | None = None, level: str = "occurrence") -> dict:
    """Valores de todos os parâmetros (identificador normalizado → valor).

    ``type_values``/``occurrence_values``: valores guardados (pelo identificador); o que
    falta vem do padrão da definição. ``level="type"`` calcula só os de tipo. Valor fora
    dos limites, ou fórmula que não pode ser calculada, recusa com ``FormulaError``.
    """
    stored = {fm.key(k): v for k, v in (type_values or {}).items()}
    stored.update({fm.key(k): v for k, v in (occurrence_values or {}).items()})
    wanted = [p for p in defn["params"] if level == "occurrence" or p["level"] == "type"]
    values: dict = {}
    for p in _order(defn, wanted):
        k = fm.key(p["name"])
        try:
            if p.get("formula"):
                raw = fm.evaluate(fm.parse(p["formula"]), values)
            else:
                raw = stored.get(k, p.get("value"))
                if raw is None:
                    raw = default_value(p)
            value = _coerce(p, raw)
        except (TypeError, ValueError) as e:
            raise FormulaError(f"{p['label']}: valor inválido ({e})") from None
        except FormulaError as e:
            raise FormulaError(f"{p['label']}: {e}") from None
        message = _value_ok(p, value)
        if message:
            raise FormulaError(message)
        values[k] = value
    return values


def num(value, values: dict, label: str = "") -> float:
    """Valor numérico de um campo (número ou fórmula)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0.0
    try:
        result = fm.calc(value, values) if not isinstance(value, (int, float)) else value
    except FormulaError as e:
        raise FormulaError(f"{label}: {e}" if label else str(e)) from None
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise FormulaError(f"{label}: esperado número")
    return float(result)


def truth(value, values: dict) -> bool:
    if value is None or (isinstance(value, str) and not value.strip()):
        return True
    if isinstance(value, bool):
        return value
    return bool(fm.calc(value, values))


def _copies(item: dict, values: dict, label: str) -> list[tuple[float, float, float]]:
    """Deslocamentos de cada cópia de uma peça repetida (§3.3)."""
    repeat = item.get("repeat")
    if not repeat:
        return [(0.0, 0.0, 0.0)]
    count = round(num(repeat.get("count", 1), values, label))
    if count < 0:
        raise FormulaError(f"{label}: quantidade negativa")
    if count > 500:
        raise FormulaError(f"{label}: mais de 500 cópias")
    d = [num(repeat.get(k, 0), values, label) for k in ("dx", "dy", "dz")]
    if repeat.get("length") not in (None, ""):
        length = num(repeat["length"], values, label)
        norm = math.sqrt(sum(c * c for c in d))
        if norm < 1e-12:
            raise FormulaError(f"{label}: distribuir pede uma direção")
        step = length / (count - 1) if count > 1 else 0.0
        d = [c / norm * step for c in d]
    return [(d[0] * n, d[1] * n, d[2] * n) for n in range(count)]


@dataclass
class Solid:
    """Uma peça calculada, no sistema local do objeto."""
    kind: str  # box | cylinder | extrusion | revolution
    dims: dict
    origin: tuple[float, float, float]
    rotation: float = 0.0  # graus em torno de z, no ponto ``origin`` (caixa)
    material: str | None = None
    role: str | None = None
    piece: int = 0
    copy: int = 0
    name: str = ""
    void: bool = False
    points: list = field(default_factory=list)


@dataclass
class Nested:
    """Um objeto aninhado calculado (§6.4)."""
    type_name: str
    origin: tuple[float, float, float]
    rotation: float
    mirror: bool
    values: dict
    piece: int
    copy: int


def _label(piece: dict, i: int) -> str:
    return piece.get("name") or f"peça {i + 1}"


def _material(defn: dict, piece: dict, values: dict) -> str | None:
    m = piece.get("material")
    if isinstance(m, dict):
        return values.get(fm.key(m.get("param") or "")) or None
    return m or None


def _area(points) -> float:
    return 0.5 * sum(points[i][0] * points[(i + 1) % len(points)][1]
                     - points[(i + 1) % len(points)][0] * points[i][1]
                     for i in range(len(points)))


def solids(defn: dict, values: dict) -> list[Solid]:
    """Peças visíveis, com a repetição expandida e as medidas calculadas."""
    out = []
    for i, piece in enumerate(defn["pieces"]):
        kind = piece["kind"]
        if kind == "object":
            continue
        label = _label(piece, i)
        if not truth(piece.get("visible"), values):
            continue
        dims = {k: num(piece.get(k, v), values, label)
                for k, v in _PIECE_FIELDS[kind].items()}
        if kind == "cylinder":
            dims["axis"] = piece.get("axis") or "z"
        if kind == "extrusion":
            dims["plane"] = piece.get("plane") or "xy"
        points = []
        if kind in ("extrusion", "revolution"):
            points = [(num(a, values, label), num(b, values, label))
                      for a, b in piece.get("points") or []]
        _check_solid(kind, dims, points, label, piece)
        material = _material(defn, piece, values)
        for n, (dx, dy, dz) in enumerate(_copies(piece, values, label)):
            if kind in ("box", "cylinder", "revolution"):
                origin = (dims["x"] + dx, dims["y"] + dy, dims["z"] + dz)
            else:
                origin = (dx, dy, dz)
            out.append(Solid(kind, dims, origin, dims.get("rotation", 0.0), material,
                             piece.get("role"), i, n, piece.get("name") or "",
                             bool(piece.get("void")), points))
    return out


def _check_solid(kind: str, dims: dict, points: list, label: str, piece: dict) -> None:
    def positive(*names):
        for name in names:
            if dims[name] <= 1e-6:
                raise FormulaError(f"{label}: medida ≤ 0 ({name} = {fmt(dims[name])})")

    if kind == "box":
        positive("width", "depth", "height")
    elif kind == "cylinder":
        positive("radius", "height")
    elif kind == "extrusion":
        positive("thickness")
        if len(points) < 3 or abs(_area(points)) < 1e-8:
            raise FormulaError(f"{label}: perfil sem área")
    elif kind == "revolution":
        if not 0 < dims["angle"] <= 360 + 1e-9:
            raise FormulaError(f"{label}: ângulo da revolução fora de (0, 360]")
        if len(points) < 3 or abs(_area(points)) < 1e-8:
            raise FormulaError(f"{label}: perfil sem área")
        if any(r < -1e-9 for r, _ in points):
            raise FormulaError(f"{label}: o perfil da revolução fica do lado x ≥ 0")


def nested(defn: dict, values: dict) -> list[Nested]:
    """Objetos aninhados visíveis (§6.4). ``values`` de cada um: as ligações calculadas."""
    out = []
    for i, piece in enumerate(defn["pieces"]):
        if piece["kind"] != "object":
            continue
        label = _label(piece, i)
        if not truth(piece.get("visible"), values):
            continue
        ref = piece.get("type")
        type_name = values.get(fm.key(ref.get("param") or "")) if isinstance(ref, dict) \
            else ref
        if not type_name:
            continue
        dims = {k: num(piece.get(k, v), values, label)
                for k, v in _PIECE_FIELDS["object"].items()}
        mirror = truth(piece.get("mirror") or False, values) if piece.get("mirror") else False
        links = {}
        for name, value in (piece.get("values") or {}).items():
            links[name] = value if isinstance(value, (bool, int, float)) else fm.calc(
                value, values)
        for n, (dx, dy, dz) in enumerate(_copies(piece, values, label)):
            out.append(Nested(type_name, (dims["x"] + dx, dims["y"] + dy, dims["z"] + dz),
                              dims["rotation"], mirror, dict(links), i, n))
    return out


def nested_refs(defn: dict) -> set[str]:
    """Nomes de tipos que a definição pode aninhar (fixos e opções dos parâmetros)."""
    out = set()
    for piece in defn["pieces"]:
        if piece["kind"] != "object":
            continue
        ref = piece.get("type")
        if isinstance(ref, dict):
            p = param(defn, ref.get("param") or "")
            if p is not None and p.get("value"):
                out.add(p["value"])
        elif ref:
            out.add(ref)
    return out


# --- geometria em planta -----------------------------------------------------------------


def _rot(p, angle: float, center=(0.0, 0.0)):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    x, y = p[0] - center[0], p[1] - center[1]
    return (center[0] + c * x - s * y, center[1] + s * x + c * y)


def _circle(cx: float, cy: float, r: float, a0: float = 0.0, a1: float = 360.0,
            steps: int = _CIRCLE_STEPS) -> list[tuple[float, float]]:
    n = max(2, math.ceil(steps * abs(a1 - a0) / 360.0))
    full = abs(a1 - a0) >= 360 - 1e-9
    count = n if full else n + 1
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(count)]


def footprint(s: Solid) -> list[tuple[float, float]]:
    """Contorno da peça vista de cima (anti-horário), no sistema local."""
    ox, oy, _ = s.origin
    d = s.dims
    if s.kind == "box":
        corners = [(0, 0), (d["width"], 0), (d["width"], d["depth"]), (0, d["depth"])]
        return [(ox + x, oy + y) for x, y in (_rot(c, s.rotation) for c in corners)]
    if s.kind == "cylinder":
        axis = s.dims.get("axis", "z")
        if axis == "z":
            return _circle(ox, oy, d["radius"])
        if axis == "x":
            return [(ox, oy - d["radius"]), (ox + d["height"], oy - d["radius"]),
                    (ox + d["height"], oy + d["radius"]), (ox, oy + d["radius"])]
        return [(ox - d["radius"], oy), (ox + d["radius"], oy),
                (ox + d["radius"], oy + d["height"]), (ox - d["radius"], oy + d["height"])]
    if s.kind == "revolution":
        r = max(p[0] for p in s.points)
        if d["angle"] >= 360 - 1e-9:
            return _circle(ox, oy, r)
        return [(ox, oy), *_circle(ox, oy, r, 0.0, d["angle"])]
    plane = s.dims.get("plane", "xy")
    t0, t1 = d["offset"], d["offset"] + d["thickness"]
    pts = s.points
    if plane == "xy":
        ring = [(ox + a, oy + b) for a, b in pts]
        return ring if _area(ring) > 0 else ring[::-1]
    a0, a1 = min(p[0] for p in pts), max(p[0] for p in pts)
    if plane == "xz":
        return [(ox + a0, oy + t0), (ox + a1, oy + t0), (ox + a1, oy + t1), (ox + a0, oy + t1)]
    return [(ox + t0, oy + a0), (ox + t1, oy + a0), (ox + t1, oy + a1), (ox + t0, oy + a1)]


def z_range(s: Solid) -> tuple[float, float]:
    z0 = s.origin[2]
    d = s.dims
    if s.kind == "box":
        return z0, z0 + d["height"]
    if s.kind == "cylinder":
        axis = d.get("axis", "z")
        if axis == "z":
            return z0, z0 + d["height"]
        return z0 - d["radius"], z0 + d["radius"]
    if s.kind == "revolution":
        zs = [p[1] for p in s.points]
        return z0 + min(zs), z0 + max(zs)
    plane = d.get("plane", "xy")
    if plane == "xy":
        return z0 + d["offset"], z0 + d["offset"] + d["thickness"]
    zs = [p[1] for p in s.points]
    return z0 + min(zs), z0 + max(zs)


def bounds(found: list[Solid]) -> tuple[float, float, float, float, float, float] | None:
    """Caixa que envolve as peças (sem o vão): (xmin, xmax, ymin, ymax, zmin, zmax)."""
    pts, zs = [], []
    for s in found:
        if s.void:
            continue
        pts.extend(footprint(s))
        zs.extend(z_range(s))
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


@dataclass
class Stroke:
    """Primitiva do símbolo 2D, no sistema local: polilinha (aberta ou fechada)."""
    points: list[tuple[float, float]]
    closed: bool = False
    fill: bool = False


def symbol_items(defn: dict, values: dict) -> list[Stroke]:
    """Primitivas do símbolo desenhado (§7). O automático é montado em ``objects.plan``."""
    out = []
    for i, item in enumerate((defn.get("symbol") or {}).get("items") or []):
        label = f"símbolo {i + 1}"
        if not truth(item.get("visible"), values):
            continue
        d = {k: num(item.get(k, v), values, label) for k, v in _SYMBOL_FIELDS[
            item["kind"]].items()}
        for dx, dy, _ in _copies(item, values, label):
            kind = item["kind"]
            if kind in ("line", "polyline"):
                pts = [(num(a, values, label) + dx, num(b, values, label) + dy)
                       for a, b in item.get("points") or []]
                closed = bool(item.get("closed")) and kind == "polyline"
                out.append(Stroke(pts, closed, bool(item.get("fill")) and closed))
            elif kind == "rect":
                corners = [(0, 0), (d["width"], 0), (d["width"], d["depth"]), (0, d["depth"])]
                pts = [(d["x"] + dx + x, d["y"] + dy + y)
                       for x, y in (_rot(c, d["rotation"]) for c in corners)]
                out.append(Stroke(pts, True, bool(item.get("fill"))))
            elif kind == "circle":
                if d["radius"] <= 1e-6:
                    raise FormulaError(f"{label}: raio ≤ 0")
                out.append(Stroke(_circle(d["x"] + dx, d["y"] + dy, d["radius"]), True,
                                  bool(item.get("fill"))))
            else:
                if d["radius"] <= 1e-6:
                    raise FormulaError(f"{label}: raio ≤ 0")
                out.append(Stroke(_circle(d["x"] + dx, d["y"] + dy, d["radius"], d["start"],
                                          d["end"]), False))
    return out


# --- alças ---------------------------------------------------------------------------------


def handle_params(defn: dict) -> list[dict]:
    return [p for p in defn["params"] if p.get("handle") and p["level"] == "occurrence"
            and p["kind"] == "length" and not p.get("formula")]


def handle_shift(defn: dict, type_values: dict, occ_values: dict, name: str,
                 new_value: float) -> tuple[float, float, float]:
    """Deslocamento local do ponto de inserção para a alça de ``name`` (§5.1): o lado
    oposto (ou o centro, na simétrica) da caixa que envolve fica no lugar."""
    p = param(defn, name)
    axis = "xyz".index(p["handle"]["axis"])
    side = p["handle"]["side"]
    before = bounds(solids(defn, evaluate(defn, type_values, occ_values)))
    after = bounds(solids(defn, evaluate(defn, type_values,
                                         {**occ_values, p["name"]: new_value})))
    if before is None or after is None:
        return (0.0, 0.0, 0.0)
    lo0, hi0 = before[2 * axis], before[2 * axis + 1]
    lo1, hi1 = after[2 * axis], after[2 * axis + 1]
    if side == "end":
        delta = lo0 - lo1
    elif side == "start":
        delta = hi0 - hi1
    else:
        delta = (lo0 + hi0) / 2 - (lo1 + hi1) / 2
    shift = [0.0, 0.0, 0.0]
    shift[axis] = delta
    return tuple(shift)
