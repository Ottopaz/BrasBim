# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pilar (RF-ELE-03): critérios de aceite de spec/elementos/pilar.md §9."""

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot
from estrutura import (
    bounds,
    check_history,
    circle_type,
    column_type,
    created,
    foreign_ifc,
    qto,
    valid,
)

from brasbim.core import clip, plan, transform
from brasbim.core.document import Document, OpError
from brasbim.core.ops import History
from brasbim.core.structure import columns, profiles
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as wall_cmd


def _column(model, point=(2, 3), column_type_=None, **options):
    t = column_type_ or column_type(model)
    return created(model, sc.create_column(model.doc, t, model.terreo, point, **options))


def _rep(element, identifier):
    return next(r for r in element.Representation.Representations
                if r.RepresentationIdentifier == identifier)


def test_pi01_pilar_basico(model, tmp_path):
    _column(model)
    ifc = model.reopen(tmp_path)
    (column,) = ifc.by_type("IfcColumn")
    assert ue.get_type(column).PredefinedType == "COLUMN"
    assert ue.get_container(column).Name == "Térreo"
    (axis,) = _rep(column, "Axis").Items
    assert [p.Coordinates for p in axis.Points] == [(0.0, 0.0, 0.0), (0.0, 0.0, 2.8)]
    (solid,) = _rep(column, "Body").Items
    assert solid.is_a("IfcExtrudedAreaSolid") and solid.Depth == pytest.approx(2.8)


def test_pi02_perfil_compartilhado(model, tmp_path):
    _column(model)
    ifc = model.reopen(tmp_path)
    (column,) = ifc.by_type("IfcColumn")
    pset = ue.get_material(ue.get_type(column))
    assert pset.is_a("IfcMaterialProfileSet")
    (mp,) = pset.MaterialProfiles
    assert mp.Profile.is_a("IfcRectangleProfileDef")
    assert (mp.Profile.XDim, mp.Profile.YDim) == pytest.approx((0.2, 0.4))
    usage = ue.get_material(column, should_inherit=False)
    assert usage.is_a("IfcMaterialProfileSetUsage") and usage.CardinalPoint == 5
    assert _rep(column, "Body").Items[0].SweptArea == mp.Profile


def test_pi03_canto_inferior_esquerdo(model):
    # Canto inferior esquerdo da planta = CardinalPoint 3 (a esquerda do IFC é o +x do
    # perfil, olhando na direção da extrusão: profiles.py).
    cardinal = profiles.PLAN_CARDINAL[(0, 0)]
    assert cardinal == 3
    column = _column(model, cardinal=cardinal)
    assert ue.get_material(column, should_inherit=False).CardinalPoint == 3
    lo, hi = bounds(column)
    assert lo[:2] == pytest.approx((2.0, 3.0)) and hi[:2] == pytest.approx((2.2, 3.4))


def test_pi04_angulo_90(model):
    lo, hi = bounds(_column(model, angle=90.0))
    assert lo[:2] == pytest.approx((1.8, 2.9)) and hi[:2] == pytest.approx((2.2, 3.1))


def test_pi05_circular(model):
    column = _column(model, column_type_=circle_type(model))
    profile = _rep(column, "Body").Items[0].SweptArea
    assert profile.is_a("IfcCircleProfileDef") and profile.Radius == pytest.approx(0.15)
    with pytest.raises(OpError):
        model.commit(sc.create_column(model.doc, ue.get_type(column), model.terreo, (5, 5),
                                      cardinal=1))


def test_pi06_cota_do_pavimento(model):
    column = _column(model)
    model.commit(wall_cmd.edit_storey(model.doc, model.superior, elevation=3.0))
    assert qto(column, "Qto_ColumnBaseQuantities")["Length"] == pytest.approx(3.0)
    assert _rep(column, "Body").Items[0].Depth == pytest.approx(3.0)


def test_pi07_topo_abaixo_da_base(model):
    t = column_type(model)
    with pytest.raises(OpError):
        model.commit(sc.create_column(model.doc, t, model.terreo, (0, 0), top_offset=-3.0))
    column = _column(model, column_type_=t)
    with pytest.raises(OpError):
        model.commit(sc.edit_element(model.doc, column, base_offset=3.0))
    assert len(model.doc.ifc.by_type("IfcColumn")) == 1


