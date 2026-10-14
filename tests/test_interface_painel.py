# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel de propriedades deitado (``spec/ui/04-painel-de-propriedades.md`` §5): UI37 a
UI40."""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QGridLayout,
    QLabel,
    QLineEdit,
    QWidget,
)
from test_interface import _field, _rectangle

from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import block_grid


def _settle():
    for _ in range(4):
        QApplication.processEvents()


def _dock(window, area, size):
    dock = window.findChild(QDockWidget, "propriedades")
    window.addDockWidget(area, dock)
    orientation = Qt.Vertical if area in (Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea) \
        else Qt.Horizontal
    window.resizeDocks([dock], [size], orientation)
    _settle()
    return dock


def _blocks(panel) -> dict[str, list[tuple[str, int, int]]]:
    """Blocos do arranjo deitado: título → [(nome do campo, linha, coluna)]."""
    out = {}
    for block in panel.widget().findChildren(QWidget, "bloco"):
        grid = block.layout().itemAt(1).layout()
        fields = []
        for i in range(grid.count()):
            r, c, _, _ = grid.getItemPosition(i)
            widget = grid.itemAt(i).widget()
            if isinstance(widget, QLabel) and c % 2 == 0:
                fields.append((widget.text(), r, c // 2))
        out[block.property("titulo")] = fields
    return out


def _lying_field(panel, name, kind=QLineEdit):
    for grid in panel.widget().findChildren(QGridLayout):
        for i in range(grid.count()):
            widget = grid.itemAt(i).widget()
            if isinstance(widget, QLabel) and widget.text() == name:
                r, c, _, _ = grid.getItemPosition(i)
                found = grid.itemAtPosition(r, c + 1).widget()
                if isinstance(found, kind):
                    return found
    raise LookupError(name)


def test_ui37_em_pe_na_lateral(window):
    s = window.session
    walls = _rectangle(window)
    _dock(window, Qt.RightDockWidgetArea, 300)
    s.select([walls[0].GlobalId])
    _settle()
    assert not window.properties.lying
    assert _field(window, "Base").text() == "0,00"


def test_ui38_deitado_no_topo(window):
    s = window.session
    walls = _rectangle(window)
    panel = window.properties
    _dock(window, Qt.TopDockWidgetArea, 170)
    s.select([walls[0].GlobalId])
    _settle()
    assert panel.lying and panel.form is None
    assert panel.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    lines = panel.lines
    assert lines >= 2
    blocks = _blocks(panel)
    assert list(blocks)[:2] == ["Parede", "Altura"]
    geometry = blocks["Geometria e quantidades"]
    assert len(geometry) == 6
    assert max(c for _, _, c in geometry) + 1 == math.ceil(6 / lines)
    assert max(r for _, r, _ in geometry) + 1 == min(lines, 6)
    _dock(window, Qt.RightDockWidgetArea, 300)  # volta a ficar em pé
    _settle()
    assert not panel.lying and panel.form is not None


def test_ui39_editar_no_arranjo_deitado(window):
    s = window.session
    walls = _rectangle(window)
    _dock(window, Qt.TopDockWidgetArea, 170)
    s.select([walls[0].GlobalId])
    _settle()
    base = _lying_field(window.properties, "Base")
    base.setText("0,10")
    base.editingFinished.emit()
    tx = s.history.undo_stack[-1]
    assert [op.op for op in tx.ops] == ["wall.edit"]
    assert tx.ops[0].after == {"base_offset": pytest.approx(0.1)}
    assert cmd.read_state(s.doc, walls[0])["base_offset"] == pytest.approx(0.1)


def test_ui40_block_grid():
    assert block_grid(6, 3) == [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
    assert block_grid(2, 3) == [(0, 0), (1, 0)]
    assert block_grid(3, 0) == [(0, 0), (0, 1), (0, 2)]
