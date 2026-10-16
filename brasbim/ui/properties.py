# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel de propriedades (``spec/ui/01-janela-e-ferramentas.md`` §7 e
``spec/ui/02-edicao.md`` §9).

Mostra a seleção (parede, porta, janela, pilar, viga, laje, ou vários elementos com
edição em lote; spec/ui 10 §4.3). As opções da
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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import geom2d
from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params, window_types
from brasbim.core.ops.history import combine
from brasbim.core.structure import beams, columns, profiles, slab_openings, slabs
from brasbim.core.structure import commands as sc
from brasbim.core.structure import common as structure_common
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings, rebuild, top
from brasbim.core.walls import params as wall_params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import common_defaults as wall_common_defaults
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui import theme
from brasbim.ui.tools import block_grid, fmt, parse_number

REF_LINES = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
TOPS = [("Pavimento de cima", "storey"), ("Altura fixa", "fixed")]
TOP_SHAPES = [("Plano", "flat"), ("Inclinado", "slope"), ("Empena", "gable"), ("Livre", "free")]
SLOPE_RISE, GABLE_RISE = 0.50, 1.00  # topo novo: fim e cumeeira acima da altura atual
OPENS_TO = [("Face esquerda da parede", "left"), ("Face direita da parede", "right")]
HINGES = [("Esquerda", "left"), ("Direita", "right")]
ALIGNS = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
_INVALID = f"QLineEdit {{ background: {theme.ERROR_SOFT}; border-color: {theme.ERROR}; }}"
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
WINDOW_COMMON = [("Reference", "Código", "read"), ("Status", "Situação", "status"),
                 ("IsExternal", "Externa", "bool"),
                 ("HasSillExternal", "Peitoril externo (pingadeira)", "bool"),
                 ("HasSillInternal", "Peitoril interno", "bool"),
                 ("FireRating", "Resistência ao fogo", "text"),
                 ("AcousticRating", "Desempenho acústico", "text"),
                 ("ThermalTransmittance", "Transmitância térmica (W/m²K)", "number")]
HANDS = [("Esquerda", "left"), ("Direita", "right")]
STRUCTURE_COMMON = [("Reference", "Código", "text"), ("Status", "Situação", "status"),
                    ("LoadBearing", "Estrutural", "bool"), ("IsExternal", "Externa", "bool"),
                    ("FireRating", "Resistência ao fogo", "text")]
SLAB_COMMON = [*STRUCTURE_COMMON, ("AcousticRating", "Desempenho acústico", "text")]
BEAM_TOPS = [("Pavimento de cima", "storey"), ("Cota fixa", "fixed")]
# Ponto de inserção do pilar como visto na planta (spec/ui 10 §3).
INSERTIONS = [("Centro", (1, 1)), ("Canto inferior esquerdo", (0, 0)),
              ("Meio de baixo", (1, 0)), ("Canto inferior direito", (2, 0)),
              ("Meio da esquerda", (0, 1)), ("Meio da direita", (2, 1)),
              ("Canto superior esquerdo", (0, 2)), ("Meio de cima", (1, 2)),
              ("Canto superior direito", (2, 2))]
SECTIONS = [("Retangular", "rect"), ("Circular", "circle")]
STRUCTURE_NOUNS = {"IfcColumn": ("Pilar", "Pilares"), "IfcBeam": ("Viga", "Vigas"),
                   "IfcSlab": ("Laje", "Lajes")}
# Caixilhos sem giro: o "abre para" é o lado interno (janela §2.4).
_NO_SWING = ("FIXEDCASEMENT", "SLIDINGHORIZONTAL", "SLIDINGVERTICAL")
YES_NO = [("Sim", True), ("Não", False)]


def _filling_info(doc, element) -> tuple[bool, dict | None]:
    """(é janela, estado do tipo do BrasBim ou None)."""
    window = element.is_a("IfcWindow")
    state = doors.read_state(element)
    found = doc.find(state["type"]) if state["type"] else None
    if found is None or state["foreign"] is not None:
        return window, None
    return window, (window_types if window else door_types).read(found)


def _hand(window: bool, tstate: dict | None) -> str | None:
    if tstate is None:
        return None
    return window_types.hand(tstate) if window else params.hand_of(tstate["operation_type"])


