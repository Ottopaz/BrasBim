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

import copy
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

from brasbim.core import display_layers, geom2d
from brasbim.core import storeys as storeys_
from brasbim.core.annotations import base as annotation_base
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import dimensions as annotation_dims
from brasbim.core.annotations import drafting, drawing2d
from brasbim.core.annotations import spaces as space_data
from brasbim.core.document import OpError
from brasbim.core.drawings import sheets, views
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params, window_types
from brasbim.core.objects import elements as objects
from brasbim.core.ops.history import combine
from brasbim.core.quantities import tables
from brasbim.core.structure import beams, columns, profiles, roofs, slab_openings, slabs
from brasbim.core.structure import commands as sc
from brasbim.core.structure import common as structure_common
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings, rebuild, top
from brasbim.core.walls import params as wall_params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import common_defaults as wall_common_defaults
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui import icons, theme
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
ROOF_COMMON = [("Reference", "Código", "text"), ("Status", "Situação", "status"),
               ("IsExternal", "Externa", "bool"), ("FireRating", "Resistência ao fogo", "text"),
               ("AcousticRating", "Desempenho acústico", "text")]
ROOF_SHAPES = [("Plana", "flat"), ("Uma água", "shed"), ("Duas águas", "gable"),
               ("Quatro águas", "hip")]
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
        self.open_view = None  # abre um corte ou fachada (posto pela janela principal)
        self.open_sheet = None  # abre uma prancha (idem)
        self.open_table = None  # abre uma tabela (idem)
        self.active_table = None  # tabela da aba à frente: o painel é o dela (spec/ui 17 §5)
        self.edit_project_info = None  # dados do projeto para o carimbo (idem)
        self.edit_object_type = None  # editar tipo de objeto paramétrico (idem)
        self.edit_object = None  # editor do objeto paramétrico (idem)
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
        active = self.session.doc.find(self.active_table) if self.active_table else None
        if active is not None:
            self._table(active)
        elif len(selection) == 1 and tables.is_table(selection[0]):
            self._table(selection[0])
        elif len(selection) == 1 and selection[0].is_a("IfcWall"):
            self._wall(selection[0])
        elif len(selection) == 1 and (selection[0].is_a("IfcDoor")
                                      or selection[0].is_a("IfcWindow")):
            self._door(selection[0])
        elif len(selection) == 1 and selection[0].is_a("IfcSpace"):
            self._space(selection[0])
        elif len(selection) == 1 and sheets.is_sheet(selection[0]):
            self._sheet(selection[0])
        elif len(selection) == 1 and views.is_view(selection[0]):
            self._view(selection[0])
        elif len(selection) == 1 and annotation_base.kind_of(selection[0]) is not None:
            self._annotation(selection[0])
        elif len(selection) == 1 and slab_openings.is_slab_opening(selection[0]):
            self._slab_opening(selection[0])
        elif len(selection) == 1 and objects.is_object(selection[0]):
            self._object(selection[0])
        elif len(selection) == 1 and sc.is_structure(selection[0]):
            {"IfcColumn": self._column, "IfcBeam": self._beam, "IfcSlab": self._slab,
             "IfcRoof": self._roof}[selection[0].is_a()](selection[0])
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
            found_objects = [e for e in selection if objects.is_object(e)]
            if found_objects:
                self._objects(found_objects)
            known = ("IfcWall", "IfcDoor", "IfcWindow", "IfcColumn", "IfcBeam", "IfcSlab")
            others = Counter(e.is_a() for e in selection
                             if not any(e.is_a(c) for c in known) and not objects.is_object(e))
            for cls, n in sorted(others.items()):
                self._add(cls, QLabel(str(n)))
        else:
            self._tool_options()
        if active is None and selection:
            self._layer_field(selection)
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

    def _roof(self, roof) -> None:
        """Cobertura (cobertura.md §5): forma, tipo, inclinação, beiral, apoio e lado."""
        doc = self.session.doc
        state = roofs.read_state(doc, roof)

        def edit(**changes):
            self._run(lambda: sc.edit_element(doc, roof, **changes))

        self._title(state["name"] or "Cobertura")
        self._text("Nome", state["name"], lambda v: edit(name=v or state["name"]))
        self._combo("Forma", ROOF_SHAPES, state["shape"], lambda v: edit(shape=v))
        types = [(t.Name or t.GlobalId, t.GlobalId)
                 for t in sorted(doc.ifc.by_type("IfcSlabType"), key=lambda t: t.Name or "")
                 if t.PredefinedType == "ROOF"]
        self._combo("Tipo", types, state["type"], lambda v: edit(type=v))
        self._edit_type_button("IfcSlabType", state["type"])
        self._read("Espessura", f"{fmt(roofs.thickness(doc, state))} m")
        self._section("Geometria")
        if state["shape"] != "flat":
            degrees = math.degrees(roofs.slope_angle(state))
            self._number("Inclinação (%)", state["slope"], lambda v: edit(slope=v))
            self._read("Em graus", f"{fmt(degrees)}°")
        self._number("Beiral", state["overhang"], lambda v: edit(overhang=v))
        self._number("Altura de apoio", state["base_height"], lambda v: edit(base_height=v))
        if state["shape"] in ("shed", "gable"):
            n = len(state["outline"])
            label = "Lado mais baixo" if state["shape"] == "shed" else "Cumeeira paralela a"
            sides = []
            for i in range(n):
                a, b = state["outline"][i], state["outline"][(i + 1) % n]
                sides.append((f"Lado {i + 1} ({fmt(math.dist(a, b))} m)", i))
            self._combo(label, sides, state["side"], lambda v: edit(side=v))
        q = ifcopenshell.util.element.get_pset(roof, "Qto_RoofBaseQuantities") or {}
        own = ifcopenshell.util.element.get_pset(roof, roofs.PSET) or {}
        self._section("Quantidades")
        self._read("Águas", str(len(state["parts"])))
        self._read("Área do telhado", f"{fmt(q.get('NetArea', 0))} m²")
        self._read("Área em planta", f"{fmt(own.get('AreaProjecao', 0))} m²")

        def defaults(_element):
            return roofs._common_defaults(doc.find(state["type"]) if state["type"] else None)

        self._common_group([roof], ROOF_COMMON,
                           lambda e: {**defaults(e), **roofs.read_state(doc, e)["common"]},
                           defaults, lambda e, common: sc.edit_element(doc, e, common=common))
        self._section("Identificação")
        self._read("GlobalId", roof.GlobalId)

    # --- ambientes e anotações (spec/ui 13) --------------------------------------------

    def _space(self, space) -> None:
        doc = self.session.doc
        state = space_data.read_state(space)

        def edit(**changes):
            self._run(lambda: ac.edit_element(doc, space, **changes))

        self._title(f"Ambiente {state['number'] or ''}".strip())
        self._text("Número", state["number"], lambda v: edit(number=v or state["number"]))
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems([space_data.DEFAULT_NAME, *space_data.NAMES])
        combo.setCurrentText(state["name"] or "")
        combo.lineEdit().editingFinished.connect(
            lambda: combo.currentText().strip() != state["name"]
            and edit(name=combo.currentText().strip() or space_data.DEFAULT_NAME))
        combo.activated.connect(lambda _i: edit(name=combo.currentText()))
        self._add("Nome", combo)
        q = ifcopenshell.util.element.get_pset(space, space_data.QTO) or {}
        self._number("Pé-direito", state["height"], lambda v: edit(height=v),
                     placeholder=f"calculado: {fmt(q.get('Height', 0))}", allow_empty=True)
        self._section("Quantidades")
        self._read("Área", f"{fmt(q.get('NetFloorArea', 0))} m²")
        self._read("Perímetro", f"{fmt(q.get('GrossPerimeter', 0))} m")
        self._read("Pé-direito", f"{fmt(q.get('Height', 0))} m")
        self._section("Identificação")
        self._read("GlobalId", space.GlobalId)

    def _annotation(self, element) -> None:
        doc = self.session.doc
        kind = annotation_base.kind_of(element)
        state = annotation_base.read_state(element)

        def edit(**changes):
            self._run(lambda: ac.edit_element(doc, element, **changes))

        self._title(kind.noun.capitalize())
        sizes = [(f"{fmt(v)} mm", v) for v in drafting.TEXT_SIZES]
        if kind is drafting.TEXT:
            self._text("Texto", state["text"].replace("\n", " / "),
                       lambda v: v and edit(text=v.replace(" / ", "\n")))
            note = QLabel("Clique duplo no texto, na planta, para várias linhas.")
            note.setStyleSheet(f"color: {theme.INK_SOFT}")
            note.setWordWrap(True)
            self._add(note)
            self._combo("Altura", sizes, state["size"], lambda v: edit(size=v))
            self._number("Ângulo (°)", state["angle"], lambda v: edit(angle=v))
            self._combo("Alinhamento", [("Esquerda", "left"), ("Centro", "center"),
                                        ("Direita", "right")], state["align"],
                        lambda v: edit(align=v))
        elif kind is drafting.LINE:
            self._combo("Espessura", [(f"{fmt(w)} mm", w) for w in drafting.LINE_WEIGHTS],
                        state["weight"], lambda v: edit(weight=v))
            self._combo("Tipo", [("Contínua", "solid"), ("Tracejada", "dashed"),
                                 ("Traço e ponto", "dashdot")], state["dash"],
                        lambda v: edit(dash=v))
            self._combo("Fechada", YES_NO, bool(state["closed"]), lambda v: edit(closed=v))
        elif kind is drafting.HATCH:
            self._combo("Padrão", [("Sólida", "solid"), ("Linhas", "lines"),
                                   ("Cruzada", "cross")], state["pattern"],
                        lambda v: edit(pattern=v))
            self._text("Cor", state["color"], lambda v: v and edit(color=v.upper()))
            self._number("Ângulo (°)", state["angle"], lambda v: edit(angle=v))
            self._number("Espaçamento (mm)", state["spacing"], lambda v: edit(spacing=v))
        elif kind is drafting.NORTH:
            self._number("Ângulo (°)", state["angle"], lambda v: edit(angle=v))
        elif kind is drafting.LEVEL:
            storey = doc.get(state["storey"])
            self._read("Valor", drafting.level_text(doc, storey, {**state, "fixed": None}))
            self._text("Valor fixo", state["fixed"], lambda v: edit(fixed=v),
                       placeholder="calculado")
        elif kind in (drawing2d.CIRCLE, drawing2d.ARC, drawing2d.SPLINE):
            if kind is not drawing2d.SPLINE:
                self._number("Raio (m)", state["radius"], lambda v: edit(radius=v))
            if kind is drawing2d.ARC:
                self._number("Início (°)", state["start"], lambda v: edit(start=v))
                self._number("Fim (°)", state["end"], lambda v: edit(end=v))
            if kind is drawing2d.SPLINE:
                self._combo("Fechada", YES_NO, bool(state["closed"]),
                            lambda v: edit(closed=v))
            self._combo("Espessura", [(f"{fmt(w)} mm", w) for w in drafting.LINE_WEIGHTS],
                        state["weight"], lambda v: edit(weight=v))
            self._combo("Tipo", [("Contínua", "solid"), ("Tracejada", "dashed"),
                                 ("Traço e ponto", "dashdot")], state["dash"],
                        lambda v: edit(dash=v))
        elif kind is drawing2d.RADIUS:
            _center, radius = drawing2d._radius_state(doc, state)
            self._read("Medida", f"R {drawing2d.fmt(radius)}")
            self._combo("Mostra", [("Raio", False), ("Diâmetro", True)],
                        bool(state["diameter"]), lambda v: edit(diameter=v))
            self._number("Direção (°)", state["angle"], lambda v: edit(angle=v))
            self._read("Presa", "sim" if state.get("ref") and doc.find(state["ref"])
                       else "não")
        elif kind is drawing2d.ANGLE:
            self._read("Ângulo", f"{drawing2d.angle_value(state):.1f}°".replace(".", ","))
            self._number("Raio do arco (m)", state["radius"], lambda v: edit(radius=v))
        elif kind is drawing2d.LABEL:
            fields = [("Tipo do elemento", "type"), ("Nome do elemento", "name"),
                      ("Código", "code"), ("Texto digitado", "free")]
            if state.get("ref"):
                self._combo("Mostra", fields, state["field"], lambda v: edit(field=v))
            self._text("Texto", state["text"], lambda v: edit(text=v or ""))
            self._read("Mostrando", drawing2d.label_text(doc, state))
        elif kind is drawing2d.REVISION:
            self._text("Número", state["number"], lambda v: v and edit(number=v))
            self._text("Nota", state["note"], lambda v: edit(note=v or ""))
        elif kind is annotation_dims.DIMENSION:
            current = ("aligned" if state["direction"] == "aligned" else
                       "vertical" if abs(state["angle"] % 180.0 - 90.0) < 1e-6 else
                       "horizontal")
            self._combo("Direção", [("Alinhada", "aligned"), ("Horizontal", "horizontal"),
                                    ("Vertical", "vertical")], current,
                        lambda v: edit(direction="aligned" if v == "aligned" else "fixed",
                                       angle=90.0 if v == "vertical" else 0.0))
            self._number("Afastamento", state["offset"], lambda v: edit(offset=v))
            values = annotation_dims.measures(doc, state)
            self._read("Medidas", " · ".join(annotation_dims.fmt(v) for v in values))
            held = sum(1 for p in state["points"] if p.get("ref") and not p.get("lost"))
            self._read("Pontos presos", f"{held} de {len(state['points'])}")
        self._section("Identificação")
        self._read("GlobalId", element.GlobalId)

    def _layer_field(self, selection) -> None:
        """Camada de um ou vários elementos (spec/ui 18 §5): "várias" quando discordam."""
        doc = self.session.doc
        if display_layers.read_config(doc) is None:
            return
        elements = [display_layers.owner(e) for e in selection]
        elements = [e for e in elements if display_layers.layerable(e)]
        if not elements:
            return
        current = {display_layers.layer_of(doc, e) or display_layers.NONE for e in elements}
        self._section("Organização")
        self._combo("Camada", display_layers.choices(doc),
                    current.pop() if len(current) == 1 else None,
                    lambda v: self._run(lambda: display_layers.assign(
                        doc, [e.GlobalId for e in elements], v)))

    def _sheet(self, sheet) -> None:
        """Prancha (spec/ui 15 §5)."""
        doc = self.session.doc
        state = sheets.read_state(sheet)

        def edit(**changes):
            self._run(lambda: sheets.edit_sheet(doc, sheet, **changes))

        self._title(f"Prancha {state['number']}")
        self._text("Número", state["number"], lambda v: v and edit(number=v))
        self._text("Título", state["title"], lambda v: edit(title=v or ""))
        self._combo("Formato", [(f, f) for f in sheets.FORMATS], state["format"],
                    lambda v: edit(format=v))
        self._combo("Orientação", [("Horizontal", "landscape"), ("Vertical", "portrait")],
                    state["orientation"], lambda v: edit(orientation=v))
        self._section("Vistas na prancha")
        config = display_layers.read_config(doc)
        combinations = [("Como na janela", None)] + [
            (c["name"], c["id"]) for c in (config["combinations"] if config else [])]

        def set_combination(index, value):
            items = copy.deepcopy(state["views"])
            items[index].pop("combination", None)
            if value:
                items[index]["combination"] = value
            edit(views=items)

        for i, item in enumerate(state["views"]):
            target = doc.find(item.get("storey") or item.get("view"))
            name = ((f"Planta: {target.Name}" if item["kind"] == "plan"
                     else views.read_state(target)["name"]) if target is not None else "—")
            self._read(name, f"1:{sheets.scale_of(doc, item)}")
            if config is not None:  # combinação de camadas da vista (spec/ui 18 §6.2)
                current = item.get("combination")
                if display_layers.combination(doc, current or "") is None:
                    current = None
                self._combo("  Camadas", combinations, current,
                            lambda v, i=i: set_combination(i, v))
        present = {it.get("storey") or it.get("view") for it in state["views"]}
        options = [(f"Planta: {s.Name}", {"kind": "plan", "storey": s.GlobalId})
                   for s in doc.storeys() if s.GlobalId not in present]
        options += [(views.read_state(v)["name"], {"kind": "view", "view": v.GlobalId})
                    for v in views.all_views(doc) if v.GlobalId not in present]
        if options:
            combo = QComboBox()
            for text, item in options:
                combo.addItem(text, item)
            self._add("Pôr na prancha", combo)
            self._buttons(("Pôr", lambda: self._run(lambda: sheets.add_to_sheet(
                doc, sheet, combo.currentData()))))
        buttons = []
        if self.open_sheet is not None:
            buttons.append(("Abrir a prancha", lambda: self.open_sheet(sheet.GlobalId)))
        if self.edit_project_info is not None:
            buttons.append(("Dados do projeto…", self.edit_project_info))
        if buttons:
            self._buttons(*buttons)

    def _table(self, table) -> None:
        """Definição da tabela (spec/ui 17 §5): cada mudança é um ``table.edit``."""
        doc = self.session.doc
        state = tables.read_state(table)
        fields = tables.fields_of(state["category"], doc)

        def edit(**changes):
            self._run(lambda: tables.edit_table(doc, table, **changes))

        self._title(f"Tabela: {state['name']}" if state["name"] else "Tabela")
        self._text("Nome", state["name"], lambda v: v and edit(name=v))
        self._combo("Categoria", [(c.label, k) for k, c in tables.CATEGORIES.items()],
                    state["category"], lambda v: edit(category=v))
        self._section("Colunas")
        columns = state["columns"]
        chosen = [c["field"] for c in columns]
        order = chosen + [k for k in fields if k not in chosen]
        for key in order:
            self._add(self._column_row(table, state, key, fields[key]))
        self._section("Linhas")
        options = [("Nenhum", None)] + [(f.title, k) for k, f in fields.items()
                                        if not f.sums]
        self._combo("Agrupar por", options, state["group_by"],
                    lambda v: edit(group_by=v))
        self._combo("Linhas", [("Uma por elemento", "element"), ("Uma por grupo", "group")],
                    state["rows"], lambda v: edit(rows=v))
        sort = state["sort"] or {}
        self._combo("Ordenar por", [("Padrão", None)] + [(f.title, k) for k, f in
                                                          fields.items()],
                    sort.get("field"),
                    lambda v: edit(sort={"field": v, "descending": bool(
                        sort.get("descending"))} if v else None))
        if sort:
            self._combo("Sentido", [("Crescente", False), ("Decrescente", True)],
                        bool(sort.get("descending")),
                        lambda v: edit(sort={**sort, "descending": v}))
        totals = QCheckBox("Subtotais e total")
        totals.setChecked(state["totals"])
        totals.toggled.connect(lambda v: edit(totals=v))
        self._add(totals)
        if state["category"] == "spaces":
            built = QCheckBox("Área construída por pavimento")
            built.setChecked(state["built_area"])
            built.setToolTip("Dentro da face externa das paredes; agrupe por pavimento "
                             "e mostre a área útil")
            built.toggled.connect(lambda v: edit(built_area=v))
            self._add(built)
        self._section("Filtro")
        self._choices("Pavimentos", [(s.Name, s.GlobalId) for s in doc.storeys()],
                      state["storeys"], lambda v: edit(storeys=v))
        options = [(t.Name or t.GlobalId, t.GlobalId)
                   for t in tables.type_options(doc, state["category"])]
        if options:
            self._choices("Tipos", options, state["types"], lambda v: edit(types=v))
        if self.open_table is not None and self.active_table != table.GlobalId:
            self._buttons(("Abrir a tabela", lambda: self.open_table(table.GlobalId)))

    def _column_row(self, table, state: dict, key: str, field) -> QWidget:
        """Coluna: marcar, título e posição (subir/descer)."""
        doc = self.session.doc
        columns = [dict(c) for c in state["columns"]]
        index = next((i for i, c in enumerate(columns) if c["field"] == key), None)

        def commit(new):
            self._run(lambda: tables.edit_table(doc, table, columns=new))

        def toggle(checked):
            if checked:
                commit([*columns, {"field": key}])
            elif len(columns) > 1:
                commit([c for c in columns if c["field"] != key])
            else:
                self.session.message("a tabela precisa de ao menos uma coluna", "recusa")
                self.refresh()

        def rename():
            text = title.text().strip()
            new = [dict(c) for c in columns]
            new[index].pop("title", None)
            if text and text != field.heading:
                new[index]["title"] = text
            if new != columns:
                commit(new)

        def move(step):
            new = list(columns)
            j = index + step
            if 0 <= j < len(new):
                new[index], new[j] = new[j], new[index]
                commit(new)

        holder = QWidget()
        holder.setObjectName(f"coluna_{key}")
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        check = QCheckBox()
        check.setChecked(index is not None)
        check.setToolTip(field.heading)
        check.toggled.connect(toggle)
        row.addWidget(check)
        title = QLineEdit(columns[index].get("title", field.heading) if index is not None
                          else field.heading)
        title.setEnabled(index is not None)
        title.setToolTip("Título da coluna")
        title.editingFinished.connect(rename)
        row.addWidget(title, 1)
        for name, step, tip in ((("up", -1, "Subir"), ("down", 1, "Descer"))
                                if index is not None else ()):
            button = QPushButton(icons.icon(name), "")
            button.setToolTip(tip)
            button.setFixedWidth(26)
            button.setEnabled(0 <= index + step < len(columns))
            button.clicked.connect(lambda _=False, s=step: move(s))
            row.addWidget(button)
        return holder

    def _choices(self, label: str, items, chosen, commit) -> None:
        """Lista de marcar; nada marcado = todos."""
        self._read(label, "todos" if not chosen else f"{len(chosen)} de {len(items)}")
        for text, value in items:
            box = QCheckBox(text)
            box.setChecked(value in chosen)

            def toggled(checked, v=value):
                new = [x for _, x in items if (x in chosen or x == v) and (checked or x != v)]
                commit(new)

            box.toggled.connect(toggled)
            self._add(box)

    def _view(self, view) -> None:
        """Corte ou fachada (spec/ui 14 §7)."""
        doc = self.session.doc
        state = views.read_state(view)

        def edit(**changes):
            self._run(lambda: ac.edit_element(doc, view, **changes))

        self._title(state["name"] or "Vista")
        self._text("Nome", state["name"], lambda v: v and edit(name=v))
        self._combo("Lado olhado", [("Esquerda de A→B", "left"), ("Direita de A→B", "right")],
                    state["side"], lambda v: edit(side=v))
        self._number("Profundidade", state["depth"], lambda v: edit(depth=v),
                     placeholder="tudo", allow_empty=True)
        self._combo("Escala", [(f"1:{v}", v) for v in storeys_.SCALES], state["scale"],
                    lambda v: edit(scale=v))
        if self.open_view is not None:
            self._buttons(("Abrir a vista", lambda: self.open_view(view.GlobalId)))
        self._section("Identificação")
        self._read("GlobalId", view.GlobalId)

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

    # --- objeto paramétrico (objeto-parametrico.md §5.1) -------------------------------

    def _object_params(self, defn: dict, values: dict, stored: dict, commit) -> None:
        """Parâmetros de ocorrência em grupos; os calculados só para ler, com a fórmula na
        dica."""
        from brasbim.core.objects import definition as od
        from brasbim.core.objects import formula as fm
        from brasbim.ui import object_widgets as ow

        doc = self.session.doc
        params = [p for p in od.occurrence_params(defn) if p["name"] != "elevacao"]
        for group in od.GROUPS:
            found = [p for p in params if p.get("group", "Outros") == group]
            if not found:
                continue
            self._section(group)
            for p in found:
                value = values.get(fm.key(p["name"]))
                if od.editable(p):
                    widget = ow.param_widget(p, stored.get(p["name"], value),
                                             lambda v, n=p["name"]: commit(n, v), doc)
                    self._add(ow.label(p), widget)
                else:
                    shown = QLabel(ow.value_text(p, value))
                    shown.setStyleSheet(f"color: {theme.INK_SOFT}")
                    shown.setToolTip(f"Calculado: = {p['formula']}")
                    self._add(ow.label(p), shown)

    def _object(self, element) -> None:
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import definition as od
        from brasbim.core.objects import elements as objects
        from brasbim.core.objects import formula as fm
        from brasbim.core.objects import types as ot
        from brasbim.ui import object_widgets as ow

        doc = self.session.doc
        state = objects.read_state(doc, element)
        element_type = doc.get(state["type"])
        tstate = ot.read(element_type)
        defn = tstate["definition"]
        try:
            values = objects.values_of(doc, element)
        except OpError:
            values = {}

        def edit(**changes):
            self._run(lambda: oc.edit_object(doc, element, **changes))

        self._title(defn["name"])
        types = [(t.Name, t.GlobalId) for t in oc.compatible_types(doc, element)]
        self._combo("Tipo", types, state["type"],
                    lambda v: self._run(lambda: oc.change_type(doc, [element.GlobalId], v)))
        buttons = [("Editar tipo…", lambda: self.edit_object_type(element_type.GlobalId))]
        if self.edit_object is not None:
            buttons.append(("Editar objeto…", lambda: self.edit_object(defn["object_id"])))
        self._buttons(*buttons)
        self._section("Posição")
        host = state["host"]
        if host is not None:
            wall = doc.find(host["wall"])
            self._read("Parede", (wall.Name or "parede") if wall else "—")
            self._combo("Face", [("Esquerda", "left"), ("Direita", "right")], host["side"],
                        lambda v: edit(host={**host, "side": v}))
            self._number("Distância (m)", host["distance"],
                         lambda v: edit(host={**host, "distance": v}))
            self._number("Altura (m)", values.get("elevacao", 0.0),
                         lambda v: edit(values={"elevacao": v}))
            self._buttons(("Soltar da parede",
                           lambda: self._run(lambda: oc.detach(doc, element))))
        else:
            self._number("Rotação (°)", state["angle"], lambda v: edit(angle=v))
            self._number("Elevação (m)", values.get("elevacao", 0.0),
                         lambda v: edit(values={"elevacao": v}))
            if defn["hosting"] == "wall":
                note = QLabel("Solto da parede: mova para perto de uma parede e use "
                              "Prender à parede no menu do botão direito.")
                note.setWordWrap(True)
                note.setStyleSheet(f"color: {theme.INK_SOFT}")
                self._add(note)
        mirror = QCheckBox()
        mirror.setChecked(bool(state["mirror"]))
        mirror.toggled.connect(lambda v: edit(mirror=bool(v)))
        self._add("Espelhado", mirror)
        self._object_params(defn, values, state["values"],
                            lambda name, v: edit(values={name: v}))
        self._section("Parâmetros do tipo")
        users = len(oc.occurrences(doc, element_type))
        type_values = {}
        try:
            type_values = ot.evaluate(tstate, level="type")
        except OpError:
            pass
        for p in od.type_params(defn):
            if p["name"] == "descricao" and not type_values.get("descricao"):
                continue
            shown = QLabel(ow.value_text(p, type_values.get(fm.key(p["name"]))))
            shown.setStyleSheet(f"color: {theme.INK_SOFT}")
            shown.setToolTip(f"Do tipo {element_type.Name}: mudar vale para as {users} "
                             "ocorrência(s); use Editar tipo…" + (
                                 f"\nCalculado: = {p['formula']}" if p.get("formula") else ""))
            self._add(ow.label(p), shown)
        self._section("Identificação")
        self._read("GlobalId", element.GlobalId)

    def _objects(self, elements_) -> None:
        """Vários objetos (§5.1): os parâmetros que todos têm; "vários" onde diferem."""
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import definition as od
        from brasbim.core.objects import elements as objects
        from brasbim.core.objects import formula as fm
        from brasbim.core.objects import types as ot
        from brasbim.ui import object_widgets as ow

        doc = self.session.doc
        gids = [e.GlobalId for e in elements_]
        self._section(f"Objetos ({len(elements_)})")
        states = [objects.read_state(doc, e) for e in elements_]
        defns = [ot.read(doc.get(s["type"]))["definition"] for s in states]
        values = []
        for e in elements_:
            try:
                values.append(objects.values_of(doc, e))
            except OpError:
                values.append({})
        classes = {e.is_a() for e in elements_}
        if len(classes) == 1:
            common = None
            for e in elements_:
                ids = {t.GlobalId for t in oc.compatible_types(doc, e)}
                common = ids if common is None else common & ids
            items = [(t.Name, t.GlobalId) for t in ot.all_types(doc) if t.GlobalId in common]
            current = _common([s["type"] for s in states])
            self._combo("Tipo", items, current,
                        lambda v: self._run(lambda: oc.change_type(doc, gids, v)))

        def key_of(p):
            return (fm.key(p["name"]), p["kind"])

        shared = None
        for defn in defns:
            found = {key_of(p): p for p in od.occurrence_params(defn) if od.editable(p)}
            shared = found if shared is None else {k: v for k, v in shared.items()
                                                   if k in found}
        for k, p in sorted((shared or {}).items(), key=lambda kv: kv[1]["label"]):
            current = _common([v.get(k[0]) for v in values])

            def commit(v, name=p["name"]):
                self._run(lambda: oc.edit_objects(doc, gids, values={name: v}))

            widget = ow.param_widget(p, current, commit, doc)
            if current is None and isinstance(widget, QLineEdit):
                widget.setPlaceholderText(MIXED)
            self._add(ow.label(p), widget)

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
