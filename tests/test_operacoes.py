# SPDX-License-Identifier: LGPL-3.0-or-later
"""Operações serializáveis e desfazer/refazer (spec da parede §5.2, P14, P15)."""

import json

import pytest
from conftest import PROJECT_ID, Model, snapshot

from brasbim.core.document import Document, OpError
from brasbim.core.ops import History, Op, Transaction
from brasbim.core.walls import commands as cmd


def _session(m: Model):
    """Sequência de ações cobrindo criar, editar e excluir."""
    a = m.wall((0, 0), (5, 0))
    m.wall((5, 0), (5, 4), ref_line="axis", flip_layers=True)
    m.commit(cmd.create_arc_wall(m.doc, m.type14, m.terreo, (0, 0), (-2, 2), (0, 4)))
    m.commit(cmd.edit_wall(m.doc, a, base_offset=0.1, common={"IsExternal": True}))
    m.commit(cmd.edit_storey(m.doc, m.superior, elevation=3.0))
    m.commit(cmd.delete_wall(m.doc, a))


def test_op_serializa_em_json():
    op = Op("wall.edit", "abc", before={"base_offset": 0.0}, after={"base_offset": 0.1})
    tx = Transaction("Editar", [op])
    again = Transaction.from_dict(json.loads(json.dumps(tx.to_dict())))
    assert again == tx
    assert "data" not in tx.to_dict()["ops"][0]


def test_p14_cada_acao_gera_as_operacoes_esperadas(model):
    tx = cmd.create_wall(model.doc, model.type14, model.terreo, (0, 0), (5, 0))
    assert [op.op for op in tx.ops] == ["wall.create"]
    data = tx.ops[0].data
    assert data["type"] == model.type14.GlobalId
    assert data["storey"] == model.terreo.GlobalId
    assert data["path"] == {"kind": "line", "start": [0, 0], "end": [5, 0]}
    model.commit(tx)
    wall = model.doc.get(tx.ops[0].id)
    edit = cmd.edit_wall(model.doc, wall, fixed_height=3.0, top_mode="fixed")
    assert [op.op for op in edit.ops] == ["wall.edit"]
    assert edit.ops[0].before == {"fixed_height": 2.8, "top_mode": "storey"}
    assert [op.op for op in cmd.delete_wall(model.doc, wall).ops] == ["wall.delete"]


def test_p14_desfazer_e_refazer_reproduzem_o_ifc(model):
    states = [snapshot(model.doc.ifc)]
    m = model
    a = m.wall((0, 0), (5, 0))
    states.append(snapshot(m.doc.ifc))
    m.commit(cmd.edit_wall(m.doc, a, ref_line="axis", flip_layers=True))
    states.append(snapshot(m.doc.ifc))
    m.commit(cmd.edit_storey(m.doc, m.superior, elevation=3.2))
    states.append(snapshot(m.doc.ifc))
    m.commit(cmd.delete_wall(m.doc, a))
    states.append(snapshot(m.doc.ifc))

    for expected in reversed(states[:-1]):
        m.history.undo()
        assert snapshot(m.doc.ifc) == expected
    for _ in range(3):
        m.history.undo()  # dois pavimentos e o tipo
    assert m.history.undo() is None
    for _ in range(3):
        m.history.redo()
    assert snapshot(m.doc.ifc) == states[0]
    for expected in states[1:]:
        m.history.redo()
        assert snapshot(m.doc.ifc) == expected


def test_p15_reaplicar_diario_reproduz_o_ifc():
    m = Model()
    _session(m)
    m.history.undo()
    m.history.redo()
    m.history.undo()
    journal = json.loads(json.dumps([tx.to_dict() for tx in m.history.journal]))

    other = Document.new(project_id=PROJECT_ID)
    history = History(other)
    for tx in journal:
        history.commit(Transaction.from_dict(tx))
    assert snapshot(other.ifc) == snapshot(m.doc.ifc)


def test_transacao_falha_inteira(model):
    a = model.wall()
    before = snapshot(model.doc.ifc)
    good = cmd.edit_wall(model.doc, a, base_offset=0.5).ops[0]
    bad = Op("wall.edit", a.GlobalId, before={"base_offset": 0.5}, after={"ref_line": "x"})
    with pytest.raises(OpError):
        model.commit(Transaction("Misto", [good, bad]))
    assert snapshot(model.doc.ifc) == before
    assert len(model.history.undo_stack) == 4


def test_edicao_em_conflito_e_rejeitada(model):
    a = model.wall()
    stale = cmd.edit_wall(model.doc, a, base_offset=0.2)
    model.commit(cmd.edit_wall(model.doc, a, base_offset=0.3))
    with pytest.raises(OpError, match="base_offset"):
        model.commit(stale)


def test_globalid_repetido_e_rejeitado(model):
    a = model.wall()
    tx = cmd.create_wall(model.doc, model.type14, model.terreo, (0, 1), (5, 1))
    tx.ops[0].id = a.GlobalId
    with pytest.raises(OpError):
        model.commit(tx)
