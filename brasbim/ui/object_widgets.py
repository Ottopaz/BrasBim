# SPDX-License-Identifier: GPL-3.0-or-later
"""Peças de interface dos objetos paramétricos (``spec/elementos/objeto-parametrico.md``
§4.4 e §5.1): escolha do tipo com busca e miniaturas, e campos de parâmetro."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QLineEdit,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.objects import definition as od
from brasbim.core.objects import types as ot
from brasbim.ui import object_preview, theme
from brasbim.ui.tools import fmt, parse_number

THUMB = 36


def resolver_for(doc):
    """Tipos aninhados para a prévia: os do projeto, pelo nome."""
    def resolve(name):
        t = ot.by_name(doc, name)
        return ot.read(t) if t is not None else None
    return resolve


class _Popup(QFrame):
    chosen = Signal(object)  # GlobalId do tipo, ou "library"

    def __init__(self, doc, current, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"_Popup {{ background: {theme.FIELD}; border: 1px solid "
                           f"{theme.RULE}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar objeto ou tipo")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(THUMB, THUMB))
        self.tree.setIndentation(12)
        self.tree.setMinimumSize(320, 360)
        layout.addWidget(self.tree)
        more = QPushButton("Mais na biblioteca")
        more.clicked.connect(lambda: self._pick("library"))
        layout.addWidget(more)
        resolve = resolver_for(doc)
        groups: dict[str, QTreeWidgetItem] = {}
        objects: dict[str, QTreeWidgetItem] = {}
        for t in ot.all_types(doc):
            state = ot.read(t)
            defn = state["definition"]
            label = od.CATEGORIES[defn["category"]][3]
            group = groups.get(label)
            if group is None:
                group = groups[label] = QTreeWidgetItem(self.tree, [label])
                group.setFlags(Qt.ItemIsEnabled)
                font = group.font(0)
                font.setBold(True)
                group.setFont(0, font)
            parent_item = objects.get(defn["object_id"])
            if parent_item is None:
                parent_item = objects[defn["object_id"]] = QTreeWidgetItem(group,
                                                                          [defn["name"]])
                parent_item.setFlags(Qt.ItemIsEnabled)
            item = QTreeWidgetItem(parent_item, [t.Name])
            item.setIcon(0, object_preview.icon(state, THUMB * 2, "3d", resolve))
            item.setData(0, Qt.UserRole, t.GlobalId)
            item.setToolTip(0, defn.get("description") or defn["name"])
            if t.GlobalId == current:
                self.tree.setCurrentItem(item)
        self.tree.expandAll()
        if not groups:
            empty = QTreeWidgetItem(self.tree, ["Nenhum objeto no projeto: abra a biblioteca"])
            empty.setFlags(Qt.ItemIsEnabled)
        self.tree.itemActivated.connect(self._activated)
        self.tree.itemClicked.connect(self._activated)
        self.search.textChanged.connect(self._filter)
        self.search.setFocus()

    def _activated(self, item, _column=0):
        gid = item.data(0, Qt.UserRole)
        if gid:
            self._pick(gid)

    def _pick(self, value):
        self.chosen.emit(value)
        self.close()

    def _filter(self, text: str) -> None:
        text = text.strip().casefold()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            any_group = False
            for j in range(group.childCount()):
                obj = group.child(j)
                any_obj = False
                match_obj = text in obj.text(0).casefold()
                for k in range(obj.childCount()):
                    t = obj.child(k)
                    show = not text or match_obj or text in t.text(0).casefold()
                    t.setHidden(not show)
                    any_obj = any_obj or show
                obj.setHidden(not any_obj)
                any_group = any_group or any_obj
            group.setHidden(not any_group)


class TypePicker(QToolButton):
    """Botão com o tipo escolhido; abre a lista dos tipos do projeto com busca (§4.4)."""

    chosen = Signal(object)

    def __init__(self, doc, current: str | None, parent=None):
        super().__init__(parent)
        self.doc, self.current = doc, current
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(22, 22))
        self.setMinimumWidth(190)
        self.setToolTip("Objeto e tipo a inserir (clique para escolher; busca pelo nome)")
        self.clicked.connect(self.open_popup)
        self._show()

    def _show(self) -> None:
        t = self.doc.find(self.current) if self.current else None
        if t is None or not ot.is_object_type(t):
            self.setText("Escolher objeto")
            self.setIcon(object_preview.QIcon())
            return
        state = ot.read(t)
        self.setText(t.Name)
        self.setIcon(object_preview.icon(state, 44, "3d", resolver_for(self.doc)))

    def open_popup(self) -> None:
        popup = _Popup(self.doc, self.current, self)
        popup.chosen.connect(self._picked)
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))
        popup.show()

    def _picked(self, value) -> None:
        if value != "library":
            self.current = value
            self._show()
        self.chosen.emit(value)


def param_widget(p: dict, value, commit, doc=None) -> QWidget:
    """Campo de um parâmetro pelo tipo do valor; ``commit(novo valor)``."""
    kind = p["kind"]
    if kind == "bool":
        box = QCheckBox()
        box.setChecked(bool(value))
        box.toggled.connect(lambda checked: commit(bool(checked)))
        return box
    if kind in ("choice", "material", "object_type"):
        combo = QComboBox()
        if kind == "choice":
            options = list(p.get("options") or [])
        elif kind == "material":
            options = sorted({m.Name for m in doc.ifc.by_type("IfcMaterial")} | {value or ""}
                             - {""}) if doc is not None else [value]
        else:
            accepts = p.get("accepts") or {}
            options = sorted(
                t.Name for t in ot.all_types(doc)
                if (not accepts.get("category")
                    or ot.definition_of(t)["category"] == accepts["category"])
                and (not accepts.get("predefined_type")
                     or t.PredefinedType == accepts["predefined_type"])) if doc else []
            if value and value not in options:
                options.append(value)
        for option in options:
            combo.addItem(option, option)
        combo.setCurrentIndex(max(0, combo.findData(value)))
        combo.currentIndexChanged.connect(lambda i: commit(combo.itemData(i)))
        return combo
    field = QLineEdit("" if value is None else (
        fmt(value) if od.KINDS[kind] == od.NUMBER and kind != "integer" else str(value)))
    original = field.text()

    def done():
        text = field.text().strip()
        if text == original:
            return
        if od.KINDS[kind] != od.NUMBER:
            commit(text)
            return
        try:
            number = parse_number(text)
        except ValueError:
            field.setStyleSheet(f"QLineEdit {{ background: {theme.ERROR_SOFT}; }}")
            return
        commit(round(number) if kind == "integer" else number)

    field.editingFinished.connect(done)
    return field


def unit(p: dict) -> str:
    return {"length": "m", "angle": "°"}.get(p["kind"], "")


def label(p: dict) -> str:
    u = unit(p)
    return f"{p['label']} ({u})" if u else p["label"]


def value_text(p: dict, value) -> str:
    if value is None:
        return ""
    if p["kind"] == "bool":
        return "sim" if value else "não"
    if p["kind"] == "integer":
        return str(int(value))
    if od.KINDS[p["kind"]] == od.NUMBER:
        return fmt(value)
    return str(value)
