# SPDX-License-Identifier: GPL-3.0-or-later
"""Paleta de comandos (``spec/ui/23-precisao.md`` §9): Ctrl+K abre um campo de busca
no alto da janela com as ações dos menus e as ferramentas."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from brasbim.ui.command_search import SYNONYMS, Command, search

WIDTH = 460
ROWS = 10
MAX_RECENT = 8


def menu_commands(menu_bar) -> list[tuple[Command, object]]:
    """(comando, QAction) de todos os itens dos menus, com o caminho do menu."""
    out = []

    def walk(menu, path):
        for action in menu.actions():
            if action.isSeparator() or not action.text():
                continue
            text = action.text().replace("&", "")
            if action.menu() is not None:
                walk(action.menu(), [*path, text])
                continue
            if not action.isEnabled():
                continue
            key = "menu:" + "/".join([*path, text])
            shortcut = action.shortcut().toString()
            out.append((Command(key, text, " › ".join(path), shortcut), action))

    for action in menu_bar.actions():
        if action.menu() is not None:
            walk(action.menu(), [action.text().replace("&", "")])
    return out


def tool_commands(groups) -> list[Command]:
    """Comandos das ferramentas: ``groups`` = [(nome do grupo, [(ferramenta, ícone,
    nome, uso)])]."""
    out = []
    for where, items in groups:
        for tool, _icon, name, _usage in items:
            out.append(Command("tool:" + tool, name, where, "", SYNONYMS.get(tool, ())))
    return out


def collect(window) -> tuple[list[Command], dict[str, object]]:
    """Comandos dos menus e das ferramentas e o alvo de cada um (nome da ferramenta ou
    QAction); usado pela paleta e pela linha de comando (spec/ui 24 §8)."""
    commands, targets = [], {}
    tools = window.tool_commands()
    names = {c.label for c in tools}  # menu que só ativa a ferramenta: fica a ferramenta
    for command, action in menu_commands(window.menuBar()):
        if command.label not in names:
            commands.append(command)
            targets[command.key] = action
    for command in tools:
        commands.append(command)
        targets[command.key] = command.key[len("tool:"):]
    return commands, targets


def execute(window, key: str, target) -> None:
    """Executa o comando e o põe no alto dos recentes (os mesmos da paleta e da linha)."""
    recent = window.recent_commands
    recent[:] = [key] + [k for k in recent if k != key][:MAX_RECENT - 1]
    if isinstance(target, str):
        window.activate_tool(target)
    else:
        target.trigger()


class CommandPalette(QFrame):
    """Campo de busca e lista, no alto da janela; Enter executa, Esc fecha."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setObjectName("paleta_comandos")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.field = QLineEdit(self)
        self.field.setPlaceholderText("Buscar comando ou ferramenta…")
        self.field.installEventFilter(self)
        self.field.textChanged.connect(self._filter)
        self.list = QListWidget(self)
        self.list.itemActivated.connect(lambda _item: self.run())
        layout.addWidget(self.field)
        layout.addWidget(self.list)
        self.commands: list[Command] = []
        self.targets: dict[str, object] = {}
        self.hide()

    def open(self) -> None:
        self.commands, self.targets = collect(self.window)
        self.field.clear()
        self._filter("")
        self.resize(WIDTH, self.field.sizeHint().height() + 22 * ROWS + 18)
        self.move((self.window.width() - self.width()) // 2, 48)
        self.show()
        self.raise_()
        self.field.setFocus()

    @property
    def recent(self) -> list[str]:
        return self.window.recent_commands

    def _filter(self, text: str) -> None:
        self.list.clear()
        for command in search(text, self.commands, self.recent):
            extra = "  ·  ".join(x for x in (command.where, command.shortcut) if x)
            item = QListWidgetItem(f"{command.label}    {extra}" if extra else command.label)
            item.setData(Qt.UserRole, command.key)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def run(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        key = item.data(Qt.UserRole)
        self.hide()
        execute(self.window, key, self.targets[key])

    def eventFilter(self, obj, event):
        if obj is self.field and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.hide()
                self.window.plan.setFocus()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.run()
                return True
            if key in (Qt.Key_Down, Qt.Key_Up):
                row = self.list.currentRow() + (1 if key == Qt.Key_Down else -1)
                self.list.setCurrentRow(max(0, min(row, self.list.count() - 1)))
                return True
        return super().eventFilter(obj, event)
