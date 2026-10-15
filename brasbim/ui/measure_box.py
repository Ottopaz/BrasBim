# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadro de medidas junto ao cursor (``spec/ui/07-medidas-e-edicao-no-3d.md`` §2) e a
entrada de teclado comum às vistas de planta e 3D.

O quadro mostra os campos da ferramenta ativa (``Tool.fields``): o valor que o cursor dá,
atualizado a cada movimento, ou o valor fixado (negrito, com cadeado). O campo aberto pelo
Tab continua acompanhando o cursor até a primeira tecla. Tab passa a digitar no primeiro campo; Tab
fixa e vai ao próximo; Enter fixa e confirma o ponto; Esc solta os valores fixados.
Ferramenta sem campos que aceita número (alças da seleção) usa um campo único, sem Tab.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit

from brasbim.ui.tools import SELECTION_TOOLS, parse_number

ROWS = 2
_CURSOR_GAP = 16  # distância do quadro ao cursor, em pixels
DWELL_MS = 400  # cursor parado sobre um vértice: ponto de referência (spec/ui 09 §2.1)
# Cores do tema (claro ou escuro): o valor do cursor legível, o fixado em negrito.
_STYLE = {
    "cursor": "QLineEdit { color: palette(text); background: transparent; border: none; }",
    "fixed": "QLineEdit { color: palette(text); font-weight: bold; background: transparent; "
             "border: none; }",
    "edit": "QLineEdit { color: palette(text); background: palette(base); "
            "border: 1px solid #1d6fd6; }",
    "invalid": "QLineEdit { color: #b3261e; background: #fdecea; border: 1px solid #d43a2f; }",
}


def _lock_pixmap(color: QColor) -> QPixmap:
    """Cadeado pequeno (desenho próprio): valor fixado."""
    pixmap = QPixmap(10, 12)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(color, 1.3))
    arc = QPainterPath()
    arc.moveTo(2.5, 6)
    arc.lineTo(2.5, 3.5)
    arc.arcTo(QRectF(2.5, 1, 5, 5), 180, -180)
    arc.lineTo(7.5, 6)
    painter.drawPath(arc)
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(1, 5.5, 8, 6), 1, 1)
    painter.end()
    return pixmap


