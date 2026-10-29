# SPDX-License-Identifier: GPL-3.0-or-later
"""Folhas mestras na interface (``spec/ui/26-folhas-mestras.md`` §4): a aba de edição
(papel, quadro, margens e o desenho do carimbo com linhas e textos com campos), o quadro
"Papel e margens…" e o quadro "Nova prancha" com a escolha da folha mestra.

A lógica de pontos (grade de 1 mm, atração nas pontas, escolha do item sob o cursor) fica
em funções sem Qt, testáveis à parte."""

from __future__ import annotations

import copy
import itertools
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.annotations.prims import Text
from brasbim.core.drawings import masters
from brasbim.ui import theme
from brasbim.ui.icons import icon
from brasbim.ui.measure_box import pick_cursor
from brasbim.ui.paper_select import DRAG_PX, PaperSelection, draw_overlay

GRID_MM = 1.0
SNAP_MM = 2.0  # atração nas pontas (mm de papel)
PICK_MM = 1.5  # tolerância do clique numa linha
WEIGHTS = (0.13, 0.18, 0.25, 0.35, 0.5, 0.7)
TOOLS = (("select", "Selecionar", "select"), ("line", "Linha", "line2d"),
         ("rect", "Retângulo", "wall_rect"), ("text", "Texto", "text"))


# --- lógica sem Qt ------------------------------------------------------------------------


def snap_point(p, items, grid: float = GRID_MM, reach: float = SNAP_MM):
    """Ponta de linha a até ``reach`` mm; senão, o ponto da grade mais perto."""
    best, best_d = None, reach
    for item in items:
        if item["kind"] != "line":
            continue
        for q in item["points"]:
            d = math.dist(p, q)
            if d <= best_d:
                best, best_d = (float(q[0]), float(q[1])), d
    if best is not None:
        return best
    return (round(p[0] / grid) * grid, round(p[1] / grid) * grid)


def _segment_distance(p, a, b) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def text_box(item) -> tuple[float, float, float, float]:
    """Retângulo aproximado do texto (largura ≈ 0,6 × altura por letra)."""
    width = 0.6 * item["height"] * max(1, len(item["text"]))
    x, y = item["at"]
    x0 = {"center": x - width / 2, "right": x - width}.get(item["align"], x)
    return x0, y, x0 + width, y + item["height"]


def pick(p, items, reach: float = PICK_MM) -> int | None:
    """Índice do item sob o ponto (o de cima primeiro), ou ``None``."""
    for i in reversed(range(len(items))):
        item = items[i]
        if item["kind"] == "text":
            x0, y0, x1, y1 = text_box(item)
            if x0 - reach <= p[0] <= x1 + reach and y0 - reach <= p[1] <= y1 + reach:
                return i
            continue
        pts = item["points"] + ([item["points"][0]] if item["closed"] else [])
        if any(_segment_distance(p, a, b) <= reach for a, b in itertools.pairwise(pts)):
            return i
    return None


