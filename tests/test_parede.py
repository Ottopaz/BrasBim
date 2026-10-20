# SPDX-License-Identifier: LGPL-3.0-or-later
"""Parede (RF-ELE-01): critérios de aceite de spec/elementos/parede.md §9."""

import math

import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.validate
import pytest

from brasbim.core.document import OpError
from brasbim.core.walls import commands as cmd

T = 0.14


def _qto(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")


def _rep(wall, identifier):
    return next(
        r for r in wall.Representation.Representations if r.RepresentationIdentifier == identifier
    )


def _profile_y_range(wall):
    solid = _rep(wall, "Body").Items[0]
    ys = [p[1] for p in solid.SweptArea.OuterCurve.Points.CoordList]
    return min(ys), max(ys)


def test_p01_parede_reta(model, tmp_path):
    model.wall((0, 0), (5, 0))
    ifc = model.reopen(tmp_path)
    (wall,) = ifc.by_type("IfcWall")
    assert ue.get_container(wall).Name == "Térreo"
    axis = _rep(wall, "Axis")
    assert axis.RepresentationType == "Curve2D"
    assert axis.ContextOfItems.ContextType == "Plan"
    (curve,) = axis.Items
    assert curve.is_a("IfcPolyline") and len(curve.Points) == 2
    assert math.dist(curve.Points[0].Coordinates, curve.Points[1].Coordinates) == pytest.approx(5)
    (solid,) = _rep(wall, "Body").Items
    assert solid.is_a("IfcExtrudedAreaSolid")
    assert solid.SweptArea.is_a("IfcArbitraryClosedProfileDef")
    assert solid.Depth == pytest.approx(2.8)
    assert wall.PredefinedType is None


def test_p02_material(model, tmp_path):
    model.wall()
    ifc = model.reopen(tmp_path)
    (wall,) = ifc.by_type("IfcWall")
    usage = ue.get_material(wall, should_inherit=False)
    assert usage.is_a("IfcMaterialLayerSetUsage")
    assert usage.LayerSetDirection == "AXIS2"
    lset = ue.get_material(ue.get_type(wall))
    assert lset.is_a("IfcMaterialLayerSet") and usage.ForLayerSet == lset
    assert len(lset.MaterialLayers) == 3
    assert sum(layer.LayerThickness for layer in lset.MaterialLayers) == pytest.approx(T)
    assert ue.get_type(wall).PredefinedType == "SOLIDWALL"


@pytest.mark.parametrize(
    ("ref_line", "flip", "sense", "offset", "y_range"),
    [
        ("right_face", False, "POSITIVE", 0, (0, T)),
        ("axis", False, "POSITIVE", -T / 2, (-T / 2, T / 2)),
        ("left_face", False, "POSITIVE", -T, (-T, 0)),
        ("right_face", True, "NEGATIVE", T, (0, T)),
        ("axis", True, "NEGATIVE", T / 2, (-T / 2, T / 2)),
        ("left_face", True, "NEGATIVE", 0, (-T, 0)),
    ],
)
def test_p03_linha_de_referencia(model, tmp_path, ref_line, flip, sense, offset, y_range):
    model.wall(ref_line=ref_line, flip_layers=flip)
    (wall,) = model.reopen(tmp_path).by_type("IfcWall")
    usage = ue.get_material(wall, should_inherit=False)
    assert usage.DirectionSense == sense
    assert usage.OffsetFromReferenceLine == pytest.approx(offset)
    assert _profile_y_range(wall) == pytest.approx(y_range)


def test_p04_cota_do_pavimento_superior(model, tmp_path):
    wall = model.wall()
    gid = wall.GlobalId
    model.commit(cmd.edit_storey(model.doc, model.superior, elevation=3.0))
    (wall,) = model.reopen(tmp_path).by_type("IfcWall")
    assert wall.GlobalId == gid
    assert _qto(wall)["Height"] == pytest.approx(3.0)
    assert _rep(wall, "Body").Items[0].Depth == pytest.approx(3.0)


def test_cota_que_zera_altura_e_rejeitada(model):
    wall = model.wall()
    with pytest.raises(OpError):
        model.commit(cmd.edit_storey(model.doc, model.superior, elevation=0.0))
    assert model.superior.Elevation == pytest.approx(2.8)
    assert _qto(wall)["Height"] == pytest.approx(2.8)


def test_p12_psets(model, tmp_path):
    model.wall()
    (wall,) = model.reopen(tmp_path).by_type("IfcWall")
    common = ue.get_pset(wall, "Pset_WallCommon")
    assert common["Status"] == ["NEW"]
    assert common["LoadBearing"] is True
    assert common["Reference"] == "Alvenaria 14"
    pset = next(
        r.RelatingPropertyDefinition for r in wall.IsDefinedBy
        if r.RelatingPropertyDefinition.Name == "Pset_WallCommon"
    )
    status = next(p for p in pset.HasProperties if p.Name == "Status")
    assert status.is_a("IfcPropertyEnumeratedValue")
    own = ue.get_pset(wall, "BrasBim_Parede")
    assert own["LinhaReferencia"] == "FACE_ESQUERDA"
    assert own["PavimentoBase"] == model.terreo.GlobalId
    assert own["TipoTopo"] == "PAVIMENTO"
    assert own["PavimentoTopo"] == model.superior.GlobalId
    assert own["DeslocamentoBase"] == 0 and own["DeslocamentoTopo"] == 0


def test_p12_divisoria_nao_portante(model):
    model.commit(cmd.create_wall_type(
        model.doc, "Drywall", [{"material": "Gesso", "thickness": 0.095}], "PARTITIONING"
    ))
    drywall = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Drywall")
    tx = model.commit(cmd.create_wall(model.doc, drywall, model.terreo, (0, 0), (3, 0)))
    wall = model.doc.get(tx.ops[0].id)
    assert ue.get_pset(wall, "Pset_WallCommon")["LoadBearing"] is False


def test_p13_parede_em_arco(model, tmp_path):
    # Semicírculo de raio 2 (eixo da linha de referência), anti-horário.
    model.commit(cmd.create_arc_wall(
        model.doc, model.type14, model.terreo, (2, 0), (0, 2), (-2, 0), ref_line="axis"
    ))
    (wall,) = model.reopen(tmp_path).by_type("IfcWall")
    (curve,) = _rep(wall, "Axis").Items
    assert curve.is_a("IfcTrimmedCurve") and curve.BasisCurve.is_a("IfcCircle")
    assert curve.BasisCurve.Radius == pytest.approx(2)
    assert _qto(wall)["Length"] == pytest.approx(2 * math.pi)
    assert _qto(wall)["NetFootprintArea"] == pytest.approx(2 * math.pi * T)


def test_arco_com_face_como_referencia_mede_pelo_eixo_central(model):
    tx = model.commit(cmd.create_arc_wall(
        model.doc, model.type14, model.terreo, (2, 0), (0, 2), (-2, 0), ref_line="left_face"
    ))
    wall = model.doc.get(tx.ops[0].id)
    # Anti-horário: a esquerda é o lado do centro; parede para fora, eixo central r = 2,07.
    assert _qto(wall)["Length"] == pytest.approx(math.pi * (2 + T / 2))


def test_arco_maior_que_meia_volta(model):
    tx = model.commit(cmd.create_arc_wall(
        model.doc, model.type14, model.terreo, (1, -1), (-1.4142135623730951, 0), (1, 1),
        ref_line="axis",
    ))
    wall = model.doc.get(tx.ops[0].id)
    r = math.sqrt(2)
    assert _qto(wall)["Length"] == pytest.approx(r * 1.5 * math.pi)


def test_quantidades_reta(model):
    wall = model.wall()
    q = _qto(wall)
    assert q["Length"] == pytest.approx(5)
    assert q["Width"] == pytest.approx(T)
    assert q["GrossSideArea"] == pytest.approx(14)
    assert q["GrossVolume"] == pytest.approx(5 * T * 2.8)
    assert q["NetVolume"] == pytest.approx(5 * T * 2.8)


@pytest.mark.parametrize(
    "options",
    [
        {"top_mode": "fixed", "fixed_height": 0.0},
        {"base_offset": 3.0},
        {"ref_line": "meio"},
    ],
)
def test_parametros_invalidos_rejeitados(model, options):
    with pytest.raises((OpError, ValueError)):
        model.wall(**options)
    assert not model.doc.ifc.by_type("IfcWall")


def test_comprimento_minimo(model):
    with pytest.raises(ValueError):
        model.wall((0, 0), (0.0005, 0))


def test_sem_pavimento_acima_topo_fica_altura_fixa(model):
    tx = model.commit(cmd.create_wall(model.doc, model.type14, model.superior, (0, 0), (2, 0)))
    wall = model.doc.get(tx.ops[0].id)
    assert ue.get_pset(wall, "BrasBim_Parede")["TipoTopo"] == "ALTURA_FIXA"
    assert _qto(wall)["Height"] == pytest.approx(2.8)


def test_trocar_tipo_mantem_linha_de_referencia(model):
    wall = model.wall(ref_line="left_face")
    model.commit(cmd.create_wall_type(
        model.doc, "Alvenaria 19", [{"material": "Bloco cerâmico", "thickness": 0.19}]
    ))
    t19 = next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == "Alvenaria 19")
    model.commit(cmd.edit_wall(model.doc, wall, type=t19))
    assert ue.get_type(wall) == t19
    assert ue.get_material(wall, should_inherit=False).ForLayerSet == ue.get_material(t19)
    assert _profile_y_range(wall) == pytest.approx((-0.19, 0))
    assert ue.get_pset(wall, "Pset_WallCommon")["Reference"] == "Alvenaria 19"


