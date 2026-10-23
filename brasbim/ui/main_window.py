# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela principal (``spec/ui/01-janela-e-ferramentas.md`` §2, §6, §8, §9; barras e
mini-barra, ``spec/ui/03-barras-e-icones.md`` §2–§5)."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from brasbim.core import display_layers, select_similar, snap
from brasbim.core import storeys as storeys_
from brasbim.core.annotations import commands as ac
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError
from brasbim.core.drawings import sheets as sheets_
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import Transaction
from brasbim.core.walls import commands as cmd
from brasbim.ui import feedback, theme
from brasbim.ui.assistant import AssistantPanel
from brasbim.ui.layers_panel import LayersPanel
from brasbim.ui.library_panel import FoldersDialog, LibraryPanel, make_index, set_user_folders
from brasbim.ui.materials_dialog import MaterialsDialog
from brasbim.ui.paper import SheetView, export_pdf
from brasbim.ui.plan_view import PlanView
from brasbim.ui.project_panel import ProjectPanel
from brasbim.ui.properties import PropertiesPanel
from brasbim.ui.scene3d import Scene
from brasbim.ui.section_view import SectionView
from brasbim.ui.selection_bar import SelectionBar
from brasbim.ui.session import Session
from brasbim.ui.table_view import TableView
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


