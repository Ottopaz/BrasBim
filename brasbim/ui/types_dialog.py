# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela de tipos de parede e de porta (``spec/ui/02-edicao.md`` §8).

Lista à esquerda (nome e quantidade de elementos que usam o tipo) e editor à direita.
Novo, Duplicar e Excluir são transações imediatas; as mudanças do editor só entram ao
**Aplicar**, numa transação (``wall_type.edit`` ou ``door_type.edit``).
"""

from __future__ import annotations

import copy

import ifcopenshell.util.element
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, params
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import types as wall_types
from brasbim.ui.tools import fmt, parse_number
from brasbim.ui.tools import fmt_exact as exact

WALL_USES = [("Parede maciça", "SOLIDWALL"), ("Divisória", "PARTITIONING"),
             ("Parapeito / mureta", "PARAPET"), ("Parede hidráulica", "PLUMBINGWALL")]
LAYER_ROLES = [("Sem função", None), ("Estrutural", "LoadBearing"),
               ("Acabamento", "Finish"), ("Isolamento", "Insulation")]
DOOR_OPERATIONS = [
    ("Giro, 1 folha, dobradiças à esquerda", "SINGLE_SWING_LEFT"),
    ("Giro, 1 folha, dobradiças à direita", "SINGLE_SWING_RIGHT"),
    ("Giro, 2 folhas", "DOUBLE_DOOR_SINGLE_SWING"),
    ("Giro com folha fixa à direita", "SWING_FIXED_LEFT"),
    ("Giro com folha fixa à esquerda", "SWING_FIXED_RIGHT"),
    ("Vaivém, 1 folha, à esquerda", "DOUBLE_SWING_LEFT"),
    ("Vaivém, 1 folha, à direita", "DOUBLE_SWING_RIGHT"),
    ("Vaivém, 2 folhas", "DOUBLE_DOOR_DOUBLE_SWING"),
    ("Correr para a esquerda", "SLIDING_TO_LEFT"),
    ("Correr para a direita", "SLIDING_TO_RIGHT"),
    ("Correr, 2 folhas", "DOUBLE_DOOR_SLIDING"),
    ("Sanfonada para a esquerda", "FOLDING_TO_LEFT"),
    ("Sanfonada para a direita", "FOLDING_TO_RIGHT"),
    ("Sanfonada, 2 folhas", "DOUBLE_DOOR_FOLDING"),
    ("Enrolar", "ROLLINGUP"),
]


def _number_text(value) -> str:
    return "" if value is None else exact(value)


def _parse_optional(text: str):
    text = text.strip()
    return None if not text else parse_number(text)


def _unique(names, base: str) -> str:
    if base not in names:
        return base
    n = 2
    while f"{base} {n}" in names:
        n += 1
    return f"{base} {n}"


class TypesDialog(QDialog):
    """Base: lista, botões e controle de mudanças não aplicadas."""

    ifc_class = ""
    title = ""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(self.title)
        self.resize(760, 460)
        self.current: str | None = None  # GlobalId do tipo no editor
        self.dirty = False
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._picked)
        left = QVBoxLayout()
        left.addWidget(self.list)
        row = QHBoxLayout()
        for text, slot in (("Novo", self.add), ("Duplicar", self.duplicate),
                           ("Excluir", self.delete)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        left.addLayout(row)
        self.editor = QWidget()
        self.form = QFormLayout(self.editor)
        right = QVBoxLayout()
        right.addWidget(self.editor, 1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.apply_button = QPushButton("Aplicar")
        self.apply_button.clicked.connect(self.apply)
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        bottom.addWidget(self.apply_button)
        bottom.addWidget(close)
        right.addLayout(bottom)
        layout = QHBoxLayout(self)
        layout.addLayout(left, 2)
        layout.addLayout(right, 5)
        self.refresh()

    # --- lista -------------------------------------------------------------------------

    def types(self) -> list:
        return sorted(self.session.doc.ifc.by_type(self.ifc_class), key=lambda t: t.Name or "")

    def uses(self, element_type) -> int:
        return len(ifcopenshell.util.element.get_types(element_type))

    def refresh(self, select: str | None = None) -> None:
        select = select or self.current
        self.list.blockSignals(True)
        self.list.clear()
        row = 0
        for i, element_type in enumerate(self.types()):
            item = QListWidgetItem(f"{element_type.Name}  ({self.uses(element_type)})")
            item.setData(Qt.UserRole, element_type.GlobalId)
            self.list.addItem(item)
            if element_type.GlobalId == select:
                row = i
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(row)
            self.load(self.list.item(row).data(Qt.UserRole))
        else:
            self.load(None)

    def _picked(self, item, previous) -> None:
        if item is None or item.data(Qt.UserRole) == self.current:
            return
        if self.dirty and not self._resolve_pending():
            self.list.blockSignals(True)
            self.list.setCurrentItem(previous)
            self.list.blockSignals(False)
            return
        self.load(item.data(Qt.UserRole))

    def _resolve_pending(self) -> bool:
        """Mudanças não aplicadas: aplicar, descartar ou cancelar (devolve se segue)."""
        answer = QMessageBox.question(
            self, "Mudanças não aplicadas", "Aplicar as mudanças deste tipo?",
            QMessageBox.Apply | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Apply:
            return self.apply()
        return answer == QMessageBox.Discard

    def closeEvent(self, event):
        if self.dirty and not self._resolve_pending():
            event.ignore()
            return
        event.accept()

    # --- editor ------------------------------------------------------------------------

    def _clear_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)

    def touched(self, *_args) -> None:
        self.dirty = True

    def load(self, gid: str | None) -> None:
        self.current = gid
        self.dirty = False
        self._clear_form()
        self.editor.setEnabled(gid is not None)
        self.apply_button.setEnabled(gid is not None)
        if gid is not None:
            self.build_editor(self.session.doc.get(gid))
        self.dirty = False

    def _line(self, label: str, text: str) -> QLineEdit:
        field = QLineEdit(text)
        field.textEdited.connect(self.touched)
        self.form.addRow(label, field)
        return field

    def _combo(self, label: str, items, current) -> QComboBox:
        combo = QComboBox()
        for text, value in items:
            combo.addItem(text, value)
        combo.setCurrentIndex(max(0, next((i for i, (_, v) in enumerate(items)
                                           if v == current), 0)))
        combo.currentIndexChanged.connect(self.touched)
        self.form.addRow(label, combo)
        return combo

    def apply(self) -> bool:
        if self.current is None:
            return True
        try:
            changes = self.changes()
        except ValueError as e:
            self.session.message(f"valor inválido: {e}", "recusa")
            return False
        if changes and not self.session.run(lambda: self.edit(changes)):
            return False
        self.dirty = False
        self.refresh(self.current)
        return True

    def add(self) -> None:
        self._create(self.new_transaction)

    def duplicate(self) -> None:
        if self.current is not None:
            self._create(self.copy_transaction)

    def _create(self, build) -> None:
        if self.dirty and not self._resolve_pending():
            return
        try:
            tx = build()
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        if self.session.run(tx):
            self.refresh(tx.ops[0].id)

    def delete(self) -> None:
        if self.current is None:
            return
        gid = self.current
        if self.session.run(lambda: self.delete_transaction(gid)):
            self.current = None
            self.refresh()

    # a implementar nas subclasses
    def build_editor(self, element_type) -> None: ...
    def changes(self) -> dict: ...
    def edit(self, changes: dict): ...
    def new_transaction(self): ...
    def copy_transaction(self): ...
    def delete_transaction(self, gid: str): ...


class WallTypesDialog(TypesDialog):
    ifc_class = "IfcWallType"
    title = "Tipos de parede"

    def build_editor(self, wall_type) -> None:
        state = wall_types.read(wall_type)
        self.state = state
        self.name = self._line("Nome", state["name"] or "")
        uses = list(WALL_USES)
        if state["predefined_type"] not in [v for _, v in uses]:
            uses.append((state["predefined_type"], state["predefined_type"]))
        self.use = self._combo("Uso", uses, state["predefined_type"])
        self.form.addRow(QLabel("Camadas, da face esquerda para a direita:"))
        self.layers = QTableWidget(0, 4)
        self.layers.setHorizontalHeaderLabels(["Material", "Espessura", "Função", "Prioridade"])
        self.layers.verticalHeader().hide()
        self.layers.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.layers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layers.itemChanged.connect(self._layers_changed)
        self.form.addRow(self.layers)
        row = QHBoxLayout()
        for text, slot in (("Acrescentar", self.add_layer), ("Remover", self.remove_layer),
                           ("Subir", lambda: self.shift_layer(-1)),
                           ("Descer", lambda: self.shift_layer(1))):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        holder = QWidget()
        holder.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        self.form.addRow(holder)
        self.total = QLabel()
        self.form.addRow("Espessura total", self.total)
        for layer in state["layers"]:
            self._append_layer(layer)
        self._update_total()

    def _append_layer(self, layer: dict, at: int | None = None) -> None:
        self.layers.blockSignals(True)
        row = self.layers.rowCount() if at is None else at
        self.layers.insertRow(row)
        material = QTableWidgetItem(layer.get("material") or "")
        material.setData(Qt.UserRole, copy.deepcopy(layer))
        self.layers.setItem(row, 0, material)
        self.layers.setItem(row, 1, QTableWidgetItem(_number_text(layer.get("thickness"))))
        role = QComboBox()
        for text, value in LAYER_ROLES:
            role.addItem(text, value)
        values = [v for _, v in LAYER_ROLES]
        if layer.get("category") not in values:
            role.addItem(layer["category"], layer["category"])
            values.append(layer["category"])
        role.setCurrentIndex(values.index(layer.get("category")))
        role.currentIndexChanged.connect(self.touched)
        self.layers.setCellWidget(row, 2, role)
        priority = layer.get("priority")
        self.layers.setItem(row, 3, QTableWidgetItem("" if priority is None else str(priority)))
        self.layers.blockSignals(False)

    def _layers_changed(self, *_args) -> None:
        self.touched()
        self._update_total()

    def _update_total(self) -> None:
        try:
            total = sum(layer["thickness"] for layer in self.read_layers())
            self.total.setText(f"{fmt(total)} m")
        except ValueError:
            self.total.setText("—")

    def read_layers(self) -> list[dict]:
        out = []
        for row in range(self.layers.rowCount()):
            item = self.layers.item(row, 0)
            layer = dict(item.data(Qt.UserRole) or {})
            material = item.text().strip()
            if not material:
                raise ValueError(f"camada {row + 1} sem material")
            priority = self.layers.item(row, 3).text().strip()
            layer.update(material=material,
                         thickness=parse_number(self.layers.item(row, 1).text()),
                         category=self.layers.cellWidget(row, 2).currentData(),
                         priority=int(priority) if priority else None)
            out.append(layer)
        return out

    def add_layer(self) -> None:
        row = self.layers.currentRow()
        self._append_layer({"material": "Reboco", "thickness": 0.02, "category": "Finish"},
                           None if row < 0 else row + 1)
        self.touched()
        self._update_total()

    def remove_layer(self) -> None:
        row = self.layers.currentRow()
        if row >= 0 and self.layers.rowCount() > 1:
            self.layers.removeRow(row)
            self.touched()
            self._update_total()

    def shift_layer(self, step: int) -> None:
        row = self.layers.currentRow()
        target = row + step
        if row < 0 or not 0 <= target < self.layers.rowCount():
            return
        try:
            layers = self.read_layers()
        except ValueError as e:
            self.session.message(f"valor inválido: {e}", "recusa")
            return
        layers[row], layers[target] = layers[target], layers[row]
        self.layers.setRowCount(0)
        for layer in layers:
            self._append_layer(layer)
        self.layers.selectRow(target)
        self.touched()

    def changes(self) -> dict:
        new = {"name": self.name.text().strip(), "predefined_type": self.use.currentData(),
               "layers": self.read_layers()}
        if not new["name"]:
            raise ValueError("nome vazio")
        names = {t.Name for t in self.types() if t.GlobalId != self.current}
        if new["name"] in names:
            raise ValueError(f"já existe um tipo chamado {new['name']}")
        return {k: v for k, v in new.items() if v != self.state[k]}

    def edit(self, changes):
        return cmd.edit_wall_type(self.session.doc, self.current, **changes)

    def new_transaction(self):
        names = {t.Name for t in self.types()}
        return cmd.create_wall_type(self.session.doc, _unique(names, "Novo tipo de parede"),
                                    [{"material": "Bloco cerâmico", "thickness": 0.09,
                                      "category": "LoadBearing", "priority": 80}])

    def copy_transaction(self):
        state = wall_types.read(self.session.doc.get(self.current))
        names = {t.Name for t in self.types()}
        return cmd.create_wall_type(self.session.doc, _unique(names, f"{state['name']} (cópia)"),
                                    state["layers"], state["predefined_type"],
                                    state["object_type"])

    def delete_transaction(self, gid):
        return cmd.delete_wall_type(self.session.doc, gid)


class DoorTypesDialog(TypesDialog):
    ifc_class = "IfcDoorType"
    title = "Tipos de porta"

    def types(self) -> list:
        """Só os tipos de origem: a variante de mão acompanha o seu (porta §2.2)."""
        out = []
        for door_type in super().types():
            state = door_types.read(door_type)
            partner = self.session.doc.find(state["variant"]) if state["variant"] else None
            is_variant = (partner is not None and params.base_name(door_type.Name)
                          != door_type.Name and door_types.read(partner)["variant"]
                          == door_type.GlobalId and params.base_name(partner.Name)
                          == partner.Name)
            if not is_variant:
                out.append(door_type)
        return out

    def uses(self, door_type) -> int:
        n = super().uses(door_type)
        variant = door_types.read(door_type)["variant"]
        partner = self.session.doc.find(variant) if variant else None
        return n + (super().uses(partner) if partner is not None else 0)

    def build_editor(self, door_type) -> None:
        state = door_types.read(door_type)
        self.state = state
        lining, defaults = state["lining"], state["defaults"]
        self.name = self._line("Nome", state["name"] or "")
        self.operation = self._combo("Operação", DOOR_OPERATIONS, state["operation_type"])
        self.form.addRow(QLabel("<span style='color:#666'>Dimensões padrão</span>"))
        self.width = self._line("Largura", exact(defaults["width"]))
        self.height = self._line("Altura", exact(defaults["height"]))
        self.base = self._line("Base", exact(defaults["base"]))
        self.form.addRow(QLabel("<span style='color:#666'>Marco e folha</span>"))
        self.lining_thickness = self._line("Espessura do marco", exact(lining["thickness"]))
        self.lining_depth = self._line("Profundidade do marco", _number_text(lining["depth"]))
        self.lining_depth.setPlaceholderText("acompanha a parede")
        self.casing_thickness = self._line("Largura da guarnição",
                                           _number_text(lining["casing_thickness"]))
        self.casing_depth = self._line("Espessura da guarnição",
                                       _number_text(lining["casing_depth"]))
        depth = state["panels"][0]["depth"] if state["panels"] else params.DEFAULT_PANEL_DEPTH
        self.panel_depth = self._line("Espessura da folha", exact(depth))
        self.material = self._line("Material do marco", state["materials"]["lining"] or "")

    def changes(self) -> dict:
        state = self.state
        name = self.name.text().strip()
        if not name:
            raise ValueError("nome vazio")
        operation = self.operation.currentData()
        depth = parse_number(self.panel_depth.text())
        if operation == state["operation_type"]:
            panels = [{**p, "depth": depth} for p in state["panels"]]
        else:
            panels = params.default_panels(operation, depth)
        new = {
            "name": name,
            "operation_type": operation,
            "panels": panels,
            "defaults": {"width": parse_number(self.width.text()),
                         "height": parse_number(self.height.text()),
                         "base": parse_number(self.base.text())},
            "lining": {**state["lining"],
                       "thickness": parse_number(self.lining_thickness.text()),
                       "depth": _parse_optional(self.lining_depth.text()),
                       "casing_thickness": _parse_optional(self.casing_thickness.text()),
                       "casing_depth": _parse_optional(self.casing_depth.text())},
            "materials": {**state["materials"],
                          "lining": self.material.text().strip() or None},
        }
        return {k: v for k, v in new.items() if v != state[k]}

    def edit(self, changes):
        return fc.edit_door_type(self.session.doc, self.current, **changes)

    def new_transaction(self):
        names = {t.Name for t in super().types()}
        return fc.create_door_type(self.session.doc, _unique(names, "Novo tipo de porta"))

    def copy_transaction(self):
        state = door_types.read(self.session.doc.get(self.current))
        names = {t.Name for t in super().types()}
        name = _unique(names, f"{params.base_name(state['name'])} (cópia)")
        return fc.create_door_type(self.session.doc, name, state["operation_type"],
                                   lining=state["lining"], defaults=state["defaults"],
                                   materials=state["materials"], panels=state["panels"])

    def delete_transaction(self, gid):
        return fc.delete_door_type(self.session.doc, gid)
