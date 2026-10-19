# SPDX-License-Identifier: GPL-3.0-or-later
"""Janela principal (``spec/ui/01-janela-e-ferramentas.md`` §2, §6, §8, §9; barras e
mini-barra, ``spec/ui/03-barras-e-icones.md`` §2–§5)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence
from PySide6.QtWidgets import (
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


def cascade_text(doors_n: int, windows_n: int) -> str:
    """"1 porta e 2 janelas" (spec/ui 09 §4.1)."""
    parts = [f"{n} {one if n == 1 else many}" for n, one, many in
             ((doors_n, "porta", "portas"), (windows_n, "janela", "janelas")) if n]
    return " e ".join(parts)


def delete_transaction(session: Session) -> tuple[Transaction, str]:
    """Exclusão da seleção numa transação (§5.1): esquadrias antes das paredes, depois
    pilares, vigas e lajes (spec/ui 10 §4.1); operações
    repetidas (abertura, junção entre duas paredes excluídas) entram uma vez. Devolve a
    transação e o que sai junto com as paredes ("1 porta e 2 janelas"; vazio se nada)."""
    tx, cascade = delete_elements(session.doc, session.selection)
    return tx, cascade_text(cascade["IfcDoor"], cascade["IfcWindow"])


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
            view.context_requested.connect(
                lambda gid, pos, v=view: self.show_context_menu(v, gid, pos))
            view.selection_bar = SelectionBar(view, self.run_selection_action)
        self.selection_bar = self.plan.selection_bar
        self.resize(1280, 800)
        self._hook_tools()
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
        self.project_dock = self._dock("Projeto", "projeto", self.project,
                                       Qt.LeftDockWidgetArea)
        self.properties = PropertiesPanel(self.session, self.toolbox)
        self.properties.setMinimumWidth(310)
        self.properties.edit_type = self.edit_type
        self.properties.open_view = self.open_view
        self.properties.open_sheet = self.open_sheet
        self.properties.open_table = self.open_table
        self.properties.edit_project_info = self.edit_project_info
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
        self._action(file_menu, "Exportar PDF…", self.export_pdf, "Ctrl+P")
        self._action(file_menu, "Exportar tabela…", lambda: self.export_table())
        self._action(file_menu, "Dados do projeto…", self.edit_project_info)
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
                              (self.space_numbers_action, False), (self.weights_action, True),
                              (self.view_symbols_action, True)):
            action.setCheckable(True)
            action.setChecked(value)
        view_menu.addSeparator()
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
                                    (self.space_numbers_action, "numeros_ambientes",
                                     "show_space_numbers"),
                                    (self.weights_action, "espessuras_linha", "show_weights"),
                                    (self.view_symbols_action, "simbolos_corte",
                                     "show_view_symbols")):
            value = settings.value(key)
            if value is not None:
                action.setChecked(str(value).lower() == "true")
                self._set_plan_option(option, action.isChecked())
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
        elif event == "selection":
            self.properties.refresh()
            for view in self.section_views.values():
                view.update()
            self.plan.update()
            self.view3d.update()
            self._refresh_show_actions()
        elif event == "messages":
            self._show_messages()

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
        self.toolbox.tools["select"].ask_text = self.ask_text

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
        if key == "auto_dimension":
            wall = next(iter(session.selection), None)
            session.run(lambda: ac.auto_dimension_wall(doc, wall))
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
            return [("Mostrar na planta", lambda: self.show_in_plan(gid)),
                    ("Enquadrar a seleção", view.frame_selection)]
        return [("Mostrar no 3D", self.show_in_3d), ("Enquadrar a seleção", view.frame_selection)]

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

