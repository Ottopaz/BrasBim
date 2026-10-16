# SPDX-License-Identifier: LGPL-3.0-or-later
"""Documentação da planta (spec/ui 13 §10), no núcleo: escala, ambientes, cotas, cota de
nível, texto, linha, hachura e norte."""

import math

import ifcopenshell.util.element as ue
import pytest
from estrutura import check_history, column_type, created, slab_type, valid

from brasbim.core import storeys, transform
from brasbim.core.annotations import base, dimensions, drafting, spaces
from brasbim.core.annotations import commands as ac
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd


def _rect(model):
    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (5, 4)))


def _space(model, p=(2, 2), **options):
    return created(model, ac.create_space_in_room(model.doc, model.terreo, p, **options))


def _anno(model, prefix, **fields):
    return created(model, ac.create_annotation(model.doc, prefix, model.terreo, **fields))


def _rep_items(element):
    rep = next(r for r in element.Representation.Representations
               if r.RepresentationIdentifier == "Annotation")
    return rep.Items


# --- escala --------------------------------------------------------------------------


def test_do01_escala(model):
    text = _anno(model, "text", at=[1, 1], text="A", size=2.5)
    h = base.build(model.doc, text).texts[0].height
    assert h == pytest.approx(0.125)
    model.commit(cmd.edit_storey(model.doc, model.terreo, scale=100))
    assert ue.get_pset(model.terreo, storeys.PSET)["Escala"] == 100
    assert base.build(model.doc, text).texts[0].height == pytest.approx(0.25)
    model.history.undo()
    assert storeys.scale(model.terreo) == 50
    assert not (ue.get_pset(model.terreo, storeys.PSET) or {}).get("Escala")


# --- ambientes -----------------------------------------------------------------------


def test_am01_ambiente_pelo_comodo(model, tmp_path):
    _rect(model)
    space = _space(model)
    assert space.is_a("IfcSpace") and space.PredefinedType == "INTERNAL"
    assert ue.get_aggregate(space) == model.terreo
    assert (space.Name, space.LongName) == ("01", "Ambiente")
    q = ue.get_pset(space, "Qto_SpaceBaseQuantities")
    assert q["NetFloorArea"] == pytest.approx(4.72 * 3.72)
    reps = {r.RepresentationIdentifier for r in space.Representation.Representations}
    assert {"FootPrint", "Body"} <= reps
    assert valid(model.reopen(tmp_path))


def test_am02_pe_direito(model):
    _rect(model)
    space = _space(model)
    assert ue.get_pset(space, "Qto_SpaceBaseQuantities")["Height"] == pytest.approx(2.8)
    slab = created(model, sc.create_slab_rectangle(model.doc, slab_type(model), model.superior,
                                                   (0, 0), (5, 4)))
    assert ue.get_pset(space, "Qto_SpaceBaseQuantities")["Height"] == pytest.approx(2.7)
    model.commit(ac.edit_element(model.doc, space, height=2.6))
    assert ue.get_pset(space, "Qto_SpaceBaseQuantities")["Height"] == pytest.approx(2.6)
    model.commit(ac.edit_element(model.doc, space, height=None))
    model.commit(sc.delete_element(model.doc, slab))
    assert ue.get_pset(space, "Qto_SpaceBaseQuantities")["Height"] == pytest.approx(2.8)


def test_am03_numeros(model):
    _rect(model)
    first = _space(model)
    second = created(model, ac.create_space(model.doc, model.terreo,
                                            [(6, 0), (8, 0), (8, 2), (6, 2)]))
    assert (first.Name, second.Name) == ("01", "02")
    model.commit(ac.delete_element(model.doc, first))
    third = created(model, ac.create_space(model.doc, model.terreo,
                                           [(10, 0), (12, 0), (12, 2), (10, 2)]))
    assert third.Name == "01"


