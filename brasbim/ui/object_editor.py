# SPDX-License-Identifier: GPL-3.0-or-later
"""Editor do objeto paramétrico (``spec/elementos/objeto-parametrico.md`` §5.3).

Abas à esquerda (Parâmetros, Peças, Símbolo 2D, Objeto, Tipos) e a prévia à direita. A
definição em edição é um dicionário (``self.defn``); cada campo muda o dicionário e pede
uma prévia nova (com 300 ms de espera durante a digitação). *Aplicar ao projeto* grava a
definição e os tipos numa transação (``commands.apply_definition``).
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import materials as material_library
from brasbim.core.document import OpError
from brasbim.core.objects import commands as oc
from brasbim.core.objects import definition as od
from brasbim.core.objects import formula as fm
from brasbim.core.objects import mesh as object_mesh
from brasbim.core.objects import types as ot
from brasbim.ui import object_preview, theme
from brasbim.ui import object_widgets as ow
from brasbim.ui.icons import icon
from brasbim.ui.tools import fmt, parse_number

PREVIEW_MS = 300
PIECE_NAMES = {"box": "Caixa", "cylinder": "Cilindro", "extrusion": "Extrusão",
               "revolution": "Revolução", "object": "Objeto aninhado"}
SYMBOL_NAMES = {"line": "Linha", "polyline": "Polilinha", "rect": "Retângulo",
                "circle": "Círculo", "arc": "Arco"}
FIELD_LABELS = {"x": "x", "y": "y", "z": "z", "width": "Largura (x)",
                "depth": "Profundidade (y)", "height": "Altura (z)", "rotation": "Rotação (°)",
                "radius": "Raio", "offset": "Deslocamento", "thickness": "Espessura",
                "angle": "Ângulo (°)", "start": "Início (°)", "end": "Fim (°)"}
HANDLES = [("Nenhuma", None), ("x, fim", ("x", "end")), ("x, início", ("x", "start")),
           ("x, simétrica", ("x", "symmetric")), ("y, fim", ("y", "end")),
           ("y, início", ("y", "start")), ("y, simétrica", ("y", "symmetric"))]
PARAM_COLUMNS = ["Identificador", "Rótulo", "Tipo do valor", "Nível", "Valor ou fórmula",
                 "Mín.", "Máx.", "Grupo", "Opções", "Alça"]


def field_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, (int, float)):
        return fmt(value)
    return str(value)


def field_value(text: str):
    """Número, se o texto for um; senão, a fórmula (sem o ``=`` do começo)."""
    text = text.strip()
    if not text:
        return None
    try:
        return parse_number(text)
    except ValueError:
        return text.removeprefix("=").strip()


def _param_value_text(p: dict) -> str:
    if p.get("formula"):
        return f"= {p['formula']}"
    if p["kind"] == "bool":
        return "sim" if p.get("value") else "não"
    return field_text(p.get("value"))


def _parse_param_value(p: dict, text: str) -> None:
    text = text.strip()
    if text.startswith("="):
        p["formula"], p["value"] = text[1:].strip() or None, None
        return
    p["formula"] = None
    kind = p["kind"]
    if kind == "bool":
        p["value"] = text.casefold() in ("sim", "s", "verdadeiro", "1", "true")
    elif od.KINDS[kind] == od.NUMBER:
        try:
            number = parse_number(text) if text else 0.0
        except ValueError:
            p["value"] = text  # o erro aparece na linha (valor deve ser um número)
            return
        p["value"] = round(number) if kind == "integer" else number
    else:
        p["value"] = text


class ObjectEditor(QDialog):
    def __init__(self, session, object_id: str | None = None, base: dict | None = None,
                 parent=None):
        super().__init__(parent)
        self.session = session
        doc = session.doc
        self.object_id = object_id
        if object_id:
            types = ot.types_of_definition(doc, object_id)
            if not types:
                raise OpError("nenhum tipo do projeto usa esta definição")
            states = [ot.read(t) for t in types]
            self.defn = copy.deepcopy(states[0]["definition"])
            self.types = [{"gid": t.GlobalId, "name": s["name"], "values": dict(s["values"]),
                           "defaults": dict(s["defaults"])} for t, s in zip(types, states,
                                                                            strict=True)]
            self.library = states[0]["library"]
        else:
            self.defn = od.normalized(base) if base else od.new_definition("Objeto novo")
            if base:
                from brasbim.core import guid

                self.defn["object_id"] = guid.new()
                self.defn["version"] = 1
                self.defn["name"] = f"{self.defn['name']} (cópia)"
            self.types = [{"gid": None, "name": self.defn["name"], "values": {},
                           "defaults": {}}]
            self.library = None
        self.setWindowTitle(f"Editar objeto: {self.defn['name']}" if object_id
                            else "Novo objeto")
        self.resize(1180, 720)
        self.test_values: dict = {}
        self.test_type = 0
        self.problems: list[od.Problem] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._update)
        self._building = False
        self._build()
        self._update()

    # --- montagem ---------------------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._params_tab(), "Parâmetros")
        self.tabs.addTab(self._pieces_tab("pieces"), "Peças")
        self.tabs.addTab(self._pieces_tab("symbol"), "Símbolo 2D")
        self.tabs.addTab(self._object_tab(), "Objeto")
        self.tabs.addTab(self._types_tab(), "Tipos")
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._preview_side())
        splitter.setSizes([720, 420])
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet(f"color: {theme.ERROR}")
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        if self.library:
            note = QLabel("Veio da biblioteca: Atualizar da biblioteca desfaria as "
                          "mudanças feitas aqui.")
            note.setStyleSheet(f"color: {theme.INK_SOFT}")
            buttons.addWidget(note)
        buttons.addStretch(1)
        self.apply_button = QPushButton("Aplicar ao projeto")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply)
        self.save_button = QPushButton("Gravar na biblioteca")
        self.save_button.clicked.connect(self.save_to_library)
        close = QPushButton("Fechar")
        close.clicked.connect(self.reject)
        for b in (self.apply_button, self.save_button, close):
            buttons.addWidget(b)
        layout.addLayout(buttons)

    def _small(self, icon_name: str, tip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setIcon(icon(icon_name))
        b.setToolTip(tip)
        b.clicked.connect(slot)
        return b

    # parâmetros

    def _params_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        self.param_table = QTableWidget(0, len(PARAM_COLUMNS))
        self.param_table.setHorizontalHeaderLabels(PARAM_COLUMNS)
        self.param_table.verticalHeader().hide()
        self.param_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.param_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        v.addWidget(self.param_table, 1)
        self.param_table.itemChanged.connect(self._param_edited)
        row = QHBoxLayout()
        add = QPushButton("Acrescentar parâmetro")
        add.clicked.connect(self.add_param)
        remove = QPushButton("Excluir")
        remove.clicked.connect(self.remove_param)
        row.addWidget(add)
        row.addWidget(remove)
        row.addWidget(self._small("up", "Subir", lambda: self.move_param(-1)))
        row.addWidget(self._small("down", "Descer", lambda: self.move_param(1)))
        row.addStretch(1)
        v.addLayout(row)
        self.param_error = QLabel()
        self.param_error.setWordWrap(True)
        self.param_error.setStyleSheet(f"color: {theme.ERROR}")
        v.addWidget(self.param_error)
        self._fill_params()
        return page

    def _fill_params(self) -> None:
        self._building = True
        table = self.param_table
        table.setRowCount(len(self.defn["params"]))
        for r, p in enumerate(self.defn["params"]):
            builtin = od.is_builtin(p)
            for c, text in enumerate((p["name"], p["label"], None, None, _param_value_text(p),
                                      field_text(p.get("min")), field_text(p.get("max")),
                                      None, "; ".join(p.get("options") or []), None)):
                if text is None:
                    continue
                item = QTableWidgetItem(text)
                if builtin and c in (0, 1):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(r, c, item)
            kind = QComboBox()
            for k, label in od.KIND_LABELS.items():
                kind.addItem(label, k)
            kind.setCurrentIndex(kind.findData(p["kind"]))
            kind.setEnabled(not builtin)
            kind.currentIndexChanged.connect(
                lambda i, row=r, w=kind: self._param_set(row, "kind", w.itemData(i)))
            table.setCellWidget(r, 2, kind)
            level = QComboBox()
            level.addItem("Tipo", "type")
            level.addItem("Ocorrência", "occurrence")
            level.setCurrentIndex(level.findData(p["level"]))
            level.setEnabled(not builtin)
            level.currentIndexChanged.connect(
                lambda i, row=r, w=level: self._param_set(row, "level", w.itemData(i)))
            table.setCellWidget(r, 3, level)
            group = QComboBox()
            for g in od.GROUPS:
                group.addItem(g, g)
            group.setCurrentIndex(max(0, group.findData(p.get("group"))))
            group.currentIndexChanged.connect(
                lambda i, row=r, w=group: self._param_set(row, "group", w.itemData(i)))
            table.setCellWidget(r, 7, group)
            handle = QComboBox()
            for label, value in HANDLES:
                handle.addItem(label, value)
            current = p.get("handle")
            index = next((i for i, (_, v) in enumerate(HANDLES)
                          if v and current and v == (current.get("axis"), current.get("side"))),
                         0)
            handle.setCurrentIndex(index)
            handle.currentIndexChanged.connect(
                lambda i, row=r, w=handle: self._param_set(row, "handle", w.itemData(i)))
            table.setCellWidget(r, 9, handle)
        self._building = False

    def _param_set(self, row: int, key: str, value) -> None:
        if self._building:
            return
        p = self.defn["params"][row]
        if key == "handle":
            p["handle"] = {"axis": value[0], "side": value[1]} if value else None
        else:
            p[key] = value
        if key == "kind":
            if p["kind"] == "choice" and not p.get("options"):
                p["options"] = ["opção 1"]
            if not p.get("formula"):
                p["value"] = od.default_value(p)
            self._fill_params()
        self.changed()

    def _param_edited(self, item: QTableWidgetItem) -> None:
        if self._building:
            return
        p = self.defn["params"][item.row()]
        text = item.text()
        column = item.column()
        if column == 0:
            old = p["name"]
            p["name"] = text.strip()
            self._rename_param(old, p["name"])
        elif column == 1:
            p["label"] = text.strip()
        elif column == 4:
            _parse_param_value(p, text)
        elif column in (5, 6):
            try:
                p["min" if column == 5 else "max"] = parse_number(text) if text.strip() \
                    else None
            except ValueError:
                pass
        elif column == 8:
            p["options"] = [o.strip() for o in text.split(";") if o.strip()] or None
        self.changed()

    def _rename_param(self, old: str, new: str) -> None:
        """Os valores guardados nos tipos acompanham o identificador renomeado."""
        if not old or old == new:
            return
        for spec in self.types:
            for key in ("values", "defaults"):
                if old in spec[key]:
                    spec[key][new] = spec[key].pop(old)

    def add_param(self) -> None:
        taken = {fm.key(p["name"]) for p in self.defn["params"]}
        n = 1
        while f"parametro{n}" in taken:
            n += 1
        self.defn["params"].append(od.new_param(f"parametro{n}", "length", "type", 0.5,
                                                label=f"Parâmetro {n}"))
        self._fill_params()
        self.param_table.selectRow(len(self.defn["params"]) - 1)
        self.changed()

    def remove_param(self) -> None:
        row = self.param_table.currentRow()
        if row < 0 or od.is_builtin(self.defn["params"][row]):
            return
        del self.defn["params"][row]
        self._fill_params()
        self.changed()

    def move_param(self, step: int) -> None:
        row = self.param_table.currentRow()
        params = self.defn["params"]
        new = row + step
        if row < 0 or not 0 <= new < len(params):
            return
        params[row], params[new] = params[new], params[row]
        self._fill_params()
        self.param_table.selectRow(new)
        self.changed()

    # peças e símbolo

    def _items(self, which: str) -> list:
        return self.defn["pieces"] if which == "pieces" else self.defn["symbol"]["items"]

    def _pieces_tab(self, which: str) -> QWidget:
        page = QWidget()
        h = QHBoxLayout(page)
        left = QVBoxLayout()
        if which == "symbol":
            mode = QComboBox()
            mode.addItem("Automático (as peças vistas de cima)", "auto")
            mode.addItem("Desenhado", "drawn")
            mode.setCurrentIndex(mode.findData(self.defn["symbol"].get("mode", "auto")))
            mode.currentIndexChanged.connect(lambda i: self._symbol_mode(mode.itemData(i)))
            left.addWidget(mode)
        listing = QListWidget()
        listing.setMinimumWidth(200)
        left.addWidget(listing, 1)
        row = QHBoxLayout()
        add = QPushButton("Acrescentar")
        menu = QMenu(add)
        names = PIECE_NAMES if which == "pieces" else SYMBOL_NAMES
        for kind, label in names.items():
            menu.addAction(label, lambda k=kind: self.add_item(which, k))
        add.setMenu(menu)
        row.addWidget(add)
        row.addWidget(self._small("copy", "Duplicar", lambda: self.duplicate_item(which)))
        row.addWidget(self._small("delete", "Excluir", lambda: self.remove_item(which)))
        row.addWidget(self._small("up", "Subir", lambda: self.move_item(which, -1)))
        row.addWidget(self._small("down", "Descer", lambda: self.move_item(which, 1)))
        left.addLayout(row)
        h.addLayout(left)
        form_holder = QWidget()
        form_layout = QVBoxLayout(form_holder)
        form_layout.setContentsMargins(0, 0, 0, 0)
        h.addWidget(form_holder, 1)
        setattr(self, f"{which}_list", listing)
        setattr(self, f"{which}_form", form_layout)
        listing.currentRowChanged.connect(lambda r: self._show_item(which, r))
        self._fill_items(which)
        return page

    def _symbol_mode(self, mode: str) -> None:
        self.defn["symbol"]["mode"] = mode
        self.changed()

    def _item_text(self, which: str, item: dict) -> str:
        names = PIECE_NAMES if which == "pieces" else SYMBOL_NAMES
        text = names.get(item["kind"], item["kind"])
        name = item.get("name")
        return f"{name} — {text}" if name else text

    def _fill_items(self, which: str, select: int | None = None) -> None:
        listing = getattr(self, f"{which}_list")
        listing.blockSignals(True)
        listing.clear()
        for item in self._items(which):
            listing.addItem(QListWidgetItem(self._item_text(which, item)))
        listing.blockSignals(False)
        if self._items(which):
            listing.setCurrentRow(select if select is not None else 0)
        else:
            self._show_item(which, -1)

    def add_item(self, which: str, kind: str) -> None:
        items = self._items(which)
        items.append(od.new_piece(kind) if which == "pieces" else od.new_symbol_item(kind))
        self._fill_items(which, len(items) - 1)
        self.changed()

    def duplicate_item(self, which: str) -> None:
        listing = getattr(self, f"{which}_list")
        r = listing.currentRow()
        items = self._items(which)
        if r < 0:
            return
        items.insert(r + 1, copy.deepcopy(items[r]))
        self._fill_items(which, r + 1)
        self.changed()

    def remove_item(self, which: str) -> None:
        listing = getattr(self, f"{which}_list")
        r = listing.currentRow()
        items = self._items(which)
        if r < 0:
            return
        del items[r]
        self._fill_items(which, max(0, r - 1) if items else None)
        self.changed()

    def move_item(self, which: str, step: int) -> None:
        listing = getattr(self, f"{which}_list")
        r = listing.currentRow()
        items = self._items(which)
        new = r + step
        if r < 0 or not 0 <= new < len(items):
            return
        items[r], items[new] = items[new], items[r]
        self._fill_items(which, new)
        self.changed()

    def _clear(self, layout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget is not None:  # some na hora (o deleteLater só vem depois)
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _show_item(self, which: str, r: int) -> None:
        layout = getattr(self, f"{which}_form")
        self._clear(layout)
        self.value_labels = getattr(self, "value_labels", {})
        self.value_labels[which] = {}
        items = self._items(which)
        if r < 0 or r >= len(items):
            empty = QLabel("Acrescente uma peça para começar." if which == "pieces"
                           else "No modo automático o símbolo vem das peças.")
            empty.setStyleSheet(f"color: {theme.INK_SOFT}")
            layout.addWidget(empty)
            layout.addStretch(1)
            return
        item = items[r]
        holder = QWidget()
        form = QFormLayout(holder)
        layout.addWidget(holder)
        if which == "pieces":
            name = QLineEdit(item.get("name") or "")
            name.editingFinished.connect(lambda: self._set_item(which, r, "name",
                                                                name.text().strip(), True))
            form.addRow("Nome", name)
        fields = (od._PIECE_FIELDS if which == "pieces" else od._SYMBOL_FIELDS)[item["kind"]]
        for key in fields:
            self._formula_row(form, which, r, key, FIELD_LABELS.get(key, key), item.get(key))
        if item["kind"] == "cylinder":
            self._choice_row(form, which, r, "axis", "Eixo", [("z", "z"), ("x", "x"),
                                                             ("y", "y")], item.get("axis"))
        if item["kind"] == "extrusion":
            self._choice_row(form, which, r, "plane", "Plano",
                             [("Planta (x, y)", "xy"), ("Frente (x, z)", "xz"),
                              ("Lado (y, z)", "yz")], item.get("plane"))
        if item["kind"] in ("extrusion", "revolution", "line", "polyline"):
            form.addRow("Pontos" if item["kind"] != "revolution" else "Perfil (raio; z)",
                        self._points_table(which, r, item))
        if item["kind"] == "polyline":
            self._check_row(form, which, r, "closed", "Fechada", item.get("closed"))
        if which == "symbol" and item["kind"] in ("rect", "circle", "polyline"):
            self._check_row(form, which, r, "fill", "Com fundo", item.get("fill"))
        if which == "pieces" and item["kind"] == "object":
            self._nested_rows(form, r, item)
        elif which == "pieces":
            roles = [(od.ROLE_LABELS.get(x, x), x) for x in od.ROLES[self.defn["category"]]]
            self._choice_row(form, which, r, "role", "Papel", [("—", None), *roles],
                             item.get("role"))
            self._material_row(form, r, item)
            if item["kind"] == "box":
                self._check_row(form, which, r, "void", "É o vão na parede", item.get("void"))
        self._formula_row(form, which, r, "visible", "Visível quando", item.get("visible"))
        repeat = item.get("repeat") or {}
        for key, label in (("count", "Repetir: quantidade"), ("dx", "Repetir: passo x"),
                           ("dy", "Repetir: passo y"), ("dz", "Repetir: passo z"),
                           ("length", "Distribuir no comprimento")):
            self._formula_row(form, which, r, f"repeat.{key}", label, repeat.get(key))
        layout.addStretch(1)
        self._update_values()

    def _formula_row(self, form, which, r, key, label, value) -> None:
        line = QLineEdit(field_text(value))
        line.setPlaceholderText("número ou fórmula")
        shown = QLabel()
        shown.setStyleSheet(f"color: {theme.INK_SOFT}")
        shown.setMinimumWidth(70)
        row = QHBoxLayout()
        row.addWidget(line, 1)
        row.addWidget(shown)
        holder = QWidget()
        row.setContentsMargins(0, 0, 0, 0)
        holder.setLayout(row)
        form.addRow(label, holder)
        self.value_labels[which][key] = shown

        def done():
            self._set_item(which, r, key, field_value(line.text()))

        line.textEdited.connect(lambda _t: self._delayed(done))
        line.editingFinished.connect(done)

    def _delayed(self, fn) -> None:
        self._pending = fn
        QTimer.singleShot(PREVIEW_MS, lambda: getattr(self, "_pending", None) is fn and fn())

    def _choice_row(self, form, which, r, key, label, options, current) -> None:
        combo = QComboBox()
        for text, value in options:
            combo.addItem(text, value)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.currentIndexChanged.connect(
            lambda i: self._set_item(which, r, key, combo.itemData(i)))
        form.addRow(label, combo)

    def _check_row(self, form, which, r, key, label, current) -> None:
        box = QCheckBox()
        box.setChecked(bool(current))
        box.toggled.connect(lambda v: self._set_item(which, r, key, bool(v)))
        form.addRow(label, box)

    def _material_row(self, form, r, item) -> None:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("—", None)
        materials = sorted({m.Name for m in self.session.doc.ifc.by_type("IfcMaterial")}
                           | set(material_library.LIBRARY))
        for name in materials:
            combo.addItem(name, name)
        for p in self.defn["params"]:
            if p["kind"] == "material":
                combo.addItem(f"Parâmetro: {p['label']}", {"param": p["name"]})
        current = item.get("material")
        index = combo.findData(current)
        if index < 0 and isinstance(current, str):
            combo.addItem(current, current)
            index = combo.count() - 1
        combo.setCurrentIndex(max(0, index))

        def chosen(i):
            data = combo.itemData(i)
            self._set_item("pieces", r, "material", data if data is not None or i == 0
                           else combo.itemText(i))

        combo.currentIndexChanged.connect(chosen)
        form.addRow("Material", combo)

    def _nested_rows(self, form, r, item) -> None:
        combo = QComboBox()
        combo.addItem("—", None)
        for t in ot.all_types(self.session.doc):
            if ot.definition_of(t)["object_id"] != self.defn["object_id"]:
                combo.addItem(t.Name, t.Name)
        for p in self.defn["params"]:
            if p["kind"] == "object_type":
                combo.addItem(f"Parâmetro: {p['label']}", {"param": p["name"]})
        combo.setCurrentIndex(max(0, combo.findData(item.get("type"))))
        combo.currentIndexChanged.connect(
            lambda i: self._set_item("pieces", r, "type", combo.itemData(i)))
        form.addRow("Tipo aninhado", combo)
        self._check_row(form, "pieces", r, "mirror", "Espelhado", item.get("mirror"))
        links = QLineEdit("; ".join(f"{k} = {field_text(v)}"
                                    for k, v in (item.get("values") or {}).items()))
        links.setPlaceholderText("parâmetro = fórmula, separados por ;")
        links.setToolTip("Parâmetros de ocorrência do aninhado ligados aos deste objeto. "
                         "Ex.: assento = altura - 0,30")

        def done():
            values = {}
            for part in links.text().split(";"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k.strip():
                        values[k.strip()] = field_value(v)
            self._set_item("pieces", r, "values", values)

        links.editingFinished.connect(done)
        form.addRow("Ligações", links)

    def _points_table(self, which: str, r: int, item: dict) -> QWidget:
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["1ª coordenada", "2ª coordenada"])
        table.verticalHeader().setDefaultSectionSize(22)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(140)
        points = item.get("points") or []
        table.setRowCount(len(points))
        for i, (a, b) in enumerate(points):
            table.setItem(i, 0, QTableWidgetItem(field_text(a)))
            table.setItem(i, 1, QTableWidgetItem(field_text(b)))

        def read():
            out = []
            for i in range(table.rowCount()):
                a, b = table.item(i, 0), table.item(i, 1)
                out.append([field_value(a.text() if a else "") or 0,
                            field_value(b.text() if b else "") or 0])
            self._set_item(which, r, "points", out)

        table.itemChanged.connect(lambda _i: read())
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(table)
        row = QHBoxLayout()
        add = QPushButton("Ponto +")
        add.clicked.connect(lambda: (table.insertRow(table.rowCount()), [
            table.setItem(table.rowCount() - 1, c, QTableWidgetItem("0")) for c in (0, 1)],
            read()))
        remove = QPushButton("Ponto −")
        remove.clicked.connect(lambda: (table.removeRow(table.currentRow() if
                                                        table.currentRow() >= 0
                                                        else table.rowCount() - 1), read()))
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        v.addLayout(row)
        return holder

    def _set_item(self, which: str, r: int, key: str, value, relabel: bool = False) -> None:
        items = self._items(which)
        if r >= len(items):
            return
        item = items[r]
        if key.startswith("repeat."):
            sub = key.split(".", 1)[1]
            repeat = dict(item.get("repeat") or {})
            if value is None or value == "":
                repeat.pop(sub, None)
            else:
                repeat[sub] = value
            item["repeat"] = repeat if repeat.get("count") not in (None, "") else None
            if item["repeat"] is None and repeat:
                item["repeat"] = {"count": 1, **repeat}
        else:
            item[key] = value
        if relabel:
            getattr(self, f"{which}_list").item(r).setText(self._item_text(which, item))
        self.changed()

    # objeto e tipos

    def _object_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        name = QLineEdit(self.defn["name"])
        name.editingFinished.connect(lambda: self._set_defn("name", name.text().strip()))
        form.addRow("Nome", name)
        category = QComboBox()
        for key, (_, _, _, label) in od.CATEGORIES.items():
            category.addItem(label, key)
        category.setCurrentIndex(category.findData(self.defn["category"]))
        category.setEnabled(self.object_id is None)  # a classe IFC dos tipos já gravados fica
        form.addRow("Categoria", category)
        predefined = QComboBox()
        form.addRow("Tipo predefinido (IFC)", predefined)

        def fill_predefined():
            predefined.blockSignals(True)
            predefined.clear()
            for value in od.PREDEFINED[self.defn["category"]]:
                predefined.addItem(value, value)
            predefined.setCurrentIndex(max(0, predefined.findData(
                self.defn["predefined_type"])))
            predefined.blockSignals(False)

        def set_category(i):
            self.defn["category"] = category.itemData(i)
            if self.defn["predefined_type"] not in od.PREDEFINED[self.defn["category"]]:
                self.defn["predefined_type"] = od.PREDEFINED[self.defn["category"]][0]
            fill_predefined()
            self.changed()

        category.currentIndexChanged.connect(set_category)
        fill_predefined()
        predefined.currentIndexChanged.connect(
            lambda i: self._set_defn("predefined_type", predefined.itemData(i)))
        element_type = QLineEdit(self.defn.get("element_type") or "")
        element_type.setPlaceholderText("usado com USERDEFINED (padrão: o nome)")
        element_type.editingFinished.connect(
            lambda: self._set_defn("element_type", element_type.text().strip() or None))
        form.addRow("Nome do tipo IFC", element_type)
        hosting = QComboBox()
        hosting.addItem("Livre", "free")
        hosting.addItem("Preso à parede", "wall")
        hosting.setCurrentIndex(hosting.findData(self.defn["hosting"]))
        hosting.currentIndexChanged.connect(
            lambda i: self._set_defn("hosting", hosting.itemData(i)))
        form.addRow("Hospedagem", hosting)
        description = QLineEdit(self.defn.get("description") or "")
        description.editingFinished.connect(
            lambda: self._set_defn("description", description.text().strip()))
        form.addRow("Descrição", description)
        note = QLabel("Convenção das peças: origem no ponto de inserção, x para a direita, "
                      "y para trás (a frente olha para −y), z para cima. Medidas em metros "
                      "e ângulos em graus; fórmulas com vírgula decimal e ; entre "
                      "argumentos: máx(largura - 2 * braco; 0,40).")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.INK_SOFT}")
        form.addRow(note)
        return page

    def _set_defn(self, key: str, value) -> None:
        if key == "name" and self.object_id is None and len(self.types) == 1                 and self.types[0]["name"] == self.defn["name"]:
            self.types[0]["name"] = value  # o tipo único do objeto novo acompanha o nome
            if hasattr(self, "types_table"):
                self._fill_types()
        self.defn[key] = value
        self.changed()

    def _types_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        self.types_table = QTableWidget()
        self.types_table.verticalHeader().hide()
        v.addWidget(self.types_table, 1)
        self.types_table.itemChanged.connect(self._type_edited)
        row = QHBoxLayout()
        add = QPushButton("Duplicar tipo")
        add.clicked.connect(self.duplicate_type)
        remove = QPushButton("Excluir tipo")
        remove.clicked.connect(self.remove_type)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        v.addLayout(row)
        self._fill_types()
        return page

    def _type_params(self) -> list[dict]:
        return [p for p in od.type_params(self.defn) if od.editable(p)]

    def _fill_types(self) -> None:
        params = self._type_params()
        table = self.types_table
        table.blockSignals(True)
        table.setColumnCount(1 + len(params))
        table.setHorizontalHeaderLabels(["Nome"] + [ow.label(p) for p in params])
        table.setRowCount(len(self.types))
        for r, spec in enumerate(self.types):
            table.setItem(r, 0, QTableWidgetItem(spec["name"]))
            for c, p in enumerate(params, start=1):
                value = spec["values"].get(p["name"], p.get("value"))
                table.setItem(r, c, QTableWidgetItem(field_text(value)))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.blockSignals(False)
        if hasattr(self, "test_combo"):
            self._fill_test_types()

    def _type_edited(self, item: QTableWidgetItem) -> None:
        spec = self.types[item.row()]
        if item.column() == 0:
            spec["name"] = item.text().strip()
            self._fill_test_types()
            return
        p = self._type_params()[item.column() - 1]
        holder = {**p}
        _parse_param_value(holder, item.text())
        spec["values"][p["name"]] = holder["value"]
        self.changed()

    def duplicate_type(self) -> None:
        r = max(0, self.types_table.currentRow())
        spec = copy.deepcopy(self.types[r])
        spec["gid"] = None
        names = {t["name"] for t in self.types}
        n = 2
        while f"{spec['name']} ({n})" in names:
            n += 1
        spec["name"] = f"{spec['name']} ({n})"
        self.types.append(spec)
        self._fill_types()
        self.changed()

    def remove_type(self) -> None:
        r = self.types_table.currentRow()
        if r < 0 or len(self.types) == 1:
            return
        del self.types[r]
        self.test_type = min(self.test_type, len(self.types) - 1)
        self._fill_types()
        self.changed()

    # prévia

    def _preview_side(self) -> QWidget:
        side = QWidget()
        v = QVBoxLayout(side)
        top = QHBoxLayout()
        top.addWidget(QLabel("Tipo de teste"))
        self.test_combo = QComboBox()
        self.test_combo.currentIndexChanged.connect(self._test_type_chosen)
        top.addWidget(self.test_combo, 1)
        self.mode_buttons = {}
        for mode, icon_name, tip in (("plan", "view_plan", "Planta"), ("3d", "view_3d", "3D")):
            b = QToolButton()
            b.setIcon(icon(icon_name))
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, m=mode: self._set_mode(m))
            top.addWidget(b)
            self.mode_buttons[mode] = b
        v.addLayout(top)
        self.preview = object_preview.PreviewWidget()
        v.addWidget(self.preview, 1)
        self.test_form_holder = QWidget()
        self.test_form = QFormLayout(self.test_form_holder)
        v.addWidget(QLabel("<b>Valores de teste</b> (parâmetros de ocorrência)"))
        v.addWidget(self.test_form_holder)
        self._set_mode("3d")
        self._fill_test_types()
        return side

    def _set_mode(self, mode: str) -> None:
        for m, b in self.mode_buttons.items():
            b.setChecked(m == mode)
        self.preview.set_mode(mode)

    def _fill_test_types(self) -> None:
        self.test_combo.blockSignals(True)
        self.test_combo.clear()
        for spec in self.types:
            self.test_combo.addItem(spec["name"])
        self.test_combo.setCurrentIndex(min(self.test_type, len(self.types) - 1))
        self.test_combo.blockSignals(False)

    def _test_type_chosen(self, i: int) -> None:
        self.test_type = max(0, i)
        self.changed()

    def _fill_test_form(self) -> None:
        while self.test_form.rowCount():
            self.test_form.removeRow(0)
        spec = self.types[self.test_type]
        for p in od.occurrence_params(self.defn):
            if not od.editable(p) or p["name"] == "elevacao":
                continue
            value = self.test_values.get(p["name"], spec["defaults"].get(p["name"],
                                                                         p.get("value")))
            self.test_form.addRow(ow.label(p), ow.param_widget(
                p, value, lambda v, n=p["name"]: self._test_set(n, v), self.session.doc))

    def _test_set(self, name: str, value) -> None:
        self.test_values[name] = value
        self.changed(rebuild_form=False)

    def changed(self, rebuild_form: bool = True) -> None:
        self._rebuild_form = rebuild_form or getattr(self, "_rebuild_form", False)
        self._timer.start(PREVIEW_MS)

    def _values(self) -> dict:
        spec = self.types[min(self.test_type, len(self.types) - 1)]
        return od.evaluate(self.defn, spec["values"], {**spec["defaults"], **self.test_values})

    def _update(self) -> None:
        self.defn = od.normalized(self.defn)
        self.problems = od.problems(self.defn)
        self._mark_problems()
        if getattr(self, "_rebuild_form", True):
            self._fill_test_form()
            self._rebuild_form = False
        if self.problems:
            first = self.problems[0]
            self.preview.set_content([], [], first.message)
            self.error.setText(f"{len(self.problems)} problema(s): {first.message}")
            self.apply_button.setEnabled(False)
            return
        try:
            values = self._values()
            resolve = ow.resolver_for(self.session.doc)
            tris = object_mesh.object_mesh(self.defn, values, resolve)
            symbol = object_preview.symbol_of(self.defn, values, resolve)
        except OpError as e:
            self.preview.set_content([], [], str(e))
            self.error.setText(str(e))
            self.apply_button.setEnabled(False)
            return
        self.preview.set_content(tris, symbol)
        self.error.setText("")
        self.apply_button.setEnabled(True)
        self._update_values()

    def _update_values(self) -> None:
        """Resultado das fórmulas ao lado dos campos da peça escolhida."""
        labels = getattr(self, "value_labels", {})
        try:
            values = self._values()
        except OpError:
            values = None
        for which, found in labels.items():
            listing = getattr(self, f"{which}_list", None)
            r = listing.currentRow() if listing is not None else -1
            items = self._items(which)
            if r < 0 or r >= len(items):
                continue
            item = items[r]
            for key, label in found.items():
                if key.startswith("repeat."):
                    raw = (item.get("repeat") or {}).get(key.split(".", 1)[1])
                else:
                    raw = item.get(key)
                text = ""
                if values is not None and isinstance(raw, str) and raw.strip():
                    try:
                        result = fm.calc(raw, values)
                        text = field_text(result)
                    except OpError as e:
                        text = "erro"
                        label.setToolTip(str(e))
                try:
                    label.setText(text)
                except RuntimeError:
                    pass

    def _mark_problems(self) -> None:
        table = self.param_table
        bad = {}
        for p in self.problems:
            if p.where[0] == "param":
                bad.setdefault(p.where[1], p.message)
        self._building = True
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item is None:
                    continue
                item.setBackground(QColor(theme.ERROR_SOFT) if r in bad else QColor(0, 0, 0, 0))
                item.setToolTip(bad.get(r, ""))
        self._building = False
        pieces = [p for p in self.problems if p.where[0] in ("piece", "symbol", "object")]
        messages = [bad[r] for r in sorted(bad)][:3]
        where = {"piece": "peça", "symbol": "símbolo", "object": "objeto"}
        messages += [f"{where[p.where[0]]} "
                     f"{p.where[1] + 1 if isinstance(p.where[1], int) else ''}: {p.message}"
                     for p in pieces][:3]
        self.param_error.setText("\n".join(messages))

    # --- gravar ------------------------------------------------------------------------

    def apply(self) -> bool:
        """Aplicar ao projeto (§5.3): nada é gravado se alguma ocorrência recusar."""
        self._update()
        if self.problems:
            return False
        doc = self.session.doc
        try:
            tx = oc.apply_definition(doc, self.object_id, self.defn, self.types)
        except OpError as e:
            QMessageBox.warning(self, "Não foi possível aplicar", str(e))
            self.error.setText(str(e).splitlines()[0])
            return False
        if not self.session.run(tx):
            self.error.setText(self.session.messages[-1]["text"])
            return False
        self.object_id = self.defn["object_id"]
        found = ot.types_of_definition(doc, self.object_id)
        by_name = {t.Name: t.GlobalId for t in found}
        for spec in self.types:
            spec["gid"] = by_name.get(spec["name"], spec.get("gid"))
        self.defn = copy.deepcopy(ot.read(found[0])["definition"])
        self.setWindowTitle(f"Editar objeto: {self.defn['name']}")
        self.error.setText(f"Aplicado ao projeto (versão {self.defn['version']}).")
        self.error.setStyleSheet(f"color: {theme.OK}")
        return True

    def save_to_library(self) -> None:
        unsaved = self.object_id is None or any(s.get("gid") is None for s in self.types)
        if unsaved and not self.apply():
            return
        window = self.parent()
        if window is not None and hasattr(window, "save_object_to_library"):
            window.save_object_to_library(self.object_id)
