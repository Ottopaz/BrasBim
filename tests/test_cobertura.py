# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cobertura simples (RF-ELE-07): critérios de aceite de spec/elementos/cobertura.md §10."""

import math

import ifcopenshell.util.element as ue
import ifcopenshell.util.placement
import numpy as np
import pytest
from conftest import snapshot
from estrutura import bounds, check_history, created, qto, slab_type, valid

from brasbim.core import plan, transform
from brasbim.core.document import OpError
from brasbim.core.structure import commands as sc
from brasbim.core.structure import roofs

TILE = [{"material": "Telha cerâmica", "thickness": 0.05}]


def _type(model, name="Telha cerâmica", layers=None):
    return slab_type(model, name, layers or TILE, "ROOF")


def _roof(model, outline=None, t=None, **options):
    """Duas águas sobre 10 × 6, h = 2,80, i = 30 %, beiral 0,60 (CB01), salvo outra coisa."""
    t = t or _type(model)
    options.setdefault("base_height", 2.80)
    outline = outline or [(0, 0), (10, 0), (10, 6), (0, 6)]
    return created(model, sc.create_roof(model.doc, t, model.terreo, outline, **options))


def _parts(roof):
    return roofs.parts_of(roof)


def _world(element):
    """Vértices do corpo em coordenadas do mundo."""
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, element)
    return np.array(shape.geometry.verts).reshape(-1, 3)


def test_cb01_duas_aguas(model):
    roof = _roof(model)
    assert roof.PredefinedType == "GABLE_ROOF" and roof.Representation is None
    assert ue.get_container(roof) == model.terreo
    parts = _parts(roof)
    assert len(parts) == 2
    (rel,) = roof.IsDecomposedBy
    assert set(rel.RelatedObjects) == set(parts)
    for part in parts:
        assert ue.get_type(part).PredefinedType == "ROOF"
        assert not part.ContainedInStructure
    state = roofs.read_state(model.doc, roof)
    faces = roofs.faces(state)
    ridge = [p for f in faces for p in f.ring if abs(p[1] - 3.0) < 1e-9]
    assert ridge and all(roofs.bottom_z(state, faces[0], p) == pytest.approx(3.70)
                         for p in ridge)
    assert roofs.bottom_z(state, faces[0], (5.0, -0.6)) == pytest.approx(2.62)
    # O telhado inteiro fica entre o beiral (2,62) e a cumeeira com a espessura.
    verts = np.concatenate([_world(p) for p in parts])
    assert verts[:, 2].max() == pytest.approx(3.70 + 0.05 * math.sqrt(1 + 0.09), abs=1e-6)
    assert verts[:, 0].min() == pytest.approx(-0.6, abs=0.02)
    assert verts[:, 1].min() == pytest.approx(-0.6, abs=0.02)


def test_cb02_pecas_no_plano_da_agua(model):
    roof = _roof(model)
    for part in _parts(roof):
        assert part.ObjectPlacement.PlacementRelTo == roof.ObjectPlacement
        (rep,) = part.Representation.Representations
        solid = rep.Items[0]
        assert solid.is_a("IfcExtrudedAreaSolid")
        assert tuple(solid.ExtrudedDirection.DirectionRatios) == (0.0, 0.0, 1.0)
        assert solid.Depth == pytest.approx(0.05)
        usage = ue.get_material(part, should_inherit=False)
        assert usage.is_a("IfcMaterialLayerSetUsage")
        assert (usage.LayerSetDirection, usage.DirectionSense) == ("AXIS3", "POSITIVE")
        total = sum(layer.LayerThickness for layer in usage.ForLayerSet.MaterialLayers)
        assert total == pytest.approx(solid.Depth)
        # A normal da peça é a da água: inclinada 30 % (cos α = 1/√1,09).
        m = ifcopenshell.util.placement.get_local_placement(part.ObjectPlacement)
        assert m[2, 2] == pytest.approx(1 / math.sqrt(1.09))


def test_cb03_quatro_aguas(model):
    roof = _roof(model, shape="hip")
    assert roof.PredefinedType == "HIP_ROOF"
    state = roofs.read_state(model.doc, roof)
    faces = roofs.faces(state)
    assert sorted(len(f.ring) for f in faces) == [3, 3, 4, 4]
    ridges = roofs.ridge_lines(state)
    lengths = sorted(round(math.dist(*r), 6) for r in ridges)
    assert 4.0 in lengths  # cumeeira L − W = 10 − 6
    assert len(ridges) == 5  # cumeeira e 4 espigões
    square = _roof(model, outline=[(20, 0), (26, 0), (26, 6), (20, 6)], shape="hip")
    assert square.PredefinedType == "PAVILION_ROOF"
    sq = roofs.faces(roofs.read_state(model.doc, square))
    assert [len(f.ring) for f in sq] == [3, 3, 3, 3]


