# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Projeto: tabela de pavimentos (``spec/ui/02-edicao.md`` §7), vistas, pranchas e
tabelas de quantitativos (spec/ui 17 §5).

Um clique numa linha torna o pavimento ativo; clique duplo numa célula edita o nome, a
cota ou o plano de corte (``storey.edit``; spec/ui 06 §3.1, vazio = padrão); os botões
criam e excluem pavimentos.
"""

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import storeys as storeys_
from brasbim.core.quantities import tables as tables_
from brasbim.core.walls import commands as cmd
from brasbim.ui.icons import icon
from brasbim.ui.saved_views_ui import SavedViewList
from brasbim.ui.tools import fmt, parse_number

# Grupos da árvore de cortes e fachadas (spec/ui 32 §2): tipo da vista → (título, ícone)
VIEW_GROUPS = {"section": ("Cortes", "section"), "elevation": ("Fachadas", "elevation")}
# Ícone da vista salva pelo que ela mostra (spec/ui 32 §2)
SAVED_ICONS = {"plan": "view_plan", "3d": "view_3d", "section": "section"}

NEW_STOREY_HEIGHT = 2.80  # cota do pavimento novo: a maior + 2,80 m (§7)


@cache
def tree_icon(name: str) -> QIcon:
    """Ícone de item que abre e fecha na árvore: a árvore desenha o item aberto no estado
    "ligado", que nos ícones do tema é a cor sobre o destaque (sumiria no fundo)."""
    base, out = icon(name), QIcon()
    for size in (16, 24, 32):
        pixmap = base.pixmap(size, QIcon.Normal, QIcon.Off)
        out.addPixmap(pixmap, QIcon.Normal, QIcon.Off)
        out.addPixmap(pixmap, QIcon.Normal, QIcon.On)
    return out


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
        # Cortes e fachadas (spec/ui 14 §7), em grupos com ícone (spec/ui 32 §2)
        self.views = QTreeWidget()
        self.views.setHeaderHidden(True)
        self.views.setIndentation(12)
        self.views.setToolTip("Clique duplo (ou Enter) abre a vista")
        self.views.itemDoubleClicked.connect(lambda item, _c=0: self._open_view_item(item))
        self.views.itemActivated.connect(lambda item, _c=0: self._open_view_item(item))
        self.views.itemClicked.connect(self._select_view_item)
        self.open_view = None  # posto pela janela principal
        # Vistas salvas (spec/ui 25 §4): clique duplo abre; arrastar leva à prancha
        self.saved = SavedViewList()
        self.saved.setToolTip("Clique duplo abre a vista; arraste para uma prancha; botão "
                              "direito: ações")
        self.saved.itemDoubleClicked.connect(
            lambda item: self.open_saved_view and self.open_saved_view(item.data(Qt.UserRole)))
        self.saved.setContextMenuPolicy(Qt.CustomContextMenu)
        self.saved.customContextMenuRequested.connect(self._saved_menu_at)
        self.open_saved_view = None  # postos pela janela principal
        self.update_saved_view = None
        self.save_view = None
        self.save_view_button = QToolButton()  # spec/ui 25 §3: no canto das abas de vistas
        self.save_view_button.setIcon(icon("save_view"))
        self.save_view_button.setText("Salvar vista")
        self.save_view_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.save_view_button.setToolTip("Salvar vista (Ctrl+Alt+S): guarda a escala, as "
                                         "camadas e as opções da vista à frente")
        self.save_view_button.setAutoRaise(True)
        self.save_view_button.clicked.connect(lambda: self.save_view and self.save_view())
        # Pranchas (spec/ui 15 §5)
        # Pranchas com os desenhos postos nelas (spec/ui 32 §2): clique duplo na prancha a
        # abre; num desenho, abre a origem dele (planta, corte ou vista salva)
        self.sheets = QTreeWidget()
        self.sheets.setHeaderHidden(True)
        self.sheets.setIndentation(12)
        self.sheets.setToolTip("Clique duplo abre a prancha; num desenho, abre a origem dele")
        self.sheets.itemDoubleClicked.connect(lambda item, _c=0: self._open_sheet_item(item))
        self.sheets.itemActivated.connect(lambda item, _c=0: self._open_sheet_item(item))
        self.sheets.itemClicked.connect(self._select_sheet_item)
        self.open_sheet = None
        self.open_plan = None  # posto pela janela principal: planta do pavimento à frente
        # Folhas mestras (spec/ui 26 §4)
        self.masters = QListWidget()
        self.masters.setToolTip("Clique duplo abre a folha mestra para editar o carimbo")
        self.masters.itemDoubleClicked.connect(
            lambda item: self.open_master and self.open_master(item.data(Qt.UserRole)))
        self.open_master = None
        self.new_master_button = QPushButton("Nova")
        self.new_master_button.setMenu(self._new_master_menu())
        self.duplicate_master_button = QPushButton("Duplicar")
        self.duplicate_master_button.clicked.connect(self.duplicate_master)
        self.delete_master_button = QPushButton("Excluir")
        self.delete_master_button.clicked.connect(self.delete_master)
        self.new_sheet_button = QPushButton("Nova prancha")
        self.new_sheet_button.clicked.connect(lambda: self.add_sheet())
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
        self.new_table_button = QPushButton("Nova tabela")
        self.new_table_button.setMenu(self._templates_menu())
        self.delete_table_button = QPushButton("Excluir tabela")
        self.delete_table_button.clicked.connect(self.delete_table)
        # Objetos paramétricos (objeto-parametrico.md §5.4)
        self.objects = QTreeWidget()
        self.objects.setHeaderHidden(True)
        self.objects.setIconSize(QSize(28, 28))
        self.objects.setIndentation(12)
        self.objects.setToolTip("Clique duplo num tipo: inserir; botão direito: ações")
        self.objects.setContextMenuPolicy(Qt.CustomContextMenu)
        self.objects.customContextMenuRequested.connect(
            lambda pos: self._objects_menu().exec(self.objects.viewport().mapToGlobal(pos)))
        self.objects.itemDoubleClicked.connect(self._object_double)
        self.objects_button = QPushButton("Ações do objeto")
        self.objects_button.clicked.connect(
            lambda: self._objects_menu().exec(self.objects_button.mapToGlobal(
                self.objects_button.rect().bottomLeft())))
        self.library_button = QPushButton("Biblioteca")
        self.library_button.clicked.connect(lambda: self.open_library and self.open_library())
        self.open_library = None  # postos pela janela principal
        self.use_object_type = None
        self.edit_object_type = None
        self.edit_object = None
        self.new_object = None
        self.save_to_library = None
        self.library_index = None
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
        self.view_tabs = QTabWidget()  # vistas salvas e cortes num lugar só (spec/ui 25 §4)
        self.view_tabs.setDocumentMode(True)
        self.view_tabs.addTab(self.saved, "Vistas salvas")
        self.view_tabs.addTab(self.views, "Cortes e fachadas")
        self.view_tabs.setCornerWidget(self.save_view_button, Qt.TopRightCorner)
        layout.addWidget(self.view_tabs)
        self.sheet_tabs = QTabWidget()  # pranchas e folhas mestras (spec/ui 26 §4)
        self.sheet_tabs.setDocumentMode(True)
        for title, listing, buttons in (
                ("Pranchas", self.sheets, (self.new_sheet_button, self.delete_sheet_button)),
                ("Folhas mestras", self.masters,
                 (self.new_master_button, self.duplicate_master_button,
                  self.delete_master_button))):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 2, 0, 0)
            page_layout.setSpacing(2)
            page_layout.addWidget(listing)
            row = QHBoxLayout()
            for button in buttons:
                row.addWidget(button)
            page_layout.addLayout(row)
            self.sheet_tabs.addTab(page, title)
        layout.addWidget(self.sheet_tabs)
        layout.addWidget(QLabel("Tabelas"))
        layout.addWidget(self.tables)
        table_buttons = QHBoxLayout()
        table_buttons.addWidget(self.new_table_button)
        table_buttons.addWidget(self.delete_table_button)
        layout.addLayout(table_buttons)
        layout.addWidget(QLabel("Objetos"))
        layout.addWidget(self.objects)
        object_buttons = QHBoxLayout()
        object_buttons.addWidget(self.objects_button)
        object_buttons.addWidget(self.library_button)
        layout.addLayout(object_buttons)
        # listas baixas no mínimo: o painel não empurra os outros (as listas crescem juntas)
        for widget in (self.saved, self.views, self.sheets, self.masters, self.tables,
                       self.objects):
            widget.setMinimumHeight(40)
        self.table.setMinimumHeight(80)
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

        closed = {self.views.topLevelItem(i).data(0, Qt.UserRole + 1)
                  for i in range(self.views.topLevelItemCount())
                  if not self.views.topLevelItem(i).isExpanded()}
        self.views.clear()
        groups = {}
        for kind, (title, name) in VIEW_GROUPS.items():
            group = QTreeWidgetItem([title])
            group.setIcon(0, tree_icon(name))
            group.setData(0, Qt.UserRole + 1, kind)
            group.setFlags(Qt.ItemIsEnabled)
            groups[kind] = group
        for view in views_.all_views(self.session.doc):
            state = views_.read_state(view)
            group = groups[state["kind"] if state["kind"] in groups else "section"]
            item = QTreeWidgetItem(group, [state["name"] or view.GlobalId])
            item.setIcon(0, icon(VIEW_GROUPS[group.data(0, Qt.UserRole + 1)][1]))
            item.setData(0, Qt.UserRole, view.GlobalId)
        for kind, group in groups.items():
            if group.childCount():
                group.setText(0, f"{VIEW_GROUPS[kind][0]} ({group.childCount()})")
                self.views.addTopLevelItem(group)
                group.setExpanded(kind not in closed)
        from brasbim.core.drawings import saved_views as saved_

        self.saved.clear()
        for entity in saved_.all_saved_views(self.session.doc):
            state = saved_.read_state(entity)
            item = QListWidgetItem(state["name"])
            item.setData(Qt.UserRole, entity.GlobalId)
            item.setIcon(icon(SAVED_ICONS.get(state["kind"], "save_view")))
            item.setToolTip(saved_.KIND_LABEL[state["kind"]])
            self.saved.addItem(item)
        from brasbim.core.drawings import sheets as sheets_

        expanded = {self.sheets.topLevelItem(i).data(0, Qt.UserRole)
                    for i in range(self.sheets.topLevelItemCount())
                    if self.sheets.topLevelItem(i).isExpanded()}
        self.sheets.clear()
        for sheet in sheets_.all_sheets(self.session.doc):
            state = sheets_.read_state(sheet)
            text = f"{state['number']} · {state['title']}" if state["title"] \
                else state["number"]
            item = QTreeWidgetItem(self.sheets, [text])
            item.setIcon(0, tree_icon("sheet"))
            item.setData(0, Qt.UserRole, sheet.GlobalId)
            for placed in state["views"]:
                source = self._placed(placed)
                if source is not None:
                    child = QTreeWidgetItem(item, [source[2]])
                    child.setIcon(0, icon(source[3]))
                    child.setData(0, Qt.UserRole + 2, source[:2])
            item.setExpanded(sheet.GlobalId in expanded)
        self.delete_sheet_button.setEnabled(self.sheets.topLevelItemCount() > 0)
        from brasbim.core.drawings import masters as masters_

        self.masters.clear()
        for entity in masters_.all_masters(self.session.doc):
            state = masters_.read_state(entity)
            item = QListWidgetItem(icon("master"),
                                   f"{state['name']} · {masters_.describe(state)}")
            item.setData(Qt.UserRole, entity.GlobalId)
            self.masters.addItem(item)
        for button in (self.duplicate_master_button, self.delete_master_button):
            button.setEnabled(self.masters.count() > 0)
        self.tables.clear()
        for table in tables_.all_tables(self.session.doc):
            item = QListWidgetItem(icon("table"),
                                   tables_.read_state(table)["name"] or table.GlobalId)
            item.setData(Qt.UserRole, table.GlobalId)
            self.tables.addItem(item)
        self.delete_table_button.setEnabled(self.tables.count() > 0)
        self._refresh_objects()

    def _placed(self, placed: dict) -> tuple[str, str, str, str] | None:
        """(tipo, GlobalId da origem, nome, ícone) do desenho posto na prancha; ``None`` se
        a origem não existe mais."""
        from brasbim.core.drawings import saved_views as saved_
        from brasbim.core.drawings import views as views_

        doc = self.session.doc
        kind = placed.get("kind")
        gid = placed.get(kind) if kind != "plan" else placed.get("storey")
        entity = doc.find(gid) if gid else None
        if entity is None:
            return None
        if kind == "plan":
            return "plan", gid, f"Planta · {entity.Name or ''}", "view_plan"
        if kind == "view":
            state = views_.read_state(entity)
            return "view", gid, state["name"] or gid, VIEW_GROUPS.get(
                state["kind"], VIEW_GROUPS["section"])[1]
        if kind == "saved":
            state = saved_.read_state(entity)
            return "saved", gid, state["name"], SAVED_ICONS.get(state["kind"], "save_view")
        return None

    def _open_sheet_item(self, item) -> None:
        gid = item.data(0, Qt.UserRole)
        if gid:
            if self.open_sheet:
                self.open_sheet(gid)
            return
        kind, gid = item.data(0, Qt.UserRole + 2)
        opener = {"plan": self.open_plan, "view": self.open_view,
                  "saved": self.open_saved_view}[kind]
        if opener:
            opener(gid)

    def _select_sheet_item(self, item, _column=0) -> None:
        gid = item.data(0, Qt.UserRole)
        if gid is None:
            kind, gid = item.data(0, Qt.UserRole + 2)
            if kind != "view":  # pavimento e vista salva não são selecionáveis na planta
                return
        self.session.select([gid])

    def view_ids(self) -> list[str]:
        """Cortes e fachadas da árvore, na ordem mostrada."""
        out = []
        for i in range(self.views.topLevelItemCount()):
            group = self.views.topLevelItem(i)
            out += [group.child(j).data(0, Qt.UserRole) for j in range(group.childCount())]
        return out

    def _open_view_item(self, item) -> None:
        gid = item.data(0, Qt.UserRole)
        if gid and self.open_view:
            self.open_view(gid)

    def _select_view_item(self, item, _column=0) -> None:
        gid = item.data(0, Qt.UserRole)
        if gid:
            self.session.select([gid])

    # --- objetos paramétricos ---------------------------------------------------------------

    def _refresh_objects(self) -> None:
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import definition as od
        from brasbim.core.objects import library
        from brasbim.core.objects import types as ot
        from brasbim.ui import object_preview
        from brasbim.ui.object_widgets import resolver_for

        doc = self.session.doc
        closed = {self.objects.topLevelItem(i).text(0)
                  for i in range(self.objects.topLevelItemCount())
                  if not self.objects.topLevelItem(i).isExpanded()}
        self.objects.clear()
        updates = library.updates(doc, self.library_index) if self.library_index else {}
        groups, defs = {}, {}
        resolve = resolver_for(doc)
        for t in ot.all_types(doc):
            state = ot.read(t)
            defn = state["definition"]
            label = od.CATEGORIES[defn["category"]][3]
            group = groups.get(label)
            if group is None:
                group = groups[label] = QTreeWidgetItem(self.objects, [label])
            parent = defs.get(defn["object_id"])
            if parent is None:
                text = defn["name"] + ("  · atualização disponível"
                                       if defn["object_id"] in updates else "")
                parent = defs[defn["object_id"]] = QTreeWidgetItem(group, [text])
                parent.setData(0, Qt.UserRole, ("definition", defn["object_id"]))
                parent.setIcon(0, object_preview.icon(state, 56, "3d", resolve))
            count = len(oc.occurrences(doc, t))
            item = QTreeWidgetItem(parent, [f"{t.Name}  ({count})"])
            item.setData(0, Qt.UserRole, ("type", t.GlobalId))
        for label, group in groups.items():
            group.setExpanded(label not in closed)
        if not groups:
            empty = QTreeWidgetItem(self.objects, ["Nenhum: traga da biblioteca"])
            empty.setFlags(Qt.ItemIsEnabled)

    def _object_double(self, item, _column=0) -> None:
        data = item.data(0, Qt.UserRole)
        if data and data[0] == "type" and self.use_object_type:
            self.use_object_type(data[1])

    def _current_object(self):
        from brasbim.core.objects import types as ot

        item = self.objects.currentItem()
        data = item.data(0, Qt.UserRole) if item is not None else None
        if not data:
            return None, None
        if data[0] == "type":
            t = self.session.doc.find(data[1])
            return data[1], ot.definition_of(t)["object_id"] if t is not None else None
        return None, data[1]

    def _objects_menu(self) -> QMenu:
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import library

        doc = self.session.doc
        type_gid, object_id = self._current_object()
        menu = QMenu(self)
        has_type = type_gid is not None
        has_def = object_id is not None

        def add(text, slot, enabled=True):
            action = menu.addAction(text, slot)
            action.setEnabled(bool(enabled))
            return action

        add("Inserir", lambda: self.use_object_type and self.use_object_type(type_gid),
            has_type)
        add("Editar tipo", lambda: self.edit_object_type and self.edit_object_type(type_gid),
            has_type)
        add("Duplicar tipo", lambda: self.session.run(
            lambda: oc.duplicate_type(doc, type_gid)), has_type)
        add("Renomear tipo", lambda: self._rename_type(type_gid), has_type)
        add("Selecionar ocorrências", lambda: self.session.select(
            [e.GlobalId for e in oc.occurrences(doc, type_gid)]), has_type)
        add("Substituir tipo", lambda: self._replace_type(type_gid), has_type)
        add("Excluir tipo", lambda: self._delete_type(type_gid), has_type)
        menu.addSeparator()
        add("Editar objeto", lambda: self.edit_object and self.edit_object(object_id),
            has_def and self.edit_object)
        add("Novo objeto", lambda: self.new_object and self.new_object(object_id),
            self.new_object)
        updates = library.updates(doc, self.library_index) if self.library_index else {}
        add("Atualizar da biblioteca", lambda: self.session.run(
            lambda: library.update_from(doc, updates[object_id])),
            has_def and object_id in updates)
        add("Gravar na biblioteca", lambda: self.save_to_library and self.save_to_library(
            object_id), has_def and self.save_to_library)
        add("Excluir objeto", lambda: self._delete_definition(object_id), has_def)
        return menu

    def _rename_type(self, gid) -> None:
        from brasbim.core.objects import commands as oc

        doc = self.session.doc
        t = doc.get(gid)
        name, ok = QInputDialog.getText(self, "Renomear tipo", "Nome:", text=t.Name or "")
        if ok and name.strip():
            self.session.run(lambda: oc.edit_type(doc, gid, name=name.strip()))

    def _delete_type(self, gid) -> None:
        from brasbim.core.objects import commands as oc
        from brasbim.ui.object_dialogs import ask_replacement

        doc = self.session.doc
        t = doc.get(gid)
        replacement = None
        if oc.occurrences(doc, t):
            replacement = ask_replacement(self, doc, t)
            if replacement is None:
                self.session.message("escolha o tipo substituto (ou exclua os objetos antes)",
                                     "recusa")
                return
        self.session.run(lambda: oc.delete_type(doc, gid, replacement))

    def _replace_type(self, gid) -> None:
        from brasbim.core.objects import commands as oc
        from brasbim.ui.object_dialogs import ask_replacement

        doc = self.session.doc
        target = ask_replacement(self, doc, doc.get(gid))
        if target is not None:
            self.session.run(lambda: oc.replace_all(doc, gid, target))

    def _delete_definition(self, object_id) -> None:
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import types as ot

        doc = self.session.doc
        used = [e for t in ot.types_of_definition(doc, object_id)
                for e in oc.occurrences(doc, t)]
        if used:
            self.session.message(f"{len(used)} objeto(s) usam este objeto: exclua-os ou troque "
                                 "o tipo antes", "recusa")
            return
        self.session.run(lambda: oc.delete_definition(doc, object_id))

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

    # --- vistas salvas (spec/ui 25 §4) ---------------------------------------------------

    def _saved_menu_at(self, pos) -> None:
        item = self.saved.itemAt(pos)
        if item is not None:
            self.saved_menu(item.data(Qt.UserRole)).exec(self.saved.viewport().mapToGlobal(pos))

    def saved_menu(self, gid: str) -> QMenu:
        from brasbim.core.drawings import saved_views as saved_
        from brasbim.core.drawings import sheets as sheets_

        doc = self.session.doc
        menu = QMenu(self)
        menu.addAction("Abrir", lambda: self.open_saved_view and self.open_saved_view(gid))
        menu.addAction("Atualizar com a janela",
                       lambda: self.update_saved_view and self.update_saved_view(gid))
        menu.addAction("Renomear", lambda: self.rename_saved_view(gid))
        sub = menu.addMenu("Pôr na prancha")
        for sheet in sheets_.all_sheets(doc):
            state = sheets_.read_state(sheet)
            text = f"{state['number']} · {state['title']}" if state["title"]                 else f"Prancha {state['number']}"
            sub.addAction(text, lambda s=sheet.GlobalId: self.put_on_sheet(gid, s))
        if sub.isEmpty():
            sub.addAction("(nenhuma prancha)").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Excluir", lambda: self.session.run(
            lambda: saved_.delete_saved_view(doc, gid)))
        return menu

    def put_on_sheet(self, gid: str, sheet_gid: str) -> bool:
        from brasbim.core.drawings import sheets as sheets_

        doc = self.session.doc
        done = self.session.run(lambda: sheets_.add_to_sheet(
            doc, sheet_gid, {"kind": "saved", "saved": gid}))
        if done and self.open_sheet:
            self.open_sheet(sheet_gid)
        return done

    def rename_saved_view(self, gid: str, name: str | None = None) -> None:
        from PySide6.QtWidgets import QInputDialog

        from brasbim.core.drawings import saved_views as saved_

        doc = self.session.doc
        current = saved_.read_state(doc.get(gid))["name"]
        if name is None:
            name, ok = QInputDialog.getText(self, "Renomear vista salva", "Nome",
                                            text=current)
            if not ok:
                return
        self.session.run(lambda: saved_.edit_saved_view(doc, gid, "Renomear vista salva",
                                                        name=name))

    def add_sheet(self, choice: dict | None = None) -> str | None:
        """Nova prancha… (spec/ui 26 §4): título e folha mestra; com ``choice`` (argumentos
        de ``create_sheet``) não pergunta."""
        from brasbim.core.drawings import sheets as sheets_
        from brasbim.ui.master_editor import NewSheetDialog

        doc = self.session.doc
        if choice is None:
            dialog = NewSheetDialog(doc, self)
            if dialog.exec() != QDialog.Accepted:
                return None
            choice = dialog.choice()
        tx = None

        def build():
            nonlocal tx
            tx = sheets_.create_sheet(doc, **choice)
            return tx

        if not self.session.run(build):
            return None
        if self.open_sheet:
            self.open_sheet(tx.ops[0].id)
        return tx.ops[0].id

    # --- folhas mestras (spec/ui 26 §4) -----------------------------------------------------

    def _new_master_menu(self) -> QMenu:
        from brasbim.core.drawings import masters as masters_

        menu = QMenu(self)
        for paper in masters_.FORMATS:
            for text, orientation in (("horizontal", "landscape"), ("vertical", "portrait")):
                menu.addAction(f"{paper} {text}",
                               lambda f=paper, o=orientation: self.add_master(f, o))
        menu.addSeparator()
        menu.addAction("Personalizado (500 × 700 mm)",
                       lambda: self.add_master(masters_.CUSTOM, "landscape", [500, 700]))
        return menu

    def add_master(self, fmt: str = "A3", orientation: str = "landscape",
                   size=None) -> str | None:
        from brasbim.core.drawings import masters as masters_

        doc = self.session.doc
        tx = None

        def build():
            nonlocal tx
            tx = masters_.create_master(doc, "", fmt, orientation, size)
            return tx

        if not self.session.run(build):
            return None
        self.sheet_tabs.setCurrentIndex(1)
        if self.open_master:
            self.open_master(tx.ops[0].id)
        return tx.ops[0].id

    def _current_master(self) -> str | None:
        item = self.masters.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def duplicate_master(self) -> None:
        from brasbim.core.drawings import masters as masters_

        gid = self._current_master()
        if gid is not None:
            doc = self.session.doc
            self.session.run(lambda: masters_.duplicate_master(doc, gid))

    def delete_master(self) -> None:
        from brasbim.core.drawings import masters as masters_

        gid = self._current_master()
        if gid is not None:
            doc = self.session.doc
            self.session.run(lambda: masters_.delete_master(doc, gid))

    def delete_sheet(self) -> None:
        from brasbim.core.drawings import sheets as sheets_

        item = self.sheets.currentItem()
        while item is not None and item.parent() is not None:
            item = item.parent()
        if item is not None:
            doc, gid = self.session.doc, item.data(0, Qt.UserRole)
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
            if category.summary:
                continue
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
