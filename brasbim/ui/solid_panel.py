# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela de operações de sólidos (``spec/ui/41-dwg-solidos-perfil-complexo.md`` §3a):
monta a operação por listas — alvos, operadores e operação — a partir da seleção, mostra o
que está selecionado e quantos, aplica e tira os recortes entre as listas."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.structure import roofs, solids
from brasbim.ui import icons, theme

TARGETS, OPERATORS = "targets", "operators"
ICONS = {solids.SUBTRACT: "solid_subtract", solids.UP: "solid_up",
         solids.DOWN: "solid_down", solids.INTERSECT: "solid_intersect"}
# Nome do tipo de elemento (singular, plural), para a contagem da seleção.
NOUNS = {"IfcWall": ("parede", "paredes"), "IfcColumn": ("pilar", "pilares"),
         "IfcBeam": ("viga", "vigas"), "IfcSlab": ("laje", "lajes"),
         "IfcRoof": ("cobertura", "coberturas"), "IfcDoor": ("porta", "portas"),
         "IfcWindow": ("janela", "janelas"), "IfcStair": ("escada", "escadas"),
         "IfcRailing": ("guarda-corpo", "guarda-corpos"),
         "IfcFurnishingElement": ("objeto", "objetos"), "IfcSpace": ("ambiente", "ambientes"),
         "IfcGeographicElement": ("terreno", "terrenos")}


def noun(element, count: int = 1) -> str:
    for cls, (one, many) in NOUNS.items():
        if element.is_a(cls):
            return one if count == 1 else many
    return "elemento" if count == 1 else "elementos"


def name_of(element) -> str:
    return element.Name or noun(element).capitalize()


def item_text(element) -> str:
    """'Parede · Alvenaria 14': o nome (com o tipo do elemento, se o nome não o diz) e o
    tipo do IFC, para distinguir elementos de mesmo nome."""
    import ifcopenshell.util.element as ue

    name = name_of(element)
    if not name.lower().startswith(noun(element)):
        name = f"{name} ({noun(element)})"
    kind = ue.get_type(element)
    return f"{name} · {kind.Name}" if kind is not None and kind.Name else name


def describe_selection(elements) -> str:
    """'Nada selecionado', 'Parede 3 (parede)' ou '3 elementos: 2 paredes, 1 laje'."""
    if not elements:
        return "Nada selecionado"
    if len(elements) == 1:
        return f"1 elemento ({item_text(elements[0])})"
    counts: dict[str, list] = {}
    for e in elements:
        counts.setdefault(noun(e), []).append(e)
    parts = [f"{len(found)} {noun(found[0], len(found))}"
             for _, found in sorted(counts.items(), key=lambda kv: -len(kv[1]))]
    return f"{len(elements)} elementos (" + ", ".join(parts) + ")"


