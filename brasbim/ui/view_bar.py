# SPDX-License-Identifier: GPL-3.0-or-later
"""Barra da vista (``spec/ui/39-barra-da-vista-e-organizacao.md`` §2): faixa fina sob a
planta (e sob os cortes e fachadas), acima da linha de comando.

Cada item é um botão com ícone próprio e o valor atual em texto; o clique abre a mesma
lista do menu Exibir. Os estados ficam na janela (``MainWindow``); a barra só os mostra e
os muda pelas mesmas funções do menu.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
)

from brasbim.core import display_layers as dl
from brasbim.core import intervention, pens
from brasbim.ui import icons, theme
from brasbim.ui.plan_view import ZOOM_PERCENTS, PlanView
from brasbim.ui.section_view import SectionView

DETAIL_LABEL = {"simple": "Simplificado", "layers": "Por camadas"}


def _button(icon: str, tip: str, text: str = "") -> QToolButton:
    button = QToolButton()
    button.setIcon(icons.icon(icon))
    button.setIconSize(QSize(16, 16))
    button.setAutoRaise(True)
    button.setToolTip(tip)
    if text:
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    return button


def _menu_button(icon: str, tip: str) -> QToolButton:
    button = _button(icon, tip, " ")
    button.setPopupMode(QToolButton.InstantPopup)
    button.setMenu(QMenu(button))
    return button


class ViewBar(QFrame):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setObjectName("barra_da_vista")
        self.setMinimumWidth(1)  # janela estreita: corta a barra em vez de alargar o centro
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"#barra_da_vista {{ background:{theme.FRAME}; border-top:1px solid {theme.RULE}; }}"
            f"#barra_da_vista QToolButton {{ color:{theme.INK_SOFT}; padding:1px 4px; }}"
            f"#barra_da_vista QToolButton:checked {{ background:{theme.ACCENT_SOFT};"
            f" color:{theme.ACCENT}; border:1px solid {theme.RULE}; border-radius:3px; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(2)
        # Zoom (§2.1)
        self.prev = _button("zoom_prev", "Zoom anterior (botão de trás do mouse)")
        self.next = _button("zoom_next", "Zoom seguinte (botão da frente do mouse)")
        self.fit = _button("zoom_fit", "Enquadrar tudo (Home)")
        self.prev.clicked.connect(lambda: self._go(-1))
        self.next.clicked.connect(lambda: self._go(1))
        self.fit.clicked.connect(self._fit)
        self.zoom = QComboBox()
        self.zoom.setEditable(True)
        self.zoom.setInsertPolicy(QComboBox.NoInsert)
        self.zoom.setToolTip("Zoom: 100% é o desenho do tamanho do papel na escala da vista; "
                             "digite outro valor")
        self.zoom.lineEdit().setValidator(QIntValidator(1, 100000, self.zoom))
        for value in ZOOM_PERCENTS:
            self.zoom.addItem(f"{value}%", value)
        self.zoom.setMinimumContentsLength(5)
        self.zoom.setMinimumWidth(self.zoom.fontMetrics().horizontalAdvance("4000%") + 30)
        self.zoom.activated.connect(lambda i: self.set_zoom(self.zoom.itemData(i)))
        self.zoom.lineEdit().returnPressed.connect(
            lambda: self.set_zoom(self.zoom.lineEdit().text()))
        for widget in (self.prev, self.next, self.fit, self.zoom):
            layout.addWidget(widget)
        self.zoom_group = (self.prev, self.next, self.fit, self.zoom)
        # Os grupos se espalham pela largura da vista, com o mesmo vão entre eles (spec/ui 42 §3)
        layout.addStretch(1)
        # Giro da vista (§3): o botão mostra o ângulo; a lista define por dois cliques,
        # digita ou volta a 0°.
        self.rotation = _menu_button("view_rotate", "Girar a vista da planta (só a tela; "
                                     "o modelo não muda)")
        menu = self.rotation.menu()
        menu.addAction("Definir por dois cliques", lambda: window.rotate_view(None))
        menu.addAction("Digitar o ângulo", self.ask_rotation)
        menu.addAction("Voltar a 0°", lambda: window.rotate_view(0.0))
        layout.addWidget(self.rotation)
        layout.addStretch(1)
        # Escala: o mesmo seletor que estava na barra de estado
        self.scale_icon = QLabel()
        self.scale_icon.setPixmap(icons.icon("scale").pixmap(16, 16))
        self.scale_icon.setToolTip(window.scale_combo.toolTip())
        layout.addWidget(self.scale_icon)
        layout.addWidget(window.scale_combo)
        layout.addStretch(1)
        self.layers = _menu_button("layers_all", "Combinação de camadas")
        self.layers.menu().aboutToShow.connect(self._fill_layers)
        self.detail = _menu_button("detail", "Detalhe da planta")
        for action in window.detail_actions.values():
            self.detail.menu().addAction(action)
        self.pens = _menu_button("pens", "Tabela de penas")
        self.pens.setMenu(window.pens_menu)
        self.situation = _menu_button("situation", "Situação na vista (projeto legal)")
        for action in window.situation_actions.values():
            self.situation.menu().addAction(action)
        for widget in (self.layers, self.detail, self.pens, self.situation):
            layout.addWidget(widget)
            layout.addStretch(1)
        # Só quando há: "N ocultos · Mostrar tudo" (§4)
        self.hidden_label = QLabel()
        self.show_all = _button("eye", "Mostrar os elementos ocultos nesta sessão",
                                "Mostrar tudo")
        self.show_all.clicked.connect(window.show_all)
        layout.addWidget(self.hidden_label)
        layout.addWidget(self.show_all)
        # À direita: chave Escolher travados (§5)
        self.pick_locked = _button("lock", "Escolher travados — desligada, o clique e a "
                                   "janela não pegam os elementos travados (a atração "
                                   "continua)", "Escolher travados")
        self.pick_locked.setCheckable(True)
        self.pick_locked.setToolButtonStyle(Qt.ToolButtonIconOnly)  # o nome fica na dica
        # Marcada é o normal: o cadeado fica na cor do texto, sem a versão clara.
        self.pick_locked.setIcon(QIcon(icons.icon("lock").pixmap(16, QIcon.Normal, QIcon.Off)))
        self.pick_locked.setChecked(True)
        self.pick_locked.toggled.connect(window.set_pick_locked)
        layout.addWidget(self.pick_locked)
        self.texted = (self.rotation, self.layers, self.detail, self.pens, self.situation,
                       self.show_all)
        self.tips = {b: b.toolTip() for b in self.texted}
        self.plan_only = (self.rotation, self.scale_icon, window.scale_combo, self.detail)

    # --- vista ------------------------------------------------------------------------

    def view(self):
        """A vista com zoom à frente: a planta ou um corte/fachada; senão None."""
        current = self.window.tabs.currentWidget()
        if self.window.split or isinstance(current, PlanView):
            return self.window.plan
        if isinstance(current, SectionView):
            return current
        return None

    def _go(self, step: int) -> None:
        view = self.view()
        if view is not None:
            view.go_frame(step)
        self.refresh_zoom()

    def _fit(self) -> None:
        view = self.view()
        if view is not None:
            view.fit()
        self.refresh_zoom()

    def set_zoom(self, value) -> None:
        view = self.view()
        try:
            percent = float(str(value).strip().rstrip("%").replace(",", "."))
        except ValueError:
            percent = 0
        if view is None or percent <= 0:
            self.refresh_zoom()
            return
        view.set_zoom_percent(percent)
        self.refresh_zoom()

    # --- atualização ------------------------------------------------------------------

    def refresh(self) -> None:
        view = self.view()
        plan = view is self.window.plan
        for widget in self.zoom_group:
            widget.setVisible(view is not None)
        for widget in self.plan_only:
            widget.setVisible(plan)
        doc = self.window.session.doc
        comb = dl.matching_combination(doc, self.window.session.display)
        self.layers.setVisible(dl.read_config(doc) is not None)
        self.layers.setText(comb["name"] if comb else "(alterada)")
        self.detail.setText(DETAIL_LABEL[self.window.ctx.detail])
        self.pens.setText(pens.table(pens.config(doc), self.window.window_pens)["name"])
        self.situation.setText(intervention.VIEW_LABEL[doc.situation_view])
        self.pick_locked.setChecked(self.window.ctx.pick_locked)
        hidden = len(self.window.ctx.hidden)
        self.hidden_label.setText(f"{hidden} oculto{'s' if hidden != 1 else ''} ·")
        self.hidden_label.setVisible(bool(hidden))
        self.show_all.setVisible(bool(hidden))
        self.refresh_zoom()
        self._fit_texts()
        return
        self.refresh_zoom()

    def ask_rotation(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        current = math.degrees(self.window.plan.rotation)
        value, ok = QInputDialog.getDouble(self, "Girar a vista", "Ângulo (°):", current,
                                           -360.0, 360.0, 2)
        if ok:
            self.window.rotate_view(value)

    def _fit_texts(self) -> None:
        """Sem lugar para tudo, os botões mostram só o ícone; o valor vai para a dica."""
        for button in self.texted:
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setToolTip(f"{self.tips[button]}: {button.text()}")
        if self.layout().sizeHint().width() > self.width():
            for button in self.texted:
                button.setToolButtonStyle(Qt.ToolButtonIconOnly)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_texts()

    def refresh_zoom(self) -> None:
        degrees = math.degrees(self.window.plan.rotation)
        self.rotation.setText(f"{round(degrees, 1) + 0.0:.1f}°".replace(".", ","))
        view = self.view()
        if view is None:
            return
        self.prev.setEnabled(view.can_go(-1))
        self.next.setEnabled(view.can_go(1))
        if not self.zoom.lineEdit().hasFocus():
            self.zoom.lineEdit().setText(f"{round(view.zoom_percent())}%")

    def _fill_layers(self) -> None:
        menu = self.layers.menu()
        menu.clear()
        doc, session = self.window.session.doc, self.window.session
        config = dl.read_config(doc) or dl.empty_config()
        current = dl.matching_combination(doc, session.display)
        for comb in config["combinations"]:
            action = menu.addAction(comb["name"])
            action.setCheckable(True)
            action.setChecked(current is not None and current["id"] == comb["id"])
            action.triggered.connect(lambda _=False, c=comb["id"]: self.window.use_combination(c))
        menu.addSeparator()
        menu.addAction("Camadas", self.window.show_layers)
