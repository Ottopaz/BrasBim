# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto > Materiais… (``spec/ui/06-planta-por-camadas.md`` §4.2): cor do 3D e estilo de
corte de cada material do projeto. Aplicar grava uma transação ``material.edit``."""

from __future__ import annotations

import copy
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import materials
from brasbim.core.ops import Transaction
from brasbim.ui.tools import fmt_exact, parse_number

PATTERNS = [("Nenhum", "none"), ("Sólido", "solid"), ("Linhas", "lines"), ("Cruzado", "cross")]
PAPER = "#F6F5F1"  # fundo da planta


def cut_swatch(style: dict, width: int, height: int, scale: float = 400.0) -> QPixmap:
    """Amostra do corte (``scale`` em px/m) com uma faixa da cor do 3D embaixo."""
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(PAPER))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    band = max(4, height // 6)
    area = QRectF(0, 0, width, height - band)
    cut = style["cut"]
    if cut.get("background"):
        painter.fillRect(area, QColor(cut["background"]))
    if cut["pattern"] in ("lines", "cross"):
        spacing = cut["spacing"] * scale
        if spacing >= 1:
            painter.setClipRect(area)
            painter.setPen(QPen(QColor(cut["line_color"]), 1))
            reach = math.hypot(width, height)
            angles = [cut["angle"]] + ([cut["angle"] + 90] if cut["pattern"] == "cross" else [])
            for degrees in angles:
                a = -math.radians(degrees)
                d = QPointF(math.cos(a), math.sin(a))
                n = QPointF(-d.y(), d.x())
                for k in range(-int(reach / spacing) - 1, int(reach / spacing) + 2):
                    o = n * (k * spacing)
                    painter.drawLine(o - d * reach, o + d * reach)
            painter.setClipping(False)
    painter.fillRect(QRectF(0, height - band, width, band), QColor(style["color"]))
    painter.setPen(QPen(QColor(materials.LINE_COLOR), 1))
    painter.drawRect(QRectF(0.5, 0.5, width - 1, height - 1))
    painter.end()
    return pixmap


class MaterialsDialog(QDialog):
    def __init__(self, session, parent=None, select: str | None = None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Materiais")
        self.current: str | None = None
        self.dirty = False
        self.list = QListWidget()
        self.list.setMinimumWidth(200)
        self.list.currentItemChanged.connect(self._picked)
        self.form = QFormLayout()
        self.color = self._color_button("Cor (3D)")
        self.pattern = QComboBox()
        for text, value in PATTERNS:
            self.pattern.addItem(text, value)
        self.pattern.currentIndexChanged.connect(self.touched)
        self.form.addRow("Corte", self.pattern)
        self.has_background = QCheckBox("Fundo")
        self.has_background.toggled.connect(self.touched)
        self.background = self._color_button(None)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.has_background)
        row.addWidget(self.background, 1)
        holder = QWidget()
        holder.setLayout(row)
        self.form.addRow("Cor do fundo", holder)
        self.angle = self._line("Ângulo (°)")
        self.spacing = self._line("Espaçamento (m)")
        self.line_color = self._color_button("Cor das linhas")
        self.note = QLabel()
        self.note.setStyleSheet("color:#666")
        self.form.addRow(self.note)
        self.sample = QLabel()
        self.form.addRow(self.sample)
        right = QWidget()
        right.setLayout(self.form)
        body = QHBoxLayout()
        body.addWidget(self.list)
        body.addWidget(right, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Apply).setText("Aplicar")
        buttons.button(QDialogButtonBox.Close).setText("Fechar")
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addWidget(buttons)
        self.refresh(select)

    # --- campos ------------------------------------------------------------------------

    def _line(self, label: str) -> QLineEdit:
        edit = QLineEdit()
        edit.textEdited.connect(self.touched)
        self.form.addRow(label, edit)
        return edit

    def _color_button(self, label: str | None) -> QPushButton:
        button = QPushButton()

        def pick():
            chosen = QColorDialog.getColor(QColor(button.property("color")), self,
                                           label or "Cor do fundo")
            if chosen.isValid():
                self.set_color(button, chosen.name())

        button.clicked.connect(pick)
        if label is not None:
            self.form.addRow(label, button)
        return button

    def set_color(self, button: QPushButton, color: str, touch: bool = True) -> None:
        color = color.upper()
        button.setProperty("color", color)
        text = "white" if QColor(color).lightness() < 128 else "black"
        button.setText(color)
        button.setStyleSheet(f"QPushButton {{ background: {color}; color: {text}; }}")
        if touch:
            self.touched()

    # --- lista -------------------------------------------------------------------------

    def names(self) -> list[str]:
        return sorted({m.Name for m in self.session.doc.ifc.by_type("IfcMaterial") if m.Name})

    def refresh(self, select: str | None = None) -> None:
        select = select or self.current
        self.list.blockSignals(True)
        self.list.clear()
        for name in self.names():
            style = materials.style(self.session.doc, name)
            text = f"{name} (padrão)" if style["default"] else name
            item = QListWidgetItem(QIcon(cut_swatch(style, 32, 20, 200)), text)
            item.setData(Qt.UserRole, name)
            self.list.addItem(item)
            if name == select:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.load(select if select in self.names() else None)

    def _picked(self, item, _previous) -> None:
        if self.dirty and self.current is not None:
            self.apply()  # mudar de material grava o que foi mexido
        self.load(item.data(Qt.UserRole) if item is not None else None)

    def load(self, name: str | None) -> None:
        self.current = name
        enabled = name is not None
        for w in (self.color, self.pattern, self.has_background, self.background, self.angle,
                  self.spacing, self.line_color):
            w.setEnabled(enabled)
        if not enabled:
            self.sample.clear()
            return
        style = materials.style(self.session.doc, name)
        cut = style["cut"]
        self.set_color(self.color, style["color"], touch=False)
        self.pattern.blockSignals(True)
        self.pattern.setCurrentIndex(self.pattern.findData(cut["pattern"]))
        self.pattern.blockSignals(False)
        self.has_background.blockSignals(True)
        self.has_background.setChecked(bool(cut.get("background")))
        self.has_background.blockSignals(False)
        self.set_color(self.background, cut.get("background") or style["color"], touch=False)
        self.angle.setText(fmt_exact(cut["angle"]))
        self.spacing.setText(fmt_exact(cut["spacing"]))
        self.set_color(self.line_color, cut["line_color"], touch=False)
        self.note.setText("Sem estilo gravado: valem os padrões." if style["default"] else "")
        self.dirty = False
        self._sync_background()
        self._update_sample()

    # --- edição ------------------------------------------------------------------------

    def read_style(self) -> dict:
        pattern = self.pattern.currentData()
        background = (self.background.property("color")
                      if self.has_background.isChecked() or pattern == "solid" else None)
        return {"color": self.color.property("color"),
                "cut": {"pattern": pattern, "background": background,
                        "angle": parse_number(self.angle.text()),
                        "spacing": parse_number(self.spacing.text()),
                        "line_color": self.line_color.property("color")}}

    def touched(self, *_args) -> None:
        self.dirty = True
        self._sync_background()
        self._update_sample()

    def _sync_background(self) -> None:
        solid = self.pattern.currentData() == "solid"
        self.has_background.setEnabled(self.current is not None and not solid)
        self.background.setEnabled(self.current is not None
                                   and (solid or self.has_background.isChecked()))

    def _update_sample(self) -> None:
        try:
            self.sample.setPixmap(cut_swatch(self.read_style(), 220, 120))
        except ValueError:
            self.sample.clear()

    def apply(self) -> bool:
        if self.current is None or not self.dirty:
            return True
        try:
            new = self.read_style()
        except ValueError as e:
            self.session.message(f"estilo inválido: {e}", "recusa")
            return False
        doc, name = self.session.doc, self.current
        ok = self.session.run(lambda: Transaction(
            f"Editar material {name}", [materials.edit_op(doc, name, copy.deepcopy(new))]))
        if ok:
            self.dirty = False
            self.refresh(name)
        return bool(ok)

    def closeEvent(self, event):
        if self.dirty:
            self.apply()
        super().closeEvent(event)
