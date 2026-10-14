# SPDX-License-Identifier: GPL-3.0-or-later
"""Vista 3D (``spec/ui/01-janela-e-ferramentas.md`` §4): só visualização, com órbita,
arrasto e aproximação. Desenha as malhas de ``scene3d.Scene`` com OpenGL de função fixa
(arrays no cliente, sem recursos na placa), o que sobrevive à troca de janela-mãe."""

from __future__ import annotations

import logging
import math

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brasbim.ui.scene3d import Scene

log = logging.getLogger(__name__)

try:
    from OpenGL import GL
    from OpenGL.error import Error as GLError
except ImportError:  # PyOpenGL ausente: a vista não desenha
    GL = None
    GLError = RuntimeError

_SELECT = np.array([0.11, 0.44, 0.84], dtype=np.float32)
_BACKGROUND = (0.93, 0.94, 0.95)


def _perspective(fovy: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1 / math.tan(math.radians(fovy) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def _look_at(eye, target, up) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


class View3D(QOpenGLWidget):
    def __init__(self, scene: Scene, selection_provider, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.selection = selection_provider  # função que devolve o conjunto selecionado
        self.target = np.zeros(3)
        self.distance = 20.0
        self.yaw, self.pitch = math.radians(-60), math.radians(30)
        self._drag: tuple[str, QPointF] | None = None
        self.failed = GL is None
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)

    def fit(self) -> None:
        bounds = self.scene.bounds()
        if bounds is not None:
            low, high = bounds
            self.target = (low + high) / 2
            self.distance = max(float(np.linalg.norm(high - low)) * 1.6, 2.0)
        self.update()

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

    def _eye(self) -> np.ndarray:
        cp = math.cos(self.pitch)
        direction = np.array([cp * math.cos(self.yaw), cp * math.sin(self.yaw),
                              math.sin(self.pitch)])
        return self.target + self.distance * direction

    def paintGL(self):
        if self.failed:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        aspect = self.width() / max(self.height(), 1)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixd(_perspective(45, aspect, self.distance / 200,
                                      self.distance * 20).T.flatten())
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixd(_look_at(self._eye(), self.target, np.array([0, 0, 1.0])).T.flatten())
        selected = self.selection()
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
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

    # --- navegação ---------------------------------------------------------------------

    def mousePressEvent(self, event):
        kind = {Qt.LeftButton: "orbit", Qt.MiddleButton: "pan"}.get(event.button())
        if kind:
            self._drag = (kind, event.position())

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        kind, last = self._drag
        delta = event.position() - last
        self._drag = (kind, event.position())
        if kind == "orbit":
            self.yaw -= delta.x() * 0.01
            self.pitch = min(max(self.pitch + delta.y() * 0.01, -1.5), 1.5)
        else:
            eye = self._eye()
            forward = self.target - eye
            forward /= np.linalg.norm(forward)
            right = np.cross(forward, [0, 0, 1.0])
            right /= max(np.linalg.norm(right), 1e-9)
            up = np.cross(right, forward)
            k = self.distance / max(self.height(), 1)
            self.target = self.target - right * delta.x() * k + up * delta.y() * k
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None

    def wheelEvent(self, event):
        self.distance = min(max(self.distance * 0.85 ** (event.angleDelta().y() / 120), 0.5),
                            5000.0)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Home:
            self.fit()
        else:
            super().keyPressEvent(event)
