# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cortes e fachadas (spec/ui 14 §8): CF01 a CF08, no núcleo."""

import pytest
from estrutura import check_history, created, slab_type, valid

from brasbim.core import plan, transform
from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import section, views
from brasbim.core.fillings import commands as fc
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd


@pytest.fixture
def casa(model):
    """Retângulo de paredes (0, 0)–(6, 4), porta na parede de baixo, laje no Superior."""
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (6, 4)))
    created(model, sc.create_slab_rectangle(model.doc, slab_type(model), model.superior,
                                            (0, 0), (6, 4)))
    bottom = _wall(model, 1, 0)
    model.commit(fc.create_door_type(model.doc, "P1", defaults={"width": 0.8}))
    (door_type,) = model.doc.ifc.by_type("IfcDoorType")
    model.commit(fc.create_door(model.doc, door_type, bottom, 1.0))
    return model


def _wall(model, axis: int, value: float):
    """Parede com as duas pontas na coordenada ``axis`` = ``value``."""
    for w in model.doc.ifc.by_type("IfcWall"):
        path = cmd.read_state(model.doc, w)["path"]
        if abs(path["start"][axis] - value) < 1e-9 and abs(path["end"][axis] - value) < 1e-9:
            return w
    raise LookupError(value)


def _cut(model, a=(3, -1), b=(3, 5), side="left"):
    return created(model, ac.create_view(model.doc, "section", a, b, side))


def _box(rings):
    pts = [p for r in rings for p in r]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _outlines(drawing, cls, doc):
    return [it for it in drawing.cuts() if it.weight and doc.get(it.owner).is_a(cls)]


def test_cf01_corte(casa):
    model = casa
    view = _cut(model)
    assert view.ObjectType == "VistaDeCorte"
    assert views.read_state(view)["letter"] == "A"
    d = section.draw(model.doc, view)
    walls = sorted(_box(it.rings) for it in _outlines(d, "IfcWall", model.doc))
    assert len(walls) == 2
    assert walls[0] == pytest.approx((1.0, 0.0, 1.14, 2.70))
    assert walls[1] == pytest.approx((4.86, 0.0, 5.0, 2.70))
    (slab,) = _outlines(d, "IfcSlab", model.doc)
    assert _box(slab.rings) == pytest.approx((1.0, 2.70, 5.0, 2.80))


def test_cf02_camadas_da_parede(casa):
    d = section.draw(casa.doc, _cut(casa))
    owner = _outlines(d, "IfcWall", casa.doc)[0].owner
    layers = [it for it in d.cuts(owner) if not it.weight]
    assert len(layers) == 3


def test_cf03_vista_alem_do_corte(casa):
    d = section.draw(casa.doc, _cut(casa))
    left = _wall(casa, 0, 0)
    faces = [it for it in d.items if it.kind == "face" and it.owner == left.GlobalId]
    assert faces
    first_cut = next(i for i, it in enumerate(d.items) if it.kind == "cut")
    assert all(d.items.index(f) < first_cut for f in faces)  # os cortes ficam por cima
    assert d.pick((3.0, 1.5)) == left.GlobalId


def test_cf04_niveis_e_titulo(casa):
    d = section.draw(casa.doc, _cut(casa))
    texts = [t.text for t in d.texts]
    assert any(t.startswith("+0,00") for t in texts)
    assert any(t.startswith("+2,80") for t in texts)
    assert "CORTE A" in texts and "ESC. 1:50" in texts


def test_cf05_fachada(casa):
    view = created(casa, ac.create_view(casa.doc, "elevation", (7, -2), (-1, -2), "right"))
    assert view.ObjectType == "VistaDeFachada"
    d = section.draw(casa.doc, view)
    assert not d.cuts()
    doors = {d.GlobalId for d in casa.doc.ifc.by_type("IfcDoor")}
    assert any(it.owner in doors for it in d.items)


def test_cf06_corte_acompanha_o_modelo(casa):
    model = casa
    view = _cut(model)
    top = _wall(model, 1, 4)
    model.commit(transform.move_elements(model.doc, [top], (0, 1)))
    walls = sorted(_box(it.rings) for it in _outlines(section.draw(model.doc, view),
                                                      "IfcWall", model.doc))
    assert walls[-1][2] == pytest.approx(6.0)
    model.history.undo()
    walls = sorted(_box(it.rings) for it in _outlines(section.draw(model.doc, view),
                                                      "IfcWall", model.doc))
    assert walls[-1][2] == pytest.approx(5.0)


def test_cf07_simbolo_nas_plantas(casa):
    view = _cut(casa)
    for storey in (casa.terreo, casa.superior):
        p = plan.storey_plan(casa.doc, storey)
        owned = [prims for gid, prims in p.annotations if gid == view.GlobalId]
        assert owned and [t.text for t in owned[0].texts] == ["A", "A"]
    arrows = views.symbol(views.read_state(view)).strokes
    (x0, y0), (x1, y1) = arrows[3].points  # seta do ponto A
    assert x1 < x0 and y1 == pytest.approx(y0)  # aponta para −x


def test_cf08_validacao_e_diario(casa, tmp_path):
    model = casa

    def action():
        view = _cut(model)
        created(model, ac.create_view(model.doc, "elevation", (7, -2), (-1, -2), "right"))
        model.commit(transform.move_elements(model.doc, [view], (0.5, 0)))
        model.commit(transform.copy_elements(model.doc, [view], (1, 0)))
        model.commit(ac.edit_element(model.doc, view, depth=2.0))

    check_history(model, action)
    assert sorted(views.read_state(v)["name"] for v in views.all_views(model.doc)) == [
        "Corte A", "Corte B", "Fachada 1"]
    assert valid(model.reopen(tmp_path))
