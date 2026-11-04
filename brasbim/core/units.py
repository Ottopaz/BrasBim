# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unidades e casas decimais do projeto (``spec/ui/44-unidades-do-projeto.md``).

Só muda o **texto** das medidas no desenho (cotas, nível, elevação, esquadrias, área);
o modelo continua em metros. Configuração no Pset ``BrasBim_Unidades`` do ``IfcProject``
(propriedade ``Config``, JSON); sem ele, o padrão (o mesmo texto de antes).

Operação: ``units.set`` (``id`` = projeto; ``before``/``after`` = {"config": ...}).
"""

from __future__ import annotations

import copy
import json

import ifcopenshell.util.element

from brasbim.core import props
from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, invert_swap, register

PSET = "BrasBim_Unidades"
MAX_DECIMALS = 4

LENGTH_UNITS = {"m": ("m", 1.0), "cm": ("cm", 100.0), "mm": ("mm", 1000.0)}
AREA_UNITS = {"m2": ("m²", 1.0), "cm2": ("cm²", 1e4)}
ANGLE_UNITS = {"deg": "graus decimais", "dms": "graus, minutos e segundos"}
UNIT_LABELS = {"m": "metros", "cm": "centímetros", "mm": "milímetros", "m2": "m²",
               "cm2": "cm²", **ANGLE_UNITS}

# (chave, nome, onde aparece, unidades possíveis, padrão)
KINDS = (
    ("work", "Medidas de trabalho",
     "o que se digita e lê: ficha, barra Opções, quadro de medidas e linha de comando",
     tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("linear", "Cota linear", "cotas e cotas automáticas da parede", tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("radius", "Raio e diâmetro", "cota de raio (R, Ø)", tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("angle", "Ângulo", "cota de ângulo", tuple(ANGLE_UNITS),
     {"unit": "deg", "decimals": 1, "show_unit": True, "hide_zeros": False}),
    ("level", "Cota de nível", "marca de nível na planta", tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("elevation", "Cota em elevação", "níveis nos cortes e fachadas", tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("opening", "Esquadrias", "etiqueta L × A / peitoril na planta", tuple(LENGTH_UNITS),
     {"unit": "m", "decimals": 2, "show_unit": False, "hide_zeros": False}),
    ("area", "Área", "área dos ambientes na planta", tuple(AREA_UNITS),
     {"unit": "m2", "decimals": 2, "show_unit": True, "hide_zeros": False}),
)
KIND_KEYS = tuple(k for k, *_ in KINDS)
DEFAULTS = {k: d for k, _, _, _, d in KINDS}
_ALLOWED = {k: units for k, _, _, units, _ in KINDS}

# Padrões prontos da barra da vista (§2): mudam as medidas de trabalho, a cota linear, o
# raio e as esquadrias. No trabalho em cm fica uma casa (o milímetro), sem zeros finais.
PRESET_KINDS = ("work", "linear", "radius", "opening")


def _preset(unit: str, decimals: int, work: dict) -> dict:
    same = {"unit": unit, "decimals": decimals}
    return {"work": {"unit": unit, **work}, "linear": same, "radius": same, "opening": same}


PRESETS = (
    ("meters", "Metros, 2 casas (projeto legal)",
     _preset("m", 2, {"decimals": 2, "hide_zeros": False})),
    ("centimeters", "Centímetros, sem casas (executivo)",
     _preset("cm", 0, {"decimals": 1, "hide_zeros": True})),
    ("millimeters", "Milímetros, sem casas", _preset("mm", 0, {"decimals": 0,
                                                              "hide_zeros": False})),
)


# --- configuração ----------------------------------------------------------------------


def default_config() -> dict:
    return copy.deepcopy(DEFAULTS)


def normalized(config: dict | None) -> dict:
    """Configuração completa: o que falta vem do padrão."""
    out = default_config()
    for key, values in (config or {}).items():
        if key in out and isinstance(values, dict):
            out[key].update({k: v for k, v in values.items() if k in out[key]})
    return out


def validate(config: dict) -> None:
    for key, values in config.items():
        if key not in DEFAULTS:
            raise OpError(f"tipo de medida desconhecido: {key!r}")
        if values["unit"] not in _ALLOWED[key]:
            raise OpError(f"unidade {values['unit']!r} não serve para {key}")
        if not isinstance(values["decimals"], int) or not 0 <= values["decimals"] <= MAX_DECIMALS:
            raise OpError(f"casas decimais de 0 a {MAX_DECIMALS}")


def _project(doc: Document):
    projects = doc.ifc.by_type("IfcProject")
    if not projects:
        raise OpError("documento sem IfcProject")
    return projects[0]


def _read_pset(doc: Document) -> dict:
    values = ifcopenshell.util.element.get_pset(_project(doc), PSET, should_inherit=False)
    if not values or not values.get("Config"):
        return default_config()
    try:
        return normalized(json.loads(values["Config"]))
    except (ValueError, TypeError):
        return default_config()


def config(doc: Document) -> dict:
    """Configuração em uso (guardada no documento; a operação a atualiza)."""
    found = doc.__dict__.get("_units")
    if found is None:
        found = doc.__dict__["_units"] = _read_pset(doc)
    return found


def key(doc: Document) -> str:
    """Texto que muda quando a configuração muda (chave de caches de desenho)."""
    found = doc.__dict__.get("_units_key")
    if found is None:
        found = doc.__dict__["_units_key"] = json.dumps(config(doc), sort_keys=True)
    return found


def set_units(doc: Document, new: dict):
    """Transação "Unidades do projeto"."""
    from brasbim.core.ops.history import Transaction

    new = normalized(new)
    validate(new)
    current = config(doc)
    if new == current:
        return Transaction("Unidades do projeto", [])
    return Transaction("Unidades do projeto", [
        Op("units.set", _project(doc).GlobalId, before={"config": copy.deepcopy(current)},
           after={"config": new})])


def apply_preset(doc: Document, preset: str):
    found = [v for k, _, v in PRESETS if k == preset]
    if not found:
        raise OpError(f"padrão de unidades desconhecido: {preset!r}")
    new = copy.deepcopy(config(doc))
    for kind, values in found[0].items():
        new[kind].update(values)
    return set_units(doc, new)


def preset_of(doc: Document) -> str | None:
    """O padrão pronto que a configuração atual segue, se segue algum."""
    cfg = config(doc)
    for name, _, kinds in PRESETS:
        if all(cfg[k][f] == v for k, values in kinds.items() for f, v in values.items()):
            return name
    return None


def _apply(doc: Document, op: Op) -> set[str]:
    project = doc.get(op.id)
    current = config(doc)
    if op.before is not None and normalized(op.before.get("config")) != current:
        raise OpError("units.set: a configuração atual não é a esperada")
    new = normalized((op.after or {}).get("config"))
    validate(new)
    if new == default_config():
        props.remove_pset(doc, project, PSET)
    else:
        props.write_pset(doc, project, PSET, {
            "Config": doc.ifc.createIfcText(json.dumps(new, sort_keys=True,
                                                       ensure_ascii=False))})
    doc.__dict__["_units"] = new
    doc.__dict__.pop("_units_key", None)
    if doc.__dict__.get("_units_active"):
        activate(doc)
    return {op.id}


register("units.set", _apply, invert_swap)


# --- texto -----------------------------------------------------------------------------


def _number(value: float, decimals: int, hide_zeros: bool) -> str:
    text = f"{value:.{decimals}f}"
    if text.lstrip("-").strip("0.") == "":  # "-0,00" → "0,00"
        text = text.lstrip("-")
    if hide_zeros and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def length(doc: Document | None, kind: str, value: float, signed: bool = False) -> str:
    """Comprimento ``value`` (m) no texto do tipo ``kind``; ``signed`` põe "+"/"−"
    (cota de nível e de elevação)."""
    cfg = config(doc)[kind] if doc is not None else DEFAULTS[kind]
    symbol, factor = LENGTH_UNITS[cfg["unit"]]
    v = value * factor
    if signed:
        v = 0.0 if abs(v) < 0.5 * 10 ** -cfg["decimals"] else v
        body = _number(abs(v), cfg["decimals"], cfg["hide_zeros"])
        text = f"{'+' if v >= 0 else '−'}{body}"
    else:
        text = _number(v, cfg["decimals"], cfg["hide_zeros"])
    return f"{text} {symbol}" if cfg["show_unit"] else text


def area(doc: Document | None, value: float) -> str:
    cfg = config(doc)["area"] if doc is not None else DEFAULTS["area"]
    symbol, factor = AREA_UNITS[cfg["unit"]]
    text = _number(value * factor, cfg["decimals"], cfg["hide_zeros"])
    return f"{text} {symbol}" if cfg["show_unit"] else text


def angle(doc: Document | None, degrees: float) -> str:
    cfg = config(doc)["angle"] if doc is not None else DEFAULTS["angle"]
    mark = "°" if cfg["show_unit"] or cfg["unit"] == "dms" else ""
    if cfg["unit"] == "dms":
        sign = "−" if degrees < 0 else ""
        total = round(abs(degrees) * 3600.0, cfg["decimals"])
        d, rest = divmod(total, 3600.0)
        m, s = divmod(rest, 60.0)
        sec = _number(s, cfg["decimals"], cfg["hide_zeros"])
        whole = sec.split(",")[0]
        sec = sec.rjust(len(sec) + max(0, 2 - len(whole)), "0")
        return f"{sign}{int(d)}°{int(m):02d}'{sec}\""
    return _number(degrees, cfg["decimals"], cfg["hide_zeros"]) + mark


def summary(doc: Document) -> str:
    """Texto do botão da barra da vista: a unidade da cota linear ("m · 2 casas")."""
    cfg = config(doc)["linear"]
    n = cfg["decimals"]
    return f"{LENGTH_UNITS[cfg['unit']][0]} · {n} casa{'s' if n != 1 else ''}"


# --- medidas de trabalho (spec/ui 44 §2a) ------------------------------------------------
# A interface lê e escreve comprimentos na unidade de trabalho do projeto aberto. Como os
# campos não conhecem o documento, a sessão marca o documento ativo (``activate``).

_work = dict(DEFAULTS["work"])


def activate(doc: Document | None) -> None:
    """O documento aberto na janela: seus campos passam a usar a unidade de trabalho dele."""
    global _work
    if doc is None:
        _work = dict(DEFAULTS["work"])
        return
    doc.__dict__["_units_active"] = True
    _work = dict(config(doc)["work"])


def work_unit() -> str:
    return _work["unit"]


def work_symbol() -> str:
    return LENGTH_UNITS[_work["unit"]][0]


def to_work(value: float) -> float:
    """Metros → unidade de trabalho."""
    return value * LENGTH_UNITS[_work["unit"]][1]


def from_work(value: float) -> float:
    """Unidade de trabalho → metros."""
    return value / LENGTH_UNITS[_work["unit"]][1]


def fmt_work(value: float, exact: bool = False) -> str:
    """Comprimento ``value`` (m) no campo, na unidade de trabalho, sem o símbolo.
    ``exact``: até 4 casas além das pedidas, sem zeros sobrando (campos que voltam ao
    modelo sem perder o milímetro)."""
    v = to_work(value)
    decimals, hide = _work["decimals"], _work["hide_zeros"]
    if exact:
        text = _number(v, decimals + 4, True)
        if not hide and decimals:
            whole, _, frac = text.partition(",")
            text = f"{whole},{frac.ljust(decimals, '0')}"
        return text
    return _number(v, decimals, hide)


def unit_label(label: str) -> str:
    """Troca "(m)" no nome de um campo pela unidade de trabalho."""
    return label.replace("(m)", f"({work_symbol()})")