def test_cb04_uma_agua_e_plana(model):
    l_shape = [(0, 0), (6, 0), (6, 3), (3, 3), (3, 5), (0, 5)]
    roof = _roof(model, outline=l_shape, shape="shed", side=0, overhang=0.0)
    assert roof.PredefinedType == "SHED_ROOF"
    (part,) = _parts(roof)
    q = qto(part, "Qto_SlabBaseQuantities")
    plan_area = 6 * 3 + 3 * 2
    assert q["GrossArea"] == pytest.approx(plan_area * math.sqrt(1.09))
    # Lado 0 (y = 0) é o mais baixo.
    state = roofs.read_state(model.doc, roof)
    (face,) = roofs.faces(state)
    assert roofs.bottom_z(state, face, (1, 0)) == pytest.approx(2.80)
    assert roofs.bottom_z(state, face, (1, 5)) == pytest.approx(2.80 + 1.5)
    flat = _roof(model, outline=[(20, 0), (25, 0), (25, 4), (20, 4)], shape="flat",
                 t=_type(model, "Laje impermeabilizada 12 cm",
                         [{"material": "Impermeabilização", "thickness": 0.02},
                          {"material": "Concreto", "thickness": 0.10}]))
    assert flat.PredefinedType == "FLAT_ROOF"
    (part,) = _parts(flat)
    assert ue.get_pset(part, "Pset_SlabCommon")["PitchAngle"] == pytest.approx(0.0)
    lo, hi = bounds(part)
    assert lo[2] == pytest.approx(2.80) and hi[2] == pytest.approx(2.92)
    assert lo[0] == pytest.approx(19.4) and hi[0] == pytest.approx(25.6)


def test_cb05_forma_recusada(model):
    t = _type(model)
    l_shape = [(0, 0), (6, 0), (6, 3), (3, 3), (3, 5), (0, 5)]
    before = snapshot(model.doc.ifc)
    for shape in ("gable", "hip"):
        with pytest.raises(OpError, match="retangular"):
            sc.create_roof(model.doc, t, model.terreo, l_shape, shape=shape)
    floor = slab_type(model)
    with pytest.raises(OpError, match="tipo de cobertura"):
        sc.create_roof(model.doc, floor, model.terreo, [(0, 0), (4, 0), (4, 4), (0, 4)])
    with pytest.raises(OpError, match="inclinação"):
        sc.create_roof(model.doc, t, model.terreo, [(0, 0), (4, 0), (4, 4), (0, 4)], slope=0)
    assert ue.get_types(floor) == []
    del before


def test_cb06_quantidades(model):
    roof = _roof(model)
    alpha = math.atan(0.30)
    total = 0.0
    for part in _parts(roof):
        q = qto(part, "Qto_SlabBaseQuantities")
        # Cada água: 11,2 × 3,6 em planta (com o beiral).
        assert q["GrossArea"] == pytest.approx(11.2 * 3.6 / math.cos(alpha))
        assert q["NetVolume"] == pytest.approx(q["GrossArea"] * 0.05)
        assert ue.get_pset(part, "Pset_SlabCommon")["PitchAngle"] == pytest.approx(alpha)
        total += q["GrossArea"]
    r = qto(roof, "Qto_RoofBaseQuantities")
    assert r["GrossArea"] == pytest.approx(total) and r["NetArea"] == pytest.approx(total)
    assert ue.get_pset(roof, roofs.PSET)["AreaProjecao"] == pytest.approx(11.2 * 7.2)
    common = ue.get_pset(roof, "Pset_RoofCommon")
    assert common["IsExternal"] is True and common["Reference"] == "Telha cerâmica"


def test_cb07_pelas_paredes(model):
    for a, b in [((0, 0), (8, 0)), ((8, 0), (8, 5)), ((8, 5), (0, 5)), ((0, 5), (0, 0))]:
        model.wall(a, b, ref_line="axis")
    t = _type(model)
    roof = created(model, sc.create_roof_over_walls(model.doc, t, model.terreo, (4, 2.5)))
    state = roofs.read_state(model.doc, roof)
    xs = [p[0] for p in state["outline"]]
    ys = [p[1] for p in state["outline"]]
    assert max(xs) - min(xs) == pytest.approx(8.14)
    assert max(ys) - min(ys) == pytest.approx(5.14)
    assert state["base_height"] == pytest.approx(roofs.wall_top(model.doc, model.terreo))


