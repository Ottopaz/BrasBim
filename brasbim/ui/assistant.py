# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Assistente (``spec/ui/16-assistente.md``): o pedido escrito no BrasBim vai para
uma IA instalada no PC, que desenha no modelo aberto pelas ferramentas do assistente.

Caminho: o painel abre o servidor MCP local (``core.assistant.mcp``) e inicia o
conector (hoje, o Claude Code em modo não interativo), que recebe o pedido e chama as
ferramentas. Cada chamada chega numa thread do servidor e é executada na thread da
interface (``_MainThread``), por ``Session.history.commit``: a planta e o 3D mudam na
hora. No fim, as transações do pedido viram um passo só de desfazer.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell.util.element
from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QObject,
    QPointF,
    QProcess,
    QRectF,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import plan as plan_mod
from brasbim.core.annotations import spaces
from brasbim.core.assistant import mcp
from brasbim.core.assistant.tools import (
    Context,
    Registry,
    Tool,
    default_registry,
    find_object_type,
    selection_note,
)
from brasbim.core.freeform import elements as freeform
from brasbim.core.objects import elements as objects
from brasbim.ui import theme
from brasbim.ui.icons import icon

# Imagens anexadas ao pedido (spec/ui 54 §2)
MAX_IMAGES = 4
MAX_IMAGE_SIDE = 1568  # px no lado maior; acima disso a imagem é reduzida antes de ir
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
ONLY_IMAGE_TEXT = "Veja a imagem anexada."
THUMB = 48

# O que fica selecionado ao fim do pedido (spec/ui 16 §5).
_SELECTABLE = ("IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcColumn", "IfcBeam", "IfcRoof",
               "IfcSpace")

# --- execução na thread da interface ----------------------------------------------------


class _MainThread(QObject):
    """Roda funções na thread da interface e espera o resultado (chamado do servidor)."""

    _job = Signal(object)

    def __init__(self):
        super().__init__()
        self._job.connect(self._run, Qt.QueuedConnection)

    def _run(self, job) -> None:
        fn, box, done = job
        try:
            box["value"] = fn()
        except Exception as e:  # noqa: BLE001 - volta para a IA como erro
            box["error"] = e
        done.set()

    def call(self, fn, timeout: float = 120.0):
        if QThread.currentThread() is self.thread():
            return fn()
        box, done = {}, threading.Event()
        self._job.emit((fn, box, done))
        if not done.wait(timeout):
            raise TimeoutError("o BrasBim não respondeu a tempo")
        if "error" in box:
            raise box["error"]
        return box["value"]


# --- imagem da planta ---------------------------------------------------------------------


def plan_image(doc, storey, size: int = 1000) -> tuple[bytes, dict]:
    """PNG da planta do pavimento com grade de 1 m e as coordenadas nas bordas (para a
    IA se localizar); devolve também a escala."""
    from brasbim.ui.paper import _PlanPainter

    plan = plan_mod.storey_plan(doc, storey)
    bounds = plan.bounds() or (0.0, 0.0, 10.0, 10.0)
    x0, y0, x1, y1 = bounds
    x0, y0, x1, y1 = x0 - 1.0, y0 - 1.0, x1 + 1.0, y1 + 1.0
    margin = 40
    scale = (size - 2 * margin) / max(x1 - x0, y1 - y0)
    w = round((x1 - x0) * scale) + 2 * margin
    h = round((y1 - y0) * scale) + 2 * margin
    origin = QPointF(margin - x0 * scale, margin + y1 * scale)
    image = QImage(w, h, QImage.Format_RGB32)
    image.fill(QColor(theme.FIELD))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont(theme.font())
    font.setPixelSize(12)
    painter.setFont(font)
    for i in range(int(x0), int(x1) + 1):
        sx = origin.x() + i * scale
        painter.setPen(QPen(QColor(theme.GRID_MAJOR if i % 5 == 0 else theme.GRID), 1))
        painter.drawLine(QPointF(sx, margin), QPointF(sx, h - margin))
        painter.setPen(QColor(theme.INK_SOFT))
        painter.drawText(QPointF(sx - 4, h - margin + 16), str(i))
    for j in range(int(y0), int(y1) + 1):
        sy = origin.y() - j * scale
        painter.setPen(QPen(QColor(theme.GRID_MAJOR if j % 5 == 0 else theme.GRID), 1))
        painter.drawLine(QPointF(margin, sy), QPointF(w - margin, sy))
        painter.setPen(QColor(theme.INK_SOFT))
        painter.drawText(QPointF(8, sy + 4), str(j))
    drawer = _PlanPainter(None, plan, scale, origin, 1.0)
    drawer.show_space_numbers = False
    drawer.paint(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data), {"pixels_por_metro": round(scale, 2), "x": [x0, x1], "y": [y0, y1]}


