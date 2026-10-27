# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel Biblioteca de objetos (``spec/elementos/objeto-parametrico.md`` §4.1 a §4.3).

Árvore: categoria › pasta (subcategoria) › objeto › tipos, com miniatura em planta ou 3D.
Busca pelo nome do objeto e do tipo. Clique duplo num tipo carrega o tipo (se ainda não
estiver no projeto) e ativa a ferramenta Objeto com ele; *Carregar no projeto* traz os
tipos marcados sem inserir nada. As pastas do usuário ficam nas preferências.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.objects import definition as od
from brasbim.core.objects import library
from brasbim.core.objects import types as ot
from brasbim.ui import object_preview, theme
from brasbim.ui.icons import icon

THUMB = 48
FOLDERS_KEY = "biblioteca/pastas"
FOLDER_LABELS = {"mobiliario": "Mobiliário", "loucas": "Louças e metais",
                 "eletrodomesticos": "Eletrodomésticos", "vegetacao": "Vegetação",
                 "quarto": "Quarto", "sala": "Sala", "jantar": "Jantar", "cozinha": "Cozinha",
                 "escritorio": "Escritório", "banheiro": "Banheiro",
                 "area-de-servico": "Área de serviço"}


def _settings() -> QSettings:
    return QSettings(QSettings.defaultFormat(), QSettings.UserScope, "BrasBim", "BrasBim")


def user_folders() -> list[str]:
    value = _settings().value(FOLDERS_KEY) or []
    if isinstance(value, str):
        value = [value]
    return [str(v) for v in value if v]


def set_user_folders(folders: list[str]) -> None:
    _settings().setValue(FOLDERS_KEY, list(folders))


def make_index() -> library.Index:
    return library.Index([library.builtin_folder(), *user_folders()])


def _label(part: str) -> str:
    return FOLDER_LABELS.get(part, part.replace("-", " ").capitalize())


def measures(entry: library.Entry) -> str:
    """Medidas do tipo na lista ("1,38 × 1,88 × 1,00")."""
    try:
        values = od.evaluate(entry.definition, entry.values, entry.defaults)
        box = od.bounds(od.solids(entry.definition, values))
    except Exception:  # noqa: BLE001 - sem medidas quem não se calcula
        return ""
    if box is None:
        return ""
    from brasbim.ui.tools import fmt

    return " × ".join(fmt(v) for v in (box[1] - box[0], box[3] - box[2], box[5] - box[4]))


def _in_project(doc, entry: library.Entry) -> bool:
    t = ot.by_name(doc, entry.name)
    return t is not None and ot.definition_of(t)["object_id"] == entry.object_id


