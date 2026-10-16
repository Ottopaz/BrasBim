# SPDX-License-Identifier: LGPL-3.0-or-later
"""Estilos de material: cor do 3D e estilo de corte da planta
(``spec/ui/06-planta-por-camadas.md`` §4).

Operação ``material.edit``: ``id`` = nome do material (o ``IfcMaterial`` não tem
GlobalId; vale para todos os materiais com esse nome). ``before``/``after``: ``style``::

    {"color": "#CC8C6B",
     "cut": {"pattern": "lines", "background": None, "angle": 45.0, "spacing": 0.03,
             "line_color": "#2B2A27"}}

``None`` = sem estilo gravado (valem os padrões). Gravação (§4.3): uma
``IfcMaterialDefinitionRepresentation`` com um ``IfcStyledRepresentation`` no contexto
``Model``/``Body`` (``IfcSurfaceStyle`` com ``IfcSurfaceStyleShading``) e outro no
``Plan``/``Body`` (``IfcFillAreaStyle``). Estilos que o BrasBim não entende (texturas,
hachura externa, ladrilho) ficam intactos.
"""

from __future__ import annotations

import copy
import math
import zlib

import ifcopenshell

from brasbim.core.document import Document, OpError
from brasbim.core.ops.base import Op, check_before, invert_swap, register

PATTERNS = ("none", "solid", "lines", "cross")
LINE_COLOR = "#2B2A27"  # preto da planta
CUT_LINE_WEIGHT = 0.00018  # m (NBR 8403)
DEFAULT_CUT = {"pattern": "none", "background": None, "angle": 45.0, "spacing": 0.05,
               "line_color": LINE_COLOR}


def _cut(pattern: str, background=None, angle=45.0, spacing=0.05) -> dict:
    return {**DEFAULT_CUT, "pattern": pattern, "background": background, "angle": angle,
            "spacing": spacing}


# Biblioteca inicial (§4.4).
LIBRARY = {
    "Bloco cerâmico": {"color": "#CC8C6B", "cut": _cut("lines", angle=45.0, spacing=0.03)},
    "Reboco": {"color": "#DBD6CC", "cut": _cut("none")},
    "Concreto": {"color": "#B3B3AD", "cut": _cut("solid", background="#8A8A85")},
    "Gesso acartonado": {"color": "#EBEBE6", "cut": _cut("none")},
    "Montante de aço": {"color": "#A6ADB8", "cut": _cut("cross", angle=45.0, spacing=0.02)},
    "Madeira": {"color": "#9E7045", "cut": _cut("lines", angle=30.0, spacing=0.015)},
    "Vidro": {"color": "#A6CCE0", "cut": _cut("solid", background="#A6CCE0"),
              "transparency": 0.6},
    "Alumínio": {"color": "#C4C7CC", "cut": _cut("solid", background="#9DA1A8")},
    # Laje (spec/ui 10 §5)
    "Contrapiso": {"color": "#C7C2B8", "cut": _cut("lines", angle=45.0, spacing=0.02)},
    "Laje pré-moldada": {"color": "#BDB8AE", "cut": _cut("cross", angle=45.0, spacing=0.04)},
}
_PALETTE = ("#C9A37D", "#9EB5C7", "#A8C499", "#D4B582", "#BAA3C9", "#C99999")


def _hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def default_style(name: str | None) -> dict:
    """Estilo padrão: o da biblioteca pelo nome, ou uma cor da paleta (sempre a mesma
    para o mesmo nome) sem corte."""
    if name in LIBRARY:
        return copy.deepcopy(LIBRARY[name])
    color = _PALETTE[zlib.crc32((name or "").encode()) % len(_PALETTE)]
    return {"color": color, "cut": dict(DEFAULT_CUT)}


# --- leitura -------------------------------------------------------------------------


def named(doc: Document, name: str) -> list:
    return [m for m in doc.ifc.by_type("IfcMaterial") if m.Name == name]


def _styled(material) -> list[tuple[object, object, object]]:
    """(representação, item, estilo) de todos os estilos ligados ao material."""
    out = []
    for definition in material.HasRepresentation or []:
        for rep in definition.Representations or []:
            for item in rep.Items or []:
                if not item.is_a("IfcStyledItem"):
                    continue
                for style in item.Styles or []:
                    styles = (style.Styles if style.is_a("IfcPresentationStyleAssignment")
                              else [style])
                    out += [(rep, item, s) for s in styles]
    return out


def _is_model(rep) -> bool:
    return rep.ContextOfItems is not None and rep.ContextOfItems.ContextType == "Model"


def _is_plan(rep) -> bool:
    return rep.ContextOfItems is not None and rep.ContextOfItems.ContextType == "Plan"


def _shading(material):
    for rep, _, style in _styled(material):
        if not (style.is_a("IfcSurfaceStyle") and _is_model(rep)):
            continue
        for s in style.Styles or []:
            if s.is_a("IfcSurfaceStyleShading") and s.SurfaceColour is not None:
                return s
    return None