def test_pi08_quantidades(model):
    q = qto(_column(model), "Qto_ColumnBaseQuantities")
    assert q["Length"] == pytest.approx(2.8)
    assert q["CrossSectionArea"] == pytest.approx(0.08)
    assert q["OuterSurfaceArea"] == pytest.approx(3.36)
    assert q["GrossVolume"] == pytest.approx(0.224) == q["NetVolume"]


def test_pi09_psets_e_reabrir(model, tmp_path):
    column = _column(model)
    common = ue.get_pset(column, "Pset_ColumnCommon")
    assert common["Reference"] == "Pilar 20×40" and common["Status"] == ["NEW"]
    assert common["LoadBearing"] is True
    assert ue.get_pset(column, columns.PSET)
    state = columns.read_state(model.doc, column)
    ifc = model.reopen(tmp_path)
    reopened = Document(ifc)
    assert columns.read_state(reopened, reopened.get(column.GlobalId)) == state


def test_pi10_nomes_automaticos(model):
    t = column_type(model)
    p1 = _column(model, (0, 0), t)
    p2 = _column(model, (3, 0), t)
    assert (p1.Name, p2.Name) == ("P1", "P2")
    model.commit(sc.delete_element(model.doc, p1))
    assert _column(model, (6, 0), t).Name == "P1"


def test_pi11_recorta_a_parede_na_planta(model):
    wall = model.wall((0, 0), (5, 0), ref_line="axis")

    def wall_area():
        p = plan.storey_plan(model.doc, model.terreo)
        return sum(clip.area(r.rings) for r in p.regions if r.key == model.type14.GlobalId)

    before = wall_area()
    _column(model, (2.5, 0))
    assert wall_area() == pytest.approx(before - 0.14 * 0.20)
    assert wall.GlobalId  # o IFC da parede não muda


def test_pi12_editar_desfazer_e_diario(model):
    t = column_type(model)

    def action():
        column = _column(model, (2, 3), t, cardinal=1)
        model.commit(transform.move_elements(model.doc, [column], (1, 1)))
        model.commit(transform.rotate_elements(model.doc, [column], (0, 0), 0.5))
        model.commit(transform.mirror_elements(model.doc, [column], (0, 0), (0, 1)))
        model.commit(sc.delete_element(model.doc, column))

    check_history(model, action)


def test_pi12_espelhar_mantem_a_secao(model):
    column = _column(model, (2, 3), cardinal=1, angle=30.0)
    lo, hi = bounds(column)
    model.commit(transform.mirror_elements(model.doc, [column], (0, 0), (0, 1)))
    lo2, hi2 = bounds(column)
    assert (lo2[0], hi2[0]) == pytest.approx((-hi[0], -lo[0]))
    assert (lo2[1], hi2[1]) == pytest.approx((lo[1], hi[1]))


def test_pi12_excluir_e_desfazer(model):
    column = _column(model)
    gid, before = column.GlobalId, snapshot(model.doc.ifc)
    count = len(list(model.doc.ifc))
    model.commit(sc.delete_element(model.doc, column))
    model.history.undo()
    assert model.doc.find(gid) is not None and snapshot(model.doc.ifc) == before
    assert len(list(model.doc.ifc)) == count


def test_pi13_outra_origem(tmp_path):
    doc = Document.open(foreign_ifc(tmp_path / "outro.ifc", "IfcColumn"))
    history = History(doc)
    (column,) = doc.ifc.by_type("IfcColumn")
    body = column.Representation.Representations[0].Items[0]
    history.commit(transform.move_elements(doc, [column], (2, 0)))
    assert column.ObjectPlacement.RelativePlacement.Location.Coordinates == (3.0, 2.0, 0.0)
    assert column.Representation.Representations[0].Items[0] == body
    history.commit(sc.delete_element(doc, column))
    history.undo()
    (column,) = doc.ifc.by_type("IfcColumn")
    assert column.ObjectPlacement.RelativePlacement.Location.Coordinates == (3.0, 2.0, 0.0)
    assert column.Representation.Representations[0].Items[0].Depth == pytest.approx(1.0)


def test_pi14_validacao(model, tmp_path):
    _column(model, (0, 0))
    _column(model, (3, 0), circle_type(model), angle=45.0)
    assert valid(model.reopen(tmp_path))
