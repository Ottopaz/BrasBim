# SPDX-License-Identifier: LGPL-3.0-or-later
"""Utilitários de teste: modelo base e comparação de IFC por GlobalId e atributos."""

import sys

import ifcopenshell
import pytest

from brasbim.core.document import Document
from brasbim.core.ops import History
from brasbim.core.walls import commands as cmd

PROJECT_ID = "3BrasBimTesteProjeto00"

LAYERS_14 = [
    {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
    {"material": "Bloco cerâmico", "thickness": 0.09, "category": "LoadBearing", "priority": 80},
    {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
]


class Model:
    """Documento + histórico com térreo (0,00), superior (2,80) e um tipo de 14 cm."""

    def __init__(self):
        self.doc = Document.new(project_id=PROJECT_ID)
        self.history = History(self.doc)
        self.commit(cmd.create_storey(self.doc, "Térreo", 0.0))
        self.commit(cmd.create_storey(self.doc, "Superior", 2.8))
        self.terreo, self.superior = self.doc.storeys()
        self.commit(cmd.create_wall_type(self.doc, "Alvenaria 14", LAYERS_14))
        (self.type14,) = self.doc.ifc.by_type("IfcWallType")

    def commit(self, tx):
        self.history.commit(tx)
        return tx

    def wall(self, start=(0, 0), end=(5, 0), **options):
        tx = self.commit(cmd.create_wall(self.doc, self.type14, self.terreo, start, end, **options))
        return self.doc.get(tx.ops[0].id)

    def reopen(self, tmp_path):
        path = tmp_path / "modelo.ifc"
        self.doc.save(str(path))
        # Guardar a referência: as entidades não mantêm o arquivo vivo.
        self.reopened = ifcopenshell.open(str(path))
        return self.reopened


@pytest.fixture
def model():
    return Model()


def _value(v, top=False):
    if isinstance(v, ifcopenshell.entity_instance):
        if v.is_a("IfcOwnerHistory"):
            return None
        if v.is_a("IfcRoot") and not top:
            return ("ref", v.GlobalId)
        return (v.is_a(), tuple(_value(a) for a in v))
    if isinstance(v, (list, tuple)):
        items = [_value(x) for x in v]
        if items and all(isinstance(i, tuple) and i and i[0] == "ref" for i in items):
            items.sort()
        return tuple(items)
    if isinstance(v, float):
        r = round(v, 6)
        return 0.0 if r == 0 else r
    return v


def snapshot(ifc) -> dict:
    """{GlobalId: atributos expandidos} de todas as entidades IfcRoot."""
    return {e.GlobalId: _value(e, top=True) for e in ifc.by_type("IfcRoot")}


# --- interface (Qt sem tela) -------------------------------------------------------------


# As janelas dos testes de interface ficam vivas até o fim (pendência no CONTEXTO: a
# fixture `window` fecha mas não apaga, e as conexões de sinal as seguram), e os servidores
# do projeto compartilhado deixam linhas abertas. No Linux e no macOS, destruir tudo isso
# na saída do Python derruba o processo (falha de segmentação, código 139) depois de os
# testes terem terminado (no Windows, com o Python 3.13). Saímos direto com o código do
# pytest, depois do resumo. No Windows, `os._exit` chama ExitProcess, que ainda descarrega
# as DLLs do Qt e cai do mesmo jeito; TerminateProcess encerra sem passar por elas.
_exit_status = None


def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if _exit_status is None or "PySide6" not in sys.modules:
        return
    import os

    sys.stdout.flush()
    sys.stderr.flush()
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.TerminateProcess.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        kernel32.TerminateProcess(kernel32.GetCurrentProcess(), _exit_status)
    os._exit(_exit_status)



@pytest.fixture(scope="module")
def app(tmp_path_factory):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    # Preferências da janela (posição de painéis e barras) num lugar só dos testes, para
    # não ler nem gravar as do usuário.
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope,
                      str(tmp_path_factory.mktemp("preferencias")))
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    """Janela principal com um projeto novo; planta a 50 px/m com (0, 0) em (100, 600)."""
    from PySide6.QtCore import QPointF

    from brasbim.ui import main_window as mw
    from brasbim.ui.session import Session

    session = Session(journal_dir=tmp_path / "diarios")
    w = mw.MainWindow(session)
    w.quiet_dialogs = True
    w.resize(1260, 800)  # a barra Ferramentas ocupa uma coluna própria (spec/ui 34 §3)
    w.show()
    w.plan.scale, w.plan.origin = 50.0, QPointF(100, 600)
    w.plan._sync_tol()
    app.processEvents()
    yield w
    session.modified = False
    w.close()
