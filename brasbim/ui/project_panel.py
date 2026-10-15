# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Projeto: tabela de pavimentos (``spec/ui/02-edicao.md`` §7).

Um clique numa linha torna o pavimento ativo; clique duplo numa célula edita o nome, a
cota ou o plano de corte (``storey.edit``; spec/ui 06 §3.1, vazio = padrão); os botões
criam e excluem pavimentos.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import storeys as storeys_
from brasbim.core.walls import commands as cmd
from brasbim.ui.tools import fmt, parse_number

NEW_STOREY_HEIGHT = 2.80  # cota do pavimento novo: a maior + 2,80 m (§7)


def new_storey_name(doc) -> str:
    names = {s.Name for s in doc.storeys()}
    n = len(names) + 1
    while f"Pavimento {n}" in names:
        n += 1
    return f"Pavimento {n}"


class ProjectPanel(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nome", "Cota", "Plano de corte"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2):
            self.table.horizontalHeader().setSectionResizeMode(column,
                                                               QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked
                                   | QAbstractItemView.EditKeyPressed)
        self.table.cellClicked.connect(self._activate)
        self.table.itemChanged.connect(self._edited)
        self.add_button = QPushButton("Novo pavimento")
        self.add_button.clicked.connect(self.add_storey)
        self.delete_button = QPushButton("Excluir pavimento")
        self.delete_button.clicked.connect(self.delete_storey)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.delete_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        self.table.blockSignals(True)
        storeys = list(reversed(self.session.doc.storeys()))
        self.table.setRowCount(len(storeys))
        for row, storey in enumerate(storeys):
            active = storey.GlobalId == self.session.storey_id
            name = QTableWidgetItem(f"{'● ' if active else ''}{storey.Name or ''}")
            name.setData(Qt.UserRole, storey.GlobalId)
            elevation = QTableWidgetItem(fmt(storey.Elevation or 0.0))
            cut = QTableWidgetItem(fmt(storeys_.cut_height(storey)))
            cut.setToolTip("Altura do plano de corte da planta acima da cota; "
                           "vazio volta ao padrão")
            for item in (elevation, cut):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if active:
                font = name.font()
                font.setBold(True)
                for item in (name, elevation, cut):
                    item.setFont(font)
                self.table.selectRow(row)
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, elevation)
            self.table.setItem(row, 2, cut)
        self.delete_button.setEnabled(len(storeys) > 1)
        self.table.blockSignals(False)

    def storey_at(self, row: int):
        item = self.table.item(row, 0)
        return self.session.doc.find(item.data(Qt.UserRole)) if item is not None else None

    def _activate(self, row: int, _column: int = 0) -> None:
        storey = self.storey_at(row)
        if storey is not None and storey.GlobalId != self.session.storey_id:
            self.session.set_storey(storey)

    def _edited(self, item: QTableWidgetItem) -> None:
        storey = self.storey_at(item.row())
        if storey is None:
            return
        text = item.text().strip()
        doc = self.session.doc
        if item.column() == 0:
            name = text.removeprefix("● ").strip()
            if name and name != storey.Name:
                self.session.run(lambda: cmd.edit_storey(doc, storey, name=name))
        elif item.column() == 2:
            self._edit_cut(storey, text)
        else:
            try:
                elevation = parse_number(text)
            except ValueError:
                self.session.message(f"cota inválida: {text!r}", "recusa")
                elevation = None
            if elevation is not None and abs(elevation - (storey.Elevation or 0.0)) > 1e-9:
                self.session.run(lambda: cmd.edit_storey(doc, storey, elevation=elevation))
        self.refresh()  # recusa ou texto inválido: volta ao valor do modelo

    def _edit_cut(self, storey, text: str) -> None:
        if not text:
            value = None
        else:
            try:
                value = parse_number(text)
            except ValueError:
                self.session.message(f"plano de corte inválido: {text!r}", "recusa")
                return
        current = storeys_.read(storey)["cut_height"]
        if value is None and current is None:
            return
        if value is not None and abs(value - storeys_.cut_height(storey)) < 1e-9:
            return
        doc = self.session.doc
        self.session.run(lambda: cmd.edit_storey(doc, storey, cut_height=value))

    def add_storey(self) -> None:
        doc = self.session.doc
        top = max((s.Elevation or 0.0 for s in doc.storeys()), default=-NEW_STOREY_HEIGHT)
        tx = cmd.create_storey(doc, new_storey_name(doc), top + NEW_STOREY_HEIGHT)
        if self.session.run(tx):
            self.session.set_storey(doc.find(tx.ops[0].id))

    def delete_storey(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        storey = self.storey_at(rows[0].row()) if rows else self.session.storey
        if storey is not None:
            doc = self.session.doc
            self.session.run(lambda: cmd.delete_storey(doc, storey))
