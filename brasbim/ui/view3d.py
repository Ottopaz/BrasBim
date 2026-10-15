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
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brasbim.core import snap, transform
from brasbim.core.document import OpError
from brasbim.ui.handles3d import PLANAR, WallHandle3D, wall_handles
from brasbim.ui.measure_box import ToolInput
from brasbim.ui.scene3d import Camera, Scene, affine_of, ray_plane, transformed
from brasbim.ui.tools import Mods, ToolBox

log = logging.getLogger(__name__)

try:
    from OpenGL import GL
    from OpenGL.error import Error as GLError
except ImportError:  # PyOpenGL ausente: a vista não desenha
    GL = None
    GLError = RuntimeError

_SELECT = np.array([0.11, 0.44, 0.84], dtype=np.float32)
_BACKGROUND = (0.93, 0.94, 0.95)
_MARK_COLOR = {"invalid": (0.83, 0.23, 0.18), "guide": (0.45, 0.60, 0.80)}
_PREVIEW = (0.11, 0.44, 0.84)
CLICK_PX = 4  # o clique só vale se o cursor andar menos que isto (§3.1)
HANDLE_PX = 8  # raio de captura das alças na tela (spec/ui 08 §3)
SNAP_PX = 10
TRANSFORM_TOOLS = ("move", "copy", "rotate", "mirror")


def storey_of(element):
    """Pavimento que contém o elemento (a porta, pelo da parede se preciso)."""
    container = ifcopenshell.util.element.get_container(element)
    if container is None and element.is_a("IfcDoor"):
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
        self.failed = GL is None
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
        """Seleção mais as portas das paredes selecionadas (elas vão junto)."""
        doc, selection = self.ctx.session.doc, self.selection
        out = set(selection)
        for gid in self.scene.meshes:
            element = doc.find(gid)
            if element is not None and element.is_a("IfcDoor") and gid not in selection:
                host = transform.host_wall(element)
                if host is not None and host.GlobalId in selection:
                    out.add(gid)
        return out

    def paintGL(self):
        if self.failed:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        aspect = self.width() / max(self.height(), 1)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixd(self.camera.projection(aspect).T.flatten())
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixd(self.camera.view().T.flatten())
        selected = self.selection
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        for gid, mesh in self.scene.meshes.items():
            colors = mesh.colors
            if gid in selected:
                colors = (colors * 0.4 + _SELECT * 0.6).astype(np.float32)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, mesh.vertices)
            GL.glColorPointer(3, GL.GL_FLOAT, 0, colors)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(mesh.vertices))
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glColor3f(0.25, 0.25, 0.25)
        for mesh in self.scene.meshes.values():
            if len(mesh.edges):
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, mesh.edges)
                GL.glDrawArrays(GL.GL_LINES, 0, len(mesh.edges))
        self._paint_tool()
        self._paint_handles()
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        if self.selection_bar is not None:
            self.selection_bar.place()

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
        for mark in tool.preview():
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

    def handles(self) -> list[tuple[str, tuple[float, float, float]]]:
        wall = self.selected_wall()
        if wall is None:
            return []
        try:
            return wall_handles(self.ctx.session.doc, wall)
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
        tool.drag3d = WallHandle3D(self.ctx, self.selected_wall(), kind)
        tool.drag3d.anchor = np.array(dict(self.handles())[kind])  # o plano passa pela alça
        tool.drag3d.update()
        self.after_tool_input()

    def _feed_handle(self, pos: QPointF, mods: Mods) -> None:
        """Leva a alça presa ao cursor: ponto no plano (pontas, face) ou cota (topo, base)."""
        h = self.toolbox.active.drag3d
        origin, direction = self.ray(pos)
        if h.kind in PLANAR:
            z = h.zb + (h.h / 2 if h.kind == "face" else 0.0)
            hit = ray_plane(origin, direction, z)
            if hit is None:
                return
            self.ctx.tol = SNAP_PX * self.camera.pixel_size(hit, self.height())
            p = (float(hit[0]), float(hit[1]))
            if h.kind == "face":
                p = self.ctx.snap(p, Mods(alt=mods.alt)).point
            else:
                fixed = h.wall.path.end if h.kind == "start" else h.wall.path.start
                p = self.ctx.snap(p, mods, fixed).point
            h.update(point=p, ctrl=mods.ctrl)
        else:
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
            h.update(z=h.snap_z(float(hit[2]), mods.alt, tol), ctrl=mods.ctrl)
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
            return
        p = self.world_point(pos)
        if p is None:
            return
        self.cursor_moved.emit(*p)
        tool.move(p, mods)
        self.after_tool_input()

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
        if press is not None and press[0] == "left" and self._drag is None \
                and (pos - press[1]).manhattanLength() >= CLICK_PX:
            self._drag = ("orbit", press[1])
            self._press = None
        if self._drag is None:
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
            return
        if press is None:
            return
        button, at = press
        self.click(at, button, self._mods(event), event.globalPosition().toPoint())

    def click(self, pos: QPointF, button: str, mods: Mods, global_pos=None) -> None:
        """Clique (sem arrastar) na posição da tela (§3.1)."""
        tool = self.toolbox.active
        session = self.ctx.session
        if tool.name == "select":
            gid = self.pick(pos)
            if button == "right":
                if gid and gid not in session.selection:
                    session.select([gid], add=mods.ctrl)
                self.context_requested.emit(gid, global_pos)
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
        self.update()

    # --- teclado -----------------------------------------------------------------------

    def event(self, event):
        if self.tool_event(event):
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        if self.tool_key(event):
            return
        if event.key() == Qt.Key_Home:
            self.fit()
        else:
            super().keyPressEvent(event)
