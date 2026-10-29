# SPDX-License-Identifier: GPL-3.0-or-later
"""Linha de comando sob as vistas (``spec/ui/24-linha-de-comando.md``): dica e opções da
ferramenta ativa, campo com sugestões, histórico e o diálogo dos apelidos.

A leitura do texto é de ``command_input`` (sem Qt); a execução dos comandos é a mesma da
paleta (``command_palette.collect`` / ``execute``)."""

from __future__ import annotations

import json
from html import escape

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
)

from brasbim.ui import command_palette, theme
from brasbim.ui.command_input import (
    DEFAULT_ALIASES,
    Entry,
    History,
    Option,
    candidates,
    diff_aliases,
    interpret,
    merge_aliases,
    parse_number,
    validate_aliases,
)
from brasbim.ui.tools import fmt

SHORT_GROUP = 6  # grupos de opções com até tantas escolhas viram links lado a lado (§5)
PLACEHOLDER = "comando, apelido ou x;y"
FIELD_TIP = ("Digite um comando, um apelido (PD = Parede), uma opção, um número ou um "
             "ponto: x;y ou @dx;dy")
ALIASES_KEY = "linha_comando/apelidos"
VISIBLE_KEY = "linha_comando/visivel"


def load_aliases(settings) -> dict[str, str]:
    """Apelidos do usuário: o padrão com as diferenças gravadas (§7)."""
    try:
        changes = json.loads(settings.value(ALIASES_KEY, "") or "{}")
    except (TypeError, ValueError):
        changes = {}
    if not isinstance(changes, dict):
        changes = {}
    # menus gravados com "…" antes da spec/ui 40 §2 ("menu:Exibir/Salvar vista…")
    changes = {key.replace("…", ""): value for key, value in changes.items()}
    return merge_aliases(changes)


def save_aliases(settings, aliases: dict[str, str]) -> None:
    settings.setValue(ALIASES_KEY, json.dumps(diff_aliases(aliases), ensure_ascii=False))


class _Popup(QFrame):
    """Lista de sugestões ou de histórico, logo acima do campo."""

    def __init__(self, line):
        super().__init__(line.window_)
        self.setObjectName("linha_comando_lista")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.list = QListWidget(self)
        self.list.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.list)
        self.hide()

    def show_items(self, rows: list[tuple[str, object]], anchor, width: int) -> None:
        self.list.clear()
        for text, data in rows:
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, data)
            self.list.addItem(item)
        if not rows:
            self.hide()
            return
        self.list.setCurrentRow(0)
        height = self.list.sizeHintForRow(0) * len(rows) + 10
        self.resize(width, height)
        top_left = anchor.mapTo(self.parentWidget(), QPoint(0, 0))
        self.move(top_left.x(), top_left.y() - height - 2)
        self.show()
        self.raise_()


