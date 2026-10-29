# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela principal (``spec/ui/01-janela-e-ferramentas.md`` §2, §6, §8, §9; barras e
mini-barra, ``spec/ui/03-barras-e-icones.md`` §2–§5)."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import display_layers, intervention, municipal, pens, select_similar, snap
from brasbim.core import storeys as storeys_
from brasbim.core.annotations import commands as ac
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError
from brasbim.core.drawings import saved_views
from brasbim.core.drawings import sheets as sheets_
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import Transaction
from brasbim.core.walls import commands as cmd
from brasbim.ui import feedback, paper, saved_views_ui, theme
from brasbim.ui.assistant import AssistantPanel
from brasbim.ui.command_line import (
    VISIBLE_KEY,
    AliasesDialog,
    CommandLine,
    load_aliases,
    save_aliases,
)
from brasbim.ui.layers_panel import LayersPanel
from brasbim.ui.library_panel import FoldersDialog, LibraryPanel, make_index, set_user_folders
from brasbim.ui.master_editor import MasterEditor
from brasbim.ui.materials_dialog import MaterialsDialog
from brasbim.ui.municipal_dialog import MunicipalDialog
from brasbim.ui.paper import SheetView, export_pdf
from brasbim.ui.pens_dialog import PensDialog
from brasbim.ui.plan_view import PlanView
from brasbim.ui.project_panel import ProjectPanel
from brasbim.ui.properties import PropertiesPanel
from brasbim.ui.scene3d import STANDARD_VIEWS, Scene
from brasbim.ui.section_view import SectionView
from brasbim.ui.selection_bar import SelectionBar
from brasbim.ui.session import Session
from brasbim.ui.table_view import TableView
from brasbim.ui.team_panel import JoinDialog, TeamPanel
from brasbim.ui.toolbars import OptionsBar, ToolsBar, history_bar
from brasbim.ui.tools import Mods, PlanContext, ToolBox, fmt
from brasbim.ui.types_dialog import (
    BeamTypesDialog,
    ColumnTypesDialog,
    DoorTypesDialog,
    SlabTypesDialog,
    WallTypesDialog,
    WindowTypesDialog,
)
from brasbim.ui.view3d import View3D, storey_of

STATE_VERSION = 3  # disposição de painéis e barras; muda quando as barras mudam
_LEVEL_COLOR = {"recusa": theme.ERROR, "aviso": theme.WARN, "info": theme.INK}


SELECT_MODE_KEY = "selecao/somar_cliques"  # spec/ui 28 §4
SHEET_LIMITS_KEY = "prancha/limites_dos_desenhos"  # spec/ui 29 §3
SITUATION_VIEW_KEY = "situacao/vista"  # spec/ui 31 §3


def _settings() -> QSettings:
    """Preferências da janela; o formato padrão permite aos testes usar outro lugar."""
    return QSettings(QSettings.defaultFormat(), QSettings.UserScope, "BrasBim", "BrasBim")


BACKUP_CHOICES = ((0, "Desligado"), (2, "A cada 2 minutos"), (5, "A cada 5 minutos"),
                  (10, "A cada 10 minutos"))
BACKUP_DEFAULT = 5  # min (spec/ui 21 §2)


def cascade_text(doors_n: int, windows_n: int, objects_n: int = 0) -> str:
    """"1 porta e 2 janelas" (spec/ui 09 §4.1), e os objetos presos às paredes."""
    parts = [f"{n} {one if n == 1 else many}" for n, one, many in
             ((doors_n, "porta", "portas"), (windows_n, "janela", "janelas"),
              (objects_n, "objeto", "objetos")) if n]
    if len(parts) > 2:
        return ", ".join(parts[:-1]) + " e " + parts[-1]
    return " e ".join(parts)


def delete_transaction(session: Session) -> tuple[Transaction, str]:
    """Exclusão da seleção numa transação (§5.1): esquadrias antes das paredes, depois
    pilares, vigas e lajes (spec/ui 10 §4.1); operações
    repetidas (abertura, junção entre duas paredes excluídas) entram uma vez. Devolve a
    transação e o que sai junto com as paredes ("1 porta e 2 janelas"; vazio se nada)."""
    tx, cascade = delete_elements(session.doc, session.selection)
    return tx, cascade_text(cascade["IfcDoor"], cascade["IfcWindow"],
                            cascade.get("objects", 0))


class _TabBar(QTabBar):
    """Abas da área central (spec/ui 32 §3): clique do meio fecha; botão direito oferece
    fechar esta, as outras ou todas. Planta e 3D não fecham."""

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            index = self.tabAt(event.position().toPoint())
            if index >= 0:
                self.window_.close_tab(self.window_.tabs.widget(index))
                return
        super().mouseReleaseEvent(event)

    def _menu(self, pos) -> None:
        index = self.tabAt(pos)
        if index < 0:
            return
        window = self.window_
        widget = window.tabs.widget(index)
        menu = QMenu(self)
        close = menu.addAction("Fechar", lambda: window.close_tab(widget))
        close.setEnabled(window.closable(widget))
        menu.addAction("Fechar as outras abas", lambda: window.close_tabs(keep=widget))
        menu.addAction("Fechar todas as abas", lambda: window.close_tabs())
        menu.exec(self.mapToGlobal(pos))


class _Pane(QWidget):
    """Vista no lado a lado com uma faixa de título; clique duplo na faixa maximiza a
    vista ou volta às duas metades (pente fino, 2026-10-27)."""

    def __init__(self, title: str, toggle) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = QLabel(title)
        self.header.setToolTip("Clique duplo: maximizar / restaurar")
        self.header.setStyleSheet(f"background:{theme.FRAME}; color:{theme.INK_SOFT};"
                                  f"padding:2px 8px; border-bottom:1px solid {theme.RULE};")
        self.header.mouseDoubleClickEvent = lambda _event: toggle(self)
        layout.addWidget(self.header)

    def hold(self, view) -> None:
        self.layout().addWidget(view, 1)


