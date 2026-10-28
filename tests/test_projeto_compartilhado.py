# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto compartilhado na rede local (spec/ui/33-projeto-compartilhado.md, EQ01–EQ09).

Servidor e clientes de verdade, por TCP em 127.0.0.1.
"""

import time

import ifcopenshell
import pytest
from conftest import Model, snapshot

from brasbim.core.collab import Client, Server, discover
from brasbim.core.document import Document, OpError
from brasbim.core.ops import History
from brasbim.core.walls import commands as cmd


def ifc_equivalent(x, y) -> bool:
    return snapshot(x) == snapshot(y)


class Peer:
    """Uma pessoa: cliente + documento + histórico."""

    def __init__(self, server: Server, name: str):
        self.client = Client(name)
        welcome = self.client.connect("127.0.0.1", server.port)
        self.doc = Document(ifcopenshell.file.from_string(welcome["ifc"]))
        self.history = History(self.doc)
        self.client.attach(self.history)
        self.events = []
        self.client.listeners.append(lambda e, d: self.events.append((e, d)))

    @property
    def type14(self):
        return self.doc.ifc.by_type("IfcWallType")[0]

    @property
    def terreo(self):
        return self.doc.storeys()[0]

    def wall(self, start=(0, 0), end=(5, 0)):
        tx = cmd.create_wall(self.doc, self.type14, self.terreo, start, end)
        self.history.commit(tx)
        return tx.ops[0].id


def settle(*peers, until=None, timeout=5.0):
    """Processa as mensagens até nada pendente (e ``until()`` verdadeiro)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        for p in peers:
            p.client.poll()
        if all(not p.client._pending for p in peers) and (until is None or until()):
            time.sleep(0.05)
            for p in peers:
                p.client.poll()
            if all(not p.client._pending for p in peers) and (until is None or until()):
                return
        time.sleep(0.01)
    raise AssertionError("tempo esgotado esperando a sincronização")


@pytest.fixture
def server():
    base = Model()
    s = Server(base.doc.ifc.to_string(), project="Casa", host="pc-teste", port=0,
               discovery=False).start()
    yield s
    s.stop()


@pytest.fixture
def pair(server):
    a, b = Peer(server, "Ana"), Peer(server, "Beto")
    settle(a, b, until=lambda: len(a.client.users) == 2)
    yield a, b
    a.client.close()
    b.client.close()


def test_eq01_parede_de_a_aparece_em_b(pair, server):
    a, b = pair
    gid = a.wall()
    settle(a, b, until=lambda: b.doc.find(gid) is not None)
    assert b.doc.get(gid, "IfcWall")
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)
    assert ifc_equivalent(a.doc.ifc, server.doc.ifc)
    assert any(e == "reservations" for e, _ in b.events)


def test_eq02_criado_fica_reservado_e_b_nao_edita(pair):
    a, b = pair
    gid = a.wall()
    settle(a, b, until=lambda: b.client.reservations.get(gid) == a.client.me)
    assert a.client.owner(gid)["name"] == "Ana"
    wall = b.doc.get(gid)
    with pytest.raises(OpError, match="reservad[ao] por Ana"):
        b.history.commit(cmd.edit_wall(b.doc, wall, base_offset=3.0 - 3))
    with pytest.raises(OpError, match="reservad[ao] por Ana"):
        b.history.commit(cmd.delete_wall(b.doc, wall))
    assert b.doc.find(gid) is not None and not b.history.undo_stack
    assert gid in b.client.reserved_by_others()


def test_eq03_autorreserva_ao_editar_elemento_livre(pair):
    a, b = pair
    gid = a.wall()
    settle(a, b, until=lambda: gid in b.client.reservations)
    a.client.release()
    settle(a, b, until=lambda: gid not in b.client.reservations)
    b.history.commit(cmd.edit_wall(b.doc, b.doc.get(gid), base_offset=3.1 - 3))
    settle(a, b, until=lambda: a.client.reservations.get(gid) == b.client.me)
    with pytest.raises(OpError, match="reservad[ao] por Beto"):
        a.history.commit(cmd.edit_wall(a.doc, a.doc.get(gid), base_offset=2.5 - 3))
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)


