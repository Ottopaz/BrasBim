# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Camadas (spec/ui 18 §7): grupos e camadas em árvore, com olho (visível),
cadeado (bloqueada) e número de elementos; busca; combinações no alto.

Olho, cadeado, isolar e aplicar combinação mudam só a exibição (``Session.set_display``,
fora do desfazer, §5.1). Criar, renomear, excluir, arrastar e as combinações em si são
transações.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import display_layers as dl
from brasbim.core.ops import Transaction
from brasbim.ui import theme
from brasbim.ui.icons import icon

NAME, EYE, LOCK, COUNT = range(4)
GROUP, LAYER = "group", "layer"
CHANGED = "(alterada)"


class _Tree(QTreeWidget):
    """Árvore com arrastar dentro dela: ao soltar, o painel lê a ordem nova."""

    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def dropEvent(self, event):
        dragged = self.currentItem()
        target = self.itemAt(event.position().toPoint())
        kind = dragged.data(0, Qt.UserRole) if dragged else None
        target_kind = target.data(0, Qt.UserRole) if target else None
        # Grupo não entra em grupo; camada não entra em camada (um nível só, §3).
        position = self.dropIndicatorPosition()
        on_item = position == QAbstractItemView.OnItem
        if kind is None or (kind[0] == GROUP and target is not None
                            and (target.parent() is not None or on_item)) \
                or (kind[0] == LAYER and on_item and target_kind and target_kind[0] == LAYER) \
                or (kind[0] == LAYER and kind[1] == dl.NONE):
            event.ignore()
            return
        super().dropEvent(event)
        self.panel.tree_reordered()


