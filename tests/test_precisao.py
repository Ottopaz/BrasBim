# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pacote de precisão (spec/ui/23-precisao.md §11), no núcleo: PR01 a PR05, PR08 a PR12."""

import math

import pytest
from estrutura import slab_type, valid

from brasbim.core import display_layers as dl
from brasbim.core import edits, plan, snap
from brasbim.core import select_similar as ss
from brasbim.core.annotations import base, drafting, reference
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import drawing2d as d2
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.structure import slabs
from brasbim.core.walls import commands as wc


def make(model, prefix, **fields):
    tx = model.commit(ac.create_annotation(model.doc, prefix, model.terreo, **fields))
    return model.doc.get(tx.ops[0].id)


def line(model, *points, closed=False):
    return make(model, "line2d", points=[list(p) for p in points], closed=closed)


def index(model):
    p = plan.storey_plan(model.doc, model.terreo)
    return snap.build_index(model.doc, model.terreo, p)


def at(model, p, tol=0.1, origin=None, kinds=None, walls=None):
    walls = snap.wall_paths(model.doc, model.terreo) if walls is None else walls
    return snap.snap(walls, p, tol, 0.1, (), index(model), origin, kinds)


def _layer_id(doc, name):
    return next(x["id"] for x in dl.read_config(doc)["layers"] if x["name"] == name)


def test_pr01_indice_de_todos_os_elementos(model):
    model.commit(sc.create_slab(model.doc, slab_type(model), model.terreo,
                                [(10, 0), (14, 0), (14, 3), (10, 3)]))
    line(model, (0, 5), (4, 5))
    make(model, "reference2d", name="Levantamento", source="x.dxf", layer="A",
         **reference.pack_lines([{"points": [[20, 0], [24, 0]], "closed": False,
                                  "z": None}]),
         texts=[], points=[])
    s = at(model, (14.03, 2.98))
    assert (s.kind, s.point) == ("end", pytest.approx((14, 3)))
    assert at(model, (12.02, 0.03)).kind == "mid"  # meio do lado da laje
    assert at(model, (2.02, 5.01)).point == pytest.approx((2, 5))
    assert at(model, (23.97, 0.02)).point == pytest.approx((24, 0))  # desenho importado
    # oculto não atrai; bloqueado atrai
    lines = _layer_id(model.doc, "Linhas e hachuras")
    model.doc.display = dl.Display(hidden=frozenset({lines}))
    assert at(model, (2.02, 5.01)).kind == "grid"
    model.doc.display = dl.Display(locked=frozenset({lines}))
    assert at(model, (2.02, 5.01)).kind == "mid"


def test_pr02_intersecao(model):
    line(model, (0, 0), (4, 4))
    line(model, (0, 4), (4, 0))
    s = at(model, (2.04, 1.97))
    assert (s.kind, s.point) == ("inter", pytest.approx((2, 2)))


def test_pr03_centro(model):
    make(model, "circle2d", center=[3, 3], radius=1.0)
    s = at(model, (3.02, 2.97))
    assert (s.kind, s.point) == ("center", pytest.approx((3, 3)))
    a = make(model, "arc2d", **d2.arc_from_points((10, 0), (11, 1), (12, 0)))
    assert base.read_state(a)["radius"] == pytest.approx(1.0)
    s = at(model, (11.02, 1.03))
    assert (s.kind, s.point) == ("mid", pytest.approx((11, 1)))
    s = at(model, (11.03, 0.02))
    assert (s.kind, s.point) == ("center", pytest.approx((11, 0)))
    # parede em arco: centro do eixo
    from brasbim.core.walls import commands as wc

    t = model.doc.ifc.by_type("IfcWallType")[0]
    model.commit(wc.create_arc_wall(model.doc, t, model.terreo, (20, 0), (21, 1), (22, 0)))
    s = at(model, (21.02, 0.02))
    assert (s.kind, s.point) == ("center", pytest.approx((21, 0), abs=1e-6))


def test_pr04_perpendicular_e_tangente(model):
    line(model, (0, 0), (10, 0))
    s = at(model, (3.05, 0.03), origin=(3, 4))
    assert (s.kind, s.point) == ("perp", pytest.approx((3, 0)))
    assert at(model, (3.05, 0.03)).kind == "near"  # sem ponto anterior
    make(model, "circle2d", center=[20, 0], radius=1.0)
    origin = (20, 2)  # tangentes em (±0,866, 0,5) a partir do centro
    q = (20 + math.sqrt(3) / 2, 0.5)
    s = at(model, (q[0] + 0.02, q[1] - 0.02), origin=origin)
    assert (s.kind, s.point) == ("tan", pytest.approx(q))
    assert at(model, (q[0] + 0.02, q[1] - 0.02)).kind == "near"


