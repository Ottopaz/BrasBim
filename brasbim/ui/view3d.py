# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista 3D (``spec/ui/01-janela-e-ferramentas.md`` §4 e
``spec/ui/07-medidas-e-edicao-no-3d.md`` §3): órbita, deslocamento e aproximação; seleção
por clique; as mesmas ferramentas da planta, com o ponto dado no plano de trabalho.

Desenha as malhas de ``scene3d.Scene`` com OpenGL de função fixa (arrays no cliente, sem
recursos na placa), o que sobrevive à troca de janela-mãe. Câmera, raio e escolha por raio
ficam em ``scene3d``, sem Qt."""

from __future__ import annotations

import logging
import math

import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QToolTip

from brasbim.core import edit_state, snap, transform
from brasbim.core.document import OpError
from brasbim.ui import theme
from brasbim.ui.handles3d import FillingHandle3D, WallHandle3D, filling_handles, wall_handles
from brasbim.ui.measure_box import ToolInput
from brasbim.ui.scene3d import (
    ORIENTATION_MARKS,
    Camera,
    Scene,
    affine_of,
    area_scene,
    current_mark,
    opposite_mark,
    orientation_marks,
    orientation_pick,
    ray_plane,
    transformed,
)
from brasbim.ui.selection_bar import ZOOM_PAUSE_MS
from brasbim.ui.tools import Mods, ToolBox

log = logging.getLogger(__name__)

try:
    from OpenGL import GL
    from OpenGL.error import Error as GLError
except ImportError:  # PyOpenGL ausente: a vista não desenha
    GL = None
    GLError = RuntimeError

_SELECT = np.array(theme.rgbf(theme.ACCENT), dtype=np.float32)
_BACKGROUND = theme.rgbf(theme.VIEW3D_BACKGROUND)
_MARK_COLOR = {"invalid": theme.rgbf(theme.ERROR), "guide": theme.rgbf("#A9739B"),
               "reference": theme.rgbf(theme.ACCENT)}
_PREVIEW = theme.rgbf(theme.ACCENT)
CLICK_PX = 4  # o clique só vale se o cursor andar menos que isto (§3.1)
HANDLE_PX = 8  # raio de captura das alças na tela (spec/ui 08 §3)
SNAP_PX = 10
TRANSFORM_TOOLS = ("move", "copy", "rotate", "mirror")
# Controle de orientação (spec/ui 40 §4), em pixels: raio dos eixos, das marcas e margem
ORIENT_AXIS = 32
ORIENT_MARK = 9
ORIENT_MARGIN = 14
_AXIS_COLORS = {"x": theme.AXIS_X, "y": theme.AXIS_Y, "z": theme.AXIS_Z}


def display_layers_locked(doc) -> set[str]:
    from brasbim.core import display_layers

    return display_layers.locked_ids(doc)


def draw_scene(scene: Scene, camera: Camera, aspect: float, selected=frozenset(),
               hover: str | None = None) -> None:
    """Pinta as malhas (com os vidros por último) e as arestas no contexto OpenGL atual:
    a vista na tela e a imagem da vista 3D salva na prancha (spec/ui 25 §5)."""
    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadMatrixd(camera.projection(aspect).T.flatten())
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadMatrixd(camera.view().T.flatten())
    GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
    GL.glEnableClientState(GL.GL_COLOR_ARRAY)
    for gid, mesh in scene.meshes.items():
        colors = mesh.colors
        if gid in selected:
            colors = (colors * 0.4 + _SELECT * 0.6).astype(np.float32)
        elif gid == hover:  # destaque sob o cursor (spec/ui 28 §3)
            colors = (colors * 0.75 + _SELECT * 0.25).astype(np.float32)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, mesh.vertices)
        GL.glColorPointer(3, GL.GL_FLOAT, 0, colors)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(mesh.vertices))
    _paint_glass(scene, selected)
    GL.glDisableClientState(GL.GL_COLOR_ARRAY)
    GL.glColor3f(0.25, 0.25, 0.25)
    for mesh in scene.meshes.values():
        if len(mesh.edges):
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, mesh.edges)
            GL.glDrawArrays(GL.GL_LINES, 0, len(mesh.edges))
    GL.glDisableClientState(GL.GL_VERTEX_ARRAY)


def _paint_glass(scene: Scene, selected) -> None:
    """Vidros translúcidos, depois das peças opacas (spec/ui 09 §7)."""
    glass = [(gid, m) for gid, m in scene.meshes.items() if m.glass is not None]
    if not glass:
        return
    GL.glEnable(GL.GL_BLEND)
    GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    GL.glDepthMask(GL.GL_FALSE)
    for gid, mesh in glass:
        colors = mesh.glass_colors
        if gid in selected:
            colors = colors.copy()
            colors[:, :3] = colors[:, :3] * 0.4 + _SELECT * 0.6
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, mesh.glass)
        GL.glColorPointer(4, GL.GL_FLOAT, 0, colors)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(mesh.glass))
    GL.glDepthMask(GL.GL_TRUE)
    GL.glDisable(GL.GL_BLEND)


def storey_of(element):
    """Pavimento que contém o elemento (a porta, pelo da parede se preciso)."""
    container = ifcopenshell.util.element.get_container(element)
    if container is None and (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
        host = transform.host_wall(element)
        container = ifcopenshell.util.element.get_container(host) if host else None
    return container if container is not None and container.is_a("IfcBuildingStorey") \
        else None


def storey_z(storey) -> float:
    if storey is None:
        return 0.0
    if storey.ObjectPlacement is not None:
        return float(ifcopenshell.util.placement.get_local_placement(
            storey.ObjectPlacement)[2][3])
    return float(storey.Elevation or 0.0)


class View3D(QOpenGLWidget, ToolInput):
    cursor_moved = Signal(float, float)
    hint_changed = Signal(str)
    tool_finished = Signal()
    tool_options_changed = Signal()
    tool_requested = Signal(str)  # Enter repete a última ferramenta (spec/ui 23 §3.2)
    context_requested = Signal(object, object)  # (GlobalId ou None, posição global)

    def __init__(self, scene: Scene, toolbox: ToolBox, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.toolbox = toolbox
        self.ctx = toolbox.ctx
        self.camera = Camera()
        self.selection_bar = None  # mini-barra (spec/ui 03 §5), posta pela janela
        self._press: tuple[str, QPointF] | None = None  # botão e posição do clique
        self._drag: tuple[str, QPointF] | None = None  # órbita ou deslocamento
        self._zooming = QTimer(self, singleShot=True, interval=ZOOM_PAUSE_MS)
        self._zooming.timeout.connect(self.update)  # a mini-barra volta ao parar o zoom
        self.failed = GL is None
        self.window_start: QPointF | None = None  # janela por dois cliques (spec/ui 28 §3)
        self.mouse_pos: QPointF | None = None
        self.orientation_hover: str | None = None  # marca sob o cursor (spec/ui 40 §4)
        self._orient_key: str | None = None  # marca do clique em curso
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self._init_tool_input()

    # --- câmera ------------------------------------------------------------------------

    @property
    def selection(self) -> set[str]:
        return self.ctx.session.selection

    def fit(self) -> None:
        bounds = self.scene.bounds()
        if bounds is not None:
            self.camera.frame(*bounds)
        self.update()

    def standard_view(self, name: str) -> None:
        """Vista 3D padrão (topo, frente, laterais, isométricas) com tudo enquadrado."""
        self.camera.look_from(name)
        self.fit()

    # --- controle de orientação (spec/ui 40 §4) ------------------------------------------

    def orientation_center(self) -> tuple[float, float]:
        r = ORIENT_AXIS + ORIENT_MARK
        return self.width() - ORIENT_MARGIN - r, ORIENT_MARGIN + r

    def on_orientation(self, pos: QPointF) -> bool:
        """``pos`` cai no controle (o disco dos eixos com as marcas)."""
        cx, cy = self.orientation_center()
        return math.hypot(pos.x() - cx, pos.y() - cy) <= ORIENT_AXIS + ORIENT_MARK

    def orientation_at(self, pos: QPointF) -> str | None:
        return orientation_pick(self.camera, self.orientation_center(), ORIENT_AXIS,
                                (pos.x(), pos.y()), ORIENT_MARK + 2)

    def orient(self, key: str) -> None:
        """Olha da direção da marca, com o mesmo centro e distância; de novo na mesma
        marca, a vista inversa."""
        if current_mark(self.camera) == key:
            key = opposite_mark(key)
        self.camera.look_from(ORIENTATION_MARKS[key][1])
        self.update()

    def _paint_orientation(self) -> None:
        from PySide6.QtGui import QColor, QFont, QPainter, QPen

        center = self.orientation_center()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(max(font.pointSizeF() - 1, 6))
        painter.setFont(font)
        back = QColor(theme.VIEW3D_BACKGROUND)
        for key, x, y, depth in orientation_marks(self.camera, center, ORIENT_AXIS):
            color = QColor(_AXIS_COLORS[key[1]])
            if depth > 0.05:  # atrás do centro: mais apagado
                color.setAlphaF(0.55)
            hot = key == self.orientation_hover
            if key[0] == "+":
                painter.setPen(QPen(color, 2))
                painter.drawLine(QPointF(*center), QPointF(x, y))
            r = ORIENT_MARK if key[0] == "+" else ORIENT_MARK - 3
            if hot:
                painter.setPen(QPen(QColor(theme.ACCENT), 2))
                painter.setBrush(QColor(theme.FIELD))
                painter.drawEllipse(QPointF(x, y), r + 3, r + 3)
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(color if key[0] == "+" else back)
            painter.drawEllipse(QPointF(x, y), r, r)
            if key[0] == "+":
                painter.setPen(QColor(theme.ACCENT_INK))
                painter.drawText(QRectF(x - r, y - r, 2 * r, 2 * r), Qt.AlignCenter,
                                 key[1].upper())
        painter.end()

    def frame_selection(self) -> bool:
        """Enquadra a seleção mantendo a direção da câmera (spec/ui 07 §4)."""
        bounds = self.scene.selection_bounds(self.selection)
        if bounds is None:
            return False
        self.camera.frame(*bounds)
        self.update()
        return True

    def selection_rect(self) -> tuple[float, float, float, float] | None:
        """Retângulo da seleção na tela (x0, y0, x1, y1), para a mini-barra."""
        bounds = self.scene.selection_bounds(self.selection)
        if bounds is None:
            return None
        low, high = bounds
        pts = [self.camera.project((x, y, z), self.width(), self.height())
               for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
        pts = [p for p in pts if p is not None]
        if not pts:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    # --- ponto no plano de trabalho (§3.2) -----------------------------------------------

    def work_z(self) -> float:
        """Cota do plano de trabalho: o pavimento da seleção nas transformações, se for um
        só; senão o pavimento ativo."""
        session = self.ctx.session
        if self.toolbox.active.name in TRANSFORM_TOOLS and self.selection:
            storeys = set()
            for gid in self.selection:
                element = session.doc.find(gid)
                storey = storey_of(element) if element is not None else None
                storeys.add(storey.GlobalId if storey is not None else None)
            if len(storeys) == 1 and None not in storeys:
                return storey_z(session.doc.find(storeys.pop()))
        return storey_z(session.storey)

    def ray(self, pos: QPointF):
        return self.camera.ray(pos.x(), pos.y(), self.width(), self.height())

    def pick(self, pos: QPointF) -> str | None:
        hit = self.scene.pick(*self.ray(pos))
        return hit[0] if hit else None

    def world_point(self, pos: QPointF) -> tuple[float, float] | None:
        """(x, y) do pavimento sob o cursor: do elemento atingido ou do plano de trabalho.
        Também ajusta a tolerância de *snap* à profundidade do ponto."""
        origin, direction = self.ray(pos)
        hit = self.scene.pick(origin, direction)
        point = hit[1] if hit else ray_plane(origin, direction, self.work_z())
        if point is None:
            return None
        self.ctx.tol = SNAP_PX * self.camera.pixel_size(point, self.height())
        return float(point[0]), float(point[1])

    # --- OpenGL ------------------------------------------------------------------------

    def initializeGL(self):
        if GL is None:
            return
        try:
            GL.glClearColor(*_BACKGROUND, 1.0)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(1.0, 1.0)
        except GLError as e:  # contexto sem suporte a função fixa
            self.failed = True
            log.warning("vista 3D indisponível: %s", e)

    def resizeGL(self, w, h):
        if not self.failed:
            GL.glViewport(0, 0, w, h)

    def _ghost_gids(self) -> set[str]:
        """Seleção mais as esquadrias das paredes selecionadas (elas vão junto)."""
        doc, selection = self.ctx.session.doc, self.selection
        out = set(selection)
        for gid in self.scene.meshes:
            element = doc.find(gid)
            filling = element is not None and (element.is_a("IfcDoor")
                                               or element.is_a("IfcWindow"))
            if filling and gid not in selection:
                host = transform.host_wall(element)
                if host is not None and host.GlobalId in selection:
                    out.add(gid)
        return out

    def paintGL(self):
        if self.failed:
            return
        selected = self.selection
        hover = self.ctx.hover if self.ctx.hover not in selected else None
        draw_scene(self.scene, self.camera, self.width() / max(self.height(), 1), selected,
                   hover)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        self._paint_tool()
        self._paint_handles()
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        if self.window_start is not None and self.mouse_pos is not None:
            self._paint_window()
        self._paint_orientation()
        if self.selection_bar is not None:
            # Mover um widget filho durante a pintura do OpenGL deixa cópias dele na tela:
            # a mini-barra é posta depois que a pintura termina.
            QTimer.singleShot(0, self.selection_bar, self.selection_bar.place)

    @property
    def navigating(self) -> bool:
        """Órbita, deslocamento ou zoom em curso (a mini-barra some até parar)."""
        return self._drag is not None or self._zooming.isActive()

    def _paint_tool(self) -> None:
        """Fantasma da seleção transformada e marcas da ferramenta no plano (§3.3)."""
        tool = self.toolbox.active
        fn = tool.transform_fn()
        if fn is not None:
            matrix = affine_of(fn)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glDepthMask(GL.GL_FALSE)
            GL.glColor4f(*_SELECT, 0.35)
            for gid in self._ghost_gids():
                mesh = self.scene.meshes.get(gid)
                if mesh is not None:
                    verts = transformed(mesh.vertices, matrix)
                    GL.glVertexPointer(3, GL.GL_FLOAT, 0, verts)
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(verts))
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisable(GL.GL_BLEND)
        z = self.work_z() + 0.005
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glLineWidth(1.5)
        for mark in tool.preview() + self.ctx.guide_marks():
            if mark.style == "gap" or len(mark.points) < 2:
                continue
            GL.glColor3f(*_MARK_COLOR.get(mark.style, _PREVIEW))
            pts = np.array([(x, y, z) for x, y in mark.points], dtype=np.float32)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, pts)
            GL.glDrawArrays(GL.GL_LINE_LOOP if mark.closed else GL.GL_LINE_STRIP, 0, len(pts))
        snapped = tool.snapped
        if snapped is not None and snapped.kind != "free":
            GL.glPointSize(7)
            GL.glColor3f(*_PREVIEW)
            pts = np.array([(*snapped.point, z)], dtype=np.float32)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, pts)
            GL.glDrawArrays(GL.GL_POINTS, 0, 1)
        GL.glLineWidth(1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)

    # --- alças da parede (spec/ui 08 §3) -------------------------------------------------

    def selected_wall(self) -> snap.WallPath | None:
        """Parede selecionada sozinha (de qualquer pavimento), com a ferramenta Selecionar."""
        tool, selection = self.toolbox.active, self.selection
        if tool.name != "select" or len(selection) != 1:
            return None
        doc = self.ctx.session.doc
        element = doc.find(next(iter(selection)))
        if element is None or not element.is_a("IfcWall"):
            return None
        storey = storey_of(element)
        if storey is None:
            return None
        walls = self.ctx.walls if storey.GlobalId == self.ctx.session.storey_id \
            else snap.wall_paths(doc, storey)
        return next((w for w in walls if w.gid == element.GlobalId), None)

    def selected_filling(self):
        """(porta ou janela selecionada sozinha, parede dela) ou (None, None)."""
        doc, selection = self.ctx.session.doc, self.selection
        if len(selection) != 1:
            return None, None
        element = doc.find(next(iter(selection)))
        from brasbim.core.structure import skylights

        if element is None or not (element.is_a("IfcDoor") or element.is_a("IfcWindow"))                 or skylights.is_skylight(element):
            return None, None
        host = transform.host_wall(element)
        storey = storey_of(element)
        if host is None or storey is None:
            return None, None
        walls = (self.ctx.walls if storey.GlobalId == self.ctx.session.storey_id
                 else snap.wall_paths(doc, storey))
        return element, next((w for w in walls if w.gid == host.GlobalId), None)

    def handles(self) -> list[tuple[str, tuple[float, float, float]]]:
        doc = self.ctx.session.doc
        if any(edit_state.is_locked(doc, g) for g in self.ctx.session.selection):
            return []  # travado: sem alças (spec/ui 39 §5)
        try:
            element, wall = self.selected_filling()
            if element is not None and wall is not None:  # spec/ui 09 §4.2
                return filling_handles(doc, wall, element)
            wall = self.selected_wall()
            return wall_handles(doc, wall) if wall is not None else []
        except (OpError, ValueError, KeyError):
            return []

    def handle_at(self, pos: QPointF) -> str | None:
        best = None
        for kind, point in self.handles():
            q = self.camera.project(point, self.width(), self.height())
            if q is None:
                continue
            d = math.hypot(q[0] - pos.x(), q[1] - pos.y())
            if d <= HANDLE_PX and (best is None or d < best[0]):
                best = (d, kind)
        return best[1] if best else None

    def _start_handle(self, kind: str) -> None:
        tool = self.toolbox.active
        element, wall = self.selected_filling()
        if element is not None and wall is not None:
            tool.drag3d = FillingHandle3D(self.ctx, wall, element, kind)
        else:
            tool.drag3d = WallHandle3D(self.ctx, self.selected_wall(), kind)
        tool.drag3d.anchor = np.array(dict(self.handles())[kind])  # o plano passa pela alça
        tool.drag3d.update()
        self.after_tool_input()

    def _feed_handle(self, pos: QPointF, mods: Mods) -> None:
        """Leva a alça presa ao cursor: ponto no plano (pontas, face, inclinação), cota
        (topo, base) ou ponto no plano da parede (vértice interno do topo)."""
        h = self.toolbox.active.drag3d
        origin, direction = self.ray(pos)
        if h.planar:
            hit = ray_plane(origin, direction, h.plane_z)
            if hit is None:
                return
            self.ctx.tol = SNAP_PX * self.camera.pixel_size(hit, self.height())
            p = (float(hit[0]), float(hit[1]))
            if h.kind == "face":
                p = self.ctx.snap(p, Mods(alt=mods.alt)).point
            elif h.kind != "tilt":
                fixed = h.wall.path.end if h.kind == "start" else h.wall.path.start
                p = self.ctx.snap(p, mods, fixed).point
            h.update(point=p, ctrl=mods.ctrl)
        else:
            if h.in_wall_plane:  # plano vertical da parede (§4.1)
                o, y = h.wall.frame.to_global((0.0, 0.0)), h.wall.frame.to_global((0.0, 1.0))
                normal = np.array([y[0] - o[0], y[1] - o[1], 0.0])
            else:  # plano vertical de frente para a câmera
                forward, _, _ = self.camera.axes()
                normal = np.array([forward[0], forward[1], 0.0])
            if np.linalg.norm(normal) < 1e-6:
                return  # olhando de cima: não há plano vertical de frente
            normal /= np.linalg.norm(normal)
            anchor = h.anchor
            denom = float(direction @ normal)
            if abs(denom) < 1e-9:
                return
            t = float((anchor - origin) @ normal) / denom
            if t <= 0:
                return
            hit = origin + t * direction
            tol = SNAP_PX * self.camera.pixel_size(hit, self.height())
            point = (float(hit[0]), float(hit[1])) if h.in_wall_plane else None
            h.update(point=point, z=h.snap_z(float(hit[2]), mods.alt, tol), ctrl=mods.ctrl)
        h.moved = True
        self.after_tool_input()

    def _paint_handles(self) -> None:
        tool = self.toolbox.active
        h = getattr(tool, "drag3d", None)
        GL.glDisable(GL.GL_DEPTH_TEST)
        if h is not None:
            GL.glLineWidth(1.5)
            GL.glColor3f(*(_MARK_COLOR["invalid"] if h.error else _PREVIEW))
            for line in h.outline():
                pts = np.array(line, dtype=np.float32)
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, pts)
                GL.glDrawArrays(GL.GL_LINE_STRIP, 0, len(pts))
            GL.glLineWidth(1.0)
        hot = h.kind if h is not None else (
            self.handle_at(self.mouse_pos) if self.mouse_pos is not None else None)
        for size, cold, filled in ((11, _PREVIEW, _PREVIEW), (7, (1.0, 1.0, 1.0), _PREVIEW)):
            GL.glPointSize(size)
            for kind, point in self.handles():
                GL.glColor3f(*(filled if kind == hot else cold))
                pts = np.array([point], dtype=np.float32)
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, pts)
                GL.glDrawArrays(GL.GL_POINTS, 0, 1)
        GL.glEnable(GL.GL_DEPTH_TEST)

    # --- mouse -------------------------------------------------------------------------

    @staticmethod
    def _mods(event) -> Mods:
        m = event.modifiers()
        return Mods(bool(m & Qt.ShiftModifier), bool(m & Qt.AltModifier),
                    bool(m & Qt.ControlModifier))

    def _feed_move(self, pos: QPointF, mods: Mods) -> None:
        """Movimento sem arrastar: a ferramenta (que não Selecionar) recebe o ponto."""
        tool = self.toolbox.active
        if tool.name == "select":
            hover = self.pick(pos) if self.ctx.accumulate else None  # destaque (ui/28 §3)
            if hover in display_layers_locked(self.ctx.session.doc):
                hover = None
            if hover != self.ctx.hover or self.window_start is not None:
                self.ctx.hover = hover
                self.update()
            return
        p = self.world_point(pos)
        if p is None:
            return
        self.cursor_moved.emit(*p)
        tool.move(p, mods)
        self.restart_dwell()
        self.after_tool_input()

    def anchor_screen(self, p):
        """Ponto do pavimento ativo projetado na tela (balão da linha de referência)."""
        q = self.camera.project((p[0], p[1], self.work_z()), self.width(), self.height())
        return QPointF(*q) if q is not None else None

    def mousePressEvent(self, event):
        self.before_press()
        self.setFocus()
        self.ctx.input_view = self
        button = event.button()
        tool = self.toolbox.active
        h = getattr(tool, "drag3d", None)
        if button == Qt.LeftButton and h is not None:  # alça presa ao cursor: confirma
            self._feed_handle(event.position(), self._mods(event))
            tool.commit3d()
            self.after_tool_input()
            return
        if button == Qt.LeftButton and self.on_orientation(event.position()):
            # controle de orientação: clique escolhe a vista, arraste orbita (spec/ui 40 §4)
            self._orient_key = self.orientation_at(event.position())
            self._press = ("orient", event.position())
            return
        kind = self.handle_at(event.position()) if button == Qt.LeftButton else None
        if kind is not None:
            self._start_handle(kind)
            self._press = ("handle", event.position())
            return
        if button == Qt.MiddleButton:
            self._drag = ("pan", event.position())
        elif button in (Qt.LeftButton, Qt.RightButton):
            self._press = ("left" if button == Qt.LeftButton else "right", event.position())

    def mouseMoveEvent(self, event):
        self.ctx.input_view = self
        pos = self.mouse_pos = event.position()
        press = self._press
        h = getattr(self.toolbox.active, "drag3d", None)
        if h is not None:
            if press is None or (pos - press[1]).manhattanLength() >= CLICK_PX:
                self._feed_handle(pos, self._mods(event))
            return
        if press is not None and press[0] in ("left", "orient") and self._drag is None \
                and (pos - press[1]).manhattanLength() >= CLICK_PX:
            self._drag = ("orbit", press[1])
            self._press = None
        if self._drag is None:
            hover = self.orientation_at(pos) if self.on_orientation(pos) else None
            if hover != self.orientation_hover:
                self.orientation_hover = hover
                if hover:
                    self.setCursor(Qt.PointingHandCursor)
                else:
                    self.apply_cursor()
                self.update()
            if press is None and self.on_orientation(pos):
                return  # a ferramenta não segue o cursor sobre o controle
            self._feed_move(pos, self._mods(event))
            return
        kind, last = self._drag
        delta = pos - last
        self._drag = (kind, pos)
        camera = self.camera
        if kind == "orbit":
            camera.yaw -= delta.x() * 0.01
            camera.pitch = min(max(camera.pitch + delta.y() * 0.01, -1.5), 1.5)
        else:
            _, right, up = camera.axes()
            k = camera.distance / max(self.height(), 1)
            camera.target = camera.target - right * delta.x() * k + up * delta.y() * k
        self.update()

    def mouseReleaseEvent(self, event):
        press, self._press = self._press, None
        tool = self.toolbox.active
        h = getattr(tool, "drag3d", None)
        if h is not None and press is not None and press[0] == "handle":
            if h.moved:
                h.update(ctrl=self._mods(event).ctrl)
                tool.commit3d()
            else:
                h.sticky = True  # clique sem arrastar: a alça segue o cursor
            self.after_tool_input()
            return
        if self._drag is not None:
            self._drag = None
            self.update()  # a mini-barra volta junto à seleção
            return
        if press is None:
            return
        button, at = press
        if button == "orient":
            if self._orient_key is not None:
                self.orient(self._orient_key)
            return
        self.click(at, button, self._mods(event), event.globalPosition().toPoint())

    def click(self, pos: QPointF, button: str, mods: Mods, global_pos=None) -> None:
        """Clique (sem arrastar) na posição da tela (§3.1)."""
        tool = self.toolbox.active
        session = self.ctx.session
        if tool.name == "select":
            if button == "left" and self.window_start is not None:
                self.finish_window(pos, mods)
                return
            gid = self.pick(pos)
            if button == "right":
                if gid and gid not in session.selection:
                    session.select([gid], add=mods.ctrl or self.ctx.accumulate)
                self.context_requested.emit(gid, global_pos)
            elif self.ctx.accumulate:  # soma; Shift tira; vazio abre a janela (ui/28 §3)
                if gid is None:
                    self.window_start = QPointF(pos)
                elif mods.shift:
                    session.select(session.selection - {gid})
                else:
                    session.select([gid], add=True)
            elif gid or not mods.ctrl:
                session.select([gid] if gid else [], add=mods.ctrl)
            self.after_tool_input()
            return
        p = self.world_point(pos)
        if p is None:
            session.message("aponte para o modelo ou para o plano do pavimento", "recusa")
            return
        tool.move(p, mods)
        tool.press(p, mods, button)
        tool.release(p, mods)
        self.after_tool_input()

    def finish_window(self, pos: QPointF, mods: Mods) -> list[str]:
        """Segundo clique da janela no 3D: direita = inteiros, esquerda = os que tocam;
        Shift tira da seleção."""
        from brasbim.ui.scene3d import in_screen_rect

        start, self.window_start = self.window_start, None
        gids = in_screen_rect(self.scene, self.camera, self.width(), self.height(),
                              (start.x(), start.y()), (pos.x(), pos.y()),
                              crossing=pos.x() < start.x())
        session = self.ctx.session
        locked = display_layers_locked(session.doc)
        gids = [g for g in gids if g not in locked]
        if mods.shift:
            session.select(session.selection - set(gids))
        else:
            session.select(set(gids) - session.selection, add=True)
        self.after_tool_input()
        return gids

    def press_escape(self) -> None:
        """Esc cancela a janela em andamento antes de tudo (spec/ui 28 §3)."""
        if self.cancel_window():
            self.after_tool_input()
            return
        super().press_escape()

    def cancel_window(self) -> bool:
        if self.window_start is None:
            return False
        self.window_start = None
        self.update()
        return True

    def _paint_window(self) -> None:
        from PySide6.QtGui import QBrush, QColor, QPainter, QPen

        a, b = self.window_start, self.mouse_pos
        crossing = b.x() < a.x()
        color = QColor(theme.OK if crossing else theme.ACCENT)
        fill = QColor(color)
        fill.setAlpha(25)
        painter = QPainter(self)
        painter.setPen(QPen(color, 1, Qt.DashLine if crossing else Qt.SolidLine))
        painter.setBrush(QBrush(fill))
        painter.drawRect(QRectF(a, b).normalized())
        painter.end()

    def mouseDoubleClickEvent(self, event):
        tool = self.toolbox.active
        if event.button() == Qt.LeftButton and tool.name != "select":
            p = self.world_point(event.position())
            if p is not None:
                tool.double(p, self._mods(event))
                self.after_tool_input()

    def wheelEvent(self, event):
        camera = self.camera
        camera.distance = min(max(camera.distance * 0.85 ** (event.angleDelta().y() / 120),
                                  0.5), 5000.0)
        self._zooming.start()
        if self.selection_bar is not None:
            self.selection_bar.hide()
        self.update()

    # --- teclado -----------------------------------------------------------------------

    def event(self, event):
        if self.tool_event(event):
            return True
        if event.type() == QEvent.ToolTip:  # nome da vista da marca (spec/ui 40 §4)
            key = self.orientation_at(QPointF(event.pos()))
            if key is not None:
                QToolTip.showText(event.globalPos(), ORIENTATION_MARKS[key][2], self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if self.tool_key(event) or self.forward_text(event):
            return
        if event.key() == Qt.Key_Home:
            self.fit()
        else:
            super().keyPressEvent(event)


class AreaView3D(View3D):
    """Aba temporária "3D da área" (spec/ui 38 §4): só o que a área de seleção pega,
    recortado por ela, sem mudar a aba 3D principal. Refaz a cena quando a área, o
    pavimento ou o modelo mudam (o modelo avisa por ``refresh``)."""

    title = "3D da área"

    def __init__(self, source: Scene, toolbox: ToolBox, parent=None):
        super().__init__(Scene(), toolbox, parent)
        self.source = source  # cena do 3D principal, já com as camadas aplicadas
        self.area = None
        self.storey_id: str | None = None
        self.dirty = True

    def refresh(self) -> None:
        self.dirty = True
        self.update()

    def rebuild(self) -> None:
        """Cena da área atual; sem área (removida), fica a última."""
        session = self.ctx.session
        area = self.ctx.area or self.area
        storey_id = session.storey_id
        if area is None or (not self.dirty and area is self.area and (
                area.all_storeys or storey_id == self.storey_id)):
            return
        first = self.area is None
        self.area, self.storey_id, self.dirty = area, storey_id, False
        keep = None
        if not area.all_storeys:
            doc = session.doc

            def keep(gid):
                element = doc.find(gid)
                storey = storey_of(element) if element is not None else None
                return storey is not None and storey.GlobalId == storey_id

        self.scene = area_scene(self.source, area, keep)
        if first:
            self.fit()

    def paintGL(self):
        self.rebuild()
        super().paintGL()