def view_plan_tool(session) -> Tool:
    def fn(ctx: Context, args: dict):
        from brasbim.core.assistant.tools import _storey

        storey = _storey(ctx, args)
        png, info = plan_image(ctx.doc, storey, int(args.get("size") or 1000))
        return [{"type": "image", "data": base64.b64encode(png).decode("ascii"),
                 "mimeType": "image/png"},
                {"type": "text", "text": json.dumps(
                    {"pavimento": storey.Name, **info,
                     "nota": "grade de 1 m; números nas bordas = coordenadas em metros"},
                    ensure_ascii=False)}]

    return Tool("view_plan", "Olhando a planta",
                "Imagem PNG da planta do pavimento como está na tela, com grade de 1 m e as "
                "coordenadas nas bordas. Use para conferir o desenho.",
                {"type": "object", "properties": {
                    "storey": {"type": "string"}, "size": {"type": "integer"}}},
                fn, changes=False)


# --- imagem do objeto (spec/ui 54 §3.3) -----------------------------------------------------

# Vistas da prévia: (nome, azimute, elevação) de ``object_preview.paint_3d``
OBJECT_VIEWS = (("Frente", 0.0, 0.0), ("Lado direito", -90.0, 0.0),
                ("Topo (a frente fica embaixo)", 0.0, 90.0), ("Perspectiva", -35.0, 30.0))


def object_image(state: dict, resolver=None, cell: int = 420) -> bytes:
    """PNG com as quatro vistas de um tipo de objeto (estado de ``types.read``), para a IA
    comparar com a foto."""
    from brasbim.core.objects import definition as od
    from brasbim.core.objects import mesh as object_mesh

    values = od.evaluate(state["definition"], state.get("values") or {},
                         state.get("defaults") or {})
    return views_image(object_mesh.object_mesh(state["definition"], values, resolver), cell)


def freeform_triangles(state: dict) -> list:
    """Triângulos de uma forma livre para a prévia: ``(triângulo, material, grupo)``. Com
    receita, um grupo por forma (o contorno de cada uma aparece); sem ela, um por parte."""
    from brasbim.core.freeform import mesh as fm
    from brasbim.core.freeform import shapes as fs

    groups = []
    if state.get("recipe"):
        for i, shape in enumerate(state["recipe"]):
            vertices, faces = fs.shape_mesh(shape, i, fs.DETAILS[1])
            groups.append((vertices, faces, str(shape.get("material") or "") or None))
    else:
        groups = [(*fm.arrays(part), part.get("material")) for part in state["parts"]]
    out = []
    for group, (vertices, faces, material) in enumerate(groups):
        for a, b, c in vertices[faces].tolist():
            out.append(((tuple(a), tuple(b), tuple(c)), material, group))
    return out


