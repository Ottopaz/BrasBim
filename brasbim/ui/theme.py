# SPDX-License-Identifier: GPL-3.0-or-later
"""Aparência do aplicativo (``spec/ui/11-aparencia.md``).

Um só lugar para cores, fonte, folha de estilo e marca. O tema é sempre claro: a moldura
em cinza levemente arroxeado e a folha de desenho quase branca, com grafite no texto e o
roxo jabuticaba da logo só para o que está ativo ou selecionado. Não segue o modo escuro
do sistema (misturava moldura escura com folha clara e deixava textos ilegíveis).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDockWidget,
    QStyleFactory,
    QTabBar,
    QToolTip,
)

FONT_DIR = Path(__file__).parent / "fonts"
LOGO_DIR = Path(__file__).parent / "logo"  # gerada por scripts/gerar_logo.py
FAMILY = "Archivo"
POINT_SIZE = 9.5

# Cores (spec/ui 11 §2), a partir da logo (2026-10-29): roxo jabuticaba e magenta.
PAPER = "#F8F7F8"        # folha da planta
FRAME = "#E6E3E6"        # moldura: janela, barras
PANEL = "#EFEDEF"        # painéis encaixados
FIELD = "#FFFFFF"        # campos de edição
INK = "#26222A"          # grafite: texto e linhas do desenho
INK_SOFT = "#5C5661"     # rótulos, texto secundário
INK_FAINT = "#918A95"    # desativado, dicas
RULE = "#CBC6CC"         # bordas e divisões
RULE_SOFT = "#DCD8DC"
ACCENT = "#6B1F5A"       # roxo jabuticaba: ferramenta ativa, seleção, foco
ACCENT_SOFT = "#EEDDEA"  # fundo de item selecionado / passagem do mouse
ACCENT_INK = "#FFFFFF"
BRAND_DARK = "#3A0D2C"   # jabuticaba escuro da logo
BRAND_PINK = "#E2336F"   # magenta da logo ("Bim")
WARN = "#8A5A00"
ERROR = "#B3261E"
ERROR_SOFT = "#FBE9E7"
OK = "#2F7D4A"

GRID = "#EAE7EA"
GRID_MAJOR = "#D8D3D8"
VIEW3D_BACKGROUND = "#EBE8EB"
# Eixos do controle de orientação do 3D (spec/ui 40 §4): leste, norte e para cima
AXIS_X = "#C4473F"
AXIS_Y = "#5E9A3A"
AXIS_Z = "#3C6FB8"


def rgbf(color: str) -> tuple[float, float, float]:
    c = QColor(color)
    return (c.redF(), c.greenF(), c.blueF())


def app_icon() -> QIcon:
    """Ícone do aplicativo: o símbolo da logo em todos os tamanhos gerados."""
    result = QIcon()
    for path in sorted(LOGO_DIR.glob("simbolo-*.png")):
        result.addPixmap(QPixmap(str(path)))
    return result


def logo(width: int) -> QPixmap:
    """Logo inteira (símbolo e nome) com ``width`` pixels de largura."""
    from PySide6.QtCore import Qt

    return QPixmap(str(LOGO_DIR / "logo.png")).scaledToWidth(width, Qt.SmoothTransformation)


def _load_font() -> str:
    family = FAMILY
    if FAMILY not in QFontDatabase.families():
        font_id = QFontDatabase.addApplicationFont(str(FONT_DIR / "Archivo.ttf"))
        loaded = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        family = loaded[0] if loaded else QApplication.font().family()
    return family


def font(size: float = POINT_SIZE, weight: QFont.Weight = QFont.Normal,
         width: float = 100.0) -> QFont:
    """Fonte do aplicativo; ``width`` < 100 estreita (eixo ``wdth`` da Archivo) para
    painéis densos."""
    f = QFont(QApplication.font().family())
    f.setPointSizeF(size)
    f.setWeight(weight)
    if width != 100.0:
        f.setVariableAxis(QFont.Tag("wdth"), width)
    f.setFeature(QFont.Tag("tnum"), 1)  # algarismos de mesma largura nas medidas
    return f


def palette() -> QPalette:
    p = QPalette()
    roles = {
        QPalette.Window: FRAME, QPalette.WindowText: INK, QPalette.Base: FIELD,
        QPalette.AlternateBase: PANEL, QPalette.Text: INK, QPalette.Button: PANEL,
        QPalette.ButtonText: INK, QPalette.BrightText: ACCENT_INK,
        QPalette.Highlight: ACCENT, QPalette.HighlightedText: ACCENT_INK,
        QPalette.ToolTipBase: INK, QPalette.ToolTipText: PAPER,
        QPalette.PlaceholderText: INK_FAINT, QPalette.Link: ACCENT,
        QPalette.Light: FIELD, QPalette.Midlight: RULE_SOFT, QPalette.Mid: RULE,
        QPalette.Dark: INK_FAINT, QPalette.Shadow: INK_SOFT,
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(INK_FAINT))
    return p


STYLE = f"""
QMainWindow, QDialog {{ background: {FRAME}; }}
QMainWindow::separator {{ background: {FRAME}; width: 6px; height: 6px; }}
QMainWindow::separator:hover {{ background: {RULE}; }}

