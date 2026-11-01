# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadro das operações de sólidos junto à seleção (pedido do revisor em 2026-11-01,
complemento da spec/ui 41 §3): com um elemento selecionado que recorta ou é recortado,
aparece, junto dele, uma linha por operação com o ícone dela e o outro elemento; os outros
elementos ficam destacados na planta e no 3D. Clicar numa linha seleciona aquele elemento.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QToolButton, QVBoxLayout

from brasbim.core.structure import solids
from brasbim.ui import icons, theme

OPERATION_ICON = {solids.SUBTRACT: "solid_subtract", solids.UP: "solid_up",
                  solids.DOWN: "solid_down", solids.INTERSECT: "solid_intersect"}
ROLE_TEXT = {"cut_by": "Recortado por", "cuts": "Recorta"}
GAP = 12.0


def partners_of_selection(view) -> list[tuple[str, str, str, str]]:
    """Operações do elemento selecionado sozinho, com a ferramenta Selecionar."""
    session = view.ctx.session
    tool = view.toolbox.active
    if tool is None or tool.name != "select" or len(session.selection) != 1:
        return []
    element = session.doc.find(next(iter(session.selection)))
    return solids.partners(element) if element is not None else []


def partner_ids(view) -> set[str]:
    """GlobalIds a destacar: os que fazem operação com o selecionado."""
    return {gid for _, gid, _, _ in partners_of_selection(view)}


def badge_position(rect, size, view, gap: float = GAP) -> tuple[float, float]:
    """Canto superior esquerdo do quadro: abaixo do canto inferior esquerdo da seleção
    (a mini-barra fica acima, à direita); sem lugar, acima à esquerda; dentro da vista."""
    x0, y0, _, y1 = rect
    w, h = size
    vw, vh = view
    y = y1 + gap
    if y + h > vh:
        y = y0 - gap - h
    return (min(max(x0, 0.0), max(vw - w, 0.0)), min(max(y, 0.0), max(vh - h, 0.0)))


class SolidBadge(QFrame):
    def __init__(self, view, select):
        super().__init__(view)
        self.view = view
        self.select = select  # (GlobalId) → seleciona o outro elemento
        self.setObjectName("quadro_solidos")
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"#quadro_solidos {{ background:{theme.FIELD}; border:1px solid {theme.RULE};"
            f" border-left:3px solid {theme.SOLID_PARTNER}; border-radius:3px; }}"
            f"#quadro_solidos QToolButton {{ color:{theme.INK}; padding:1px 4px;"
            f" text-align:left; }}")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(2, 2, 2, 2)
        self.layout_.setSpacing(0)
        self.rows: list[QToolButton] = []
        self._shown: list = []
        self.hide()

    def texts(self) -> list[str]:
        return [b.text() for b in self.rows]

    def _fill(self, items) -> None:
        if items == self._shown:
            return
        self._shown = list(items)
        for button in self.rows:
            button.deleteLater()
        self.rows = []
        for role, gid, name, operation in items:
            button = QToolButton(self)
            button.setIcon(icons.icon(OPERATION_ICON[operation]))
            button.setIconSize(QSize(18, 18))
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setText(f"{ROLE_TEXT[role]} {name} · {solids.LABELS[operation]}")
            button.setToolTip("Clique para selecionar este elemento")
            button.clicked.connect(lambda _=False, g=gid: self.select(g))
            self.layout_.addWidget(button)
            self.rows.append(button)

    def place(self) -> None:
        view = self.view
        tool = view.toolbox.active
        busy = (getattr(tool, "drag", None) is not None
                or getattr(tool, "drag3d", None) is not None
                or getattr(view, "navigating", False))
        items = partners_of_selection(view)
        rect = view.selection_rect() if items else None
        if busy or rect is None:
            self.hide()
            return
        self._fill(items)
        self.adjustSize()
        x, y = badge_position(rect, (self.width(), self.height()),
                              (view.width(), view.height()))
        self.move(int(x), int(y))
        self.show()
        self.raise_()