def test_pr05_prioridade_e_tipos_ligados(model):
    line(model, (0, 0), (4, 0))
    assert at(model, (0.04, 0.03)).kind == "end"  # vence a borda, que está mais perto
    kinds = set(snap.KINDS) - {"end"}
    assert at(model, (0.04, 0.03), kinds=kinds).kind == "near"
    assert at(model, (2.0, 3.0), kinds=set(snap.KINDS) - {"grid"}).kind == "free"
    # arco aproximado: os vértices internos não viram extremidade
    make(model, "circle2d", center=[10, 0], radius=2.0)
    st = base.build(model.doc, model.doc.ifc.by_type("IfcAnnotation")[-1]).strokes[0]
    inner = st.points[5]
    assert at(model, (inner[0] + 0.01, inner[1])).kind == "near"


# --- edições (§4–§7) ---------------------------------------------------------------------


def _points(element):
    return [tuple(q) for q in base.read_state(element)["points"]]


def _flat(points):
    """Pontos em lista plana: o ``pytest.approx`` não aceita listas de pares."""
    return [c for q in points for c in q]


def _lines(model):
    return [e for e in model.doc.ifc.by_type("IfcAnnotation")
            if base.kind_of(e) is drafting.LINE]


def _path(model, wall):
    return wc.read_state(model.doc, wall)["path"]


def _joined(model, a, b) -> bool:
    return any({r.RelatingElement.GlobalId, r.RelatedElement.GlobalId} ==
               {a.GlobalId, b.GlobalId}
               for r in model.doc.ifc.by_type("IfcRelConnectsPathElements"))


def test_pr08_deslocar_paralela(model):
    wall = model.wall((0, 0), (5, 0))
    tx = model.commit(edits.offset_element(model.doc, wall, 0.5, (2, 3)))
    new = model.doc.get(tx.ops[0].id)
    assert new.is_a("IfcWall")
    assert _path(model, new)["start"] == pytest.approx([0, 0.5])
    assert _path(model, new)["end"] == pytest.approx([5, 0.5])
    assert wc.read_state(model.doc, new)["type"] == wc.read_state(model.doc, wall)["type"]
    model.commit(edits.offset_element(model.doc, wall, 0.2, (2, -1), copy=False))
    assert _path(model, wall)["start"] == pytest.approx([0, -0.2])
    assert len(model.doc.ifc.by_type("IfcWall")) == 2
    # linha 2D (para dentro do canto), círculo e contorno de laje
    line(model, (0, 10), (4, 10), (4, 14))
    model.commit(edits.offset_element(model.doc, _lines(model)[0], 1.0, (2, 12)))
    assert _flat(_points(_lines(model)[-1])) == pytest.approx([0, 11, 3, 11, 3, 14])
    c = make(model, "circle2d", center=[20, 0], radius=1.0)
    model.commit(edits.offset_element(model.doc, c, 0.25, (22, 0), copy=False))
    assert base.read_state(c)["radius"] == pytest.approx(1.25)
    with pytest.raises(OpError, match="raio"):
        edits.offset_element(model.doc, c, 2.0, (20.1, 0))
    model.commit(sc.create_slab(model.doc, slab_type(model), model.terreo,
                                [(30, 0), (34, 0), (34, 4), (30, 4)]))
    (slab,) = model.doc.ifc.by_type("IfcSlab")
    model.commit(edits.offset_element(model.doc, slab, 0.5, (35, 2)))
    outlines = [_flat(sorted(map(tuple, slabs.read_state(model.doc, s)["outline"])))
                for s in model.doc.ifc.by_type("IfcSlab")]
    assert pytest.approx([29.5, -0.5, 29.5, 4.5, 34.5, -0.5, 34.5, 4.5]) in outlines
    assert valid(model.doc.ifc)


def test_pr09_aparar_e_estender_linhas(model):
    target = line(model, (0, 0), (10, 0))
    left = line(model, (3, -1), (3, 1))
    line(model, (6, -1), (6, 1))
    model.commit(edits.trim_extend(model.doc, target, (4.5, 0), index(model)))
    pieces = sorted(_points(e) for e in _lines(model) if _points(e)[0][1] == 0)
    assert pieces == [[(0, 0), (3, 0)], [(6, 0), (10, 0)]]
    # a sobra além do cruzamento
    model.commit(edits.trim_extend(model.doc, left, (3, 0.8), index(model)))
    assert _flat(_points(left)) == pytest.approx([3, -1, 3, 0])
    loose = line(model, (0, 5), (2, 5))
    line(model, (8, 3), (8, 7))
    model.commit(edits.trim_extend(model.doc, loose, (1.8, 5), index(model)))
    assert _points(loose)[-1] == pytest.approx((8, 5))
    alone = line(model, (0, 20), (1, 20))
    with pytest.raises(OpError, match="nada para aparar"):
        edits.trim_extend(model.doc, alone, (0.9, 20), index(model))


