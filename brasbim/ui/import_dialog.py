# SPDX-License-Identifier: GPL-3.0-or-later
"""Arquivo > Importar desenho (DXF, DWG)… (``spec/ui/22-importar-desenho.md`` §5): escolha
das camadas, da unidade e de trazer o desenho para perto da origem."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
)

from brasbim.core.imports import dxf
from brasbim.ui import theme

UNIT_NAMES = (("Milímetros", "mm"), ("Centímetros", "cm"), ("Metros", "m"))


def _count(layer: dxf.Layer) -> str:
    parts = []
    for n, one, many in ((len(layer.lines), "linha", "linhas"),
                         (len(layer.texts), "texto", "textos"),
                         (len(layer.points), "ponto", "pontos")):
        if n:
            parts.append(f"{n} {one if n == 1 else many}")
    return ", ".join(parts)


class ImportDialog(QDialog):
    """Mostra o que o arquivo tem e devolve (camadas, unidade, deslocamento)."""

    def __init__(self, drawing: dxf.Drawing, storey_name: str, parent=None):
        super().__init__(parent)
        self.drawing = drawing
        self.setWindowTitle(f"Importar {drawing.source}")
        form = QFormLayout(self)
        form.addRow("Pavimento", QLabel(storey_name))
        self.layers = QListWidget()
        for name in sorted(drawing.layers):
            item = QListWidgetItem(f"{name}  ({_count(drawing.layers[name])})")
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.layers.addItem(item)
        self.layers.setMinimumHeight(160)
        form.addRow("Camadas", self.layers)
        self.unit = QComboBox()
        for text, value in UNIT_NAMES:
            self.unit.addItem(text, value)
        self.unit.setCurrentIndex(self.unit.findData(drawing.unit or "m"))
        self.unit.setToolTip("Unidade em que o desenho foi feito"
                             + ("" if drawing.unit else " (o arquivo não informa)"))
        form.addRow("Unidade do arquivo", self.unit)
        self.near = QCheckBox("Trazer o desenho para perto da origem")
        self.near.setToolTip("Coordenadas de levantamento (UTM) ficam a milhares de km da "
                             "origem; o canto inferior esquerdo do desenho vai para (0, 0)")
        self.near.setChecked(dxf.default_offset(drawing, self.unit.currentData()) != (0, 0))
        form.addRow("", self.near)
        note = QLabel("O desenho entra como referência na camada Levantamento; dá para "
                      "ocultar ou bloquear no painel Camadas.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.INK_SOFT}")
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Importar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def choice(self) -> tuple[set[str], str, tuple[float, float]]:
        layers = {self.layers.item(i).data(Qt.UserRole) for i in range(self.layers.count())
                  if self.layers.item(i).checkState() == Qt.Checked}
        unit = self.unit.currentData()
        box = self.drawing.bounds()
        offset = (box[0], box[1]) if self.near.isChecked() and box else (0.0, 0.0)
        return layers, unit, offset
