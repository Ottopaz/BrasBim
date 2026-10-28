# SPDX-License-Identifier: GPL-3.0-or-later
"""Projeto compartilhado na interface (spec/ui/33-projeto-compartilhado.md §4): duas
janelas no mesmo processo, uma compartilha e a outra entra."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF

from brasbim.core.walls import commands as cmd
from brasbim.ui import main_window as mw
from brasbim.ui.session import Session
from brasbim.ui.team_panel import parse_address


@pytest.fixture
def guest(app, tmp_path):
    session = Session(journal_dir=tmp_path / "diarios_b")
    w = mw.MainWindow(session)
    w.quiet_dialogs = True
    w.resize(1200, 800)
    w.show()
    w.plan.scale, w.plan.origin = 50.0, QPointF(100, 600)
    app.processEvents()
    yield w
    session.modified = False
    w.close()


def _settle(app, *windows, until, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for w in windows:
            w.session.poll()
        app.processEvents()
        if until():
            return
        time.sleep(0.01)
    raise AssertionError("tempo esgotado")


def test_eq_interface_compartilhar_entrar_e_reservas(app, window, guest):
    host = window
    assert not host.team_label.isVisible() and not host.leave_action.isEnabled()
    assert host.share_project("Ana", port=0, discovery=False)
    port = host.session.server.port
    assert host.team_dock.isVisible() and host.leave_action.isEnabled()
    assert "localhost" not in host._team_info and str(port) in host._team_info
    assert guest.join_project(choose=("127.0.0.1", port, "Beto"))
    _settle(app, host, guest, until=lambda: len(host.session.collab.users) == 2)
    assert "2 pessoas" in host.team_label.text()
    assert "(compartilhado)" in guest.windowTitle()

    s = host.session
    s.run(lambda: cmd.create_rectangle(s.doc, host.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    walls = [w.GlobalId for w in s.doc.ifc.by_type("IfcWall")]
    _settle(app, host, guest, until=lambda: all(
        guest.session.collab.reservations.get(g) == host.session.collab.me for g in walls))
    assert {w.GlobalId for w in guest.session.doc.ifc.by_type("IfcWall")} == set(walls)
    # Na planta de B as paredes de A têm contorno; o botão direito pede a liberação.
    assert set(guest.session.collab.reserved_by_others()) >= set(walls)
    labels = [t for t, _ in guest._team_context(walls[0])]
    assert labels == ["Pedir liberação a Ana"]
    assert host._team_context(walls[0]) == []
    guest.plan.grab()  # desenha o contorno sem erro
    # B não move a parede de A: a recusa vira mensagem.
    g = guest.session
    assert not g.run(lambda: cmd.edit_wall(g.doc, g.doc.get(walls[0]), base_offset=0.1))
    assert g.messages[-1]["text"].startswith("A parede está reservada")
    # Pedido e liberação pelo painel.
    guest._team_context(walls[0])[0][1]()
    _settle(app, host, guest, until=lambda: host.session.requests)
    host.team.refresh()
    assert host.team.requests_layout.count() == 1
    host.session.answer_request(host.session.requests[0], True)
    _settle(app, host, guest,
            until=lambda: guest.session.collab.reservations.get(walls[0])
            == guest.session.collab.me)
    assert g.run(lambda: cmd.edit_wall(g.doc, g.doc.get(walls[0]), base_offset=0.1))
    _settle(app, host, guest, until=lambda: not guest.session.collab._pending)
    # Sair: o convidado continua com a cópia.
    host.leave_shared()
    _settle(app, guest, until=lambda: not guest.session.shared)
    assert not guest.team_label.isVisible()
    assert len(guest.session.doc.ifc.by_type("IfcWall")) == len(walls)


def test_eq_interface_endereco():
    assert parse_address("pc-ana") == ("pc-ana", 47815)
    assert parse_address(" 192.168.0.10:47820 ") == ("192.168.0.10", 47820)


def test_eq_interface_menu_nao_passa_checked(window, monkeypatch):
    """O triggered do menu passa ``checked`` (bool); ele não pode virar o nome nem o
    endereço (erro do revisor em 2026-10-28: "cannot unpack non-iterable bool")."""
    calls = []
    monkeypatch.setattr(window, "share_project", lambda *a, **k: calls.append(("share", a)))
    monkeypatch.setattr(window, "join_project", lambda *a, **k: calls.append(("join", a)))
    monkeypatch.setattr(window, "export_pdf", lambda *a, **k: calls.append(("pdf", a)))
    for menu in window.menuBar().actions():
        for action in menu.menu().actions():
            if action.text().startswith(("Compartilhar", "Entrar", "Exportar PDF")):
                action.trigger()
    assert sorted(calls) == [("join", ()), ("pdf", ()), ("share", ())]