def test_pr10_aparar_e_estender_parede(model):
    a = model.wall((0, 0), (6, 0))
    b = model.wall((4, -2), (4, 2))  # atravessa a: a sobra de a vai de 4 a 6
    model.commit(edits.trim_extend(model.doc, a, (5.5, 0), index(model)))
    assert _path(model, a)["end"] == pytest.approx([4, 0])
    assert _joined(model, a, b), "a junção se forma ao aparar até o eixo"
    c = model.wall((0, 5), (2, 5))
    d = model.wall((7, 3), (7, 8))
    model.commit(edits.trim_extend(model.doc, c, (1.9, 5), index(model)))
    assert _path(model, c)["end"] == pytest.approx([7, 5])
    assert _joined(model, c, d), "junção T ao estender até o eixo"
    assert valid(model.doc.ifc)


def test_pr11_concordar(model):
    h = line(model, (0, 0), (4, 0))
    v = line(model, (5, 1), (5, 4))
    model.commit(edits.fillet(model.doc, h, (1, 0), v, (5, 3)))
    assert _points(h)[-1] == pytest.approx((5, 0))
    assert _points(v)[0] == pytest.approx((5, 0))
    w1 = model.wall((10, 0), (14, 0))
    w2 = model.wall((15, 1), (15, 4))
    model.commit(edits.fillet(model.doc, w1, (11, 0), w2, (15, 3)))
    assert _path(model, w1)["end"] == pytest.approx([15, 0])
    assert _path(model, w2)["start"] == pytest.approx([15, 0])
    assert _joined(model, w1, w2)
    h2 = line(model, (20, 0), (24, 0))
    v2 = line(model, (25, 1), (25, 4))
    model.commit(edits.fillet(model.doc, h2, (21, 0), v2, (25, 3), radius=0.3))
    assert _points(h2)[-1] == pytest.approx((24.7, 0))
    assert _points(v2)[0] == pytest.approx((25, 0.3))
    (arc,) = [e for e in model.doc.ifc.by_type("IfcAnnotation") if base.kind_of(e) is d2.ARC]
    st = base.read_state(arc)
    assert st["radius"] == pytest.approx(0.3)
    assert st["center"] == pytest.approx([24.7, 0.3])
    p1, p2 = line(model, (0, 30), (4, 30)), line(model, (0, 31), (4, 31))
    with pytest.raises(OpError, match="paralelas"):
        edits.fillet(model.doc, p1, (1, 30), p2, (1, 31))
    assert valid(model.doc.ifc)


def test_pr12_selecionar_semelhantes(model):
    w1 = model.wall((0, 0), (5, 0))
    w2 = model.wall((0, 3), (5, 3))
    tx = model.commit(wc.create_wall_type(model.doc, "Concreto 20", [
        {"material": "Concreto", "thickness": 0.2, "category": "LoadBearing",
         "priority": 90}]))
    other = model.doc.get(tx.ops[0].id)
    tx = model.commit(wc.create_wall(model.doc, other, model.terreo, (0, 6), (5, 6)))
    w3 = model.doc.get(tx.ops[0].id)
    up = model.commit(wc.create_wall(model.doc, model.type14, model.superior, (0, 0), (5, 0)))
    ln = line(model, (0, 9), (4, 9))
    st, ids = model.terreo, (lambda *ws: sorted(w.GlobalId for w in ws))
    assert ss.similar(model.doc, st, [w1.GlobalId], "class") == ids(w1, w2, w3)
    assert ss.similar(model.doc, st, [w1.GlobalId], "type") == ids(w1, w2)
    assert ss.similar(model.doc, st, [w1.GlobalId, w3.GlobalId], "type") == ids(w1, w2, w3)
    assert ss.similar(model.doc, st, [w3.GlobalId], "material") == ids(w3)
    assert ss.similar(model.doc, st, [ln.GlobalId], "layer") == ids(ln)
    assert ss.similar(model.doc, st, [w1.GlobalId], "predefined") == ids(w1, w2, w3)
    assert up.ops[0].id not in ss.similar(model.doc, st, [w1.GlobalId], "class")