def outlines(items) -> list[list[tuple[list, bool]]]:
    """Contornos de cada item para a janela e o laço (spec/ui 29 §2): a linha como é, o
    texto pela caixa dele."""
    out = []
    for item in items:
        if item["kind"] == "text":
            x0, y0, x1, y1 = text_box(item)
            out.append([([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)])
        else:
            out.append([([tuple(q) for q in item["points"]], bool(item["closed"]))])
    return out


def moved(item: dict, dx: float, dy: float) -> dict:
    out = copy.deepcopy(item)
    if out["kind"] == "line":
        out["points"] = [[round(x + dx, 3), round(y + dy, 3)] for x, y in out["points"]]
    else:
        out["at"] = [round(out["at"][0] + dx, 3), round(out["at"][1] + dy, 3)]
    return out


# --- quadros ------------------------------------------------------------------------------


FORMAT_CHOICES = [(f, f) for f in masters.FORMATS] + [("Personalizado", masters.CUSTOM)]
ORIENTATION_CHOICES = (("Horizontal", "landscape"), ("Vertical", "portrait"))


def _combo(choices, current) -> QComboBox:
    combo = QComboBox()
    for text, value in choices:
        combo.addItem(text, value)
    combo.setCurrentIndex(max(0, combo.findData(current)))
    return combo


def _spin(value: float, low: float, high: float, step: float = 1.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setDecimals(1)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setSuffix(" mm")
    return spin


class PaperDialog(QDialog):
    """Papel e margens… da folha mestra (§4)."""

    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Papel e margens")
        form = QFormLayout(self)
        self.name = QLineEdit(state["name"])
        form.addRow("Nome", self.name)
        self.format = _combo(FORMAT_CHOICES, state["format"])
        form.addRow("Formato", self.format)
        self.orientation = _combo(ORIENTATION_CHOICES, state["orientation"])
        form.addRow("Orientação", self.orientation)
        w, h = masters.paper_size(state)
        self.width = _spin(w, 50, 5000)
        self.height = _spin(h, 50, 5000)
        size = QHBoxLayout()
        size.addWidget(self.width)
        size.addWidget(QLabel("×"))
        size.addWidget(self.height)
        form.addRow("Tamanho", size)
        self.margins = [_spin(v, 0, 200, 0.5) for v in state["margins"]]
        for label, spin in zip(("Esquerda", "Inferior", "Direita", "Superior"), self.margins,
                               strict=True):
            form.addRow(f"Margem {label.lower()}", spin)
        self.frame = QCheckBox("Quadro na linha das margens")
        self.frame.setChecked(bool(state["frame"]))
        form.addRow(self.frame)
        self.fold = QCheckBox("Marcas de dobra para A4")
        self.fold.setChecked(bool(state["fold_marks"]))
        form.addRow(self.fold)
        self.format.currentIndexChanged.connect(self._format_changed)
        self.orientation.currentIndexChanged.connect(self._format_changed)
        self._format_changed()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _format_changed(self) -> None:
        fmt = self.format.currentData()
        custom = fmt == masters.CUSTOM
        self.width.setEnabled(custom)
        self.height.setEnabled(custom)
        self.orientation.setEnabled(not custom)
        if not custom:
            w, h = masters.paper_size({"format": fmt, "size": None,
                                       "orientation": self.orientation.currentData()})
            self.width.setValue(w)
            self.height.setValue(h)

    def changes(self) -> dict:
        fmt = self.format.currentData()
        return {"name": self.name.text().strip(), "format": fmt,
                "orientation": self.orientation.currentData(),
                "size": [self.width.value(), self.height.value()]
                if fmt == masters.CUSTOM else None,
                "margins": [s.value() for s in self.margins],
                "frame": self.frame.isChecked(), "fold_marks": self.fold.isChecked()}


class TextDialog(QDialog):
    """Texto do carimbo: texto, altura, alinhamento, negrito e "Inserir campo ▾" (§4)."""

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Texto da folha mestra")
        form = QFormLayout(self)
        row = QHBoxLayout()
        self.text = QLineEdit(item["text"])
        row.addWidget(self.text)
        self.field_button = QPushButton("Inserir campo")
        menu = QMenu(self.field_button)
        for key, label in masters.FIELDS.items():
            menu.addAction(f"{label}  {{{key}}}", lambda k=key: self.insert_field(k))
        self.field_button.setMenu(menu)
        row.addWidget(self.field_button)
        form.addRow("Texto", row)
        self.height = _spin(item["height"], 0.5, 50, 0.5)
        form.addRow("Altura", self.height)
        self.align = _combo((("À esquerda", "left"), ("No centro", "center"),
                             ("À direita", "right")), item["align"])
        form.addRow("Alinhamento", self.align)
        self.bold = QCheckBox("Negrito")
        self.bold.setChecked(bool(item.get("bold")))
        form.addRow(self.bold)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def insert_field(self, key: str) -> None:
        self.text.insert(f"{{{key}}}")
        self.text.setFocus()

    def item(self, base: dict) -> dict:
        return {**base, "text": self.text.text(), "height": self.height.value(),
                "align": self.align.currentData(), "bold": self.bold.isChecked()}


class NewSheetDialog(QDialog):
    """Nova prancha: título e folha mestra (as do projeto e, por último, os formatos
    padrão sem folha mestra), §4."""

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova prancha")
        form = QFormLayout(self)
        self.title = QLineEdit()
        form.addRow("Título", self.title)
        self.master = QComboBox()
        for entity in masters.all_masters(doc):
            state = masters.read_state(entity)
            self.master.addItem(f"{state['name']} ({masters.describe(state)})",
                                ("master", entity.GlobalId))
        if self.master.count():
            self.master.insertSeparator(self.master.count())
        for fmt in masters.FORMATS:
            for text, orientation in ORIENTATION_CHOICES:
                self.master.addItem(f"Padrão {fmt} {text.lower()}",
                                    ("standard", fmt, orientation))
        index = self.master.findData(("standard", "A3", "landscape"))
        if not masters.all_masters(doc):
            self.master.setCurrentIndex(index)
        form.addRow("Folha mestra", self.master)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Criar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def choice(self) -> dict:
        """Argumentos de ``sheets.create_sheet``."""
        data = self.master.currentData()
        if data[0] == "master":
            return {"title": self.title.text().strip(), "master": data[1]}
        return {"title": self.title.text().strip(), "fmt": data[1], "orientation": data[2]}


# --- aba de edição ------------------------------------------------------------------------


class MasterCanvas(QWidget):
    """O papel da folha mestra: quadro, margens tracejadas e o desenho, com as ferramentas
    da barra (§4)."""

    cursor_moved = Signal(float, float)

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.zoom = 1.5
        self.top_left = QPointF(20, 20)
        # seleção pelo cursor como na planta (spec/ui 29 §2)
        self.selection = PaperSelection(lambda p: pick(p, self.state["items"]),
                                        lambda: outlines(self.state["items"]),
                                        lambda: self.editor.accumulate())
        self.points: list[tuple[float, float]] = []  # linha ou retângulo em andamento
        self.cursor: tuple[float, float] | None = None
        self._pan: QPointF | None = None
        self._fitted = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self.setCursor(pick_cursor())

    @property
    def selected(self) -> set[int]:
        return self.selection.selected

    @selected.setter
    def selected(self, value) -> None:
        self.selection.selected = set(value)

    @property
    def state(self) -> dict:
        return self.editor.state

    def fit(self) -> None:
        w, h = masters.paper_size(self.state)
        self.zoom = max(0.2, min((self.width() - 40) / w, (self.height() - 40) / h))
        self.top_left = QPointF((self.width() - w * self.zoom) / 2,
                                (self.height() - h * self.zoom) / 2)
        self._fitted = True
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._fitted:
            self.fit()

    def at(self, p) -> QPointF:
        _, h = masters.paper_size(self.state)
        return QPointF(self.top_left.x() + p[0] * self.zoom,
                       self.top_left.y() + (h - p[1]) * self.zoom)

    def to_paper(self, pos: QPointF) -> tuple[float, float]:
        _, h = masters.paper_size(self.state)
        return ((pos.x() - self.top_left.x()) / self.zoom,
                h - (pos.y() - self.top_left.y()) / self.zoom)

    # pintura

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.FRAME))
        state = self.state
        w, h = masters.paper_size(state)
        painter.fillRect(QRectF(self.at((0, h)), self.at((w, 0))), QColor(theme.FIELD))
        x0, y0, x1, y1 = masters.frame_of((w, h), state["margins"])
        margin = QPen(QColor(theme.INK_SOFT), 1, Qt.DashLine)
        painter.setPen(margin)
        painter.drawRect(QRectF(self.at((x0, y1)), self.at((x1, y0))))
        if state["frame"]:
            painter.setPen(QPen(QColor(theme.INK), max(1.0, masters.FRAME_WEIGHT * self.zoom)))
            painter.drawRect(QRectF(self.at((x0, y1)), self.at((x1, y0))))
        from brasbim.ui.paper import draw_paper_text

        offset = self.selection.offset()
        for i, item in enumerate(state["items"]):
            chosen = i in self.selected
            color = QColor(theme.ACCENT if chosen else theme.INK)
            if chosen and offset is not None:  # o que está sendo arrastado
                item = moved(item, *offset)
            if item["kind"] == "line":
                painter.setPen(QPen(color, max(1.0, item["weight"] * self.zoom)))
                painter.setBrush(Qt.NoBrush)
                poly = QPolygonF([self.at(p) for p in item["points"]])
                painter.drawPolygon(poly) if item["closed"] else painter.drawPolyline(poly)
            else:
                painter.setPen(color)
                text = Text(tuple(item["at"]), item["text"], item["height"], 0.0,
                            item["align"], "bottom", bool(item.get("bold")))
                draw_paper_text(painter, text, self.at(item["at"]), self.zoom)
        tool = self.editor.tool
        if tool == "select":
            draw_overlay(painter, self.selection, self.at)
        if self.points and self.cursor is not None:
            painter.setPen(QPen(QColor(theme.ACCENT), 1, Qt.DashLine))
            if tool == "rect":
                a, b = self.points[0], self.cursor
                painter.drawRect(QRectF(self.at((min(a[0], b[0]), max(a[1], b[1]))),
                                        self.at((max(a[0], b[0]), min(a[1], b[1])))))
            else:
                painter.drawPolyline(QPolygonF([self.at(p) for p in [*self.points,
                                                                       self.cursor]]))
        if self.cursor is not None and tool != "select":
            c = self.at(self.cursor)
            painter.setPen(QPen(QColor(theme.ACCENT), 1))
            painter.drawLine(QPointF(c.x() - 6, c.y()), QPointF(c.x() + 6, c.y()))
            painter.drawLine(QPointF(c.x(), c.y() - 6), QPointF(c.x(), c.y() + 6))
        painter.end()

    # mouse e teclado

    def snapped(self, pos: QPointF) -> tuple[float, float]:
        return snap_point(self.to_paper(pos), self.state["items"])

    def press(self, p, shift: bool = False, button: str = "left", ctrl: bool = False) -> None:
        """Clique em mm do papel (já atraído para as ferramentas de desenho)."""
        tool = self.editor.tool
        if button == "right":
            if tool == "line":
                self.finish_line()
            return
        if tool == "select":
            self.selection.press(p, shift, ctrl)
            self.update()
            return
        if tool == "text":
            self.editor.add_text(p)
            return
        if tool == "rect":
            if not self.points:
                self.points = [p]
            else:
                a, b = self.points[0], p
                self.points = []
                if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
                    self.editor.add_item({"kind": "line", "closed": True,
                                          "weight": self.editor.weight,
                                          "points": [[a[0], a[1]], [b[0], a[1]],
                                                     [b[0], b[1]], [a[0], b[1]]]})
            self.update()
            return
        if not self.points or math.dist(self.points[-1], p) > 1e-6:
            self.points.append(p)
        self.update()

    def finish_line(self) -> None:
        points, self.points = self.points, []
        if len(points) >= 2:
            self.editor.add_item({"kind": "line", "closed": False,
                                  "weight": self.editor.weight,
                                  "points": [[x, y] for x, y in points]})
        self.update()

    def move(self, p) -> None:
        if self.editor.tool == "select":
            self.selection.move(p, DRAG_PX / self.zoom)

    def release(self, p, shift: bool = False) -> None:
        """Fim do gesto de seleção; o arrasto anda em milímetros inteiros (grade)."""
        delta = self.selection.release(p, shift)
        if delta is not None and self.selected:
            dx, dy = round(delta[0]), round(delta[1])
            if dx or dy:
                self.editor.move_selected(dx, dy)
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        self.setFocus()
        if event.button() == Qt.MiddleButton:
            self._pan = pos
            return
        button = "right" if event.button() == Qt.RightButton else "left"
        p = self.to_paper(pos) if self.editor.tool == "select" else self.snapped(pos)
        mods = event.modifiers()
        self.press(p, bool(mods & Qt.ShiftModifier), button, bool(mods & Qt.ControlModifier))

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._pan is not None:
            self.top_left += pos - self._pan
            self._pan = pos
            self.update()
            return
        self.cursor = self.snapped(pos)
        self.move(self.to_paper(pos))
        self.cursor_moved.emit(*self.cursor)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None
            return
        if event.button() == Qt.LeftButton and self.editor.tool == "select":
            self.release(self.to_paper(event.position()),
                         bool(event.modifiers() & Qt.ShiftModifier))

    def leaveEvent(self, event):
        if self.selection.hover is not None:
            self.selection.hover = None
            self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.editor.tool == "line":
            self.finish_line()
            return
        if self.editor.tool == "select":
            index = pick(self.to_paper(event.position()), self.state["items"])
            if index is not None and self.state["items"][index]["kind"] == "text":
                self.editor.edit_text(index)

    def wheelEvent(self, event):
        factor = 1.15 ** (event.angleDelta().y() / 120)
        at = event.position()
        mm = (at - self.top_left) / self.zoom
        self.zoom = min(max(self.zoom * factor, 0.1), 50.0)
        self.top_left = at - mm * self.zoom
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter) and self.editor.tool == "line":
            self.finish_line()
        elif key == Qt.Key_Escape:
            if self.points:  # desenho em andamento: só cancela ele
                self.points = []
            else:
                self.selection.escape()
            self.update()
        elif key == Qt.Key_Delete:
            self.editor.delete_selected()
        else:
            super().keyPressEvent(event)


