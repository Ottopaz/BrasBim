# SPDX-License-Identifier: LGPL-3.0-or-later
"""Projeto com quase todos os elementos do BrasBim, para os testes de exportação."""

from conftest import Model
from estrutura import beam_type, column_type, slab_type
from test_objetos import bancada, cama, load, put

from brasbim.core import grids, terrain
from brasbim.core.annotations import commands as ac
from brasbim.core.fillings import commands as fc
from brasbim.core.structure import commands as sc
from brasbim.core.structure import coverings as cv
from brasbim.core.structure import railings, stairs
from brasbim.core.walls import commands as wc
from brasbim.core.walls import roof_top


def build() -> Model:
    m = Model()
    doc, t = m.doc, m.terreo
    m.commit(wc.create_rectangle(doc, m.type14, t, (0, 0), (8, 6)))
    inner = m.wall((4, 0), (4, 6))
    door_t = doc.get(m.commit(fc.create_door_type(doc, "P1", "SINGLE_SWING_LEFT")).ops[0].id)
    win_t = doc.get(m.commit(fc.create_window_type(doc, "J1")).ops[0].id)
    m.commit(fc.create_door(doc, door_t, inner, 2.0))
    front = min(doc.ifc.by_type("IfcWall"), key=lambda w: w.id())
    m.commit(fc.create_window(doc, win_t, front, 1.5))
    m.commit(sc.create_column(doc, column_type(m), t, (2, 3)))
    m.commit(sc.create_beam(doc, beam_type(m), t, (0, 3), (8, 3)))
    m.commit(sc.create_slab(doc, slab_type(m), m.superior, [(0, 0), (8, 0), (8, 6), (0, 6)]))
    roof_t = slab_type(m, "Telha", [{"material": "Telha cerâmica", "thickness": 0.05}], "ROOF")
    roof = doc.get(m.commit(sc.create_roof(doc, roof_t, m.superior,
                                           [(0, 0), (8, 0), (8, 6), (0, 6)])).ops[-1].id)
    upper = m.commit(wc.create_wall(doc, m.type14, m.superior, (0, 0), (0, 6)))
    m.commit(roof_top.attach(doc, [doc.get(upper.ops[0].id)], roof))
    for p in ((2, 1.5), (6, 1.5)):
        space = doc.get(m.commit(ac.create_space_in_room(doc, t, p)).ops[0].id)
        floor = doc.get(m.commit(cv.create_type(doc, f"Piso {p[0]}", [
            {"material": "Porcelanato", "thickness": 0.01}], "FLOORING")).ops[0].id)
        m.commit(cv.create_in_space(doc, floor, space))
    m.commit(stairs.create_stair(doc, t, (5, 4)))
    m.commit(railings.create_railing(doc, t, [(9, 0), (9, 4)]))
    put(m, load(m, cama(), "Cama casal"), (1, 4))
    put(m, load(m, bancada(), "Bancada"), (5, 0.5))
    m.commit(terrain.create_terrain(doc, [(-5, -5, 0), (15, -5, 0.5), (15, 12, 1.0),
                                          (-5, 12, 0.2)]))
    m.commit(grids.create_grid(doc, (0, 0), 0.0, [4, 4], [6]))
    m.commit(ac.create_dimension(doc, t, [(0, -1), (8, -1)]))
    return m
