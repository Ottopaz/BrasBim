# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela principal (``spec/ui/01-janela-e-ferramentas.md`` §2, §6, §8, §9; barras e
mini-barra, ``spec/ui/03-barras-e-icones.md`` §2–§5)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import doors
from brasbim.core.ops import Transaction
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.ui import feedback
from brasbim.ui.plan_view import PlanView
from brasbim.ui.project_panel import ProjectPanel
from brasbim.ui.properties import PropertiesPanel
from brasbim.ui.scene3d import Scene
from brasbim.ui.selection_bar import SelectionBar
from brasbim.ui.session import Session
from brasbim.ui.toolbars import OptionsBar, ToolsBar, history_bar
from brasbim.ui.tools import Mods, PlanContext, ToolBox, fmt
from brasbim.ui.types_dialog import DoorTypesDialog, WallTypesDialog
from brasbim.ui.view3d import View3D

STATE_VERSION = 3  # disposição de painéis e barras; muda quando as barras mudam
_LEVEL_COLOR = {"recusa": "#b3261e", "aviso": "#8a5a00", "info": "#333333"}


def _settings() -> QSettings:
    """Preferências da janela; o formato padrão permite aos testes usar outro lugar."""
    return QSettings(QSettings.defaultFormat(), QSettings.UserScope, "BrasBim", "BrasBim")


def delete_transaction(session: Session) -> tuple[Transaction, int]:
    """Exclusão da seleção numa transação (§5.1): portas antes das paredes; operações
    repetidas (abertura, junção entre duas paredes excluídas) entram uma vez. Devolve a
    transação e quantas portas saem junto com paredes."""
    doc = session.doc
    entities = [doc.find(g) for g in sorted(session.selection)]
    entities = [e for e in entities if e is not None]
    door_list = [e for e in entities if e.is_a("IfcDoor")]
    wall_list = [e for e in entities if e.is_a("IfcWall")]
    ops, seen, cascade = [], set(), 0
    for door in door_list:
        for op in fc.delete_door(doc, door).ops:
            if (op.op, op.id) not in seen:
                seen.add((op.op, op.id))
                ops.append(op)
    for wall in wall_list:
        for opening in openings.of_wall(wall):
            cascade += sum(1 for r in opening.HasFillings
                           if r.RelatedBuildingElement.is_a("IfcDoor")
                           and r.RelatedBuildingElement not in door_list
                           and doors.is_parametric(r.RelatedBuildingElement))
        for op in cmd.delete_wall(doc, wall).ops:
            if (op.op, op.id) not in seen:
                seen.add((op.op, op.id))
                ops.append(op)
    label = "Excluir porta" if len(entities) == 1 and door_list else "Excluir"
    return Transaction(label, ops), cascade


