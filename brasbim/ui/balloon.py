# SPDX-License-Identifier: GPL-3.0-or-later
"""Balão de mensagem (``spec/ui/42-limpeza-da-janela.md`` §4).

Depois de uma ação, a mesma mensagem que entra em Mensagens aparece num balão no canto de
baixo, à esquerda da vista, logo acima da barra da vista. Some sozinho depois de alguns
segundos, esmaecendo; uma mensagem nova toma o lugar da anterior. Não pega o mouse: o
clique passa para a vista que está embaixo.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from brasbim.ui import theme

MARGIN = 10  # px entre o balão, a borda da vista e a barra de baixo
MAX_WIDTH = 520
FADE_MS = 400
LEVEL_COLOR = {"recusa": theme.ERROR, "aviso": theme.WARN, "info": theme.ACCENT}


def duration(text: str, level: str) -> int:
    """Tempo na tela (ms): o bastante para ler; recusas e avisos ficam mais."""
    base = 3000 + 60 * len(text.split())
    if level in ("recusa", "aviso"):
        base += 2000
    return min(base, 10000)


class MessageBalloon(QFrame):
    def __init__(self, area: QWidget, anchor):
        """``area``: o widget central da janela; ``anchor()``: o widget acima do qual o
        balão fica (a barra da vista ou, sem ela, a linha de comando)."""
        super().__init__(area)
        self.anchor = anchor
        self.setObjectName("balao")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.PlainText)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.addWidget(self.label)
        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.fade = QPropertyAnimation(self.opacity, b"opacity", self)
        self.fade.setDuration(FADE_MS)
        self.fade.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade.finished.connect(self._faded)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)
        self.level = "info"
        area.installEventFilter(self)
        self.hide()

    def show_message(self, text: str, level: str = "info") -> None:
        self.level = level
        color = LEVEL_COLOR.get(level, theme.ACCENT)
        self.setStyleSheet(
            f"#balao {{ background: {theme.FIELD}; border: 1px solid {theme.RULE};"
            f" border-left: 3px solid {color}; border-radius: 4px; }}"
            f"#balao QLabel {{ color: {theme.INK}; background: transparent; border: none; }}")
        self.label.setText(text)
        self.fade.stop()
        self.opacity.setOpacity(1.0)
        self.place()
        self.show()
        self.raise_()
        self.timer.start(duration(text, level))

    def dismiss(self) -> None:
        """Esmaece e esconde."""
        self.timer.stop()
        if not self.isVisible():
            return
        self.fade.stop()
        self.fade.setStartValue(self.opacity.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()

    def _faded(self) -> None:
        if self.opacity.opacity() <= 0.01:
            self.hide()

    def place(self) -> None:
        area = self.parentWidget()
        room = min(MAX_WIDTH, max(120, area.width() - 2 * MARGIN)) - 24
        text = self.label.fontMetrics().horizontalAdvance(self.label.text()) + 2
        width = min(room, text)
        self.label.setFixedSize(width, self.label.heightForWidth(width))
        self.adjustSize()
        anchor = self.anchor()
        bottom = anchor.y() if anchor is not None and anchor.isVisible() else area.height()
        self.move(MARGIN, max(0, bottom - self.height() - MARGIN))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and self.isVisible():
            self.place()
        return False
