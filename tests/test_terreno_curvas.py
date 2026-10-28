# SPDX-License-Identifier: LGPL-3.0-or-later
"""Terreno por contorno e curvas de nível (escada-terreno.md §4.2–§4.4): TR01 a TR07."""

import math
import time

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, created, valid

from brasbim.core import plan, terrain, transform
from brasbim.core.annotations import base, reference
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError

RECT = [(0, 0), (30, 0), (30, 20), (0, 20)]


def _curve(y, z, wave=0.0, x0=-1.0, x1=31.0, n=33):
    return {"points": [(x0 + (x1 - x0) * i / (n - 1),
                        y + wave * math.sin(i / 3)) for i in range(n)], "z": z,
            "closed": False}


def _terrain(model, **options):
    return created(model, terrain.create_terrain(model.doc, **options))


def test_tr01_contorno_com_cota(model):
    def create():
        _terrain(model, boundary=RECT, boundary_z=100.0)

    check_history(model, create)
    (t,) = terrain.all_terrains(model.doc)
    assert ue.get_container(t) == model.doc.ifc.by_type("IfcSite")[0]
    pts, _ = terrain.surface(terrain.read_state(t))
    assert {p[2] for p in pts} == {100.0}
    assert terrain.height_at(terrain.read_state(t), (15, 10)) == pytest.approx(100.0)
    p = plan.storey_plan(model.doc, model.terreo)
    prims = dict(p.annotations)[t.GlobalId]
    assert prims.strokes[0].dash == "solid" and len(prims.strokes[0].points) == 4
    assert valid(model.doc.ifc)


def test_tr02_curvas_dao_a_superficie(model):
    t = _terrain(model, boundary=RECT,
                 curves=[_curve(4, 100.0), _curve(10, 101.0), _curve(16, 102.0)])
    state = terrain.read_state(t)
    assert terrain.height_at(state, (15, 7)) == pytest.approx(100.5, abs=0.05)
    assert terrain.height_at(state, (15, 13)) == pytest.approx(101.5, abs=0.05)
    # o contorno sem cota segue as curvas vizinhas
    assert terrain.height_at(state, (15, 0.01)) < 100.0 + 0.3
    assert terrain.height_at(state, (15, 19.99)) > 102.0 - 0.3
    assert terrain.height_at(state, (31, 10)) is None  # fora do contorno
    pts, tris = terrain.surface(state)
    assert all(-1e-6 <= sum(pts[i][0] for i in tri) / 3 <= 30 + 1e-6 for tri in tris)
    (faces,) = t.Representation.Representations[0].Items
    assert len(faces.CoordIndex) == len(tris)
    assert valid(model.doc.ifc)


def test_tr03_curva_sem_cota(model):
    t = _terrain(model, boundary=RECT, curves=[_curve(4, 100.0), _curve(16, 102.0),
                                               {**_curve(10, None)}])
    state = terrain.read_state(t)
    assert terrain.height_at(state, (15, 10)) == pytest.approx(101.0, abs=0.1)  # sem ela
    prims = dict(plan.storey_plan(model.doc, model.terreo).annotations)[t.GlobalId]
    pending = [s for s in prims.strokes if s.dash == "dashed"]
    assert len(pending) == 1 and len(pending[0].points) == 33
    assert terrain.curve_near(state, (15.2, 10.4), 0.5) == 2
    model.commit(terrain.set_curve_level(model.doc, t, 2, 101.6))
    state = terrain.read_state(t)
    assert terrain.height_at(state, (5, 10 + math.sin(5 / 3 * 32 / 32))) == \
        pytest.approx(101.6, abs=0.15)
    texts = [x.text for x in dict(plan.storey_plan(model.doc, model.terreo)
                                  .annotations)[t.GlobalId].texts]
    assert "101,60" in texts
    model.history.undo()
    assert terrain.read_state(t)["curves"][2]["z"] is None


def test_tr04_pegar_linhas_do_desenho(model, tmp_path):
    from test_importar_desenho import E0, N0, levantamento

    from brasbim.core.imports import dxf

    d = dxf.read(str(levantamento(tmp_path / "topo.dxf")))
    model.commit(dxf.import_drawing(model.doc, model.terreo, d, "m", (E0, N0)))
    refs = {base.read_state(a)["layer"]: (a.GlobalId, base.read_state(a))
            for a in model.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)}
    border = reference.lines_of(refs["DIVISA"][1]).line(0)
    t = _terrain(model, boundary=border["points"])
    lines = reference.lines_of(refs["CURVAS"][1]).to_dicts()

    def pick():
        model.commit(terrain.add_curves(model.doc, t, lines))

    check_history(model, pick)
    state = terrain.read_state(t)
    assert sorted(c["z"] for c in state["curves"]) == [100.0, 101.0, 102.0]  # cota do DWG
    assert not terrain.add_curves(model.doc, t, lines[:1]).ops  # repetida fica de fora
    found = reference.lines_near([refs["CURVAS"]], tuple(lines[1]["points"][3]), 0.05)
    assert found and found[0][3]["z"] == lines[1]["z"]
    model.commit(terrain.remove_curve(model.doc, t, 0))
    assert len(terrain.read_state(t)["curves"]) == 2
    assert valid(model.doc.ifc)