def test_cb08_edicao_mantem_pecas(model):
    roof = _roof(model)
    original = [p.GlobalId for p in _parts(roof)]
    model.commit(sc.edit_element(model.doc, roof, slope=35, overhang=0.8))
    assert [p.GlobalId for p in _parts(roof)] == original
    assert roofs.read_state(model.doc, roof)["slope"] == 35
    model.commit(sc.edit_element(model.doc, roof, shape="hip"))
    assert len(_parts(roof)) == 4
    assert [p.GlobalId for p in _parts(roof)][:2] == original
    model.history.undo()
    assert [p.GlobalId for p in _parts(roof)] == original
    check_history(model, lambda: model.commit(sc.edit_element(model.doc, roof, shape="shed",
                                                              side=1)))


def test_cb09_transformacoes(model):
    roof = _roof(model, shape="shed", side=0)
    gid = roof.GlobalId

    def low_y():
        state = roofs.read_state(model.doc, model.doc.get(gid))
        (face,) = roofs.faces(state)
        return min(face.ring, key=lambda p: roofs.bottom_z(state, face, p))[1]

    assert low_y() == pytest.approx(-0.6)
    check_history(model, lambda: model.commit(transform.move_elements(model.doc, [gid],
                                                                      (1, 2))))
    assert low_y() == pytest.approx(1.4)
    # Espelhar pelo eixo horizontal y = 5: o lado baixo vai para cima.
    check_history(model, lambda: model.commit(transform.mirror_elements(
        model.doc, [gid], (0, 5), (1, 5))))
    assert low_y() == pytest.approx(10 - 1.4)
    model.commit(transform.rotate_elements(model.doc, [gid], (0, 0), math.pi / 2))
    state = roofs.read_state(model.doc, model.doc.get(gid))
    (face,) = roofs.faces(state)
    low = min(face.ring, key=lambda p: roofs.bottom_z(state, face, p))
    assert low[0] == pytest.approx(-(10 - 1.4))
    tx = model.commit(transform.copy_elements(model.doc, [gid], (30, 0)))
    (op,) = tx.ops
    copy_ = model.doc.get(op.id)
    assert copy_.Name == "Cobertura 2"
    assert not set(op.data["parts"]) & {p.GlobalId for p in _parts(model.doc.get(gid))}


def test_cb10_excluir_e_desfazer(model):
    roof = _roof(model, shape="hip")
    gids = {roof.GlobalId, *(p.GlobalId for p in _parts(roof))}
    before = snapshot(model.doc.ifc)

    def delete():
        model.commit(sc.delete_element(model.doc, roof))

    check_history(model, delete)
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    assert all(model.doc.find(g) is not None for g in gids)
    model.history.redo()
    assert all(model.doc.find(g) is None for g in gids)
    assert not model.doc.ifc.by_type("IfcRelAggregates", include_subtypes=False) or all(
        r.RelatingObject.is_a() != "IfcRoof" for r in model.doc.ifc.by_type("IfcRelAggregates"))


def test_cb10b_tipo_muda_espessura(model):
    t = _type(model)
    roof = _roof(model, t=t)
    model.commit(sc.edit_type(model.doc, t, layers=[{"material": "Telha cerâmica",
                                                     "thickness": 0.08}]))
    for part in _parts(roof):
        assert part.Representation.Representations[0].Items[0].Depth == pytest.approx(0.08)
    other = _type(model, "Telha de fibrocimento",
                  [{"material": "Telha de fibrocimento", "thickness": 0.03}])
    model.commit(sc.delete_type(model.doc, t, replacement=other))
    assert ue.get_type(_parts(roof)[0]) == other


def test_cb13_valido_e_reaberto(model, tmp_path):
    roof = _roof(model, shape="hip")
    assert valid(model.doc.ifc)
    ifc = model.reopen(tmp_path)
    (found,) = ifc.by_type("IfcRoof")
    assert found.GlobalId == roof.GlobalId
    assert len(roofs.parts_of(found)) == 4


