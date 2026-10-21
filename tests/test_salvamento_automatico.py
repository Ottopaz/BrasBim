# SPDX-License-Identifier: GPL-3.0-or-later
"""Salvamento automático e recuperação (spec/ui/21-salvamento-automatico.md §5): SA01 a
SA05."""

import json
import os
from datetime import datetime, timedelta

import ifcopenshell
import pytest
from conftest import snapshot

from brasbim.core.walls import commands as cmd
from brasbim.ui import recovery
from brasbim.ui.session import Session

LATER = timedelta(minutes=10)


def _session(tmp_path) -> Session:
    return Session(recovery_dir=tmp_path / "recuperacao")


def _wall(s: Session, start=(0, 0), end=(5, 0)):
    wall_type = min(s.doc.ifc.by_type("IfcWallType"), key=lambda t: t.Name)
    assert s.run(lambda: cmd.create_wall(s.doc, wall_type, s.storey, start, end))


def test_sa01_copia_so_quando_muda(tmp_path):
    s = _session(tmp_path)
    assert not s.backup()  # nada mudou
    assert not s.recovery_path.exists()
    project = tmp_path / "Casa.ifc"
    _wall(s)
    s.save(str(project))
    before = project.read_bytes()
    _wall(s, (0, 0), (0, 4))
    events = []
    s.listeners.append(events.append)
    assert s.backup()
    assert "backup" in events and "messages" not in events  # nada no painel Mensagens
    assert not s.backup()  # já está na cópia
    copy = ifcopenshell.open(str(s.recovery_path))
    assert len(copy.by_type("IfcWall")) == 2
    assert snapshot(copy) == snapshot(s.doc.ifc)
    meta = json.loads(recovery.sidecar(s.recovery_path).read_text(encoding="utf-8"))
    assert meta["file"] == str(project)
    assert project.read_bytes() == before  # o arquivo do projeto não muda
    assert not list((tmp_path / "recuperacao").glob("*.tmp*"))


def test_sa02_copia_apagada(tmp_path):
    s = _session(tmp_path)
    _wall(s)
    assert s.backup()
    path = s.recovery_path
    s.save(str(tmp_path / "a.ifc"))
    assert not path.exists() and not recovery.sidecar(path).exists()
    _wall(s, (0, 0), (0, 4))
    assert s.backup()
    first = s.recovery_path
    s.new()
    assert not first.exists() and s.recovery_path != first
    _wall(s)
    assert s.backup()
    second = s.recovery_path
    s.open(str(tmp_path / "a.ifc"))
    assert not second.exists()
    _wall(s, (0, 0), (0, 4))
    assert s.backup()
    third = s.recovery_path
    s.close()
    assert not third.exists()


def test_sa03_recupera_sessao_que_nao_fechou(tmp_path):
    crashed = _session(tmp_path)
    project = tmp_path / "Casa.ifc"
    _wall(crashed)
    crashed.save(str(project))
    _wall(crashed, (0, 0), (0, 4))
    assert crashed.backup()
    expected = snapshot(crashed.doc.ifc)
    # sem close(): o BrasBim caiu. A próxima abertura, 10 min depois:
    s = _session(tmp_path)
    (entry,) = s.orphan_backups(datetime.now() + LATER)
    assert entry["file"] == str(project)
    s.recover(entry)
    assert snapshot(s.doc.ifc) == expected
    assert s.path == str(project) and s.modified
    assert not s.history.undo_stack
    assert s.recovery_path.exists()  # a cópia agora é desta sessão
    assert not s.orphan_backups(datetime.now() + LATER)  # não é oferecida de novo
    assert any("recuperado" in m["text"] for m in s.messages)
    s.save()
    assert len(ifcopenshell.open(str(project)).by_type("IfcWall")) == 2
    # projeto sem nome volta sem nome; descartar apaga
    crashed2 = _session(tmp_path)
    _wall(crashed2)
    assert crashed2.backup()
    s2 = _session(tmp_path)
    (entry,) = s2.orphan_backups(datetime.now() + LATER)
    assert entry["file"] is None
    s2.discard_orphan(entry)
    assert not entry["path"].exists()
    assert not s2.orphan_backups(datetime.now() + LATER)


def test_sa04_outra_janela_aberta(tmp_path):
    other = _session(tmp_path)
    _wall(other)
    assert other.backup()
    s = _session(tmp_path)
    assert not s.orphan_backups(datetime.now() + timedelta(minutes=1))
    other.heartbeat(datetime.now() + LATER)  # a outra janela continua viva
    assert not s.orphan_backups(datetime.now() + LATER + timedelta(minutes=1))
    assert len(s.orphan_backups(datetime.now() + 2 * LATER)) == 1
    # cópia com o JSON estragado é ignorada
    recovery.sidecar(other.recovery_path).write_text("{", encoding="utf-8")
    assert not s.orphan_backups(datetime.now() + 2 * LATER)


def test_sa05_interface(window, app, tmp_path, monkeypatch):
    s = window.session
    s.recovery_dir = tmp_path / "recuperacao"
    s.new()
    window.backup_actions[2].trigger()
    assert window.backup_minutes == 2
    _wall(s)
    t0 = window._last_backup
    assert not window.backup_tick(t0 + 60)  # um minuto: ainda não
    assert window.backup_tick(t0 + 120)
    assert s.recovery_path.exists()
    assert "Cópia de segurança" in window.statusBar().currentMessage()
    window.backup_actions[0].trigger()  # desligado
    _wall(s, (0, 0), (0, 4))
    assert not window.backup_tick(t0 + 10_000)
    # a pergunta da abertura: uma cópia órfã de outra sessão
    crashed = Session(recovery_dir=tmp_path / "recuperacao")
    _wall(crashed)
    _wall(crashed, (0, 0), (0, 3))
    _wall(crashed, (0, 3), (3, 3))
    assert crashed.backup()
    old = datetime.now() - LATER
    recovery.touch(crashed.recovery_path, old)
    os.utime(crashed.recovery_path)
    s.modified = False
    asked = []
    monkeypatch.setattr(window, "_ask_recovery", lambda text: asked.append(text) or "later")
    window.offer_recovery()
    assert "projeto sem nome" in asked[0]
    assert crashed.recovery_path.exists()  # depois: fica para a próxima
    monkeypatch.setattr(window, "_ask_recovery", lambda text: "recover")
    window.offer_recovery()
    assert len(s.doc.ifc.by_type("IfcWall")) == 3
    assert s.modified and "*" in window.windowTitle()


@pytest.fixture(autouse=True)
def _sem_janela_de_salvar(monkeypatch):
    """Nenhum teste aqui deve abrir a pergunta "Salvar as alterações?"."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: pytest.fail("pergunta inesperada"))
