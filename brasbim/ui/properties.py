# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel de propriedades (``spec/ui/01-janela-e-ferramentas.md`` §7 e
``spec/ui/02-edicao.md`` §9).

Mostra a seleção (parede, porta, ou vários elementos com edição em lote). As opções da
ferramenta ativa ficam na barra Opções (``spec/ui/03-barras-e-icones.md`` §4.3).

Os campos são montados como grupos (título + linhas) e desenhados em pé (painel nas
laterais) ou deitados, em blocos lado a lado (painel no topo ou na base;
``spec/ui/04-painel-de-propriedades.md``). Cada campo confirmado gera uma transação; recusas do núcleo voltam o
campo ao valor anterior (o painel é refeito a partir do modelo).
"""

from __future__ import annotations

import math
import re
from collections import Counter

import ifcopenshell.util.element
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import geom2d
from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.ops.history import combine
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings, rebuild, top
from brasbim.core.walls import params as wall_params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import common_defaults as wall_common_defaults
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui.tools import block_grid, fmt, parse_number

REF_LINES = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
TOPS = [("Pavimento de cima", "storey"), ("Altura fixa", "fixed")]
TOP_SHAPES = [("Plano", "flat"), ("Inclinado", "slope"), ("Empena", "gable"), ("Livre", "free")]
SLOPE_RISE, GABLE_RISE = 0.50, 1.00  # topo novo: fim e cumeeira acima da altura atual
OPENS_TO = [("Face esquerda da parede", "left"), ("Face direita da parede", "right")]
HINGES = [("Esquerda", "left"), ("Direita", "right")]
ALIGNS = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
_INVALID = "QLineEdit { background: #fde2df; }"
MIXED = "vários"

# Propriedades comuns no painel (spec/ui 05 §6): (propriedade IFC, nome, edição).
STATUS = [("Nova", "NEW"), ("Existente", "EXISTING"), ("A demolir", "DEMOLISH"),
          ("Temporária", "TEMPORARY")]
WALL_COMMON = [("Reference", "Código", "text"), ("Status", "Situação", "status"),
               ("IsExternal", "Externa", "bool"), ("LoadBearing", "Estrutural", "bool"),
               ("FireRating", "Resistência ao fogo", "text"),
               ("AcousticRating", "Desempenho acústico", "text"),
               ("ThermalTransmittance", "Transmitância térmica (W/m²K)", "number")]
DOOR_COMMON = [("Reference", "Código", "read"), ("Status", "Situação", "status"),
               ("IsExternal", "Externa", "bool"),
               ("FireRating", "Resistência ao fogo", "text"),
               ("AcousticRating", "Desempenho acústico", "text"),
               ("HandicapAccessible", "Acessível", "bool"),
               ("FireExit", "Saída de emergência", "bool")]
YES_NO = [("Sim", True), ("Não", False)]


ROW_HEIGHT = 27  # altura de uma linha de campo no arranjo deitado (px)
TITLE_HEIGHT = 22


class _Group:
    """Grupo de campos: título e linhas (nome ou None, widget)."""

    def __init__(self, title: str = ""):
        self.title = title
        self.rows: list[tuple[str | None, QWidget]] = []


def _initial_profile(shape: str, state: dict, path, height: float) -> list:
    """Perfil ao trocar a forma do topo: parte da altura atual (spec/ui 08 §4.1)."""
    old, length = state["top_profile"], path.length
    if shape == "flat":
        return []
    if shape == "slope":
        return top.slope(length, height, height + SLOPE_RISE)
    if shape == "gable":
        return top.gable(length, height, height + GABLE_RISE)
    return [list(p) for p in old] or top.slope(length, height, height)


def _points_text(profile) -> str:
    return "; ".join(f"{fmt(x)} {fmt(h)}" for x, h in profile)


def _parse_points(text: str) -> list:
    """``"0 2,8; 3 4; 6 2,8"`` → [[0, 2.8], [3, 4], [6, 2.8]]."""
    points = []
    for item in text.split(";"):
        parts = item.split()
        if len(parts) != 2:
            raise ValueError(item)
        points.append([parse_number(parts[0]), parse_number(parts[1])])
    return points


def _common(values):
    """O valor comum a todos, ou ``None`` se diferem (campo "vários")."""
    values = list(values)
    first = values[0]
    return first if all(v == first for v in values[1:]) else None


class PropertiesPanel(QScrollArea):
    def __init__(self, session, toolbox, parent=None):
        super().__init__(parent)
        self.session = session
        self.toolbox = toolbox
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._pending = False
        self.edit_type = None  # abre a janela de tipos (posto pela janela principal)
        self.lying = False  # arranjo deitado (spec/ui 04 §2)
        self.lines = 0  # linhas por bloco no arranjo deitado
        self.refresh()

    # --- refazer o painel ------------------------------------------------------------

    def refresh(self) -> None:
        """Refaz o painel depois do evento atual (um campo pode estar emitindo o sinal)."""
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self._rebuild)

    def wants_lying(self) -> bool:
        return self.width() >= 2 * self.height()

    def lines_available(self) -> int:
        return max(1, (self.viewport().height() - TITLE_HEIGHT - 12) // ROW_HEIGHT)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        lying = self.wants_lying()
        if lying != self.lying or (lying and self.lines_available() != self.lines):
            focus = QApplication.focusWidget()
            if focus is not None and self.isAncestorOf(focus):
                return  # não atrapalha quem está digitando (spec/ui 04 §3)
            self.refresh()

    def _rebuild(self) -> None:
        self._pending = False
        self.groups = [_Group()]
        selection = [self.session.doc.find(g) for g in sorted(self.session.selection)]
        selection = [e for e in selection if e is not None]
        if len(selection) == 1 and selection[0].is_a("IfcWall"):
            self._wall(selection[0])
        elif len(selection) == 1 and selection[0].is_a("IfcDoor"):
            self._door(selection[0])
        elif selection:
            self._title(f"{len(selection)} elementos selecionados")
            walls = [e for e in selection if e.is_a("IfcWall")]
            door_list = [e for e in selection if e.is_a("IfcDoor")]
            if walls:
                self._walls(walls)
            if door_list:
                self._doors(door_list)
            others = Counter(e.is_a() for e in selection
                             if not e.is_a("IfcWall") and not e.is_a("IfcDoor"))
            for cls, n in sorted(others.items()):
                self._add(cls, QLabel(str(n)))
        else:
            self._tool_options()
        self.lying = self.wants_lying()
        if self.lying:
            self._render_lying()
        else:
            self._render_standing()

    # --- arranjos ---------------------------------------------------------------------

    def _render_standing(self) -> None:
        """Em pé: grupos um abaixo do outro (spec 0.1 §7)."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        body = QWidget()
        self.layout_ = QVBoxLayout(body)
        form = self.form = QFormLayout()
        self.layout_.addLayout(form)
        for i, group in enumerate(self.groups):
            if group.title:
                text = f"<b>{group.title}</b>" if i == 0 else (
                    f"<span style='color:#666'>{group.title}</span>")
                label = QLabel(text)
                label.setWordWrap(True)
                form.addRow(label)
            for name, widget in group.rows:
                if name is None:
                    form.addRow(widget)
                else:
                    form.addRow(name, widget)
        self.layout_.addStretch(1)
        self.setWidget(body)

    def _render_lying(self) -> None:
        """Deitado: grupos em blocos lado a lado; campos em colunas dentro do bloco
        (spec/ui 04 §3)."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lines = self.lines_available()
        self.form = None
        body = QWidget()
        row = QHBoxLayout(body)
        row.setContentsMargins(4, 2, 4, 2)
        metrics = self.fontMetrics()
        blocks = [g for g in self.groups if g.title or g.rows]
        for i, group in enumerate(blocks):
            if i:
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setStyleSheet("color: #ccc")
                row.addWidget(line)
            block = QWidget()
            block.setObjectName("bloco")
            block.setProperty("titulo", group.title)
            column = QVBoxLayout(block)
            column.setContentsMargins(2, 0, 2, 0)
            column.setSpacing(2)
            title = QLabel(f"<b>{group.title}</b>" if i == 0 and group.title
                           else f"<span style='color:#666'>{group.title}</span>")
            column.addWidget(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(2)
            for (name, widget), (r, c) in zip(group.rows,
                                              block_grid(len(group.rows), self.lines),
                                              strict=True):
                self._compact(widget, metrics)
                if name is None:
                    grid.addWidget(widget, r, 2 * c, 1, 2)
                else:
                    label = QLabel(name)
                    label.setStyleSheet("color: #444")
                    grid.addWidget(label, r, 2 * c)
                    grid.addWidget(widget, r, 2 * c + 1)
            column.addLayout(grid)
            column.addStretch(1)
            row.addWidget(block)
        row.addStretch(1)
        self.setWidget(body)

    @staticmethod
    def _compact(widget: QWidget, metrics) -> None:
        if isinstance(widget, QLineEdit):
            widget.setMaximumWidth(metrics.horizontalAdvance("0") * 8 + 16)
        elif isinstance(widget, QComboBox):
            widget.setMaximumWidth(metrics.horizontalAdvance("M") * 15 + 30)
        elif isinstance(widget, QLabel) and widget.wordWrap():
            widget.setMaximumWidth(280)

    # --- campos ---------------------------------------------------------------------------

    def _add(self, name, widget=None) -> None:
        """Linha no grupo atual: ``(nome, campo)`` ou só um widget (largura inteira)."""
        if widget is None:
            name, widget = None, name
        self.groups[-1].rows.append((name or None, widget))

    def _title(self, text: str) -> None:
        self.groups[0].title = text

    def _section(self, text: str) -> None:
        self.groups.append(_Group(re.sub(r"</?b>", "", text)))

    def _read(self, label: str, text: str) -> None:
        value = QLabel(text)
        value.setStyleSheet("color: #777")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._add(label, value)

    def _number(self, label: str, value, commit, placeholder: str = "",
                allow_empty: bool = False) -> QLineEdit:
        field = QLineEdit("" if value is None else fmt(value))
        field.setPlaceholderText(placeholder)
        original = field.text()

        def done():
            text = field.text().strip()
            if text == original:
                return
            if not text and allow_empty:
                commit(None)
                return
            try:
                number = parse_number(text)
            except ValueError:
                field.setStyleSheet(_INVALID)
                self.session.message(f"{label}: número inválido", "recusa")
                return
            field.setStyleSheet("")
            commit(number)

        field.editingFinished.connect(done)
        self._add(label, field)
        return field

    def _combo(self, label: str, items, current, commit) -> QComboBox:
        """Lista; ``current`` ``None`` com valores diferentes mostra "vários"."""
        combo = QComboBox()
        if current is None and items and None not in [v for _, v in items]:
            items = [(f"({MIXED})", None), *items]
        for text, value in items:
            combo.addItem(text, value)
        index = next((i for i, (_, v) in enumerate(items) if v == current), -1)
        combo.setCurrentIndex(index)

        def changed(i):
            value = combo.itemData(i)
            if value != current and (value is not None or current is not None):
                commit(value)

        combo.currentIndexChanged.connect(changed)
        self._add(label, combo)
        return combo

    def _buttons(self, *buttons) -> None:
        row = QHBoxLayout()
        for text, action in buttons:
            b = QPushButton(text)
            b.clicked.connect(action)
            row.addWidget(b)
        holder = QWidget()
        holder.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        self._add(holder)

    def _types(self, ifc_class: str):
        return [(e.Name or e.GlobalId, e.GlobalId)
                for e in sorted(self.session.doc.ifc.by_type(ifc_class), key=lambda e: e.Name or "")]

    def _run(self, build) -> None:
        self.session.run(build)
        self.refresh()  # recusa: o campo volta ao valor do modelo

    # --- parede (§7.2) -------------------------------------------------------------

    def _wall(self, wall) -> None:
        doc = self.session.doc
        state = read_wall(doc, wall)
        foreign = not ifcopenshell.util.element.get_pset(wall, wall_params.PSET)
        self._title(f"Parede {wall.Name or ''}".strip())

        def edit(**changes):
            self._run(lambda: cmd.edit_wall(doc, wall, **changes))

        self._combo("Tipo", self._types("IfcWallType"), state["type"],
                    lambda v: edit(type=v))
        self._edit_type_button("IfcWallType", state["type"])
        self._combo("Linha de referência", REF_LINES, state["ref_line"],
                    lambda v: edit(ref_line=v))
        flip = QCheckBox("Inverter camadas")
        flip.setChecked(bool(state["flip_layers"]))
        flip.toggled.connect(lambda v: edit(flip_layers=bool(v)))
        self._add("", flip)

        self._section("Altura")
        self._number("Base", state["base_offset"], lambda v: edit(base_offset=v))
        height = rebuild.height(doc, state)

        def top(mode):
            if mode == "fixed":
                edit(top_mode="fixed", fixed_height=height)
                return
            storey = doc.get(state["storey"])
            above = doc.storey_above(storey)
            if above is None:
                self.session.message("não há pavimento acima deste", "recusa")
                self.refresh()
                return
            edit(top_mode="storey", top_storey=above.GlobalId, top_offset=0.0)

        path = geom2d.path_from_dict(state["path"])
        straight = isinstance(path, geom2d.LinePath)
        if straight:
            self._combo("Forma do topo", TOP_SHAPES, state["top_shape"],
                        lambda v: edit(top_shape=v,
                                       top_profile=_initial_profile(v, state, path, height)))
        if state["top_shape"] == "flat":
            self._combo("Topo", TOPS, state["top_mode"], top)
            if state["top_mode"] == "fixed":
                self._number("Altura", state["fixed_height"], lambda v: edit(fixed_height=v))
            else:
                self._number("Deslocamento do topo", state["top_offset"],
                             lambda v: edit(top_offset=v))
        else:
            self._top_profile(state, path, lambda p: edit(top_profile=p))
        if straight:
            self._number("Inclinação (°)", state["tilt"], lambda v: edit(tilt=v))

        self._section("Geometria")
        if straight:
            def to_end(length, angle):
                end = (path.start[0] + length * math.cos(angle),
                       path.start[1] + length * math.sin(angle))
                self._run(lambda: cmd.move_wall_end(doc, wall, "end", end, carry=False))

            degrees = math.degrees(path.start_angle) % 360.0
            self._number("Comprimento", path.length,
                         lambda v: to_end(v, path.start_angle))
            self._number("Ângulo (°)", degrees,
                         lambda v: to_end(path.length, math.radians(v)))
        else:
            self._read("Comprimento", f"{fmt(path.length)} m")
            self._read("Raio", f"{fmt(path.radius)} m")
        q = ifcopenshell.util.element.get_pset(wall, "Qto_WallBaseQuantities") or {}
        self._section("Quantidades")
        thickness = wall_types.thickness(doc.get(state["type"], "IfcWallType"))
        self._read("Comprimento no eixo", f"{fmt(q.get('Length', 0))} m")
        self._read("Espessura", f"{fmt(thickness)} m")
        self._read("Altura", f"{fmt(height)} m")
        self._read("Área lateral bruta", f"{fmt(q.get('GrossSideArea', 0))} m²")
        self._read("Área lateral líquida", f"{fmt(q.get('NetSideArea', 0))} m²")
        self._read("Volume líquido", f"{fmt(q.get('NetVolume', 0))} m³")
        self._wall_common([wall])
        self._section("Identificação")
        self._read("GlobalId", wall.GlobalId)
        self._read("Origem", "outro programa" if foreign else "BrasBim")

    def _top_profile(self, state, path, commit) -> None:
        """Parâmetros do topo inclinado, empena ou livre (spec/ui 08 §4.1)."""
        profile, shape, length = state["top_profile"], state["top_shape"], path.length
        if shape == "slope":
            (_, h0), (_, h1) = profile
            self._number("Altura no início", h0, lambda v: commit(top.slope(length, v, h1)))
            self._number("Altura no fim", h1, lambda v: commit(top.slope(length, h0, v)))
            self._number("Ângulo (°)", top.angle(profile),
                         lambda v: commit(top.slope_by_angle(length, h0, v)))
        elif shape == "gable":
            (_, h), (x, hc), _ = profile
            self._number("Altura nas pontas", h,
                         lambda v: commit(top.gable(length, v, hc, x)))
            self._number("Altura da cumeeira", hc,
                         lambda v: commit(top.gable(length, h, v, x)))
            self._number("Ângulo (°)", top.angle(profile),
                         lambda v: commit(top.gable_by_angle(length, h, v, x)))
            self._number("Posição da cumeeira", x,
                         lambda v: commit(top.gable(length, h, hc, v)))
        else:
            def points(text):
                try:
                    found = _parse_points(text)
                except ValueError:
                    self.session.message("Pontos do topo: use \"distância altura\" "
                                         "separados por ponto e vírgula", "recusa")
                    self.refresh()
                    return
                commit(found)

            self._text("Pontos (distância altura; …)", _points_text(profile), points)

    # --- vários elementos (0.2 §9) ---------------------------------------------------------

    def _walls(self, walls) -> None:
        doc = self.session.doc
        states = [read_wall(doc, w) for w in walls]
        self._section(f"<b>Paredes ({len(walls)})</b>")
        label = f"Editar {len(walls)} paredes"

        def edit(**changes):
            self._run(lambda: cmd.edit_walls(doc, walls, **changes))

        def each(build):
            self._run(lambda: combine(doc, label, [lambda w=w: build(w) for w in walls]))

        self._combo("Tipo", self._types("IfcWallType"), _common(s["type"] for s in states),
                    lambda v: edit(type=v))
        self._combo("Linha de referência", REF_LINES, _common(s["ref_line"] for s in states),
                    lambda v: edit(ref_line=v))
        self._combo("Inverter camadas", [("Não", False), ("Sim", True)],
                    _common(bool(s["flip_layers"]) for s in states),
                    lambda v: edit(flip_layers=v))
        self._number("Base", _common(s["base_offset"] for s in states),
                     lambda v: edit(base_offset=v), placeholder=MIXED)
        mode = _common(s["top_mode"] for s in states)

        def to_fixed(w):
            height = rebuild.height(doc, read_wall(doc, w))
            return cmd.edit_wall(doc, w, top_mode="fixed", fixed_height=height)

        def to_storey(w):
            above = doc.storey_above(doc.get(read_wall(doc, w)["storey"]))
            if above is None:
                raise OpError(f"não há pavimento acima da parede {w.GlobalId}")
            return cmd.edit_wall(doc, w, top_mode="storey", top_storey=above.GlobalId,
                                 top_offset=0.0)

        self._combo("Topo", TOPS, mode,
                    lambda v: each(to_fixed if v == "fixed" else to_storey))
        if mode == "fixed":
            self._number("Altura", _common(s["fixed_height"] for s in states),
                         lambda v: edit(fixed_height=v), placeholder=MIXED)
        elif mode == "storey":
            self._number("Deslocamento do topo", _common(s["top_offset"] for s in states),
                         lambda v: edit(top_offset=v), placeholder=MIXED)
        total = sum((ifcopenshell.util.element.get_pset(w, "Qto_WallBaseQuantities") or {})
                    .get("Length", 0.0) for w in walls)
        self._read("Comprimento total", f"{fmt(total)} m")
        names = Counter(doc.get(s["type"]).Name for s in states)
        for name, n in sorted(names.items()):
            self._read(name, str(n))
        self._wall_common(walls)

    def _doors(self, door_list) -> None:
        doc = self.session.doc
        states = [doors.read_state(d) for d in door_list]
        found = [fc.opening_of(d) for d in door_list]
        spans = [openings.read_state(o) for o in found if o is not None]
        self._section(f"<b>Portas ({len(door_list)})</b>")

        def edit(**changes):
            self._run(lambda: fc.edit_doors(doc, door_list, **changes))

        self._combo("Tipo", self._types("IfcDoorType"), _common(s["type"] for s in states),
                    lambda v: edit(type=v))
        if len(spans) == len(door_list):
            self._number("Largura", _common(o["width"] for o in spans),
                         lambda v: edit(width=v), placeholder=MIXED)
            self._number("Altura", _common(o["height"] for o in spans),
                         lambda v: edit(height=v), placeholder=MIXED)
            self._number("Base", _common(o["sill"] for o in spans),
                         lambda v: edit(base=v), placeholder=MIXED)
        self._combo("Abre para", OPENS_TO, _common(s["opens_to"] for s in states),
                    lambda v: edit(opens_to=v))
        hands = []
        for s in states:
            door_type = doc.find(s["type"]) if s["type"] else None
            tstate = door_types.read(door_type) if door_type and s["foreign"] is None else None
            hands.append(params.hand_of(tstate["operation_type"]) if tstate else None)
        buttons = [("Inverter sentido", lambda: self._run(
            lambda: fc.flip_each(doc, door_list, fc.flip_opening)))]
        if all(hands):
            self._combo("Dobradiças", HINGES, _common(hands), lambda v: edit(hinges=v))
            buttons.append(("Inverter dobradiças", lambda: self._run(
                lambda: fc.flip_each(doc, door_list, fc.flip_hinges))))
        self._buttons(*buttons)
        self._combo("Alinhamento", ALIGNS, _common(s["align"] for s in states),
                    lambda v: edit(align=v))
        self._number("Deslocamento", _common(s["offset"] for s in states),
                     lambda v: edit(offset=v), placeholder=MIXED)
        names = Counter(params.base_name(doc.get(s["type"]).Name) if s["type"] else "sem tipo"
                        for s in states)
        for name, n in sorted(names.items()):
            self._read(name, str(n))
        self._door_common(door_list)

    # --- porta (§7.3) -------------------------------------------------------------------

    def _door(self, door) -> None:
        doc = self.session.doc
        state = doors.read_state(door)
        opening = fc.opening_of(door)
        o = openings.read_state(opening) if opening is not None else None
        door_type = doc.find(state["type"]) if state["type"] else None
        tstate = (door_types.read(door_type)
                  if door_type is not None and state["foreign"] is None else None)
        common = ifcopenshell.util.element.get_pset(door, "Pset_DoorCommon") or {}
        self._title(f"Porta {door.Name or ''}".strip())

        def edit(**changes):
            self._run(lambda: fc.edit_door(doc, door, **changes))

        self._combo("Tipo", self._types("IfcDoorType"), state["type"], lambda v: edit(type=v))
        if state["type"] and state["foreign"] is None:
            self._edit_type_button("IfcDoorType", state["type"])
        self._read("Código", str(common.get("Reference") or "—"))
        if o is not None:
            self._section("Vão")
            self._number("Largura", o["width"], lambda v: edit(width=v))
            self._number("Altura", o["height"], lambda v: edit(height=v))
            self._number("Base", o["sill"], lambda v: edit(base=v))
            self._number("Distância ao início", o["distance"], lambda v: edit(distance=v))
        self._section("Abertura")
        self._combo("Abre para", OPENS_TO, state["opens_to"], lambda v: edit(opens_to=v))
        hand = params.hand_of(tstate["operation_type"]) if tstate else None
        if hand is not None:
            self._combo("Dobradiças", HINGES, hand, lambda v: edit(hinges=v))
        buttons = [("Inverter sentido",
                    lambda: self._run(lambda: fc.flip_opening(doc, door)))]
        if hand is not None:
            buttons.append(("Inverter dobradiças",
                            lambda: self._run(lambda: fc.flip_hinges(doc, door))))
        self._buttons(*buttons)
        self._section("Posição no marco")
        self._combo("Alinhamento", ALIGNS, state["align"], lambda v: edit(align=v))
        self._number("Deslocamento", state["offset"], lambda v: edit(offset=v))
        q = ifcopenshell.util.element.get_pset(door, params.QTO) or {}
        if q:
            self._section("Quantidades")
            self._read("Largura", f"{fmt(q.get('Width', 0))} m")
            self._read("Altura", f"{fmt(q.get('Height', 0))} m")
            self._read("Área", f"{fmt(q.get('Area', 0))} m²")
        self._door_common([door])
        self._section("Identificação")
        self._read("GlobalId", door.GlobalId)
        self._read("Origem", "outro programa" if state["foreign"] is not None else "BrasBim")
        if state["foreign"] is not None:
            warning = QLabel("Porta de outro programa: mudar tamanho, tipo, sentido, "
                             "dobradiças ou alinhamento a converte em porta do BrasBim, e o "
                             "corpo original é substituído.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #8a5a00")
            self._add(warning)

    # --- opções da ferramenta (§7.1) ------------------------------------------------------

    # --- propriedades comuns (spec/ui 05 §6) ------------------------------------------

    def _text(self, label: str, value, commit, placeholder: str = "") -> QLineEdit:
        field = QLineEdit("" if value is None else str(value))
        field.setPlaceholderText(placeholder)
        original = field.text()

        def done():
            if field.text().strip() != original:
                commit(field.text().strip() or None)

        field.editingFinished.connect(done)
        self._add(label, field)
        return field

    def _common_group(self, elements, fields, effective, defaults, edit) -> None:
        """Campos de ``Pset_*Common``. ``effective(e)``: valores com os padrões;
        ``defaults(e)``: padrões do tipo; ``edit(e, common)``: transação de um elemento."""
        doc = self.session.doc
        self._section("Propriedades comuns")
        values = [effective(e) for e in elements]
        label = (f"Editar {len(elements)} elementos" if len(elements) > 1
                 else "Editar propriedades")

        def commit(key, value):
            def build(element):
                base = defaults(element)
                merged = {**effective(element), key: value}
                common = {k: v for k, v in merged.items()
                          if v not in (None, "") and base.get(k) != v}
                return edit(element, common)

            if len(elements) == 1:
                self._run(lambda: build(elements[0]))
            else:
                self._run(lambda: combine(doc, label, [lambda e=e: build(e)
                                                       for e in elements]))

        for key, name, kind in fields:
            if kind == "bool":
                current = _common(bool(v.get(key)) for v in values)
                self._combo(name, YES_NO, current, lambda v, k=key: commit(k, v))
            elif kind == "status":
                current = _common(v.get("Status") or "NEW" for v in values)
                self._combo(name, STATUS, current, lambda v, k=key: commit(k, v))
            elif kind == "number":
                self._number(name, _common(v.get(key) for v in values),
                             lambda v, k=key: commit(k, v), placeholder=MIXED
                             if len(values) > 1 else "", allow_empty=True)
            elif kind == "read":
                current = _common(v.get(key) for v in values)
                self._read(name, MIXED if current is None and len(values) > 1
                           else str(current or "—"))
            else:
                current = _common(v.get(key) for v in values)
                self._text(name, current, lambda v, k=key: commit(k, v),
                           placeholder=MIXED if current is None and len(values) > 1 else "")

    def _wall_common(self, walls) -> None:
        doc = self.session.doc

        def defaults(wall):
            return wall_common_defaults(doc.get(read_wall(doc, wall)["type"], "IfcWallType"))

        def effective(wall):
            return {**defaults(wall), **read_wall(doc, wall)["common"]}

        self._common_group(walls, WALL_COMMON, effective, defaults,
                           lambda w, common: cmd.edit_wall(doc, w, common=common))

    def _door_common(self, door_list) -> None:
        doc = self.session.doc

        def defaults(door):
            state = doors.read_state(door)
            if state["foreign"] is not None or not state["type"]:
                return {}
            return doors.common_defaults(doc.get(state["type"]).Name)

        def effective(door):
            return {**defaults(door), **doors.read_state(door)["common"]}

        self._common_group(door_list, DOOR_COMMON, effective, defaults,
                           lambda d, common: fc.edit_door(doc, d, common=common))

    def _edit_type_button(self, ifc_class: str, gid: str) -> None:
        if self.edit_type is not None:
            self._buttons(("Editar tipo…", lambda: self.edit_type(ifc_class, gid)))

    def _tool_options(self) -> None:
        """Sem seleção: só o pavimento ativo e a dica (spec/ui 03 §4.3)."""
        self._title("Nada selecionado")
        storey = self.session.storey
        if storey is not None:
            self._read("Pavimento ativo", f"{storey.Name} ({fmt(storey.Elevation or 0)})")
        note = QLabel("Clique num elemento da planta para ver e editar as propriedades.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #666")
        self._add(note)
