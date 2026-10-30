# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto > Perfis (spec/ui 41 §4 e §4.1): as seções desenhadas do projeto.

À esquerda, a lista de perfis; à direita, o nome, para que o perfil serve, a área de
desenho em escala real (grade de 1 cm, origem = ponto de inserção) e a lista de partes,
cada uma com material e papel (núcleo ou acabamento). Retângulo e polígono por cliques
ou por medidas; linhas de esticar na largura e na altura. Aplicar grava
``profile_def.create``/``edit``; editar um perfil em uso refaz os tipos e os elementos.
"""

from __future__ import annotations

import copy
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import materials, profile_defs
from brasbim.core.document import OpError
from brasbim.ui import icons, theme
from brasbim.ui.tools import fmt, fmt_exact, parse_number

# Usos que já têm ferramenta (spec/ui 41 §4.1, ordem do ponto (n)); os outros entram
# nas próximas etapas.
AVAILABLE_USES = ("wall", "beam", "column")
ROLE_LABEL = {"core": "Núcleo", "finish": "Acabamento"}
GRID = 0.01  # m
PICK_PX = 8


def default_state(name: str) -> dict:
    return {"name": name, "uses": list(AVAILABLE_USES), "stretch_x": None, "stretch_y": None,
            "parts": [{"material": "Concreto", "role": "core", "holes": [],
                       "outline": [[-0.1, -0.4], [0.1, -0.4], [0.1, 0.0], [-0.1, 0.0]]}]}


def _unique(names, base: str) -> str:
    name, n = base, 2
    while name in names:
        name, n = f"{base} ({n})", n + 1
    return name


class ProfileCanvas(QWidget):
    """Área de desenho do perfil, em metros com y para cima."""

    changed = Signal()
    picked = Signal(int)  # índice da parte escolhida (-1: nenhuma)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.state: dict | None = None
        self.selected = -1
        self.mode = "select"  # select, rect, polygon
        self.points: list[tuple[float, float]] = []  # desenho em andamento
        self.cursor: tuple[float, float] | None = None
        self.scale = 400.0  # px/m
        self.center = (0.0, -0.2)
        self.setMinimumSize(360, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._pan: QPointF | None = None

    # --- coordenadas ------------------------------------------------------------------

    def to_screen(self, p) -> QPointF:
        return QPointF(self.width() / 2 + (p[0] - self.center[0]) * self.scale,
                       self.height() / 2 - (p[1] - self.center[1]) * self.scale)

    def to_model(self, q: QPointF) -> tuple[float, float]:
        return (self.center[0] + (q.x() - self.width() / 2) / self.scale,
                self.center[1] - (q.y() - self.height() / 2) / self.scale)

    def snapped(self, q: QPointF) -> tuple[float, float]:
        """Vértice de uma parte perto do cursor, senão a grade de 1 cm."""
        best, dist = None, PICK_PX
        for part in (self.state or {}).get("parts", []):
            for p in part["outline"]:
                d = math.dist((q.x(), q.y()), (self.to_screen(p).x(), self.to_screen(p).y()))
                if d < dist:
                    best, dist = (p[0], p[1]), d
        if best is not None:
            return best
        x, y = self.to_model(q)
        return round(round(x / GRID) * GRID, 6), round(round(y / GRID) * GRID, 6)

    def fit(self) -> None:
        if not self.state or not self.state["parts"]:
            return
        x0, y0, x1, y1 = profile_defs.bounds(self.state["parts"])
        x0, y0, x1, y1 = min(x0, 0.0), min(y0, 0.0), max(x1, 0.0), max(y1, 0.0)
        w, h = max(x1 - x0, 0.05), max(y1 - y0, 0.05)
        self.scale = max(20.0, min((self.width() - 80) / w, (self.height() - 80) / h))
        self.center = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.update()

    def show_state(self, state: dict | None) -> None:
        self.state = state
        self.selected = -1
        self.points = []
        self.fit()
        self.update()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.points = []
        self.setCursor(Qt.ArrowCursor if mode == "select" else Qt.CrossCursor)
        self.update()

    # --- desenho ----------------------------------------------------------------------

    def _grid(self, painter: QPainter) -> None:
        step = GRID
        while step * self.scale < 8:
            step *= 5 if str(step).rstrip("0").endswith("1") else 2
        major = step * 10
        x0, y1 = self.to_model(QPointF(0, 0))
        x1, y0 = self.to_model(QPointF(self.width(), self.height()))
        for spacing, color in ((step, theme.GRID), (major, theme.GRID_MAJOR)):
            painter.setPen(QPen(QColor(color), 1))
            k = math.floor(x0 / spacing)
            while k * spacing <= x1:
                x = self.to_screen((k * spacing, 0)).x()
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                k += 1
            k = math.floor(y0 / spacing)
            while k * spacing <= y1:
                y = self.to_screen((0, k * spacing)).y()
                painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
                k += 1

    def _path(self, part: dict) -> QPainterPath:
        path = QPainterPath()
        for ring in [part["outline"], *(part.get("holes") or [])]:
            path.addPolygon(QPolygonF([self.to_screen(p) for p in ring]))
            path.closeSubpath()
        path.setFillRule(Qt.OddEvenFill)
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PAPER))
        self._grid(painter)
        state = self.state
        if state is not None:
            for i, part in enumerate(state["parts"]):
                color = QColor(materials.style(self.session.doc, part["material"])["color"])
                painter.setBrush(QBrush(color))
                selected = i == self.selected
                painter.setPen(QPen(QColor(theme.ACCENT if selected else theme.INK),
                                    2.5 if selected else 1.2))
                painter.drawPath(self._path(part))
            dash = QPen(QColor(theme.ACCENT), 1.2, Qt.DashLine)
            painter.setPen(dash)
            if state.get("stretch_x") is not None:
                x = self.to_screen((state["stretch_x"], 0)).x()
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                painter.drawText(QPointF(x + 4, 14), "esticar largura")
            if state.get("stretch_y") is not None:
                y = self.to_screen((0, state["stretch_y"])).y()
                painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
                painter.drawText(QPointF(6, y - 4), "esticar altura")
        # origem: ponto de inserção
        o = self.to_screen((0.0, 0.0))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(theme.ACCENT), 1.6))
        painter.drawLine(o + QPointF(-12, 0), o + QPointF(12, 0))
        painter.drawLine(o + QPointF(0, -12), o + QPointF(0, 12))
        painter.drawEllipse(o, 4, 4)
        # desenho em andamento
        if self.points and self.cursor is not None:
            painter.setPen(QPen(QColor(theme.ACCENT), 1.5))
            if self.mode == "rect":
                a, b = self.to_screen(self.points[0]), self.to_screen(self.cursor)
                painter.drawRect(QRectF(a, b).normalized())
            else:
                pts = [self.to_screen(p) for p in [*self.points, self.cursor]]
                painter.drawPolyline(QPolygonF(pts))
        if self.cursor is not None and self.mode != "select":
            c = self.to_screen(self.cursor)
            painter.setPen(QPen(QColor(theme.ACCENT), 1))
            painter.drawRect(QRectF(c.x() - 3, c.y() - 3, 6, 6))
            painter.setPen(QPen(QColor(theme.INK_SOFT), 1))
            painter.drawText(QPointF(c.x() + 8, c.y() - 8),
                             f"{fmt(self.cursor[0])} ; {fmt(self.cursor[1])}")
        painter.end()

    # --- mouse e teclado --------------------------------------------------------------

    def part_at(self, q: QPointF) -> int:
        if self.state is None:
            return -1
        for i in reversed(range(len(self.state["parts"]))):
            if self._path(self.state["parts"][i]).contains(q):
                return i
        return -1

    def select(self, index: int) -> None:
        self.selected = index
        self.picked.emit(index)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = event.position()
            return
        if event.button() != Qt.LeftButton or self.state is None:
            return
        q = event.position()
        if self.mode == "select":
            self.select(self.part_at(q))
            return
        p = self.snapped(q)
        if self.mode == "rect":
            if not self.points:
                self.points = [p]
            else:
                (ax, ay), (bx, by) = self.points[0], p
                self.points = []
                if abs(ax - bx) > 1e-9 and abs(ay - by) > 1e-9:
                    self.add_outline([[ax, ay], [bx, ay], [bx, by], [ax, by]])
        else:
            if len(self.points) >= 3 and p == self.points[0]:
                self.close_polygon()
            else:
                self.points.append(p)
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.mode == "polygon" and len(self.points) >= 3:
            self.close_polygon()

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            d = event.position() - self._pan
            self._pan = event.position()
            self.center = (self.center[0] - d.x() / self.scale, self.center[1] + d.y() / self.scale)
        else:
            self.cursor = self.snapped(event.position())
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None

    def wheelEvent(self, event):
        before = self.to_model(event.position())
        self.scale = max(20.0, min(20000.0, self.scale * (1.2 if event.angleDelta().y() > 0
                                                          else 1 / 1.2)))
        after = self.to_model(event.position())
        self.center = (self.center[0] + before[0] - after[0],
                       self.center[1] + before[1] - after[1])
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.points:
            self.points = []
            self.update()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.mode == "polygon":
            self.close_polygon()
        elif event.key() == Qt.Key_Delete and self.selected >= 0:
            self.remove_selected()
        else:
            super().keyPressEvent(event)

    # --- edição -----------------------------------------------------------------------

    def close_polygon(self) -> None:
        pts = [list(p) for p in self.points]
        self.points = []
        if len(pts) >= 3:
            self.add_outline(pts)
        self.update()

    def add_outline(self, outline) -> None:
        if self.state is None:
            return
        material = (self.state["parts"][self.selected]["material"]
                    if 0 <= self.selected < len(self.state["parts"]) else "Concreto")
        self.state["parts"].append({"material": material, "role": "core",
                                    "outline": [[float(x), float(y)] for x, y in outline],
                                    "holes": []})
        self.select(len(self.state["parts"]) - 1)
        self.changed.emit()

    def remove_selected(self) -> None:
        if self.state is None or not 0 <= self.selected < len(self.state["parts"]):
            return
        del self.state["parts"][self.selected]
        self.select(-1)
        self.changed.emit()


class ProfilesDialog(QDialog):
    def __init__(self, session, parent=None, select: str | None = None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Perfis")
        self.resize(980, 600)
        self.current: str | None = None  # id do perfil no editor
        self.state: dict | None = None  # cópia em edição
        self.dirty = False
        self._loading = False
        # lista
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._picked)
        left = QVBoxLayout()
        left.addWidget(self.list)
        row = QHBoxLayout()
        for text, slot in (("Novo", self.add), ("Duplicar", self.duplicate),
                           ("Excluir", self.delete)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        left.addLayout(row)
        # editor
        self.editor = QWidget()
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.textEdited.connect(self._name_edited)
        form.addRow("Nome", self.name)
        uses = QHBoxLayout()
        self.use_boxes = {}
        for use in AVAILABLE_USES:
            box = QCheckBox(profile_defs.USE_LABEL[use])
            box.toggled.connect(self._uses_edited)
            uses.addWidget(box)
            self.use_boxes[use] = box
        uses.addStretch(1)
        form.addRow("Serve para", uses)
        # ferramentas da área de desenho
        tools = QHBoxLayout()
        self.modes = QButtonGroup(self)
        for mode, icon, tip in (("select", "select", "Escolher parte"),
                                ("rect", "area_rect", "Retângulo: dois cliques nos cantos"),
                                ("polygon", "area_polygon",
                                 ("Polígono: clique nos vértices; clique no primeiro, clique "
                                  "duplo ou Enter fecha"))):
            button = QToolButton()
            button.setIcon(icons.icon(icon))
            button.setToolTip(tip)
            button.setCheckable(True)
            button.setProperty("mode", mode)
            self.modes.addButton(button)
            tools.addWidget(button)
        self.modes.buttons()[0].setChecked(True)
        self.modes.buttonClicked.connect(lambda b: self.canvas.set_mode(b.property("mode")))
        fit = QToolButton()
        fit.setIcon(icons.icon("zoom_fit"))
        fit.setToolTip("Enquadrar")
        fit.clicked.connect(lambda: self.canvas.fit())
        tools.addWidget(fit)
        remove = QToolButton()
        remove.setIcon(icons.icon("delete"))
        remove.setToolTip("Remover a parte escolhida (Delete)")
        remove.clicked.connect(lambda: self.canvas.remove_selected())
        tools.addWidget(remove)
        tools.addStretch(1)
        self.size_label = QLabel()
        self.size_label.setStyleSheet(f"color: {theme.INK_SOFT}")
        tools.addWidget(self.size_label)
        self.canvas = ProfileCanvas(session)
        self.canvas.changed.connect(self._parts_edited)
        self.canvas.picked.connect(self._canvas_picked)
        # retângulo por medidas
        exact = QHBoxLayout()
        self.rect_fields = []
        for label in ("x", "y", "Largura", "Altura"):
            exact.addWidget(QLabel(label))
            field = QLineEdit()
            field.setMaximumWidth(70)
            exact.addWidget(field)
            self.rect_fields.append(field)
        add_rect = QPushButton("Acrescentar retângulo")
        add_rect.clicked.connect(self.add_exact_rect)
        exact.addWidget(add_rect)
        exact.addStretch(1)
        # partes
        self.parts = QTableWidget(0, 2)
        self.parts.setHorizontalHeaderLabels(["Material", "Papel"])
        self.parts.verticalHeader().hide()
        self.parts.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.parts.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.parts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parts.setSelectionMode(QAbstractItemView.SingleSelection)
        self.parts.setMinimumHeight(110)
        self.parts.setMaximumHeight(170)
        self.parts.itemSelectionChanged.connect(self._table_picked)
        # esticar
        stretch = QGridLayout()
        self.stretch_boxes, self.stretch_fields = {}, {}
        for row_i, (key, text, axis) in enumerate((("stretch_x", "Esticar na largura", "x ="),
                                                   ("stretch_y", "Esticar na altura", "y ="))):
            box = QCheckBox(text)
            field = QLineEdit()
            field.setMaximumWidth(80)
            box.toggled.connect(lambda on, k=key: self._stretch_edited(k))
            field.textEdited.connect(lambda _t, k=key: self._stretch_edited(k))
            stretch.addWidget(box, row_i, 0)
            stretch.addWidget(QLabel(f"linha em {axis}"), row_i, 1)
            stretch.addWidget(field, row_i, 2)
            self.stretch_boxes[key], self.stretch_fields[key] = box, field
        stretch.setColumnStretch(3, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet(f"color: {theme.INK_SOFT}")
        editor = QVBoxLayout(self.editor)
        editor.setContentsMargins(0, 0, 0, 0)
        editor.addLayout(form)
        editor.addLayout(tools)
        editor.addWidget(self.canvas, 1)
        editor.addLayout(exact)
        editor.addWidget(self.parts)
        editor.addLayout(stretch)
        editor.addWidget(self.note)
        right = QVBoxLayout()
        right.addWidget(self.editor, 1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.apply_button = QPushButton("Aplicar")
        self.apply_button.clicked.connect(self.apply)
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        bottom.addWidget(self.apply_button)
        bottom.addWidget(close)
        right.addLayout(bottom)
        layout = QHBoxLayout(self)
        layout.addLayout(left, 2)
        layout.addLayout(right, 7)
        self.refresh(select)

    # --- lista -------------------------------------------------------------------------

    def defs(self) -> list:
        return profile_defs.all_defs(self.session.doc)

    def refresh(self, select: str | None = None) -> None:
        select = select or self.current
        self.list.blockSignals(True)
        self.list.clear()
        row = 0
        for i, profile_set in enumerate(self.defs()):
            def_id = profile_defs.id_of(profile_set)
            used = len(profile_defs.users(self.session.doc, def_id))
            item = QListWidgetItem(f"{profile_set.Name}  ({used})")
            item.setData(Qt.UserRole, def_id)
            self.list.addItem(item)
            if def_id == select:
                row = i
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(row)
            self.load(self.list.item(row).data(Qt.UserRole))
        else:
            self.load(None)

    def _picked(self, item, previous) -> None:
        if item is None or item.data(Qt.UserRole) == self.current:
            return
        if self.dirty and not self._resolve_pending():
            self.list.blockSignals(True)
            self.list.setCurrentItem(previous)
            self.list.blockSignals(False)
            return
        self.load(item.data(Qt.UserRole))

    def _resolve_pending(self) -> bool:
        answer = QMessageBox.question(
            self, "Mudanças não aplicadas", "Aplicar as mudanças deste perfil?",
            QMessageBox.Apply | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Apply:
            return self.apply()
        return answer == QMessageBox.Discard

    def closeEvent(self, event):
        if self.dirty and not self._resolve_pending():
            event.ignore()
            return
        event.accept()

    # --- editor ------------------------------------------------------------------------

    def load(self, def_id: str | None) -> None:
        self._loading = True
        self.current = def_id
        self.state = profile_defs.state(self.session.doc, def_id) if def_id else None
        self.editor.setEnabled(def_id is not None)
        self.apply_button.setEnabled(def_id is not None)
        state = self.state
        self.name.setText(state["name"] if state else "")
        for use, box in self.use_boxes.items():
            box.setChecked(bool(state) and use in state["uses"])
        for key in ("stretch_x", "stretch_y"):
            value = state.get(key) if state else None
            self.stretch_boxes[key].setChecked(value is not None)
            self.stretch_fields[key].setText(fmt_exact(value) if value is not None else "")
        self.canvas.show_state(state)
        self._fill_parts()
        self._loading = False
        self.dirty = False
        self._update_info()

    def _touch(self) -> None:
        if not self._loading:
            self.dirty = True
            self._update_info()

    def _name_edited(self, text: str) -> None:
        if self.state is not None:
            self.state["name"] = text.strip()
            self._touch()

    def _uses_edited(self, *_args) -> None:
        if self.state is None or self._loading:
            return
        others = [u for u in self.state["uses"] if u not in AVAILABLE_USES]
        self.state["uses"] = others + [u for u, b in self.use_boxes.items() if b.isChecked()]
        self._touch()

    def _stretch_edited(self, key: str) -> None:
        if self.state is None or self._loading:
            return
        on = self.stretch_boxes[key].isChecked()
        field = self.stretch_fields[key]
        if on and not field.text().strip() and self.state["parts"]:
            x0, y0, x1, y1 = profile_defs.bounds(self.state["parts"])
            middle = (x0 + x1) / 2 if key == "stretch_x" else (y0 + y1) / 2
            field.setText(fmt_exact(round(middle, 3)))
        try:
            self.state[key] = parse_number(field.text()) if on else None
        except ValueError:
            self.state[key] = None
        self.canvas.update()
        self._touch()

    def _parts_edited(self) -> None:
        self._fill_parts()
        self._touch()

    def _material_names(self) -> list[str]:
        names = {m.Name for m in self.session.doc.ifc.by_type("IfcMaterial") if m.Name}
        return sorted(names | set(materials.LIBRARY))

    def _fill_parts(self) -> None:
        self.parts.blockSignals(True)
        self.parts.setRowCount(0)
        parts = self.state["parts"] if self.state else []
        names = self._material_names()
        for i, part in enumerate(parts):
            self.parts.insertRow(i)
            material = QComboBox()
            material.setEditable(True)
            material.addItems(names if part["material"] in names else [part["material"], *names])
            material.setCurrentText(part["material"])
            material.currentTextChanged.connect(
                lambda text, k=i: self._part_field(k, "material", text.strip()))
            role = QComboBox()
            for value, text in ROLE_LABEL.items():
                role.addItem(text, value)
            role.setCurrentIndex(role.findData(part["role"]))
            role.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            role.currentIndexChanged.connect(
                lambda _i, k=i, box=role: self._part_field(k, "role", box.currentData()))
            self.parts.setCellWidget(i, 0, material)
            self.parts.setCellWidget(i, 1, role)
            # a coluna mede o combo, não o texto: "Acabamento" inteiro, sem cortar
            self.parts.setColumnWidth(1, max(self.parts.columnWidth(1),
                                             role.sizeHint().width() + 4))
        if 0 <= self.canvas.selected < len(parts):
            self.parts.selectRow(self.canvas.selected)
        self.parts.blockSignals(False)

    def _part_field(self, index: int, key: str, value) -> None:
        if self.state is None or not value:
            return
        self.state["parts"][index][key] = value
        self.canvas.update()
        self._touch()

    def _table_picked(self) -> None:
        rows = self.parts.selectionModel().selectedRows()
        self.canvas.selected = rows[0].row() if rows else -1
        self.canvas.update()

    def _canvas_picked(self, index: int) -> None:
        self.parts.blockSignals(True)
        if index >= 0:
            self.parts.selectRow(index)
        else:
            self.parts.clearSelection()
        self.parts.blockSignals(False)

    def add_exact_rect(self) -> None:
        try:
            x, y, w, h = (parse_number(f.text()) for f in self.rect_fields)
        except ValueError:
            self.session.message("retângulo: preencha x, y, largura e altura", "recusa")
            return
        if w <= 0 or h <= 0:
            self.session.message("retângulo: largura e altura devem passar de zero", "recusa")
            return
        self.canvas.add_outline([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])

    def _update_info(self) -> None:
        state = self.state
        if not state or not state["parts"]:
            self.size_label.setText("")
            self.note.setText("Desenhe pelo menos uma parte." if state else "")
            return
        w, h = profile_defs.nominal(state)
        area = profile_defs.area(state["parts"])
        self.size_label.setText(f"Largura {fmt(w)} m · Altura {fmt(h)} m · "
                                f"Área {fmt(area)} m²")
        try:
            profile_defs.validate(state)
            problem = ""
        except OpError as e:
            problem = str(e)
        hint = ("A cruz é o ponto de inserção: o eixo da viga e o ponto do pilar. "
                "Sem linha de esticar, a medida naquela direção é fixa.")
        self.note.setText(f"{problem[:1].upper()}{problem[1:]}." if problem else hint)

    # --- gravar -----------------------------------------------------------------------

    def apply(self) -> bool:
        if self.current is None or not self.dirty:
            return True
        doc, def_id = self.session.doc, self.current
        before = profile_defs.state(doc, def_id)
        changes = {k: copy.deepcopy(v) for k, v in self.state.items() if v != before.get(k)}
        if changes and not self.session.run(lambda: profile_defs.edit(doc, def_id, **changes)):
            return False
        self.dirty = False
        self.refresh(def_id)
        return True

    def _create(self, state: dict) -> None:
        if self.dirty and not self._resolve_pending():
            return
        doc = self.session.doc
        holder = {}

        def build():
            tx = profile_defs.create(doc, state)
            holder["id"] = tx.ops[0].id
            return tx

        if self.session.run(build):
            self.dirty = False
            self.refresh(holder["id"])

    def add(self) -> None:
        names = {s.Name for s in self.defs()}
        self._create(default_state(_unique(names, "Novo perfil")))

    def duplicate(self) -> None:
        if self.current is None:
            return
        state = profile_defs.state(self.session.doc, self.current)
        state["name"] = _unique({s.Name for s in self.defs()}, f"{state['name']} (cópia)")
        self._create(state)

    def delete(self) -> None:
        if self.current is None:
            return
        doc, def_id = self.session.doc, self.current
        if self.session.run(lambda: profile_defs.delete(doc, def_id)):
            self.current = None
            self.dirty = False
            self.refresh()
