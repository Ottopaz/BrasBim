# SPDX-License-Identifier: GPL-3.0-or-later
"""Aba da tabela de quantitativos (spec/ui 17 §5): grade com as linhas calculadas do
modelo, exportação para CSV e XLSX. Clicar numa linha seleciona os elementos dela;
clique duplo mostra na planta. No quadro de áreas do projeto legal (spec/ui 31 §5), a
memória de cálculo da linha escolhida aparece embaixo da grade (e sai na exportação)."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.document import OpError
from brasbim.core.quantities import export
from brasbim.core.quantities import tables as tables_
from brasbim.ui import theme

FORMATS = {"csv": ("CSV (*.csv)", export.write_csv),
           "xlsx": ("Planilha XLSX (*.xlsx)", export.write_xlsx)}


class TableView(QWidget):
    def __init__(self, session, table_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.table_gid = table_gid
        self.show_in_plan = None  # posto pela janela principal
        self.result: tables_.Result | None = None
        self.grid = QTableWidget(0, 0)
        self.grid.verticalHeader().hide()
        self.grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grid.cellClicked.connect(self._clicked)
        self.grid.cellDoubleClicked.connect(self._double_clicked)
        self.csv_button = QPushButton("Exportar CSV…")
        self.csv_button.clicked.connect(lambda: self.export("csv"))
        self.xlsx_button = QPushButton("Exportar XLSX…")
        self.xlsx_button.clicked.connect(lambda: self.export("xlsx"))
        bar = QHBoxLayout()
        bar.addStretch(1)
        bar.addWidget(self.csv_button)
        bar.addWidget(self.xlsx_button)
        self.memo = QLabel()
        self.memo.setWordWrap(True)
        self.memo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.memo.setStyleSheet(f"color: {theme.INK}; padding: 6px; background: {theme.PANEL}")
        self.memo.hide()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(bar)
        layout.addWidget(self.grid, 1)
        layout.addWidget(self.memo)
        self.invalidate()

    @property
    def table(self):
        return self.session.doc.find(self.table_gid)

    @property
    def title(self) -> str:
        table = self.table
        return (tables_.read_state(table)["name"] or "Tabela") if table is not None \
            else "Tabela"

    def invalidate(self) -> None:
        """Refaz a grade a partir do modelo (a cada mudança, §5)."""
        table = self.table
        if table is None:
            return
        try:
            self.result = tables_.compute(self.session.doc, table)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        result = self.result
        self.grid.clear()
        self.grid.setColumnCount(len(result.columns))
        self.grid.setRowCount(len(result.rows))
        self.grid.setHorizontalHeaderLabels([c.title for c in result.columns])
        for r, row in enumerate(result.rows):
            for c, value in enumerate(row.cells):
                item = QTableWidgetItem(tables_.format_value(value))
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if row.bold:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if isinstance(value, bool):  # "Atende" do quadro do projeto legal
                    item.setForeground(QColor(theme.OK if value else theme.ERROR))
                self.grid.setItem(r, c, item)
        header = self.grid.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        legal = any(row.memo for row in result.rows)
        for c, column in enumerate(result.columns):  # a memória vai embaixo, não numa coluna
            self.grid.setColumnHidden(c, legal and column.field == "memo")
        self.memo.setVisible(legal)
        self._show_memo(self.grid.currentRow())

    def _show_memo(self, row: int) -> None:
        if self.result is None or not 0 <= row < len(self.result.rows) \
                or not self.result.rows[row].memo:
            self.memo.setText("Memória de cálculo: escolha uma linha.")
            return
        line = self.result.rows[row]
        self.memo.setText(f"<b>{escape(str(line.cells[0]))}</b>: {escape(line.memo)}")

    def elements_at(self, row: int) -> list[str]:
        if self.result is None or not 0 <= row < len(self.result.rows):
            return []
        return self.result.rows[row].elements

    def _clicked(self, row: int, _column: int = 0) -> None:
        self._show_memo(row)
        self.session.select(self.elements_at(row))

    def _double_clicked(self, row: int, _column: int = 0) -> None:
        gids = self.elements_at(row)
        if gids and self.show_in_plan is not None:
            self.session.select(gids)
            self.show_in_plan(gids[0])

    def export(self, kind: str, path: str | None = None) -> str | None:
        """Grava a tabela em CSV ou XLSX (§5); sem ``path``, pergunta onde."""
        if self.result is None:
            return None
        label, write = FORMATS[kind]
        if path is None:
            name = export.sheet_name(self.result.name)
            path, _ = QFileDialog.getSaveFileName(self, f"Exportar {kind.upper()}",
                                                  f"{name}.{kind}", label)
            if not path:
                return None
        if not path.lower().endswith(f".{kind}"):
            path += f".{kind}"
        try:
            write(path, self.result)
        except OSError as e:
            self.session.message(f"não foi possível gravar {path}: {e}", "recusa")
            return None
        self.session.message(f"Tabela exportada: {path}")
        return path
