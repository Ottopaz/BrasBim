# SPDX-License-Identifier: GPL-3.0-or-later
"""Barra da vista e organização: núcleo (``spec/ui/39-barra-da-vista-e-organizacao.md``
§10): VB07 (travar) e VB09 (ordem de desenho)."""

import ifcopenshell.util.element
import pytest
from conftest import snapshot
from estrutura import valid

from brasbim.core import edit_state, intervention, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError
from brasbim.core.walls.wall import read_state as read_wall


def _pset(element):
    return ifcopenshell.util.element.get_pset(element, edit_state.PSET, should_inherit=False)


def test_vb07_travar_no_ifc_e_recusa_no_nucleo(model, tmp_path):
    wall = model.wall((0, 0), (5, 0))
    other = model.wall((0, 3), (5, 3))
    model.commit(edit_state.lock(model.doc, [wall.GlobalId]))
    assert _pset(wall)[edit_state.LOCKED] is True
    assert edit_state.is_locked(model.doc, wall)
    # Gravado no arquivo e lido de volta (o mapa dos travados sai do IFC).
    reopened = model.reopen(tmp_path)
    rwall = reopened.by_guid(wall.GlobalId)
    assert ifcopenshell.util.element.get_pset(rwall, edit_state.PSET)[edit_state.LOCKED]

    before = snapshot(model.doc.ifc)
    refused = [
        lambda: transform.move_elements(model.doc, [wall.GlobalId, other.GlobalId], (0, 1)),
        lambda: delete_elements(model.doc, [wall.GlobalId])[0],
        lambda: intervention.set_situation(model.doc, [wall.GlobalId], "A_DEMOLIR"),
    ]
    for build in refused:
        with pytest.raises(OpError, match="elemento travado"):
            model.commit(build())
        assert snapshot(model.doc.ifc) == before  # nada muda, nem a outra parede
    assert read_wall(model.doc, other)["path"]["start"] == pytest.approx([0, 3])

    # Copiar o travado vale; a cópia não vem travada.
    tx = model.commit(transform.copy_elements(model.doc, [wall.GlobalId], (0, 6)))
    copies = [model.doc.find(op.id) for op in tx.ops if op.op == "wall.create"]
    assert copies and not any(edit_state.is_locked(model.doc, c) for c in copies)
    assert not any(_pset(c) for c in copies)

    # Junção com o travado continua sendo feita (é derivada).
    model.wall((5, 0), (5, 3))
    assert valid(model.doc.ifc)

    model.commit(edit_state.unlock(model.doc, [wall.GlobalId]))
    assert _pset(wall) is None and not edit_state.is_locked(model.doc, wall)
    model.history.undo()
    assert edit_state.is_locked(model.doc, wall)
    model.history.redo()
    model.commit(transform.move_elements(model.doc, [wall.GlobalId], (0, 1)))
    assert read_wall(model.doc, wall)["path"]["start"] == pytest.approx([0, 1])


def test_vb07_destravar_tudo_e_anotacao(model):
    wall = model.wall()
    tx = model.commit(ac.create_annotation(model.doc, "line2d", model.terreo,
                                           points=[[0, 6], [5, 6]]))
    line = model.doc.get(tx.ops[0].id)
    model.commit(edit_state.lock(model.doc, [wall.GlobalId, line.GlobalId]))
    with pytest.raises(OpError, match="elemento travado"):
        model.commit(transform.move_elements(model.doc, [line.GlobalId], (1, 0)))
    model.commit(edit_state.unlock_all(model.doc))
    assert not edit_state.locked_ids(model.doc)
    with pytest.raises(OpError):
        edit_state.unlock_all(model.doc)
    model.history.undo()
    assert edit_state.locked_ids(model.doc) == {wall.GlobalId, line.GlobalId}


def _lines(model, n):
    out = []
    for i in range(n):
        tx = model.commit(ac.create_annotation(model.doc, "line2d", model.terreo,
                                               points=[[0, i * 0.1], [5, i * 0.1]]))
        out.append(tx.ops[0].id)
    return out


def _items(model, gids):
    return [(g, edit_state.order_of(model.doc.get(g), "line")) for g in gids]


def test_vb09_ordem_de_desenho(model):
    a, b, c = _lines(model, 3)
    model.commit(edit_state.reorder(model.doc, _items(model, [a, b, c]), [a], "front"))
    assert _pset(model.doc.get(a))[edit_state.ORDER] == 101
    orders = dict(_items(model, [a, b, c]))
    assert orders[a] > orders[b] and orders[a] > orders[c]

    model.commit(edit_state.reorder(model.doc, _items(model, [a, b, c]), [a], "back"))
    orders = dict(_items(model, [a, b, c]))
    assert orders[a] < min(orders[b], orders[c])

    # Um passo à frente: troca com a seguinte que se sobrepõe (aqui só b). Com todas
    # sobrepostas, b e c empatam e o desempate por GlobalId (aleatório) decidia o teste.
    only_b = lambda g, h: h == b
    model.commit(edit_state.reorder(model.doc, _items(model, [a, b, c]), [a], "forward",
                                    overlaps=only_b))
    orders = dict(_items(model, [a, b, c]))
    assert orders[b] < orders[a] <= orders[c]

    model.commit(edit_state.reorder(model.doc, _items(model, [a, b, c]), [a], "backward",
                                    overlaps=only_b))
    orders = dict(_items(model, [a, b, c]))
    assert orders[a] < min(orders[b], orders[c])

    model.commit(edit_state.reorder(model.doc, _items(model, [a, b, c]), [a], "default"))
    assert _pset(model.doc.get(a)) is None
    model.history.undo()
    assert _pset(model.doc.get(a))[edit_state.ORDER] is not None
    assert valid(model.doc.ifc)