class MeasureBox(QFrame):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setObjectName("quadro_medidas")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.NoFocus)
        # O cursor passa por cima do quadro sem que a vista perca o movimento; o teclado
        # chega aos campos pelo foco.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        grid = QGridLayout(self)
        grid.setContentsMargins(6, 3, 6, 3)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(1)
        lock = _lock_pixmap(self.palette().color(QPalette.WindowText))
        self.names: list[QLabel] = []
        self.edits: list[QLineEdit] = []
        self.locks: list[QLabel] = []
        self.units: list[QLabel] = []
        for row in range(ROWS):
            name, edit, unit, padlock = QLabel(self), QLineEdit(self), QLabel(self), QLabel(self)
            edit.setFixedWidth(64)
            edit.setAlignment(Qt.AlignRight)
            edit.installEventFilter(self)
            edit.textEdited.connect(self._typed)
            padlock.setPixmap(lock)
            padlock.setFixedWidth(10)
            for col, w in enumerate((name, edit, unit, padlock)):
                grid.addWidget(w, row, col)
            self.names.append(name)
            self.edits.append(edit)
            self.units.append(unit)
            self.locks.append(padlock)
        self.editing: int | None = None
        self.typed = False  # o campo em edição já recebeu tecla (deixa de seguir o cursor)
        self.generic = False  # campo único para ferramenta sem campos (alças)
        self.hide()

    @property
    def tool(self):
        return self.view.toolbox.active

    def _typed(self, _text: str) -> None:
        self.typed = True

    def current(self) -> QLineEdit | None:
        return self.edits[self.editing] if self.editing is not None else None

    # --- exibição ------------------------------------------------------------------------

    def refresh(self) -> None:
        """Atualiza valores e posição; esconde se a ferramenta não tem campos."""
        if self.generic:
            self._place()
            return
        active = self.view.ctx.input_view is self.view or self.editing is not None
        fields = self.tool.fields()[:ROWS] if active else []
        if not fields:
            self.editing = None
            self.hide()
            return
        if self.editing is not None and self.editing >= len(fields):
            self.editing = None
        for row in range(ROWS):
            widgets = (self.names[row], self.edits[row], self.units[row], self.locks[row])
            if row >= len(fields):
                for w in widgets:
                    w.hide()
                continue
            f = fields[row]
            self.names[row].setText(f.label)
            self.units[row].setText(f.unit)
            for w in widgets[:3]:
                w.show()
            self.locks[row].setVisible(f.fixed is not None)
            edit = self.edits[row]
            if row == self.editing:
                if not self.typed:  # aberto pelo Tab: mostra a medida atual, selecionada
                    edit.setText(f.text(f.fixed) if f.fixed is not None else f.text())
                    edit.selectAll()
                continue
            edit.setReadOnly(True)
            edit.setFocusPolicy(Qt.NoFocus)
            edit.setText(f.text(f.fixed) if f.fixed is not None else f.text())
            edit.setStyleSheet(_STYLE["fixed" if f.fixed is not None else "cursor"])
        self.adjustSize()
        self._place()
        self.show()
        self.raise_()

    def _place(self) -> None:
        pos = None
        anchor = self.tool.field_anchor()  # meio da linha de referência (spec/ui 09 §2.1)
        if anchor is not None:
            pos = self.view.anchor_screen(anchor)
        if pos is None:
            pos = self.view.mouse_pos
        if pos is None:
            pos = self.view.mapFromGlobal(QCursor.pos())
        x = min(max(pos.x() + _CURSOR_GAP, 0), max(self.view.width() - self.width(), 0))
        y = min(max(pos.y() + _CURSOR_GAP, 0), max(self.view.height() - self.height(), 0))
        self.move(int(x), int(y))

    # --- edição ----------------------------------------------------------------------------

    def start(self, row: int = 0, text: str | None = None) -> None:
        """Passa a digitar no campo ``row``; ``text`` substitui o valor (primeira tecla)."""
        fields = self.tool.fields()
        if not fields:
            return
        self.editing = row % min(len(fields), ROWS)
        self.typed = text is not None
        self.refresh()
        edit = self.edits[self.editing]
        edit.setReadOnly(False)
        edit.setFocusPolicy(Qt.StrongFocus)
        edit.setStyleSheet(_STYLE["edit"])
        if text is not None:
            edit.setText(text)
        edit.show()
        self.show()
        edit.setFocus()
        if text is None:
            edit.selectAll()

    def start_generic(self, text: str) -> None:
        """Campo único (ferramenta sem campos que aceita número)."""
        self.generic = True
        self.editing = 0
        for row in range(ROWS):
            for w in (self.names[row], self.edits[row], self.units[row], self.locks[row]):
                w.setVisible(row == 0 and w is not self.locks[row])
        self.names[0].setText(self.tool.number_hint)
        self.units[0].setText("")
        edit = self.edits[0]
        edit.setReadOnly(False)
        edit.setFocusPolicy(Qt.StrongFocus)
        edit.setStyleSheet(_STYLE["edit"])
        edit.setText(text)
        self.adjustSize()
        self._place()
        self.show()
        self.raise_()
        edit.setFocus()

    def stop(self) -> None:
        self.editing = None
        self.generic = False
        self.view.setFocus()
        self.refresh()

    def commit(self, quiet: bool = False) -> bool:
        """Fixa o valor do campo em edição; devolve se foi aceito."""
        edit = self.current()
        if edit is None or self.generic:
            return True
        fields = self.tool.fields()
        if self.editing >= len(fields):
            return True
        if not self.typed:  # nada digitado: o campo continua seguindo o cursor
            return True
        key, text = fields[self.editing].key, edit.text()
        error = None
        if not text.strip():
            self.tool.fix(key, None)
            return True
        try:
            value = parse_number(text)
        except ValueError:
            error = f"número inválido: {text!r}"
        else:
            error = self.tool.fix(key, value)
        if error:
            edit.setStyleSheet(_STYLE["invalid"])
            if not quiet:
                self.view.ctx.session.message(error, "recusa")
            return False
        edit.setStyleSheet(_STYLE["edit"])
        return True

    def _enter(self) -> None:
        if self.generic:
            text = self.edits[0].text()
            self.stop()
            try:
                value = parse_number(text)
            except ValueError:
                self.view.ctx.session.message(f"número inválido: {text!r}", "recusa")
                return
            if not self.tool.numeric(value):
                self.view.ctx.session.message("a ferramenta não espera um número agora",
                                              "recusa")
            self.view.after_tool_input()
            return
        if not self.commit():
            return
        self.editing = None
        self.tool.confirm()
        self.stop()
        self.view.after_tool_input()

    def escape(self) -> None:
        """Esc no quadro: solta os valores fixados e devolve o controle ao cursor."""
        self.generic = False
        self.editing = None
        self.tool.release_fixed()
        self.stop()
        self.view.after_tool_input()

    def eventFilter(self, obj, event):
        if obj in self.edits and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.escape()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):  # não deixa o Enter chegar à vista
                self._enter()
                return True
            if key in (Qt.Key_Tab, Qt.Key_Backtab) and not self.generic:
                if self.commit():
                    step = -1 if key == Qt.Key_Backtab or \
                        event.modifiers() & Qt.ShiftModifier else 1
                    self.start(self.editing + step)
                    self.view.after_tool_input()
                return True
        return super().eventFilter(obj, event)


