# SPDX-License-Identifier: GPL-3.0-or-later
"""Vistas salvas na interface (``spec/ui/25-vistas-salvas.md``): o quadro de salvar, o
que se lê da janela (planta, 3D ou corte) para guardar, abrir a vista de novo na janela
e a imagem da vista 3D para a prancha."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
)

from brasbim.core import display_layers, storeys
from brasbim.core.drawings import saved_views, views
from brasbim.ui import theme

log = logging.getLogger(__name__)

MIME = "application/x-brasbim-vista-salva"
OPTION_ACTIONS = ("show_tags", "show_tag_size", "show_structure_tags", "show_object_tags",
                  "show_space_numbers", "show_weights", "show_view_symbols")


# --- ler a janela ----------------------------------------------------------------------


def current_kind(window) -> tuple[str, object] | None:
    """("plan" | "3d" | "section", widget) da vista à frente; ``None`` se a aba não é de
    vista (prancha, tabela)."""
    from brasbim.ui.section_view import SectionView

    if window.split:
        return ("3d", window.view3d) if window.view3d.hasFocus() else ("plan", window.plan)
    widget = window.tabs.currentWidget()
    if widget is window.plan:
        return "plan", widget
    if widget is window.view3d:
        return "3d", widget
    if isinstance(widget, SectionView):
        return "section", widget
    return None


def capture(window, crop: bool = False) -> tuple[str, dict, str] | None:
    """(tipo, campos do estado, nome sugerido) do que está na tela."""
    found = current_kind(window)
    if found is None:
        return None
    kind, widget = found
    session = window.session
    doc = session.doc
    layers = display_layers.states_of(doc, session.display)
    pen_table = window.window_pen_table()  # tabela de penas da janela (spec/ui 27 §4)
    if kind == "plan":
        storey = session.storey
        if storey is None:
            return None
        options = {"detail": window.ctx.detail, "show_above": window.ctx.show_above}
        options.update({name: bool(getattr(window.plan, name)) for name in OPTION_ACTIONS})
        fields = {"storey": storey.GlobalId, "scale": storeys.scale(storey),
                  "layers": layers, "options": options, "pens": pen_table}
        if crop:
            a = window.plan.to_world(QPointF(0, widget.height()))
            b = window.plan.to_world(QPointF(widget.width(), 0))
            fields["crop"] = [round(a[0], 3), round(a[1], 3), round(b[0], 3), round(b[1], 3)]
        name = saved_views.suggest_name(doc, "plan", storey.Name or "", fields["scale"])
        return kind, fields, name
    if kind == "3d":
        camera = widget.camera
        fields = {"layers": layers, "camera": {
            "target": [round(float(v), 4) for v in camera.target],
            "distance": round(float(camera.distance), 4), "yaw": round(float(camera.yaw), 6),
            "pitch": round(float(camera.pitch), 6),
            "aspect": round(widget.width() / max(widget.height(), 1), 4)}}
        return kind, fields, saved_views.suggest_name(doc, "3d")
    view = widget.view
    if view is None:
        return None
    state = views.read_state(view)
    scale = widget.scale_override or state["scale"]
    fields = {"view": view.GlobalId, "scale": scale, "layers": layers, "pens": pen_table,
              "options": {"show_weights": bool(widget.show_weights)}}
    return kind, fields, saved_views.suggest_name(doc, "section", state["name"] or "", scale)


def summary(window, kind: str, fields: dict) -> str:
    """Resumo do que a vista guarda, para o quadro de salvar (§3)."""
    doc = window.session.doc
    comb = display_layers.matching_combination(doc, window.session.display)
    layers = f"camadas: {comb['name']}" if comb else "camadas: como estão na janela"
    if kind == "plan":
        storey = doc.find(fields["storey"])
        return f"Planta de {storey.Name} · 1:{fields['scale']} · {layers}"
    if kind == "3d":
        return f"Câmera do 3D · {layers}"
    view = doc.find(fields["view"])
    return f"{views.read_state(view)['name']} · 1:{fields['scale']} · {layers}"


class SaveViewDialog(QDialog):
    """Nome da vista, resumo e, na planta, "Recortar pela área visível" (§3)."""

    def __init__(self, name: str, text: str, can_crop: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Salvar vista")
        layout = QFormLayout(self)
        self.name = QLineEdit(name)
        self.name.selectAll()
        layout.addRow("Nome", self.name)
        info = QLabel(text)
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {theme.INK_SOFT};")
        layout.addRow(info)
        self.crop = QCheckBox("Recortar pela área visível")
        self.crop.setToolTip("Na prancha, só o que está na tela agora")
        self.crop.setVisible(can_crop)
        layout.addRow(self.crop)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Salvar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


# --- lista arrastável -----------------------------------------------------------------


class SavedViewList(QListWidget):
    """Lista do painel Projeto; arrastar um item leva o GlobalId para a prancha (§5)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)

    def mimeData(self, items):
        data = QMimeData()
        if items:
            data.setData(MIME, items[0].data(Qt.UserRole).encode())
        return data

    def mimeTypes(self):
        return [MIME]


