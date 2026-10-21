# SPDX-License-Identifier: GPL-3.0-or-later
"""Barras Ferramentas, Histórico e Opções (``spec/ui/03-barras-e-icones.md`` §2 e §4).

Barras comuns do Qt: vão para qualquer borda da janela ou ficam soltas. A barra Opções
é uma só e troca de conteúdo conforme a ferramenta ativa.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QToolBar, QWidget

from brasbim.core import display_layers
from brasbim.core.annotations import drafting
from brasbim.core.annotations import spaces as space_data
from brasbim.core.fillings import params
from brasbim.core.structure import profiles, roofs
from brasbim.core.walls import types as wall_types
from brasbim.ui import icons, theme
from brasbim.ui.tools import (
    BeamTool,
    ColumnTool,
    DimensionTool,
    DoorTool,
    GridTool,
    HatchTool,
    LabelTool,
    LevelTool,
    LineTool,
    NorthTool,
    ObjectTool,
    RadiusDimTool,
    RailingTool,
    RevisionTool,
    RoofTool,
    SkylightTool,
    SlabOpeningTool,
    SlabTool,
    SpaceTool,
    SplineTool,
    StairTool,
    TerrainTool,
    TextTool,
    ViewTool,
    WallOpeningTool,
    WindowTool,
    _ClickTool,
    _FillingTool,
    _WallTool,
    floor_types,
    fmt,
    parse_number,
    roof_types,
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
    ("wall_opening", "wall_opening", "Vão",
     "vão passante ou nicho: passe o cursor sobre uma parede reta e clique"),
    # Estrutura na ordem em que se costuma lançar (spec/ui 10 §2).
    ("column", "column", "Pilar",
     "clique o ponto de inserção; barra de espaço gira 90°"),
    ("beam", "beam", "Viga",
     "clique o início e o fim; continua do último ponto; Esc ou clique duplo encerra"),
    ("slab", "slab", "Laje",
     "polígono (feche no primeiro ponto) ou retângulo por dois cantos"),
    ("roof", "roof", "Cobertura",
     "clique dentro da edificação, ou desenhe o contorno de apoio; escolha a forma na barra"),
    ("skylight", "skylight", "Claraboia",
     "clique o centro sobre uma laje ou cobertura; barra de espaço gira 90°"),
    ("stair", "stair", "Escada",
     "clique o canto direito do primeiro degrau e a direção de subida; forma na barra"),
    ("railing", "railing", "Guarda-corpo", "clique os pontos; Enter ou clique duplo encerra"),
    ("object", "object", "Objeto",
     "escolha o objeto na barra de opções e clique; barra de espaço gira 90°"),
    ("grid", "grid", "Eixos", "clique a origem e a direção; espaçamentos na barra de opções"),
    ("terrain", "terrain", "Terreno",
     "clique os pontos; Tab digita a cota de cada um; Enter encerra"),
]
# Grupo Documentação (spec/ui 13 §9): anotação da planta.
DOC_TOOLS = [
    ("space", "space", "Ambiente", "clique dentro de um cômodo, ou desenhe o contorno"),
    ("dimension", "dimension", "Cota",
     "clique os pontos (nos elementos a cota fica presa) e depois a posição da linha"),
    ("radius_dim", "radius_dim", "Cota de raio",
     "clique sobre um círculo, um arco ou uma parede em arco e onde vai o texto"),
    ("angle_dim", "angle_dim", "Cota de ângulo",
     "clique o vértice, um ponto em cada lado e onde passa o arco"),
    ("level_mark", "level_mark", "Nível", "clique onde vai a cota de nível"),
    ("text", "text", "Texto", "clique e digite o texto"),
    ("label", "label", "Rótulo",
     "clique a ponta da seta sobre o elemento e onde vai o texto"),
    ("line2d", "line2d", "Linha", "clique os pontos; Enter ou clique duplo encerra"),
    ("spline2d", "spline2d", "Curva", "clique os pontos por onde ela passa; Enter encerra"),
    ("circle2d", "circle2d", "Círculo", "clique o centro e um ponto; Tab digita o raio"),
    ("arc2d", "arc2d", "Arco", "clique o início, um ponto do arco e o fim"),
    ("hatch", "hatch", "Hachura", "polígono ou retângulo"),
    ("north", "north", "Norte", "clique a posição e a direção"),
    ("revision", "revision", "Alteração", "dois cantos da área alterada (nuvem e número)"),
    ("section", "section", "Corte", "clique os dois pontos da linha e o lado olhado"),
    ("elevation", "elevation", "Fachada",
     "clique os dois pontos da linha, fora do edifício, e o lado olhado"),
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
SLAB_ROOM = ("room", "slab_room", "Pelo cômodo",
             "clique dentro de um cômodo fechado por paredes")
ROOF_MODES = [("room", "slab_room", "Pelas paredes",
               "clique dentro da edificação: apoia no contorno externo das paredes"),
              *SLAB_MODES]
ROOF_SHAPES = [("flat", "roof_flat", "Plana", "uma peça horizontal"),
               ("shed", "roof_shed", "Uma água", "depois do contorno, clique o lado mais baixo"),
               ("gable", "roof_gable", "Duas águas",
                "depois do contorno, clique um lado paralelo à cumeeira (só retângulo)"),
               ("hip", "roof_hip", "Quatro águas", "cumeeira no meio do lado maior (só retângulo)")]
ROOM_BOUNDARIES = [("Face externa", "outer"), ("Eixo das paredes", "axis"),
                   ("Face interna", "inner")]
BEAM_TOPS = [("Pavimento de cima", "storey"), ("Cota fixa", "fixed")]
SECTIONS = [("Retangular", "rect"), ("Circular", "circle")]
DIM_DIRECTIONS = [("aligned", "dimension", "Alinhada", "paralela aos dois primeiros pontos"),
                  ("horizontal", "ref_axis", "Horizontal", "mede só a distância em x"),
                  ("vertical", "ref_left", "Vertical", "mede só a distância em y")]
DASHES = [("Contínua", "solid"), ("Tracejada", "dashed"), ("Traço e ponto", "dashdot")]
ALIGN_TEXT = [("Esquerda", "left"), ("Centro", "center"), ("Direita", "right")]
HATCHES = [("Sólida", "solid"), ("Linhas", "lines"), ("Cruzada", "cross")]
SPACE_MODES = [("room", "slab_room", "Pelo cômodo",
                "clique dentro de um cômodo fechado por paredes"),
               ("polygon", "space", "Polígono", "clique os vértices do contorno")]


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
        self.addSeparator()
        for tool, icon_name, name, usage in DOC_TOOLS:
            action = make_action(self, icon_name, name, usage, checkable=True)
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


def tool_kind(tool) -> str | None:
    """Ferramenta de criação → tipo de elemento (chave das camadas padrão, spec/ui 18)."""
    if isinstance(tool, ObjectTool):  # a camada vem da categoria do objeto escolhido
        from brasbim.core.objects import elements as objects

        t = tool.type_entity()
        return objects.kind_of_type(t) if t is not None else None
    if isinstance(tool, GridTool):
        return "grid"
    if isinstance(tool, SkylightTool):
        return "window"
    for cls, kind in ((StairTool, "stair"), (RailingTool, "railing"),
                      (TerrainTool, "terrain")):
        if isinstance(tool, cls):
            return kind
    for cls, kind in ((_ClickTool, None), (RevisionTool, "revision")):
        if isinstance(tool, cls):
            return getattr(tool, "prefix", kind)
    if isinstance(tool, SplineTool):
        return "spline2d"
    for cls, kind in ((SpaceTool, "space"), (HatchTool, "hatch"), (LineTool, "line2d"),
                      (TextTool, "text"), (DimensionTool, "dimension"), (NorthTool, "north"),
                      (ViewTool, "view"), (LevelTool, "level_mark"), (BeamTool, "beam"),
                      (SlabOpeningTool, None), (RoofTool, "roof"), (SlabTool, "slab"),
                      (_WallTool, "wall"), (ColumnTool, "column"), (WindowTool, "window"),
                      (DoorTool, "door")):
        if isinstance(tool, cls):
            return kind
    return None


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
        if isinstance(tool, StairTool):
            o = tool.options
            self._combo([("Reta", "straight"), ("Em L", "L"), ("Em U", "U")], o.shape,
                        lambda v: (setattr(o, "shape", v), self.show_for(tool)),
                        "Forma da escada")
            self._label("Largura")
            self._number(o.width, lambda v: setattr(o, "width", v), "Largura da escada (m)")
            if o.shape != "straight":
                self._combo([("Giro à esquerda", "left"), ("Giro à direita", "right")],
                            o.turn, lambda v: setattr(o, "turn", v),
                            "Para que lado o segundo lance vira")
            self._combo([("Guarda-corpo dos dois lados", "both"),
                         ("Guarda-corpo à esquerda", "left"),
                         ("Guarda-corpo à direita", "right"), ("Sem guarda-corpo", "none")],
                        o.railing, lambda v: setattr(o, "railing", v),
                        "Lados com guarda-corpo (de quem sobe)")
        elif isinstance(tool, RailingTool):
            o = tool.options
            for key, name in (("height", "Altura"), ("base", "Base"),
                              ("spacing", "Montantes a cada")):
                self._label(name)
                self._number(getattr(o, key), lambda v, k=key: setattr(o, k, v),
                             f"{name} (m)" + (" acima do piso do pavimento"
                                              if key == "base" else ""))
        elif isinstance(tool, TerrainTool):
            o = tool.options
            self._combo([("Contorno", "outline"), ("Pontos cotados", "points")], o.mode,
                        lambda v: (setattr(o, "mode", v), tool.cancel(), self.show_for(tool)),
                        "Desenhar o contorno do terreno ou pontos com cota")
            if o.mode == "outline":
                self._label("Cota do contorno")
                self._number(o.boundary_z, lambda v: setattr(o, "boundary_z", v),
                             "Cota do contorno (m); vazio: calculada pelas curvas de nível",
                             placeholder="pelas curvas", allow_empty=True)
            else:
                self._label("Cota")
                self._number(o.z, lambda v: setattr(o, "z", v),
                             "Cota do próximo ponto (m); Tab digita junto ao cursor")
            self._label("Curvas a cada")
            self._number(o.interval, lambda v: setattr(o, "interval", v),
                         "Intervalo das curvas de nível (m)")
        elif isinstance(tool, SkylightTool):
            for key, name in (("width", "Largura"), ("length", "Comprimento"),
                              ("angle", "Ângulo")):
                self._label(name)
                self._number(getattr(tool, key), lambda v, k=key: setattr(tool, k, v),
                             f"{name} da claraboia" + (" (graus)" if key == "angle"
                                                         else " (m)"))
        elif isinstance(tool, WallOpeningTool):
            o = tool.options
            self._choices([("OPENING", "wall_opening", "Vão passante", "atravessa a parede"),
                           ("RECESS", "slab_opening", "Nicho",
                            "rebaixo na face do lado do cursor")],
                          o.kind, lambda v: (setattr(o, "kind", v), self.show_for(tool)))
            self.addSeparator()
            fields = [("width", "Largura"), ("height", "Altura"), ("sill", "Peitoril")]
            if o.kind == "RECESS":
                fields.append(("depth", "Profundidade"))
            for key, name in fields:
                self._label(name)
                self._number(getattr(o, key), lambda v, k=key: setattr(o, k, v),
                             f"{name} (m)")
        elif isinstance(tool, GridTool):
            o = tool.options
            for key, label, tip, width in (
                    ("u", "Em x", "Espaçamentos dos eixos numerados (m): 5; 4; 4", 110),
                    ("first_number", "de", "Primeiro número", 36),
                    ("v", "Em y", "Espaçamentos dos eixos com letras (m): 6; 6", 110),
                    ("first_letter", "de", "Primeira letra", 36)):
                self._label(label)
                field = QLineEdit(getattr(o, key))
                field.setToolTip(tip)
                field.setFixedWidth(width)
                field.editingFinished.connect(
                    lambda k=key, f=field: setattr(o, k, f.text().strip() or getattr(o, k)))
                self.addWidget(field)
        elif isinstance(tool, RadiusDimTool):
            self._choices([(False, "radius_dim", "Raio", "R 1,20"),
                           (True, "circle2d", "Diâmetro", "Ø 2,40")],
                          tool.options.diameter,
                          lambda v: setattr(tool.options, "diameter", v))
        elif isinstance(tool, LabelTool):
            self._label("Mostra")
            self._combo([("Tipo do elemento", "type"), ("Nome do elemento", "name"),
                         ("Código", "code"), ("Texto digitado", "free")], tool.options.field,
                        lambda v: setattr(tool.options, "field", v),
                        "O que o rótulo mostra quando a seta está sobre um elemento")
        elif isinstance(tool, _ClickTool):
            self._line(tool)
        elif isinstance(tool, RevisionTool):
            self._choices(SLAB_MODES, tool.options.mode,
                          lambda v: setattr(tool.options, "mode", v))
            self._label("Número")
            field = QLineEdit(tool.options.number or "")
            field.setPlaceholderText("próximo")
            field.setFixedWidth(64)
            field.editingFinished.connect(
                lambda: setattr(tool.options, "number", field.text().strip() or None))
            self.addWidget(field)
            self._label("Nota")
            note = QLineEdit(tool.options.note)
            note.setFixedWidth(160)
            note.editingFinished.connect(lambda: setattr(tool.options, "note",
                                                         note.text().strip()))
            self.addWidget(note)
        elif isinstance(tool, SpaceTool):
            self._space(tool)
        elif isinstance(tool, HatchTool):
            self._hatch(tool)
        elif isinstance(tool, LineTool):
            self._line(tool)
        elif isinstance(tool, TextTool):
            self._text(tool)
        elif isinstance(tool, DimensionTool):
            self._choices(DIM_DIRECTIONS, tool.direction,
                          lambda v: setattr(tool, "direction", v))
        elif isinstance(tool, (NorthTool, ViewTool, LevelTool)):
            pass  # só a camada
        elif isinstance(tool, BeamTool):
            self._beam(tool)
        elif isinstance(tool, SlabOpeningTool):
            self._choices(SLAB_MODES, tool.options.mode,
                          lambda v: setattr(tool.options, "mode", v))
        elif isinstance(tool, RoofTool):
            self._roof(tool)
        elif isinstance(tool, SlabTool):
            self._slab(tool)
        elif isinstance(tool, _WallTool):
            self._wall(tool)
        elif isinstance(tool, ColumnTool):
            self._column(tool)
        elif isinstance(tool, ObjectTool):
            self._object(tool)
        elif isinstance(tool, _FillingTool):
            self._door(tool)
        else:
            self.hide()
            return
        self._layer(tool)
        if not self.actions():
            self.hide()
            return
        if self.wanted:
            self.show()

    def _layer(self, tool) -> None:
        """Camada padrão da ferramenta (spec/ui 18 §3.2), gravada no projeto."""
        session = self.window_.session
        doc = session.doc
        kind = tool_kind(tool)
        config = display_layers.read_config(doc)
        if kind is None or config is None:
            return
        self.addSeparator()
        self._label("Camada")
        current = display_layers.default_layer(config, kind) or display_layers.NONE
        self._combo(display_layers.choices(doc), current,
                    lambda v: session.run(lambda: display_layers.set_default(doc, kind, v)),
                    "Camada em que esta ferramenta desenha")

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

    def _type_group(self, ifc_class: str, holder, commit, noun: str, types=None) -> None:
        """Tipo e Editar tipo; ``holder.type`` é o tipo escolhido."""
        window = self.window_
        self._label("Tipo")
        types = self._types(ifc_class) if types is None else types
        self._combo([(t.Name, t.GlobalId) for t in types], holder.type, commit, f"Tipo {noun}")
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

    # --- objeto paramétrico (objeto-parametrico.md §4.4) -------------------------------------

    def _object(self, tool) -> None:
        from brasbim.core.objects import definition as od
        from brasbim.ui import object_widgets as ow

        window = self.window_
        doc = window.session.doc
        picker = ow.TypePicker(doc, tool.type)

        def chosen(value):
            if value == "library":
                window.show_library()
                return
            tool.set_type(value)
            self.show_for(tool)
            window.hint.setText(tool.hint())

        picker.chosen.connect(chosen)
        self.addWidget(picker)
        state = tool.type_state()
        if state is None:
            return
        defn = state["definition"]
        self.addSeparator()
        if defn["hosting"] != "wall":
            self._label("Rotação")
            self.angle_field = self._number(tool.angle, lambda v: setattr(tool, "angle", v),
                                            "Rotação do objeto (graus, anti-horário)")
        mirror = make_action(self, "mirror", "Espelhar", "o próximo objeto sai espelhado",
                             checkable=True)
        mirror.setChecked(tool.mirror)
        mirror.toggled.connect(lambda v: setattr(tool, "mirror", bool(v)))
        self.addAction(mirror)
        values = {**state["defaults"], **tool.values}
        elevation = od.param(defn, "elevacao")
        self._label("Elevação" if defn["hosting"] != "wall" else "Altura")
        self._number(values.get("elevacao", elevation["value"] if elevation else 0.0),
                     lambda v: tool.values.__setitem__("elevacao", v),
                     "Altura da base do objeto acima do piso (m)")
        shown = [p for p in od.occurrence_params(defn)
                 if od.editable(p) and p["group"] == "Dimensões" and p["name"] != "elevacao"][:3]
        if shown:
            self.addSeparator()
        for p in shown:
            self._label(ow.label(p))

            def commit(v, name=p["name"]):
                tool.values[name] = v
            self.addWidget(ow.param_widget(p, values.get(p["name"], p["value"]), commit, doc))
        more = [p for p in od.occurrence_params(defn)
                if od.editable(p) and p not in shown and p["name"] != "elevacao"]
        if more:
            action = make_action(self, "edit_type", "Mais parâmetros",
                                 "os outros parâmetros de ocorrência do próximo objeto")
            action.triggered.connect(lambda: window.object_values_dialog(tool, more))
            self.addAction(action)

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

        self._type_group("IfcSlabType", options, set_type, "da próxima laje",
                         floor_types(self.window_.session.doc))
        self.addSeparator()

        def set_mode(value):
            tool.cancel()
            tool.points = []
            options.mode = value
            self.show_for(tool)

        self._choices([*SLAB_MODES, SLAB_ROOM], options.mode, set_mode)
        if options.mode == "room":
            self._label("Contorno")
            self._combo(ROOM_BOUNDARIES, options.boundary,
                        lambda v: setattr(options, "boundary", v),
                        "Até onde vai a laje: face externa, eixo ou face interna das paredes")
        self.addSeparator()
        self._label("Deslocamento do topo")
        self._number(options.top_offset, lambda v: setattr(options, "top_offset", v),
                     "Cota da face de cima em relação ao pavimento (m)")

    def _roof(self, tool) -> None:
        """Cobertura (cobertura.md §4): tipo, forma, modo do contorno, inclinação, beiral e
        altura de apoio."""
        options = tool.options

        def set_type(gid):
            options.type = gid
            self.show_for(tool)

        self._type_group("IfcSlabType", options, set_type, "da próxima cobertura",
                         roof_types(self.window_.session.doc))
        self.addSeparator()

        def set_shape(value):
            tool.cancel()
            options.shape = value
            self.show_for(tool)

        self._choices(ROOF_SHAPES, options.shape, set_shape)
        self.addSeparator()

        def set_mode(value):
            tool.cancel()
            tool.points = []
            options.mode = value
            self.show_for(tool)

        self._choices(ROOF_MODES, options.mode, set_mode)
        self.addSeparator()
        if options.shape != "flat":
            self._label("Inclinação (%)")

            def set_slope(value):
                if not roofs.MIN_SLOPE <= value <= roofs.MAX_SLOPE:
                    self.window_.session.message(
                        f"a inclinação deve ficar entre {roofs.MIN_SLOPE:.0f} e "
                        f"{roofs.MAX_SLOPE:.0f} %", "recusa")
                    self.show_for(tool)
                    return
                options.slope = value

            degrees = math.degrees(math.atan(options.slope / 100.0))
            self._number(options.slope, set_slope,
                         f"Inclinação das águas em % ({fmt(degrees)}°)")
        self._label("Beiral")

        def set_overhang(value):
            if not 0.0 <= value <= roofs.MAX_OVERHANG:
                self.window_.session.message(
                    f"o beiral deve ficar entre 0 e {roofs.MAX_OVERHANG:.0f} m", "recusa")
                self.show_for(tool)
                return
            options.overhang = value

        self._number(options.overhang, set_overhang,
                     "Quanto a cobertura passa do contorno de apoio (m)")
        self._label("Apoio")
        self._number(options.base_height, lambda v: setattr(options, "base_height", v),
                     "Cota da face de baixo sobre o contorno de apoio, a partir do pavimento "
                     "(m); vazio: topo das paredes", fmt(tool.base_height()), allow_empty=True)

    # --- documentação da planta (spec/ui 13) ----------------------------------------------

    def _space(self, tool) -> None:
        options = tool.options

        def set_mode(value):
            tool.cancel()
            tool.points = []
            options.mode = value

        self._choices(SPACE_MODES, options.mode, set_mode)
        self.addSeparator()
        self._label("Nome")
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems([space_data.DEFAULT_NAME, *space_data.NAMES])
        combo.setCurrentText(options.name)
        combo.setToolTip("Nome do próximo ambiente")
        combo.currentTextChanged.connect(lambda v: setattr(options, "name", v.strip()
                                                           or space_data.DEFAULT_NAME))
        self.addWidget(combo)
        self._label("Pé-direito")
        self._number(options.height, lambda v: setattr(options, "height", v),
                     "Pé-direito (vazio = calculado até a laje de cima)", "calculado",
                     allow_empty=True)

    def _hatch(self, tool) -> None:
        options = tool.options

        def set_mode(value):
            tool.cancel()
            options.mode = value

        self._choices(SLAB_MODES, options.mode, set_mode)
        self.addSeparator()
        self._label("Padrão")
        self._combo(HATCHES, options.pattern, lambda v: setattr(options, "pattern", v),
                    "Padrão da hachura")
        self._label("Ângulo")
        self._number(options.angle, lambda v: setattr(options, "angle", v),
                     "Ângulo das linhas (graus)")
        self._label("Espaçamento")
        self._number(options.spacing, lambda v: setattr(options, "spacing", v),
                     "Espaçamento das linhas, em mm de papel")

    def _line(self, tool) -> None:
        options = tool.options
        self._label("Espessura")
        self._combo([(f"{fmt(w)} mm", w) for w in drafting.LINE_WEIGHTS], options.weight,
                    lambda v: setattr(options, "weight", v), "Espessura da linha no papel")
        self._label("Tipo")
        self._combo(DASHES, options.dash, lambda v: setattr(options, "dash", v),
                    "Tipo de linha")

    def _text(self, tool) -> None:
        options = tool.options
        self._label("Altura")
        self._combo([(f"{fmt(v)} mm", v) for v in drafting.TEXT_SIZES], options.size,
                    lambda v: setattr(options, "size", v), "Altura do texto no papel")
        self._label("Ângulo")
        self._number(options.angle, lambda v: setattr(options, "angle", v),
                     "Ângulo do texto (graus)")
        self._label("Alinhamento")
        self._combo(ALIGN_TEXT, options.align, lambda v: setattr(options, "align", v),
                    "Alinhamento do texto")
