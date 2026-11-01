# SPDX-License-Identifier: GPL-3.0-or-later
"""Faixa de título dos painéis (``spec/ui/42-limpeza-da-janela.md`` §1).

Encaixado, o painel mostra só o nome: sem os botões de soltar e fechar. Solto (flutuando),
ganha o botão de fechar. Arrastar a faixa solta e encaixa o painel, e o clique duplo
alterna, como antes; o painel fechado volta por Exibir > Painéis.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from brasbim.ui import icons, theme


class DockTitle(QWidget):
    def __init__(self, dock: QDockWidget):
        super().__init__(dock)
        self.dock = dock
        self.setObjectName("titulo_painel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#titulo_painel {{ background: {theme.FRAME}; border: none; }}"
            f"QWidget#titulo_painel QLabel {{ color: {theme.INK_SOFT}; }}"
            "QWidget#titulo_painel QToolButton { padding: 1px; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 4, 3)
        layout.setSpacing(4)
        # O rótulo deixa passar o mouse: o painel recebe o arrasto e o clique duplo.
        self.label = QLabel(dock.windowTitle())
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # não alarga
        self.close_button = QToolButton()
        self.close_button.setIcon(icons.icon("delete"))
        self.close_button.setIconSize(QSize(12, 12))
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip("Fechar o painel (volta por Exibir > Painéis)")
        self.close_button.clicked.connect(dock.close)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.close_button)
        dock.windowTitleChanged.connect(self.label.setText)
        dock.topLevelChanged.connect(self._floating)
        self._floating(dock.isFloating())

    def _floating(self, floating: bool) -> None:
        self.close_button.setVisible(bool(floating))

    _height: int | None = None

    def _title_height(self) -> int:
        """A mesma altura com e sem o botão: o painel não pula ao soltar. Guardada: o Qt
        pede o tamanho dezenas de milhares de vezes; muda só com a fonte ou o estilo."""
        if self._height is None:
            margins = self.layout().contentsMargins()
            self._height = max(self.label.sizeHint().height(),
                               self.close_button.sizeHint().height())                 + margins.top() + margins.bottom()
        return self._height

    def changeEvent(self, event):
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._height = None
        super().changeEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), self._title_height())

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self._title_height())


def plain_title(dock: QDockWidget) -> DockTitle:
    """Põe a faixa de título do BrasBim no painel."""
    title = DockTitle(dock)
    dock.setTitleBarWidget(title)
    return title
