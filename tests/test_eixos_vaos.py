# SPDX-License-Identifier: LGPL-3.0-or-later
"""Eixos, vão e nicho, claraboia (spec/ui/20-eixos-vaos-claraboia.md §5): EV01 a EV05."""

import math

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import bounds, check_history, created, slab_type, valid

from brasbim.core import grids, plan, snap, transform
from brasbim.core.delete import delete_elements
from brasbim.core.structure import commands as sc
from brasbim.core.structure import roofs, skylights
from brasbim.core.walls import commands as wc
from brasbim.core.walls import openings


def _grid(model, u=(5, 4), v=(6,), **options):
    return created(model, grids.create_grid(model.doc, (0, 0), 0.0, list(u), list(v),
                                            **options))


def test_ev01_eixos(model):
    def create():
        _grid(model)

    check_history(model, create)
    (g,) = model.doc.ifc.by_type("IfcGrid")
    assert ue.get_container(g) == model.doc.building
    assert [a.AxisTag for a in g.UAxes] == ["1", "2", "3"]
    assert [a.AxisTag for a in g.VAxes] == ["A", "B"]
    xs = [a.AxisCurve.Points[0].Coordinates[0] for a in g.UAxes]
    assert xs == pytest.approx([0, 5, 9])
    model.commit(grids.edit_grid(model.doc, g, u=grids.axes_from_spacings([3, 3, 3])))
    assert [a.AxisTag for a in g.UAxes] == ["1", "2", "3", "4"]
    assert grids.letters(26) == "AA"
    model.commit(transform.rotate_elements(model.doc, [g.GlobalId], (0, 0), math.pi / 2))
    assert grids.read_state(g)["angle"] == pytest.approx(90.0)
    assert valid(model.doc.ifc)


def test_ev02_eixos_em_todo_pavimento_e_snap(model):
    g = _grid(model)
    for storey in (model.terreo, model.superior):
        p = plan.storey_plan(model.doc, storey)
        assert g.GlobalId in {owner for owner, _ in p.annotations}
    points = grids.intersections(grids.read_state(g))
    assert (5.0, 6.0) in [(round(q[0], 6), round(q[1], 6)) for q in points]
    found = snap.snap([], (5.04, 5.97), 0.1, 0.1, points)
    assert found.point == pytest.approx((5.0, 6.0))


def test_ev03_vao_e_nicho(model):
    wall = model.wall((0, 0), (6, 0))
    model.commit(wc.create_opening(model.doc, wall, 1.0, 0.9, 2.1))
    model.commit(wc.create_opening(model.doc, wall, 3.0, 0.6, 0.6, sill=1.0, kind="RECESS",
                                   depth=0.05, side="left"))
    found = openings.of_wall(wall)
    assert {o.PredefinedType for o in found} == {"OPENING", "RECESS"}
    p = plan.storey_plan(model.doc, model.terreo)
    boxes = p.owners("opening_box")
    assert set(boxes) == {o.GlobalId for o in found}
    vao = next(o for o in found if o.PredefinedType == "OPENING")
    assert p.pick((1.45, -0.07), 0.02) == vao.GlobalId or \
        p.pick((1.45, 0.07), 0.02) == vao.GlobalId
    model.commit(wc.edit_opening(model.doc, vao, width=1.2))
    assert openings.read_state(vao)["width"] == pytest.approx(1.2)
    before = snapshot(model.doc.ifc)
    tx, _ = delete_elements(model.doc, [vao.GlobalId])
    model.commit(tx)
    assert len(openings.of_wall(wall)) == 1
    model.history.undo()
    assert snapshot(model.doc.ifc) == before


def _slab(model):
    t = slab_type(model)
    return created(model, sc.create_slab_rectangle(model.doc, t, model.terreo, (0, 0), (6, 4)))


def test_ev04_claraboia_na_laje(model):
    slab = _slab(model)

    def create():
        model.commit(skylights.create_skylight(model.doc, model.terreo, (3, 2), 1.0, 1.5))

    check_history(model, create)
    (w,) = skylights.all_skylights(model.doc)
    assert w.PredefinedType == "SKYLIGHT"
    opening = w.FillsVoids[0].RelatingOpeningElement
    assert opening.VoidsElements[0].RelatingBuildingElement == slab
    low, high = bounds(w)
    assert low[2] == pytest.approx(0.0, abs=1e-6)  # o topo da laje (top_offset 0)
    assert (high[0] - low[0], high[1] - low[1]) == pytest.approx((1.0, 1.5))
    assert ue.get_pset(w, "Pset_WindowCommon")["Reference"] == "CL1"
    # a laje que sobe leva a claraboia
    model.commit(sc.edit_element(model.doc, slab, top_offset=0.5))
    assert bounds(w)[0][2] == pytest.approx(0.5, abs=1e-6)
    # a laje que sai leva a claraboia
    before = snapshot(model.doc.ifc)
    tx, _ = delete_elements(model.doc, [slab.GlobalId])
    model.commit(tx)
    assert not skylights.all_skylights(model.doc)
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    with pytest.raises(Exception, match="fora|laje ou uma cobertura"):
        skylights.create_skylight(model.doc, model.terreo, (20, 20))
    assert valid(model.doc.ifc)


def test_ev05_claraboia_na_cobertura(model):
    t = slab_type(model, "Telha cerâmica", [{"material": "Telha cerâmica", "thickness": 0.05}],
                  "ROOF")
    roof = created(model, sc.create_roof(model.doc, t, model.terreo,
                                         [(0, 0), (10, 0), (10, 6), (0, 6)], base_height=2.8))
    model.commit(skylights.create_skylight(model.doc, model.terreo, (5, 1.5)))
    (w,) = skylights.all_skylights(model.doc)
    part = w.FillsVoids[0].RelatingOpeningElement.VoidsElements[0].RelatingBuildingElement
    assert part in roofs.parts_of(roof)
    low, high = bounds(w)
    assert high[2] - low[2] > 0.15  # inclinada: o caixilho sobe com a água
    model.commit(transform.move_elements(model.doc, [roof.GlobalId], (2, 0)))
    assert skylights.read_state(w)["center"] == pytest.approx([7, 1.5])
    assert valid(model.doc.ifc)