def test_pecas_fora_da_planta_das_lajes(model):
    roof = _roof(model)
    model.wall((0, 0), (10, 0))
    p = plan.storey_plan(model.doc, model.terreo)
    owners = {s.owner for s in p.shapes}
    assert not owners & {x.GlobalId for x in _parts(roof)}
    assert sc.is_structure(roof) and not sc.is_structure(_parts(roof)[0])


def test_cb11_planta_e_corte(model):
    from brasbim.core.annotations import commands as ac
    from brasbim.core.drawings import section
    from brasbim.core.walls import commands as cmd

    roof = _roof(model)
    p = plan.storey_plan(model.doc, model.terreo)
    (prims,) = [pr for owner, pr in p.annotations if owner == roof.GlobalId]
    # Acima do plano de corte: só o beiral tracejado, sem setas nem textos.
    assert [s.dash for s in prims.strokes] == ["dashed"] and not prims.texts
    assert p.pick((5.0, -0.6), 0.05) == roof.GlobalId
    assert p.pick((5.0, 3.0), 0.05) is None  # por dentro, não pega a cobertura de cima
    # Pavimento "Cobertura" acima das paredes: planta de cobertura.
    model.commit(cmd.create_storey(model.doc, "Cobertura", 2.8))
    top = next(s for s in model.doc.storeys() if s.Name == "Cobertura")
    roof2 = created(model, sc.create_roof(model.doc, _type(model, "T2"), top,
                                          [(20, 0), (30, 0), (30, 6), (20, 6)],
                                          base_height=0.0))
    p = plan.storey_plan(model.doc, top)
    (prims,) = [pr for owner, pr in p.annotations if owner == roof2.GlobalId]
    assert all(s.dash == "solid" for s in prims.strokes)
    assert [t.text for t in prims.texts] == ["i = 30%", "i = 30%"]
    assert len(prims.strokes) == 1 + 1 + 2 * 2  # beiral, cumeeira, duas setas
    assert p.pick((25, 2), 0.05) == roof2.GlobalId
    # Corte transversal: as duas águas cortadas, em nome da cobertura.
    view = created(model, ac.create_view(model.doc, "section", (5, -2), (5, 8), "left"))
    drawing = section.draw(model.doc, view)
    owners = {it.owner for it in drawing.items if it.kind == "cut"}
    assert roof.GlobalId in owners
    assert not owners & {x.GlobalId for x in _parts(roof)}


def test_cb11b_projecao_no_pavimento_de_baixo(model):
    roof = created(model, sc.create_roof(model.doc, _type(model), model.superior,
                                         [(0, 0), (10, 0), (10, 6), (0, 6)],
                                         base_height=0.0))
    p = plan.storey_plan(model.doc, model.terreo)
    (prims,) = [pr for owner, pr in p.annotations if owner == roof.GlobalId]
    assert [s.dash for s in prims.strokes] == ["dashed"]
    assert p.pick((5.0, -0.6), 0.05) is None  # a de cima não se escolhe por aqui


def test_cb12_assistente(model):
    import json

    from brasbim.core.assistant.tools import Context, default_registry

    _type(model)
    ctx = Context(model.doc, model.commit, model.terreo.GlobalId)

    def call(tool, **args):
        result = default_registry().call(ctx, tool, args)
        text = result["content"][0]["text"]
        return (text if result["isError"] else json.loads(text)), result["isError"]

    out, err = call("layout_rooms", rooms=[
        {"name": "Sala", "x": 0, "y": 0, "width": 5, "depth": 4},
        {"name": "Quarto", "x": 5, "y": 0, "width": 3, "depth": 4}], height=2.8)
    assert not err, out
    out, err = call("create_roof")
    assert not err, out
    assert out["forma"] == "gable" and out["aguas"] == 2
    xs = [p[0] for p in out["contorno_apoio"]]
    assert max(xs) - min(xs) == pytest.approx(8.14)  # a casa inteira, não um cômodo
    assert out["cota_cumeeira"] > out["cota_beiral"]
    model_out, _ = call("describe_model")
    (roof,) = model_out["coberturas"]
    assert roof["tipo"] == "Telha cerâmica" and roof["lado"] in (1, 2, 3, 4)
    assert "Telha cerâmica" in model_out["tipos"]["cobertura"]
    assert "Telha cerâmica" not in model_out["tipos"]["laje"]
    out, err = call("edit_roof", id=roof["id"], shape="hip", slope=25)
    assert not err and out["aguas"] == 4
    out, err = call("create_roof", outline=[[0, 0], [6, 0], [6, 3], [3, 3], [3, 5], [0, 5]],
                    shape="gable")
    assert err and "retangular" in out