def views_image(tris: list, cell: int = 420) -> bytes:
    """PNG com as quatro vistas de uma lista de triângulos ``(triângulo, material,
    grupo)``."""
    from brasbim.ui import mesh_render

    points, colors, groups = mesh_render.arrays(tris)
    paper = QColor(theme.PAPER)
    image = QImage(2 * cell, 2 * cell, QImage.Format_RGB32)
    image.fill(paper)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont(theme.font())
    font.setPixelSize(15)
    painter.setFont(font)
    for i, (name, azimuth, elevation) in enumerate(OBJECT_VIEWS):
        x, y = (i % 2) * cell, (i // 2) * cell
        # desenhada uma vez e meia maior e reduzida: as linhas saem suaves
        big = mesh_render.render(points, colors, groups, azimuth, elevation,
                                 3 * (cell - 8) // 2, 3 * (cell - 44) // 2,
                                 (paper.red(), paper.green(), paper.blue()))
        painter.drawImage(x + 4, y + 4, mesh_render.to_qimage(big).scaled(
            cell - 8, cell - 44, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        painter.setPen(QPen(QColor(theme.GRID_MAJOR), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(x, y, cell - 1, cell - 1)
        painter.setPen(QColor(theme.INK))
        painter.drawText(QRectF(x, y + cell - 34, cell, 26), Qt.AlignCenter, name)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def _object_state(doc, name: str) -> dict:
    """Estado do tipo pelo nome: do projeto ou, sem carregar nada, da biblioteca."""
    from brasbim.core.assistant.tools import _library
    from brasbim.core.document import OpError
    from brasbim.core.objects import types as ot

    try:
        return ot.read(find_object_type(doc, name))
    except OpError:
        wanted = name.strip().casefold()
        for entry in _library().entries() if wanted else ():
            if wanted in (entry.name.casefold(), entry.definition["name"].casefold()):
                return entry.state()
        raise OpError(f"objeto {name!r} não está no projeto nem na biblioteca (veja "
                      "list_objects)") from None


def view_object_tool(session) -> Tool:
    def fn(ctx: Context, args: dict):
        from brasbim.core.assistant.tools import _box_of
        from brasbim.ui.object_widgets import resolver_for

        size = int(args.get("size") or 420)
        if args.get("id"):  # forma livre (forma-livre.md §4.1)
            from brasbim.core.document import OpError
            from brasbim.core.freeform import elements as ff

            element = ctx.doc.find(str(args["id"]))
            if not ff.is_freeform(element):
                raise OpError(f"{args['id']} não é forma livre (para objetos, use 'type')")
            state = ff.read_state(ctx.doc, element)
            png, box = views_image(freeform_triangles(state), size), ff.box_of(state)
        else:
            state = _object_state(ctx.doc, str(args.get("type") or ""))
            png = object_image(state, resolver_for(ctx.doc), size)
            box = _box_of(state["definition"], state["values"], state["defaults"])
        return [{"type": "image", "data": base64.b64encode(png).decode("ascii"),
                 "mimeType": "image/png"},
                {"type": "text", "text": json.dumps(
                    {"tipo": state["name"], "caixa": box,
                     "nota": "quatro vistas: frente, lado direito, topo e perspectiva; "
                             "cada peça tem o contorno marcado; medidas em metros"},
                    ensure_ascii=False)}]

    return Tool("view_object", "Olhando o objeto",
                "Imagem PNG de um objeto do projeto ou da biblioteca ('type' = nome do tipo "
                "ou do objeto; o da biblioteca não precisa ser inserido para ser visto) ou "
                "de uma forma livre ('id'), em quatro vistas (frente, lado direito, topo, "
                "perspectiva), com a caixa que o envolve em texto. Use para comparar com a "
                "foto do usuário e corrigir.",
                {"type": "object", "properties": {
                    "type": {"type": "string"}, "id": {"type": "string"},
                    "size": {"type": "integer"}}},
                fn, changes=False)


# --- imagens anexadas (spec/ui 54 §2) -------------------------------------------------------


@dataclass
class Attachment:
    """Imagem pronta para ir com o pedido: já reduzida e regravada."""

    data: bytes
    media_type: str
    thumb: QPixmap
    name: str = ""


def prepare_image(image: QImage) -> tuple[bytes, str]:
    """Reduz a imagem para caber em ``MAX_IMAGE_SIDE`` e a regrava: PNG se tem
    transparência, JPEG de qualidade 85 se não tem."""
    if max(image.width(), image.height()) > MAX_IMAGE_SIDE:
        image = image.scaled(MAX_IMAGE_SIDE, MAX_IMAGE_SIDE, Qt.KeepAspectRatio,
                             Qt.SmoothTransformation)
    alpha = image.hasAlphaChannel()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    if alpha:
        image.save(buffer, "PNG")
    else:
        image.convertToFormat(QImage.Format_RGB32).save(buffer, "JPEG", 85)
    return bytes(data), "image/png" if alpha else "image/jpeg"


def request_message(text: str, attachments=()) -> str:
    """O pedido como uma linha de ``stream-json``: as imagens e depois o texto."""
    content = [{"type": "image", "source": {
        "type": "base64", "media_type": a.media_type,
        "data": base64.b64encode(a.data).decode("ascii")}} for a in attachments]
    content.append({"type": "text", "text": text})
    return json.dumps({"type": "user", "message": {"role": "user", "content": content}},
                      ensure_ascii=False)


def _image_paths(mime) -> list[str]:
    """Arquivos locais de imagem numa colagem ou num arrasto."""
    return [u.toLocalFile() for u in mime.urls()
            if u.isLocalFile() and u.toLocalFile().lower().endswith(IMAGE_SUFFIXES)] \
        if mime.hasUrls() else []


class PromptEdit(QPlainTextEdit):
    """Campo do pedido: colar ou soltar uma imagem a anexa em vez de escrever texto."""

    def __init__(self, take_mime, parent=None):
        super().__init__(parent)
        self._take_mime = take_mime

    def canInsertFromMimeData(self, source) -> bool:
        return bool(_image_paths(source)) or source.hasImage() \
            or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source) -> None:
        if not self._take_mime(source):
            super().insertFromMimeData(source)


# --- conectores ---------------------------------------------------------------------------


@dataclass
class ClaudeCode:
    """Claude Code instalado (``claude``), em modo não interativo (spec/ui 16 §3.2): só as
    ferramentas do BrasBim, nenhuma do próprio Claude Code (terminal, arquivos)."""

    name: str = "Claude Code"
    program: str | None = field(default_factory=lambda: shutil.which("claude"))

    @property
    def available(self) -> bool:
        return self.program is not None

    def arguments(self, config_path: str, resume: str | None = None) -> list[str]:
        """``resume``: código da conversa a continuar (memória, spec/ui 16 §2.1)."""
        args = ["-p", "--input-format", "stream-json",  # pedido com imagens (spec/ui 54)
                "--output-format", "stream-json", "--verbose",
                "--tools", "", "--strict-mcp-config", "--mcp-config", config_path,
                "--allowedTools", f"mcp__{mcp.SERVER_NAME}",
                "--append-system-prompt", mcp.INSTRUCTIONS]
        if resume:
            args += ["--resume", resume]
        return args


def _short(text: str, size: int = 40) -> str:
    """Começo do pedido para o nome do passo de desfazer: corta numa palavra, sem "…"
    (spec/ui 40 §2)."""
    text = " ".join(text.split())
    if len(text) <= size:
        return text
    cut = text[:size].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:")


# --- painel -------------------------------------------------------------------------------


class AssistantPanel(QWidget):
    """Pedido, botão Enviar/Parar e o andamento (o que a IA faz, a resposta final)."""

    finished = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.registry: Registry = default_registry()
        self.registry.add(view_plan_tool(session))
        self.registry.add(view_object_tool(session))
        self.connector = ClaudeCode()
        self.server: mcp.Server | None = None
        self.process: QProcess | None = None
        self._main = _MainThread()
        self._ours: list = []  # transações do pedido em curso
        self._buffer = b""
        self._config: str | None = None
        self._prompt = ""
        self.conversation: str | None = None  # código da conversa (memória entre pedidos)
        self._resumed = False
        session.listeners.append(self._on_session)

        self.log = QListWidget()
        self.log.setWordWrap(True)
        self.prompt = PromptEdit(self.take_mime)
        self.prompt.setPlaceholderText(
            "Peça o que desenhar. Ex.: casa térrea de 3 quartos, sala e cozinha "
            "integradas, banheiro e área de serviço, uns 100 m².\n"
            "Ou anexe a foto de um móvel ou aparelho, diga as medidas e peça para criar "
            "o objeto.")
        # Imagens anexadas (spec/ui 54 §2): faixa de miniaturas, cada uma com um ×
        self.attachments: list[Attachment] = []
        self.remove_buttons: list[QToolButton] = []
        self.attach_strip = QWidget()
        strip = QHBoxLayout(self.attach_strip)
        strip.setContentsMargins(0, 0, 0, 0)
        strip.setSpacing(4)
        self.attach_strip.hide()
        self.attach_button = QToolButton()
        self.attach_button.setIcon(icon("image"))
        self.attach_button.setAutoRaise(True)
        self.attach_button.setToolTip("Anexar imagem (é enviada à IA junto com o pedido). "
                                      "Também dá para colar (Ctrl+V) ou arrastar para cá")
        self.attach_button.clicked.connect(lambda _=False: self.choose_images())
        self.setAcceptDrops(True)
        self.prompt.setMaximumHeight(110)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send)
        self.stop_button = QPushButton("Parar")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        self.new_button = QPushButton("Nova conversa")
        self.new_button.setToolTip("Esquece os pedidos anteriores; o modelo continua igual")
        self.new_button.clicked.connect(self.new_conversation)
        self.new_button.setEnabled(False)
        self.status = QLabel()
        self.status.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.addWidget(self.status, 1)
        buttons.addWidget(self.attach_button)
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.send_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.log, 1)
        layout.addWidget(self.attach_strip)
        layout.addWidget(self.prompt)
        layout.addLayout(buttons)
        self._idle_status()

    # --- estado ----------------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self.process is not None

    def _idle_status(self) -> None:
        if not self.connector.available:
            self.status.setText(f"{self.connector.name} não encontrado neste PC")
        elif self.conversation:
            self.status.setText(f"IA: {self.connector.name} · continuando a conversa")
        else:
            self.status.setText(f"IA: {self.connector.name}")
        self.send_button.setEnabled(self.connector.available)
        self.new_button.setEnabled(self.conversation is not None)

    def new_conversation(self) -> None:
        """Esquece a conversa: o próximo pedido começa do zero (o modelo fica)."""
        if self.running:
            return
        if self.conversation is not None:
            self.conversation = None
            self._add("— nova conversa —", "info")
        self._idle_status()

    def _on_session(self, event: str) -> None:
        if event == "document":  # outro projeto: a conversa não passa de um para outro
            self.stop()
            self.conversation = None
            self.log.clear()
            self.attachments = []
            self._refresh_attachments()
            self._idle_status()

    # --- imagens anexadas (spec/ui 54 §2) ---------------------------------------------

    def attach_image(self, image: QImage, name: str = "") -> bool:
        """Anexa uma imagem já aberta (colada, solta ou lida do arquivo)."""
        if image.isNull():
            self._add(f"não foi possível abrir {name or 'a imagem'}", "erro")
            return False
        if len(self.attachments) >= MAX_IMAGES:
            self._add(f"no máximo {MAX_IMAGES} imagens por pedido", "erro")
            return False
        data, media_type = prepare_image(image)
        thumb = QPixmap.fromImage(image.scaled(THUMB, THUMB, Qt.KeepAspectRatio,
                                               Qt.SmoothTransformation))
        self.attachments.append(Attachment(data, media_type, thumb, name))
        self._refresh_attachments()
        return True

    def attach_files(self, paths) -> int:
        """Anexa arquivos de imagem; devolve quantos entraram."""
        count = 0
        for path in paths:
            name = Path(path).name
            if not str(path).lower().endswith(IMAGE_SUFFIXES):
                self._add(f"{name} não é imagem PNG, JPEG ou WebP", "erro")
                continue
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)  # foto de celular: respeita a rotação gravada
            count += self.attach_image(reader.read(), name)
        return count

    def choose_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Anexar imagem", "", "Imagens (*.png *.jpg *.jpeg *.webp)")
        self.attach_files(paths)

    def remove_attachment(self, index: int) -> None:
        if 0 <= index < len(self.attachments):
            del self.attachments[index]
            self._refresh_attachments()

    def take_mime(self, mime) -> bool:
        """Imagem colada ou solta: anexa e devolve ``True``; outra coisa, ``False``."""
        paths = _image_paths(mime)
        if paths:
            self.attach_files(paths)
            return True
        if mime.hasImage():
            self.attach_image(QImage(mime.imageData()), "a imagem colada")
            return True
        return False

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if _image_paths(mime) or mime.hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if self.take_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _refresh_attachments(self) -> None:
        layout = self.attach_strip.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.remove_buttons = []
        for i, attachment in enumerate(self.attachments):
            picture = QLabel()
            picture.setPixmap(attachment.thumb)
            picture.setFixedSize(THUMB, THUMB)
            picture.setAlignment(Qt.AlignCenter)
            picture.setToolTip(attachment.name)
            remove = QToolButton()
            remove.setText("×")
            remove.setAutoRaise(True)
            remove.setToolTip("Tirar esta imagem")
            remove.clicked.connect(lambda _=False, i=i: self.remove_attachment(i))
            self.remove_buttons.append(remove)
            layout.addWidget(picture)
            layout.addWidget(remove, 0, Qt.AlignTop)
        layout.addStretch(1)
        self.attach_strip.setVisible(bool(self.attachments))

    def _add_images(self, attachments) -> None:
        """Miniaturas do pedido enviado, numa linha do andamento."""
        strip = QPixmap((THUMB + 4) * len(attachments), THUMB)
        strip.fill(Qt.transparent)
        painter = QPainter(strip)
        for i, attachment in enumerate(attachments):
            thumb = attachment.thumb
            painter.drawPixmap(i * (THUMB + 4) + (THUMB - thumb.width()) // 2,
                               (THUMB - thumb.height()) // 2, thumb)
        painter.end()
        item = QListWidgetItem()
        item.setData(Qt.DecorationRole, strip)
        self.log.addItem(item)
        self.log.scrollToBottom()

    def _add(self, text: str, level: str = "info") -> None:
        item = QListWidgetItem(text)
        color = {"erro": theme.ERROR, "ia": theme.INK, "ferramenta": theme.INK_SOFT,
                 "info": theme.INK_FAINT, "pedido": theme.ACCENT}[level]
        item.setForeground(QColor(color))
        if level in ("pedido", "ia"):
            font = theme.font()
            font.setBold(level == "pedido")
            item.setFont(font)
        self.log.addItem(item)
        self.log.scrollToBottom()

    # --- servidor e ferramentas ------------------------------------------------------

    def ensure_server(self) -> mcp.Server:
        if self.server is None:
            handler = mcp.Handler(self.registry.specs, self._call_from_server)
            self.server = mcp.Server(handler).start()
        return self.server

    def _call_from_server(self, name: str, args: dict) -> dict:
        try:
            return self._main.call(lambda: self.execute(name, args))
        except Exception as e:  # noqa: BLE001
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}

    def execute(self, name: str, args: dict) -> dict:
        """Roda a ferramenta no modelo aberto (thread da interface)."""
        tool = self.registry.tools.get(name)
        ctx = Context(self.session.doc, self._commit, self.session.storey_id)
        result = self.registry.call(ctx, name, args)
        title = tool.title if tool else name
        if result["isError"]:
            self._add(f"✗ {title}: {result['content'][0]['text']}", "erro")
        else:
            self._add(f"• {title}", "ferramenta")
        return result

    def _commit(self, tx) -> None:
        self.session.history.commit(tx)
        self._ours.append(tx)

    # --- pedido ------------------------------------------------------------------------

    def send(self) -> None:
        text = self.prompt.toPlainText().strip()
        images = list(self.attachments)
        if not (text or images) or self.running or not self.connector.available:
            return
        server = self.ensure_server()
        fd, self._config = tempfile.mkstemp(prefix="brasbim-mcp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(server.client_config(), f)
        self._ours, self._buffer, self._prompt = [], b"", text or "imagem anexada"
        self._add(text or "(imagem)", "pedido")
        if images:
            self._add_images(images)
        self.prompt.clear()
        self.attachments = []
        self._refresh_attachments()
        self._resumed = self.conversation is not None
        message = self.build_message(text, images)
        process = QProcess(self)
        process.setProgram(self.connector.program)
        process.setArguments(self.connector.arguments(self._config, self.conversation))
        process.setWorkingDirectory(tempfile.gettempdir())
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._done)
        process.errorOccurred.connect(self._failed)
        self.process = process
        self.send_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Trabalhando")
        process.start()
        process.write((message + "\n").encode("utf-8"))
        process.closeWriteChannel()

    def build_message(self, text: str, images=()) -> str:
        """A linha enviada ao conector: imagens, contexto da tela e o texto do usuário
        (só imagem: um texto padrão; spec/ui 54 §2.2)."""
        return request_message(f"{self.context_note()}\n\n{text or ONLY_IMAGE_TEXT}", images)

    def context_note(self) -> str:
        """Pavimento ativo e seleção, que vão junto do pedido (spec/ui 16 §2.1)."""
        return selection_note(self.session.doc, self.session.storey, self.session.selection)

    def stop(self) -> None:
        if self.process is not None:
            self._add("Interrompido.", "info")
            self.process.kill()

    def _read(self) -> None:
        self._buffer += bytes(self.process.readAllStandardOutput())
        *lines, self._buffer = self._buffer.split(b"\n")
        for line in lines:
            if line.strip():
                try:
                    self.handle_event(json.loads(line))
                except ValueError:
                    continue

    def handle_event(self, event: dict) -> None:
        """Um evento do ``stream-json`` do Claude Code."""
        kind = event.get("type")
        if event.get("session_id"):
            self.conversation = event["session_id"]
        if kind == "system" and event.get("subtype") == "init":
            servers = {s.get("name"): s.get("status") for s in event.get("mcp_servers", [])}
            if servers.get(mcp.SERVER_NAME) not in (None, "connected"):
                self._add(f"A IA não conectou ao BrasBim ({servers[mcp.SERVER_NAME]}).", "erro")
            model = event.get("model")
            if model:
                self.status.setText(f"Trabalhando ({model})")
        elif kind == "assistant":
            for block in (event.get("message") or {}).get("content", []):
                if block.get("type") == "text" and block.get("text", "").strip():
                    self._add(block["text"].strip(), "ia")
        elif kind == "result":
            if event.get("is_error"):
                self._add(str(event.get("result") or "A IA terminou com erro."), "erro")
            seconds = (event.get("duration_ms") or 0) / 1000
            self._add(f"Concluído em {seconds:.0f} s.", "info")

    def _failed(self, error) -> None:
        if error == QProcess.FailedToStart:
            self._add(f"Não foi possível iniciar o {self.connector.name}.", "erro")
            self._done()

    def _done(self, *args) -> None:
        if self.process is None:
            return
        self._read()
        err = bytes(self.process.readAllStandardError()).decode("utf-8", "replace").strip()
        if self.process.exitCode() != 0:
            if err:
                self._add(err[-500:], "erro")
            if self._resumed and not self._ours:
                self.conversation = None  # a conversa não pôde ser retomada
                self._add("A conversa anterior não pôde ser continuada; envie de novo "
                          "para começar outra.", "erro")
        self.process.deleteLater()
        self.process = None
        if self._config:
            Path(self._config).unlink(missing_ok=True)
            self._config = None
        self._group()
        self.stop_button.setEnabled(False)
        self._idle_status()
        self.finished.emit()

    def _group(self) -> None:
        """As transações do pedido viram um passo de desfazer (se nada entrou no meio)."""
        n, stack = len(self._ours), self.session.history.undo_stack
        if n and stack[-n:] == self._ours:
            label = f"Assistente: {_short(self._prompt)}"
            if n > 1:
                self.session.history.squash(n, label)
            else:
                stack[-1].label = label
            self.session.message(f"{label} ({n} alterações; Ctrl+Z desfaz tudo)")
            self.session.select(self.touched())  # o que a IA criou ou mudou fica à vista
        self._ours = []

    def touched(self) -> set[str]:
        """Elementos criados ou alterados no pedido que ainda existem no pavimento ativo."""
        doc, storey, found = self.session.doc, self.session.storey, set()
        for tx in self._ours:
            for op in tx.ops:
                e = doc.find(op.id) if op.op.endswith((".create", ".edit")) else None
                if e is None or not (any(e.is_a(c) for c in _SELECTABLE)
                                     or objects.is_object(e) or freeform.is_freeform(e)):
                    continue
                if e.is_a("IfcSpace"):
                    where = spaces.storey_of(e)
                else:
                    where = ifcopenshell.util.element.get_container(e)
                if where == storey:
                    found.add(op.id)
        return found

    def shutdown(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(2000)
        if self.server is not None:
            self.server.stop()
            self.server = None
