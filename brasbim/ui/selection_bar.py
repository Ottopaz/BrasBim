# SPDX-License-Identifier: GPL-3.0-or-later
"""Mini-barra da seleção (``spec/ui/03-barras-e-icones.md`` §5): ícones das ações sobre
o que está selecionado, na planta, junto à seleção.

Quais ações aparecem e onde a barra fica são calculados sem Qt em ``tools.py``
(``selection_actions`` e ``bar_position``).
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

from brasbim.ui import icons
from brasbim.ui.tools import bar_position, selection_actions

# ação → (ícone, nome, uso)
ACTIONS = {
    "move": ("move", "Mover", "clique o ponto de base e o destino"),
    "copy": ("copy", "Copiar", "clique o ponto de base e o destino de cada cópia"),
    "rotate": ("rotate", "Girar", "clique o centro, a direção de referência e a final"),
    "mirror": ("mirror", "Espelhar",
               "clique dois pontos do eixo; Ctrl no segundo mantém o original"),
    "split": ("split", "Dividir", "clique o ponto de divisão na parede selecionada"),
    "join": ("join", "Unir", "estende as duas paredes até o encontro"),
    "unjoin": ("unjoin", "Desfazer junção",
               "separa as duas paredes; a junção não volta sozinha"),
    "swap": ("swap", "Trocar a contínua", "no cruzamento, a outra parede fica inteira"),
    "flip_opening": ("flip_opening", "Inverter sentido", "a folha passa a abrir para o outro lado"),
    "flip_hinges": ("flip_hinges", "Inverter dobradiças", "troca o lado das dobradiças"),
    "slab_opening": ("slab_opening", "Abertura",
                     "desenhe uma abertura (escada, shaft) dentro da laje selecionada"),
    "auto_dimension": ("dimension", "Cotar",
                       "cota em cadeia na face externa: pontas da parede e bordas dos vãos"),
    "swap_type": ("swap_type", "Trocar tipo", "escolhe outro tipo para os objetos"),
    "edit_object_type": ("edit_type", "Editar tipo",
                         "valores do tipo; valem para todas as ocorrências dele"),
    "select_similar": ("select_same", "Selecionar semelhantes",
                       "escolha o critério: classe IFC, tipo, material, camada…"),
    "detach": ("detach", "Soltar da parede", "o objeto fica livre, no mesmo lugar, sem o vão"),
    "pick_curves": ("pick_curves", "Pegar linhas",
                    "clique ou tecle Enter sobre as linhas do desenho para pô-las no terreno"),
    "curve_level": ("curve_level", "Cota das curvas",
                    "clique uma curva do terreno e digite a cota"),
    "delete": ("delete", "Excluir", "exclui a seleção (Delete)"),
}


ZOOM_PAUSE_MS = 300  # sem girar a roda por este tempo, o zoom acabou e a barra volta


class SelectionBar(QFrame):
    def __init__(self, plan_view, run_action):
        super().__init__(plan_view)
        self.plan_view = plan_view
        self.run_action = run_action
        self.enabled = True  # Exibir > Mini-barra da seleção
        self.setObjectName("mini_barra")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(2, 2, 2, 2)
        self.layout_.setSpacing(0)
        self.buttons: dict[str, QToolButton] = {}
        for key, (icon_name, name, usage) in ACTIONS.items():
            button = QToolButton(self)
            button.setIcon(icons.icon(icon_name))
            button.setIconSize(QSize(20, 20))
            button.setAutoRaise(True)
            button.setToolTip(f"{name} — {usage}")
            button.clicked.connect(lambda _=False, k=key: self.run_action(k))
            self.layout_.addWidget(button)
            self.buttons[key] = button
        self.hide()

    def visible_actions(self) -> list[str]:
        return [k for k, b in self.buttons.items() if not b.isHidden()]

    def place(self) -> None:
        """Mostra, esconde e posiciona conforme a seleção e a ferramenta (§5)."""
        view = self.plan_view
        tool = view.toolbox.active
        session = view.ctx.session
        busy = (tool.name != "select" or getattr(tool, "drag", None) is not None
                or getattr(tool, "drag3d", None) is not None
                or getattr(view, "navigating", False))  # zoom, deslocamento ou órbita
        other = view.ctx.input_view not in (None, view)  # só na vista em uso (spec/ui 07 §3.1)
        rect = view.selection_rect() if session.selection else None
        if not self.enabled or busy or other or rect is None:
            self.hide()
            return
        wanted = set(selection_actions(session.doc, session.selection))
        for key, button in self.buttons.items():
            button.setVisible(key in wanted)
        self.adjustSize()
        x, y = bar_position(rect, (self.width(), self.height()), (view.width(), view.height()))
        self.move(int(x), int(y))
        self.show()
        self.raise_()