class MasterEditor(QWidget):
    """Aba "Folha mestra: nome" (§4): barra própria e o papel."""

    def __init__(self, session, master_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.master_gid = master_gid
        self.tool = "select"
        self.weight = 0.25
        self.accumulate = lambda: True  # Editar > Modo de seleção (posto pela janela)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.bar = QToolBar()
        group = QActionGroup(self)
        self.tool_actions: dict[str, QAction] = {}
        for key, text, icon_name in TOOLS:
            action = self.bar.addAction(icon(icon_name), text)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            group.addAction(action)
            self.tool_actions[key] = action
        self.tool_actions["select"].setChecked(True)
        self.bar.addSeparator()
        self.weight_combo = QComboBox()
        for w in WEIGHTS:
            self.weight_combo.addItem(f"{w:g} mm".replace(".", ","), w)
        self.weight_combo.setCurrentIndex(self.weight_combo.findData(self.weight))
        self.weight_combo.setToolTip("Espessura das linhas novas")
        self.weight_combo.currentIndexChanged.connect(
            lambda i: setattr(self, "weight", self.weight_combo.itemData(i)))
        self.bar.addWidget(self.weight_combo)
        self.bar.addSeparator()
        delete = QToolButton()
        delete.setIcon(icon("delete"))
        delete.setToolTip("Apagar o que está selecionado (Delete)")
        delete.clicked.connect(self.delete_selected)
        self.bar.addWidget(delete)
        self.bar.addAction("Papel e margens", self.edit_paper)
        self.position = QLabel()
        self.position.setStyleSheet(f"color: {theme.INK_SOFT}; padding: 0 8px;")
        self.bar.addWidget(self.position)
        layout.addWidget(self.bar)
        self.canvas = MasterCanvas(self)
        self.canvas.cursor_moved.connect(
            lambda x, y: self.position.setText(f"x {x:.0f}  y {y:.0f} mm"))
        layout.addWidget(self.canvas)

    @property
    def entity(self):
        return self.session.doc.find(self.master_gid)

    @property
    def state(self) -> dict:
        entity = self.entity
        return masters.read_state(entity) if entity is not None \
            else masters.default_state()

    @property
    def title(self) -> str:
        entity = self.entity
        return f"Folha mestra: {masters.read_state(entity)['name']}" if entity is not None \
            else "Folha mestra"

    def invalidate(self) -> None:
        self.canvas.selection.prune(len(self.state["items"]))
        self.canvas.update()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.tool_actions[tool].setChecked(True)
        self.canvas.points = []
        self.canvas.selection.drag = None
        self.canvas.selection.hover = None
        self.canvas.update()

    # edição (cada mudança é uma transação "Editar folha mestra")

    def _items(self, items, label: str) -> bool:
        doc = self.session.doc
        return self.session.run(lambda: masters.edit_master(doc, self.master_gid, label,
                                                            items=items))

    def add_item(self, item: dict) -> bool:
        return self._items([*self.state["items"], item], "Desenhar na folha mestra")

    def add_text(self, p, text: str | None = None) -> bool:
        item = {"kind": "text", "at": [round(p[0], 3), round(p[1], 3)], "text": text or "",
                "height": 2.5, "align": "left", "bold": False}
        if text is None:
            dialog = TextDialog(item, self)
            if dialog.exec() != QDialog.Accepted:
                return False
            item = dialog.item(item)
        if not item["text"].strip():
            return False
        return self.add_item(item)

    def edit_text(self, index: int, values: dict | None = None) -> bool:
        items = self.state["items"]
        if values is None:
            dialog = TextDialog(items[index], self)
            if dialog.exec() != QDialog.Accepted:
                return False
            values = dialog.item(items[index])
        items[index] = {**items[index], **values}
        return self._items(items, "Editar texto da folha mestra")

    def move_selected(self, dx: float, dy: float) -> bool:
        items = self.state["items"]
        for i in self.canvas.selected:
            items[i] = moved(items[i], dx, dy)
        return self._items(items, "Mover na folha mestra")

    def delete_selected(self) -> bool:
        chosen = self.canvas.selected
        if not chosen:
            return False
        items = [it for i, it in enumerate(self.state["items"]) if i not in chosen]
        self.canvas.selected = set()
        return self._items(items, "Apagar na folha mestra")

    def edit_paper(self, changes: dict | None = None) -> bool:
        if changes is None:
            dialog = PaperDialog(self.state, self)
            if dialog.exec() != QDialog.Accepted:
                return False
            changes = dialog.changes()
        doc = self.session.doc
        done = self.session.run(lambda: masters.edit_master(doc, self.master_gid,
                                                            "Papel da folha mestra",
                                                            **changes))
        if done:
            self.canvas.fit()
        return done
