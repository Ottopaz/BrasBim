# SPDX-License-Identifier: GPL-3.0-or-later
"""Área de seleção: núcleo (``spec/ui/38-area-de-selecao.md`` §8): AS01 a AS04."""

import pytest
from estrutura import slab_type, valid

from brasbim.core import plan, transform
from brasbim.core import selection_area as sa
from brasbim.core.annotations import commands as ac
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as wc
from brasbim.core.walls.wall import read_state as read_wall


def _touched(model, area):
    return sa.touched(plan.storey_plan(model.doc, model.terreo), area)


def test_as01_poligono_e_dentro():
    area = sa.Area(((0, 0), (4, 0), (4, 4), (2, 2), (0, 4)))
    assert area.contains((1, 1)) and area.contains((4, 2))  # dentro e na borda
    assert not area.contains((2, 3))  # no recorte em V
    assert not sa.valid([(0, 0), (1, 1), (2, 2)])
    assert sa.valid([(0, 0), (1, 0), (0, 1)])


def test_as02_esticar_parede_laje_e_linha(model):
    tx = model.commit(wc.create_wall(model.doc, model.type14, model.terreo, (0, 0), (5, 0)))
    wall = model.doc.get(tx.ops[0].id)
    model.commit(sc.create_slab(model.doc, slab_type(model), model.terreo,
                                [(0, 1), (5, 1), (5, 4), (0, 4)]))
    (slab,) = model.doc.ifc.by_type("IfcSlab")
    tx = model.commit(ac.create_annotation(model.doc, "line2d", model.terreo,
                                           points=[[0, 6], [5, 6]]))
    line = model.doc.get(tx.ops[0].id)
    far = model.commit(wc.create_wall(model.doc, model.type14, model.terreo, (0, 10),
                                      (2, 10)))
    area = sa.Area.rectangle((4, -1), (6, 7))
    gids = _touched(model, area)
    assert wall.GlobalId in gids and slab.GlobalId in gids and line.GlobalId in gids
    assert far.ops[0].id not in gids
    model.commit(transform.stretch_elements(model.doc, gids, area, (1.5, 0)))
    path = read_wall(model.doc, wall)["path"]
    assert path["start"] == pytest.approx([0, 0]) and path["end"] == pytest.approx([6.5, 0])
    outline = sc.read_state(model.doc, slab)["outline"]
    assert sorted(map(tuple, outline)) == [pytest.approx(p) for p in
                                            [(0, 1), (0, 4), (6.5, 1), (6.5, 4)]]
    pts = ac.read_state(model.doc, line)["points"]
    assert [tuple(p) for p in pts] == [pytest.approx((0, 6)), pytest.approx((6.5, 6))]
    assert valid(model.doc.ifc)


def test_as03_todo_dentro_anda_inteiro(model):
    tx = model.commit(wc.create_wall(model.doc, model.type14, model.terreo, (0, 0), (2, 0)))
    wall = model.doc.get(tx.ops[0].id)
    area = sa.Area.rectangle((-1, -1), (3, 1))
    model.commit(transform.stretch_elements(model.doc, _touched(model, area), area, (0, 3)))
    path = read_wall(model.doc, wall)["path"]
    assert path["start"] == pytest.approx([0, 3]) and path["end"] == pytest.approx([2, 3])


def test_as04_nada_a_esticar(model):
    model.commit(wc.create_wall(model.doc, model.type14, model.terreo, (0, 0), (5, 0)))
    area = sa.Area.rectangle((1, -1), (2, 1))  # pega a parede no meio, sem pontas
    gids = _touched(model, area)
    with pytest.raises(OpError):
        transform.stretch_elements(model.doc, gids, area, (1, 0))