def test_am04_etiqueta(model):
    _rect(model)
    space = _space(model, name="Sala")
    state = spaces.read_state(space)
    assert spaces.label_point(state) == pytest.approx((2.5, 2.0))
    model.commit(ac.edit_element(model.doc, space, label_at=[1, 1]))
    assert spaces.read_state(space)["outline"] == state["outline"]
    assert spaces.label_point(spaces.read_state(space)) == (1, 1)


def test_am05_transformar_e_diario(model):
    def action():
        _rect(model)
        space = _space(model)
        model.commit(transform.move_elements(model.doc, [space], (1, 0)))
        model.commit(transform.rotate_elements(model.doc, [space], (0, 0), 0.3))
        model.commit(transform.mirror_elements(model.doc, [space], (0, 0), (0, 1)))
        model.commit(transform.copy_elements(model.doc, [space], (10, 0)))
        assert sorted(s.Name for s in model.doc.ifc.by_type("IfcSpace")) == ["01", "02"]

    check_history(model, action)


# --- cotas ---------------------------------------------------------------------------


def test_ct01_cota_horizontal(model):
    dim = created(model, ac.create_dimension(model.doc, model.terreo, [(0, 0), (5, 0)],
                                             "fixed", 0.0, -0.6))
    assert dim.is_a("IfcAnnotation") and dim.PredefinedType == "DIMENSION"
    assert ue.get_container(dim) == model.terreo
    assert [t.text for t in base.build(model.doc, dim).texts] == ["5,00"]
    assert any(i.is_a("IfcTextLiteralWithExtent") for i in _rep_items(dim))


def _wall_ref(wall, end, face="right"):
    return {"kind": "wall", "gid": wall.GlobalId, "end": end, "face": face}


def test_ct02_presa_a_parede(model):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    items = [(dimensions.resolve(model.doc, _wall_ref(wall, e)), _wall_ref(wall, e))
             for e in ("start", "end")]
    dim = created(model, ac.create_dimension(model.doc, model.terreo, items, offset=-0.6))
    model.commit(cmd.move_wall_end(model.doc, wall, "end", (6, 0)))
    assert [t.text for t in base.build(model.doc, dim).texts] == ["6,00"]


def test_ct03_ct04_presa_ao_pilar(model):
    column = created(model, sc.create_column(model.doc, column_type(model), model.terreo,
                                             (2, 3)))
    ref = {"kind": "column", "gid": column.GlobalId, "u": -1.0, "v": -1.0}
    p = dimensions.resolve(model.doc, ref)
    assert p == pytest.approx((1.9, 2.8))
    dim = created(model, ac.create_dimension(model.doc, model.terreo, [(0, 2.8), (p, ref)],
                                             "fixed", 0.0, -1.0))
    model.commit(transform.move_elements(model.doc, [column], (1, 0)))
    assert [t.text for t in base.build(model.doc, dim).texts] == ["2,90"]
    model.commit(sc.delete_element(model.doc, column))
    state = base.read_state(dim)
    assert state["points"][1]["at"] == pytest.approx([2.9, 2.8]) and state["points"][1]["lost"]
    assert [t.text for t in base.build(model.doc, dim).texts] == ["2,90"]
    model.history.undo()
    assert not base.read_state(dim)["points"][1].get("lost")


def test_ct05_cotar_parede_com_porta(model):
    from brasbim.core.fillings import commands as fc

    wall = model.wall((0, 0), (5, 0), ref_line="axis")
    model.commit(fc.create_door_type(model.doc, "P1", defaults={"width": 0.8}))
    (door_type,) = model.doc.ifc.by_type("IfcDoorType")
    model.commit(fc.create_door(model.doc, door_type, wall, 1.0))
    tx = model.commit(ac.auto_dimension_wall(model.doc, wall))
    assert [op.op for op in tx.ops] == ["dimension.create"]
    dim = model.doc.get(tx.ops[0].id)
    assert [t.text for t in base.build(model.doc, dim).texts] == ["1,00", "0,80", "3,20"]


def test_ct06_cadeia(model):
    dim = created(model, ac.create_dimension(model.doc, model.terreo,
                                             [(0, 0), (1, 0), (3, 0), (6, 0)], offset=0.5))
    assert len(base.build(model.doc, dim).texts) == 3