class ToolInput:
    """Mouse e teclado comuns às vistas (planta e 3D): Tab, Enter, Esc e números vão para
    a ferramenta ativa e para o quadro de medidas (spec/ui 07 §2.2, §3.1).

    A classe que usa precisa ter ``toolbox``, ``ctx`` e os sinais ``hint_changed``,
    ``tool_finished`` e ``tool_options_changed``."""

    def _init_tool_input(self) -> None:
        self.mouse_pos = None  # última posição do mouse na vista (QPointF)
        self.measure = MeasureBox(self)
        self.dwell = QTimer(self)
        self.dwell.setSingleShot(True)
        self.dwell.setInterval(DWELL_MS)
        self.dwell.timeout.connect(self._dwelled)

    def restart_dwell(self) -> None:
        """Cursor andou: recomeça a contar a parada sobre um vértice."""
        if self.toolbox.active.creates:
            self.dwell.start()

    def _dwelled(self) -> None:
        if self.measure.editing is None and self.toolbox.active.acquire():
            self.after_tool_input()

    def anchor_screen(self, p):
        """Ponto do pavimento na tela (QPointF), ou None (a vista que sabe projeta)."""

    @property
    def numeric(self) -> QLineEdit:
        """Campo em edição no quadro (ou o primeiro)."""
        return self.measure.current() or self.measure.edits[0]

    def after_tool_input(self) -> None:
        tool = self.toolbox.active
        if tool.finished:
            tool.finished = False
            self.tool_finished.emit()
        self.hint_changed.emit(self.toolbox.active.hint())
        self.measure.refresh()
        self.update()

    def tool_event(self, event) -> bool:
        """Tab é da ferramenta (spec/ui 01 §5.5, 07 §2.2), não troca o foco."""
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            tool = self.toolbox.active
            if tool.fields():
                last = len(tool.fields()[:ROWS]) - 1
                self.measure.start(last if event.key() == Qt.Key_Backtab else 0)
            else:
                tool.key("tab")
                self.tool_options_changed.emit()
            self.after_tool_input()
            return True
        return False

    def tool_key(self, event) -> bool:
        """Esc, Enter e números; devolve se a tecla foi usada."""
        key, text = event.key(), event.text()
        tool = self.toolbox.active
        if key == Qt.Key_Escape:
            busy = tool.cancel()
            session = self.ctx.session
            if tool.name in SELECTION_TOOLS or not busy:
                if tool.name == "select" and session.selection:
                    session.select([])  # Esc com a mini-barra visível (spec/ui 03 §5)
                else:
                    self.tool_finished.emit()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            tool.key("enter")
        elif text and (text.isdigit() or text in ",.-") and tool.wants_number():
            if tool.fields():
                self.measure.start(0, text)
            else:
                self.measure.start_generic(text)
            return True
        else:
            return False
        self.after_tool_input()
        return True

    def before_press(self) -> None:
        """Clique na vista com o quadro em edição: o valor digitado vale para o clique."""
        if self.measure.editing is not None and not self.measure.generic:
            self.measure.commit(quiet=True)
        if self.measure.editing is not None:
            self.measure.editing = None
            self.measure.generic = False
            self.measure.hide()