class LayersPanel(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._isolated_from: dl.Display | None = None  # Alt + clique (§7)
        self._filling = False

        self.combination = QComboBox()
        self.combination.setToolTip("Combinação de camadas: escolher aplica os estados")
        self.combination.activated.connect(self._apply_combination)
        self.combination_menu = QToolButton()
        self.combination_menu.setText("…")
        self.combination_menu.setToolTip("Salvar, atualizar, renomear ou excluir a combinação")
        self.combination_menu.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.combination_menu)
        menu.addAction("Salvar como…", self.save_combination_as)
        self.update_action = menu.addAction("Atualizar combinação", self.update_combination)
        self.rename_action = menu.addAction("Renomear combinação…", self.rename_combination)
        self.delete_action = menu.addAction("Excluir combinação", self.delete_combination)
        self.combination_menu.setMenu(menu)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar camada")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)

        self.tree = _Tree(self)
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Camada", "", "", "Nº"])
        header = self.tree.header()
        header.setSectionResizeMode(NAME, QHeaderView.Stretch)
        for column in (EYE, LOCK, COUNT):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.tree.setIconSize(QSize(16, 16))
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.itemChanged.connect(self._renamed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        for name, tip, slot in (("layer_new", "Nova camada", self.new_layer),
                                ("layer_group", "Novo grupo", self.new_group),
                                ("delete", "Excluir camada ou grupo", self.delete_current),
                                ("layers_all", "Mostrar todas", self.show_all)):
            button = QToolButton()
            button.setIcon(icon(name))
            button.setToolTip(tip)
            button.setAutoRaise(True)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch(1)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.combination, 1)
        top.addWidget(self.combination_menu)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(top)
        layout.addWidget(self.search)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)
        self.setMinimumWidth(260)
        session.listeners.append(self._on_session)
        self.refresh()

    # --- dados ----------------------------------------------------------------------------

    @property
    def doc(self):
        return self.session.doc

    def _on_session(self, event: str) -> None:
        if event in ("document", "model", "layers"):
            if event == "document":
                self._isolated_from = None
            self.refresh()

    def refresh(self) -> None:
        self._filling = True
        try:
            self._fill_combinations()
            self._fill_tree()
        finally:
            self._filling = False
        self._filter(self.search.text())

    def _fill_combinations(self) -> None:
        config = dl.read_config(self.doc) or dl.empty_config()
        current = dl.matching_combination(self.doc, self.session.display)
        self.combination.clear()
        for comb in config["combinations"]:
            self.combination.addItem(comb["name"], comb["id"])
        if current is None:
            self.combination.insertItem(0, CHANGED, None)
            self.combination.setCurrentIndex(0)
        else:
            self.combination.setCurrentIndex(self.combination.findData(current["id"]))
        for action in (self.update_action, self.rename_action, self.delete_action):
            action.setEnabled(bool(config["combinations"]))

    def _fill_tree(self) -> None:
        expanded = {self.tree.topLevelItem(i).data(0, Qt.UserRole)
                    for i in range(self.tree.topLevelItemCount())
                    if self.tree.topLevelItem(i).isExpanded()}
        first = self.tree.topLevelItemCount() == 0
        current = self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else None
        self.tree.clear()
        config = dl.read_config(self.doc)
        self.setEnabled(config is not None)
        if config is None:
            return
        counts = dl.counts(self.doc)
        display = self.session.display
        for group in config["groups"]:
            item = self._item((GROUP, group["id"]), group["name"])
            visible, locked = dl.group_state(self.doc, display, group["id"])
            self._marks(item, visible, locked)
            total = 0
            for lay in config["layers"]:
                if lay.get("group") == group["id"]:
                    child = self._layer_item(lay["id"], lay["name"], display, counts)
                    item.addChild(child)
                    total += counts.get(lay["id"], 0)
            item.setText(COUNT, str(total) if total else "")
            item.setFlags(item.flags() | Qt.ItemIsDropEnabled)
            self.tree.addTopLevelItem(item)
            item.setExpanded(first or (GROUP, group["id"]) in expanded)
        for lay in config["layers"]:
            if not lay.get("group"):
                self.tree.addTopLevelItem(self._layer_item(lay["id"], lay["name"], display,
                                                           counts))
        none = self._layer_item(dl.NONE, dl.NONE_NAME, display, counts)
        none.setFlags(none.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsDragEnabled)
        none.setForeground(NAME, QColor(theme.INK_SOFT))
        self.tree.addTopLevelItem(none)
        if current is not None:
            found = self._find(current)
            if found is not None:
                self.tree.setCurrentItem(found)

    def _item(self, key, name: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name, "", "", ""])
        item.setData(0, Qt.UserRole, key)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
                      | Qt.ItemIsDragEnabled)
        item.setTextAlignment(COUNT, Qt.AlignRight | Qt.AlignVCenter)
        return item

    def _layer_item(self, layer_id: str, name: str, display, counts) -> QTreeWidgetItem:
        item = self._item((LAYER, layer_id), name)
        visible, locked = display.state(layer_id)
        self._marks(item, visible, locked)
        n = counts.get(layer_id, 0)
        item.setText(COUNT, str(n) if n else "")
        item.setToolTip(COUNT, "Clique duplo seleciona os elementos do pavimento")
        return item

    def _marks(self, item, visible: bool | None, locked: bool | None) -> None:
        item.setIcon(EYE, icon("eye" if visible is not False else "eye_off"))
        item.setIcon(LOCK, icon("lock" if locked is not False else "unlock"))
        mixed = "misto: as camadas do grupo discordam"
        item.setToolTip(EYE, mixed if visible is None else
                        "Visível (Alt + clique: mostrar só esta)" if visible else "Oculta")
        item.setToolTip(LOCK, mixed if locked is None else "Bloqueada" if locked else "Livre")
        if visible is None or locked is None:
            item.setForeground(EYE if visible is None else LOCK, QColor(theme.INK_FAINT))

    def _find(self, key) -> QTreeWidgetItem | None:
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.data(0, Qt.UserRole) == key:
                return top
            for j in range(top.childCount()):
                if top.child(j).data(0, Qt.UserRole) == key:
                    return top.child(j)
        return None

    def _filter(self, text: str) -> None:
        """Busca (§7): só as camadas com o texto; grupos com achados ficam abertos."""
        needle = text.strip().casefold()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.data(0, Qt.UserRole)[0] == GROUP:
                hits = 0
                for j in range(top.childCount()):
                    child = top.child(j)
                    hit = not needle or needle in child.text(NAME).casefold()
                    child.setHidden(not hit)
                    hits += hit
                group_hit = needle and needle in top.text(NAME).casefold()
                if group_hit:
                    for j in range(top.childCount()):
                        top.child(j).setHidden(False)
                top.setHidden(bool(needle) and not hits and not group_hit)
                if needle and (hits or group_hit):
                    top.setExpanded(True)
            else:
                top.setHidden(bool(needle) and needle not in top.text(NAME).casefold())

    def _layers_of(self, key) -> list[str]:
        kind, value = key
        return dl.group_layers(self.doc, value) if kind == GROUP else [value]

    # --- exibição (fora do desfazer) -------------------------------------------------------

    def _clicked(self, item, column) -> None:
        key = item.data(0, Qt.UserRole)
        if column == EYE:
            if QApplication.keyboardModifiers() & Qt.AltModifier:
                self.isolate(key)
            else:
                visible = self._state(key)[0]
                self.set_visible(key, visible is False)
        elif column == LOCK:
            locked = self._state(key)[1]
            self.set_locked(key, locked is not True)

    def _state(self, key) -> tuple[bool | None, bool | None]:
        if key[0] == GROUP:
            return dl.group_state(self.doc, self.session.display, key[1])
        return self.session.display.state(key[1])

    def set_visible(self, key, visible: bool) -> None:
        display = self.session.display
        for layer_id in self._layers_of(key):
            display = display.with_layer(layer_id, visible=visible)
        self._isolated_from = None
        self.session.set_display(display)

    def set_locked(self, key, locked: bool) -> None:
        display = self.session.display
        for layer_id in self._layers_of(key):
            display = display.with_layer(layer_id, locked=locked)
        self.session.set_display(display)

    def isolate(self, key) -> None:
        """Alt + clique no olho: só esta camada (ou grupo); de novo, volta ao anterior."""
        if self._isolated_from is not None:
            previous, self._isolated_from = self._isolated_from, None
            self.session.set_display(previous)
            return
        keep = set(self._layers_of(key))
        every = [x for x in dl.states_of(self.doc, self.session.display)]
        previous = self.session.display
        hidden = frozenset(x for x in every if x not in keep)
        self.session.set_display(dl.Display(hidden, previous.locked))
        self._isolated_from = previous

    def show_all(self) -> None:
        self._isolated_from = None
        self.session.set_display(dl.Display(frozenset(), self.session.display.locked))

    def _apply_combination(self, index: int) -> None:
        comb_id = self.combination.itemData(index)
        comb = dl.combination(self.doc, comb_id) if comb_id else None
        if comb is not None:
            self._isolated_from = None
            self.session.set_display(dl.display_of(comb["states"]))

    # --- transações ------------------------------------------------------------------------

    def _current_combination(self) -> str | None:
        comb_id = self.combination.currentData()
        if comb_id is None:  # "(alterada)": a que o usuário escolheu por último não se sabe
            config = dl.read_config(self.doc) or dl.empty_config()
            names = [c["name"] for c in config["combinations"]]
            if not names:
                return None
            name, ok = QInputDialog.getItem(self, "Combinação", "Qual combinação?", names, 0,
                                            False)
            if not ok:
                return None
            comb_id = next(c["id"] for c in config["combinations"] if c["name"] == name)
        return comb_id

    def save_combination_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Salvar combinação", "Nome da combinação:")
        if ok and name.strip():
            self.session.run(lambda: dl.save_combination(self.doc, name, self.session.display))

    def update_combination(self) -> None:
        comb_id = self._current_combination()
        if comb_id:
            self.session.run(lambda: dl.update_combination(self.doc, comb_id,
                                                           self.session.display))

    def rename_combination(self) -> None:
        comb_id = self._current_combination()
        comb = dl.combination(self.doc, comb_id) if comb_id else None
        if comb is None:
            return
        name, ok = QInputDialog.getText(self, "Renomear combinação", "Nome:", text=comb["name"])
        if ok and name.strip():
            self.session.run(lambda: dl.rename_combination(self.doc, comb_id, name))

    def delete_combination(self) -> None:
        comb_id = self._current_combination()
        if comb_id:
            self.session.run(lambda: dl.delete_combination(self.doc, comb_id))

    def _target_group(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        kind, value = item.data(0, Qt.UserRole)
        if kind == GROUP:
            return value
        parent = item.parent()
        return parent.data(0, Qt.UserRole)[1] if parent is not None else None

    def _free_name(self, base: str, items: list[dict]) -> str:
        taken = {x["name"].casefold() for x in items}
        n = 1
        while f"{base} {n}".casefold() in taken:
            n += 1
        return f"{base} {n}"

    def new_layer(self) -> None:
        config = dl.read_config(self.doc)
        if config is None:
            return
        group = self._target_group()
        tx = dl.create_layer(self.doc, self._free_name("Camada", config["layers"]), group)
        if self.session.run(tx):
            self._edit((LAYER, tx.ops[0].id))

    def new_group(self) -> None:
        config = dl.read_config(self.doc)
        if config is None:
            return
        tx = dl.create_group(self.doc, self._free_name("Grupo", config["groups"]))
        if self.session.run(tx):
            self._edit((GROUP, tx.ops[0].id))

    def _edit(self, key) -> None:
        item = self._find(key)
        if item is not None:
            self.tree.setCurrentItem(item)
            self.tree.editItem(item, NAME)

    def delete_current(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        kind, value = item.data(0, Qt.UserRole)
        if kind == GROUP:
            self.session.run(lambda: dl.delete_group(self.doc, value))
            return
        if value == dl.NONE:
            self.session.message("Sem camada não pode ser excluída", "recusa")
            return
        move_to = None
        if dl.members(self.doc, value):
            choices = [(text, lid) for text, lid in dl.choices(self.doc) if lid != value]
            text, ok = QInputDialog.getItem(
                self, "Excluir camada",
                f"A camada {item.text(NAME)} tem elementos. Para onde eles vão?",
                [t for t, _ in choices], 0, False)
            if not ok:
                return
            move_to = dict(choices)[text]
        self.session.run(lambda: dl.delete_layer(self.doc, value, move_to))

    def _renamed(self, item, column) -> None:
        if self._filling or column != NAME:
            return
        kind, value = item.data(0, Qt.UserRole)
        name = item.text(NAME).strip()
        if kind == GROUP:
            ok = self.session.run(lambda: dl.rename_group(self.doc, value, name))
        else:
            ok = self.session.run(lambda: dl.edit_layer(self.doc, value, name=name))
        if not ok:
            self.refresh()

    def _double_clicked(self, item, column) -> None:
        kind, value = item.data(0, Qt.UserRole)
        if column == COUNT:
            self.select_members(item.data(0, Qt.UserRole))
        elif column == NAME and not (kind == LAYER and value == dl.NONE):
            self.tree.editItem(item, NAME)

    def select_members(self, key) -> None:
        """Seleciona os elementos visíveis da camada (ou grupo) no pavimento atual (§7)."""
        import ifcopenshell.util.element

        storey = self.session.storey
        gids = []
        for layer_id in self._layers_of(key):
            for gid in dl.members(self.doc, layer_id):
                element = self.doc.find(gid)
                container = ifcopenshell.util.element.get_container(element)
                if container is None or container == storey:
                    gids.append(gid)
        self.session.select(gids)

    def tree_reordered(self) -> None:
        """Depois de arrastar: grupo de cada camada e ordem nova, numa transação."""
        config = dl.read_config(self.doc)
        if config is None:
            return
        layers, groups, membership = [], [], {}
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            kind, value = top.data(0, Qt.UserRole)
            if kind == GROUP:
                groups.append(value)
                for j in range(top.childCount()):
                    child = top.child(j).data(0, Qt.UserRole)
                    if child[0] == LAYER:
                        layers.append(child[1])
                        membership[child[1]] = value
            elif value != dl.NONE:
                layers.append(value)
                membership[value] = None
        ops = []
        for lay in config["layers"]:
            if lay["id"] in membership and lay.get("group") != membership[lay["id"]]:
                ops += dl.edit_layer(self.doc, lay["id"], group=membership[lay["id"]]).ops
        if sorted(layers) == sorted(x["id"] for x in config["layers"]) and \
                sorted(groups) == sorted(x["id"] for x in config["groups"]):
            order = dl.reorder(self.doc, layers, groups)
            if order.ops[0].before != order.ops[0].after:
                ops += order.ops
        if ops:
            self.session.run(Transaction("Organizar camadas", ops))
        else:
            self.refresh()

    def _context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        key = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Mostrar só esta", lambda: self.isolate(key))
        menu.addAction("Selecionar os elementos do pavimento", lambda: self.select_members(key))
        if not (key[0] == LAYER and key[1] == dl.NONE):
            menu.addAction("Renomear", lambda: self.tree.editItem(item, NAME))
            menu.addAction("Excluir", self.delete_current)
        if key[0] == LAYER and key[1] != dl.NONE:
            config = dl.read_config(self.doc) or dl.empty_config()
            move = menu.addMenu("Mover para o grupo")
            move.addAction("(sem grupo)", lambda: self.session.run(
                lambda: dl.edit_layer(self.doc, key[1], group=None)))
            for group in config["groups"]:
                move.addAction(group["name"], lambda g=group["id"]: self.session.run(
                    lambda: dl.edit_layer(self.doc, key[1], group=g)))
        menu.exec(self.tree.viewport().mapToGlobal(pos))