# --- imagem da vista 3D (§5) ------------------------------------------------------------

_context: tuple | None = None  # (contexto, superfície), criados na primeira imagem
scene_provider = None  # posto pela janela: devolve a Scene já carregada do documento


def _gl_context():
    global _context
    if _context is None:
        fmt = QSurfaceFormat.defaultFormat()
        fmt.setProfile(QSurfaceFormat.CompatibilityProfile)
        surface = QOffscreenSurface()
        surface.setFormat(fmt)
        surface.create()
        context = QOpenGLContext()
        context.setFormat(fmt)
        if not context.create():
            raise RuntimeError("sem contexto OpenGL")
        _context = (context, surface)
    return _context


def _scene_for(doc, layers):
    from brasbim.ui.scene3d import Scene

    scene = scene_provider() if scene_provider is not None else None
    if scene is None or scene.doc is not doc:
        scene = Scene()
        scene.load(doc.ifc, doc)
    every = {**scene.meshes, **scene._hidden}
    if layers is None:
        hidden = display_layers.hidden_ids(doc)
    else:
        with display_layers.using(doc, display_layers.display_of(layers)):
            hidden = display_layers.hidden_ids(doc)
    return SimpleNamespace(meshes={g: m for g, m in every.items() if g not in hidden})


def render_3d(doc, state: dict, width: int, height: int) -> QImage | None:
    """Imagem da vista 3D salva com ``width`` × ``height`` pixels, ou ``None`` se não há
    OpenGL."""
    from brasbim.ui import view3d
    from brasbim.ui.scene3d import Camera

    if view3d.GL is None:
        return None
    GL = view3d.GL
    width, height = max(16, int(width)), max(16, int(height))
    try:
        context, surface = _gl_context()
        previous = QOpenGLContext.currentContext()
        previous_surface = previous.surface() if previous is not None else None
        if not context.makeCurrent(surface):
            return None
        try:
            fbo_format = QOpenGLFramebufferObjectFormat()
            fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
            fbo_format.setSamples(4)
            fbo = QOpenGLFramebufferObject(width, height, fbo_format)
            fbo.bind()
            GL.glViewport(0, 0, width, height)
            GL.glClearColor(*theme.rgbf(theme.VIEW3D_BACKGROUND), 1.0)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(1.0, 1.0)
            camera = Camera()
            cam = state["camera"]
            camera.target = np.array(cam["target"], dtype=float)
            camera.distance, camera.yaw, camera.pitch = (cam["distance"], cam["yaw"],
                                                         cam["pitch"])
            view3d.draw_scene(_scene_for(doc, state.get("layers")), camera, width / height)
            GL.glFinish()
            fbo.release()
            image = fbo.toImage()
        finally:
            context.doneCurrent()
            if previous is not None and previous_surface is not None:
                previous.makeCurrent(previous_surface)
        return image
    except (RuntimeError, view3d.GLError) as e:
        log.warning("imagem do 3D indisponível: %s", e)
        return None


def placeholder(width: int, height: int) -> QImage:
    image = QImage(max(1, width), max(1, height), QImage.Format_RGB32)
    image.fill(QColor(theme.FRAME))
    return image