class FoldersDialog(QDialog):
    """Pastas do usuário (§4.1): onde se gravam os objetos novos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pastas da biblioteca")
        layout = QVBoxLayout(self)
        note = QLabel("A biblioteca do BrasBim vem com o programa e só pode ser lida. "
                      "Acrescente pastas suas para gravar e reunir os seus objetos.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.INK_SOFT}")
        layout.addWidget(note)
        self.list = QListWidget()
        self.list.addItems(user_folders())
        layout.addWidget(self.list)
        row = QHBoxLayout()
        add, remove = QPushButton("Acrescentar…"), QPushButton("Tirar")
        add.clicked.connect(self._add)
        remove.clicked.connect(lambda: self.list.takeItem(self.list.currentRow()))
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pasta da biblioteca")
        if folder:
            self.list.addItem(folder)

    def folders(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]


MIME = "application/x-brasbim-objeto"  # arrastar da biblioteca para a planta


def entry_key(entry: library.Entry) -> str:
    return f"{entry.object_id}|{entry.name}"


def find_entry(index: library.Index, key: str) -> library.Entry | None:
    return next((e for e in index.entries() if entry_key(e) == key), None)


class _Tree(QTreeWidget):
    """Árvore que arrasta o tipo escolhido (pente fino, 2026-10-27)."""

    def mimeData(self, items):
        entries = [i.data(0, Qt.UserRole) for i in items if i.data(0, Qt.UserRole) is not None]
        if not entries:
            return None
        data = QMimeData()
        data.setData(MIME, entry_key(entries[0]).encode("utf-8"))
        return data


class LibraryPanel(QWidget):
    """Painel solto, como o das camadas (§4.2)."""

    use_type = Signal(str)  # GlobalId do tipo no projeto: ativar a ferramenta com ele

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.index = make_index()
        self.mode = "3d"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar objeto ou tipo")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search, 1)
        self.mode_buttons = {}
        for mode, icon_name, tip in (("plan", "view_plan", "Miniaturas em planta"),
                                     ("3d", "view_3d", "Miniaturas em 3D")):
            b = QToolButton()
            b.setIcon(icon(icon_name))
            b.setCheckable(True)
            b.setChecked(mode == self.mode)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, m=mode: self.set_mode(m))
            top.addWidget(b)
            self.mode_buttons[mode] = b
        folders = QToolButton()
        folders.setIcon(icon("folder"))
        folders.setToolTip("Pastas da biblioteca…")
        folders.clicked.connect(self.edit_folders)
        top.addWidget(folders)
        layout.addLayout(top)
        self.tree = _Tree()
        self.tree.setDragEnabled(True)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(THUMB, THUMB))
        self.tree.setIndentation(14)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self._double)
        self.tree.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.tree, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color: {theme.INK_SOFT}")
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.load_button = QPushButton("Carregar no projeto")
        self.load_button.setToolTip("Traz os tipos marcados para o projeto, sem inserir")
        self.load_button.clicked.connect(self.load_selected)
        self.update_button = QPushButton("Atualizar no projeto")
        self.update_button.setToolTip("Troca a definição do projeto pela versão nova da "
                                      "biblioteca, mantendo os valores")
        self.update_button.clicked.connect(self.update_selected)
        row.addWidget(self.load_button)
        row.addWidget(self.update_button)
        layout.addLayout(row)
        self.refresh()

    # --- montagem ---------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        for m, b in self.mode_buttons.items():
            b.setChecked(m == mode)
        self.refresh()

    def _resolver(self, entries):
        by_name = {e.name: e.state() for e in entries}
        return by_name.get

    def refresh(self) -> None:
        self.tree.clear()
        entries = self.index.entries()
        resolve = self._resolver(entries)
        doc = self.session.doc
        loaded = {(ot.definition_of(t)["object_id"], t.Name) for t in ot.all_types(doc)}
        updates = library.updates(doc, self.index)
        builtin = library.builtin_folder().resolve()
        roots: dict[str, QTreeWidgetItem] = {}
        folders: dict[tuple, QTreeWidgetItem] = {}
        objects: dict[tuple, QTreeWidgetItem] = {}

        def bold(item):
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)

        for entry in sorted(entries, key=lambda e: (e.category, e.definition["name"], e.name)):
            path = Path(entry.file).resolve()
            mine = not path.is_relative_to(builtin)
            category = ("Minhas pastas" if mine
                        else od.CATEGORIES[entry.category][3])
            root = roots.get(category)
            if root is None:
                root = roots[category] = QTreeWidgetItem(self.tree, [category])
                root.setFlags(Qt.ItemIsEnabled)
                bold(root)
            # biblioteca do BrasBim: categoria › arquivo (Quarto, Sala…); minhas: pasta
            parts = [Path(entry.file).stem] if not mine else [
                Path(entry.file).parent.name, Path(entry.file).stem]
            parent = root
            for k in range(len(parts)):
                key = (category, *parts[:k + 1])
                item = folders.get(key)
                if item is None:
                    item = folders[key] = QTreeWidgetItem(parent, [_label(parts[k])])
                    item.setFlags(Qt.ItemIsEnabled)
                parent = item
            okey = (entry.file, entry.object_id)
            obj = objects.get(okey)
            if obj is None:
                obj = objects[okey] = QTreeWidgetItem(parent, [entry.definition["name"]])
                obj.setIcon(0, object_preview.icon(entry.state(), THUMB * 2, self.mode,
                                                   resolve))
                obj.setFlags(Qt.ItemIsEnabled)
                obj.setToolTip(0, entry.definition.get("description") or "")
                if entry.object_id in updates:
                    obj.setText(0, f"{entry.definition['name']}  · atualização disponível")
                    obj.setForeground(0, QColor(theme.ACCENT))
            item = QTreeWidgetItem(obj, [entry.name])
            size = measures(entry)
            in_project = (entry.object_id, entry.name) in loaded
            item.setText(0, entry.name + (f"   {size}" if size else "")
                         + ("   · no projeto" if in_project else ""))
            if in_project:
                item.setForeground(0, QColor(theme.INK_SOFT))
            item.setData(0, Qt.UserRole, entry)
            item.setToolTip(0, f"{entry.name}\n{Path(entry.file).name}, versão {entry.version}"
                               "\nClique duplo: inserir; vários marcados: Carregar")
        for item in (*roots.values(), *folders.values()):  # os objetos aparecem; os tipos não
            item.setExpanded(True)
        self._filter(self.search.text())
        errors = self.index.errors
        self.status.setText(f"{len(errors)} arquivo(s) não puderam ser lidos" if errors
                            else "Clique duplo num tipo para inserir")
        self._selection_changed()

    def _filter(self, text: str) -> None:
        text = text.strip().casefold()

        def visit(item) -> bool:
            entry = item.data(0, Qt.UserRole)
            if entry is not None:
                show = (not text or text in entry.name.casefold()
                        or text in entry.definition["name"].casefold())
                item.setHidden(not show)
                return show
            shown = False
            for i in range(item.childCount()):
                shown = visit(item.child(i)) or shown
            item.setHidden(not shown)
            if text and shown:
                item.setExpanded(True)
            return shown

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def _selected(self) -> list[library.Entry]:
        return [i.data(0, Qt.UserRole) for i in self.tree.selectedItems()
                if i.data(0, Qt.UserRole) is not None]

    def _selection_changed(self) -> None:
        chosen = self._selected()
        self.load_button.setEnabled(bool(chosen))
        updates = library.updates(self.session.doc, self.index)
        self.update_button.setVisible(any(e.object_id in updates for e in chosen))

    # --- ações ------------------------------------------------------------------------

    def _conflict(self, entry: library.Entry) -> str | None:
        box = QMessageBox(self)
        box.setWindowTitle("Tipo já está no projeto")
        box.setText(f"O tipo {entry.name} já está no projeto.")
        keep = box.addButton("Manter o do projeto", QMessageBox.RejectRole)
        replace = box.addButton("Substituir pelo da biblioteca", QMessageBox.AcceptRole)
        new = box.addButton("Carregar como novo tipo", QMessageBox.ActionRole)
        box.exec()
        clicked = box.clickedButton()
        return {keep: "keep", replace: "replace", new: "new"}.get(clicked)

    def load(self, wanted: list[library.Entry], ask: bool = True) -> list[str]:
        """Carrega e devolve os GlobalIds dos tipos pedidos no projeto."""
        doc = self.session.doc
        entries = self.index.entries()
        present = [e for e in wanted if _in_project(doc, e)]
        conflict = "keep"
        if present and ask:
            conflict = self._conflict(present[0]) or "keep"
        tx = library.load(doc, entries, wanted, conflict)
        if tx.ops:
            self.session.run(tx)
        out = []
        for e in wanted:
            name = e.name
            if conflict == "new":
                made = [o.data["name"] for o in tx.ops if o.op == "object_type.create"
                        and o.data["definition"]["object_id"] == e.object_id]
                name = next((n for n in made if n.startswith(e.name)), e.name)
            t = ot.by_name(doc, name)
            if t is not None:
                out.append(t.GlobalId)
        self.refresh()
        return out

    def load_selected(self) -> None:
        chosen = self._selected()
        if chosen:
            self.load(chosen)

    def update_selected(self) -> None:
        updates = library.updates(self.session.doc, self.index)
        for oid in dict.fromkeys(e.object_id for e in self._selected()):
            if oid in updates:
                self.session.run(lambda e=updates[oid]: library.update_from(
                    self.session.doc, e))
        self.refresh()

    def _double(self, item, _column=0) -> None:
        entry = item.data(0, Qt.UserRole)
        if entry is None:
            return
        found = self.load([entry], ask=False)
        if found:
            self.use_type.emit(found[0])

    def load_key(self, key: str) -> str | None:
        """Tipo arrastado (``entry_key``) carregado no projeto; devolve o GlobalId."""
        entry = find_entry(self.index, key)
        found = self.load([entry], ask=False) if entry is not None else []
        return found[0] if found else None

    def edit_folders(self) -> None:
        dialog = FoldersDialog(self)
        if dialog.exec() == QDialog.Accepted:
            set_user_folders(dialog.folders())
            self.index = make_index()
            self.refresh()
