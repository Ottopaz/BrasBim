# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Projeto: tabela de pavimentos (``spec/ui/02-edicao.md`` §7), vistas, pranchas e
tabelas de quantitativos (spec/ui 17 §5).

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
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import storeys as storeys_
from brasbim.core.quantities import tables as tables_
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
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nome", "Cota", "Plano de corte", "Escala"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(column,
                                                               QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked
                                   | QAbstractItemView.EditKeyPressed)
        self.table.cellClicked.connect(self._activate)
        self.table.itemChanged.connect(self._edited)
        self.views = QListWidget()  # cortes e fachadas (spec/ui 14 §7)
        self.views.setToolTip("Clique duplo abre a vista")
        self.views.itemDoubleClicked.connect(
            lambda item: self.open_view and self.open_view(item.data(Qt.UserRole)))
        self.views.itemClicked.connect(
            lambda item: self.session.select([item.data(Qt.UserRole)]))
        self.open_view = None  # posto pela janela principal
        # Pranchas (spec/ui 15 §5)
        self.sheets = QListWidget()
        self.sheets.setToolTip("Clique duplo abre a prancha")
        self.sheets.itemDoubleClicked.connect(
            lambda item: self.open_sheet and self.open_sheet(item.data(Qt.UserRole)))
        self.sheets.itemClicked.connect(
            lambda item: self.session.select([item.data(Qt.UserRole)]))
        self.open_sheet = None
        self.new_sheet_button = QPushButton("Nova prancha")
        self.new_sheet_button.clicked.connect(self.add_sheet)
        self.delete_sheet_button = QPushButton("Excluir prancha")
        self.delete_sheet_button.clicked.connect(self.delete_sheet)
        # Tabelas (spec/ui 17 §5)
        self.tables = QListWidget()
        self.tables.setToolTip("Clique duplo abre a tabela")
        self.tables.itemDoubleClicked.connect(
            lambda item: self.open_table and self.open_table(item.data(Qt.UserRole)))
        self.tables.itemClicked.connect(
            lambda item: self.session.select([item.data(Qt.UserRole)]))
        self.open_table = None
        self.new_table_button = QPushButton("Nova tabela…")
        self.new_table_button.setMenu(self._templates_menu())
        self.delete_table_button = QPushButton("Excluir tabela")
        self.delete_table_button.clicked.connect(self.delete_table)
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
        layout.addWidget(QLabel("Vistas"))
        layout.addWidget(self.views)
        layout.addWidget(QLabel("Pranchas"))
        layout.addWidget(self.sheets)
        sheet_buttons = QHBoxLayout()
        sheet_buttons.addWidget(self.new_sheet_button)
        sheet_buttons.addWidget(self.delete_sheet_button)
        layout.addLayout(sheet_buttons)
        layout.addWidget(QLabel("Tabelas"))
        layout.addWidget(self.tables)
        table_buttons = QHBoxLayout()
        table_buttons.addWidget(self.new_table_button)
        table_buttons.addWidget(self.delete_table_button)
        layout.addLayout(table_buttons)
        # o nome do pavimento cabe inteiro ao lado das outras três colunas
        self.setMinimumWidth(320)
        self.refresh()

    def refresh(self) -> None:
        self.table.blockSignals(True)
        storeys = list(reversed(self.session.doc.storeys()))
        self.table.setRowCount(len(storeys))
        for row, storey in enumerate(storeys):
            active = storey.GlobalId == self.session.storey_id
            name = QTableWidgetItem(f"{'● ' if active else ''}{storey.Name or ''}")
            name.setData(Qt.UserRole, storey.GlobalId)
            name.setToolTip("Clique para trabalhar neste pavimento (Page Up / Page Down "
                            "trocam pelo teclado); clique duplo renomeia")
            elevation = QTableWidgetItem(fmt(storey.Elevation or 0.0))
            cut = QTableWidgetItem(fmt(storeys_.cut_height(storey)))
            cut.setToolTip("Altura do plano de corte da planta acima da cota; "
                           "vazio volta ao padrão")
            scale = QTableWidgetItem(f"1:{storeys_.scale(storey)}")
            scale.setToolTip("Escala de desenho da planta: "
                             + ", ".join(f"1:{v}" for v in storeys_.SCALES))
            for item in (elevation, cut, scale):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if active:
                font = name.font()
                font.setBold(True)
                for item in (name, elevation, cut, scale):
                    item.setFont(font)
                self.table.selectRow(row)
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, elevation)
            self.table.setItem(row, 2, cut)
            self.table.setItem(row, 3, scale)
        self.delete_button.setEnabled(len(storeys) > 1)
        self.table.blockSignals(False)
        from brasbim.core.drawings import views as views_

        self.views.clear()
        for view in views_.all_views(self.session.doc):
            item = QListWidgetItem(views_.read_state(view)["name"] or view.GlobalId)
            item.setData(Qt.UserRole, view.GlobalId)
            self.views.addItem(item)
        from brasbim.core.drawings import sheets as sheets_

        self.sheets.clear()
        for sheet in sheets_.all_sheets(self.session.doc):
            state = sheets_.read_state(sheet)
            text = f"{state['number']} · {state['title']}" if state["title"] \
                else state["number"]
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, sheet.GlobalId)
            self.sheets.addItem(item)
        self.delete_sheet_button.setEnabled(self.sheets.count() > 0)
        self.tables.clear()
        for table in tables_.all_tables(self.session.doc):
            item = QListWidgetItem(tables_.read_state(table)["name"] or table.GlobalId)
            item.setData(Qt.UserRole, table.GlobalId)
            self.tables.addItem(item)
        self.delete_table_button.setEnabled(self.tables.count() > 0)

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
        elif item.column() == 3:
            self.set_scale(storey, text)
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

    def set_scale(self, storey, text: str) -> None:
        """Escala da planta do pavimento (spec/ui 13 §2): "1:100" ou "100"."""
        try:
            value = int(text.replace(" ", "").removeprefix("1:"))
        except ValueError:
            self.session.message(f"escala inválida: {text!r}", "recusa")
            return
        if value != storeys_.scale(storey):
            doc = self.session.doc
            self.session.run(lambda: cmd.edit_storey(doc, storey, scale=value))

    def add_sheet(self) -> None:
        from brasbim.core.drawings import sheets as sheets_

        doc = self.session.doc
        tx = sheets_.create_sheet(doc)
        if self.session.run(tx) and self.open_sheet:
            self.open_sheet(tx.ops[0].id)

    def delete_sheet(self) -> None:
        from brasbim.core.drawings import sheets as sheets_

        item = self.sheets.currentItem()
        if item is not None:
            doc, gid = self.session.doc, item.data(Qt.UserRole)
            self.session.run(lambda: sheets_.delete_sheet(doc, gid))

    def _templates_menu(self) -> QMenu:
        """Modelos prontos (§3.3); "Em branco" pede a categoria."""
        menu = QMenu(self)
        for key, (label, _) in tables_.TEMPLATES.items():
            if key == "blank":
                continue
            menu.addAction(label, lambda k=key: self.add_table(k))
        blank = menu.addMenu("Em branco")
        for key, category in tables_.CATEGORIES.items():
            blank.addAction(category.label, lambda c=key: self.add_table("blank", c))
        return menu

    def add_table(self, template: str, category: str = "walls") -> str | None:
        doc = self.session.doc
        tx = tables_.create_table(doc, template, category)
        if not self.session.run(tx):
            return None
        if self.open_table:
            for op in reversed(tx.ops):  # a primeira fica à frente
                self.open_table(op.id)
        return tx.ops[0].id

    def delete_table(self) -> None:
        item = self.tables.currentItem()
        if item is not None:
            doc, gid = self.session.doc, item.data(Qt.UserRole)
            self.session.run(lambda: tables_.delete_table(doc, gid))

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