def test_eq04_pedir_e_liberar(pair):
    a, b = pair
    gid = a.wall()
    settle(a, b, until=lambda: gid in b.client.reservations)
    b.client.request([gid])
    settle(a, b, until=lambda: any(e == "request" for e, _ in a.events))
    request = next(d for e, d in a.events if e == "request")
    assert request["name"] == "Beto" and request["ids"] == [gid]
    a.client.grant(request["from"], request["ids"])
    settle(a, b, until=lambda: b.client.reservations.get(gid) == b.client.me)
    assert any(e == "message" and "liberou" in d["text"] for e, d in b.events)
    b.history.commit(cmd.edit_wall(b.doc, b.doc.get(gid), base_offset=3.2 - 3))
    settle(a, b)
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)
    # Recusa: o pedido volta como aviso.
    a.client.request([gid])
    settle(a, b, until=lambda: any(e == "request" for e, _ in b.events))
    req = next(d for e, d in b.events if e == "request")
    b.client.deny(req["from"], req["ids"])
    settle(a, b, until=lambda: any(e == "message" and "recusou" in d["text"]
                                   for e, d in a.events))


def test_eq05_simultaneas_terminam_iguais(pair, server):
    a, b = pair
    # Sem processar nada entre elas: as duas aplicam na hora e enviam.
    ga = [a.wall((0, i), (4, i)) for i in range(3)]
    gb = [b.wall((10, i), (14, i)) for i in range(3)]
    settle(a, b, until=lambda: all(b.doc.find(g) for g in ga)
           and all(a.doc.find(g) for g in gb))
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)
    assert ifc_equivalent(a.doc.ifc, server.doc.ifc)
    assert len(a.history.undo_stack) == len(b.history.undo_stack) == 3


def test_eq06_recusa_do_servidor_tira_do_desfazer(pair, server):
    a, b = pair
    gid = a.wall()
    settle(a, b)
    # B ainda não sabe da reserva de A (a guarda local passa); o servidor recusa.
    b.client.reservations.pop(gid, None)
    b.history.commit(cmd.edit_wall(b.doc, b.doc.get(gid), base_offset=3.3 - 3))
    assert b.history.undo_stack
    settle(a, b, until=lambda: any(e == "message" and "Recusado" in d["text"]
                                   for e, d in b.events))
    assert not b.history.undo_stack
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)
    assert ifc_equivalent(b.doc.ifc, server.doc.ifc)


def test_eq07_entrada_tardia_e_saida_libera(pair, server):
    a, b = pair
    gid = a.wall()
    settle(a, b)
    c = Peer(server, "Caio")
    assert c.doc.find(gid) is not None
    assert c.client.reservations.get(gid) == a.client.me
    assert ifc_equivalent(a.doc.ifc, c.doc.ifc)
    settle(a, b, c, until=lambda: len(b.client.users) == 3)
    a.client.close()
    settle(b, c, until=lambda: gid not in c.client.reservations and len(c.client.users) == 2)
    assert any(e == "users" and "Ana saiu" in d["event"] for e, d in c.events)
    c.client.close()


def test_eq08_descoberta_por_udp():
    base = Model()
    s = Server(base.doc.ifc.to_string(), project="Casa do Teste", host="pc-teste", port=0,
               udp_port=47896).start()
    try:
        found = discover(timeout=0.6, port=47896, targets=("127.0.0.1",))
    finally:
        s.stop()
    assert [f["project"] for f in found] == ["Casa do Teste"]
    assert found[0]["port"] == s.port


def test_eq09_desfazer_passa_por_todos(pair):
    a, b = pair
    gid = a.wall()
    settle(a, b, until=lambda: b.doc.find(gid) is not None)
    a.history.undo()
    settle(a, b, until=lambda: b.doc.find(gid) is None)
    a.history.redo()
    settle(a, b, until=lambda: b.doc.find(gid) is not None)
    assert ifc_equivalent(a.doc.ifc, b.doc.ifc)
    # B não desfaz o que é de A: a pilha de B está vazia.
    assert b.history.undo() is None


def test_eq10_encerrar_avisa_os_outros(server):
    a = Peer(server, "Ana")
    server.stop()
    end = time.monotonic() + 3
    while time.monotonic() < end and a.client.connected:
        a.client.poll()
        time.sleep(0.01)
    assert not a.client.connected
    assert any(e == "closed" for e, _ in a.events)
    # Desconectado, edita como cópia local.
    a.wall()
