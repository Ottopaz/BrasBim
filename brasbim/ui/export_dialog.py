# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadro Arquivo > Exportar DWG/DXF (``spec/ui/41-dwg-solidos-perfil-complexo.md`` §2):
plantas, cortes e fachadas, vistas salvas e pranchas com caixas para marcar, o formato e
a pasta. Um arquivo por item, com o nome do item."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from brasbim.core.drawings import saved_views, sheets, views
from brasbim.ui.dwg_export import sheet_title
from brasbim.ui.project_panel import icon_button, tree_icon

FORMAT_LABELS = (("dwg", "DWG (AutoCAD 2000)"), ("dxf", "DXF (2018)"))


def drawing_items(doc) -> list[tuple[str, list[tuple[str, str, str]]]]:
    """[(grupo, [(tipo, GlobalId, nome)])]: o que pode ir para o DWG, na ordem do
    Navegador. Vista salva 3D fica de fora (não tem desenho em linhas)."""
    plans = [("plan", s.GlobalId, f"Planta {s.Name or ''}".strip()) for s in doc.storeys()]
    sections = [("view", v.GlobalId, views.read_state(v)["name"] or v.GlobalId)
                for v in views.all_views(doc)]
    saved = []
    for entity in saved_views.all_saved_views(doc):
        state = saved_views.read_state(entity)
        if state["kind"] != "3d":
            saved.append(("saved", entity.GlobalId, state["name"]))
    pages = [("sheet", s.GlobalId, sheet_title(sheets.read_state(s)))
             for s in sheets.all_sheets(doc)]
    return [(title, found) for title, found in (
        ("Plantas", plans), ("Cortes e fachadas", sections), ("Vistas salvas", saved),
        ("Pranchas", pages)) if found]


_ICONS = {"plan": "view_plan", "view": "section", "saved": "save_view", "sheet": "sheet"}


class ExportDwgDialog(QDialog):
    def __init__(self, doc, folder: str = "", checked=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar DWG/DXF")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        for title, found in drawing_items(doc):
            group = QTreeWidgetItem(self.tree, [title])
            group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            for kind, gid, name in found:
                item = QTreeWidgetItem(group, [name])
                item.setIcon(0, tree_icon(_ICONS[kind]))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setData(0, Qt.UserRole, (kind, gid, name))
                item.setCheckState(0, Qt.Checked if gid in checked else Qt.Unchecked)
            group.setExpanded(True)
        self.format = QComboBox()
        for key, label in FORMAT_LABELS:
            self.format.addItem(label, key)
        self.folder = QLineEdit(folder)
        self.folder.setPlaceholderText("Pasta onde gravar")
        browse = icon_button("folder", "Escolher a pasta", self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        form = QFormLayout()
        form.addRow("Formato", self.format)
        form.addRow("Pasta", row)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Exportar")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree, 1)
        layout.addLayout(form)
        layout.addWidget(self.buttons)
        self.tree.itemChanged.connect(self._update)
        self.folder.textChanged.connect(self._update)
        self.resize(420, 480)
        self._update()

    def _browse(self) -> None:
        found = QFileDialog.getExistingDirectory(self, "Pasta para exportar",
                                                 self.folder.text())
        if found:
            self.folder.setText(found)

    def _update(self, *_args) -> None:
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.chosen()) and bool(self.folder.text().strip()))

    def items(self) -> list[QTreeWidgetItem]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            out += [group.child(j) for j in range(group.childCount())]
        return out

    def chosen(self) -> list[tuple[str, str, str]]:
        """(tipo, GlobalId, nome) dos itens marcados."""
        return [item.data(0, Qt.UserRole) for item in self.items()
                if item.checkState(0) == Qt.Checked]

    def fmt(self) -> str:
        return self.format.currentData()
