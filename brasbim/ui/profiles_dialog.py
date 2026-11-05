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

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
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

from brasbim.core import materials, profile_defs, units
from brasbim.core.document import OpError
from brasbim.ui import icons, theme
from brasbim.ui.tools import fmt, fmt_len, parse_len

# Usos que já têm ferramenta (spec/ui 41 §4.1, ordem do ponto (n)); os outros entram
# nas próximas etapas.
AVAILABLE_USES = ("wall", "beam", "column")
ROLE_LABEL = {"core": "Núcleo", "finish": "Acabamento"}
GRID = 0.01  # m
PICK_PX = 8


def default_state(name: str) -> dict:
    return {"name": name, "uses": list(AVAILABLE_USES), "stretch_x": None, "stretch_y": None,
            "opening_ref": None,
            "parts": [{"material": "Concreto", "role": "core", "holes": [],
                       "outline": [[-0.1, -0.4], [0.1, -0.4], [0.1, 0.0], [-0.1, 0.0]]}]}


def _unique(names, base: str) -> str:
    name, n = base, 2
    while name in names:
        name, n = f"{base} ({n})", n + 1
    return name


class ProfileCanvas(QWidget):
    """Área de desenho do perfil, em metros com y para cima, desenhada como a planta:
    atração a vértices, meios, arestas, interseções, origem e linhas do perfil (com o
    marcador do que pegou), Shift trava a direção em passos de 15°, medidas digitadas na
    unidade de trabalho, vértices arrastáveis e partes com a hachura do material."""

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
        self.snap_kind = ""  # o que o cursor pegou (para o marcador)
        self.typed = ""  # medida digitada durante o desenho
        self.scale = 400.0  # px/m
        self.center = (0.0, -0.2)
        self.setMinimumSize(360, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._pan: QPointF | None = None
        self._drag: dict | None = None  # vértice ou parte sendo arrastada
        self._undo: list[list] = []

    # --- coordenadas ------------------------------------------------------------------

    def to_screen(self, p) -> QPointF:
        return QPointF(self.width() / 2 + (p[0] - self.center[0]) * self.scale,
                       self.height() / 2 - (p[1] - self.center[1]) * self.scale)

    def to_model(self, q: QPointF) -> tuple[float, float]:
        return (self.center[0] + (q.x() - self.width() / 2) / self.scale,
                self.center[1] - (q.y() - self.height() / 2) / self.scale)

    def grid_step(self) -> float:
        """Passo da grade: 1 mm em milímetros, 1 cm nas outras unidades, mais largo de
        longe (sempre ≥ 8 px)."""
        base = 0.001 if units.work_unit() == "mm" else GRID
        k = 0
        while (step := base * (1, 2, 5)[k % 3] * 10 ** (k // 3)) * self.scale < 8:
            k += 1  # 1, 2, 5, 10, 20, 50…
        return round(step, 9)

    def _rings(self, skip: tuple | None = None):
        """Anéis de todas as partes; ``skip`` = (parte, vértice) que está sendo arrastado
        (não atrai a si mesmo)."""
        for i, part in enumerate((self.state or {}).get("parts", [])):
            for ring in [part["outline"], *(part.get("holes") or [])]:
                if skip is not None and skip[0] == i and ring is part["outline"]:
                    ring = [p for k, p in enumerate(ring) if k != skip[1]]
                yield ring

    def _edges(self, skip=None):
        for ring in self._rings(skip):
            for k in range(len(ring)):
                yield tuple(ring[k]), tuple(ring[(k + 1) % len(ring)])

    def snap(self, q: QPointF, skip=None, shift: bool = False) -> tuple[tuple, str]:
        """(ponto, o que pegou). Ordem: vértice, origem, interseção, meio, aresta ou
        linha, alinhado a um vértice, grade. Com ``shift`` e um ponto anterior, a direção
        anda de 15 em 15 graus e o comprimento pela grade."""
        here = (q.x(), q.y())

        def px(p):
            s = self.to_screen(p)
            return math.dist(here, (s.x(), s.y()))

        step = self.grid_step()
        base = self.points[-1] if self.points else None
        if shift and base is not None:
            x, y = self.to_model(q)
            angle = round(math.degrees(math.atan2(y - base[1], x - base[0])) / 15.0) * 15.0
            length = round(math.dist(base, (x, y)) / step) * step
            a = math.radians(angle)
            return (round(base[0] + length * math.cos(a), 9),
                    round(base[1] + length * math.sin(a), 9)), fmt_angle(angle % 360.0)
        edges = list(self._edges(skip))
        points = [(tuple(p), "vértice") for ring in self._rings(skip) for p in ring]
        points.append(((0.0, 0.0), "origem"))
        points += [(tuple(p), "vértice") for p in self.points]
        for k, (a, b) in enumerate(edges):
            for c, d in edges[k + 1:]:
                found = _intersection(a, b, c, d)
                if found is not None:
                    points.append((found, "interseção"))
        best = min(points, key=lambda t: px(t[0]), default=None)
        if best is not None and px(best[0]) < PICK_PX:
            return best
        mids = [(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), "meio") for a, b in edges]
        best = min(mids, key=lambda t: px(t[0]), default=None)
        if best is not None and px(best[0]) < PICK_PX:
            return best
        m = self.to_model(q)
        near = [(_closest(m, a, b), "na aresta") for a, b in edges]
        for key, label in (("stretch_x", "linha de esticar"), ("opening_ref", "aberturas")):
            if (self.state or {}).get(key) is not None:
                near.append(((self.state[key], m[1]), label))
        if (self.state or {}).get("stretch_y") is not None:
            near.append(((m[0], self.state["stretch_y"]), "linha de esticar"))
        best = min(near, key=lambda t: px(t[0]), default=None)
        if best is not None and px(best[0]) < PICK_PX * 0.75:
            return (round(best[0][0], 9), round(best[0][1], 9)), best[1]
        # na grade, ou alinhado na horizontal ou na vertical com um vértice
        x = round(round(m[0] / step) * step, 9)
        y = round(round(m[1] / step) * step, 9)
        kind = "grade"
        for p, _ in points:
            s = self.to_screen(p)
            if abs(s.x() - q.x()) < PICK_PX * 0.6:
                x, kind = p[0], "alinhado"
            if abs(s.y() - q.y()) < PICK_PX * 0.6:
                y, kind = p[1], "alinhado"
        return (x, y), kind

    def snapped(self, q: QPointF) -> tuple[float, float]:
        return self.snap(q)[0]

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
        self.typed = ""
        self._undo = []
        self.fit()
        self.update()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.points = []
        self.typed = ""
        self.setCursor(Qt.ArrowCursor if mode == "select" else Qt.CrossCursor)
        self.update()

    # --- desenho ----------------------------------------------------------------------

    def _grid(self, painter: QPainter) -> None:
        step = self.grid_step()
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

    def _hatch(self, painter: QPainter, path: QPainterPath, name: str) -> None:
        """Corte do material (fundo e hachura), ancorado na origem do perfil, como na
        planta (spec/ui 06 §2.2). Material sem hachura: a cor dele, clara."""
        style = materials.style(self.session.doc, name)
        cut = style["cut"]
        pattern = cut["pattern"]
        painter.fillPath(path, QColor(theme.PAPER))
        if cut.get("background"):
            painter.fillPath(path, QColor(cut["background"]))
        elif pattern == "solid":
            painter.fillPath(path, QColor(cut.get("line_color") or style["color"]))
        elif pattern == "none":
            tint = QColor(style["color"])
            tint.setAlpha(110)
            painter.fillPath(path, tint)
        if pattern not in ("lines", "cross"):
            return
        spacing = cut["spacing"] * self.scale
        if spacing < 2:
            return
        painter.save()
        painter.setClipPath(path, Qt.IntersectClip)
        painter.setPen(QPen(QColor(cut["line_color"]), 1))
        rect = path.boundingRect()
        corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
        anchor = self.to_screen((0.0, 0.0))
        angles = [cut["angle"]] + ([cut["angle"] + 90.0] if pattern == "cross" else [])
        for degrees in angles:
            a = -math.radians(degrees)
            d = QPointF(math.cos(a), math.sin(a))
            n = QPointF(-d.y(), d.x())
            ss = [QPointF.dotProduct(c - anchor, n) for c in corners]
            ts = [QPointF.dotProduct(c - anchor, d) for c in corners]
            for k in range(math.floor(min(ss) / spacing), math.ceil(max(ss) / spacing) + 1):
                o = anchor + n * (k * spacing)
                painter.drawLine(o + d * (min(ts) - 1), o + d * (max(ts) + 1))
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PAPER))
        self._grid(painter)
        state = self.state
        unit = units.work_symbol()
        if state is not None:
            for i, part in enumerate(state["parts"]):
                path = self._path(part)
                self._hatch(painter, path, part["material"])
                selected = i == self.selected
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(theme.ACCENT if selected else theme.INK),
                                    2.5 if selected else 1.2))
                painter.drawPath(path)
            # vértices da parte escolhida (arrastáveis) e a medida dela
            if 0 <= self.selected < len(state["parts"]):
                part = state["parts"][self.selected]
                painter.setPen(QPen(QColor(theme.ACCENT), 1.2))
                painter.setBrush(QBrush(QColor(theme.PAPER)))
                for ring in [part["outline"], *(part.get("holes") or [])]:
                    for p in ring:
                        c = self.to_screen(p)
                        painter.drawRect(QRectF(c.x() - 3.5, c.y() - 3.5, 7, 7))
                painter.setBrush(Qt.NoBrush)
                x0, y0, x1, y1 = profile_defs.bounds([part])
                top = self.to_screen((x0, y1))
                painter.setPen(QPen(QColor(theme.INK_SOFT), 1))
                painter.drawText(QPointF(top.x(), top.y() - 6),
                                 f"{fmt_len(x1 - x0)} × {fmt_len(y1 - y0)} {unit}")
            painter.setPen(QPen(QColor(theme.ACCENT), 1.2, Qt.DashLine))
            if state.get("stretch_x") is not None:
                x = self.to_screen((state["stretch_x"], 0)).x()
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                painter.drawText(QPointF(x + 4, 14), "esticar largura")
            if state.get("stretch_y") is not None:
                y = self.to_screen((0, state["stretch_y"])).y()
                painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
                painter.drawText(QPointF(6, y - 4), "esticar altura")
            if state.get("opening_ref") is not None:
                painter.setPen(QPen(QColor(theme.ACCENT), 1.2, Qt.DashDotLine))
                x = self.to_screen((state["opening_ref"], 0)).x()
                painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                painter.drawText(QPointF(x + 4, 28), "aberturas")
        # origem: ponto de inserção
        o = self.to_screen((0.0, 0.0))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(theme.ACCENT), 1.6))
        painter.drawLine(o + QPointF(-12, 0), o + QPointF(12, 0))
        painter.drawLine(o + QPointF(0, -12), o + QPointF(0, 12))
        painter.drawEllipse(o, 4, 4)
        # desenho em andamento, com a medida do trecho
        if self.points and self.cursor is not None:
            painter.setPen(QPen(QColor(theme.ACCENT), 1.5))
            if self.mode == "rect":
                a, b = self.to_screen(self.points[0]), self.to_screen(self.cursor)
                painter.drawRect(QRectF(a, b).normalized())
                w = abs(self.cursor[0] - self.points[0][0])
                h = abs(self.cursor[1] - self.points[0][1])
                measure = f"{fmt_len(w)} × {fmt_len(h)} {unit}"
            else:
                pts = [self.to_screen(p) for p in [*self.points, self.cursor]]
                painter.drawPolyline(QPolygonF(pts))
                last = self.points[-1]
                length = math.dist(last, self.cursor)
                angle = math.degrees(math.atan2(self.cursor[1] - last[1],
                                                self.cursor[0] - last[0]))
                measure = f"{fmt_len(length)} {unit} · {fmt_angle(angle % 360.0)}"
            c = self.to_screen(self.cursor)
            painter.setPen(QPen(QColor(theme.INK), 1))
            painter.drawText(QPointF(c.x() + 10, c.y() + 20), measure)
        if self.cursor is not None and (self.mode != "select" or self._drag):
            self._marker(painter, self.to_screen(self.cursor))
            painter.setPen(QPen(QColor(theme.INK_SOFT), 1))
            label = f"{fmt_len(self.cursor[0])} ; {fmt_len(self.cursor[1])} {unit}"
            if self.snap_kind:
                label += f" · {self.snap_kind}"
            c = self.to_screen(self.cursor)
            painter.drawText(QPointF(c.x() + 10, c.y() - 8), label)
        if self.typed:
            painter.setPen(QPen(QColor(theme.ACCENT), 1))
            painter.drawText(QPointF(10, self.height() - 12),
                             f"Medida: {self.typed} {unit}   (Enter aplica; a;b = "
                             "deslocamento em x e y)")
        painter.end()

    def _marker(self, painter: QPainter, c: QPointF) -> None:
        """Marcador do ponto pego: quadrado (vértice, origem, interseção), triângulo
        (meio), círculo (aresta ou linha), ponto pequeno (grade)."""
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(theme.ACCENT), 1.4))
        kind = self.snap_kind
        if kind in ("vértice", "origem", "interseção"):
            painter.drawRect(QRectF(c.x() - 5, c.y() - 5, 10, 10))
        elif kind == "meio":
            painter.drawPolygon(QPolygonF([c + QPointF(0, -6), c + QPointF(6, 5),
                                           c + QPointF(-6, 5)]))
        elif kind == "grade":
            painter.drawRect(QRectF(c.x() - 2, c.y() - 2, 4, 4))
        else:
            painter.drawEllipse(c, 4, 4)

    # --- mouse e teclado --------------------------------------------------------------

    def part_at(self, q: QPointF) -> int:
        if self.state is None:
            return -1
        for i in reversed(range(len(self.state["parts"]))):
            if self._path(self.state["parts"][i]).contains(q):
                return i
        return -1

    def vertex_at(self, q: QPointF) -> tuple[int, int] | None:
        """(parte, vértice do contorno) perto do cursor; a parte escolhida primeiro."""
        if self.state is None:
            return None
        order = list(range(len(self.state["parts"])))
        if 0 <= self.selected < len(order):
            order.remove(self.selected)
            order.insert(0, self.selected)
        for i in order:
            for k, p in enumerate(self.state["parts"][i]["outline"]):
                s = self.to_screen(p)
                if math.dist((s.x(), s.y()), (q.x(), q.y())) < PICK_PX:
                    return i, k
        return None

    def edge_at(self, q: QPointF) -> tuple[int, int] | None:
        """(parte, vértice antes) da aresta do contorno sob o cursor."""
        if self.state is None:
            return None
        m = self.to_model(q)
        for i, part in enumerate(self.state["parts"]):
            ring = part["outline"]
            for k in range(len(ring)):
                s = self.to_screen(_closest(m, ring[k], ring[(k + 1) % len(ring)]))
                if math.dist((s.x(), s.y()), (q.x(), q.y())) < PICK_PX:
                    return i, k
        return None

    def select(self, index: int) -> None:
        self.selected = index
        self.picked.emit(index)
        self.update()

    def _remember(self) -> None:
        if self.state is not None:
            self._undo.append(copy.deepcopy(self.state["parts"]))
            del self._undo[:-50]

    def undo(self) -> None:
        """Desfaz o último desenho ou edição no editor (Ctrl+Z, antes de aplicar)."""
        if self.state is None or not self._undo:
            return
        self.state["parts"][:] = self._undo.pop()
        self.select(-1)
        self.changed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = event.position()
            return
        if self.state is None:
            return
        q = event.position()
        if event.button() == Qt.RightButton:
            if self.mode != "select" and self.points:
                if self.mode == "polygon" and len(self.points) >= 3:
                    self.close_polygon()  # botão direito fecha o polígono
                else:
                    self.points = []
                self.update()
            elif (found := self.vertex_at(q)) is not None:
                self.remove_vertex(*found)  # botão direito no vértice: tira o vértice
            return
        if event.button() != Qt.LeftButton:
            return
        if self.mode == "select":
            found = self.vertex_at(q)
            if found is not None:
                self._remember()
                self._drag = {"vertex": found}
                self.select(found[0])
                return
            index = self.part_at(q)
            self.select(index)
            if index >= 0:
                self._remember()
                self._drag = {"part": index, "from": self.snapped(q),
                              "original": copy.deepcopy(self.state["parts"][index])}
            return
        p, self.snap_kind = self.snap(q, shift=bool(event.modifiers() & Qt.ShiftModifier))
        self.add_point(p)

    def add_point(self, p) -> None:
        """Mais um ponto do desenho em andamento (clique ou medida digitada)."""
        self.typed = ""
        if self.mode == "rect":
            if not self.points:
                self.points = [p]
            else:
                (ax, ay), (bx, by) = self.points[0], p
                self.points = []
                if abs(ax - bx) > 1e-9 and abs(ay - by) > 1e-9:
                    self.add_outline([[ax, ay], [bx, ay], [bx, by], [ax, by]])
        elif len(self.points) >= 3 and math.dist(p, self.points[0]) < 1e-9:
            self.close_polygon()
        elif not self.points or math.dist(p, self.points[-1]) > 1e-9:
            self.points.append(p)
        self.update()

    def mouseDoubleClickEvent(self, event):
        q = event.position()
        if self.mode == "polygon" and len(self.points) >= 3:
            self.close_polygon()
        elif self.mode == "select" and self.vertex_at(q) is None:
            found = self.edge_at(q)
            if found is not None:  # clique duplo na aresta: vértice novo
                self.insert_vertex(*found, self.snapped(q))

    def mouseMoveEvent(self, event):
        q = event.position()
        if self._pan is not None:
            d = q - self._pan
            self._pan = q
            self.center = (self.center[0] - d.x() / self.scale, self.center[1] + d.y() / self.scale)
            self.update()
            return
        if self._drag and "vertex" in self._drag:
            i, k = self._drag["vertex"]
            self.cursor, self.snap_kind = self.snap(q, skip=(i, k))
            self.state["parts"][i]["outline"][k] = [self.cursor[0], self.cursor[1]]
        elif self._drag:
            self.cursor, self.snap_kind = self.snap(q)
            dx = self.cursor[0] - self._drag["from"][0]
            dy = self.cursor[1] - self._drag["from"][1]
            original = self._drag["original"]

            def moved(ring):
                return [[round(x + dx, 9), round(y + dy, 9)] for x, y in ring]

            self.state["parts"][self._drag["part"]].update(
                outline=moved(original["outline"]),
                holes=[moved(h) for h in original.get("holes") or []])
        else:
            self.cursor, self.snap_kind = self.snap(
                q, shift=bool(event.modifiers() & Qt.ShiftModifier))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = None
        elif event.button() == Qt.LeftButton and self._drag:
            drag, self._drag = self._drag, None
            if "vertex" in drag or self.state["parts"][drag["part"]] != drag["original"]:
                self.changed.emit()
            elif self._undo:
                self._undo.pop()  # só escolheu a parte: nada a desfazer
            self.update()

    def leaveEvent(self, event):
        self.cursor = None
        self.update()

    def wheelEvent(self, event):
        before = self.to_model(event.position())
        self.scale = max(20.0, min(20000.0, self.scale * (1.2 if event.angleDelta().y() > 0
                                                          else 1 / 1.2)))
        after = self.to_model(event.position())
        self.center = (self.center[0] + before[0] - after[0],
                       self.center[1] + before[1] - after[1])
        self.update()

    def apply_typed(self) -> bool:
        """Medida digitada, na unidade de trabalho: "a" = comprimento na direção do
        cursor; "a;b" = deslocamento em x e y a partir do último ponto (no retângulo,
        largura;altura)."""
        text, self.typed = self.typed.strip(), ""
        if not text or not self.points:
            self.update()
            return False
        base = self.points[-1]
        try:
            if ";" in text:
                a, b = (parse_len(t) for t in text.split(";", 1))
                p = (base[0] + a, base[1] + b)
            else:
                length = parse_len(text)
                target = self.cursor or (base[0] + 1.0, base[1])
                angle = math.atan2(target[1] - base[1], target[0] - base[0])
                p = (base[0] + length * math.cos(angle), base[1] + length * math.sin(angle))
        except ValueError:
            self.session.message(f"medida inválida: {text!r}", "recusa")
            self.update()
            return False
        self.add_point((round(p[0], 9), round(p[1], 9)))
        return True

    def event(self, event):
        # Ctrl+Z desfaz no editor (o atalho da janela principal desfaria o projeto)
        if (event.type() == QEvent.ShortcutOverride and event.matches(QKeySequence.Undo)
                and self._undo):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        key, text = event.key(), event.text()
        drawing = self.mode != "select" and bool(self.points)
        if event.matches(QKeySequence.Undo):
            self.undo()
        elif drawing and text and (text.isdigit() or text in ",.;-"):
            self.typed += text
            self.update()
        elif drawing and key == Qt.Key_Backspace and self.typed:
            self.typed = self.typed[:-1]
            self.update()
        elif key == Qt.Key_Escape and (self.typed or self.points):
            if self.typed:
                self.typed = ""
            else:
                self.points = []
            self.update()
        elif key in (Qt.Key_Return, Qt.Key_Enter) and self.typed:
            self.apply_typed()
        elif key in (Qt.Key_Return, Qt.Key_Enter) and self.mode == "polygon":
            self.close_polygon()
        elif key == Qt.Key_Delete and self.selected >= 0:
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
        self._remember()
        material = (self.state["parts"][self.selected]["material"]
                    if 0 <= self.selected < len(self.state["parts"]) else "Concreto")
        self.state["parts"].append({"material": material, "role": "core",
                                    "outline": [[float(x), float(y)] for x, y in outline],
                                    "holes": []})
        self.select(len(self.state["parts"]) - 1)
        self.changed.emit()

    def insert_vertex(self, index: int, after: int, p) -> None:
        self._remember()
        self.state["parts"][index]["outline"].insert(after + 1, [p[0], p[1]])
        self.select(index)
        self.changed.emit()

    def remove_vertex(self, index: int, k: int) -> None:
        ring = self.state["parts"][index]["outline"]
        if len(ring) <= 3:
            self.session.message("a parte precisa de 3 vértices ou mais", "recusa")
            return
        self._remember()
        del ring[k]
        self.select(index)
        self.changed.emit()

    def remove_selected(self) -> None:
        if self.state is None or not 0 <= self.selected < len(self.state["parts"]):
            return
        self._remember()
        del self.state["parts"][self.selected]
        self.select(-1)
        self.changed.emit()


