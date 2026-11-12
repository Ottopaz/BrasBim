# SPDX-License-Identifier: GPL-3.0-or-later
"""Diálogo de Arquivo > Importar forma livre (``spec/elementos/forma-livre.md`` §4.2):
unidade do arquivo, eixo para cima, categoria e nome, com as medidas que a peça terá."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
)

from brasbim.core.document import OpError
from brasbim.core.freeform import importer, shapes
from brasbim.core.objects import definition as od
from brasbim.ui.tools import fmt

CATEGORY_ITEMS = [(v[3], k) for k, v in od.CATEGORIES.items()]


class FreeformImportDialog(QDialog):
    """Escolhas para importar ``path``; ``choice()`` devolve o que foi escolhido."""

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.setWindowTitle("Importar forma livre")
        self.name = QLineEdit(Path(path).stem)
        self.unit = QComboBox()
        for text, key in (("Milímetros", "mm"), ("Centímetros", "cm"), ("Metros", "m")):
            self.unit.addItem(text, key)
        self.unit.setCurrentIndex(2)
        self.up = QComboBox()
        self.up.addItem("Z (CAD, impressão 3D)", "z")
        self.up.addItem("Y (glTF, animação)", "y")
        self.up.setCurrentIndex(1 if path.lower().endswith(".glb") else 0)
        self.category = QComboBox()
        for text, key in CATEGORY_ITEMS:
            self.category.addItem(text, key)
        self.category.setCurrentIndex(self.category.findData("proxy"))
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow("Nome", self.name)
        form.addRow("Unidade do arquivo", self.unit)
        form.addRow("Eixo para cima", self.up)
        form.addRow("Categoria", self.category)
        form.addRow(self.summary)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Importar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        self.unit.currentIndexChanged.connect(self._refresh)
        self.up.currentIndexChanged.connect(self._refresh)
        self._refresh()

    def choice(self) -> dict:
        return {"name": self.name.text().strip() or Path(self.path).stem,
                "unit": self.unit.currentData(), "up": self.up.currentData(),
                "category": self.category.currentData()}

    def _refresh(self) -> None:
        """Medidas e triângulos com a unidade e o eixo escolhidos."""
        choice = self.choice()
        ok = self.buttons.button(QDialogButtonBox.Ok)
        try:
            _, info = importer.read(self.path, choice["unit"], choice["up"],
                                    shapes.MAX_TRIANGLES)
        except OpError as e:
            self.summary.setText(str(e))
            ok.setEnabled(False)
            return
        ok.setEnabled(True)
        w, d, h = info["size"]
        text = f"A peça fica com {fmt(w)} × {fmt(d)} × {fmt(h)} m (largura × " \
               f"profundidade × altura) e {info['kept']} triângulos."
        if info["kept"] < info["triangles"]:
            text += f" O arquivo tem {info['triangles']}: a malha será simplificada."
        self.summary.setText(text)
