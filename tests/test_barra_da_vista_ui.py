# SPDX-License-Identifier: GPL-3.0-or-later
"""Barra da vista e organização: interface (``spec/ui/39-barra-da-vista-e-organizacao.md``
§10)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from brasbim.core import edit_state
from brasbim.core.walls import commands as cmd
from brasbim.core.walls.wall import read_state as read_wall
from brasbim.ui.tools import Mods, selection_actions


def _wall(window, a, b):
    s = window.session
    assert s.run(lambda: cmd.create_wall(s.doc, window.toolbox.tools["wall"].options.type,
                                         s.storey, a, b))
    window.ctx.invalidate()
    return max(s.doc.ifc.by_type("IfcWall"), key=lambda e: e.id())


def _drag(tool, a, b):
    tool.move(a, Mods())
    tool.press(a, Mods())
    tool.move(b, Mods())
    tool.release(b, Mods())


def test_vb07_travar_na_interface(window):
    s = window.session
    wall = _wall(window, (0, 0), (5, 0))
    s.select([wall.GlobalId])
    assert "lock" in selection_actions(s.doc, s.selection)
    window.lock_selection(True)
    assert edit_state.is_locked(s.doc, wall)
    assert "unlock" in selection_actions(s.doc, s.selection)
    assert any(r == "Destravar" for r, _ in window._lock_context(wall.GlobalId))
    window.properties.refresh()

    tool = window.toolbox.active
    window.ctx.tol = 0.1
    assert tool._all_handles() == [] and tool.locked_handles()  # alças cinza, não pegam
    _drag(tool, (2.5, 0.0), (2.5, 2.0))  # arrastar o travado: recusado antes de começar
    assert s.messages[-1]["text"].startswith("elemento travado")
    assert read_wall(s.doc, wall)["path"]["start"] == pytest.approx([0, 0])
    window.run_selection_action("move")
    assert window.toolbox.active.name == "select"  # Mover nem começa
    window.delete_selection()
    assert s.doc.find(wall.GlobalId) is not None
    window.grab()  # desenha a planta com o cadeado

    window.lock_selection(False)
    assert not edit_state.is_locked(s.doc, wall)
    window.lock_selection(True)
    window.unlock_all()
    assert not edit_state.locked_ids(s.doc)
    window.undo()
    assert edit_state.is_locked(s.doc, wall)


def test_vb08_travado_escolhivel_e_atraivel(window):
    s = window.session
    wall = _wall(window, (0, 0), (5, 0))
    s.select([wall.GlobalId])
    window.lock_selection(True)
    window.ctx.tol = 0.1
    assert window.ctx.plan.pick((2.5, 0.0), 0.1) == wall.GlobalId  # escolhível
    assert window.view_bar.pick_locked.isChecked()
    window.view_bar.pick_locked.click()  # desliga
    assert not window.ctx.pick_locked and not s.selection
    assert window.ctx.plan.pick((2.5, 0.0), 0.1) is None
    assert wall.GlobalId not in window.ctx.plan.in_rect((-1, -1), (6, 1))
    snapped = window.ctx.snap((5.02, 0.03), Mods())
    assert snapped.kind == "end"  # a atração continua
    window.set_pick_locked(True)
    assert window.ctx.plan.pick((2.5, 0.0), 0.1) == wall.GlobalId


def test_vb01_seletores_da_barra(window):
    from brasbim.core import storeys

    bar, s = window.view_bar, window.session
    assert bar.isVisible() and bar.isAncestorOf(window.scale_combo)
    assert not window.statusBar().isAncestorOf(window.scale_combo)  # saiu da barra de estado
    window.scale_combo.setCurrentIndex(window.scale_combo.findData(100))
    assert storeys.scale(s.storey) == 100
    by_text = {a.text(): a for a in bar.detail.menu().actions()}
    by_text["Por camadas"].trigger()
    assert window.ctx.detail == "layers" and bar.detail.text() == "Por camadas"
    assert window.detail_actions["layers"].isChecked()  # o mesmo do menu Exibir
    by_text = {a.text(): a for a in bar.situation.menu().actions()}
    by_text["Antes da obra"].trigger()
    assert s.doc.situation_view == "before" and bar.situation.text() == "Antes da obra"
    assert bar.pens.menu() is window.pens_menu
    bar.pens.menu().aboutToShow.emit()
    assert bar.pens.text() in [a.text() for a in window.pens_menu.actions()]
    bar._fill_layers()
    combos = [a for a in bar.layers.menu().actions() if a.isCheckable()]
    assert combos  # combinações do projeto
    combos[-1].trigger()
    assert bar.layers.text() == combos[-1].text()
    window.set_view_bar_visible(False)
    assert not bar.isVisible()
    window.set_view_bar_visible(True)


def test_vb02_zoom_anterior_e_seguinte(window):
    plan, bar = window.plan, window.view_bar
    plan.frames.clear()
    plan.frame_index = -1
    for i in range(25):
        plan.scale = 10.0 + i
        plan.remember_frame()
    assert len(plan.frames) == 20 and plan.frames[-1][0] == 34.0
    assert bar.prev.isEnabled() and not bar.next.isEnabled()
    bar.prev.click()
    bar.prev.click()
    assert plan.scale == 32.0 and bar.next.isEnabled()
    bar.next.click()
    assert plan.scale == 33.0
    plan.scale = 99.0  # enquadramento novo depois de voltar: apaga os seguintes
    plan.remember_frame()
    assert plan.frames[-1][0] == 99.0 and not plan.can_go(1)
    assert len(plan.frames) == 20
    plan.go_frame(-1)
    assert plan.scale == 33.0


def test_vb03_zoom_por_cento(window):
    plan, bar = window.plan, window.view_bar
    center = plan.current_frame()[1:3]
    bar.set_zoom("100%")
    dpi = plan.physicalDpiX() / max(plan.devicePixelRatioF(), 1.0)
    if not 40 <= dpi <= 600:
        dpi = plan.logicalDpiX()
    assert plan.scale == pytest.approx(dpi / 25.4 * 1000 / 50)  # 1:50: 20 mm de papel/m
    assert plan.current_frame()[1:3] == pytest.approx(center)
    assert bar.zoom.lineEdit().text() == "100%"
    bar.set_zoom("250")
    assert plan.zoom_percent() == pytest.approx(250)
    bar.set_zoom("abc")  # inválido: nada muda
    assert plan.zoom_percent() == pytest.approx(250)