class MainWindow(QMainWindow):

    quiet_dialogs = False  # True nos testes: avisos só em Mensagens

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.ctx = PlanContext(session)
        self.section_views: dict[str, SectionView] = {}  # abas de corte e fachada
        self.sheet_views: dict[str, SheetView] = {}  # abas de prancha (spec/ui 15)
        self.table_views: dict[str, TableView] = {}  # abas de tabela (spec/ui 17)
        self.master_views: dict[str, MasterEditor] = {}  # folhas mestras (spec/ui 26)
        self.toolbox = ToolBox(self.ctx)
        self.scene = Scene()
        self.scene.load(session.doc.ifc, session.doc)
        self.plan = PlanView(self.toolbox)
        self.view3d = View3D(self.scene, self.toolbox)
        self.ctx.input_view = self.plan
        self.split = False
        self.recent_commands: list[str] = []  # paleta e linha de comando (spec/ui 23, 24)
        self.active_saved_view: str | None = None  # vista salva aberta (spec/ui 25 §4)
        self.window_pens: str | None = None  # tabela de penas da vista aberta (spec/ui 27)
        saved_views_ui.scene_provider = lambda: self.scene
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_status()
        session.listeners.append(self._on_session)
        for view in (self.plan, self.view3d):
            view.cursor_moved.connect(self._show_cursor)
            view.hint_changed.connect(self._set_hint)
            view.tool_finished.connect(lambda: self.activate_tool("select"))
            view.tool_options_changed.connect(self._options_changed)
            view.tool_requested.connect(self.activate_tool)
            view.context_requested.connect(
                lambda gid, pos, v=view: self.show_context_menu(v, gid, pos))
            view.selection_bar = SelectionBar(view, self.run_selection_action)
        self.selection_bar = self.plan.selection_bar
        self.resize(1280, 800)
        self._hook_tools()
        self._restore()
        self._refresh_all()
        # Cópia de segurança (spec/ui 21): o relógio bate a cada minuto, renova o sinal de
        # vida e grava a cópia quando passou o intervalo escolhido.
        self._last_backup = time.monotonic()
        self.backup_timer = QTimer(self)
        self.backup_timer.setInterval(60_000)
        self.backup_timer.timeout.connect(self.backup_tick)
        self.backup_timer.start()
        # Projeto compartilhado (spec/ui 33 §2): o que chegou da rede é aplicado aqui.
        self.team_timer = QTimer(self)
        self.team_timer.setInterval(40)
        self.team_timer.timeout.connect(self.session.poll)
        self.team_timer.start()
        self._refresh_team()

    # --- montagem --------------------------------------------------------------------

    def _build_central(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setTabBar(_TabBar(self))
        self.tabs.setTabsClosable(True)  # spec/ui 32 §3
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(lambda i: self.close_tab(self.tabs.widget(i)))
        self.splitter = QSplitter(Qt.Horizontal)
        self.central = QWidget()
        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tabs)
        layout.addWidget(self.splitter)
        self.command_line = CommandLine(self)  # spec/ui 24
        self.command_line.aliases = load_aliases(_settings())
        layout.addWidget(self.command_line)
        self.panes = [_Pane("Planta", self.toggle_maximized),
                      _Pane("3D", self.toggle_maximized)]
        for pane in self.panes:
            self.splitter.addWidget(pane)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.hide()
        self._add_fixed_tabs()
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self.central)

    def _dock(self, title: str, name: str, widget, area) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _build_docks(self) -> None:
        self.project = ProjectPanel(self.session)
        self.project.open_view = self.open_view
        self.project.open_saved_view = self.open_saved_view
        self.project.open_plan = self.open_plan
        self.project.update_saved_view = self.update_saved_view
        self.project.save_view = self.save_view
        self.project.open_sheet = self.open_sheet
        self.project.open_master = self.open_master
        self.project.open_table = self.open_table
        self.project.open_library = self.show_library
        self.project.use_object_type = self.use_object_type
        self.project.edit_object_type = self.edit_object_type
        self.project.save_to_library = self.save_object_to_library
        self.project.edit_object = self.edit_object
        self.project.new_object = self.new_object
        self.project_dock = self._dock("Projeto", "projeto", self.project,
                                       Qt.LeftDockWidgetArea)
        self.properties = PropertiesPanel(self.session, self.toolbox)
        self.properties.setMinimumWidth(310)
        self.properties.edit_type = self.edit_type
        self.properties.open_view = self.open_view
        self.properties.open_sheet = self.open_sheet
        self.properties.open_table = self.open_table
        self.properties.edit_project_info = self.edit_project_info
        self.properties.edit_object_type = self.edit_object_type
        self.properties.edit_object = self.edit_object
        self.properties_dock = self._dock("Propriedades", "propriedades", self.properties,
                                          Qt.RightDockWidgetArea)
        self.messages = QListWidget()
        self.messages.setWordWrap(True)
        self.messages.setSelectionMode(QListWidget.ExtendedSelection)
        copy_messages = QAction("Copiar", self.messages)  # medidas copiáveis (spec/ui 30 §7)
        copy_messages.setShortcut(QKeySequence.Copy)
        copy_messages.setShortcutContext(Qt.WidgetShortcut)
        copy_messages.triggered.connect(self.copy_messages)
        self.messages.addAction(copy_messages)
        self.messages.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.messages_dock = self._dock("Mensagens", "mensagens", self.messages,
                                        Qt.BottomDockWidgetArea)
        self.messages_dock.setMaximumHeight(160)
        # Assistente (spec/ui 16): fechado até ser pedido em Exibir > Assistente
        self.assistant = AssistantPanel(self.session)
        self.assistant.finished.connect(self._assistant_finished)
        self.assistant_dock = self._dock("Assistente", "assistente", self.assistant,
                                         Qt.RightDockWidgetArea)
        self.assistant_dock.hide()
        # Camadas (spec/ui 18 §7): painel separado, solto; fechado até ser pedido
        self.layers = LayersPanel(self.session)
        self.layers_dock = self._dock("Camadas", "camadas", self.layers, Qt.RightDockWidgetArea)
        self.layers_dock.setFloating(True)
        self.layers_dock.resize(320, 480)
        self.layers_dock.hide()
        # Biblioteca de objetos (objeto-parametrico.md §4.2): solta, fechada até ser pedida
        self.library = LibraryPanel(self.session)
        self.library.use_type.connect(self.use_object_type)
        self.plan.object_dropped.connect(self.drop_object)
        self.project.library_index = self.library.index
        self.library_dock = self._dock("Biblioteca de objetos", "biblioteca", self.library,
                                       Qt.RightDockWidgetArea)
        self.library_dock.setFloating(True)
        self.library_dock.resize(380, 560)
        self.library_dock.hide()
        self.project.library_index = self.library.index
        # Equipe (spec/ui 33 §4): aparece ao compartilhar ou entrar
        self.team = TeamPanel(self.session)
        self.team_dock = self._dock("Equipe", "equipe", self.team, Qt.RightDockWidgetArea)
        self.team_dock.hide()

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
        self._action(file_menu, "Importar desenho (DXF, DWG)…", lambda: self.import_drawing())
        self._action(file_menu, "Exportar PDF…", lambda: self.export_pdf(), "Ctrl+P")
        self._action(file_menu, "Exportar tabela…", lambda: self.export_table())
        self._action(file_menu, "Dados do projeto…", self.edit_project_info)
        file_menu.addSeparator()
        backup_menu = file_menu.addMenu("Salvamento automático")  # spec/ui 21 §2
        group = QActionGroup(self)
        self.backup_actions: dict[int, QAction] = {}
        for minutes, text in BACKUP_CHOICES:
            action = backup_menu.addAction(text)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, m=minutes: self.set_backup_minutes(m))
            group.addAction(action)
            self.backup_actions[minutes] = action
        self.backup_minutes = BACKUP_DEFAULT
        self.backup_actions[BACKUP_DEFAULT].setChecked(True)
        file_menu.addSeparator()
        self._action(file_menu, "Sair", self.close)
        edit_menu = bar.addMenu("&Editar")
        self.undo_action = self._action(edit_menu, "Desfazer", self.undo, "Ctrl+Z")
        self.redo_action = self._action(edit_menu, "Refazer", self.redo,
                                        ["Ctrl+Y", "Ctrl+Shift+Z"])
        edit_menu.addSeparator()
        for key, text in (("move", "Mover"), ("copy", "Copiar"), ("rotate", "Girar"),
                          ("mirror", "Espelhar"), ("split", "Dividir")):
            self._action(edit_menu, text, lambda _=False, k=key: self.run_selection_action(k))
        self.delete_action = self._action(edit_menu, "Excluir", self.delete_selection, "Del")
        edit_menu.addSeparator()  # pacote de precisão (spec/ui 23)
        self._action(edit_menu, "Girar 90° à esquerda", lambda: self.rotate_quarter(1), "Ctrl+R")
        self._action(edit_menu, "Girar 90° à direita", lambda: self.rotate_quarter(-1),
                     "Ctrl+Shift+R")
        similar_menu = edit_menu.addMenu("Selecionar semelhantes")
        for key, text in select_similar.CRITERIA:
            self._action(similar_menu, text, lambda _=False, k=key: self.select_similar(k))
        situation_menu = edit_menu.addMenu("Situação")  # spec/ui 31 §2
        for code, text, _ in intervention.SITUATIONS:
            self._action(situation_menu, text,
                         lambda _=False, c=code: self.set_selection_situation(c))
        for key, text in (("offset", "Deslocar paralela"), ("trim", "Aparar/estender"),
                          ("fillet", "Concordar"), ("measure", "Medir"),
                          ("selection_area", "Área de seleção")):
            self._action(edit_menu, text, lambda _=False, k=key: self.activate_tool(k))
        self._action(edit_menu, "Remover área de seleção", self.remove_selection_area)
        mode_menu = edit_menu.addMenu("Modo de seleção")  # spec/ui 28 §4
        group = QActionGroup(self)
        self.select_mode_actions = {}
        for value, text in ((True, "Somar cliques (como no CAD)"),
                            (False, "Trocar a seleção a cada clique")):
            action = self._action(mode_menu, text,
                                  lambda _=False, v=value: self.set_select_mode(v))
            action.setCheckable(True)
            group.addAction(action)
            self.select_mode_actions[value] = action
        self.select_mode_actions[True].setChecked(True)
        edit_menu.addSeparator()
        self._action(edit_menu, "Paleta de comandos…", self.open_palette, "Ctrl+K")
        self._action(edit_menu, "Apelidos da linha de comando…", self.edit_aliases)
        view_menu = bar.addMenu("E&xibir")
        self._action(view_menu, "Planta", lambda: self.set_view("plan"))
        self._action(view_menu, "3D", lambda: self.set_view("3d"))
        self._action(view_menu, "Lado a lado", lambda: self.set_view("split"))
        view_menu.addSeparator()
        self._action(view_menu, "Enquadrar tudo", self.fit_all)
        standard = view_menu.addMenu("Vista 3D padrão")
        for key, (label, _, _) in STANDARD_VIEWS.items():
            if key == "iso_sw":
                standard.addSeparator()
            self._action(standard, label, lambda _=False, k=key: self.standard_view(k))
        self._action(view_menu, "Salvar vista…", lambda: self.save_view(), "Ctrl+Alt+S")
        self.show_in_plan_action = self._action(view_menu, "Mostrar na planta",
                                                lambda: self.show_in_plan(), "Ctrl+Shift+P")
        self.show_in_3d_action = self._action(view_menu, "Mostrar no 3D", self.show_in_3d,
                                              "Ctrl+Shift+3")
        self._action(view_menu, "Fechar aba", lambda: self.close_tab(),  # spec/ui 32 §3
                     ["Ctrl+W", "Ctrl+F4"])
        self._action(view_menu, "Fechar todas as abas", lambda: self.close_tabs())
        self.sheet_limits_action = self._action(  # spec/ui 29 §3
            view_menu, "Limites dos desenhos na prancha",
            lambda checked: self.set_sheet_limits(checked))
        self.sheet_limits_action.setCheckable(True)
        self.sheet_limits_action.setChecked(True)
        view_menu.addSeparator()
        self._action(view_menu, "Pavimento acima", lambda: self.step_storey(1), "PgUp")
        self._action(view_menu, "Pavimento abaixo", lambda: self.step_storey(-1), "PgDown")
        view_menu.addSeparator()
        self.panels_menu = view_menu.addMenu("Painéis")
        for dock in (self.project_dock, self.properties_dock, self.messages_dock):
            self.panels_menu.addAction(dock.toggleViewAction())
        assistant_action = self.assistant_dock.toggleViewAction()
        assistant_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self.panels_menu.addAction(assistant_action)
        layers_action = self.layers_dock.toggleViewAction()
        layers_action.setShortcut(QKeySequence("Ctrl+Shift+L"))
        self.panels_menu.addAction(layers_action)
        library_action = self.library_dock.toggleViewAction()
        library_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self.panels_menu.addAction(library_action)
        self.panels_menu.addAction(self.team_dock.toggleViewAction())
        self.bars_menu = view_menu.addMenu("Barras")
        self._action(view_menu, "Reorganizar barras", self.reset_bars)
        self.selection_bar_action = self._action(view_menu, "Mini-barra da seleção",
                                                 self._toggle_selection_bar)
        self.selection_bar_action.setCheckable(True)
        self.selection_bar_action.setChecked(True)
        view_menu.addSeparator()
        self.tags_action = self._action(view_menu, "Etiquetas de esquadrias",
                                        lambda v: self._set_plan_option("show_tags", v))
        self.tag_size_action = self._action(view_menu, "Medidas na etiqueta",
                                            lambda v: self._set_plan_option("show_tag_size", v))
        self.structure_tags_action = self._action(
            view_menu, "Etiquetas de estrutura",
            lambda v: self._set_plan_option("show_structure_tags", v))
        self.object_tags_action = self._action(
            view_menu, "Etiquetas de objetos",
            lambda v: self._set_plan_option("show_object_tags", v))
        self.space_numbers_action = self._action(
            view_menu, "Número dos ambientes",
            lambda v: self._set_plan_option("show_space_numbers", v))
        self.weights_action = self._action(
            view_menu, "Espessuras de linha", lambda v: self._set_weights(v))
        self.view_symbols_action = self._action(
            view_menu, "Símbolos de corte",
            lambda v: self._set_plan_option("show_view_symbols", v))
        for action, value in ((self.tags_action, True), (self.tag_size_action, False),
                              (self.structure_tags_action, True),
                              (self.object_tags_action, False),
                              (self.space_numbers_action, False), (self.weights_action, True),
                              (self.view_symbols_action, True)):
            action.setCheckable(True)
            action.setChecked(value)
        view_menu.addSeparator()
        self.pens_menu = view_menu.addMenu("Tabela de penas")  # spec/ui 27 §4
        self.pens_menu.aboutToShow.connect(self._fill_pens_menu)
        self._snap_menu(view_menu.addMenu("Atração"))
        detail_menu = view_menu.addMenu("Detalhe da planta")
        group = QActionGroup(self)
        self.detail_actions = {}
        for key, text in (("simple", "Simplificado"), ("layers", "Por camadas")):
            action = self._action(detail_menu, text,
                                  lambda _=False, k=key: self.set_plan_detail(k))
            action.setCheckable(True)
            group.addAction(action)
            self.detail_actions[key] = action
        self.detail_actions["simple"].setChecked(True)
        self.above_action = self._action(view_menu, "Elementos acima do plano de corte",
                                         self.set_show_above)
        self.above_action.setCheckable(True)
        self.above_action.setChecked(True)
        situation_menu = view_menu.addMenu("Situação na vista")  # spec/ui 31 §3
        group = QActionGroup(self)
        self.situation_actions = {}
        for key, text in intervention.VIEWS:
            action = self._action(situation_menu, text,
                                  lambda _=False, k=key: self.set_situation_view(k))
            action.setCheckable(True)
            group.addAction(action)
            self.situation_actions[key] = action
        self.situation_actions[intervention.DEFAULT_VIEW].setChecked(True)
        project_menu = bar.addMenu("&Projeto")
        self._action(project_menu, "Tipos de parede…", lambda: self.edit_type("IfcWallType"))
        self._action(project_menu, "Tipos de porta…", lambda: self.edit_type("IfcDoorType"))
        self._action(project_menu, "Tipos de janela…",
                     lambda: self.edit_type("IfcWindowType"))
        self._action(project_menu, "Tipos de pilar…", lambda: self.edit_type("IfcColumnType"))
        self._action(project_menu, "Tipos de viga…", lambda: self.edit_type("IfcBeamType"))
        self._action(project_menu, "Tipos de laje…", lambda: self.edit_type("IfcSlabType"))
        self._action(project_menu, "Materiais…", lambda: self.edit_materials())
        self._action(project_menu, "Tabelas de penas…", lambda: self.edit_pens())
        self._action(project_menu, "Perfil municipal…", lambda: self.edit_municipal())
        project_menu.addSeparator()
        self._action(project_menu, "Biblioteca de objetos", self.show_library)
        self._action(project_menu, "Novo objeto…", lambda: self.new_object())
        self._action(project_menu, "Pastas da biblioteca…", self.edit_library_folders)
        team_menu = bar.addMenu("E&quipe")  # projeto compartilhado (spec/ui 33 §4)
        # lambda: o triggered passa "checked", que tomaria o lugar de name/choose
        self._action(team_menu, "Compartilhar este projeto na rede…",
                     lambda: self.share_project())
        self._action(team_menu, "Entrar num projeto da rede…", lambda: self.join_project())
        team_menu.addSeparator()
        self.team_actions = [
            self._action(team_menu, "Pedir liberação da seleção",
                         lambda: self.session.request_release(self.session.selection)),
            self._action(team_menu, "Liberar a seleção",
                         lambda: self.session.release(self.session.selection)),
            self._action(team_menu, "Liberar minhas reservas", lambda: self.session.release()),
        ]
        self.reservations_action = self._action(team_menu, "Mostrar reservas",
                                                self.set_show_reservations)
        self.reservations_action.setCheckable(True)
        self.reservations_action.setChecked(True)
        team_menu.addSeparator()
        self.leave_action = self._action(team_menu, "Sair do projeto compartilhado",
                                         self.leave_shared)
        help_menu = bar.addMenu("A&juda")
        self._action(help_menu, "Registrar observação…", self.register_note)
        self._action(help_menu, "Sobre", self.about)

        self.tools_bar = ToolsBar(self)
        self.history_bar = history_bar(self)
        self.options_bar = OptionsBar(self)
        self.tool_actions = self.tools_bar.actions_by_tool
        for toolbar in (self.tools_bar, self.history_bar, self.options_bar):
            self.bars_menu.addAction(toolbar.toggleViewAction())
        self.command_line_action = self._action(self.bars_menu, "Linha de comando",
                                                self.set_command_line_visible)
        self.command_line_action.setCheckable(True)
        self.command_line_action.setChecked(True)
        self.options_bar.toggleViewAction().triggered.connect(
            lambda checked: setattr(self.options_bar, "wanted", checked))
        self.reset_bars()
        self.tool_actions["select"].setChecked(True)

    def reset_bars(self) -> None:
        """Posição inicial (spec/ui 03 §2): Ferramentas à esquerda, com duas colunas
        (spec/ui 34 §3), Histórico e Opções no topo."""
        self.tools_bar.setFloating(False)
        self.removeDockWidget(self.tools_bar)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tools_bar)
        # coluna própria, ao lado dos painéis da esquerda (o Projeto tem largura mínima)
        others = [d for d in self.findChildren(QDockWidget) if d is not self.tools_bar
                  and not d.isFloating()
                  and self.dockWidgetArea(d) == Qt.LeftDockWidgetArea]
        if others:
            self.splitDockWidget(self.tools_bar, others[0], Qt.Horizontal)
        self.tools_bar.show()
        self.resizeDocks([self.tools_bar], [2 * self.tools_bar.button_size + 22],
                         Qt.Horizontal)
        for toolbar, area in ((self.history_bar, Qt.TopToolBarArea),
                              (self.options_bar, Qt.TopToolBarArea)):
            self.removeToolBar(toolbar)
            self.addToolBar(area, toolbar)
            toolbar.setVisible(toolbar is not self.options_bar)
        self.options_bar.wanted = True
        self.options_bar.show_for(self.toolbox.active)

    def _set_plan_option(self, name: str, value: bool) -> None:
        """Preferência de desenho da planta (spec/ui 05 §5); não vai para o IFC."""
        setattr(self.plan, name, bool(value))
        self.plan.update()

    def set_plan_detail(self, detail: str) -> None:
        """Exibir > Detalhe da planta (spec/ui 06 §2): preferência, não vai para o IFC."""
        self.detail_actions[detail].setChecked(True)
        self.ctx.detail = detail
        self.ctx.invalidate()
        self.plan.update()

    def set_show_above(self, value: bool) -> None:
        """Exibir > Elementos acima do plano de corte (spec/ui 06 §3.2)."""
        self.above_action.setChecked(bool(value))
        self.ctx.show_above = bool(value)
        self.ctx.invalidate()
        self.plan.update()

    def _toggle_selection_bar(self, checked: bool) -> None:
        for view in (self.plan, self.view3d):
            view.selection_bar.enabled = checked
            view.update()

    def _build_status(self) -> None:
        self.hint = QLabel()
        self.coords = QLabel()
        self.statusBar().addWidget(self.hint, 1)
        self.hint.setVisible(not self.command_line.isVisibleTo(self))
        self.statusBar().addPermanentWidget(self.coords)
        self.statusBar().addPermanentWidget(QLabel(f"Grade {fmt(self.ctx.grid)} m"))
        self.team_label = QLabel()  # projeto compartilhado (spec/ui 33 §4)
        self.team_label.hide()
        self.statusBar().addPermanentWidget(self.team_label)
        self.saved_view_label = QLabel()  # vista salva aberta (spec/ui 25 §4)
        self.saved_view_label.hide()
        self.statusBar().addPermanentWidget(self.saved_view_label)
        self.scale_combo = QComboBox()
        self.scale_combo.setToolTip("Escala da planta do pavimento ativo (textos, cotas e "
                                    "símbolos seguem a escala)")
        for value in storeys_.SCALES:
            self.scale_combo.addItem(f"1:{value}", value)
        self.scale_combo.currentIndexChanged.connect(self._scale_chosen)
        self.statusBar().addPermanentWidget(self.scale_combo)

    def _restore(self) -> None:
        settings = _settings()
        geometry, state = settings.value("geometria"), settings.value("paineis")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state, STATE_VERSION)
        for action, key, option in ((self.tags_action, "etiquetas_porta", "show_tags"),
                                    (self.tag_size_action, "medidas_etiqueta",
                                     "show_tag_size"),
                                    (self.structure_tags_action, "etiquetas_estrutura",
                                     "show_structure_tags"),
                                    (self.object_tags_action, "etiquetas_objetos",
                                     "show_object_tags"),
                                    (self.space_numbers_action, "numeros_ambientes",
                                     "show_space_numbers"),
                                    (self.weights_action, "espessuras_linha", "show_weights"),
                                    (self.view_symbols_action, "simbolos_corte",
                                     "show_view_symbols")):
            value = settings.value(key)
            if value is not None:
                action.setChecked(str(value).lower() == "true")
                self._set_plan_option(option, action.isChecked())
        try:
            minutes = int(settings.value("salvamento_automatico_min", BACKUP_DEFAULT))
        except (TypeError, ValueError):
            minutes = BACKUP_DEFAULT
        if minutes in self.backup_actions:
            self.set_backup_minutes(minutes)
        mode = settings.value(SELECT_MODE_KEY)
        if mode is not None:
            self.set_select_mode(str(mode).lower() == "true", save=False)
        limits = settings.value(SHEET_LIMITS_KEY)
        if limits is not None:
            self.set_sheet_limits(str(limits).lower() == "true", save=False)
        situation = settings.value(SITUATION_VIEW_KEY)
        if situation in self.situation_actions:
            self.set_situation_view(situation, save=False)
        detail = settings.value("detalhe_planta")
        if detail in self.detail_actions:
            self.set_plan_detail(detail)
        above = settings.value("acima_do_corte")
        if above is not None:
            self.set_show_above(str(above).lower() == "true")
        visible = settings.value(VISIBLE_KEY)
        self.set_command_line_visible(visible is None or str(visible).lower() == "true")
        self.options_bar.show_for(self.toolbox.active)
        self.command_line.refresh_tool()

    # --- atualização ------------------------------------------------------------------

    def _on_session(self, event: str) -> None:
        if event in ("model", "layers", "document"):
            paper.invalidate_images()
        if event == "document":
            self.close_saved_view()
        elif event == "storey" and self.active_saved_view is not None:
            entity = self.session.doc.find(self.active_saved_view)
            state = saved_views.read_state(entity) if entity is not None else None
            if state is None or state["kind"] != "plan" \
                    or state["storey"] != self.session.storey_id:
                self.close_saved_view()
        if event == "document":
            self.ctx.area = None  # a área de seleção é da sessão (spec/ui 38 §2)
            self.toolbox.reset()
            self._hook_tools()
            self._refresh_section_views(reset=True)
            self.activate_tool("select")
            self.ctx.invalidate()
            self.scene.load(self.session.doc.ifc, self.session.doc)
            self.plan.fit()
            self.view3d.fit()
            self._refresh_all()
        elif event == "model":
            self.ctx.invalidate()
            self._refresh_section_views()
            if self.session.last_tx is not None and any(
                    op.op == "material.edit" for op in self.session.last_tx.ops):
                self.scene.load(self.session.doc.ifc, self.session.doc)  # cores novas
            else:
                self.scene.update(self.session.doc.ifc, self.session.last_changed)
            tool = self.toolbox.active
            if tool.cursor is not None and tool.name in ("door", "window", "split", "column"):
                tool.move(tool.cursor, Mods())  # a pré-visualização vê o modelo novo
            self._refresh_all()
        elif event == "storey":
            self.ctx.invalidate()
            self._refresh_all()
        elif event == "layers":  # exibição das camadas (spec/ui 18 §4)
            self.ctx.invalidate()
            self._refresh_section_views()
            self.scene.apply_layers()
            self._refresh_all()
        elif event == "selection":
            self.properties.refresh()
            for view in self.section_views.values():
                view.update()
            self.plan.update()
            self.view3d.update()
            self._refresh_show_actions()
        elif event == "messages":
            self._show_messages()
        elif event == "backup":
            self.statusBar().showMessage(
                f"Cópia de segurança às {datetime.now():%H:%M}", 5000)
        elif event == "team":
            self._refresh_team()
            self.plan.update()

    def _refresh_all(self) -> None:
        self.refresh_pens()
        self.project.refresh()
        self.options_bar.refresh()
        self.properties.refresh()
        self.plan.update()
        self.view3d.update()
        self._refresh_title()
        self._refresh_scale()
        undo = self.session.history.undo_stack
        redo = self.session.history.redo_stack
        self.undo_action.setEnabled(bool(undo))
        self.redo_action.setEnabled(bool(redo))
        self.undo_action.setToolTip(f"Desfazer {undo[-1].label}" if undo else "Desfazer")
        self.redo_action.setToolTip(f"Refazer {redo[-1].label}" if redo else "Refazer")
        self._set_hint(self.toolbox.active.hint())
        self._refresh_show_actions()

    def _refresh_show_actions(self) -> None:
        for action in (self.show_in_plan_action, self.show_in_3d_action):
            action.setEnabled(bool(self.session.selection))

    def _refresh_scale(self) -> None:
        storey = self.session.storey
        self.scale_combo.blockSignals(True)
        self.scale_combo.setCurrentIndex(max(0, self.scale_combo.findData(
            storeys_.scale(storey) if storey is not None else storeys_.DEFAULT_SCALE)))
        self.scale_combo.blockSignals(False)
        entity = self.session.doc.find(self.active_saved_view) \
            if self.active_saved_view else None
        if entity is None:
            self.saved_view_label.hide()
            return
        self.saved_view_label.setText(f"Vista: {saved_views.read_state(entity)['name']}")
        self.saved_view_label.setToolTip("Vista salva aberta; a escala escolhida aqui vale "
                                         "só para a janela")
        self.saved_view_label.show()

    def _scale_chosen(self, index: int) -> None:
        storey, doc = self.session.storey, self.session.doc
        value = self.scale_combo.itemData(index)
        if storey is None or value == storeys_.scale(storey):
            return
        if self._window_scale_active():  # vista salva aberta: só a janela (spec/ui 25 §4)
            storeys_.set_scale_override(storey.GlobalId, value)
            self.ctx.invalidate()
            self._refresh_all()
            return
        self.session.run(lambda: cmd.edit_storey(doc, storey, scale=value))

    def set_select_mode(self, accumulate: bool, save: bool = True) -> None:
        """Editar > Modo de seleção (spec/ui 28 §4): somar cliques ou trocar a seleção."""
        self.ctx.accumulate = bool(accumulate)
        self.ctx.hover = None
        self.select_mode_actions[bool(accumulate)].setChecked(True)
        if save:
            _settings().setValue(SELECT_MODE_KEY, bool(accumulate))
        self._set_hint(self.toolbox.active.hint())
        self.plan.update()

    def set_situation_view(self, view: str, save: bool = True) -> None:
        """Exibir > Situação na vista (spec/ui 31 §3): preferência, não vai para o IFC."""
        self.situation_actions[view].setChecked(True)
        if save:
            _settings().setValue(SITUATION_VIEW_KEY, view)
        self.session.set_situation_view(view)

    def set_selection_situation(self, code: str) -> None:
        """Editar > Situação e mini-barra Situação (spec/ui 31 §2)."""
        session = self.session
        if not session.selection:
            session.message("selecione os elementos antes", "recusa")
            return
        if session.run(lambda: intervention.set_situation(
                session.doc, sorted(session.selection), code)):
            self.properties.refresh()

    def set_sheet_limits(self, show: bool, save: bool = True) -> None:
        """Exibir > Limites dos desenhos na prancha (spec/ui 29 §3): o traço só da tela."""
        self.sheet_limits_action.setChecked(bool(show))
        if save:
            _settings().setValue(SHEET_LIMITS_KEY, bool(show))
        for view in self.sheet_views.values():
            view.update()

    # --- tabelas de penas (spec/ui 27) ---------------------------------------------------

    def window_pen_table(self) -> str:
        """Código da tabela de penas da janela: a da vista salva aberta ou a do projeto."""
        cfg = pens.config(self.session.doc)
        return pens.table(cfg, self.window_pens)["id"]

    def refresh_pens(self) -> None:
        resolved = pens.resolve(self.session.doc, self.window_pens)
        self.plan.pens = resolved
        for view in self.section_views.values():
            if view.pens is not resolved:
                view.pens = resolved
                view.update()

    def _fill_pens_menu(self) -> None:
        self.pens_menu.clear()
        current = self.window_pen_table()
        for table in pens.config(self.session.doc)["tables"]:
            action = self.pens_menu.addAction(table["name"])
            action.setCheckable(True)
            action.setChecked(table["id"] == current)
            action.triggered.connect(lambda _=False, t=table["id"]: self.use_pen_table(t))
        self.pens_menu.addSeparator()
        self.pens_menu.addAction("Editar tabelas…", lambda: self.edit_pens())

    def use_pen_table(self, table_id: str) -> bool:
        """Exibir > Tabela de penas: a tabela passa a ser a do projeto (e da janela)."""
        self.window_pens = None
        doc = self.session.doc
        done = self.session.run(lambda: pens.use_table(doc, table_id))
        self._refresh_all()
        return done or self.window_pen_table() == table_id

    def edit_pens(self, apply=None) -> bool:
        """Projeto > Tabelas de penas… (§4); ``apply`` recebe o quadro antes de gravar
        (testes)."""
        dialog = PensDialog(self.session.doc, self)
        if apply is not None:
            apply(dialog)
        elif dialog.exec() != QDialog.Accepted:
            return False
        doc, new = self.session.doc, dialog.config
        done = self.session.run(lambda: pens.edit_config(doc, new))
        self._refresh_all()
        return done

    def edit_municipal(self, apply=None) -> bool:
        """Projeto > Perfil municipal… (spec/ui 31 §4); ``apply`` recebe o quadro antes de
        gravar (testes)."""
        dialog = MunicipalDialog(self.session.doc, self)
        if apply is not None:
            apply(dialog)
        elif dialog.exec() != QDialog.Accepted:
            return False
        doc, profile = self.session.doc, dialog.profile
        scales = dialog.apply_scales.isChecked()
        done = self.session.run(lambda: municipal.choose(doc, profile, scales))
        self._refresh_all()
        return done

    # --- vistas salvas (spec/ui 25) -------------------------------------------------------

    def _window_scale_active(self) -> bool:
        entity = self.session.doc.find(self.active_saved_view) \
            if self.active_saved_view else None
        return entity is not None and saved_views.read_state(entity)["kind"] == "plan"

    def save_view(self, name: str | None = None, crop: bool = False) -> str | None:
        """Exibir > Salvar vista… e o botão das abas de vistas do painel Projeto (§3). Com
        ``name`` dado não
        pergunta nada; devolve o GlobalId da vista nova."""
        found = saved_views_ui.capture(self)
        if found is None:
            self.session.message("Salvar vista: ponha à frente a planta, o 3D ou um corte",
                                 "aviso")
            return None
        kind, fields, suggested = found
        if name is None:
            dialog = saved_views_ui.SaveViewDialog(
                suggested, saved_views_ui.summary(self, kind, fields), kind == "plan", self)
            if dialog.exec() != QDialog.Accepted:
                return None
            name, crop = dialog.name.text(), dialog.crop.isChecked()
        if crop and kind == "plan":
            kind, fields, _ = saved_views_ui.capture(self, crop=True)
        doc = self.session.doc
        tx = saved_views.create_saved_view(doc, name, kind, **fields) \
            if name.strip() else None
        if tx is None or not self.session.run(tx):
            if tx is None:
                self.session.message("a vista salva precisa de um nome", "recusa")
            return None
        self.active_saved_view = tx.ops[0].id
        self._refresh_scale()
        return tx.ops[0].id

    def update_saved_view(self, gid: str) -> bool:
        """Atualizar com a janela (§4): regrava o que está na tela, mesma origem."""
        doc = self.session.doc
        entity = doc.find(gid)
        if entity is None:
            return False
        state = saved_views.read_state(entity)
        found = saved_views_ui.capture(self, crop=bool(state.get("crop")))
        if found is None or found[0] != state["kind"]:
            self.session.message(f"Atualizar vista: ponha à frente a vista de "
                                 f"{saved_views.KIND_LABEL[state['kind']].lower()}", "aviso")
            return False
        fields = found[1]
        if not self.session.run(lambda: saved_views.edit_saved_view(
                doc, gid, "Atualizar vista salva", **fields)):
            return False
        self.active_saved_view = gid
        self._refresh_scale()
        return True

    def open_saved_view(self, gid: str) -> bool:
        """Abre a vista salva (§4): pavimento, camadas, opções e escala da janela; câmera no
        3D; aba do corte com a escala dela."""
        doc = self.session.doc
        entity = doc.find(gid)
        if entity is None:
            return False
        state = saved_views.read_state(entity)
        self.close_saved_view()
        self.window_pens = state.get("pens")
        if state["layers"] is not None:
            self.session.set_display(display_layers.display_of(state["layers"]))
        if state["kind"] == "plan":
            storey = doc.find(state["storey"])
            if storey is None:
                return False
            if storey.GlobalId != self.session.storey_id:
                self.session.set_storey(storey)
            options = saved_views.options(state)
            for action, name in ((self.tags_action, "show_tags"),
                                 (self.tag_size_action, "show_tag_size"),
                                 (self.structure_tags_action, "show_structure_tags"),
                                 (self.object_tags_action, "show_object_tags"),
                                 (self.space_numbers_action, "show_space_numbers"),
                                 (self.weights_action, "show_weights"),
                                 (self.view_symbols_action, "show_view_symbols")):
                action.setChecked(options[name])
                if name == "show_weights":
                    self._set_weights(options[name])
                else:
                    self._set_plan_option(name, options[name])
            self.set_plan_detail(options["detail"])
            self.set_show_above(options["show_above"])
            self.set_situation_view(options["situation"], save=False)
            stored = storeys_.stored_scale(storey)
            storeys_.set_scale_override(storey.GlobalId,
                                        None if state["scale"] == stored else state["scale"])
            self.ctx.invalidate()
            if not self.split:
                self.set_view("plan")
        elif state["kind"] == "3d":
            camera, cam = self.view3d.camera, state["camera"]
            camera.target = np.array(cam["target"], dtype=float)
            camera.distance, camera.yaw, camera.pitch = (cam["distance"], cam["yaw"],
                                                         cam["pitch"])
            if not self.split:
                self.set_view("3d")
            self.view3d.update()
        else:
            view = self.open_view(state["view"])
            if view is None:
                return False
            view.scale_override = state["scale"]
            view.show_weights = saved_views.options(state)["show_weights"]
            self.set_situation_view(saved_views.options(state)["situation"], save=False)
            view.invalidate()
        self.active_saved_view = gid
        self._refresh_all()
        return True

    def close_saved_view(self) -> None:
        """A janela volta à escala gravada nos pavimentos e nos cortes e à tabela de penas
        do projeto."""
        self.active_saved_view = None
        self.window_pens = None
        storeys_.clear_scale_overrides()
        for view in self.section_views.values():
            if view.scale_override is not None:
                view.scale_override = None
                view.invalidate()
        self.ctx.invalidate()

    def _set_weights(self, value: bool) -> None:
        self._set_plan_option("show_weights", value)
        for view in self.section_views.values():
            view.show_weights = bool(value)
            view.update()

    def open_view(self, gid: str) -> SectionView | None:
        """Abre o corte ou a fachada numa aba própria (spec/ui 14 §7)."""
        if self.session.doc.find(gid) is None:
            return None
        view = self.section_views.get(gid)
        if view is None:
            view = SectionView(self.session, gid)
            view.show_weights = self.weights_action.isChecked()
            self.section_views[gid] = view
            self.tabs.addTab(view, view.title)
        if self.split:
            self.set_view("plan")
        self.tabs.setCurrentWidget(view)
        return view

    def open_plan(self, storey_gid: str) -> bool:
        """Planta do pavimento à frente (desenho de prancha no painel Projeto)."""
        storey = self.session.doc.find(storey_gid)
        if storey is None:
            return False
        if self.session.storey_id != storey_gid:
            self.session.set_storey(storey)
        self.set_view("plan")
        return True

    def open_sheet(self, gid: str) -> SheetView | None:
        """Abre a prancha numa aba (spec/ui 15 §5)."""
        if self.session.doc.find(gid) is None:
            return None
        view = self.sheet_views.get(gid)
        if view is None:
            view = SheetView(self.session, gid)
            view.accumulate = lambda: self.ctx.accumulate  # spec/ui 29 §2
            view.show_limits = self.sheet_limits_action.isChecked
            self.sheet_views[gid] = view
            self.tabs.addTab(view, view.title)
        if self.split:
            self.set_view("plan")
        self.tabs.setCurrentWidget(view)
        return view

    def open_master(self, gid: str) -> MasterEditor | None:
        """Abre a folha mestra numa aba de edição (spec/ui 26 §4)."""
        if self.session.doc.find(gid) is None:
            return None
        view = self.master_views.get(gid)
        if view is None:
            view = MasterEditor(self.session, gid)
            view.accumulate = lambda: self.ctx.accumulate  # spec/ui 29 §2
            self.master_views[gid] = view
            self.tabs.addTab(view, view.title)
        if self.split:
            self.set_view("plan")
        self.tabs.setCurrentWidget(view)
        return view

    def open_table(self, gid: str) -> TableView | None:
        """Abre a tabela numa aba (spec/ui 17 §5)."""
        if self.session.doc.find(gid) is None:
            return None
        view = self.table_views.get(gid)
        if view is None:
            view = TableView(self.session, gid)
            view.show_in_plan = self.show_in_plan
            self.table_views[gid] = view
            self.tabs.addTab(view, view.title)
        if self.split:
            self.set_view("plan")
        self.tabs.setCurrentWidget(view)
        return view

    def _add_fixed_tabs(self) -> None:
        """Planta e 3D, sempre presentes: as únicas abas sem o botão de fechar."""
        bar = self.tabs.tabBar()
        for widget, title in ((self.plan, "Planta"), (self.view3d, "3D")):
            index = self.tabs.insertTab(0 if widget is self.plan else 1, widget, title)
            for side in (QTabBar.LeftSide, QTabBar.RightSide):
                bar.setTabButton(index, side, None)

    def _tab_views(self) -> tuple[dict, ...]:
        return self.section_views, self.sheet_views, self.master_views, self.table_views

    def closable(self, widget) -> bool:
        return any(widget in views.values() for views in self._tab_views())

    def close_tab(self, widget=None) -> bool:
        """Fecha a aba (corte, fachada, prancha, folha mestra ou tabela; spec/ui 32 §3).
        O que foi editado nela já está no projeto: fechar não perde nada."""
        if widget is None:
            widget = self.tabs.currentWidget() if not self.split else None
        for views in self._tab_views():
            gid = next((g for g, v in views.items() if v is widget), None)
            if gid is None:
                continue
            if views is self.section_views and self.active_saved_view is not None:
                entity = self.session.doc.find(self.active_saved_view)
                if entity is not None and saved_views.read_state(entity).get("view") == gid:
                    self.close_saved_view()
            del views[gid]
            self.tabs.removeTab(self.tabs.indexOf(widget))
            widget.deleteLater()
            return True
        if widget is self.plan or widget is self.view3d:
            self.session.message("a planta e o 3D ficam sempre abertos", "recusa")
        return False

    def close_tabs(self, keep=None) -> None:
        """Fecha todas as abas que fecham, menos ``keep``."""
        for views in self._tab_views():
            for widget in list(views.values()):
                if widget is not keep:
                    self.close_tab(widget)

    def _tab_changed(self, _index: int = -1) -> None:
        """Com a aba de uma tabela à frente, o painel de propriedades é o dela (§5)."""
        view = self.tabs.currentWidget()
        gid = view.table_gid if isinstance(view, TableView) else None
        if getattr(self.properties, "active_table", None) != gid:
            self.properties.active_table = gid
            self.properties.refresh()

    def export_table(self, kind: str | None = None, path: str | None = None) -> str | None:
        """Arquivo > Exportar tabela…: a tabela da aba à frente, em CSV ou XLSX (§5)."""
        view = self.tabs.currentWidget()
        if not isinstance(view, TableView):
            self.session.message("abra uma tabela (painel do projeto) para exportar",
                                 "recusa")
            return None
        if kind is None:
            if path is not None:
                kind = "xlsx" if path.lower().endswith(".xlsx") else "csv"
            else:
                name, _ = QFileDialog.getSaveFileName(
                    self, "Exportar tabela", f"{view.title}.xlsx",
                    "Planilha XLSX (*.xlsx);;CSV (*.csv)")
                if not name:
                    return None
                path = name
                kind = "csv" if name.lower().endswith(".csv") else "xlsx"
        return view.export(kind, path)

    def export_pdf(self, path: str | None = None) -> int:
        """Arquivo > Exportar PDF…: todas as pranchas, uma por página (spec/ui 15 §5)."""
        found = sheets_.all_sheets(self.session.doc)
        if not found:
            self.session.message("não há pranchas: crie uma no painel do projeto", "recusa")
            return 0
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "", "PDF (*.pdf)")
            if not path:
                return 0
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
        pages = export_pdf(path, self.session.doc, found)
        self.session.message(f"PDF exportado ({pages} página(s)): {path}")
        return pages

    def edit_project_info(self) -> None:
        """Dados do projeto para o carimbo (spec/ui 15 §4)."""
        info = sheets_.read_project(self.session.doc)
        dialog = QDialog(self)
        dialog.setWindowTitle("Dados do projeto")
        form = QFormLayout(dialog)
        fields = {}
        for key, label in (("name", "Nome do projeto"), ("address", "Endereço da obra"),
                           ("owner", "Proprietário"), ("responsible", "Responsável técnico"),
                           ("registration", "Registro (CAU ou CREA)")):
            fields[key] = QLineEdit(info.get(key) or "")
            form.addRow(label, fields[key])
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            doc = self.session.doc
            values = {k: f.text().strip() for k, f in fields.items()}
            self.session.run(lambda: sheets_.edit_project(doc, **values))

    def _refresh_section_views(self, reset: bool = False) -> None:
        for gid, view in list(self.master_views.items()):
            if reset or self.session.doc.find(gid) is None:
                self.tabs.removeTab(self.tabs.indexOf(view))
                view.deleteLater()
                del self.master_views[gid]
                continue
            view.invalidate()
            self.tabs.setTabText(self.tabs.indexOf(view), view.title)
        for gid, view in list(self.table_views.items()):
            if reset or self.session.doc.find(gid) is None:
                self.tabs.removeTab(self.tabs.indexOf(view))
                view.deleteLater()
                del self.table_views[gid]
                continue
            view.invalidate()
            self.tabs.setTabText(self.tabs.indexOf(view), view.title)
        for gid, view in list(self.sheet_views.items()):
            if reset or self.session.doc.find(gid) is None:
                self.tabs.removeTab(self.tabs.indexOf(view))
                view.deleteLater()
                del self.sheet_views[gid]
                continue
            view.invalidate()
            self.tabs.setTabText(self.tabs.indexOf(view), view.title)
        for gid, view in list(self.section_views.items()):
            if reset or self.session.doc.find(gid) is None:
                self.tabs.removeTab(self.tabs.indexOf(view))
                view.deleteLater()
                del self.section_views[gid]
                continue
            view.invalidate()
            self.tabs.setTabText(self.tabs.indexOf(view), view.title)

    def ask_text(self, current: str = "") -> str | None:
        """Texto da ferramenta Texto e da edição por clique duplo (spec/ui 13 §6)."""
        text, ok = QInputDialog.getMultiLineText(self, "Texto", "Texto:", current)
        return text if ok else None

    def _hook_tools(self) -> None:
        self.toolbox.tools["text"].ask = self.ask_text
        self.toolbox.tools["label"].ask = self.ask_text
        self.toolbox.tools["select"].ask_text = self.ask_text
        self.toolbox.tools["object"].on_missing_type = self.show_library

    # --- objetos paramétricos (objeto-parametrico.md §4) --------------------------------------

    def show_library(self) -> None:
        """Abre o painel Biblioteca de objetos (Ctrl+Shift+B)."""
        self.library.refresh()
        self.library_dock.show()
        self.library_dock.raise_()

    def edit_library_folders(self) -> None:
        dialog = FoldersDialog(self)
        if dialog.exec() == QDialog.Accepted:
            set_user_folders(dialog.folders())
            self.library.index = make_index()
            self.library.refresh()

    def use_object_type(self, gid: str) -> None:
        """Ferramenta Objeto com o tipo escolhido (clique duplo na biblioteca)."""
        tool = self.toolbox.tools["object"]
        tool.set_type(gid)
        self.activate_tool("object")

    def drop_object(self, key: str, x: float, y: float) -> None:
        """Objeto arrastado da biblioteca e solto na planta: carrega o tipo e insere no
        ponto (com a atração de sempre); a ferramenta Objeto fica ativa com ele."""
        gid = self.library.load_key(key)
        if gid is None:
            return
        self.use_object_type(gid)
        self.toolbox.tools["object"].press((x, y), Mods())

    def _object_action(self, key: str) -> None:
        """Ações da mini-barra sobre objetos paramétricos (§5.1)."""
        from PySide6.QtGui import QCursor

        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import elements as objects

        session, doc = self.session, self.session.doc
        found = [doc.get(g) for g in sorted(session.selection)
                 if objects.is_object(doc.find(g))]
        if not found:
            return
        types = {objects.read_state(doc, e)["type"] for e in found}
        if key == "edit_object_type" and len(types) == 1:
            self.edit_object_type(next(iter(types)))
        elif key == "detach" and len(found) == 1:
            session.run(lambda: oc.detach(doc, found[0]))
        elif key == "swap_type":
            menu = QMenu(self)
            common = None
            for e in found:
                ids = [t.GlobalId for t in oc.compatible_types(doc, e)]
                common = ids if common is None else [g for g in common if g in ids]
            for gid in common or []:
                t = doc.get(gid)
                action = menu.addAction(t.Name)
                action.setCheckable(True)
                action.setChecked(types == {gid})
                action.triggered.connect(lambda _=False, g=gid: session.run(
                    lambda: oc.change_type(doc, [e.GlobalId for e in found], g)))
            menu.addSeparator()
            menu.addAction("Mais na biblioteca…", self.show_library)
            menu.exec(QCursor.pos())

    def save_object_to_library(self, object_id: str, path: str | None = None) -> str | None:
        """Gravar na biblioteca (§4.3): arquivo novo ou existente numa pasta do usuário."""
        from brasbim.core.objects import library
        from brasbim.core.objects import types as ot
        from brasbim.ui.library_panel import user_folders

        doc = self.session.doc
        found = ot.types_of_definition(doc, object_id)
        if not found:
            return None
        if path is None:
            folders = user_folders()
            if not folders:
                self.session.message("acrescente uma pasta sua em Projeto > Pastas da "
                                     "biblioteca… para gravar objetos", "recusa")
                self.edit_library_folders()
                folders = user_folders()
                if not folders:
                    return None
            name = ot.definition_of(found[0])["name"]
            path, _ = QFileDialog.getSaveFileName(self, "Gravar na biblioteca",
                                                  str(Path(folders[0]) / f"{name}.ifc"),
                                                  "IFC (*.ifc)")
            if not path:
                return None
        try:
            names = library.save(doc, path, object_id)
        except (OpError, OSError) as e:
            self.session.message(str(e), "recusa")
            return None
        self.session.message(f"Gravado na biblioteca: {', '.join(names)} em {path}")
        self.library.refresh()
        return path

    def edit_object(self, object_id: str):
        """Editor do objeto (§5.3) aberto na definição do projeto."""
        from brasbim.ui.object_editor import ObjectEditor

        self.toolbox.active.cancel()
        try:
            editor = ObjectEditor(self.session, object_id, parent=self)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return None
        editor.exec()
        self._after_object_edit()
        return editor

    def new_object(self, base_id: str | None = None):
        """Novo objeto, em branco ou a partir de uma cópia da definição ``base_id``."""
        from brasbim.core.objects import types as ot
        from brasbim.ui.object_editor import ObjectEditor

        self.toolbox.active.cancel()
        base = None
        if base_id:
            found = ot.types_of_definition(self.session.doc, base_id)
            base = ot.read(found[0])["definition"] if found else None
        editor = ObjectEditor(self.session, None, base, parent=self)
        editor.exec()
        self._after_object_edit()
        return editor

    def _after_object_edit(self) -> None:
        self.options_bar.refresh()
        self.properties.refresh()
        self.project.refresh()
        self.plan.update()

    def edit_object_type(self, gid: str) -> None:
        """Editar tipo (§5.4): nome, código e parâmetros de tipo."""
        from brasbim.ui.object_dialogs import TypeDialog

        self.toolbox.active.cancel()
        TypeDialog(self.session, gid, self).exec()
        self.options_bar.refresh()
        self.properties.refresh()

    def object_values_dialog(self, tool, params) -> None:
        """Outros parâmetros de ocorrência do próximo objeto (barra Opções, *Mais*)."""
        from brasbim.ui import object_widgets as ow

        state = tool.type_state()
        if state is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Parâmetros do próximo objeto")
        form = QFormLayout(dialog)
        values = {**state["defaults"], **tool.values}
        for p in params:
            form.addRow(ow.label(p), ow.param_widget(
                p, values.get(p["name"], p["value"]),
                lambda v, n=p["name"]: tool.values.__setitem__(n, v), self.session.doc))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        form.addRow(buttons)
        dialog.exec()

    def _refresh_title(self) -> None:
        name = Path(self.session.path).name if self.session.path else "Projeto sem nome"
        if self.session.shared and self.session.server is None:
            name = f"{self.session.collab.project} (compartilhado)"
        self.setWindowTitle(f"{name}{'*' if self.session.modified else ''} — BrasBim")

    # --- projeto compartilhado (spec/ui 33) ----------------------------------------------

    def _refresh_team(self) -> None:
        shared = self.session.shared
        for action in (*self.team_actions, self.leave_action):
            action.setEnabled(shared)
        if shared:
            n = len(self.session.collab.users)
            self.team_label.setText(f"Compartilhado · {n} pessoa{'s' if n != 1 else ''}")
        self.team_label.setVisible(shared)
        self._refresh_title()

    def set_show_reservations(self, value: bool) -> None:
        self.reservations_action.setChecked(bool(value))
        self.plan.show_reservations = bool(value)
        self.plan.update()

    def _team_name(self, title: str) -> str | None:
        settings = _settings()
        name, ok = QInputDialog.getText(self, title, "Seu nome (aparece para os colegas):",
                                        text=str(settings.value("equipe_nome")
                                                 or self.session.default_name()))
        if not ok or not name.strip():
            return None
        settings.setValue("equipe_nome", name.strip())
        return name.strip()

    def share_project(self, name: str | None = None, **options) -> bool:
        """Equipe > Compartilhar este projeto na rede… (§4). ``options``: porta e
        descoberta (testes)."""
        from brasbim.core.collab.protocol import local_addresses

        name = name or self._team_name("Compartilhar na rede")
        if name is None:
            return False
        try:
            server = self.session.share(name, **options)
        except OSError as e:
            self.session.message(f"não foi possível compartilhar: {e}", "recusa")
            return False
        self.team_dock.show()
        ips = ", ".join(f"{ip}:{server.port}" for ip in local_addresses()) or "—"
        self._team_info = (f"O projeto está compartilhado.\n\nNos outros computadores: "
                           f"Equipe > Entrar num projeto da rede…\nEle aparece na lista; "
                           f"se não aparecer, digite o endereço:\n\n"
                           f"    {server.host}:{server.port}\n    {ips}\n\n"
                           "Se o Windows perguntar, permita o acesso em Redes privadas.")
        if not self.quiet_dialogs:
            QMessageBox.information(self, "Projeto compartilhado", self._team_info)
        return True

    def join_project(self, choose=None) -> bool:
        """Equipe > Entrar num projeto da rede… (§4). ``choose``: (host, porta, nome) sem
        diálogo (testes)."""
        if choose is None:
            settings = _settings()
            dialog = JoinDialog(str(settings.value("equipe_nome")
                                    or self.session.default_name()), self)
            dialog.show()
            dialog.search()
            if dialog.exec() != QDialog.Accepted:
                return False
            choose = dialog.result_value()
            settings.setValue("equipe_nome", choose[2])
        if not self._ask_save():
            return False
        host, port, name = choose
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.session.join(host, port, name)
        except OSError as e:
            self.session.message(f"não foi possível entrar em {host}:{port}: {e}", "recusa")
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.team_dock.show()
        return True

    def leave_shared(self) -> None:
        if self.session.server is not None and len(self.session.collab.users) > 1 \
                and not self.quiet_dialogs:
            answer = QMessageBox.question(
                self, "Sair do projeto compartilhado",
                "Você compartilha este projeto. Ao sair, os colegas são desconectados e "
                "ficam com uma cópia. Sair?")
            if answer != QMessageBox.Yes:
                return
        self.session.leave()

    def copy_messages(self) -> str:
        """Copia as mensagens escolhidas (ou a última) para a área de transferência, sem a
        hora: uma medida vai direto para outro programa (spec/ui 30 §7)."""
        items = self.messages.selectedItems() or [self.messages.item(self.messages.count() - 1)]
        text = "\n".join(i.data(Qt.UserRole) for i in items if i is not None)
        if text:
            QApplication.clipboard().setText(text)
        return text

    def _show_messages(self) -> None:
        self.messages.clear()
        for m in self.session.messages[-60:]:
            item = QListWidgetItem(f"{m['time']}  {m['text']}")
            item.setToolTip(m["level"])
            item.setData(Qt.UserRole, m["text"])
            item.setForeground(QColor(_LEVEL_COLOR.get(m["level"], theme.INK)))
            self.messages.addItem(item)
        self.messages.scrollToBottom()
        last = self.session.messages[-1] if self.session.messages else None
        if last and last["level"] == "recusa":
            self.statusBar().showMessage(last["text"], 6000)

    def _show_cursor(self, x: float, y: float) -> None:
        self.coords.setText(f"x {fmt(x)}   y {fmt(y)}")

    # --- ações -------------------------------------------------------------------------

    # --- pacote de precisão (spec/ui 23) -----------------------------------------------

    def _snap_menu(self, menu) -> None:
        """Exibir > Atração (§2.3): um item por tipo e desligar tudo; preferência do
        usuário, não do projeto."""
        settings = _settings()
        saved = settings.value("atracao/tipos", None)
        if saved is not None:
            kinds = saved if isinstance(saved, list) else [saved] if saved else []
            self.ctx.snap_kinds = {k for k in kinds if k in snap.KINDS}
        self.ctx.snap_off = settings.value("atracao/desligada", "false") in (True, "true")
        self.snap_actions = {}
        for kind in snap.KINDS:
            text = snap.KIND_LABEL[kind].capitalize()
            action = self._action(menu, text, lambda v, k=kind: self._set_snap_kind(k, v))
            action.setCheckable(True)
            action.setChecked(kind in self.ctx.snap_kinds)
            self.snap_actions[kind] = action
        menu.addSeparator()
        # Linhas-guia (spec/ui 37 §4): preferência própria, ligada por padrão.
        self.ctx.guides_on = settings.value("atracao/guias", "true") in (True, "true")
        self.guides_action = self._action(menu, "Linhas-guia", self._set_guides)
        self.guides_action.setCheckable(True)
        self.guides_action.setChecked(self.ctx.guides_on)
        self.snap_off_action = self._action(menu, "Desligar toda a atração", self._set_snap_off)
        self.snap_off_action.setCheckable(True)
        self.snap_off_action.setChecked(self.ctx.snap_off)

    def _set_snap_kind(self, kind: str, on: bool) -> None:
        (self.ctx.snap_kinds.add if on else self.ctx.snap_kinds.discard)(kind)
        _settings().setValue("atracao/tipos", sorted(self.ctx.snap_kinds))

    def _set_guides(self, on: bool) -> None:
        self.ctx.guides_on = bool(on)
        _settings().setValue("atracao/guias", "true" if on else "false")

    def _set_snap_off(self, on: bool) -> None:
        self.ctx.snap_off = bool(on)
        _settings().setValue("atracao/desligada", "true" if on else "false")

    def select_similar(self, criterion: str) -> None:
        """Selecionar semelhantes no pavimento ativo (§7)."""
        session = self.session
        if not session.selection or session.storey is None:
            session.message("selecione um elemento antes", "recusa")
            return
        found = select_similar.similar(session.doc, session.storey, session.selection,
                                       criterion)
        session.select(found)
        session.message(f"{len(found)} selecionado(s)")

    def rotate_quarter(self, sign: int) -> None:
        """Ctrl+R / Ctrl+Shift+R: gira a seleção 90° em torno do centro da caixa (§8)."""
        import math

        from brasbim.core import transform

        session = self.session
        gids = sorted(session.selection)
        if not gids:
            session.message("selecione os elementos antes", "recusa")
            return
        pts = [q for s in self.ctx.plan.shapes if s.owner in session.selection
               for q in s.points]
        if not pts:
            session.message("a seleção não aparece na planta", "recusa")
            return
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        doc = session.doc
        session.run(lambda: transform.rotate_elements(doc, gids, center, sign * math.pi / 2))
        self.plan.update()
        self.view3d.update()

    def tool_commands(self):
        """Ferramentas para a paleta de comandos (§9)."""
        from brasbim.ui import command_palette, toolbars

        return command_palette.tool_commands([
            ("Ferramentas", toolbars.CREATE_TOOLS + toolbars.WALL_FORMS),
            ("Vistas", toolbars.VIEW_TOOLS), ("Documentação", toolbars.DOC_TOOLS),
            ("Edição", toolbars.EDIT_TOOLS)])

    def open_palette(self) -> None:
        if getattr(self, "palette_widget", None) is None:
            from brasbim.ui.command_palette import CommandPalette

            self.palette_widget = CommandPalette(self)
        self.palette_widget.open()

    # --- linha de comando (spec/ui 24) ------------------------------------------------------

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.command_line.set_prompt(text or self.toolbox.active.label)

    def _options_changed(self) -> None:
        self.options_bar.refresh()
        self.command_line.refresh_tool()

    def set_command_line_visible(self, visible: bool) -> None:
        """Exibir > Barras > Linha de comando; escondida, a dica volta à barra de estado."""
        self.command_line_action.setChecked(bool(visible))
        self.command_line.setVisible(bool(visible))
        self.hint.setVisible(not visible)

    def edit_aliases(self) -> bool:
        from brasbim.ui import command_palette

        commands, _ = command_palette.collect(self)
        dialog = AliasesDialog(self, commands, self.command_line.aliases)
        if dialog.exec() != AliasesDialog.Accepted:
            return False
        self.command_line.aliases = dialog.values()
        save_aliases(_settings(), self.command_line.aliases)
        return True

    def activate_tool(self, name: str) -> None:
        tool = self.toolbox.activate(name)
        self.tools_bar.mark(name)
        self.options_bar.show_for(tool)
        self._set_hint(tool.hint())
        self.command_line.refresh_tool()
        self.properties.refresh()
        self.plan.update()
        self.view3d.update()
        (self.ctx.input_view or self.plan).setFocus()

    def remove_selection_area(self) -> None:
        """Editar > Remover área de seleção (spec/ui 38 §2)."""
        if self.ctx.area is not None:
            self.ctx.area = None
            self._set_hint(self.toolbox.active.hint())
            self.plan.update()

    def undo(self) -> None:
        self.toolbox.active.cancel()
        self.session.undo()

    def redo(self) -> None:
        self.toolbox.active.cancel()
        self.session.redo()

    def delete_selection(self) -> None:
        view = self.tabs.currentWidget() if not self.split else None
        if isinstance(view, SheetView):  # Delete na prancha tira os desenhos (ui/29 §2)
            view.delete_selected()
            return
        if isinstance(view, MasterEditor):
            view.delete_selected()
            return
        if not self.session.selection:
            return
        try:
            tx, cascade = delete_transaction(self.session)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        if cascade and not self.confirm(
                f"A exclusão leva junto {cascade} das paredes selecionadas. Continuar?"):
            return
        self.session.run(tx)

    def confirm(self, text: str) -> bool:
        answer = QMessageBox.question(self, "Confirmar", text)
        return answer == QMessageBox.Yes

    def step_storey(self, step: int) -> None:
        """Page Up / Page Down: o pavimento de cima ou de baixo fica ativo."""
        storeys = self.session.doc.storeys()
        current = self.session.storey
        if current is None or current not in storeys:
            return
        i = storeys.index(current) + step
        if 0 <= i < len(storeys):
            self.session.set_storey(storeys[i])
            self.session.message(f"Pavimento ativo: {storeys[i].Name}")

    def set_view(self, mode: str) -> None:
        if mode == "split":
            if not self.split:
                self.panes[0].hold(self.plan)
                self.panes[1].hold(self.view3d)
                self.tabs.hide()
                self.splitter.show()
                self.plan.show()  # a aba que não estava à frente sai das abas oculta
                self.view3d.show()
                half = max(self.splitter.width() // 2, 1)
                self.splitter.setSizes([half, half])
                self.split = True
            return
        if self.split:
            self._add_fixed_tabs()
            self.splitter.hide()
            self.tabs.show()
            self.split = False
        self.tabs.setCurrentWidget(self.plan if mode == "plan" else self.view3d)

    def standard_view(self, name: str) -> None:
        """Vista 3D padrão; com a planta à frente, passa para o 3D."""
        if not self.split:
            self.set_view("3d")
        self.view3d.standard_view(name)

    def toggle_maximized(self, pane) -> None:
        """Lado a lado: a vista ocupa tudo; de novo, as duas metades."""
        total = max(sum(self.splitter.sizes()), 2)
        if min(self.splitter.sizes()) == 0:
            self.splitter.setSizes([total // 2, total - total // 2])
        else:
            self.splitter.setSizes([total, 0] if pane is self.panes[0] else [0, total])

    def edit_type(self, ifc_class: str, gid: str | None = None) -> None:
        """Janela de tipos (parede, porta, janela, pilar, viga, laje), aberta no ``gid``."""
        dialog_class = {"IfcWallType": WallTypesDialog, "IfcDoorType": DoorTypesDialog,
                        "IfcWindowType": WindowTypesDialog, "IfcColumnType": ColumnTypesDialog,
                        "IfcBeamType": BeamTypesDialog, "IfcSlabType": SlabTypesDialog}[ifc_class]
        self.toolbox.active.cancel()
        dialog_class(self.session, self, select=gid).exec()
        self.toolbox.check_types()
        self.options_bar.refresh()
        self.properties.refresh()
        self.plan.update()

    def edit_materials(self, name: str | None = None) -> None:
        """Projeto > Materiais… (spec/ui 06 §4.2), aberto no material ``name``."""
        self.toolbox.active.cancel()
        MaterialsDialog(self.session, self, select=name).exec()
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
            self._set_hint(tool.hint())
            return
        if key == "select_similar":
            menu = QMenu(self)
            for criterion, text in select_similar.CRITERIA:
                menu.addAction(text, lambda c=criterion: self.select_similar(c))
            from PySide6.QtGui import QCursor

            menu.exec(QCursor.pos())
            return
        if key == "situation":  # spec/ui 31 §2
            menu = QMenu(self)
            current = {intervention.situation_of(doc, doc.find(g))
                       for g in session.selection if doc.find(g) is not None}
            for code, text, _ in intervention.SITUATIONS:
                action = menu.addAction(text, lambda c=code: self.set_selection_situation(c))
                action.setCheckable(True)
                action.setChecked(current == {code})
            from PySide6.QtGui import QCursor

            menu.exec(QCursor.pos())
            return
        if key in ("swap_type", "edit_object_type", "detach"):
            self._object_action(key)
            return
        if key == "auto_dimension":
            wall = next(iter(session.selection), None)
            session.run(lambda: ac.auto_dimension_wall(doc, wall))
            return
        if key in ("pick_curves", "curve_level"):  # escada-terreno.md §4.4
            name = "terrain_pick" if key == "pick_curves" else "terrain_level"
            self.toolbox.tools[name].terrain = next(iter(session.selection), None)
            self.activate_tool(name)
            return
        if key == "slab_opening":
            tool = self.toolbox.tools["slab_opening"]
            tool.slab = next(iter(session.selection), None)
            self.activate_tool("slab_opening")
            return
        if not session.selection:
            session.message("selecione os elementos antes", "recusa")
            return
        if key in ("move", "copy", "rotate", "mirror"):
            self.activate_tool(key)
            return
        if key in ("join", "unjoin", "swap"):
            a, b = sorted(session.selection)
            command = {"join": cmd.join_walls, "unjoin": cmd.unjoin_walls,
                       "swap": cmd.swap_continuous}[key]
            session.run(lambda: command(doc, a, b))
            return
        door_list = [doc.get(g) for g in sorted(session.selection)]
        flip = fc.flip_opening if key == "flip_opening" else fc.flip_hinges
        session.run(lambda: fc.flip_each(doc, door_list, flip))

    # --- mostrar a seleção na outra vista (spec/ui 07 §4) ------------------------------------

    def context_actions(self, view, gid) -> list[tuple[str, object]]:
        """Itens do menu do botão direito na vista, sobre ``gid`` (ou no vazio)."""
        if not gid:
            if view is self.view3d:
                return [("Enquadrar tudo", view.fit),
                        ("Vista de topo", lambda: view.standard_view("top")),
                        ("Isométrica", lambda: view.standard_view("iso_sw"))]
            return [("Enquadrar tudo", view.fit)]
        if view is self.view3d:
            actions = [("Mostrar na planta", lambda: self.show_in_plan(gid)),
                       ("Enquadrar a seleção", view.frame_selection)]
        else:
            actions = [("Mostrar no 3D", self.show_in_3d),
                       ("Enquadrar a seleção", view.frame_selection)]
        return (actions + self._object_context(gid) + self._layer_actions(gid)
                + self._team_context(gid))

    def _team_context(self, gid) -> list:
        """Pedir liberação do que é de outra pessoa (spec/ui 33 §3)."""
        collab = self.session.collab if self.session.shared else None
        owner = collab.owner(gid) if collab is not None else None
        if owner is None or owner["id"] == collab.me:
            return []
        ids = self.session.selection if gid in self.session.selection else {gid}
        return [(f"Pedir liberação a {owner['name']}",
                 lambda: self.session.request_release(ids))]

    def _object_context(self, gid) -> list[tuple[str, object]]:
        """Objeto paramétrico sob o cursor: editar o tipo, soltar ou prender à parede."""
        from brasbim.core.objects import commands as oc
        from brasbim.core.objects import elements as objects
        from brasbim.core.objects import hosting
        from brasbim.core.objects import types as ot

        doc = self.session.doc
        element = objects.parent_of(doc.find(gid)) if doc.find(gid) else None
        if not objects.is_object(element):
            return []
        state = objects.read_state(doc, element)
        out = [("Editar tipo…", lambda: self.edit_object_type(state["type"]))]
        if self.properties.edit_object is not None:
            object_id = ot.read(doc.get(state["type"]))["definition"]["object_id"]
            out.append(("Editar objeto…", lambda: self.properties.edit_object(object_id)))
        if state["host"] is not None:
            out.append(("Soltar da parede", lambda: self.session.run(
                lambda: oc.detach(doc, element))))
        elif ot.read(doc.get(state["type"]))["definition"]["hosting"] == "wall":
            from brasbim.core import snap

            walls = [w for w in self.ctx.walls if w.straight]
            hit = snap.wall_at(walls, tuple(state["point"]), 1.0)
            if hit is not None:
                built = objects.resolve(doc, state)[2]
                box = built.box or (0, 0, 0, 0, 0, 0)
                host = hosting.at_point(doc, doc.get(hit.wall.gid), tuple(state["point"]),
                                        box[1] - box[0])
                if host is not None:
                    out.append(("Prender à parede", lambda: self.session.run(
                        lambda: oc.attach(doc, element, host["wall"], host["side"],
                                          host["distance"]))))
        return out

    def _layer_actions(self, gid) -> list[tuple[str, object]]:
        """Camada do elemento sob o cursor (spec/ui 18 §5): ocultar, bloquear, isolar."""
        doc = self.session.doc
        element = doc.find(gid)
        if display_layers.read_config(doc) is None or not display_layers.layerable(
                display_layers.owner(element)):
            return []
        layer_id = display_layers.layer_of(doc, element) or display_layers.NONE
        key = ("layer", layer_id)
        return [("Ocultar a camada deste elemento",
                 lambda: self.layers.set_visible(key, False)),
                ("Bloquear a camada deste elemento",
                 lambda: self.layers.set_locked(key, True)),
                ("Mostrar só a camada deste elemento", lambda: self.layers.isolate(key))]

    def show_context_menu(self, view, gid, pos) -> None:
        menu = QMenu(self)
        for text, slot in self.context_actions(view, gid):
            menu.addAction(text, slot)
        menu.exec(pos)

    def _bring(self, view) -> None:
        """Põe a vista à frente (em abas); lado a lado, nada muda."""
        if not self.split:
            self.tabs.setCurrentWidget(view)
        self.ctx.input_view = view
        view.setFocus()

    def show_in_plan(self, gid: str | None = None) -> bool:
        """Pavimento do elemento ativo, planta à frente e seleção enquadrada."""
        session = self.session
        if gid is None:
            gid = next(iter(sorted(session.selection)), None)
        element = session.doc.find(gid) if gid else None
        if element is None:
            return False
        storey = storey_of(element)
        if storey is not None and storey.GlobalId != session.storey_id:
            kept = set(session.selection)
            session.set_storey(storey)  # limpa a seleção: aqui ela continua
            session.select(kept)
        self._bring(self.plan)
        return self.plan.frame_selection()

    def show_in_3d(self) -> bool:
        """3D à frente, com a órbita na seleção e a mesma direção da câmera."""
        if not self.session.selection:
            return False
        self._bring(self.view3d)
        return self.view3d.frame_selection()

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
        """Arquivo > Abrir…: projeto IFC; DWG e DXF vão para Importar desenho no projeto
        aberto (spec/ui 22 §8)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir", "", "Projetos e desenhos (*.ifc *.dwg *.dxf);;IFC (*.ifc);;"
            "Desenhos (*.dwg *.dxf)")
        if path and Path(path).suffix.lower() in (".dwg", ".dxf"):
            self.import_drawing(path)
            return
        if path and self._ask_save():
            try:
                self.session.open(path)
            except (OSError, RuntimeError, OpError) as e:
                self.session.message(f"não foi possível abrir {path}: {e}", "recusa")

    # --- importar desenho (spec/ui 22) ---------------------------------------------------

    def import_drawing(self, path: str | None = None, choose=None) -> bool:
        """Arquivo > Importar desenho: lê o DXF (ou converte o DWG), mostra as camadas e
        importa no pavimento ativo. ``choose``: substitui o diálogo (testes)."""
        from brasbim.core.imports import dxf
        from brasbim.ui.import_dialog import ImportDialog

        storey = self.session.storey
        if storey is None:
            self.session.message("não há pavimento ativo", "recusa")
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Importar desenho", "", "Desenhos (*.dxf *.dwg);;DXF (*.dxf);;DWG (*.dwg)")
            if not path:
                return False
        drawing = self._read_drawing(path)
        if drawing is None:
            return False
        if not drawing.layers:
            self.session.message(f"{drawing.source} não tem linhas, textos nem pontos",
                                 "recusa")
            return False
        if choose is None:
            dialog = ImportDialog(drawing, storey.Name or "", self)
            if dialog.exec() != QDialog.Accepted:
                return False
            choice = dialog.choice()
        else:
            choice = choose(drawing)
        layers, unit, offset = choice
        doc = self.session.doc
        if not self.session.run(lambda: dxf.import_drawing(doc, storey, drawing, unit, offset,
                                                           layers)):
            return False
        n = sum(len(drawing.layers[name].lines) for name in layers)
        self.session.message(f"Importado {drawing.source}: {len(layers)} camada"
                             f"{'' if len(layers) == 1 else 's'}, {n} linhas")
        self.fit_all()
        return True

    def _read_drawing(self, path: str):
        """Lê o desenho; sem conversor de DWG, oferece baixar o LibreDWG e tenta de novo
        (spec/ui 22 §8). Erros vão para Mensagens e para um aviso na tela."""
        from brasbim.core.imports import dxf, libredwg

        for attempt in (1, 2):
            self.statusBar().showMessage(f"Lendo {Path(path).name}…")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                return dxf.read(path)
            except dxf.MissingConverter as e:
                error = e
            except OpError as e:
                self._drawing_error(str(e))
                return None
            finally:
                QApplication.restoreOverrideCursor()
                self.statusBar().clearMessage()
            if attempt == 2 or not libredwg.supported() or not self.confirm_download():
                self._drawing_error(str(error))
                return None
            self.statusBar().showMessage("Baixando o conversor de DWG (LibreDWG)…")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                libredwg.install()
            except RuntimeError as e:
                self._drawing_error(str(e))
                return None
            finally:
                QApplication.restoreOverrideCursor()
                self.statusBar().clearMessage()
            self.session.message(f"Conversor de DWG LibreDWG {libredwg.VERSION} baixado em "
                                 f"{libredwg.user_folder()}")
        return None

    def confirm_download(self) -> bool:
        """Pergunta antes de baixar o conversor de DWG (testes trocam este método)."""
        from brasbim.core.imports import libredwg

        answer = QMessageBox.question(
            self, "Conversor de DWG",
            "Para abrir DWG, o BrasBim usa o conversor livre GNU LibreDWG (licença GPL). "
            f"Ele ainda não está neste computador.\n\nBaixar agora ({libredwg.SIZE_MB} MB, "
            "uma vez só)? Fica na pasta do BrasBim; nada é instalado no sistema.")
        return answer == QMessageBox.Yes

    def _drawing_error(self, text: str) -> None:
        self.session.message(text, "recusa")
        if self.isVisible() and not self.quiet_dialogs:
            QMessageBox.warning(self, "Importar desenho", text[:1].upper() + text[1:])

    # --- cópia de segurança e recuperação (spec/ui 21) -----------------------------------

    def set_backup_minutes(self, minutes: int) -> None:
        self.backup_minutes = minutes
        self.backup_actions[minutes].setChecked(True)
        _settings().setValue("salvamento_automatico_min", minutes)

    def backup_tick(self, now: float | None = None) -> bool:
        """Renova o sinal de vida e, passado o intervalo, grava a cópia (§2)."""
        self.session.heartbeat()
        now = time.monotonic() if now is None else now
        if not self.backup_minutes or now - self._last_backup < self.backup_minutes * 60 - 1:
            return False
        self._last_backup = now
        return self.session.backup()

    def _ask_recovery(self, text: str) -> str:
        """"recover", "discard" ou "later" (separado para os testes)."""
        box = QMessageBox(QMessageBox.Warning, "Recuperar projeto", text, parent=self)
        recover = box.addButton("Recuperar", QMessageBox.AcceptRole)
        discard = box.addButton("Descartar", QMessageBox.DestructiveRole)
        box.addButton("Depois", QMessageBox.RejectRole)
        box.setDefaultButton(recover)
        box.exec()
        clicked = box.clickedButton()
        return "recover" if clicked is recover else "discard" if clicked is discard else "later"

    def offer_recovery(self) -> None:
        """Na abertura: oferece a cópia órfã mais recente (§4)."""
        found = self.session.orphan_backups()
        if not found:
            return
        entry = found[0]
        name = Path(entry["file"]).name if entry["file"] else "um projeto sem nome"
        answer = self._ask_recovery(
            f"O BrasBim fechou sem salvar {name} (cópia de "
            f"{entry['saved']:%d/%m às %H:%M}). Recuperar?")
        if answer == "recover":
            if not self._ask_save():
                return
            try:
                self.session.recover(entry)
            except (OSError, RuntimeError, OpError) as e:
                self.session.message(f"não foi possível recuperar a cópia: {e}", "recusa")
        elif answer == "discard":
            self.session.discard_orphan(entry)

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
        settings.setValue("etiquetas_porta", self.tags_action.isChecked())
        settings.setValue("medidas_etiqueta", self.tag_size_action.isChecked())
        settings.setValue("etiquetas_estrutura", self.structure_tags_action.isChecked())
        settings.setValue("etiquetas_objetos", self.object_tags_action.isChecked())
        settings.setValue("numeros_ambientes", self.space_numbers_action.isChecked())
        settings.setValue("espessuras_linha", self.weights_action.isChecked())
        settings.setValue("simbolos_corte", self.view_symbols_action.isChecked())
        settings.setValue("detalhe_planta", self.ctx.detail)
        settings.setValue("acima_do_corte", self.ctx.show_above)
        settings.setValue(VISIBLE_KEY, self.command_line_action.isChecked())
        self.assistant.shutdown()
        self.session.close()
        event.accept()

    def _assistant_finished(self) -> None:
        """Enquadra a planta se o desenho do assistente saiu da vista."""
        bounds = self.ctx.plan.bounds()
        if bounds is None:
            return
        a = self.plan.to_screen((bounds[0], bounds[1]))
        b = self.plan.to_screen((bounds[2], bounds[3]))
        if not self.plan.rect().contains(a.toPoint()) or not self.plan.rect().contains(
                b.toPoint()):
            self.plan.fit()

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

