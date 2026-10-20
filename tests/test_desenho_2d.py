# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho 2D (spec/ui/19-desenho-2d.md §7): D2D01 a D2D07, no núcleo."""

import math

import pytest
from estrutura import check_history, valid

from brasbim.core import display_layers, plan, transform
from brasbim.core.annotations import base
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import drawing2d as d2
from brasbim.core.document import OpError
from brasbim.core.walls import commands as wc


def make(model, prefix, **fields):
    tx = model.commit(ac.create_annotation(model.doc, prefix, model.terreo, **fields))
    return model.doc.get(tx.ops[0].id)


def strokes(model, element):
    return base.build(model.doc, element).strokes


def texts(model, element):
    return [t.text for t in base.build(model.doc, element).texts]


def layer(model, element):
    return display_layers.layer_name(model.doc, display_layers.layer_of(model.doc, element))


def test_d2d01_circulo(model):
    def create():
        make(model, "circle2d", center=[2, 3], radius=1.5)

    check_history(model, create)
    (c,) = [e for e in model.doc.ifc.by_type("IfcAnnotation") if base.kind_of(e) is d2.CIRCLE]
    (st,) = strokes(model, c)
    assert st.closed
    assert all(math.dist(p, (2, 3)) == pytest.approx(1.5) for p in st.points)
    assert layer(model, c) == "Linhas e hachuras"
    model.commit(transform.move_elements(model.doc, [c.GlobalId], (1, 0)))
    assert base.read_state(c)["center"] == pytest.approx([3, 3])
    model.commit(transform.copy_elements(model.doc, [c.GlobalId], (0, 5)))
    assert len([e for e in model.doc.ifc.by_type("IfcAnnotation")
                if base.kind_of(e) is d2.CIRCLE]) == 2
    with pytest.raises(OpError):
        ac.create_annotation(model.doc, "circle2d", model.terreo, center=[0, 0], radius=0)
    assert valid(model.doc.ifc)


def test_d2d02_arco_por_tres_pontos(model):
    fields = d2.arc_from_points((1, 0), (0, 1), (-1, 0))
    assert fields["center"] == pytest.approx([0, 0], abs=1e-9)
    assert fields["radius"] == pytest.approx(1.0)
    a = make(model, "arc2d", **fields)
    (st,) = strokes(model, a)
    assert any(math.dist(p, (0, 1)) < 0.05 for p in st.points)  # passa pelo ponto do meio
    assert all(p[1] >= -1e-9 for p in st.points)
    # o outro sentido: ponto do meio embaixo
    other = d2.arc_from_points((1, 0), (0, -1), (-1, 0))
    o = make(model, "arc2d", **other)
    assert all(p[1] <= 1e-9 for p in strokes(model, o)[0].points)
    # espelhar pelo eixo x: o arco de cima vira o de baixo, mesmo desenho
    model.commit(transform.mirror_elements(model.doc, [a.GlobalId], (0, 0), (1, 0)))
    assert all(p[1] <= 1e-9 for p in strokes(model, a)[0].points)
    with pytest.raises(OpError, match="alinhados"):
        d2.arc_from_points((0, 0), (1, 0), (2, 0))


def test_d2d03_curva_livre(model):
    pts = [[0, 0], [1, 1], [2, 0], [3, 1]]
    c = make(model, "spline2d", points=pts)
    (st,) = strokes(model, c)
    for p in pts:
        assert min(math.dist(p, q) for q in st.points) < 1e-9
    closed = make(model, "spline2d", points=pts, closed=True)
    assert strokes(model, closed)[0].closed


def test_d2d04_cota_de_raio_presa(model):
    c = make(model, "circle2d", center=[0, 0], radius=1.2)
    r = make(model, "radius_dim", center=[0, 0], radius=1.2, angle=30, ref=c.GlobalId)
    assert texts(model, r) == ["R 1,20"]
    assert layer(model, r) == "Cotas"

    def grow():
        model.commit(ac.edit_element(model.doc, c, radius=2.0))

    check_history(model, grow)
    assert texts(model, r) == ["R 2,00"]
    d = make(model, "radius_dim", center=[0, 0], radius=2.0, diameter=True, ref=c.GlobalId)
    assert texts(model, d) == ["Ø 4,00"]
    found = d2.curves_near(model.doc, model.terreo, (2.0, 0.0), 0.1)
    assert found and found[0][0] == c.GlobalId


def test_d2d04b_cota_de_raio_em_parede_em_arco(model):
    tx = model.commit(wc.create_arc_wall(model.doc, model.type14, model.terreo, (0, 0),
                                         (2, 2), (4, 0)))
    wall = model.doc.get(next(op.id for op in tx.ops if op.op == "wall.create"))
    found = d2.curve_of(model.doc, wall.GlobalId)
    assert found is not None
    center, radius = found
    assert center == pytest.approx((2, 0), abs=1e-6) and radius == pytest.approx(2.0)
    r = make(model, "radius_dim", center=list(center), radius=radius, angle=90,
             ref=wall.GlobalId)
    assert texts(model, r) == ["R 2,00"]


def test_d2d05_cota_de_angulo(model):
    a = make(model, "angle_dim", vertex=[0, 0], a=[2, 0], b=[0, 2], radius=1.0)
    assert texts(model, a) == ["90,0°"]
    b = make(model, "angle_dim", vertex=[0, 0], a=[2, 0], b=[1, 1], radius=0.8)
    assert texts(model, b) == ["45,0°"]
    arc = strokes(model, b)[0]
    assert all(math.dist(p, (0, 0)) == pytest.approx(0.8) for p in arc.points)


def test_d2d06_rotulo(model):
    wall = model.wall((0, 0), (5, 0))
    lab = make(model, "label", at=[2, 0], text_at=[3, 1], ref=wall.GlobalId, field="type")
    assert texts(model, lab) == ["Alvenaria 14"]
    assert layer(model, lab) == "Textos e rótulos"
    model.commit(wc.create_wall_type(model.doc, "Drywall 10", [
        {"material": "Gesso acartonado", "thickness": 0.1}]))
    other = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Drywall 10")
    model.commit(wc.edit_wall(model.doc, wall, type=other))
    assert texts(model, lab) == ["Drywall 10"]
    free = make(model, "label", at=[1, 1], text_at=[2, 2], text="Bancada de granito")
    assert texts(model, free) == ["Bancada de granito"]
    with pytest.raises(OpError):
        ac.create_annotation(model.doc, "label", model.terreo, at=[0, 0], text_at=[1, 1])


def test_d2d07_marcador_de_alteracao(model):
    first = make(model, "revision", outline=[[0, 0], [3, 0], [3, 2], [0, 2]],
                 number=d2.next_revision(model.doc))
    assert base.read_state(first)["number"] == "1"
    assert d2.next_revision(model.doc) == "2"
    cloud, tag = strokes(model, first)
    assert cloud.closed and len(cloud.points) > 20 and tag.closed
    assert texts(model, first) == ["1"]
    assert layer(model, first) == "Símbolos"
    p = plan.storey_plan(model.doc, model.terreo)
    assert first.GlobalId in {owner for owner, _ in p.annotations}
    assert valid(model.doc.ifc)