def test_editar_camadas_do_tipo_recalcula_paredes(model):
    wall = model.wall(ref_line="axis")
    layers = [{"material": "Concreto", "thickness": 0.12}]
    model.commit(cmd.edit_wall_type(model.doc, model.type14, layers=layers))
    assert _qto(wall)["Width"] == pytest.approx(0.12)
    assert _profile_y_range(wall) == pytest.approx((-0.06, 0.06))


def test_editar_caminho(model):
    wall = model.wall()
    model.commit(cmd.edit_wall(model.doc, wall, path={"kind": "line", "start": [1, 1],
                                                     "end": [1, 4]}))
    assert _qto(wall)["Length"] == pytest.approx(3)
    loc = wall.ObjectPlacement.RelativePlacement
    assert loc.Location.Coordinates[:2] == pytest.approx((1, 1))
    assert loc.RefDirection.DirectionRatios[:2] == pytest.approx((0, 1))


def test_excluir_sem_orfaos(model):
    before = len(list(model.doc.ifc))
    wall = model.wall()
    model.commit(cmd.delete_wall(model.doc, wall))
    assert not model.doc.ifc.by_type("IfcWall")
    assert not model.doc.ifc.by_type("IfcMaterialLayerSetUsage")
    # Só o Pset das camadas, que é do projeto (spec/ui 18 §2).
    assert [p.Name for p in model.doc.ifc.by_type("IfcPropertySet")] == ["BrasBim_Camadas"]
    assert not model.doc.ifc.by_type("IfcElementQuantity")
    assert not model.doc.ifc.by_type("IfcShapeRepresentation")
    assert not model.doc.ifc.by_type("IfcRelContainedInSpatialStructure")
    assert len(list(model.doc.ifc)) == before


def test_p17_validacao_de_esquema(model, tmp_path):
    model.wall()
    model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo, (5, 0), (7, 2),
                                     (5, 4)))
    ifc = model.reopen(tmp_path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []
