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
