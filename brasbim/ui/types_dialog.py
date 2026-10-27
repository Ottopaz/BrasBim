# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela de tipos de parede, de porta (``spec/ui/02-edicao.md`` §8), de janela
(``spec/ui/09-janela.md`` §5) e de pilar, viga e laje (``spec/ui/10-laje-pilar-viga.md``
§5).

Lista à esquerda (nome e quantidade de elementos que usam o tipo) e editor à direita.
Novo, Duplicar e Excluir são transações imediatas; as mudanças do editor só entram ao
**Aplicar**, numa transação (``wall_type.edit`` ou ``door_type.edit``).
"""

from __future__ import annotations

import copy

import ifcopenshell.util.element
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import materials, plan
from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, params, window_types
from brasbim.core.ops import Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.structure import profiles
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import types as wall_types
from brasbim.ui import icons, theme
from brasbim.ui.materials_dialog import MaterialsDialog
from brasbim.ui.tools import fmt, parse_number
from brasbim.ui.tools import fmt_exact as exact

WALL_USES = [("Parede maciça", "SOLIDWALL"), ("Divisória", "PARTITIONING"),
             ("Parapeito / mureta", "PARAPET"), ("Parede hidráulica", "PLUMBINGWALL")]
LAYER_ROLES = [("Sem função", None), ("Estrutural", "LoadBearing"),
               ("Acabamento", "Finish"), ("Isolamento", "Insulation")]
FILLS = [("Nenhum", "none"), ("Sólido", "solid"), ("Hachura", "hatch")]
DOOR_OPERATIONS = params.DOOR_OPERATION_LABELS


def _number_text(value) -> str:
    return "" if value is None else exact(value)


def _parse_optional(text: str):
    text = text.strip()
    return None if not text else parse_number(text)


def _dispose(item) -> None:
    """Esconde e manda apagar (``deleteLater``) o widget ou o layout de um item tirado de
    um layout, com o que houver dentro."""
    if item is None:
        return
    widget, layout = item.widget(), item.layout()
    if widget is not None:
        widget.hide()
        widget.deleteLater()
    elif layout is not None:
        while layout.count():
            _dispose(layout.takeAt(0))
        layout.deleteLater()


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

    def __init__(self, session, parent=None, select: str | None = None):
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
        self.refresh(select)

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
        """Tira as linhas e apaga os widgets pelo laço de eventos: ``removeRow`` apagava
        na hora widgets que o Python ainda segurava (campos em layouts aninhados) e a
        memória era liberada duas vezes (queda intermitente no UI91)."""
        while self.form.rowCount():
            row = self.form.takeRow(0)
            for item in (row.labelItem, row.fieldItem):
                _dispose(item)

    def touched(self, *_args) -> None:
        self.dirty = True

    def load(self, gid: str | None) -> None:
        self.current = gid
        self.dirty = False
        self.sample = None
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


class _PlanStyleDialog(TypesDialog):
    """Tipos com representação na planta (Pset ``BrasBim_RepresentacaoPlanta``)."""

    # representação na planta (spec/ui 03 §6.3)

    def _color(self, label: str, color: str) -> QPushButton:
        button = QPushButton(color.upper())
        button.setProperty("color", color.upper())

        def paint():
            c = button.property("color")
            text = "white" if QColor(c).lightness() < 128 else "black"
            button.setText(c)
            button.setStyleSheet(f"QPushButton {{ background: {c}; color: {text}; }}")

        def pick():
            chosen = QColorDialog.getColor(QColor(button.property("color")), self, label)
            if chosen.isValid():
                self.set_color(button, chosen.name())

        button.paint = paint
        button.clicked.connect(pick)
        paint()
        self.form.addRow(label, button)
        return button

    def set_color(self, button: QPushButton, color: str) -> None:
        button.setProperty("color", color.upper())
        button.paint()
        self.touched()

    def _plan_style_editor(self, wall_type) -> None:
        style = wall_types.plan_style(wall_type)
        self.form.addRow(QLabel("<span style='color:#666'>Representação na planta</span>"))
        self.fill = self._combo("Preenchimento", FILLS, style["fill"])
        self.fill_color = self._color("Cor do preenchimento", style["fill_color"])
        self.hatch_angle = self._line("Ângulo da hachura (°)", exact(style["hatch_angle"]))
        self.hatch_spacing = self._line("Espaçamento da hachura", exact(style["hatch_spacing"]))
        weights = list(wall_types.LINE_WEIGHTS)
        if style["line_weight"] not in weights:
            weights.append(style["line_weight"])
        self.line_weight = self._combo(
            "Espessura da linha",
            [(f"{exact(w * 1000)} mm", w) for w in sorted(weights)], style["line_weight"])
        self.line_color = self._color("Cor da linha", style["line_color"])
        self.sample = QLabel()
        self.form.addRow("Amostra", self.sample)
        self._update_sample()

    def read_plan_style(self) -> dict:
        return {"fill": self.fill.currentData(),
                "fill_color": self.fill_color.property("color"),
                "hatch_angle": parse_number(self.hatch_angle.text()),
                "hatch_spacing": parse_number(self.hatch_spacing.text()),
                "line_weight": self.line_weight.currentData(),
                "line_color": self.line_color.property("color")}

    def _update_sample(self) -> None:
        try:
            self.sample.setPixmap(icons.swatch(self.read_plan_style(), 120, 28))
        except ValueError:
            self.sample.clear()

    def touched(self, *_args) -> None:
        super().touched()
        if getattr(self, "sample", None) is not None:
            self._update_sample()



class WallTypesDialog(_PlanStyleDialog):
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
        self.layers = QTableWidget(0, 5)
        self.layers.setHorizontalHeaderLabels(["Material", "Espessura", "Função", "Prioridade",
                                               ""])
        self.layers.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
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
        self._plan_style_editor(wall_type)

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
        style = QToolButton()
        style.setText("…")
        style.setToolTip("Estilo do material (cor e corte)")
        style.clicked.connect(lambda _=False, item=material: self.edit_material(item))
        self.layers.setCellWidget(row, 4, style)
        self.layers.blockSignals(False)

    def edit_material(self, item: QTableWidgetItem) -> None:
        """Abre Projeto > Materiais… no material da camada (spec/ui 06 §4.2)."""
        name = item.text().strip()
        if not materials.named(self.session.doc, name):
            self.session.message(f"o material {name!r} ainda não existe: aplique o tipo antes",
                                 "recusa")
            return
        self.materials_dialog = MaterialsDialog(self.session, self, select=name)
        self.materials_dialog.exec()

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
        style, old = self.read_plan_style(), self.state["plan_style"]
        if style != {**wall_types.DEFAULT_PLAN_STYLE, **(old or {})}:
            new["plan_style"] = style
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
                                    state["object_type"], state["plan_style"])

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
        self.code = self._line("Código", state["code"] or "")
        self.code.setPlaceholderText(params.base_name(state["name"] or ""))
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
            "code": self.code.text().strip() or None,
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


# --- janela (spec/ui 09 §5) -----------------------------------------------------------

PARTITIONINGS = [("1 caixilho", "SINGLE_PANEL"), ("2 lado a lado", "DOUBLE_PANEL_VERTICAL"),
                 ("2 um sobre o outro", "DOUBLE_PANEL_HORIZONTAL"),
                 ("3 lado a lado", "TRIPLE_PANEL_VERTICAL"),
                 ("3 um sobre o outro", "TRIPLE_PANEL_HORIZONTAL")]
WINDOW_OPERATIONS = params.WINDOW_OPERATION_LABELS
POSITION_NAMES = {"MIDDLE": "Caixilho", "LEFT": "Esquerda", "RIGHT": "Direita",
                  "TOP": "Superior", "BOTTOM": "Inferior"}


class WindowPreview(QWidget):
    """Desenho do tipo, visto de frente (``plan.window_elevation``)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.drawing: list = []
        self.size_ = (1.0, 1.0)

    def show_state(self, state: dict | None) -> None:
        self.drawing = []
        if state is not None:
            d = state["defaults"]
            try:
                self.drawing = plan.window_elevation(d["width"], d["height"], state)
                self.size_ = (d["width"], d["height"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                self.drawing = []
        self.update()

    def paintEvent(self, event):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        if not self.drawing:
            return
        w, h = self.size_
        margin = 16
        k = min((self.width() - 2 * margin) / max(w, 1e-6),
                (self.height() - 2 * margin) / max(h, 1e-6))
        ox = (self.width() - w * k) / 2
        oy = (self.height() + h * k) / 2

        def screen(p):
            return QPointF(ox + p[0] * k, oy - p[1] * k)

        styles = {"lining": (QColor("#2b2a27"), QColor("#9da1a8"), Qt.SolidLine),
                  "framing": (QColor("#2b2a27"), QColor("#c4c7cc"), Qt.SolidLine),
                  "glass": (QColor("#6d8fa3"), QColor("#dcebf3"), Qt.SolidLine),
                  "symbol": (QColor("#6d6a62"), None, Qt.SolidLine),
                  "axis": (QColor("#6d6a62"), None, Qt.DashLine)}
        for role, points, closed in self.drawing:
            line, fill, style = styles[role]
            path = QPainterPath(screen(points[0]))
            for q in points[1:]:
                path.lineTo(screen(q))
            if closed:
                path.closeSubpath()
            painter.setPen(QPen(line, 1, style))
            painter.setBrush(QBrush(fill) if fill is not None and closed else Qt.NoBrush)
            painter.drawPath(path)


class WindowTypesDialog(TypesDialog):
    ifc_class = "IfcWindowType"
    title = "Tipos de janela"

    def types(self) -> list:
        """Só os tipos de origem: a variante de mão acompanha o seu (janela §2.4)."""
        out = []
        for window_type in super().types():
            state = window_types.read(window_type)
            partner = self.session.doc.find(state["variant"]) if state["variant"] else None
            is_variant = (partner is not None and params.base_name(window_type.Name)
                          != window_type.Name and window_types.read(partner)["variant"]
                          == window_type.GlobalId and params.base_name(partner.Name)
                          == partner.Name)
            if not is_variant:
                out.append(window_type)
        return out

    def uses(self, window_type) -> int:
        n = super().uses(window_type)
        variant = window_types.read(window_type)["variant"]
        partner = self.session.doc.find(variant) if variant else None
        return n + (super().uses(partner) if partner is not None else 0)

    def build_editor(self, window_type) -> None:
        self.state = window_types.read(window_type)
        if not hasattr(self, "preview"):
            self.preview = WindowPreview()
            self.layout().addWidget(self.preview, 3)
        self._build(copy.deepcopy(self.state))

    def _section(self, text: str) -> None:
        self.form.addRow(QLabel(f"<span style='color:#666'>{text}</span>"))

    def _build(self, state: dict) -> None:
        """Campos do editor a partir de ``state`` (refeitos quando a divisão muda)."""
        lining, defaults = state["lining"], state["defaults"]
        vertical = params.is_vertical(state["partitioning"])
        self.form_partitioning = state["partitioning"]  # a dos campos de caixilho
        self.name = self._line("Nome", state["name"] or "")
        self.code = self._line("Código", state["code"] or "")
        self.code.setPlaceholderText(params.base_name(state["name"] or ""))
        self.partitioning = self._combo("Divisão", PARTITIONINGS, state["partitioning"])
        self.partitioning.currentIndexChanged.connect(self._repartition)
        self._section("Caixilhos")
        self.operations = []
        for panel in state["panels"]:
            combo = self._combo(POSITION_NAMES[panel["position"]], WINDOW_OPERATIONS,
                                panel["operation"])
            self.operations.append(combo)
        self._section("Dimensões padrão")
        self.width = self._line("Largura", exact(defaults["width"]))
        self.height = self._line("Altura", exact(defaults["height"]))
        self.base = self._line("Peitoril", exact(defaults["base"]))
        self._section("Marco")
        self.lining_depth = self._line("Profundidade", exact(lining["depth"]))
        self.lining_thickness = self._line("Espessura", exact(lining["thickness"]))
        offsets = lining["mullion_offsets"] if vertical else lining["transom_offsets"]
        self.bar_thickness = self.bar_positions = None
        if offsets:
            noun = "Montante" if vertical else "Travessa"
            key = "mullion_thickness" if vertical else "transom_thickness"
            self._section(f"{noun}s" if len(offsets) > 1 else noun)
            self.bar_thickness = self._line("Espessura", exact(lining[key]))
            self.bar_positions = [
                self._line(f"Posição {i + 1} (%)", f"{f * 100:.1f}".replace(".", ","))
                for i, f in enumerate(offsets)]
        self._section("Perfil do caixilho")
        first = state["panels"][0]
        self.frame_depth = self._line("Profundidade", exact(first["frame_depth"]))
        self.frame_thickness = self._line("Largura", exact(first["frame_thickness"] or 0.0))
        self._section("Materiais")
        self.materials = {}
        for key, label in (("lining", "Marco"), ("framing", "Caixilho"), ("glazing", "Vidro")):
            field = QLineEdit(state["materials"].get(key) or "")
            field.textEdited.connect(self.touched)
            button = QToolButton()
            button.setText("…")
            button.setToolTip("Estilo do material (cor e corte)")
            button.clicked.connect(lambda _=False, f=field: self.edit_material(f))
            row = QHBoxLayout()
            row.addWidget(field, 1)
            row.addWidget(button)
            self.form.addRow(label, row)
            self.materials[key] = field
        for i in range(self.form.rowCount()):
            item = self.form.itemAt(i, QFormLayout.FieldRole)
            widget = item.widget() if item is not None else None
            if isinstance(widget, QLineEdit):
                widget.textEdited.connect(self._redraw)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._redraw)
        self.preview.show_state(state)

    def edit_material(self, field: QLineEdit) -> None:
        name = field.text().strip()
        if not materials.named(self.session.doc, name):
            self.session.message(f"o material {name!r} ainda não existe: aplique o tipo antes",
                                 "recusa")
            return
        self.materials_dialog = MaterialsDialog(self.session, self, select=name)
        self.materials_dialog.exec()

    def collect(self) -> dict:
        """Estado do tipo como está nos campos (``ValueError`` se algum número é inválido)."""
        state = copy.deepcopy(self.state)
        partitioning = self.form_partitioning
        if partitioning != state["partitioning"]:
            state = window_types.with_partitioning(state, partitioning)
        vertical = params.is_vertical(partitioning)
        frame = {"frame_depth": parse_number(self.frame_depth.text()),
                 "frame_thickness": parse_number(self.frame_thickness.text())}
        state["panels"] = [{**p, **frame, "operation": combo.currentData()}
                           for p, combo in zip(state["panels"], self.operations)]
        lining = {**state["lining"], "depth": parse_number(self.lining_depth.text()),
                  "thickness": parse_number(self.lining_thickness.text())}
        if self.bar_positions is not None:
            key = "mullion" if vertical else "transom"
            lining[f"{key}_thickness"] = parse_number(self.bar_thickness.text())
            lining[f"{key}_offsets"] = [round(parse_number(f.text()) / 100, 9)
                                        for f in self.bar_positions]
        state["lining"] = lining
        state["name"] = self.name.text().strip()
        state["code"] = self.code.text().strip() or None
        state["defaults"] = {"width": parse_number(self.width.text()),
                             "height": parse_number(self.height.text()),
                             "base": parse_number(self.base.text())}
        state["materials"] = {k: f.text().strip() or None for k, f in self.materials.items()}
        chosen = self.partitioning.currentData()
        if chosen != partitioning:  # divisão trocada agora: caixilhos refeitos
            state = window_types.with_partitioning(state, chosen)
        return state

    def _repartition(self, *_args) -> None:
        """Nova divisão: refaz os caixilhos (spec/ui 09 §5.1) e o formulário."""
        try:
            state = self.collect()
        except ValueError:
            return
        self._clear_form()
        self._build(state)
        self.dirty = True

    def _redraw(self, *_args) -> None:
        try:
            self.preview.show_state(self.collect())
        except ValueError:
            pass

    def changes(self) -> dict:
        new = self.collect()
        if not new["name"]:
            raise ValueError("nome vazio")
        keys = ("name", "code", "partitioning", "lining", "panels", "materials", "defaults")
        return {k: new[k] for k in keys if new[k] != self.state[k]}

    def edit(self, changes):
        return fc.edit_window_type(self.session.doc, self.current, **changes)

    def new_transaction(self):
        names = {t.Name for t in super().types()}
        return fc.create_window_type(self.session.doc, _unique(names, "Novo tipo de janela"))

    def copy_transaction(self):
        state = window_types.read(self.session.doc.get(self.current))
        names = {t.Name for t in super().types()}
        name = _unique(names, f"{params.base_name(state['name'])} (cópia)")
        tx = fc.create_window_type(self.session.doc, name, state["partitioning"])
        data = tx.ops[0].data
        data.update({k: copy.deepcopy(state[k]) for k in ("lining", "panels", "materials",
                                                           "defaults")}, code=None)
        return tx

    def delete_transaction(self, gid):
        return fc.delete_window_type(self.session.doc, gid)


# --- pilar, viga e laje (spec/ui 10 §5) --------------------------------------------------

SECTIONS = (("Retangular", "rect"), ("Circular", "circle"))
SLAB_USES = [("Laje de piso", "FLOOR"), ("Laje sobre o solo", "BASESLAB"),
             ("Cobertura (telhado)", "ROOF")]
PLAN_SOURCES = [("Padrão", "default"), ("Própria", "own")]


class SectionPreview(QWidget):
    """Desenho da seção cotado (spec/ui 10 §5)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.section: dict | None = None
        self.setMinimumSize(200, 150)

    def show_section(self, section: dict | None) -> None:
        self.section = section
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.PAPER))
        section = self.section
        if section is None:
            painter.end()
            return
        w, h = profiles.size(section)
        k = min((self.width() - 80) / w, (self.height() - 60) / h)
        cx, cy = self.width() / 2, self.height() / 2 - 8
        rect = QRectF(cx - w * k / 2, cy - h * k / 2, w * k, h * k)
        painter.setPen(QPen(QColor(theme.INK), 1.5))
        if section["shape"] == "circle":
            painter.drawEllipse(rect)
            text = f"Ø {fmt(section['d'])}"
            painter.drawText(QRectF(0, rect.bottom() + 6, self.width(), 20), Qt.AlignCenter,
                             text)
        else:
            painter.drawRect(rect)
            painter.drawText(QRectF(0, rect.bottom() + 6, self.width(), 20), Qt.AlignCenter,
                             f"b = {fmt(section['b'])}")
            painter.save()
            painter.translate(QPointF(rect.right() + 18, cy))
            painter.rotate(-90)
            painter.drawText(QRectF(-60, -10, 120, 20), Qt.AlignCenter,
                             f"h = {fmt(section['h'])}")
            painter.restore()
        painter.end()


class _StructureTypesDialog(_PlanStyleDialog):
    """Base de pilar, viga e laje: representação na planta padrão ou própria, e excluir
    um tipo em uso pede o tipo que fica no lugar (spec/ui 10 §5)."""

    noun = ""

    def _plan_source(self, element_type) -> None:
        own = wall_types.read_plan_style(element_type) is not None
        self.plan_source = self._combo("Representação na planta", PLAN_SOURCES,
                                       "own" if own else "default")
        self._plan_style_editor(element_type)
        self.plan_source.currentIndexChanged.connect(self._plan_enabled)
        self._plan_enabled()

    def _plan_enabled(self, *_args) -> None:
        own = self.plan_source.currentData() == "own"
        for field in (self.fill, self.fill_color, self.hatch_angle, self.hatch_spacing,
                      self.line_weight, self.line_color):
            field.setEnabled(own)

    def plan_changes(self) -> dict:
        new = self.read_plan_style() if self.plan_source.currentData() == "own" else None
        return {"plan_style": new} if new != self.state["plan_style"] else {}

    def _material(self, current: str) -> QLineEdit:
        field = QLineEdit(current)
        field.textEdited.connect(self.touched)
        button = QToolButton()
        button.setText("…")
        button.setToolTip("Estilo do material (cor e corte)")
        button.clicked.connect(lambda: self._edit_material(field.text().strip()))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        row.addWidget(button)
        holder = QWidget()
        holder.setLayout(row)
        self.form.addRow("Material", holder)
        return field

    def _edit_material(self, name: str) -> None:
        if not materials.named(self.session.doc, name):
            self.session.message(f"o material {name!r} ainda não existe: aplique o tipo antes",
                                 "recusa")
            return
        self.materials_dialog = MaterialsDialog(self.session, self, select=name)
        self.materials_dialog.exec()

    def _unique_name(self, name: str) -> str:
        if not name:
            raise ValueError("nome vazio")
        names = {t.Name for t in self.types() if t.GlobalId != self.current}
        if name in names:
            raise ValueError(f"já existe um tipo chamado {name}")
        return name

    def edit(self, changes):
        return sc.edit_type(self.session.doc, self.current, **changes)

    def delete_transaction(self, gid):
        doc = self.session.doc
        element_type = doc.get(gid)
        if not self.uses(element_type):
            return sc.delete_type(doc, gid)
        others = [t for t in self.types() if t.GlobalId != gid]
        if not others:
            raise OpError(f"o tipo {element_type.Name} está em uso e não há outro para pôr "
                          "no lugar")
        names = [t.Name for t in others]
        name, ok = QInputDialog.getItem(
            self, "Tipo em uso",
            f"{self.uses(element_type)} {self.noun} usam {element_type.Name}. "
            "Que tipo fica no lugar?", names, 0, False)
        if not ok:
            return Transaction("", [])  # desistiu: nada a fazer
        return sc.delete_type(doc, gid, others[names.index(name)].GlobalId)


class _ProfileTypesDialog(_StructureTypesDialog):
    shapes = SECTIONS

    def build_editor(self, element_type) -> None:
        state = sc.read_type(element_type)
        self.state = state
        self.name = self._line("Nome", state["name"] or "")
        section = state["section"]
        self.shape = self._combo("Seção", self.shapes, section["shape"])
        self.b = self._line("b (largura)", exact(section.get("b", section.get("d", 0.2))))
        self.h = self._line("h (altura)", exact(section.get("h", section.get("d", 0.4))))
        self.d = self._line("Diâmetro", exact(section.get("d", section.get("b", 0.3))))
        self.material = self._material(state["material"] or "")
        self.preview = SectionPreview()
        self.form.addRow(self.preview)
        for field in (self.b, self.h, self.d):
            field.textEdited.connect(self._redraw)
        self.shape.currentIndexChanged.connect(self._redraw)
        self._plan_source(element_type)
        self._redraw()

    def read_section(self) -> dict:
        if self.shape.currentData() == "circle":
            return {"shape": "circle", "d": parse_number(self.d.text())}
        return {"shape": "rect", "b": parse_number(self.b.text()),
                "h": parse_number(self.h.text())}

    def _redraw(self, *_args) -> None:
        circle = self.shape.currentData() == "circle"
        for field, visible in ((self.b, not circle), (self.h, not circle), (self.d, circle)):
            field.setVisible(visible)
            self.form.labelForField(field).setVisible(visible)
        try:
            section = self.read_section()
            profiles.validate(section)
        except (ValueError, KeyError):
            section = None
        self.preview.show_section(section)

    def changes(self) -> dict:
        section = self.read_section()
        try:
            profiles.validate(section)
        except ValueError as e:
            raise ValueError(str(e)) from e
        new = {"name": self._unique_name(self.name.text().strip()), "section": section,
               "material": self.material.text().strip()}
        if not new["material"]:
            raise ValueError("material vazio")
        out = {k: v for k, v in new.items() if v != self.state[k]}
        return {**out, **self.plan_changes()}


class ColumnTypesDialog(_ProfileTypesDialog):
    ifc_class = "IfcColumnType"
    title = "Tipos de pilar"
    noun = "pilares"

    def new_transaction(self):
        names = {t.Name for t in self.types()}
        return sc.create_column_type(self.session.doc, _unique(names, "Novo tipo de pilar"),
                                     {"shape": "rect", "b": 0.20, "h": 0.40})

    def copy_transaction(self):
        state = sc.read_type(self.session.doc.get(self.current))
        names = {t.Name for t in self.types()}
        return sc.create_column_type(self.session.doc,
                                     _unique(names, f"{state['name']} (cópia)"),
                                     state["section"], state["material"], state["plan_style"])


class BeamTypesDialog(_ProfileTypesDialog):
    ifc_class = "IfcBeamType"
    title = "Tipos de viga"
    noun = "vigas"
    shapes = SECTIONS[:1]

    def new_transaction(self):
        names = {t.Name for t in self.types()}
        return sc.create_beam_type(self.session.doc, _unique(names, "Novo tipo de viga"),
                                   0.14, 0.40)

    def copy_transaction(self):
        state = sc.read_type(self.session.doc.get(self.current))
        names = {t.Name for t in self.types()}
        section = state["section"]
        return sc.create_beam_type(self.session.doc, _unique(names, f"{state['name']} (cópia)"),
                                   section["b"], section["h"], state["material"],
                                   state["plan_style"])


class SlabTypesDialog(_StructureTypesDialog):
    """Camadas de cima para baixo, como se lê um corte (laje.md §2.3)."""

    ifc_class = "IfcSlabType"
    title = "Tipos de laje"
    noun = "lajes"

    def build_editor(self, slab_type) -> None:
        state = sc.read_type(slab_type)
        self.state = state
        self.name = self._line("Nome", state["name"] or "")
        self.use = self._combo("Função", SLAB_USES, state["predefined_type"])
        self.form.addRow(QLabel("Camadas, de cima para baixo:"))
        self.layers = QTableWidget(0, 3)
        self.layers.setHorizontalHeaderLabels(["Material", "Espessura", ""])
        self.layers.verticalHeader().hide()
        self.layers.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.layers.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
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
        self._plan_source(slab_type)

    def _append_layer(self, layer: dict, at: int | None = None) -> None:
        self.layers.blockSignals(True)
        row = self.layers.rowCount() if at is None else at
        self.layers.insertRow(row)
        material = QTableWidgetItem(layer.get("material") or "")
        self.layers.setItem(row, 0, material)
        self.layers.setItem(row, 1, QTableWidgetItem(_number_text(layer.get("thickness"))))
        style = QToolButton()
        style.setText("…")
        style.setToolTip("Estilo do material (cor e corte)")
        style.clicked.connect(lambda _=False, item=material: self._edit_material(
            item.text().strip()))
        self.layers.setCellWidget(row, 2, style)
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
            material = self.layers.item(row, 0).text().strip()
            if not material:
                raise ValueError(f"camada {row + 1} sem material")
            out.append({"material": material,
                        "thickness": parse_number(self.layers.item(row, 1).text())})
        return out

    def add_layer(self) -> None:
        row = self.layers.currentRow()
        self._append_layer({"material": "Concreto", "thickness": 0.10},
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
        new = {"name": self._unique_name(self.name.text().strip()),
               "predefined_type": self.use.currentData(), "layers": self.read_layers()}
        out = {k: v for k, v in new.items() if v != self.state[k]}
        return {**out, **self.plan_changes()}

    def new_transaction(self):
        names = {t.Name for t in self.types()}
        return sc.create_slab_type(self.session.doc, _unique(names, "Novo tipo de laje"),
                                   [{"material": "Concreto", "thickness": 0.10}])

    def copy_transaction(self):
        state = sc.read_type(self.session.doc.get(self.current))
        names = {t.Name for t in self.types()}
        return sc.create_slab_type(self.session.doc, _unique(names, f"{state['name']} (cópia)"),
                                   state["layers"], state["predefined_type"],
                                   state["plan_style"])