def test_tr05_patamar_falso_e_topo(model):
    meander = {"points": [(x, 10 + 4 * math.sin(x / 2.5)) for x in range(-1, 32)], "z": 101.0,
               "closed": False}
    state = {**terrain.default_state(), "boundary": [list(p) for p in RECT],
             "curves": [_curve(1, 100.0), meander, _curve(19, 102.0)]}

    def flat_area(pts, tris):
        return sum(terrain._area(pts, t) for t in tris
                   if all(abs(pts[i][2] - 101.0) < 1e-9 for i in t))

    samples = terrain._samples(state)
    before = flat_area(samples, terrain._triangulate(samples, state["boundary"]))
    assert before > 5.0  # a curva sinuosa cria patamares falsos (m²)
    after = flat_area(*terrain.surface(state))
    assert after < before / 4
    # topo de morro: curva fechada mais alta que as vizinhas fica plana por dentro
    hill = {**terrain.default_state(), "boundary": [list(p) for p in RECT],
            "boundary_z": 100.0,
            "curves": [{"points": [(15 + 3 * math.cos(a / 8 * math.pi),
                                    10 + 3 * math.sin(a / 8 * math.pi)) for a in range(16)],
                        "closed": True, "z": 103.0}]}
    assert terrain.height_at(hill, (15, 10)) == pytest.approx(103.0)


def test_tr06_transformacoes_e_exclusao(model):
    t = _terrain(model, boundary=RECT, curves=[_curve(4, 100.0), _curve(16, 102.0)])
    model.commit(transform.move_elements(model.doc, [t.GlobalId], (5.0, 1.0)))
    state = terrain.read_state(t)
    assert state["boundary"][0] == pytest.approx([5, 1])
    assert state["curves"][0]["points"][0] == pytest.approx([4, 5])
    model.commit(transform.rotate_elements(model.doc, [t.GlobalId], (5, 1), math.pi / 2))
    assert terrain.read_state(t)["boundary"][1] == pytest.approx([5, 31])
    with pytest.raises(OpError, match="contorno"):
        terrain.create_terrain(model.doc, boundary=[(0, 0), (1, 0)])
    model.commit(delete_elements(model.doc, [t.GlobalId])[0])
    assert not terrain.all_terrains(model.doc)


def test_tr07_levantamento_grande():
    curves = [{"points": [(x * 2.0, 3.0 * i + math.sin(x / 7 + i)) for x in range(101)],
               "closed": False, "z": 100.0 + 0.5 * i} for i in range(40)]
    state = {**terrain.default_state(), "boundary": [[0, -2], [200, -2], [200, 120], [0, 120]],
             "curves": curves}
    t0 = time.perf_counter()
    pts, tris = terrain.surface(state)
    assert time.perf_counter() - t0 < 5.0
    assert len(pts) > 8000 and tris


def test_tr08_fluxo_na_interface(window, app, tmp_path):
    """O fluxo do revisor: importa o levantamento, desenha o contorno, seleciona o
    terreno, pega as curvas com Enter e clique, e dá a cota à linha que veio sem ela."""
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QPointF
    from test_importar_desenho import E0, N0, levantamento

    from brasbim.core.annotations import commands as ac
    from brasbim.ui.tools import Mods, selection_actions

    window.plan.origin = QPointF(150, 450)
    s = window.session
    assert window.import_drawing(str(levantamento(tmp_path / "topo.dxf")),
                                 choose=lambda d: (set(d.layers), "m", (E0, N0)))
    s.run(lambda: ac.create_annotation(s.doc, "line2d", s.storey,
                                       points=[[0.0, 13.5], [20.0, 13.5]]))
    # 1. contorno
    window.activate_tool("terrain")
    tool = window.toolbox.active
    assert tool.options.mode == "outline"
    for q in ((0, 0), (20, 0), (20, 15), (0, 15), (0, 0)):
        tool.move(q, Mods(alt=True))
        tool.press(q, Mods(alt=True))
    (t,) = terrain.all_terrains(s.doc)
    assert len(terrain.read_state(t)["boundary"]) == 4
    # 2. pegar as linhas
    s.select([t.GlobalId])
    assert {"pick_curves", "curve_level"} <= set(selection_actions(s.doc, [t.GlobalId]))
    window.run_selection_action("pick_curves")
    tool = window.toolbox.active
    assert tool.name == "terrain_pick" and tool.terrain == t.GlobalId
    state = base.read_state(next(a for a in s.doc.ifc.by_type("IfcAnnotation")
                                 if reference.is_reference(a)
                                 and base.read_state(a)["layer"] == "CURVAS"))
    for line in reference.lines_of(state).to_dicts():
        tool.move(tuple(line["points"][4]), Mods())
        assert tool.hover is not None and tool.preview()
        tool.key("enter")
    tool.move((10, 13.5), Mods())  # a linha 2D desenhada no BrasBim, sem cota
    assert tool.labels()[0][1] == "sem cota"
    tool.press((10, 13.5), Mods())
    curves = terrain.read_state(t)["curves"]
    assert [c["z"] for c in curves] == [100.0, 101.0, 102.0, None]
    # 3. cota da curva que veio sem cota
    window.activate_tool("select")
    s.select([t.GlobalId])
    window.run_selection_action("curve_level")
    tool = window.toolbox.active
    assert tool.name == "terrain_level"
    assert [m.style for m in tool.preview()] == ["invalid"]
    tool.press((10, 13.5), Mods())
    assert tool.chosen == 3 and tool.fields()[0].key == "z"
    assert tool.numeric(102.8)
    assert terrain.read_state(t)["curves"][3]["z"] == pytest.approx(102.8)
    assert not [m for m in tool.preview() if m.style == "invalid"]
    # a sugestão é a última cota mais o intervalo
    tool.press(tuple(reference.lines_of(state).line(0)["points"][4]), Mods())
    assert tool.chosen is not None
    # 4. o 3D acompanha
    from brasbim.ui.scene3d import Scene

    scene = Scene()
    scene.load(s.doc.ifc, s.doc)
    z = scene.meshes[t.GlobalId].vertices[:, 2]
    assert z.max() == pytest.approx(102.8, abs=0.01)
    window.properties._rebuild()
    assert window.properties.groups[0].title == "Terreno"
