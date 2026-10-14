# SPDX-License-Identifier: GPL-3.0-or-later
"""Painel de propriedades (``spec/ui/01-janela-e-ferramentas.md`` §7 e
``spec/ui/02-edicao.md`` §9).

Mostra a seleção (parede, porta, ou vários elementos com edição em lote). As opções da
ferramenta ativa ficam na barra Opções (``spec/ui/03-barras-e-icones.md`` §4.3).

Os campos são montados como grupos (título + linhas) e desenhados em pé (painel nas
laterais) ou deitados, em blocos lado a lado (painel no topo ou na base;
``spec/ui/04-painel-de-propriedades.md``). Cada campo confirmado gera uma transação; recusas do núcleo voltam o
campo ao valor anterior (o painel é refeito a partir do modelo).
"""

from __future__ import annotations

import re
from collections import Counter

import ifcopenshell.util.element
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.ops.history import combine
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings, rebuild
from brasbim.core.walls import params as wall_params
from brasbim.core.walls import types as wall_types
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui.tools import block_grid, fmt, parse_number

REF_LINES = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
TOPS = [("Pavimento de cima", "storey"), ("Altura fixa", "fixed")]
OPENS_TO = [("Face esquerda da parede", "left"), ("Face direita da parede", "right")]
HINGES = [("Esquerda", "left"), ("Direita", "right")]
ALIGNS = [("Face esquerda", "left_face"), ("Eixo", "axis"), ("Face direita", "right_face")]
_INVALID = "QLineEdit { background: #fde2df; }"
MIXED = "vários"


ROW_HEIGHT = 27  # altura de uma linha de campo no arranjo deitado (px)
TITLE_HEIGHT = 22


class _Group:
    """Grupo de campos: título e linhas (nome ou None, widget)."""

    def __init__(self, title: str = ""):
        self.title = title
        self.rows: list[tuple[str | None, QWidget]] = []


def _common(values):
    """O valor comum a todos, ou ``None`` se diferem (campo "vários")."""
    values = list(values)
    first = values[0]
    return first if all(v == first for v in values[1:]) else None