def _opens_label(window: bool, tstate: dict | None) -> str:
    if window and tstate and all(p["operation"] in _NO_SWING for p in tstate["panels"]):
        return "Lado interno"
    return "Abre para"


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
        self.setFont(theme.font(width=92))  # um pouco estreita: painel denso (spec/ui 11 §3)
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
        elif len(selection) == 1 and (selection[0].is_a("IfcDoor")
                                      or selection[0].is_a("IfcWindow")):
            self._door(selection[0])
        elif len(selection) == 1 and slab_openings.is_slab_opening(selection[0]):
            self._slab_opening(selection[0])
        elif len(selection) == 1 and sc.is_structure(selection[0]):
            {"IfcColumn": self._column, "IfcBeam": self._beam,
             "IfcSlab": self._slab}[selection[0].is_a()](selection[0])
        elif selection:
            self._title(f"{len(selection)} elementos selecionados")
            walls = [e for e in selection if e.is_a("IfcWall")]
            door_list = [e for e in selection if e.is_a("IfcDoor")]
            window_list = [e for e in selection if e.is_a("IfcWindow")]
            if walls:
                self._walls(walls)
            if door_list:
                self._doors(door_list)
            if window_list:
                self._doors(window_list)
            for cls in ("IfcColumn", "IfcBeam", "IfcSlab"):
                found = [e for e in selection if e.is_a(cls)]
                if found:
                    self._structures(found)
            known = ("IfcWall", "IfcDoor", "IfcWindow", "IfcColumn", "IfcBeam", "IfcSlab")
            others = Counter(e.is_a() for e in selection
                             if not any(e.is_a(c) for c in known))
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
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(4)
        self.layout_.addLayout(form)
        for i, group in enumerate(self.groups):
            if group.title:
                text = f"<b>{group.title}</b>" if i == 0 else (
                    f"<span style='font-weight:600'>{group.title}</span>")
                label = QLabel(text)
                label.setWordWrap(True)
                if i:
                    label.setContentsMargins(0, 8, 0, 0)
                form.addRow(label)
            for name, widget in group.rows:
                if isinstance(widget, QComboBox):
                    # nomes longos de tipo não alargam o painel além da tela
                    widget.setSizeAdjustPolicy(
                        QComboBox.AdjustToMinimumContentsLengthWithIcon)
                    widget.setMinimumContentsLength(8)
                elif isinstance(widget, QLabel) and name is not None:
                    # valor longo (GlobalId) não alarga o painel; selecionável para copiar
                    widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                if name is None:
                    form.addRow(widget)
                else:
                    label = QLabel(name)
                    label.setWordWrap(True)  # rótulo longo quebra; o campo fica ao lado
                    form.addRow(label, widget)
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
                line.setStyleSheet(f"color: {theme.RULE_SOFT}")
                row.addWidget(line)
            block = QWidget()
            block.setObjectName("bloco")
            block.setProperty("titulo", group.title)
            column = QVBoxLayout(block)
            column.setContentsMargins(2, 0, 2, 0)
            column.setSpacing(2)
            title = QLabel(f"<b>{group.title}</b>" if i == 0 and group.title
                           else f"<span style='font-weight:600'>{group.title}</span>")
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
                    label.setStyleSheet(f"color: {theme.INK_SOFT}")
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
        value.setStyleSheet(f"color: {theme.INK}")
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
        """Várias portas, ou várias janelas (spec/ui 02 §9; spec/ui 09 §4.4)."""
        doc = self.session.doc
        window = door_list[0].is_a("IfcWindow")
        type_class = "IfcWindowType" if window else "IfcDoorType"
        states = [doors.read_state(d) for d in door_list]
        found = [fc.opening_of(d) for d in door_list]
        spans = [openings.read_state(o) for o in found if o is not None]
        self._section(f"<b>{'Janelas' if window else 'Portas'} ({len(door_list)})</b>")

        def edit(**changes):
            self._run(lambda: fc.edit_doors(doc, door_list, **changes))

        self._combo("Tipo", self._types(type_class), _common(s["type"] for s in states),
                    lambda v: edit(type=v))
        if len(spans) == len(door_list):
            self._number("Largura", _common(o["width"] for o in spans),
                         lambda v: edit(width=v), placeholder=MIXED)
            self._number("Altura", _common(o["height"] for o in spans),
                         lambda v: edit(height=v), placeholder=MIXED)
            self._number("Peitoril" if window else "Base", _common(o["sill"] for o in spans),
                         lambda v: edit(base=v), placeholder=MIXED)
        infos = [_filling_info(doc, d) for d in door_list]
        labels = {_opens_label(w, t) for w, t in infos}
        self._combo(labels.pop() if len(labels) == 1 else "Abre para", OPENS_TO,
                    _common(s["opens_to"] for s in states), lambda v: edit(opens_to=v))
        hands = [_hand(w, t) for w, t in infos]
        buttons = [("Inverter sentido", lambda: self._run(
            lambda: fc.flip_each(doc, door_list, fc.flip_opening)))]
        if all(hands):
            name = "Mão" if window else "Dobradiças"
            self._combo(name, HANDS if window else HINGES, _common(hands),
                        lambda v: edit(hinges=v))
            buttons.append((f"Inverter {'mão' if window else 'dobradiças'}", lambda: self._run(
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
        """Porta (spec/ui 01 §7.3) ou janela (spec/ui 09 §4.4) selecionada sozinha."""
        doc = self.session.doc
        state = doors.read_state(door)
        opening = fc.opening_of(door)
        o = openings.read_state(opening) if opening is not None else None
        window, tstate = _filling_info(doc, door)
        _, type_class, common_pset, qto, _ = doors.kind_of(door)
        noun = "Janela" if window else "Porta"
        common = ifcopenshell.util.element.get_pset(door, common_pset) or {}
        self._title(f"{noun} {door.Name or ''}".strip())

        def edit(**changes):
            self._run(lambda: fc.edit_door(doc, door, **changes))

        self._combo("Tipo", self._types(type_class), state["type"], lambda v: edit(type=v))
        if state["type"] and state["foreign"] is None:
            self._edit_type_button(type_class, state["type"])
        self._read("Código", str(common.get("Reference") or "—"))
        if o is not None:
            self._section("Vão")
            self._number("Largura", o["width"], lambda v: edit(width=v))
            self._number("Altura", o["height"], lambda v: edit(height=v))
            self._number("Peitoril" if window else "Base", o["sill"], lambda v: edit(base=v))
            if window:  # a verga muda a altura e mantém o peitoril (janela §3.1)
                self._number("Verga", o["sill"] + o["height"],
                             lambda v: edit(height=v - o["sill"]))
            self._number("Distância ao início", o["distance"], lambda v: edit(distance=v))
            host = openings.host(opening)
            base_offset = read_wall(doc, host)["base_offset"] if host is not None else 0.0
            if window and abs(base_offset) > 1e-9:
                self._read("Peitoril do piso", f"{fmt(o['sill'] + base_offset)} m")
        self._section("Abertura")
        self._combo(_opens_label(window, tstate), OPENS_TO, state["opens_to"],
                    lambda v: edit(opens_to=v))
        hand = _hand(window, tstate)
        hand_name = "Mão" if window else "Dobradiças"
        if hand is not None:
            self._combo(hand_name, HANDS if window else HINGES, hand,
                        lambda v: edit(hinges=v))
        buttons = [("Inverter sentido",
                    lambda: self._run(lambda: fc.flip_opening(doc, door)))]
        if hand is not None:
            buttons.append((f"Inverter {hand_name.lower()}",
                            lambda: self._run(lambda: fc.flip_hinges(doc, door))))
        self._buttons(*buttons)
        self._section("Posição no marco")
        self._combo("Alinhamento", ALIGNS, state["align"], lambda v: edit(align=v))
        self._number("Deslocamento", state["offset"], lambda v: edit(offset=v))
        if window and tstate and o is not None:
            host = openings.host(opening)
            band, _ = openings.wall_info(doc, host)
            if tstate["lining"]["depth"] > band.thickness + 1e-6:
                note = QLabel("O marco é mais profundo que a parede.")
                note.setStyleSheet(f"color: {theme.WARN}")
                self._add(note)
        q = ifcopenshell.util.element.get_pset(door, qto) or {}
        if q:
            self._section("Quantidades")
            self._read("Largura", f"{fmt(q.get('Width', 0))} m")
            self._read("Altura", f"{fmt(q.get('Height', 0))} m")
            self._read("Área", f"{fmt(q.get('Area', 0))} m²")
            if window:
                self._read("Perímetro", f"{fmt(q.get('Perimeter', 0))} m")
        self._door_common([door])
        self._section("Identificação")
        self._read("GlobalId", door.GlobalId)
        self._read("Origem", "outro programa" if state["foreign"] is not None else "BrasBim")
        if state["foreign"] is not None:
            warning = QLabel(f"{noun} de outro programa: mudar tamanho, tipo, sentido, "
                             f"{hand_name.lower()} ou alinhamento a converte em "
                             f"{noun.lower()} do BrasBim, e o corpo original é substituído.")
            warning.setWordWrap(True)
            warning.setStyleSheet(f"color: {theme.WARN}")
            self._add(warning)

    # --- pilar, viga e laje (spec/ui 10 §4.3) -----------------------------------------------

    def _structure_head(self, element, state: dict, type_class: str) -> None:
        """Pilar e viga: nome e dimensões da seção, digitadas (decisão do revisor,
        2026‑10‑16); laje: tipo e Editar tipo…"""
        doc = self.session.doc
        if element.is_a("IfcSlab") or state["foreign"] is not None:
            self._combo("Tipo", self._types(type_class), state["type"],
                        lambda v: self._run(lambda: sc.edit_element(doc, element, type=v)))
            if state["type"] and element.is_a("IfcSlab"):
                self._edit_type_button(type_class, state["type"])
            return
        self._text("Nome", element.Name, lambda v: self._run(
            lambda: sc.edit_element(doc, element, name=v)))
        section = sc.module_of(element).section(doc, state)
        self._section_fields([element], [section])

    def _section_fields(self, elements, sections) -> None:
        """b, h (ou Ø) da seção; mudar vale só para os elementos mostrados, cada um
        mantendo a outra dimensão (o tipo da seção é achado ou criado)."""
        doc = self.session.doc
        column = elements[0].is_a("IfcColumn")

        def apply(change):
            builds = [lambda e=e, sec=sec: sc.edit_element(doc, e, section=change(sec))
                      for e, sec in zip(elements, sections, strict=True)]
            if len(builds) == 1:
                self._run(builds[0])
            else:
                self._run(lambda: combine(doc, f"Editar {len(builds)} elementos", builds))

        def size(key):
            def commit(value):
                if value <= profiles.MIN_SIZE:
                    self.session.message(f"a dimensão deve passar de "
                                         f"{fmt(profiles.MIN_SIZE)} m", "recusa")
                    self.refresh()
                    return
                apply(lambda sec: {**sec, key: value})
            return commit

        shape = _common(sec["shape"] for sec in sections)
        if column:
            def to_shape(value):
                def change(sec):
                    if value == "circle":
                        return {"shape": "circle", "d": max(sec.get("b", 0), sec.get("h", 0))
                                or sec["d"]}
                    d = sec.get("d", 0.20)
                    return {"shape": "rect", "b": sec.get("b", d), "h": sec.get("h", d)}
                apply(change)

            self._combo("Seção", SECTIONS, shape, to_shape)
        if shape == "circle":
            self._number("Ø (diâmetro)", _common(sec["d"] for sec in sections), size("d"),
                         placeholder=MIXED)
        elif shape == "rect":
            self._number("b (largura)", _common(sec["b"] for sec in sections), size("b"),
                         placeholder=MIXED)
            self._number("h (altura)" if not column else "h (profundidade)",
                         _common(sec["h"] for sec in sections), size("h"), placeholder=MIXED)

    def _structure_tail(self, element, state: dict) -> None:
        self._structure_common([element])
        self._section("Identificação")
        self._read("GlobalId", element.GlobalId)
        foreign = state["foreign"] is not None
        self._read("Origem", "outro programa" if foreign else "BrasBim")
        if foreign:
            note = QLabel("Elemento de outro programa: o corpo é mantido; mover e girar "
                          "mudam só a posição.")
            note.setWordWrap(True)
            note.setStyleSheet(f"color: {theme.WARN}")
            self._add(note)

    def _top_fields(self, element, state: dict, fixed_key: str, fixed_label: str,
                    current_top: float, tops) -> None:
        """Topo ligado ao pavimento de cima ou fixo (altura do pilar, cota da viga)."""
        doc = self.session.doc

        def edit(**changes):
            self._run(lambda: sc.edit_element(doc, element, **changes))

        def top(mode):
            if mode == "fixed":
                edit(top_mode="fixed", **{fixed_key: current_top})
                return
            above = doc.storey_above(doc.get(state["storey"]))
            if above is None:
                self.session.message("não há pavimento acima deste", "recusa")
                self.refresh()
                return
            edit(top_mode="storey", top_storey=above.GlobalId, top_offset=0.0)

        self._combo("Topo", tops, state["top_mode"], top)
        if state["top_mode"] == "fixed":
            self._number(fixed_label, state[fixed_key], lambda v: edit(**{fixed_key: v}))
        else:
            self._number("Deslocamento do topo", state["top_offset"],
                         lambda v: edit(top_offset=v))

    def _column(self, column) -> None:
        doc = self.session.doc
        state = columns.read_state(doc, column)
        self._title(f"Pilar {column.Name or ''}".strip())
        self._structure_head(column, state, "IfcColumnType")
        if state["foreign"] is not None:
            self._structure_tail(column, state)
            return
        section = columns.section(doc, state)

        def edit(**changes):
            self._run(lambda: sc.edit_element(doc, column, **changes))

        self._section("Posição")
        x, y = state["point"]
        self._number("X", x, lambda v: edit(point=[v, y]))
        self._number("Y", y, lambda v: edit(point=[x, v]))
        self._number("Ângulo (°)", state["angle"], lambda v: edit(angle=v))
        if section["shape"] == "rect":
            plan_pos = {c: pos for pos, c in profiles.PLAN_CARDINAL.items()}
            self._combo("Inserção", INSERTIONS, plan_pos.get(state["cardinal"]),
                        lambda v: edit(cardinal=profiles.PLAN_CARDINAL[v]))
        self._section("Altura")
        self._number("Base", state["base_offset"], lambda v: edit(base_offset=v))
        height = columns.height(doc, state)
        self._top_fields(column, state, "fixed_height", "Altura fixa", height, TOPS)
        q = ifcopenshell.util.element.get_pset(column, "Qto_ColumnBaseQuantities") or {}
        self._section("Quantidades")
        self._read("Altura", f"{fmt(q.get('Length', 0))} m")
        self._read("Área da seção", f"{fmt(q.get('CrossSectionArea', 0))} m²")
        self._read("Área lateral", f"{fmt(q.get('OuterSurfaceArea', 0))} m²")
        self._read("Volume", f"{fmt(q.get('NetVolume', 0))} m³")
        self._structure_tail(column, state)

    def _beam(self, beam) -> None:
        doc = self.session.doc
        state = beams.read_state(doc, beam)
        self._title(f"Viga {beam.Name or ''}".strip())
        self._structure_head(beam, state, "IfcBeamType")
        if state["foreign"] is not None:
            self._structure_tail(beam, state)
            return

        def edit(**changes):
            self._run(lambda: sc.edit_element(doc, beam, **changes))

        self._section("Geometria")
        (x0, y0), (x1, y1) = state["start"], state["end"]
        length = beams.length(state)
        angle = math.atan2(y1 - y0, x1 - x0)

        def to_end(new_length, new_angle):
            edit(end=[x0 + new_length * math.cos(new_angle),
                      y0 + new_length * math.sin(new_angle)])

        self._number("Comprimento", length, lambda v: to_end(v, angle))
        self._number("Ângulo (°)", math.degrees(angle) % 360.0,
                     lambda v: to_end(length, math.radians(v)))
        self._combo("Linha de referência", REF_LINES, state["ref_line"],
                    lambda v: edit(ref_line=v))
        self._section("Altura")
        self._top_fields(beam, state, "top_elevation", "Cota do topo", beams.top_z(doc, state),
                         BEAM_TOPS)
        q = ifcopenshell.util.element.get_pset(beam, "Qto_BeamBaseQuantities") or {}
        self._section("Quantidades")
        self._read("Comprimento", f"{fmt(q.get('Length', 0))} m")
        self._read("Área da seção", f"{fmt(q.get('CrossSectionArea', 0))} m²")
        self._read("Volume", f"{fmt(q.get('NetVolume', 0))} m³")
        self._structure_tail(beam, state)

    def _slab(self, slab) -> None:
        doc = self.session.doc
        state = slabs.read_state(doc, slab)
        self._title("Laje")
        self._structure_head(slab, state, "IfcSlabType")
        if state["foreign"] is not None:
            self._structure_tail(slab, state)
            return
        thickness = slabs.thickness(doc, state)
        self._read("Espessura", f"{fmt(thickness)} m")
        self._section("Altura")
        self._number("Deslocamento do topo", state["top_offset"], lambda v: self._run(
            lambda: sc.edit_element(doc, slab, top_offset=v)))
        self._read("Cota do topo", f"{fmt(state['top_offset'])} m")
        self._read("Cota do fundo", f"{fmt(state['top_offset'] - thickness)} m")
        q = ifcopenshell.util.element.get_pset(slab, "Qto_SlabBaseQuantities") or {}
        self._section("Quantidades")
        self._read("Área", f"{fmt(q.get('NetArea', 0))} m²")
        self._read("Perímetro", f"{fmt(q.get('Perimeter', 0))} m")
        self._read("Volume", f"{fmt(q.get('NetVolume', 0))} m³")
        self._structure_tail(slab, state)

    def _slab_opening(self, opening) -> None:
        """Abertura na laje (spec/ui 12 §3.3)."""
        outline = slab_openings.read_state(opening)["outline"]
        slab = slab_openings.host(opening)
        self._title("Abertura na laje")
        self._read("Área", f"{fmt(slabs.area(outline))} m²")
        self._read("Perímetro", f"{fmt(slabs.perimeter(outline))} m")
        slab_type = ifcopenshell.util.element.get_type(slab) if slab is not None else None
        self._read("Laje", slab_type.Name if slab_type is not None else "—")
        self._section("Identificação")
        self._read("GlobalId", opening.GlobalId)

    def _structures(self, elements) -> None:
        """Vários pilares, várias vigas ou várias lajes (spec/ui 10 §4.3)."""
        doc = self.session.doc
        _, plural = STRUCTURE_NOUNS[elements[0].is_a()]
        type_class = f"{elements[0].is_a()}Type"
        states = [sc.read_state(doc, e) for e in elements]
        self._section(f"<b>{plural} ({len(elements)})</b>")
        own = [(e, s) for e, s in zip(elements, states, strict=True) if s["foreign"] is None]
        if elements[0].is_a("IfcSlab"):
            self._combo("Tipo", self._types(type_class), _common(s["type"] for s in states),
                        lambda v: self._run(lambda: sc.edit_elements(doc, elements, type=v)))
        elif own:
            module = sc.module_of(elements[0])
            self._section_fields([e for e, _ in own], [module.section(doc, s) for _, s in own])
        if elements[0].is_a("IfcSlab"):
            self._number("Deslocamento do topo", _common(s["top_offset"] for s in states),
                         lambda v: self._run(lambda: sc.edit_elements(doc, elements,
                                                                      top_offset=v)),
                         placeholder=MIXED)
        names = Counter(doc.get(s["type"]).Name if s["type"] else "sem tipo" for s in states)
        for name, n in sorted(names.items()):
            self._read(name, str(n))
        self._structure_common(elements)

    def _structure_common(self, elements) -> None:
        doc = self.session.doc

        def foreign(element):
            return sc.read_state(doc, element)["foreign"] is not None

        def defaults(element):
            if foreign(element):
                return {}
            state = sc.read_state(doc, element)
            return structure_common.common_defaults(doc.find(state["type"]) if state["type"]
                                                    else None)

        def effective(element):
            return {**defaults(element), **sc.read_state(doc, element)["common"]}

        fields = SLAB_COMMON if elements[0].is_a("IfcSlab") else STRUCTURE_COMMON
        self._common_group(elements, fields, effective, defaults,
                           lambda e, common: sc.edit_element(doc, e, common=common))

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
            return doors.type_common_defaults(doc.get(state["type"]))

        def effective(door):
            return {**defaults(door), **doors.read_state(door)["common"]}

        fields = WINDOW_COMMON if door_list[0].is_a("IfcWindow") else DOOR_COMMON
        self._common_group(door_list, fields, effective, defaults,
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
        note.setStyleSheet(f"color: {theme.INK_SOFT}")
        self._add(note)