def _read_color(material) -> str | None:
    s = _shading(material)
    if s is None:
        return None
    c = s.SurfaceColour
    return _hex((c.Red, c.Green, c.Blue))


def surface_style(doc: Document, name: str | None):
    """``IfcSurfaceStyle`` gravado no material (para os ``IfcStyledItem`` das peças da
    esquadria, spec/ui 09 §7), ou ``None``."""
    for material in named(doc, name) if name else []:
        for rep, _, style in _styled(material):
            if style.is_a("IfcSurfaceStyle") and _is_model(rep):
                return style
    return None


def _colour(c) -> str | None:
    if c is not None and c.is_a("IfcColourRgb"):
        return _hex((c.Red, c.Green, c.Blue))
    return None


def _read_cut(material) -> dict | None:
    for rep, _, style in _styled(material):
        if not (style.is_a("IfcFillAreaStyle") and _is_plan(rep)):
            continue
        colors = [_colour(s) for s in style.FillStyles or [] if s.is_a("IfcColour")]
        hatches = [s for s in style.FillStyles or [] if s.is_a("IfcFillAreaStyleHatching")]
        background = colors[0] if colors else None
        if not hatches:
            if background is None:
                continue
            return _cut("solid", background=background)
        h = hatches[0]
        spacing = h.StartOfNextHatchLine
        spacing = (float(spacing.wrappedValue) if hasattr(spacing, "wrappedValue")
                   else DEFAULT_CUT["spacing"])
        line = (h.HatchLineAppearance.CurveColour
                if h.HatchLineAppearance is not None else None)
        return {"pattern": "cross" if len(hatches) > 1 else "lines",
                "background": background,
                "angle": round(math.degrees(float(h.HatchLineAngle)), 9),
                "spacing": spacing,
                "line_color": _colour(line) or LINE_COLOR}
    return None


def read_style(material) -> dict | None:
    """Estilo gravado no material (``None`` se não tem nenhum que o BrasBim entenda)."""
    color, cut = _read_color(material), _read_cut(material)
    if color is None and cut is None:
        return None
    base = default_style(material.Name)
    out = {"color": color or base["color"], "cut": cut or dict(DEFAULT_CUT)}
    shading = _shading(material)
    transparency = shading.Transparency if shading is not None else None
    if transparency:
        out["transparency"] = round(float(transparency), 6)
    return out


def style(doc: Document, name: str | None) -> dict:
    """Estilo do material, com os padrões; ``"default": True`` quando nada está gravado."""
    for material in named(doc, name) if name else []:
        found = read_style(material)
        if found is not None:
            return {**found, "default": False}
    return {**default_style(name), "default": True}


def state(doc: Document, name: str) -> dict:
    mats = named(doc, name)
    return {"style": read_style(mats[0]) if mats else None}


# --- gravação ------------------------------------------------------------------------


def _rgb_entity(doc: Document, color: str):
    r, g, b = rgb(color)
    return doc.ifc.createIfcColourRgb(None, r, g, b)


def _remove_rep(doc: Document, rep) -> None:
    """Apaga a representação e o que só ela usa (itens, estilos, cores), sem tocar no
    contexto."""
    pending, seen = [rep], set()
    while pending:
        entity = pending.pop()
        if not entity.id() or entity.id() in seen or entity.is_a("IfcRepresentationContext"):
            continue
        seen.add(entity.id())
        if entity is not rep and doc.ifc.get_total_inverses(entity) > 0:
            continue
        children = [v for v in entity if isinstance(v, ifcopenshell.entity_instance)]
        children += [x for v in entity if isinstance(v, (list, tuple)) for x in v
                     if isinstance(x, ifcopenshell.entity_instance)]
        doc.ifc.remove(entity)
        pending += children


def _definition(doc: Document, material):
    for definition in material.HasRepresentation or []:
        return definition
    return doc.ifc.createIfcMaterialDefinitionRepresentation(None, None, [], material)


def _attach(doc: Document, material, context, style) -> None:
    item = doc.ifc.createIfcStyledItem(None, [style], style.Name)
    rep = doc.ifc.createIfcStyledRepresentation(context, context.ContextIdentifier, None,
                                                [item])
    definition = _definition(doc, material)
    definition.Representations = [*definition.Representations, rep]


def _drop_plan(doc: Document, material) -> None:
    for rep in {rep for rep, _, s in _styled(material)
                if _is_plan(rep) and s.is_a("IfcFillAreaStyle")}:
        _detach(material, rep)
        _remove_rep(doc, rep)


def _detach(material, rep) -> None:
    for definition in material.HasRepresentation or []:
        if rep in definition.Representations:
            definition.Representations = [r for r in definition.Representations if r != rep]