class PropertiesPanel(QScrollArea):
    def __init__(self, session, toolbox, parent=None):
        super().__init__(parent)
        self.session = session
        self.toolbox = toolbox
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._pending = False
        self.edit_type = None  # abre a janela de tipos (posto pela janela principal)
        self.lying = False  # arranjo deitado (spec/ui 04 §2)
        self.lines = 0  # linhas por bloco no arranjo deitado
        self.refresh()

    # --- refazer o painel ------------------------------------------------------------

    def refresh(self) -> None:
        """Refaz o painel depois do evento atual (um campo pode estar emitindo o sinal)."""
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self._rebuild)

    def wants_lying(self) -> bool:
        return self.width() >= 2 * self.height()

    def lines_available(self) -> int:
        return max(1, (self.viewport().height() - TITLE_HEIGHT - 12) // ROW_HEIGHT)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        lying = self.wants_lying()
        if lying != self.lying or (lying and self.lines_available() != self.lines):
            focus = QApplication.focusWidget()
            if focus is not None and self.isAncestorOf(focus):
                return  # não atrapalha quem está digitando (spec/ui 04 §3)
            self.refresh()

    def _rebuild(self) -> None:
        self._pending = False
        self.groups = [_Group()]
        selection = [self.session.doc.find(g) for g in sorted(self.session.selection)]
        selection = [e for e in selection if e is not None]
        if len(selection) == 1 and selection[0].is_a("IfcWall"):
            self._wall(selection[0])
        elif len(selection) == 1 and selection[0].is_a("IfcDoor"):
            self._door(selection[0])
        elif selection:
            self._title(f"{len(selection)} elementos selecionados")
            walls = [e for e in selection if e.is_a("IfcWall")]
            door_list = [e for e in selection if e.is_a("IfcDoor")]
            if walls:
                self._walls(walls)
            if door_list:
                self._doors(door_list)
            others = Counter(e.is_a() for e in selection
                             if not e.is_a("IfcWall") and not e.is_a("IfcDoor"))
            for cls, n in sorted(others.items()):
                self._add(cls, QLabel(str(n)))
        else:
            self._tool_options()
        self.lying = self.wants_lying()
        if self.lying:
            self._render_lying()
        else:
            self._render_standing()

    # --- arranjos ---------------------------------------------------------------------

    def _render_standing(self) -> None:
        """Em pé: grupos um abaixo do outro (spec 0.1 §7)."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        body = QWidget()
        self.layout_ = QVBoxLayout(body)
        form = self.form = QFormLayout()
        self.layout_.addLayout(form)
        for i, group in enumerate(self.groups):
            if group.title:
                text = f"<b>{group.title}</b>" if i == 0 else (
                    f"<span style='color:#666'>{group.title}</span>")
                label = QLabel(text)
                label.setWordWrap(True)
                form.addRow(label)
            for name, widget in group.rows:
                if name is None:
                    form.addRow(widget)
                else:
                    form.addRow(name, widget)
        self.layout_.addStretch(1)
        self.setWidget(body)

    def _render_lying(self) -> None:
        """Deitado: grupos em blocos lado a lado; campos em colunas dentro do bloco
        (spec/ui 04 §3)."""
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lines = self.lines_available()
        self.form = None
        body = QWidget()
        row = QHBoxLayout(body)
        row.setContentsMargins(4, 2, 4, 2)
        metrics = self.fontMetrics()
        blocks = [g for g in self.groups if g.title or g.rows]
        for i, group in enumerate(blocks):
            if i:
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setStyleSheet("color: #ccc")
                row.addWidget(line)
            block = QWidget()
            block.setObjectName("bloco")
            block.setProperty("titulo", group.title)
            column = QVBoxLayout(block)
            column.setContentsMargins(2, 0, 2, 0)
            column.setSpacing(2)
            title = QLabel(f"<b>{group.title}</b>" if i == 0 and group.title
                           else f"<span style='color:#666'>{group.title}</span>")
            column.addWidget(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(2)
            for (name, widget), (r, c) in zip(group.rows,
                                              block_grid(len(group.rows), self.lines),
                                              strict=True):
                self._compact(widget, metrics)
                if name is None:
                    grid.addWidget(widget, r, 2 * c, 1, 2)
                else:
                    label = QLabel(name)
                    label.setStyleSheet("color: #444")
                    grid.addWidget(label, r, 2 * c)
                    grid.addWidget(widget, r, 2 * c + 1)
            column.addLayout(grid)
            column.addStretch(1)
            row.addWidget(block)
        row.addStretch(1)
        self.setWidget(body)

    @staticmethod
    def _compact(widget: QWidget, metrics) -> None:
        if isinstance(widget, QLineEdit):
            widget.setMaximumWidth(metrics.horizontalAdvance("0") * 8 + 16)
        elif isinstance(widget, QComboBox):
            widget.setMaximumWidth(metrics.horizontalAdvance("M") * 15 + 30)
        elif isinstance(widget, QLabel) and widget.wordWrap():
            widget.setMaximumWidth(280)

    # --- campos ---------------------------------------------------------------------------

    def _add(self, name, widget=None) -> None:
        """Linha no grupo atual: ``(nome, campo)`` ou só um widget (largura inteira)."""
        if widget is None:
            name, widget = None, name
        self.groups[-1].rows.append((name or None, widget))

    def _title(self, text: str) -> None:
        self.groups[0].title = text

    def _section(self, text: str) -> None:
        self.groups.append(_Group(re.sub(r"</?b>", "", text)))

    def _read(self, label: str, text: str) -> None:
        value = QLabel(text)
        value.setStyleSheet("color: #777")
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._add(label, value)

    def _number(self, label: str, value, commit, placeholder: str = "",
                allow_empty: bool = False) -> QLineEdit:
        field = QLineEdit("" if value is None else fmt(value))
        field.setPlaceholderText(placeholder)
        original = field.text()

        def done():
            text = field.text().strip()
            if text == original:
                return
            if not text and allow_empty:
                commit(None)
                return
            try:
                number = parse_number(text)
            except ValueError:
                field.setStyleSheet(_INVALID)
                self.session.message(f"{label}: número inválido", "recusa")
                return
            field.setStyleSheet("")
            commit(number)

        field.editingFinished.connect(done)
        self._add(label, field)
        return field

    def _combo(self, label: str, items, current, commit) -> QComboBox:
        """Lista; ``current`` ``None`` com valores diferentes mostra "vários"."""
        combo = QComboBox()
        if current is None and items and None not in [v for _, v in items]:
            items = [(f"({MIXED})", None), *items]
        for text, value in items:
            combo.addItem(text, value)
        index = next((i for i, (_, v) in enumerate(items) if v == current), -1)
        combo.setCurrentIndex(index)

        def changed(i):
            value = combo.itemData(i)
            if value != current and (value is not None or current is not None):
                commit(value)

        combo.currentIndexChanged.connect(changed)
        self._add(label, combo)
        return combo

    def _buttons(self, *buttons) -> None:
        row = QHBoxLayout()
        for text, action in buttons:
            b = QPushButton(text)
            b.clicked.connect(action)
            row.addWidget(b)
        holder = QWidget()
        holder.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        self._add(holder)

    def _types(self, ifc_class: str):
        return [(e.Name or e.GlobalId, e.GlobalId)
                for e in sorted(self.session.doc.ifc.by_type(ifc_class), key=lambda e: e.Name or "")]

    def _run(self, build) -> None:
        self.session.run(build)
        self.refresh()  # recusa: o campo volta ao valor do modelo

    # --- parede (§7.2) -------------------------------------------------------------

    def _wall(self, wall) -> None:
        doc = self.session.doc
        state = read_wall(doc, wall)
        foreign = not ifcopenshell.util.element.get_pset(wall, wall_params.PSET)
        self._title(f"Parede {wall.Name or ''}".strip())

        def edit(**changes):
            self._run(lambda: cmd.edit_wall(doc, wall, **changes))

        self._combo("Tipo", self._types("IfcWallType"), state["type"],
                    lambda v: edit(type=v))
        self._edit_type_button("IfcWallType", state["type"])
        self._combo("Linha de referência", REF_LINES, state["ref_line"],
                    lambda v: edit(ref_line=v))
        flip = QCheckBox("Inverter camadas")
        flip.setChecked(bool(state["flip_layers"]))
        flip.toggled.connect(lambda v: edit(flip_layers=bool(v)))
        self._add("", flip)

        self._section("Altura")
        self._number("Base", state["base_offset"], lambda v: edit(base_offset=v))
        height = rebuild.height(doc, state)

        def top(mode):
            if mode == "fixed":
                edit(top_mode="fixed", fixed_height=height)
                return
            storey = doc.get(state["storey"])
            above = doc.storey_above(storey)
            if above is None:
                self.session.message("não há pavimento acima deste", "recusa")
                self.refresh()
                return
            edit(top_mode="storey", top_storey=above.GlobalId, top_offset=0.0)

        self._combo("Topo", TOPS, state["top_mode"], top)
        if state["top_mode"] == "fixed":
            self._number("Altura", state["fixed_height"], lambda v: edit(fixed_height=v))
        else:
            self._number("Deslocamento do topo", state["top_offset"],
                         lambda v: edit(top_offset=v))

        q = ifcopenshell.util.element.get_pset(wall, "Qto_WallBaseQuantities") or {}
        self._section("Geometria e quantidades")
        thickness = wall_types.thickness(doc.get(state["type"], "IfcWallType"))
        self._read("Comprimento", f"{fmt(q.get('Length', 0))} m")
        self._read("Espessura", f"{fmt(thickness)} m")
        self._read("Altura", f"{fmt(height)} m")
        self._read("Área lateral bruta", f"{fmt(q.get('GrossSideArea', 0))} m²")
        self._read("Área lateral líquida", f"{fmt(q.get('NetSideArea', 0))} m²")
        self._read("Volume líquido", f"{fmt(q.get('NetVolume', 0))} m³")
        self._section("Identificação")
        self._read("GlobalId", wall.GlobalId)
        self._read("Origem", "outro programa" if foreign else "BrasBim")

    # --- vários elementos (0.2 §9) ---------------------------------------------------------

    def _walls(self, walls) -> None:
        doc = self.session.doc
        states = [read_wall(doc, w) for w in walls]
        self._section(f"<b>Paredes ({len(walls)})</b>")
        label = f"Editar {len(walls)} paredes"

        def edit(**changes):
            self._run(lambda: cmd.edit_walls(doc, walls, **changes))

        def each(build):
            self._run(lambda: combine(doc, label, [lambda w=w: build(w) for w in walls]))

        self._combo("Tipo", self._types("IfcWallType"), _common(s["type"] for s in states),
                    lambda v: edit(type=v))
        self._combo("Linha de referência", REF_LINES, _common(s["ref_line"] for s in states),
                    lambda v: edit(ref_line=v))
        self._combo("Inverter camadas", [("Não", False), ("Sim", True)],
                    _common(bool(s["flip_layers"]) for s in states),
                    lambda v: edit(flip_layers=v))
        self._number("Base", _common(s["base_offset"] for s in states),
                     lambda v: edit(base_offset=v), placeholder=MIXED)
        mode = _common(s["top_mode"] for s in states)

        def to_fixed(w):
            height = rebuild.height(doc, read_wall(doc, w))
            return cmd.edit_wall(doc, w, top_mode="fixed", fixed_height=height)

        def to_storey(w):
            above = doc.storey_above(doc.get(read_wall(doc, w)["storey"]))
            if above is None:
                raise OpError(f"não há pavimento acima da parede {w.GlobalId}")
            return cmd.edit_wall(doc, w, top_mode="storey", top_storey=above.GlobalId,
                                 top_offset=0.0)

        self._combo("Topo", TOPS, mode,
                    lambda v: each(to_fixed if v == "fixed" else to_storey))
        if mode == "fixed":
            self._number("Altura", _common(s["fixed_height"] for s in states),
                         lambda v: edit(fixed_height=v), placeholder=MIXED)
        elif mode == "storey":
            self._number("Deslocamento do topo", _common(s["top_offset"] for s in states),
                         lambda v: edit(top_offset=v), placeholder=MIXED)
        total = sum((ifcopenshell.util.element.get_pset(w, "Qto_WallBaseQuantities") or {})
                    .get("Length", 0.0) for w in walls)
        self._read("Comprimento total", f"{fmt(total)} m")
        names = Counter(doc.get(s["type"]).Name for s in states)
        for name, n in sorted(names.items()):
            self._read(name, str(n))

    def _doors(self, door_list) -> None:
        doc = self.session.doc
        states = [doors.read_state(d) for d in door_list]
        found = [fc.opening_of(d) for d in door_list]
        spans = [openings.read_state(o) for o in found if o is not None]
        self._section(f"<b>Portas ({len(door_list)})</b>")

        def edit(**changes):
            self._run(lambda: fc.edit_doors(doc, door_list, **changes))

        self._combo("Tipo", self._types("IfcDoorType"), _common(s["type"] for s in states),
                    lambda v: edit(type=v))
        if len(spans) == len(door_list):
            self._number("Largura", _common(o["width"] for o in spans),
                         lambda v: edit(width=v), placeholder=MIXED)
            self._number("Altura", _common(o["height"] for o in spans),
                         lambda v: edit(height=v), placeholder=MIXED)
            self._number("Base", _common(o["sill"] for o in spans),
                         lambda v: edit(base=v), placeholder=MIXED)
        self._combo("Abre para", OPENS_TO, _common(s["opens_to"] for s in states),
                    lambda v: edit(opens_to=v))
        hands = []
        for s in states:
            door_type = doc.find(s["type"]) if s["type"] else None
            tstate = door_types.read(door_type) if door_type and s["foreign"] is None else None
            hands.append(params.hand_of(tstate["operation_type"]) if tstate else None)
        buttons = [("Inverter sentido", lambda: self._run(
            lambda: fc.flip_each(doc, door_list, fc.flip_opening)))]
        if all(hands):
            self._combo("Dobradiças", HINGES, _common(hands), lambda v: edit(hinges=v))
            buttons.append(("Inverter dobradiças", lambda: self._run(
                lambda: fc.flip_each(doc, door_list, fc.flip_hinges))))
        self._buttons(*buttons)
        self._combo("Alinhamento", ALIGNS, _common(s["align"] for s in states),
                    lambda v: edit(align=v))
        self._number("Deslocamento", _common(s["offset"] for s in states),
                     lambda v: edit(offset=v), placeholder=MIXED)
        names = Counter(params.base_name(doc.get(s["type"]).Name) if s["type"] else "sem tipo"
                        for s in states)
        for name, n in sorted(names.items()):
            self._read(name, str(n))

    # --- porta (§7.3) -------------------------------------------------------------------

    def _door(self, door) -> None:
        doc = self.session.doc
        state = doors.read_state(door)
        opening = fc.opening_of(door)
        o = openings.read_state(opening) if opening is not None else None
        door_type = doc.find(state["type"]) if state["type"] else None
        tstate = (door_types.read(door_type)
                  if door_type is not None and state["foreign"] is None else None)
        common = ifcopenshell.util.element.get_pset(door, "Pset_DoorCommon") or {}
        self._title(f"Porta {door.Name or ''}".strip())

        def edit(**changes):
            self._run(lambda: fc.edit_door(doc, door, **changes))

        self._combo("Tipo", self._types("IfcDoorType"), state["type"], lambda v: edit(type=v))
        if state["type"] and state["foreign"] is None:
            self._edit_type_button("IfcDoorType", state["type"])
        self._read("Código", str(common.get("Reference") or "—"))
        if o is not None:
            self._section("Vão")
            self._number("Largura", o["width"], lambda v: edit(width=v))
            self._number("Altura", o["height"], lambda v: edit(height=v))
            self._number("Base", o["sill"], lambda v: edit(base=v))
            self._number("Distância ao início", o["distance"], lambda v: edit(distance=v))
        self._section("Abertura")
        self._combo("Abre para", OPENS_TO, state["opens_to"], lambda v: edit(opens_to=v))
        hand = params.hand_of(tstate["operation_type"]) if tstate else None
        if hand is not None:
            self._combo("Dobradiças", HINGES, hand, lambda v: edit(hinges=v))
        buttons = [("Inverter sentido",
                    lambda: self._run(lambda: fc.flip_opening(doc, door)))]
        if hand is not None:
            buttons.append(("Inverter dobradiças",
                            lambda: self._run(lambda: fc.flip_hinges(doc, door))))
        self._buttons(*buttons)
        self._section("Posição no marco")
        self._combo("Alinhamento", ALIGNS, state["align"], lambda v: edit(align=v))
        self._number("Deslocamento", state["offset"], lambda v: edit(offset=v))
        q = ifcopenshell.util.element.get_pset(door, params.QTO) or {}
        if q:
            self._section("Quantidades")
            self._read("Largura", f"{fmt(q.get('Width', 0))} m")
            self._read("Altura", f"{fmt(q.get('Height', 0))} m")
            self._read("Área", f"{fmt(q.get('Area', 0))} m²")
        self._section("Identificação")
        self._read("GlobalId", door.GlobalId)
        self._read("Origem", "outro programa" if state["foreign"] is not None else "BrasBim")
        if state["foreign"] is not None:
            warning = QLabel("Porta de outro programa: mudar tamanho, tipo, sentido, "
                             "dobradiças ou alinhamento a converte em porta do BrasBim, e o "
                             "corpo original é substituído.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #8a5a00")
            self._add(warning)

    # --- opções da ferramenta (§7.1) ------------------------------------------------------

    def _edit_type_button(self, ifc_class: str, gid: str) -> None:
        if self.edit_type is not None:
            self._buttons(("Editar tipo…", lambda: self.edit_type(ifc_class, gid)))

    def _tool_options(self) -> None:
        """Sem seleção: só o pavimento ativo e a dica (spec/ui 03 §4.3)."""
        self._title("Nada selecionado")
        storey = self.session.storey
        if storey is not None:
            self._read("Pavimento ativo", f"{storey.Name} ({fmt(storey.Elevation or 0)})")
        note = QLabel("Clique num elemento da planta para ver e editar as propriedades.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #666")
        self._add(note)