class CommandLine(QFrame):
    """Barra de uma linha: dica, opções da ferramenta, campo e histórico (§2)."""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self.setObjectName("linha_comando")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)
        # Opções num rótulo só, com links (nada é criado nem destruído ao trocar de
        # ferramenta); encolhe, cortada à direita, para a janela caber.
        self.options_label = QLabel()
        self.options_label.setObjectName("linha_comando_opcoes")
        self.options_label.setTextFormat(Qt.RichText)
        self.options_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.options_label.linkActivated.connect(self.follow)
        self.field = QLineEdit()
        self.field.setObjectName("linha_comando_campo")
        # a dica da ferramenta é o texto-fantasma do campo (some ao digitar)
        self._prompt = PLACEHOLDER
        self.field.setPlaceholderText(PLACEHOLDER)
        self.field.setToolTip(FIELD_TIP)
        self.field.setMinimumWidth(160)
        self.field.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.field.installEventFilter(self)
        self.field.textEdited.connect(self._suggest)
        self.history_button = QToolButton()
        self.history_button.setText("Histórico")
        self.history_button.setToolTip("O que foi digitado nesta sessão e o resultado")
        self.history_button.setAutoRaise(True)
        self.history_button.clicked.connect(self.show_history)
        layout.addWidget(self.field, 3)
        layout.addWidget(self.options_label, 2)
        layout.addWidget(self.history_button)
        self.popup = _Popup(self)
        self.popup.list.itemClicked.connect(self._clicked)
        self.popup_mode = ""  # "suggest" ou "history"
        self.history = History()
        self.aliases: dict[str, str] = dict(DEFAULT_ALIASES)
        self.options: list[Option] = []
        self._signature: list | None = None  # opções mostradas (refaz só se mudarem)

    # --- dica e opções (§5) -----------------------------------------------------------

    def set_prompt(self, text: str) -> None:
        self._prompt = f"{text}   ·   {PLACEHOLDER}" if text else PLACEHOLDER
        self._fit_prompt()

    @property
    def prompt(self) -> str:
        """Dica mostrada no campo vazio (inteira, mesmo quando não cabe)."""
        return self._prompt

    def _fit_prompt(self) -> None:
        """O Qt corta o texto-fantasma com "…" (spec/ui 40 §2): sem lugar, sai o final
        "comando, apelido ou x;y" e depois as últimas palavras; a dica inteira fica na dica
        do campo."""
        room = self.field.width() - 16
        metrics = self.field.fontMetrics()
        text = self._prompt
        if metrics.horizontalAdvance(text) > room:
            text = text.removesuffix(f"   ·   {PLACEHOLDER}")
        while metrics.horizontalAdvance(text) > room and " " in text:
            text = text.rsplit(" ", 1)[0].rstrip(",.;:")
        self.field.setPlaceholderText(text)
        self.field.setToolTip(f"{self._prompt}\n\n{FIELD_TIP}" if text != self._prompt
                              else FIELD_TIP)

    def refresh_tool(self) -> None:
        """Dica e opções da ferramenta ativa (lidas da barra Opções)."""
        tool = self.window_.toolbox.active
        self.set_prompt(tool.hint() or tool.label)
        choices = self.window_.options_bar.choices
        signature = [(name, tuple(labels), current()) for name, labels, current, _ in choices]
        if signature == self._signature:
            return  # nada mudou: não refaz os botões
        self._signature = signature
        self.options = []
        parts = []
        link = "color: {}; text-decoration: none;{}"
        for g, ((name, labels, _, _), (_, _, current)) in enumerate(zip(choices, signature)):
            if len(labels) <= SHORT_GROUP:
                items = []
                for i, label in enumerate(labels):
                    self.options.append(Option(g, i, label, i == current))
                    style = link.format(theme.ACCENT, " font-weight: bold;") if i == current                         else link.format(theme.INK, "")
                    items.append(f'<a href="opt:{g}:{i}" style="{style}">{escape(label)}</a>')
                parts.append("&nbsp;&nbsp;".join(items))
            else:
                text = labels[current] if 0 <= current < len(labels) else ""
                text = f"{name}: {text}" if name else text
                parts.append(f'<a href="menu:{g}" style="{link.format(theme.INK, "")}">'
                             f"{escape(text)}&nbsp;▾</a>")
        sep = f'&nbsp;&nbsp;<span style="color: {theme.INK_SOFT}">·</span>&nbsp;&nbsp;'
        self.options_label.setText(sep.join(parts))

    def follow(self, href: str) -> None:
        """Link do rótulo das opções: escolhe, ou abre a lista longa num menu."""
        choices = self.window_.options_bar.choices
        kind, *rest = href.split(":")
        g = int(rest[0])
        if g >= len(choices):
            return
        _, labels, _, choose = choices[g]
        if kind == "opt":
            self.choose(choose, int(rest[1]))
            return
        menu = QMenu(self)
        for i, label in enumerate(labels):
            menu.addAction(label, lambda i=i: self.choose(choose, i))
        menu.exec(QCursor.pos())

    def choose(self, choose, index: int) -> None:
        """Escolhe a opção (a barra Opções acompanha) e redesenha as duas."""
        choose(index)
        self.refresh_tool()
        self._view().update()

    # --- entrada (§3) ---------------------------------------------------------------------

    def take(self, text: str) -> None:
        """Tecla de texto vinda da vista: começa (ou continua) a digitação."""
        self.field.setText(self.field.text() + text)
        self.field.setFocus()
        self.field.end(False)
        self._suggest(self.field.text())

    def _view(self):
        return self.window_.ctx.input_view or self.window_.plan

    def _commands(self):
        return command_palette.collect(self.window_)

    def _suggest(self, text: str) -> None:
        self.history.pos = None
        if parse_number(text) is not None or ";" in text or text.strip().startswith("@"):
            self.popup.hide()  # coordenada ou número: nada a sugerir
            return
        commands, _ = self._commands()
        found = candidates(text, commands, self.aliases, self.options,
                           self.window_.recent_commands)
        rows = []
        for c in found:
            if c.kind == "option":
                rows.append((f"Opção: {c.label}", ("option", c.option)))
            else:
                extra = "  ·  ".join(x for x in (c.alias, c.where) if x)
                rows.append((f"{c.label}    {extra}" if extra else c.label,
                             ("command", c.key)))
        self.popup_mode = "suggest"
        self.popup.show_items(rows, self.field, max(self.field.width(), 320))

    def show_history(self) -> None:
        rows = [(f"{text}  →  {result}", ("text", text))
                for text, result in self.history.lines[-12:]]
        if not rows:
            rows = [("(nada digitado ainda)", ("text", ""))]
        self.popup_mode = "history"
        self.popup.show_items(rows, self.field, max(self.field.width(), 320))

    def _clicked(self, item) -> None:
        kind, data = item.data(Qt.UserRole)
        if kind == "text":
            self.popup.hide()
            self.field.setText(data)
            self.field.setFocus()
            return
        self.run(picked=(kind, data))

    def _base(self):
        """Ponto anterior para "@" (§4)."""
        tool = self.window_.toolbox.active
        ctx = self.window_.ctx
        if tool.cursor is None:
            return ctx.last_point
        tool.move(tool.cursor, tool.mods)  # atualiza o ponto anterior da ferramenta
        return ctx.last_origin if ctx.last_origin is not None else ctx.last_point

    def run(self, picked=None) -> str:
        """Enter: lê e executa o texto (ou a sugestão escolhida); devolve o resultado."""
        text = self.field.text()
        if picked is None and self.popup.isVisible() and self.popup_mode == "suggest":
            item = self.popup.list.currentItem()
            if item is not None:
                picked = item.data(Qt.UserRole)
        self.popup.hide()
        commands, targets = self._commands()
        if picked is not None:
            kind, data = picked
            entry = Entry("option", option=data) if kind == "option" else Entry("command",
                                                                                 key=data)
        else:
            entry = interpret(text, commands, self.aliases, self.options, self._base(),
                              self.window_.recent_commands)
        self.field.clear()
        view = self._view()
        result = self._execute(entry, commands, targets, view)
        if text.strip():
            self.history.add(text.strip(), result)
        if entry.kind not in ("empty",):
            view.setFocus()
        return result

    def _execute(self, entry: Entry, commands, targets, view) -> str:
        session = self.window_.session
        tool = self.window_.toolbox.active
        if entry.kind == "empty":
            view.setFocus()
            view.press_enter()
            return ""
        if entry.kind in ("error", "unknown"):
            session.message(entry.text, "recusa")
            return entry.text.split(":")[0] if entry.kind == "unknown" else entry.text
        if entry.kind == "point":
            if tool.name == "select":
                session.message("a ferramenta não espera um ponto", "recusa")
                return "recusado"
            self.point(entry.point)
            x, y = entry.point
            return f"ponto {fmt(x)}; {fmt(y)}"
        if entry.kind == "number":
            if not tool.numeric(entry.value):
                session.message("a ferramenta não espera um número agora", "recusa")
                return "recusado"
            view.after_tool_input()
            return f"valor {fmt(entry.value)}"
        if entry.kind == "option":
            _, labels, _, choose = self.window_.options_bar.choices[entry.option.group]
            self.choose(choose, entry.option.index)
            return f"opção {labels[entry.option.index]}"
        label = next((c.label for c in commands if c.key == entry.key), entry.key)
        command_palette.execute(self.window_, entry.key, targets[entry.key])
        return label

    def point(self, p) -> None:
        """Ponto digitado: um clique exato, sem atração nem trava (§4)."""
        self._view().enter_point(p)

    def escape(self) -> None:
        had = bool(self.field.text()) or self.popup.isVisible()
        self.popup.hide()
        self.field.clear()
        view = self._view()
        view.setFocus()
        if not had:
            view.press_escape()

    def eventFilter(self, obj, event):
        if obj is self.field and event.type() == QEvent.Resize:
            self._fit_prompt()
        if obj is self.field and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.escape()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.run()
                return True
            if key in (Qt.Key_Up, Qt.Key_Down):
                step = -1 if key == Qt.Key_Up else 1
                if self.popup.isVisible() and self.popup.list.count():
                    row = self.popup.list.currentRow() + step
                    self.popup.list.setCurrentRow(max(0, min(row,
                                                             self.popup.list.count() - 1)))
                else:
                    text = self.history.step(step)
                    self.field.setText(text or "")
                return True
        if (obj is self.field and event.type() == QEvent.FocusOut
                and not self.popup.list.underMouse()):
            self.popup.hide()
        return super().eventFilter(obj, event)


