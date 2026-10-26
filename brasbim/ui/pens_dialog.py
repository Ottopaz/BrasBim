# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto > Tabelas de penas… (``spec/ui/27-tabela-de-penas.md`` §4): penas (cor,
espessura, descrição) e a pena de cada categoria de linha, em várias tabelas. Trabalha
numa cópia da configuração; OK grava tudo numa transação."""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import pens


def swatch(color: str, size: int = 14) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def pen_label(number: str, pen: dict) -> str:
    weight = f"{pen['weight']:g}".replace(".", ",")
    note = f" · {pen['note']}" if pen.get("note") else ""
    return f"{number} · {weight} mm{note}"


class PensDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tabelas de penas")
        self.resize(560, 560)
        self.config = copy.deepcopy(pens.config(doc))
        self.table_id = self.config["current"]
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Tabela"))
        self.tables = QComboBox()
        self.tables.currentIndexChanged.connect(self._table_chosen)
        top.addWidget(self.tables, 1)
        for text, slot in (("Nova", self.new_table), ("Duplicar", self.duplicate_table),
                           ("Renomear…", self.rename_table), ("Excluir", self.delete_table)):
            button = QPushButton(text)
            button.clicked.connect(lambda _=False, f=slot: f())
            top.addWidget(button)
        layout.addLayout(top)
        row = QHBoxLayout()
        self.current = QCheckBox("Usar na janela")
        self.current.toggled.connect(self._set_current)
        row.addWidget(self.current)
        self.black = QCheckBox("Imprimir em preto (pranchas e PDF)")
        self.black.toggled.connect(lambda v: self.table.__setitem__("print_black", bool(v)))
        row.addWidget(self.black)
        row.addStretch(1)
        layout.addLayout(row)
        self.tabs = QTabWidget()
        self.pen_grid = QTableWidget(0, 4)
        self.pen_grid.setHorizontalHeaderLabels(["Nº", "Cor", "Espessura", "Descrição"])
        self.pen_grid.verticalHeader().hide()
        self.pen_grid.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.pen_grid.setSelectionMode(QAbstractItemView.NoSelection)
        pens_page = QVBoxLayout()
        pens_page.addWidget(self.pen_grid)
        pen_buttons = QHBoxLayout()
        add = QPushButton("Adicionar pena")
        add.clicked.connect(self.add_pen)
        remove = QPushButton("Tirar a última")
        remove.clicked.connect(self.remove_pen)
        pen_buttons.addWidget(add)
        pen_buttons.addWidget(remove)
        pen_buttons.addStretch(1)
        pens_page.addLayout(pen_buttons)
        page = QWidget()
        page.setLayout(pens_page)
        self.tabs.addTab(page, "Penas")
        self.category_grid = QTableWidget(0, 2)
        self.category_grid.setHorizontalHeaderLabels(["Categoria", "Pena"])
        self.category_grid.verticalHeader().hide()
        self.category_grid.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.category_grid.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.category_grid.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabs.addTab(self.category_grid, "Categorias")
        layout.addWidget(self.tabs, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._fill_tables()

    # --- tabela escolhida ----------------------------------------------------------------

    @property
    def table(self) -> dict:
        return pens.table(self.config, self.table_id)

    def _fill_tables(self) -> None:
        self.tables.blockSignals(True)
        self.tables.clear()
        for t in self.config["tables"]:
            self.tables.addItem(t["name"], t["id"])
        self.tables.setCurrentIndex(max(0, self.tables.findData(self.table_id)))
        self.tables.blockSignals(False)
        self._fill()

    def _table_chosen(self, index: int) -> None:
        self.table_id = self.tables.itemData(index)
        self._fill()

    def _set_current(self, on: bool) -> None:
        if on:
            self.config["current"] = self.table_id

    def _fill(self) -> None:
        table = self.table
        for box, value in ((self.current, self.config["current"] == table["id"]),
                           (self.black, bool(table.get("print_black")))):
            box.blockSignals(True)
            box.setChecked(value)
            box.blockSignals(False)
        self.current.setEnabled(not self.current.isChecked())
        numbers = sorted(table["pens"], key=int)
        self.pen_grid.setRowCount(len(numbers))
        for row, number in enumerate(numbers):
            pen = table["pens"][number]
            label = QLabel(number)
            label.setAlignment(Qt.AlignCenter)
            self.pen_grid.setCellWidget(row, 0, label)
            color = QPushButton(pen["color"].upper())
            color.setIcon(swatch(pen["color"]))
            color.clicked.connect(lambda _=False, n=number: self.choose_color(n))
            self.pen_grid.setCellWidget(row, 1, color)
            weight = QDoubleSpinBox()
            weight.setRange(0.05, 5.0)
            weight.setDecimals(2)
            weight.setSingleStep(0.05)
            weight.setSuffix(" mm")
            weight.setValue(float(pen["weight"]))
            weight.valueChanged.connect(lambda v, n=number: self.set_pen(n, weight=v))
            self.pen_grid.setCellWidget(row, 2, weight)
            note = QLineEdit(pen.get("note") or "")
            note.textEdited.connect(lambda v, n=number: self.set_pen(n, note=v))
            self.pen_grid.setCellWidget(row, 3, note)
        self.category_grid.setRowCount(len(pens.CATEGORIES))
        for row, (key, (label, _, default)) in enumerate(pens.CATEGORIES.items()):
            self.category_grid.setCellWidget(row, 0, QLabel(label))
            combo = QComboBox()
            for number in numbers:
                combo.addItem(swatch(table["pens"][number]["color"]),
                              pen_label(number, table["pens"][number]), number)
            current = str(table["categories"].get(key, default))
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.currentIndexChanged.connect(
                lambda i, k=key, c=combo: self.set_category(k, c.itemData(i)))
            self.category_grid.setCellWidget(row, 1, combo)

    # --- edição --------------------------------------------------------------------------

    def set_pen(self, number: str, **values) -> None:
        self.table["pens"][number].update(values)
        if "weight" in values:  # os rótulos das categorias mostram a espessura
            for row in range(self.category_grid.rowCount()):
                combo = self.category_grid.cellWidget(row, 1)
                index = combo.findData(number)
                if index >= 0:
                    combo.setItemText(index, pen_label(number, self.table["pens"][number]))

    def choose_color(self, number: str, color: str | None = None) -> None:
        if color is None:
            chosen = QColorDialog.getColor(QColor(self.table["pens"][number]["color"]), self,
                                           f"Cor da pena {number}")
            if not chosen.isValid():
                return
            color = chosen.name()
        self.table["pens"][number]["color"] = color.upper()
        self._fill()

    def set_category(self, key: str, number: str) -> None:
        self.table["categories"][key] = int(number)

    def add_pen(self) -> None:
        table = self.table
        if len(table["pens"]) >= pens.MAX_PENS:
            return
        number = str(max(int(n) for n in table["pens"]) + 1)
        table["pens"][number] = {"color": pens.INK, "weight": 0.25, "note": ""}
        self._fill()

    def remove_pen(self) -> None:
        table = self.table
        if len(table["pens"]) <= 1:
            return
        last = str(max(int(n) for n in table["pens"]))
        if last in {str(v) for v in table["categories"].values()}:
            return  # pena em uso por uma categoria
        del table["pens"][last]
        self._fill()

    def _unique(self, base: str) -> str:
        names = {t["name"].lower() for t in self.config["tables"]}
        name, n = base, 2
        while name.lower() in names:
            name, n = f"{base} ({n})", n + 1
        return name

    def new_table(self) -> None:
        table = pens.default_table(self._unique("Nova tabela"), pens.new_id())
        self.config["tables"].append(table)
        self.table_id = table["id"]
        self._fill_tables()

    def duplicate_table(self) -> None:
        table = copy.deepcopy(self.table)
        table["id"], table["name"] = pens.new_id(), self._unique(f"{table['name']} (cópia)")
        self.config["tables"].append(table)
        self.table_id = table["id"]
        self._fill_tables()

    def rename_table(self, name: str | None = None) -> None:
        if name is None:
            name, ok = QInputDialog.getText(self, "Renomear tabela", "Nome",
                                            text=self.table["name"])
            if not ok:
                return
        if name.strip():
            self.table["name"] = name.strip()
            self._fill_tables()

    def delete_table(self) -> None:
        if len(self.config["tables"]) <= 1:
            return
        gone = self.table_id
        self.config["tables"] = [t for t in self.config["tables"] if t["id"] != gone]
        if self.config["current"] == gone:
            self.config["current"] = self.config["tables"][0]["id"]
        self.table_id = self.config["current"]
        self._fill_tables()