# --- nível, texto, linha, hachura, norte --------------------------------------------------


def test_nv01_cota_de_nivel(model):
    slab = created(model, sc.create_slab_rectangle(model.doc, slab_type(model), model.terreo,
                                                   (0, 0), (5, 4), top_offset=-0.05))
    mark = _anno(model, "level_mark", at=[2, 2])
    assert drafting.level_text(model.doc, model.terreo, base.read_state(mark)) == "−0,05"
    assert "−0,05" in [t.text for t in base.build(model.doc, mark).texts]
    model.commit(sc.edit_element(model.doc, slab, top_offset=0.0))
    assert [t.text for t in base.build(model.doc, mark).texts] == ["+0,00"]


def test_tx01_texto(model):
    text = _anno(model, "text", at=[1, 1], text="PLANTA BAIXA", size=5.0)
    assert text.PredefinedType == "TEXT"
    (literal,) = [i for i in _rep_items(text) if i.is_a("IfcTextLiteral")]
    assert literal.Literal == "PLANTA BAIXA"
    assert base.build(model.doc, text).texts[0].height == pytest.approx(0.25)
    model.commit(transform.rotate_elements(model.doc, [text], (0, 0), math.pi / 2))
    assert base.read_state(text)["angle"] == pytest.approx(90)
    model.commit(transform.mirror_elements(model.doc, [text], (0, 0), (1, 0)))
    angle = base.read_state(text)["angle"]
    assert -90 < angle <= 90  # legível


def test_lh01_linha_tracejada(model):
    line = _anno(model, "line2d", points=[[0, 0], [4, 0]], weight=0.35, dash="dashed")
    (curve_set,) = [i for i in _rep_items(line) if i.is_a("IfcGeometricCurveSet")]
    (styled,) = curve_set.StyledByItem
    (style,) = styled.Styles
    assert style.CurveWidth.wrappedValue == pytest.approx(0.00035)
    assert style.CurveFont.is_a("IfcCurveStyleFont")


def test_hc01_hachura(model):
    hatch = _anno(model, "hatch", outline=[[0, 0], [2, 0], [2, 1], [0, 1]], pattern="solid",
                  color="#9C9A93")
    (area,) = [i for i in _rep_items(hatch) if i.is_a("IfcAnnotationFillArea")]
    (styled,) = area.StyledByItem
    assert styled.Styles[0].is_a("IfcFillAreaStyle")


def test_no01_norte_e_validacao(model, tmp_path):
    north = _anno(model, "north", at=[0, 0], angle=30.0)
    arrow = base.build(model.doc, north).strokes[0]
    (x0, y0), (x1, y1) = arrow.points
    assert math.degrees(math.atan2(y1 - y0, x1 - x0)) == pytest.approx(30)
    assert north.PredefinedType == "SYMBOL" and north.ObjectType == "Norte"
    assert valid(model.reopen(tmp_path))


def test_do02_tudo_valido_e_diario(model, tmp_path):
    def action():
        _rect(model)
        space = _space(model, name="Sala")
        _anno(model, "text", at=[1, 1], text="SALA\nnível 0", size=3.0)
        _anno(model, "line2d", points=[[0, -1], [5, -1]], dash="dashdot")
        _anno(model, "hatch", outline=[[6, 0], [7, 0], [7, 1], [6, 1]], pattern="cross")
        _anno(model, "north", at=[8, 8])
        _anno(model, "level_mark", at=[2, 2])
        walls = sorted(model.doc.ifc.by_type("IfcWall"), key=lambda w: w.GlobalId)
        model.commit(ac.auto_dimension_wall(model.doc, walls[0]))
        model.commit(transform.move_elements(model.doc, [space], (0.5, 0)))
        model.commit(cmd.edit_storey(model.doc, model.terreo, scale=100))

    check_history(model, action)
    assert valid(model.reopen(tmp_path))
