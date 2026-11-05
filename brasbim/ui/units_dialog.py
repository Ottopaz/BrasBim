# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela "Unidades do projeto" (``spec/ui/44-unidades-do-projeto.md`` §2): uma linha por
tipo de medida com unidade, casas, mostrar a unidade e ocultar zeros, e um exemplo."""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from brasbim.core import units
from brasbim.core.document import OpError
from brasbim.ui import theme

# Valor do exemplo de cada tipo de medida (m, m² ou graus).
SAMPLES = {"work": 3.255, "linear": 3.25, "radius": 0.45, "angle": 37.5, "level": 2.8, "elevation": -0.15,
           "opening": 0.8, "area": 12.4}


class _Preview:
    """Documento de mentira para o exemplo."""


def sample(config: dict, kind: str) -> str:
    """Texto do exemplo com a configuração ``config`` (ainda não aplicada)."""

    doc = _Preview()
    doc.__dict__["_units"] = config  # ``units`` só lê a configuração do documento
    value = SAMPLES[kind]
    if kind == "area":
        return units.area(doc, value)
    if kind == "angle":
        return units.angle(doc, value)
    return units.length(doc, kind, value, signed=kind in ("level", "elevation"))


class UnitsDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Unidades do projeto")
        self.config = copy.deepcopy(units.config(session.doc))
        layout = QVBoxLayout(self)
        note = QLabel("Medidas de trabalho: o que se digita e lê nos campos. As outras "
                      "linhas: o texto das medidas no desenho. O modelo continua exato, em "
                      "metros. Vale para todo o projeto.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.INK_SOFT};")
        layout.addWidget(note)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        for col, title in enumerate(("Tipo de medida", "Unidade", "Casas", "Mostrar a unidade",
                                     "Ocultar zeros finais", "Exemplo")):
            head = QLabel(title)
            head.setStyleSheet(f"color: {theme.INK_SOFT};")
            grid.addWidget(head, 0, col)
        self.rows: dict[str, dict] = {}
        for row, (kind, name, where, allowed, _) in enumerate(units.KINDS, start=1):
            label = QLabel(name)
            label.setToolTip(where)
            unit = QComboBox()
            for code in allowed:
                unit.addItem(units.UNIT_LABELS[code], code)
            decimals = QSpinBox()
            decimals.setRange(0, units.MAX_DECIMALS)
            show = QCheckBox()
            if kind == "work":  # o campo já diz a unidade
                show.setEnabled(False)
                show.setToolTip("os campos mostram a unidade no nome")
            hide = QCheckBox()
            example = QLabel()
            example.setMinimumWidth(90)
            widgets = {"unit": unit, "decimals": decimals, "show_unit": show,
                       "hide_zeros": hide, "example": example}
            self.rows[kind] = widgets
            for col, w in enumerate((label, unit, decimals, show, hide, example)):
                grid.addWidget(w, row, col)
            unit.currentIndexChanged.connect(lambda _=0, k=kind: self._changed(k))
            decimals.valueChanged.connect(lambda _=0, k=kind: self._changed(k))
            show.toggled.connect(lambda _=False, k=kind: self._changed(k))
            hide.toggled.connect(lambda _=False, k=kind: self._changed(k))
        layout.addLayout(grid)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.reset_button = QPushButton("Restaurar o padrão")
        self.reset_button.clicked.connect(self.reset)
        buttons.addButton(self.reset_button, QDialogButtonBox.ResetRole)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load()

    def _load(self) -> None:
        for kind, w in self.rows.items():
            cfg = self.config[kind]
            for widget in (w["unit"], w["decimals"], w["show_unit"], w["hide_zeros"]):
                widget.blockSignals(True)
            w["unit"].setCurrentIndex(max(0, w["unit"].findData(cfg["unit"])))
            w["decimals"].setValue(cfg["decimals"])
            w["show_unit"].setChecked(cfg["show_unit"])
            w["hide_zeros"].setChecked(cfg["hide_zeros"])
            for widget in (w["unit"], w["decimals"], w["show_unit"], w["hide_zeros"]):
                widget.blockSignals(False)
            w["example"].setText(sample(self.config, kind))

    def _changed(self, kind: str) -> None:
        w = self.rows[kind]
        self.config[kind] = {"unit": w["unit"].currentData(), "decimals": w["decimals"].value(),
                             "show_unit": w["show_unit"].isChecked(),
                             "hide_zeros": w["hide_zeros"].isChecked()}
        w["example"].setText(sample(self.config, kind))

    def reset(self) -> None:
        self.config = units.default_config()
        self._load()

    def apply(self) -> None:
        doc = self.session.doc
        try:
            tx = units.set_units(doc, copy.deepcopy(self.config))
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        if not tx.ops or self.session.run(tx):
            self.accept()
