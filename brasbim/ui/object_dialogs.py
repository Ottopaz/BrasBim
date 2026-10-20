# SPDX-License-Identifier: GPL-3.0-or-later
"""Diálogos pequenos dos objetos paramétricos (``spec/elementos/objeto-parametrico.md``
§5.4): editar tipo (nome, código e parâmetros de tipo) e escolher o substituto."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from brasbim.core.document import OpError
from brasbim.core.objects import commands as oc
from brasbim.core.objects import definition as od
from brasbim.core.objects import formula as fm
from brasbim.core.objects import types as ot
from brasbim.ui import object_widgets as ow
from brasbim.ui import theme


class TypeDialog(QDialog):
    """Editar tipo: uma transação com o que mudou (§5.4)."""

    def __init__(self, session, type_gid: str, parent=None):
        super().__init__(parent)
        self.session = session
        doc = session.doc
        self.element_type = doc.get(type_gid)
        state = ot.read(self.element_type)
        defn = state["definition"]
        self.setWindowTitle(f"Tipo {self.element_type.Name}")
        layout = QVBoxLayout(self)
        users = len(oc.occurrences(doc, self.element_type))
        note = QLabel(f"{defn['name']}: as mudanças valem para {users} ocorrência(s).")
        note.setStyleSheet(f"color: {theme.INK_SOFT}")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        layout.addLayout(form)
        self.name = QLineEdit(self.element_type.Name or "")
        form.addRow("Nome", self.name)
        self.values: dict = {}
        self.defaults: dict = {}
        try:
            current = ot.evaluate(state, level="type")
        except OpError:
            current = {}
        for p in od.type_params(defn):
            value = state["values"].get(p["name"], p["value"])
            if od.editable(p):
                form.addRow(ow.label(p), ow.param_widget(
                    p, value, lambda v, n=p["name"]: self.values.__setitem__(n, v), doc))
            else:
                shown = QLabel(ow.value_text(p, current.get(fm.key(p["name"]))))
                shown.setStyleSheet(f"color: {theme.INK_SOFT}")
                shown.setToolTip(f"= {p['formula']}")
                form.addRow(ow.label(p), shown)
        occ = [p for p in od.occurrence_params(defn) if od.editable(p)]
        if occ:
            title = QLabel("<b>Padrões das ocorrências novas</b>")
            title.setContentsMargins(0, 8, 0, 0)
            form.addRow(title)
            for p in occ:
                value = state["defaults"].get(p["name"], p["value"])
                form.addRow(ow.label(p), ow.param_widget(
                    p, value, lambda v, n=p["name"]: self.defaults.__setitem__(n, v), doc))
        self.error = QLabel()
        self.error.setStyleSheet(f"color: {theme.ERROR}")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        doc = self.session.doc
        changes = {}
        name = self.name.text().strip()
        if name and name != self.element_type.Name:
            changes["name"] = name
        if self.values:
            changes["values"] = self.values
        if self.defaults:
            changes["defaults"] = self.defaults
        try:
            tx = oc.edit_type(doc, self.element_type, **changes)
        except OpError as e:
            self.error.setText(str(e))
            return
        if tx.ops and not self.session.run(tx):
            self.error.setText(self.session.messages[-1]["text"])
            return
        self.accept()


def ask_replacement(parent, doc, element_type) -> str | None:
    """Tipo substituto para excluir um tipo em uso (§5.4); None = cancelou."""
    others = [t for t in ot.all_types(doc) if t != element_type
              and t.is_a(element_type.is_a())]
    if not others:
        return None
    dialog = QDialog(parent)
    dialog.setWindowTitle("Excluir tipo em uso")
    layout = QVBoxLayout(dialog)
    count = len(oc.occurrences(doc, element_type))
    label = QLabel(f"{count} objeto(s) usam {element_type.Name}. Para qual tipo eles vão?")
    label.setWordWrap(True)
    layout.addWidget(label)
    combo = QComboBox()
    for t in others:
        combo.addItem(t.Name, t.GlobalId)
    layout.addWidget(combo)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return combo.currentData() if dialog.exec() == QDialog.Accepted else None