def _closest(p, a, b) -> tuple[float, float]:
    """Ponto do segmento ``a``–``b`` mais perto de ``p``."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    n = dx * dx + dy * dy
    t = 0.0 if n < 1e-18 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return ax + t * dx, ay + t * dy


def _intersection(a, b, c, d) -> tuple[float, float] | None:
    """Cruzamento de dois segmentos fora das pontas, ou ``None``."""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-15:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return (round(a[0] + t * r[0], 9), round(a[1] + t * r[1], 9))
    return None


def fmt_angle(degrees: float) -> str:
    return f"{degrees:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "°"



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
        self.from_selection_button = QPushButton("Criar a partir da seleção")
        self.from_selection_button.setToolTip(
            "Parede de camadas, viga ou pilar retangular ou circular selecionado vira um "
            "perfil novo, com uma parte por camada ou pela seção")
        self.from_selection_button.clicked.connect(self.from_selection)
        left.addWidget(self.from_selection_button)
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
            exact.addWidget(QLabel(f"{label} ({units.work_symbol()})"))
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
        lines = (("stretch_x", "Esticar na largura", "x ="),
                 ("stretch_y", "Esticar na altura", "y ="),
                 ("opening_ref", "Referência das aberturas (parede)", "x ="))
        for row_i, (key, text, axis) in enumerate(lines):
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
        for key in self.stretch_boxes:
            value = state.get(key) if state else None
            self.stretch_boxes[key].setChecked(value is not None)
            self.stretch_fields[key].setText(fmt_len(value, exact=True) if value is not None
                                             else "")
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
            middle = (y0 + y1) / 2 if key == "stretch_y" else (x0 + x1) / 2
            field.setText(fmt_len(round(middle, 3), exact=True))
        try:
            self.state[key] = parse_len(field.text()) if on else None
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
            x, y, w, h = (parse_len(f.text()) for f in self.rect_fields)
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
        unit = units.work_symbol()  # medidas na unidade de trabalho (spec/ui 44 §2a)
        self.size_label.setText(f"Largura {fmt_len(w)} {unit} · Altura {fmt_len(h)} {unit} · "
                                f"Área {fmt(area)} m²")
        try:
            resolved = profile_defs.resolve_overlaps(state["parts"])
            profile_defs.validate({**state, "parts": resolved})
            problem = ""
        except OpError as e:
            problem = str(e)
        hint = ("A cruz é o ponto de inserção: o eixo da viga e o ponto do pilar. Os "
                "pontos atraem vértices, meios, arestas e cruzamentos; Shift trava a "
                f"direção; digite a medida em {unit} e Enter. Arraste os vértices; clique "
                "duplo na aresta cria um, botão direito tira.")
        if not problem and resolved is not state["parts"]:  # houve recorte
            hint = ("Há partes sobrepostas: ao aplicar, o núcleo recorta o acabamento e, "
                    "entre iguais, a de cima recorta a de baixo.")
        self.note.setText(f"{problem[:1].upper()}{problem[1:]}." if problem else hint)
        self.note.setStyleSheet(f"color: {theme.ERROR if problem else theme.INK_SOFT}")

    # --- gravar -----------------------------------------------------------------------

    def _run(self, build) -> bool:
        """Grava pela sessão; a recusa do núcleo aparece aqui, e não só na janela
        principal (que fica atrás deste diálogo)."""
        count = len(self.session.messages)
        if self.session.run(build):
            return True
        news = [m["text"] for m in self.session.messages[count:] if m["level"] == "recusa"]
        text = news[-1] if news else "o perfil não pôde ser gravado"
        self.note.setText(f"Não aplicado: {text}.")
        self.note.setStyleSheet(f"color: {theme.ERROR}")
        if self.isVisible():
            QMessageBox.warning(self, "Perfil não aplicado", f"{text[:1].upper()}{text[1:]}.")
        return False

    def apply(self) -> bool:
        if self.current is None or not self.dirty:
            return True
        doc, def_id = self.session.doc, self.current
        before = profile_defs.state(doc, def_id)
        changes = {k: copy.deepcopy(v) for k, v in self.state.items() if v != before.get(k)}
        if changes and not self._run(lambda: profile_defs.edit(doc, def_id, **changes)):
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

        if self._run(build):
            self.dirty = False
            self.refresh(holder["id"])

    def add(self) -> None:
        names = {s.Name for s in self.defs()}
        self._create(default_state(_unique(names, "Novo perfil")))

    def from_selection(self) -> None:
        """Criar perfil a partir da seleção (spec/ui 41 §4): um elemento selecionado."""
        if self.dirty and not self._resolve_pending():
            return
        doc = self.session.doc
        found = [doc.find(g) for g in sorted(self.session.selection)]
        found = [e for e in found if e is not None]
        if len(found) != 1:
            self.session.message("selecione uma parede, viga ou pilar", "recusa")
            return
        try:
            state = profile_defs.from_element(doc, found[0])
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        self._create(state)

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
