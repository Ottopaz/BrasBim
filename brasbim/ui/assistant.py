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

from PySide6.QtCore import QBuffer, QByteArray, QObject, QPointF, QProcess, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import plan as plan_mod
from brasbim.core.assistant import mcp
from brasbim.core.assistant.tools import Context, Registry, Tool, default_registry
from brasbim.ui import theme

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

    def arguments(self, config_path: str) -> list[str]:
        return ["-p", "--output-format", "stream-json", "--verbose",
                "--tools", "", "--strict-mcp-config", "--mcp-config", config_path,
                "--allowedTools", f"mcp__{mcp.SERVER_NAME}",
                "--no-session-persistence",
                "--append-system-prompt", mcp.INSTRUCTIONS]


def tool_label(name: str) -> str:
    """Nome da ferramenta MCP (``mcp__brasbim__create_walls``) → ``create_walls``."""
    return name.split("__")[-1]


# --- painel -------------------------------------------------------------------------------


class AssistantPanel(QWidget):
    """Pedido, botão Enviar/Parar e o andamento (o que a IA faz, a resposta final)."""

    finished = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.registry: Registry = default_registry()
        self.registry.add(view_plan_tool(session))
        self.connector = ClaudeCode()
        self.server: mcp.Server | None = None
        self.process: QProcess | None = None
        self._main = _MainThread()
        self._ours: list = []  # transações do pedido em curso
        self._buffer = b""
        self._config: str | None = None
        self._prompt = ""

        self.log = QListWidget()
        self.log.setWordWrap(True)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText(
            "Peça o que desenhar. Ex.: casa térrea de 3 quartos, sala e cozinha "
            "integradas, banheiro e área de serviço, uns 100 m².")
        self.prompt.setMaximumHeight(110)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send)
        self.stop_button = QPushButton("Parar")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        self.status = QLabel()
        self.status.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.addWidget(self.status, 1)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.send_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.log, 1)
        layout.addWidget(self.prompt)
        layout.addLayout(buttons)
        self._idle_status()

    # --- estado ----------------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self.process is not None

    def _idle_status(self) -> None:
        if self.connector.available:
            self.status.setText(f"IA: {self.connector.name}")
        else:
            self.status.setText(f"{self.connector.name} não encontrado neste PC")
        self.send_button.setEnabled(self.connector.available)

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
        if not text or self.running or not self.connector.available:
            return
        server = self.ensure_server()
        fd, self._config = tempfile.mkstemp(prefix="brasbim-mcp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(server.client_config(), f)
        self._ours, self._buffer, self._prompt = [], b"", text
        self._add(text, "pedido")
        self.prompt.clear()
        process = QProcess(self)
        process.setProgram(self.connector.program)
        process.setArguments(self.connector.arguments(self._config))
        process.setWorkingDirectory(tempfile.gettempdir())
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._done)
        process.errorOccurred.connect(self._failed)
        self.process = process
        self.send_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Trabalhando…")
        process.start()
        process.write(text.encode("utf-8"))
        process.closeWriteChannel()

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
        if kind == "system" and event.get("subtype") == "init":
            servers = {s.get("name"): s.get("status") for s in event.get("mcp_servers", [])}
            if servers.get(mcp.SERVER_NAME) not in (None, "connected"):
                self._add(f"A IA não conectou ao BrasBim ({servers[mcp.SERVER_NAME]}).", "erro")
            model = event.get("model")
            if model:
                self.status.setText(f"Trabalhando… ({model})")
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
        if self.process.exitCode() != 0 and err:
            self._add(err[-500:], "erro")
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
            label = f"Assistente: {self._prompt[:40]}{'…' if len(self._prompt) > 40 else ''}"
            if n > 1:
                self.session.history.squash(n, label)
            else:
                stack[-1].label = label
            self.session.message(f"{label} ({n} alterações; Ctrl+Z desfaz tudo)")
        self._ours = []

    def shutdown(self) -> None:
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(2000)
        if self.server is not None:
            self.server.stop()
            self.server = None