QMenuBar {{ background: {FRAME}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 4px 10px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {RULE_SOFT}; }}
QMenu {{ background: {FIELD}; border: 1px solid {RULE}; padding: 4px; }}
QMenu::item {{ padding: 5px 24px 5px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; color: {INK}; }}
QMenu::separator {{ height: 1px; background: {RULE_SOFT}; margin: 4px 8px; }}

QToolBar {{ background: {FRAME}; border: none; spacing: 2px; padding: 3px; }}
QToolBar::separator {{ background: {RULE}; width: 1px; height: 1px; margin: 5px; }}
QToolBar::handle {{ width: 8px; height: 8px; }}
QToolButton {{ border: 1px solid transparent; border-radius: 5px; padding: 5px; }}
QToolButton:hover {{ background: {RULE_SOFT}; }}
QToolButton:pressed {{ background: {RULE}; }}
QToolButton:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QDockWidget {{ color: {INK_SOFT}; }}
QDockWidget::title {{ background: {FRAME}; padding: 5px 8px 3px 8px; text-align: left; }}
QDockWidget > QWidget {{ background: {PANEL}; border-top: 1px solid {RULE}; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {RULE}; }}
QTabBar {{ background: {FRAME}; }}
QTabBar::tab {{ background: transparent; color: {INK_SOFT}; padding: 6px 16px;
               border: none; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ color: {INK}; }}
QTabBar::tab:selected {{ color: {INK}; border-bottom-color: {ACCENT}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {FIELD}; border: 1px solid {RULE}; border-radius: 3px;
    padding: 2px 5px; min-height: 18px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT}; }}
QLineEdit:read-only {{ background: transparent; border-color: transparent; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {INK_FAINT}; background: {PANEL}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{ background: {FIELD}; border: 1px solid {RULE};
    selection-background-color: {ACCENT_SOFT}; selection-color: {INK}; }}

QPushButton {{ background: {FIELD}; border: 1px solid {RULE}; border-radius: 4px;
              padding: 4px 12px; }}
QPushButton:hover {{ border-color: {INK_FAINT}; }}
QPushButton:pressed {{ background: {RULE_SOFT}; }}
QPushButton:default {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {INK_FAINT}; background: {PANEL}; }}

QCheckBox, QRadioButton {{ spacing: 6px; }}