class SolidPanel(QWidget):
    """Painel "Operações de sólidos". ``targets``/``operators``: GlobalIds, na ordem."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.targets: list[str] = []
        self.operators: list[str] = []
        self.operation = solids.SUBTRACT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.selection_label = QLabel()
        self.selection_label.setWordWrap(True)
        self.selection_label.setStyleSheet(f"color: {theme.INK_SOFT};")
        layout.addWidget(self.selection_label)
        self.boxes: dict[str, QGroupBox] = {}
        self.lists: dict[str, QListWidget] = {}
        self.buttons: dict[str, QPushButton] = {}
        for role in (TARGETS, OPERATORS):
            layout.addWidget(self._role_box(role), 1)
        ops_box = QGroupBox("Operação")
        ops_layout = QHBoxLayout(ops_box)
        ops_layout.setContentsMargins(6, 4, 6, 4)
        self.op_group = QButtonGroup(self)
        self.op_buttons: dict[str, QToolButton] = {}
        for op in solids.OPERATIONS:
            button = QToolButton()
            button.setIcon(icons.icon(ICONS[op]))
            button.setIconSize(QSize(20, 20))
            button.setText(solids.LABELS[op].capitalize())
            button.setToolTip(solids.LABELS[op].capitalize())
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setChecked(op == self.operation)
            button.clicked.connect(lambda _=False, o=op: self.set_operation(o))
            self.op_group.addButton(button)
            self.op_buttons[op] = button
            ops_layout.addWidget(button)
        ops_layout.addStretch(1)
        self.op_label = QLabel()
        layout.addWidget(ops_box)
        layout.addWidget(self.op_label)
        row = QHBoxLayout()
        self.apply_button = QPushButton("Aplicar")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply)
        self.remove_button = QPushButton("Tirar entre eles")
        self.remove_button.setToolTip("Tira só os recortes dos alvos pelos operadores da lista")
        self.remove_button.clicked.connect(self.remove)
        row.addWidget(self.apply_button)
        row.addWidget(self.remove_button)
        layout.addLayout(row)
        session.listeners.append(self._on_session)
        self.refresh()

    def _role_box(self, role: str) -> QGroupBox:
        box = QGroupBox()
        inner = QVBoxLayout(box)
        inner.setContentsMargins(6, 4, 6, 6)
        items = QListWidget()
        items.setMinimumHeight(60)
        items.itemClicked.connect(lambda item: self.session.select([item.data(Qt.UserRole)]))
        inner.addWidget(items)
        row = QHBoxLayout()
        for key, text, slot in (("use", "Usar a seleção", lambda: self.take(role)),
                                ("add", "Somar a seleção", lambda: self.take(role, add=True)),
                                ("clear", "Limpar", lambda: self.clear(role))):
            button = QPushButton(text)
            button.clicked.connect(lambda _=False, f=slot: f())
            row.addWidget(button)
            self.buttons[f"{role}_{key}"] = button
        inner.addLayout(row)
        self.boxes[role], self.lists[role] = box, items
        return box

    # --- estado ------------------------------------------------------------------------

    def _list(self, role: str) -> list[str]:
        return self.targets if role == TARGETS else self.operators

    def _elements(self, gids) -> list:
        doc = self.session.doc
        return [e for e in (doc.find(g) for g in gids) if e is not None]

    def _selected(self) -> list:
        """A seleção, com cada água de cobertura trocada pela cobertura."""
        out, seen = [], set()
        for e in self._elements(sorted(self.session.selection)):
            e = roofs.roof_of(e) or e
            if e.GlobalId not in seen:
                seen.add(e.GlobalId)
                out.append(e)
        return out

    def take(self, role: str, add: bool = False) -> None:
        """Põe a seleção na lista do papel; o que não pode ter o papel é recusado."""
        doc = self.session.doc
        ok = (lambda e: solids.can_be_target(doc, e)) if role == TARGETS \
            else solids.can_be_operator
        chosen = self._selected()
        if not chosen:
            self.session.message("selecione os elementos antes", "recusa")
            return
        good = [e.GlobalId for e in chosen if ok(e)]
        refused = len(chosen) - len(good)
        if refused:
            what = ("só parede, pilar, viga e laje do BrasBim são recortados" if role == TARGETS
                    else "elemento sem corpo não recorta")
            self.session.message(f"{refused} fora da lista: {what}", "recusa")
        current = self._list(role)
        if not add:
            current.clear()
        current.extend(g for g in good if g not in current)
        other = self._list(OPERATORS if role == TARGETS else TARGETS)
        other[:] = [g for g in other if g not in good]  # um elemento, um papel
        self.refresh()

    def clear(self, role: str) -> None:
        self._list(role).clear()
        self.refresh()

    def set_operation(self, op: str) -> None:
        self.operation = op
        self.op_buttons[op].setChecked(True)
        self.refresh()

    def apply(self) -> bool:
        doc = self.session.doc
        targets, operators = self._elements(self.targets), self._elements(self.operators)
        if not targets or not operators:
            self.session.message("escolha os alvos e os operadores", "recusa")
            return False
        op = self.operation
        if not self.session.run(lambda: solids.cut_elements(doc, targets, operators, op)):
            return False
        self.session.select([e.GlobalId for e in targets])
        return True

    def remove(self) -> bool:
        doc = self.session.doc
        targets, operators = self._elements(self.targets), self._elements(self.operators)
        return bool(self.session.run(
            lambda: solids.remove_between(doc, targets, operators)))

    # --- tela --------------------------------------------------------------------------

    def _on_session(self, event: str) -> None:
        if event in ("selection", "model", "document"):
            if event == "document":
                self.targets, self.operators = [], []
            self.refresh()

    def refresh(self) -> None:
        self.selection_label.setText("Seleção: " + describe_selection(self._selected()))
        for role, title in ((TARGETS, "Alvos (recortados)"),
                            (OPERATORS, "Operadores (que recortam)")):
            current = self._list(role)
            elements = self._elements(current)
            current[:] = [e.GlobalId for e in elements]  # apagados saem
            self.boxes[role].setTitle(f"{title}: {len(elements)}")
            items = self.lists[role]
            items.clear()
            for e in elements:
                cuts = ""
                if role == TARGETS and solids.cut_by(e):
                    cuts = f" · recortado por {len(solids.cut_by(e))}"
                item = QListWidgetItem(item_text(e) + cuts)
                item.setData(Qt.UserRole, e.GlobalId)
                items.addItem(item)
                if e.GlobalId in self.session.selection:
                    item.setSelected(True)
            self.buttons[f"{role}_clear"].setEnabled(bool(elements))
        ready = bool(self.targets and self.operators)
        self.apply_button.setEnabled(ready)
        self.remove_button.setEnabled(ready)
        self.op_label.setText(f"Operação escolhida: {solids.LABELS[self.operation]}")
