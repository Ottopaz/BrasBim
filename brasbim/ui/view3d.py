# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista 3D (``spec/ui/01-janela-e-ferramentas.md`` §4 e
``spec/ui/07-medidas-e-edicao-no-3d.md`` §3): órbita, deslocamento e aproximação; seleção
por clique; as mesmas ferramentas da planta, com o ponto dado no plano de trabalho.

Desenha as malhas de ``scene3d.Scene`` com OpenGL de função fixa (arrays no cliente, sem
recursos na placa), o que sobrevive à troca de janela-mãe. Câmera, raio e escolha por raio
ficam em ``scene3d``, sem Qt."""

from __future__ import annotations

import logging

import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brasbim.core import transform
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
        if button == Qt.MiddleButton:
            self._drag = ("pan", event.position())
        elif button in (Qt.LeftButton, Qt.RightButton):
            self._press = ("left" if button == Qt.LeftButton else "right", event.position())

    def mouseMoveEvent(self, event):
        self.ctx.input_view = self
        pos = self.mouse_pos = event.position()
        press = self._press
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