class MainWindow(QMainWindow):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.ctx = PlanContext(session)
        self.toolbox = ToolBox(self.ctx)
        self.scene = Scene()
        self.scene.load(session.doc.ifc)
        self.plan = PlanView(self.toolbox)
        self.view3d = View3D(self.scene, lambda: self.session.selection)
        self.split = False
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_status()
        session.listeners.append(self._on_session)
        self.plan.cursor_moved.connect(self._show_cursor)
        self.plan.hint_changed.connect(self.hint.setText)
        self.plan.tool_finished.connect(lambda: self.activate_tool("select"))
        self.plan.tool_options_changed.connect(self.options_bar.refresh)
        self.selection_bar = SelectionBar(self.plan, self.run_selection_action)
        self.plan.selection_bar = self.selection_bar
        self.resize(1280, 800)
        self._restore()
        self._refresh_all()

    # --- montagem --------------------------------------------------------------------

    def _build_central(self) -> None:
        self.tabs = QTabWidget()
        self.splitter = QSplitter(Qt.Horizontal)
        self.central = QWidget()
        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        layout.addWidget(self.splitter)
        self.splitter.hide()
        self.tabs.addTab(self.plan, "Planta")
        self.tabs.addTab(self.view3d, "3D")
        self.setCentralWidget(self.central)

    def _dock(self, title: str, name: str, widget, area) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _build_docks(self) -> None:
        self.project = ProjectPanel(self.session)
        self._dock("Projeto", "projeto", self.project, Qt.LeftDockWidgetArea)
        self.properties = PropertiesPanel(self.session, self.toolbox)
        self.properties.setMinimumWidth(270)
        self.properties.edit_type = self.edit_type
        self._dock("Propriedades", "propriedades", self.properties, Qt.RightDockWidgetArea)
        self.messages = QListWidget()
        self.messages.setWordWrap(True)
        dock = self._dock("Mensagens", "mensagens", self.messages, Qt.BottomDockWidgetArea)
        dock.setMaximumHeight(160)

    def _action(self, menu, text, slot, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            shortcuts = shortcut if isinstance(shortcut, list) else [shortcut]
            action.setShortcuts([QKeySequence(s) for s in shortcuts])
        action.triggered.connect(slot)
        if menu is not None:
            menu.addAction(action)
        return action

    def _build_actions(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&Arquivo")
        self._action(file_menu, "Novo", self.new_project, "Ctrl+N")
        self._action(file_menu, "Abrir…", self.open_project, "Ctrl+O")
        self._action(file_menu, "Salvar", self.save_project, "Ctrl+S")
        self._action(file_menu, "Salvar como…", self.save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        self._action(file_menu, "Sair", self.close)
        edit_menu = bar.addMenu("&Editar")
        self.undo_action = self._action(edit_menu, "Desfazer", self.undo, "Ctrl+Z")
        self.redo_action = self._action(edit_menu, "Refazer", self.redo,
                                        ["Ctrl+Y", "Ctrl+Shift+Z"])
        edit_menu.addSeparator()
        for key, text in (("move", "Mover"), ("copy", "Copiar"), ("rotate", "Girar"),
                          ("split", "Dividir")):
            self._action(edit_menu, text, lambda _=False, k=key: self.run_selection_action(k))
        self.delete_action = self._action(edit_menu, "Excluir", self.delete_selection, "Del")
        view_menu = bar.addMenu("E&xibir")
        self._action(view_menu, "Planta", lambda: self.set_view("plan"))
        self._action(view_menu, "3D", lambda: self.set_view("3d"))
        self._action(view_menu, "Lado a lado", lambda: self.set_view("split"))
        view_menu.addSeparator()
        self._action(view_menu, "Enquadrar tudo", self.fit_all)
        view_menu.addSeparator()
        self.bars_menu = view_menu.addMenu("Barras")
        self._action(view_menu, "Reorganizar barras", self.reset_bars)
        self.selection_bar_action = self._action(view_menu, "Mini-barra da seleção",
                                                 self._toggle_selection_bar)
        self.selection_bar_action.setCheckable(True)
        self.selection_bar_action.setChecked(True)
        project_menu = bar.addMenu("&Projeto")
        self._action(project_menu, "Tipos de parede…", lambda: self.edit_type("IfcWallType"))
        self._action(project_menu, "Tipos de porta…", lambda: self.edit_type("IfcDoorType"))
        help_menu = bar.addMenu("A&juda")
        self._action(help_menu, "Registrar observação…", self.register_note)
        self._action(help_menu, "Sobre", self.about)

        self.tools_bar = ToolsBar(self)
        self.history_bar = history_bar(self)
        self.options_bar = OptionsBar(self)
        self.tool_actions = self.tools_bar.actions_by_tool
        for toolbar in (self.tools_bar, self.history_bar, self.options_bar):
            self.bars_menu.addAction(toolbar.toggleViewAction())
        self.options_bar.toggleViewAction().triggered.connect(
            lambda checked: setattr(self.options_bar, "wanted", checked))
        self.reset_bars()
        self.tool_actions["select"].setChecked(True)

    def reset_bars(self) -> None:
        """Posição inicial (spec/ui 03 §2): Ferramentas à esquerda, Histórico e Opções no
        topo."""
        for toolbar, area in ((self.tools_bar, Qt.LeftToolBarArea),
                              (self.history_bar, Qt.TopToolBarArea),
                              (self.options_bar, Qt.TopToolBarArea)):
            self.removeToolBar(toolbar)
            self.addToolBar(area, toolbar)
            toolbar.setVisible(toolbar is not self.options_bar)
        self.options_bar.wanted = True
        self.options_bar.show_for(self.toolbox.active)

    def _toggle_selection_bar(self, checked: bool) -> None:
        self.selection_bar.enabled = checked
        self.plan.update()

    def _build_status(self) -> None:
        self.hint = QLabel()
        self.coords = QLabel()
        self.statusBar().addWidget(self.hint, 1)
        self.statusBar().addPermanentWidget(self.coords)
        self.statusBar().addPermanentWidget(QLabel(f"Grade {fmt(self.ctx.grid)} m"))

    def _restore(self) -> None:
        settings = _settings()
        geometry, state = settings.value("geometria"), settings.value("paineis")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state, STATE_VERSION)
        self.options_bar.show_for(self.toolbox.active)

    # --- atualização ------------------------------------------------------------------

    def _on_session(self, event: str) -> None:
        if event == "document":
            self.toolbox.reset()
            self.activate_tool("select")
            self.ctx.invalidate()
            self.scene.load(self.session.doc.ifc)
            self.plan.fit()
            self.view3d.fit()
            self._refresh_all()
        elif event == "model":
            self.ctx.invalidate()
            self.scene.update(self.session.doc.ifc, self.session.last_changed)
            tool = self.toolbox.active
            if tool.cursor is not None and tool.name in ("door", "split"):
                tool.move(tool.cursor, Mods())  # a pré-visualização vê o modelo novo
            self._refresh_all()
        elif event == "storey":
            self.ctx.invalidate()
            self._refresh_all()
        elif event == "selection":
            self.properties.refresh()
            self.plan.update()
            self.view3d.update()
        elif event == "messages":
            self._show_messages()

    def _refresh_all(self) -> None:
        self.project.refresh()
        self.options_bar.refresh()
        self.properties.refresh()
        self.plan.update()
        self.view3d.update()
        self._refresh_title()
        undo = self.session.history.undo_stack
        redo = self.session.history.redo_stack
        self.undo_action.setEnabled(bool(undo))
        self.redo_action.setEnabled(bool(redo))
        self.undo_action.setToolTip(f"Desfazer {undo[-1].label}" if undo else "Desfazer")
        self.redo_action.setToolTip(f"Refazer {redo[-1].label}" if redo else "Refazer")
        self.hint.setText(self.toolbox.active.hint())

    def _refresh_title(self) -> None:
        name = Path(self.session.path).name if self.session.path else "Projeto sem nome"
        self.setWindowTitle(f"{name}{'*' if self.session.modified else ''} — BrasBim")

    def _show_messages(self) -> None:
        self.messages.clear()
        for m in self.session.messages[-60:]:
            item = QListWidgetItem(f"{m['time']}  {m['text']}")
            item.setToolTip(m["level"])
            item.setForeground(QColor(_LEVEL_COLOR.get(m["level"], "#333333")))
            self.messages.addItem(item)
        self.messages.scrollToBottom()
        last = self.session.messages[-1] if self.session.messages else None
        if last and last["level"] == "recusa":
            self.statusBar().showMessage(last["text"], 6000)

    def _show_cursor(self, x: float, y: float) -> None:
        self.coords.setText(f"x {fmt(x)}   y {fmt(y)}")

    # --- ações -------------------------------------------------------------------------

    def activate_tool(self, name: str) -> None:
        tool = self.toolbox.activate(name)
        self.tools_bar.mark(name)
        self.options_bar.show_for(tool)
        self.hint.setText(tool.hint())
        self.properties.refresh()
        self.plan.update()
        self.plan.setFocus()

    def undo(self) -> None:
        self.toolbox.active.cancel()
        self.session.undo()

    def redo(self) -> None:
        self.toolbox.active.cancel()
        self.session.redo()

    def delete_selection(self) -> None:
        if not self.session.selection:
            return
        try:
            tx, cascade = delete_transaction(self.session)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        if cascade and not self.confirm(
                f"A exclusão leva junto {cascade} porta(s) das paredes selecionadas. Continuar?"):
            return
        self.session.run(tx)

    def confirm(self, text: str) -> bool:
        answer = QMessageBox.question(self, "Confirmar", text)
        return answer == QMessageBox.Yes

    def set_view(self, mode: str) -> None:
        if mode == "split":
            if not self.split:
                self.splitter.addWidget(self.plan)
                self.splitter.addWidget(self.view3d)
                self.tabs.hide()
                self.splitter.show()
                self.plan.show()  # a aba que não estava à frente sai das abas oculta
                self.view3d.show()
                half = max(self.splitter.width() // 2, 1)
                self.splitter.setSizes([half, half])
                self.split = True
            return
        if self.split:
            self.tabs.addTab(self.plan, "Planta")
            self.tabs.addTab(self.view3d, "3D")
            self.splitter.hide()
            self.tabs.show()
            self.split = False
        self.tabs.setCurrentWidget(self.plan if mode == "plan" else self.view3d)

    def edit_type(self, ifc_class: str, gid: str | None = None) -> None:
        """Janela de tipos de parede ou de porta, aberta no tipo ``gid``."""
        dialog_class = WallTypesDialog if ifc_class == "IfcWallType" else DoorTypesDialog
        self.toolbox.active.cancel()
        dialog_class(self.session, self, select=gid).exec()
        self.toolbox.check_types()
        self.options_bar.refresh()
        self.properties.refresh()
        self.plan.update()

    def run_selection_action(self, key: str) -> None:
        """Ação da mini-barra ou do menu Editar sobre a seleção (spec/ui 03 §5)."""
        session, doc = self.session, self.session.doc
        if key == "delete":
            self.delete_selection()
            return
        if key == "split":
            walls = [g for g in session.selection
                     if doc.find(g) is not None and doc.find(g).is_a("IfcWall")]
            tool = self.toolbox.tools["split"]
            self.activate_tool("split")
            tool.only = set(walls) if len(walls) == 1 and len(session.selection) == 1 else None
            self.hint.setText(tool.hint())
            return
        if not session.selection:
            session.message("selecione os elementos antes", "recusa")
            return
        if key in ("move", "copy", "rotate"):
            self.activate_tool(key)
            return
        door_list = [doc.get(g) for g in sorted(session.selection)]
        flip = fc.flip_opening if key == "flip_opening" else fc.flip_hinges
        session.run(lambda: fc.flip_each(doc, door_list, flip))

    def fit_all(self) -> None:
        self.plan.fit()
        self.view3d.fit()

    def _ask_save(self) -> bool:
        """Pergunta se salva as alterações; devolve se pode continuar."""
        if not self.session.modified:
            return True
        answer = QMessageBox.question(
            self, "Alterações não salvas", "Salvar as alterações do projeto?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def new_project(self) -> None:
        if self._ask_save():
            self.session.new()

    def open_project(self) -> None:
        if not self._ask_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Abrir projeto", "", "IFC (*.ifc)")
        if path:
            try:
                self.session.open(path)
            except (OSError, RuntimeError, OpError) as e:
                self.session.message(f"não foi possível abrir {path}: {e}", "recusa")

    def save_project(self) -> bool:
        if not self.session.path:
            return self.save_project_as()
        self.session.save()
        return True

    def save_project_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Salvar projeto", "", "IFC (*.ifc)")
        if not path:
            return False
        if not path.lower().endswith(".ifc"):
            path += ".ifc"
        self.session.save(path)
        return True

    def register_note(self) -> None:
        text, ok = QInputDialog.getMultiLineText(
            self, "Registrar observação",
            "O que você tentou fazer, o que esperava e o que aconteceu?")
        if ok and text.strip():
            path = feedback.write_note(self.session, text, self.toolbox.active.label)
            self.session.message(f"Observação registrada em {path}")

    def about(self) -> None:
        QMessageBox.about(self, "Sobre o BrasBim",
                          f"BrasBim {feedback.version()}\n\nSoftware BIM open source e "
                          "IFC-nativo.\nAplicativo GPL-3.0-or-later; núcleo LGPL-3.0-or-later.")

    def closeEvent(self, event):
        if not self._ask_save():
            event.ignore()
            return
        settings = _settings()
        settings.setValue("geometria", self.saveGeometry())
        settings.setValue("paineis", self.saveState(STATE_VERSION))
        self.session.close()
        event.accept()

    # --- erro inesperado (§8) ------------------------------------------------------------

    def install_excepthook(self) -> None:
        previous = sys.excepthook

        def hook(exc_type, exc, tb):
            try:
                path = feedback.write_crash(self.session, exc, self.toolbox.active.label)
                self.toolbox.active.cancel()
                QMessageBox.critical(
                    self, "Erro inesperado",
                    f"{exc_type.__name__}: {exc}\n\nO modelo continua no último estado "
                    f"consistente. Relatório gravado em:\n{path}")
            except Exception:  # noqa: BLE001 - o próprio aviso falhou: usa o padrão
                previous(exc_type, exc, tb)

        sys.excepthook = hook