def _write_color(doc: Document, material, color: str | None,
                 transparency: float = 0.0) -> None:
    surfaces = [(rep, s) for rep, _, s in _styled(material)
                if _is_model(rep) and s.is_a("IfcSurfaceStyle")]
    if color is None:
        # Só some o que é só cor; estilos com textura e outros ficam.
        for rep, s in surfaces:
            if all(x.is_a("IfcSurfaceStyleShading") for x in s.Styles or []):
                _detach(material, rep)
                _remove_rep(doc, rep)
        return
    for _, s in surfaces:
        shading = [x for x in s.Styles or [] if x.is_a("IfcSurfaceStyleShading")]
        if shading:
            old = shading[0].SurfaceColour
            shading[0].SurfaceColour = _rgb_entity(doc, color)
            shading[0].Transparency = float(transparency)
            if old is not None and not doc.ifc.get_inverse(old):
                doc.ifc.remove(old)
        else:
            s.Styles = [*s.Styles, doc.ifc.createIfcSurfaceStyleShading(
                _rgb_entity(doc, color), float(transparency))]
        return
    surface = doc.ifc.createIfcSurfaceStyle(
        material.Name, "BOTH", [doc.ifc.createIfcSurfaceStyleShading(
            _rgb_entity(doc, color), float(transparency))])
    _attach(doc, material, doc.body_context, surface)


def _hatching(doc: Document, cut: dict, angle: float):
    f = doc.ifc
    curve = f.createIfcCurveStyle(None, None, f.createIfcPositiveLengthMeasure(CUT_LINE_WEIGHT),
                                  _rgb_entity(doc, cut["line_color"]), True)
    return f.createIfcFillAreaStyleHatching(
        curve, f.createIfcPositiveLengthMeasure(float(cut["spacing"])), None, None,
        math.radians(angle))


def _write_cut(doc: Document, material, cut: dict | None) -> None:
    _drop_plan(doc, material)
    if cut is None or cut["pattern"] == "none":
        return
    fills = []
    if cut["pattern"] == "solid" or cut.get("background"):
        fills.append(_rgb_entity(doc, cut["background"]))
    if cut["pattern"] in ("lines", "cross"):
        fills.append(_hatching(doc, cut, cut["angle"]))
    if cut["pattern"] == "cross":
        fills.append(_hatching(doc, cut, cut["angle"] + 90.0))
    fill = doc.ifc.createIfcFillAreaStyle(material.Name, fills, True)
    _attach(doc, material, doc.plan_body_context, fill)


def _cleanup(doc: Document, material) -> None:
    for definition in list(material.HasRepresentation or []):
        if not definition.Representations:
            doc.ifc.remove(definition)


def _validate(style: dict | None) -> None:
    if style is None:
        return

    def color_ok(c):
        return isinstance(c, str) and len(c) == 7 and c.startswith("#")

    if not color_ok(style.get("color")):
        raise OpError(f"cor inválida: {style.get('color')!r}")
    cut = style.get("cut") or DEFAULT_CUT
    if cut["pattern"] not in PATTERNS:
        raise OpError(f"padrão de corte inválido: {cut['pattern']!r}")
    if cut["pattern"] == "solid" and not color_ok(cut.get("background")):
        raise OpError("o corte sólido precisa da cor do fundo")
    if cut.get("background") is not None and not color_ok(cut["background"]):
        raise OpError(f"cor inválida: {cut['background']!r}")
    if not 0 <= style.get("transparency", 0.0) < 1:
        raise OpError("a transparência deve ficar entre 0 e 1")
    if cut["spacing"] <= 0:
        raise OpError("o espaçamento da hachura deve ser positivo")
    if not color_ok(cut["line_color"]):
        raise OpError(f"cor inválida: {cut['line_color']!r}")


def write_style(doc: Document, material, new: dict | None) -> None:
    _validate(new)
    _write_color(doc, material, new["color"] if new else None,
                 new.get("transparency", 0.0) if new else 0.0)
    _write_cut(doc, material, {**DEFAULT_CUT, **new["cut"]} if new and new.get("cut") else None)
    _cleanup(doc, material)


def _edit(doc: Document, op: Op) -> set[str]:
    mats = named(doc, op.id)
    if not mats:
        raise OpError(f"material {op.id!r} não existe")
    check_before(op, state(doc, op.id))
    new = (op.after or {}).get("style")
    for material in mats:
        write_style(doc, material, copy.deepcopy(new))
    # Quem usa o material é redesenhado (planta e 3D leem o estilo na hora).
    return set()


register("material.edit", _edit, invert_swap)


def edit_op(doc: Document, name: str, new: dict | None) -> Op:
    return Op("material.edit", name, before=state(doc, name), after={"style": new})


def add_library_styles(doc: Document, names=None) -> None:
    """Grava os estilos da biblioteca (§4.4) nos materiais que ainda não têm estilo."""
    for material in doc.ifc.by_type("IfcMaterial"):
        if material.Name in LIBRARY and (names is None or material.Name in names) \
                and read_style(material) is None:
            write_style(doc, material, copy.deepcopy(LIBRARY[material.Name]))


def ensure_style(doc: Document, name: str) -> None:
    """Grava o estilo padrão no material que ainda não tem nenhum (as peças das esquadrias
    apontam para o ``IfcSurfaceStyle`` dele, spec/ui 09 §7)."""
    for material in named(doc, name):
        if read_style(material) is None:
            write_style(doc, material, default_style(name))
