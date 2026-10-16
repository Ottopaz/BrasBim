# SPDX-License-Identifier: GPL-3.0-or-later
"""Barras Ferramentas, Histórico e Opções (``spec/ui/03-barras-e-icones.md`` §2 e §4).

Barras comuns do Qt: vão para qualquer borda da janela ou ficam soltas. A barra Opções
é uma só e troca de conteúdo conforme a ferramenta ativa.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QToolBar, QWidget

from brasbim.core.fillings import params
from brasbim.core.structure import profiles
from brasbim.core.walls import types as wall_types
from brasbim.ui import icons, theme
from brasbim.ui.tools import (
    BeamTool,
    ColumnTool,
    SlabOpeningTool,
    SlabTool,
    WindowTool,
    _FillingTool,
    _WallTool,
    fmt,
    parse_number,
)

# (ferramenta, ícone, nome, uso) — o uso vai na dica e na barra de estado (§3).
ICON_PX = 20  # ícones das barras (spec/ui 11 §3)

CREATE_TOOLS = [
    ("select", "select", "Selecionar",
     "clique para selecionar; Ctrl+clique soma; arraste no vazio para selecionar por janela"),
    ("wall", "wall", "Parede",
     "escolha a forma, o tipo e a linha de referência na barra de opções"),
    ("door", "door", "Porta",
     "passe o cursor sobre uma parede reta e clique; Tab digita a distância"),
    ("window", "window", "Janela",
     "passe o cursor sobre uma parede reta e clique; Tab digita a distância e o peitoril"),
    # Estrutura na ordem em que se costuma lançar (spec/ui 10 §2).
    ("column", "column", "Pilar",
     "clique o ponto de inserção; barra de espaço gira 90°"),
    ("beam", "beam", "Viga",
     "clique o início e o fim; continua do último ponto; Esc ou clique duplo encerra"),
    ("slab", "slab", "Laje",
     "polígono (feche no primeiro ponto) ou retângulo por dois cantos"),
]
WALL_FORMS = [
    ("wall", "wall_line", "Parede reta",
     "clique os pontos; Enter, clique duplo ou botão direito encerra"),
    ("arc", "wall_arc", "Parede em arco", "clique o início, um ponto do arco e o fim"),
    ("rectangle", "wall_rect", "Retângulo de paredes", "clique dois cantos opostos"),
]
REF_LINES = [("left_face", "ref_left", "Face esquerda",
              "a linha clicada é a face esquerda de quem anda do início ao fim"),
             ("axis", "ref_axis", "Eixo", "a linha clicada é o eixo da parede"),
             ("right_face", "ref_right", "Face direita",
              "a linha clicada é a face direita de quem anda do início ao fim")]
HINGES = [("left", "hinge_left", "Dobradiças à esquerda", "vista de quem empurra a folha"),
          ("right", "hinge_right", "Dobradiças à direita", "vista de quem empurra a folha")]
_SEEN = "vista do lado oposto ao da abertura"
HANDS = [("left", "hinge_left", "Mão esquerda", f"dobradiças à esquerda, {_SEEN}"),
         ("right", "hinge_right", "Mão direita", f"dobradiças à direita, {_SEEN}")]
TOPS = [("Pavimento de cima", "storey"), ("Altura fixa", "fixed")]
ALIGNS = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
SLAB_MODES = [("polygon", "slab", "Polígono",
               "clique os vértices; feche no primeiro ponto, com clique duplo ou Enter"),
              ("rectangle", "wall_rect", "Retângulo", "clique dois cantos opostos")]
BEAM_TOPS = [("Pavimento de cima", "storey"), ("Cota fixa", "fixed")]
SECTIONS = [("Retangular", "rect"), ("Circular", "circle")]


class InsertionPicker(QWidget):
    """Quadradinho de 9 pontos: ponto de inserção do pilar na seção, como visto na planta
    (spec/ui 10 §3). Na seção circular, só o centro."""

    SIZE = 26

    def __init__(self, current: tuple[int, int], commit, center_only: bool = False):
        super().__init__()
        self.current, self.commit, self.center_only = current, commit, center_only
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setToolTip("Ponto de inserção do pilar na seção")
        self.setCursor(Qt.PointingHandCursor)

    def _point(self, col: int, row: int) -> QPointF:
        m = 5
        step = (self.SIZE - 2 * m) / 2
        return QPointF(m + col * step, self.SIZE - m - row * step)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(theme.INK_SOFT), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(self._point(0, 2), self._point(2, 0)))
        for col in range(3):
            for row in range(3):
                on = (col, row) == self.current
                usable = not self.center_only or (col, row) == (1, 1)
                color = QColor(theme.ACCENT if on else theme.INK if usable else theme.RULE_SOFT)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                r = 3.2 if on else 2.0
                painter.drawEllipse(self._point(col, row), r, r)
        painter.end()

    def mousePressEvent(self, event):
        if self.center_only:
            return
        p = event.position()
        best = min(((col, row) for col in range(3) for row in range(3)),
                   key=lambda c: (self._point(*c) - p).manhattanLength())
        self.current = best
        self.update()
        self.commit(best)


def make_action(parent, icon_name: str, name: str, usage: str = "",
                checkable: bool = False) -> QAction:
    action = QAction(icons.icon(icon_name), name, parent)
    tip = f"{name} — {usage}" if usage else name
    action.setToolTip(tip)
    action.setStatusTip(tip)
    action.setCheckable(checkable)
    return action


def _bar(title: str, name: str, parent) -> QToolBar:
    bar = QToolBar(title, parent)
    bar.setObjectName(name)
    bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    bar.setIconSize(QSize(ICON_PX, ICON_PX))
    bar.setMovable(True)
    bar.setFloatable(True)
    bar.setAllowedAreas(Qt.AllToolBarAreas)
    return bar


class ToolsBar(QToolBar):
    def __init__(self, window):
        super().__init__("Ferramentas", window)
        self.setObjectName("barra_ferramentas")
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setIconSize(QSize(ICON_PX, ICON_PX))
        self.setAllowedAreas(Qt.AllToolBarAreas)
        group = QActionGroup(self)
        self.actions_by_tool = {}
        for tool, icon_name, name, usage in CREATE_TOOLS:
            action = make_action(self, icon_name, name, usage, checkable=True)
            if tool == "wall":
                action.triggered.connect(lambda _=False: window.activate_tool(
                    window.toolbox.wall_form))
            else:
                action.triggered.connect(lambda _=False, t=tool: window.activate_tool(t))
            group.addAction(action)
            self.addAction(action)
            self.actions_by_tool[tool] = action

    def mark(self, tool_name: str) -> None:
        key = "wall" if tool_name in ("wall", "arc", "rectangle") else tool_name
        action = self.actions_by_tool.get(key)
        if action is not None:
            action.setChecked(True)
        else:  # ferramenta da mini-barra: nenhuma de criação marcada
            for a in self.actions_by_tool.values():
                a.setChecked(False)


def history_bar(window) -> QToolBar:
    bar = _bar("Histórico", "barra_historico", window)
    window.undo_action.setIcon(icons.icon("undo"))
    window.redo_action.setIcon(icons.icon("redo"))
    bar.addAction(window.undo_action)
    bar.addAction(window.redo_action)
    return bar


class OptionsBar(QToolBar):
    """Opções da ferramenta de criação ativa (§4); escondida nas outras."""

    def __init__(self, window):
        super().__init__("Opções", window)
        self.setObjectName("barra_opcoes")
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setAllowedAreas(Qt.AllToolBarAreas)
        self.window_ = window
        self.tool = None
        self.wanted = True  # o usuário pode fechar a barra (Exibir > Barras)

    def _clear(self) -> None:
        for action in list(self.actions()):
            self.removeAction(action)
            widget = getattr(action, "defaultWidget", lambda: None)()
            if widget is not None:
                widget.deleteLater()
            action.deleteLater()

    def show_for(self, tool) -> None:
        self.tool = tool
        self._clear()
        if isinstance(tool, BeamTool):
            self._beam(tool)
        elif isinstance(tool, SlabOpeningTool):
            self._choices(SLAB_MODES, tool.options.mode,
                          lambda v: setattr(tool.options, "mode", v))
        elif isinstance(tool, SlabTool):
            self._slab(tool)
        elif isinstance(tool, _WallTool):
            self._wall(tool)
        elif isinstance(tool, ColumnTool):
            self._column(tool)
        elif isinstance(tool, _FillingTool):
            self._door(tool)
        else:
            self.hide()
            return
        if self.wanted:
            self.show()

    def refresh(self) -> None:
        if self.tool is not None and self.isVisible():
            self.show_for(self.tool)

    # --- peças -----------------------------------------------------------------------

    def _label(self, text: str) -> None:
        label = QLabel(f" {text} ")
        label.setStyleSheet(f"color: {theme.INK_SOFT}")
        self.addWidget(label)

    def _choices(self, items, current, commit) -> None:
        group = QActionGroup(self)
        for value, icon_name, name, usage in items:
            action = make_action(self, icon_name, name, usage, checkable=True)
            action.setChecked(value == current)
            action.setData(value)
            action.triggered.connect(lambda _=False, v=value: commit(v))
            group.addAction(action)
            self.addAction(action)

    def _combo(self, items, current, commit, tip: str) -> QComboBox:
        combo = QComboBox()
        combo.setToolTip(tip)
        for item in items:
            text, value, *rest = item
            if rest:
                combo.addItem(rest[0], text, value)
            else:
                combo.addItem(text, value)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.currentIndexChanged.connect(lambda i: commit(combo.itemData(i)))
        self.addWidget(combo)
        return combo

    def _number(self, value, commit, tip: str, placeholder: str = "",
                allow_empty: bool = False) -> QLineEdit:
        field = QLineEdit("" if value is None else fmt(value))
        field.setFixedWidth(64)
        field.setToolTip(tip)
        field.setPlaceholderText(placeholder)

        def done():
            text = field.text().strip()
            if not text and allow_empty:
                commit(None)
                return
            try:
                commit(parse_number(text))
                field.setStyleSheet("")
            except ValueError:
                field.setStyleSheet(f"QLineEdit {{ background: {theme.ERROR_SOFT}; "
                                    f"border-color: {theme.ERROR}; }}")

        field.editingFinished.connect(done)
        self.addWidget(field)
        return field

    def _types(self, ifc_class: str):
        doc = self.window_.session.doc
        return sorted(doc.ifc.by_type(ifc_class), key=lambda t: t.Name or "")

    # --- parede (§4.1) --------------------------------------------------------------

    def _wall(self, tool) -> None:
        window, options = self.window_, tool.options
        self._choices(WALL_FORMS, tool.name, window.activate_tool)
        self.addSeparator()
        self._label("Tipo")
        items = [(t.Name, t.GlobalId, icons.icon_from(icons.swatch(wall_types.plan_style(t))))
                 for t in self._types("IfcWallType")]

        def set_type(gid):
            options.type = gid
            window.properties.refresh()

        self.type_combo = self._combo(items, options.type, set_type, "Tipo da próxima parede")
        edit = make_action(self, "edit_type", "Editar tipo",
                           "abre o tipo escolhido na janela de tipos de parede")
        edit.triggered.connect(lambda: window.edit_type("IfcWallType", options.type))
        self.addAction(edit)
        self.addSeparator()
        self._choices(REF_LINES, options.ref_line, lambda v: setattr(options, "ref_line", v))
        self.addSeparator()
        self._label("Topo")

        def set_top(value):
            options.top = value
            self.show_for(tool)

        self._combo(TOPS, options.top, set_top, "Topo da próxima parede")
        if options.top == "fixed":
            self._number(options.fixed_height, lambda v: setattr(options, "fixed_height", v),
                         "Altura da parede (m)")

    # --- porta (§4.2) ---------------------------------------------------------------

    def _door(self, tool) -> None:
        """Porta (§4.2) e janela (spec/ui 09 §3)."""
        window = self.window_
        is_window = isinstance(tool, WindowTool)
        type_class = tool.type_class
        self._label("Tipo")
        variants = {t.GlobalId for t in self._types(type_class)
                    if params.base_name(t.Name or "") != (t.Name or "")}
        items = [(t.Name, t.GlobalId) for t in self._types(type_class)
                 if t.GlobalId not in variants or t.GlobalId == tool.type]

        def set_type(gid):
            tool.type = gid
            self.show_for(tool)

        self._combo(items, tool.type, set_type, f"Tipo da próxima {tool.noun}")
        edit = make_action(self, "edit_type", "Editar tipo",
                           f"abre o tipo escolhido na janela de tipos de {tool.noun}")
        edit.triggered.connect(lambda: window.edit_type(type_class, tool.type))
        self.addAction(edit)
        self.addSeparator()
        tstate = tool.type_state()
        defaults = tstate["defaults"] if tstate else {"width": 0, "height": 0, "base": 0}
        base = "Peitoril" if is_window else "Base"
        for key, name in (("width", "Largura"), ("height", "Altura"), ("base", base)):
            self._label(name)
            self._number(getattr(tool, key), lambda v, k=key: setattr(tool, k, v),
                         f"{name} do vão (vazio = do tipo)",
                         placeholder=fmt(defaults[key]), allow_empty=True)
        if tstate and tool.hand(tstate) is not None:
            self.addSeparator()
            self._choices(HANDS if is_window else HINGES, tool.hinges,
                          lambda v: setattr(tool, "hinges", v))
        self.addSeparator()
        self._label("Marco")
        self._combo(ALIGNS, tool.align, lambda v: setattr(tool, "align", v),
                    "Alinhamento do marco na parede")
        self._number(tool.offset, lambda v: setattr(tool, "offset", v),
                     "Deslocamento do marco (m)")

    # --- pilar, viga e laje (spec/ui 10 §3) ----------------------------------------------

    def _type_group(self, ifc_class: str, holder, commit, noun: str) -> None:
        """Tipo e Editar tipo; ``holder.type`` é o tipo escolhido."""
        window = self.window_
        self._label("Tipo")
        self._combo([(t.Name, t.GlobalId) for t in self._types(ifc_class)], holder.type,
                    commit, f"Tipo {noun}")
        edit = make_action(self, "edit_type", "Editar tipo",
                           f"abre o tipo escolhido na janela de tipos {noun}")
        edit.triggered.connect(lambda: window.edit_type(ifc_class, holder.type))
        self.addAction(edit)

    def _size(self, holder, key: str, label: str, tip: str) -> None:
        """Dimensão da seção digitada na hora (decisão do revisor, 2026‑10‑16)."""
        def commit(value):
            if value <= profiles.MIN_SIZE:
                self.window_.session.message(
                    f"{label}: a dimensão deve passar de {fmt(profiles.MIN_SIZE)} m", "recusa")
                self.show_for(self.tool)
                return
            setattr(holder, key, value)

        self._label(label)
        self._number(getattr(holder, key), commit, tip)

    def _column(self, tool) -> None:
        self._label("Seção")

        def set_shape(value):
            tool.shape = value
            self.show_for(tool)

        self._combo(SECTIONS, tool.shape, set_shape, "Forma da seção do próximo pilar")
        if tool.shape == "circle":
            self._size(tool, "d", "Ø", "Diâmetro do pilar (m)")
        else:
            self._size(tool, "b", "b", "Largura do pilar, ao longo do ângulo (m)")
            self._size(tool, "h", "h", "Profundidade do pilar (m)")
        self.addSeparator()
        self._label("Inserção")
        circle = tool.shape == "circle"
        self.addWidget(InsertionPicker(tool.insertion, lambda v: setattr(tool, "insertion", v),
                                       center_only=circle))
        self._label("Ângulo")
        self.angle_field = self._number(tool.angle, lambda v: setattr(tool, "angle", v),
                                        "Ângulo do pilar (graus, anti-horário)")
        self.addSeparator()
        self._label("Base")
        self._number(tool.base_offset, lambda v: setattr(tool, "base_offset", v),
                     "Deslocamento da base (m)")
        self._label("Topo")

        def set_top(value):
            tool.top = value
            self.show_for(tool)

        self._combo(TOPS, tool.top, set_top, "Topo do próximo pilar")
        if tool.top == "fixed":
            self._number(tool.fixed_height, lambda v: setattr(tool, "fixed_height", v),
                         "Altura do pilar (m)")
        else:
            self._number(tool.top_offset, lambda v: setattr(tool, "top_offset", v),
                         "Deslocamento do topo (m)")

    def _beam(self, tool) -> None:
        options = tool.options
        self._size(options, "b", "b", "Largura da viga (m)")
        self._size(options, "h", "h", "Altura da viga (m)")
        self.addSeparator()
        self._choices(REF_LINES, options.ref_line, lambda v: setattr(options, "ref_line", v))
        self.addSeparator()
        self._label("Topo")

        def set_top(value):
            options.top = value
            self.show_for(tool)

        self._combo(BEAM_TOPS, options.top, set_top, "Topo da próxima viga")
        if options.top == "fixed":
            self._number(options.top_elevation, lambda v: setattr(options, "top_elevation", v),
                         "Cota do topo, a partir do pavimento (m)")
        else:
            self._number(options.top_offset, lambda v: setattr(options, "top_offset", v),
                         "Deslocamento do topo (m)")

    def _slab(self, tool) -> None:
        options = tool.options

        def set_type(gid):
            options.type = gid
            self.show_for(tool)

        self._type_group("IfcSlabType", options, set_type, "da próxima laje")
        self.addSeparator()

        def set_mode(value):
            tool.cancel()
            tool.points = []
            options.mode = value

        self._choices(SLAB_MODES, options.mode, set_mode)
        self.addSeparator()
        self._label("Deslocamento do topo")
        self._number(options.top_offset, lambda v: setattr(options, "top_offset", v),
                     "Cota da face de cima em relação ao pavimento (m)")