class AliasesDialog(QDialog):
    """Editar > Apelidos da linha de comando… (§7)."""

    def __init__(self, parent, commands, aliases: dict[str, str]):
        super().__init__(parent)
        self.setWindowTitle("Apelidos da linha de comando")
        self.resize(520, 560)
        layout = QVBoxLayout(self)
        seen, self.keys = set(), []
        rows = []
        for c in commands:
            if c.key not in seen:
                seen.add(c.key)
                rows.append(c)
        self.table = QTableWidget(len(rows), 3, self)
        self.table.setHorizontalHeaderLabels(["Comando", "Onde", "Apelido"])
        self.table.verticalHeader().hide()
        for r, c in enumerate(rows):
            self.keys.append(c.key)
            for col, text in enumerate((c.label, c.where)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, col, item)
            self.table.setItem(r, 2, QTableWidgetItem(aliases.get(c.key, "")))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.error = QLabel()
        self.error.setStyleSheet(f"color: {theme.ERROR}")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        reset = QPushButton("Restaurar padrões")
        buttons.addButton(reset, QDialogButtonBox.ResetRole)
        reset.clicked.connect(self.restore_defaults)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        out = {}
        for r, key in enumerate(self.keys):
            item = self.table.item(r, 2)
            text = (item.text() if item else "").strip().upper()
            if text:
                out[key] = text
        return out

    def restore_defaults(self) -> None:
        for r, key in enumerate(self.keys):
            self.table.item(r, 2).setText(DEFAULT_ALIASES.get(key, ""))

    def _accept(self) -> None:
        errors = validate_aliases(self.values())
        if errors:
            self.error.setText("; ".join(errors))
            return
        self.accept()