QListWidget, QTableWidget, QTableView, QTreeView {{
    background: {FIELD}; border: 1px solid {RULE_SOFT}; gridline-color: {RULE_SOFT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {INK}; }}
QHeaderView::section {{ background: {PANEL}; color: {INK_SOFT}; border: none;
    border-bottom: 1px solid {RULE}; padding: 4px 6px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {RULE}; border-radius: 4px; min-height: 24px;
                      min-width: 24px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {INK_FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QStatusBar {{ background: {FRAME}; color: {INK_SOFT}; border-top: 1px solid {RULE}; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: {INK}; color: {PAPER}; border: none; padding: 4px 6px; }}

QLabel[role="secondary"] {{ color: {INK_SOFT}; }}
QLabel[role="note"] {{ color: {INK_FAINT}; }}
QLabel[role="warning"] {{ color: {WARN}; }}
QLabel[role="group"] {{ color: {INK}; font-weight: 600; }}
QFrame#mini_barra {{ background: {FIELD}; border: 1px solid {RULE}; border-radius: 6px; }}
QFrame#mini_barra QToolButton {{ padding: 4px; }}
QFrame[role="rule"] {{ background: {RULE_SOFT}; border: none; }}
QLineEdit[invalid="true"] {{ background: {ERROR_SOFT}; border-color: {ERROR}; }}
"""


def apply(app: QApplication) -> None:
    """Aplica o tema ao aplicativo (antes de criar a janela)."""
    app.setStyle(QStyleFactory.create("Fusion"))
    family = _load_font()
    base = QFont(family)
    base.setPointSizeF(POINT_SIZE)
    base.setFeature(QFont.Tag("tnum"), 1)
    app.setFont(base)
    app.setPalette(palette())
    app.setStyleSheet(STYLE)
    install_no_elide(app)


class _NoElide(QObject):
    """Sem reticências do Qt (spec/ui 40 §2): listas, árvores e tabelas cortam o texto seco
    e dão o texto inteiro na dica; as abas não encurtam o título (aparecem as setas); o
    painel estreito fica sem título (só os botões), em vez de "Ferr…"."""

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind == QEvent.Polish:
            if isinstance(obj, QAbstractItemView):
                obj.setTextElideMode(Qt.ElideNone)
            elif isinstance(obj, QTabBar):
                obj.setElideMode(Qt.ElideNone)
        elif kind == QEvent.Resize and isinstance(obj, QDockWidget):
            fit_dock_title(obj)
        elif kind == QEvent.ToolTip and isinstance(obj.parent(), QAbstractItemView)                 and obj is obj.parent().viewport():
            return self._full_text(obj.parent(), event)
        return False

    @staticmethod
    def _full_text(view, event) -> bool:
        index = view.indexAt(event.pos())
        text = index.data(Qt.DisplayRole) if index.isValid() else None
        if not isinstance(text, str) or not text or index.data(Qt.ToolTipRole):
            return False
        rect = view.visualRect(index)
        icon_room = view.iconSize().width() + 8 if index.data(Qt.DecorationRole) else 0
        if view.fontMetrics().horizontalAdvance(text) + icon_room + 8 <= rect.width():
            return False
        QToolTip.showText(event.globalPos(), text, view)
        return True


DOCK_TITLE_ROOM = 24  # margens do título do painel encaixado (spec/ui 42 §1)
DOCK_CLOSE_ROOM = 22  # o botão de fechar, só no painel solto


def fit_dock_title(dock: QDockWidget) -> None:
    """Título do painel só se couber inteiro; o nome em Exibir > Painéis não muda."""
    full = dock.property("titulo_inteiro")
    if full is None:
        full = dock.windowTitle()
        dock.setProperty("titulo_inteiro", full)
    room = DOCK_TITLE_ROOM + (DOCK_CLOSE_ROOM if dock.isFloating() else 0)
    fits = dock.fontMetrics().horizontalAdvance(full) <= dock.width() - room
    title = full if fits else ""
    if dock.windowTitle() != title:
        dock.setWindowTitle(title)
        dock.toggleViewAction().setText(full)
        dock.setToolTip("" if fits else full)


def install_no_elide(app: QApplication) -> None:
    """Liga o ``_NoElide`` no aplicativo (uma vez só)."""
    if getattr(app, "_no_elide", None) is None:
        app._no_elide = _NoElide(app)
        app.installEventFilter(app._no_elide)