class MainWindow(QMainWindow):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.ctx = PlanContext(session)
        self.section_views: dict[str, SectionView] = {}  # abas de corte e fachada
        self.sheet_views: dict[str, SheetView] = {}  # abas de prancha (spec/ui 15)
        self.table_views: dict[str, TableView] = {}  # abas de tabela (spec/ui 17)
        self.toolbox = ToolBox(self.ctx)
        self.scene = Scene()
        self.scene.load(session.doc.ifc, session.doc)
        self.plan = PlanView(self.toolbox)
        self.view3d = View3D(self.scene, self.toolbox)
        self.ctx.input_view = self.plan
        self.split = False
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_status()
        session.listeners.append(self._on_session)
        for view in (self.plan, self.view3d):
            view.cursor_moved.connect(self._show_cursor)
            view.hint_changed.connect(self.hint.setText)
            view.tool_finished.connect(lambda: self.activate_tool("select"))
            view.tool_options_changed.connect(self.options_bar.refresh)
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
        self.project.open_sheet = self.open_sheet
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
        self.project.library_index = self.library.index
        self.library_dock = self._dock("Biblioteca de objetos", "biblioteca", self.library,
                                       Qt.RightDockWidgetArea)
        self.library_dock.setFloating(True)
        self.library_dock.resize(380, 560)
        self.library_dock.hide()
        self.project.library_index = self.library.index

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
        self._action(file_menu, "Exportar PDF…", self.export_pdf, "Ctrl+P")
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
        for key, text in (("offset", "Deslocar paralela"), ("trim", "Aparar/estender"),
                          ("fillet", "Concordar")):
            self._action(edit_menu, text, lambda _=False, k=key: self.activate_tool(k))
        edit_menu.addSeparator()
        self._action(edit_menu, "Paleta de comandos…", self.open_palette, "Ctrl+K")
        view_menu = bar.addMenu("E&xibir")
        self._action(view_menu, "Planta", lambda: self.set_view("plan"))
        self._action(view_menu, "3D", lambda: self.set_view("3d"))
        self._action(view_menu, "Lado a lado", lambda: self.set_view("split"))
        view_menu.addSeparator()
        self._action(view_menu, "Enquadrar tudo", self.fit_all)
        self.show_in_plan_action = self._action(view_menu, "Mostrar na planta",
                                                lambda: self.show_in_plan(), "Ctrl+Shift+P")
        self.show_in_3d_action = self._action(view_menu, "Mostrar no 3D", self.show_in_3d,
                                              "Ctrl+Shift+3")
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
        project_menu = bar.addMenu("&Projeto")
        self._action(project_menu, "Tipos de parede…", lambda: self.edit_type("IfcWallType"))
        self._action(project_menu, "Tipos de porta…", lambda: self.edit_type("IfcDoorType"))
        self._action(project_menu, "Tipos de janela…",
                     lambda: self.edit_type("IfcWindowType"))
        self._action(project_menu, "Tipos de pilar…", lambda: self.edit_type("IfcColumnType"))
        self._action(project_menu, "Tipos de viga…", lambda: self.edit_type("IfcBeamType"))
        self._action(project_menu, "Tipos de laje…", lambda: self.edit_type("IfcSlabType"))
        self._action(project_menu, "Materiais…", lambda: self.edit_materials())
        project_menu.addSeparator()
        self._action(project_menu, "Biblioteca de objetos", self.show_library)
        self._action(project_menu, "Novo objeto…", lambda: self.new_object())
        self._action(project_menu, "Pastas da biblioteca…", self.edit_library_folders)
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
        self.statusBar().addPermanentWidget(self.coords)
        self.statusBar().addPermanentWidget(QLabel(f"Grade {fmt(self.ctx.grid)} m"))
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
        detail = settings.value("detalhe_planta")
        if detail in self.detail_actions:
            self.set_plan_detail(detail)
        above = settings.value("acima_do_corte")
        if above is not None:
            self.set_show_above(str(above).lower() == "true")
        self.options_bar.show_for(self.toolbox.active)

    # --- atualização ------------------------------------------------------------------

    def _on_session(self, event: str) -> None:
        if event == "document":
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

    def _refresh_all(self) -> None:
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
        self.hint.setText(self.toolbox.active.hint())
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

    def _scale_chosen(self, index: int) -> None:
        storey, doc = self.session.storey, self.session.doc
        value = self.scale_combo.itemData(index)
        if storey is not None and value != storeys_.scale(storey):
            self.session.run(lambda: cmd.edit_storey(doc, storey, scale=value))

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

    def open_sheet(self, gid: str) -> SheetView | None:
        """Abre a prancha numa aba (spec/ui 15 §5)."""
        if self.session.doc.find(gid) is None:
            return None
        view = self.sheet_views.get(gid)
        if view is None:
            view = SheetView(self.session, gid)
            self.sheet_views[gid] = view
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
        self.setWindowTitle(f"{name}{'*' if self.session.modified else ''} — BrasBim")

    def _show_messages(self) -> None:
        self.messages.clear()
        for m in self.session.messages[-60:]:
            item = QListWidgetItem(f"{m['time']}  {m['text']}")
            item.setToolTip(m["level"])
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
        self.snap_off_action = self._action(menu, "Desligar toda a atração", self._set_snap_off)
        self.snap_off_action.setCheckable(True)
        self.snap_off_action.setChecked(self.ctx.snap_off)

    def _set_snap_kind(self, kind: str, on: bool) -> None:
        (self.ctx.snap_kinds.add if on else self.ctx.snap_kinds.discard)(kind)
        _settings().setValue("atracao/tipos", sorted(self.ctx.snap_kinds))

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
            ("Documentação", toolbars.DOC_TOOLS), ("Edição", toolbars.EDIT_TOOLS)])

    def open_palette(self) -> None:
        if getattr(self, "palette_widget", None) is None:
            from brasbim.ui.command_palette import CommandPalette

            self.palette_widget = CommandPalette(self)
        self.palette_widget.open()

    def activate_tool(self, name: str) -> None:
        tool = self.toolbox.activate(name)
        self.tools_bar.mark(name)
        self.options_bar.show_for(tool)
        self.hint.setText(tool.hint())
        self.properties.refresh()
        self.plan.update()
        self.view3d.update()
        (self.ctx.input_view or self.plan).setFocus()

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
            self.hint.setText(tool.hint())
            return
        if key == "select_similar":
            menu = QMenu(self)
            for criterion, text in select_similar.CRITERIA:
                menu.addAction(text, lambda c=criterion: self.select_similar(c))
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
            return [("Enquadrar tudo", view.fit)]
        if view is self.view3d:
            actions = [("Mostrar na planta", lambda: self.show_in_plan(gid)),
                       ("Enquadrar a seleção", view.frame_selection)]
        else:
            actions = [("Mostrar no 3D", self.show_in_3d),
                       ("Enquadrar a seleção", view.frame_selection)]
        return actions + self._object_context(gid) + self._layer_actions(gid)

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
        if not self._ask_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Abrir projeto", "", "IFC (*.ifc)")
        if path:
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
        self.statusBar().showMessage(f"Lendo {Path(path).name}…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            drawing = dxf.read(path)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return False
        finally:
            QApplication.restoreOverrideCursor()
            self.statusBar().clearMessage()
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

