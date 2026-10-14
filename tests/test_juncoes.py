# SPDX-License-Identifier: LGPL-3.0-or-later
"""Junções L/T/X da parede (spec §6.2; critérios P05, P06, P07)."""

import math

import ifcopenshell.util.element as ue
import pytest
from conftest import snapshot

from brasbim.core import geom2d
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import rebuild
from brasbim.core.walls.wall import read_state

T = 0.14
H = 2.8


def _qto(wall):
    return ue.get_pset(wall, "Qto_WallBaseQuantities")


def _rels(ifc):
    return ifc.by_type("IfcRelConnectsPathElements")


def _walls(model, tx):
    return [model.doc.get(op.id) for op in tx.ops if op.op == "wall.create"]


def _type(model, name, thickness):
    model.commit(cmd.create_wall_type(model.doc, name, [{"material": "M", "thickness": thickness}]))
    return next(t for t in model.doc.ifc.by_type("IfcWallType") if t.Name == name)


def _global_profile(model, wall):
    band = rebuild.band(model.doc, read_state(model.doc, wall))
    segments = rebuild.profile(model.doc, wall, band)
    to_global = band.frame.to_global
    return [tuple(to_global(p) for p in seg) for seg in segments]


def _max_x(model, wall):
    return max(p[0] for seg in _global_profile(model, wall) for p in seg)


def test_p05_cadeia_e_retangulo(model, tmp_path):
    tx = model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                       [(0, 0), (4, 0), (4, 3), (0, 3)]))
    assert [op.op for op in tx.ops] == ["wall.create"] * 3 + ["path_connection.create"] * 2
    a, b, c = _walls(model, tx)
    ifc = model.reopen(tmp_path)
    assert len(ifc.by_type("IfcWall")) == 3
    rels = _rels(ifc)
    assert len(rels) == 2
    pairs = {(r.RelatingElement.GlobalId, r.RelatedElement.GlobalId) for r in rels}
    assert pairs == {(a.GlobalId, b.GlobalId), (b.GlobalId, c.GlobalId)}
    for r in rels:
        assert (r.RelatingConnectionType, r.RelatedConnectionType) == ("ATEND", "ATSTART")

    model.history.undo()
    tx = model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (8, 5), (0, 0)))
    ifc = model.reopen(tmp_path)
    assert len(ifc.by_type("IfcWall")) == 4
    rels = _rels(ifc)
    assert len(rels) == 4
    assert all((r.RelatingConnectionType, r.RelatedConnectionType) == ("ATEND", "ATSTART")
               for r in rels)
    # Meia-esquadria nos 4 cantos: as paredes ocupam exatamente o anel do retângulo.
    total = sum(_qto(w)["NetFootprintArea"] for w in ifc.by_type("IfcWall"))
    assert total == pytest.approx(8 * 5 - (8 - 2 * T) * (5 - 2 * T))
    for w in ifc.by_type("IfcWall"):
        assert _qto(w)["NetVolume"] == pytest.approx(_qto(w)["NetFootprintArea"] * H)


def test_cadeia_fechada(model):
    tx = model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                       [(0, 0), (4, 0), (4, 3)], closed=True))
    first, *_, last = _walls(model, tx)
    rels = _rels(model.doc.ifc)
    assert len(rels) == 3
    closing = next(r for r in rels if r.RelatedElement == first)
    assert closing.RelatingElement == last


def test_l_espessuras_diferentes(model):
    t19 = _type(model, "Bloco 19", 0.19)
    a = model.wall((0, 0), (5, 0), ref_line="axis")
    model.commit(cmd.create_wall(model.doc, t19, model.terreo, (5, 0), (5, 4), ref_line="axis"))
    b = next(w for w in model.doc.ifc.by_type("IfcWall") if w != a)
    # A mais espessa (b) vai até a face externa de a; a mais fina para na face interna de b.
    assert _qto(a)["NetFootprintArea"] == pytest.approx((5 - 0.095) * T)
    assert _qto(b)["NetFootprintArea"] == pytest.approx((4 + T / 2) * 0.19)
    assert _qto(a)["Length"] == pytest.approx(5)  # Length sem recortes (spec §8)


def test_l_colinear(model):
    tx = model.commit(cmd.create_chain(model.doc, model.type14, model.terreo,
                                       [(0, 0), (2, 0), (5, 0)]))
    a, b = _walls(model, tx)
    assert len(_rels(model.doc.ifc)) == 1
    assert _qto(a)["NetFootprintArea"] == pytest.approx(2 * T)
    assert _qto(b)["NetFootprintArea"] == pytest.approx(3 * T)


def test_l_reta_com_arco_compartilha_o_corte(model):
    a = model.wall((0, 0), (4, 0), ref_line="axis")
    tx = model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                          (4, 0), (6, 2), (4, 4), ref_line="axis"))
    (b,) = _walls(model, tx)
    assert len(_rels(model.doc.ifc)) == 1
    end_cap_a = _global_profile(model, a)[1]
    start_cap_b = _global_profile(model, b)[3]
    assert {tuple(round(c, 9) for c in p) for p in (end_cap_a[0], end_cap_a[-1])} == {
        tuple(round(c, 9) for c in p) for p in (start_cap_b[0], start_cap_b[-1])
    }


def test_p06_juncao_t(model, tmp_path):
    a = model.wall((0, 0), (6, 0), ref_line="axis")
    b = model.wall((3, 0), (3, 4), ref_line="axis")
    ifc = model.reopen(tmp_path)
    (rel,) = _rels(ifc)
    assert rel.RelatingElement.GlobalId == a.GlobalId
    assert rel.RelatedElement.GlobalId == b.GlobalId
    assert (rel.RelatingConnectionType, rel.RelatedConnectionType) == ("ATPATH", "ATSTART")
    by_id = {w.GlobalId: w for w in ifc.by_type("IfcWall")}
    assert _qto(by_id[b.GlobalId])["NetVolume"] == pytest.approx((4 - T / 2) * T * H)
    assert _qto(by_id[a.GlobalId])["NetVolume"] == pytest.approx(6 * T * H)


def test_t_em_parede_curva(model):
    model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo,
                                     (2, 0), (0, 2), (-2, 0), ref_line="axis"))
    b = model.wall((0, 0), (0, 2), ref_line="axis")
    (rel,) = _rels(model.doc.ifc)
    assert (rel.RelatingConnectionType, rel.RelatedConnectionType) == ("ATPATH", "ATEND")
    # b termina na face interna do arco (r = 1,93): tampa em arco.
    r, w = 2 - T / 2, T / 2

    def primitive(x):
        return x / 2 * math.sqrt(r * r - x * x) + r * r / 2 * math.asin(x / r)

    assert _qto(b)["NetFootprintArea"] == pytest.approx(2 * primitive(w), rel=1e-9)


def test_p07_juncao_x(model, tmp_path):
    a = model.wall((0, 0), (4, 0), ref_line="axis")
    b = model.wall((2, -2), (2, 2), ref_line="axis")
    ifc = model.reopen(tmp_path)
    assert len(ifc.by_type("IfcWall")) == 2
    (rel,) = _rels(ifc)
    assert (rel.RelatingConnectionType, rel.RelatedConnectionType) == ("ATPATH", "ATPATH")
    assert rel.RelatingElement.GlobalId == a.GlobalId
    by_id = {w.GlobalId: w for w in ifc.by_type("IfcWall")}
    assert _qto(by_id[a.GlobalId])["NetVolume"] == pytest.approx(4 * T * H)
    assert _qto(by_id[b.GlobalId])["NetVolume"] == pytest.approx(4 * T * H)


def test_sem_juncao_em_outro_pavimento_ou_alturas_disjuntas(model):
    model.wall((0, 0), (4, 0))
    model.commit(cmd.create_wall(model.doc, model.type14, model.superior, (4, 0), (4, 3)))
    model.wall((4, 0), (8, 0), top_mode="fixed", base_offset=2.9, fixed_height=1.0)
    assert not _rels(model.doc.ifc)


def test_editar_desfaz_e_refaz_juncao(model):
    a = model.wall((0, 0), (4, 0), ref_line="axis")
    b = model.wall((4, 0), (4, 3), ref_line="axis")
    with_join = snapshot(model.doc.ifc)
    assert _max_x(model, a) == pytest.approx(4 + T / 2)

    model.commit(cmd.edit_wall(model.doc, b, path={"kind": "line", "start": [6, 0],
                                                   "end": [6, 3]}))
    assert not _rels(model.doc.ifc)
    assert _max_x(model, a) == pytest.approx(4)

    model.history.undo()
    assert snapshot(model.doc.ifc) == with_join


def test_excluir_remove_juncao_e_recorte_da_vizinha(model):
    a = model.wall((0, 0), (4, 0), ref_line="axis")
    b = model.wall((4, 0), (4, 3), ref_line="axis")
    tx = model.commit(cmd.delete_wall(model.doc, b))
    assert [op.op for op in tx.ops] == ["path_connection.delete", "wall.delete"]
    assert not _rels(model.doc.ifc)
    assert _max_x(model, a) == pytest.approx(4)


def test_geom2d_corte_reta_e_circulo():
    path = geom2d.LinePath((0, 0), (4, 0))
    cut = geom2d.Circle((5, 0), 1.5)  # extremidade final recortada por um arco
    segments = geom2d.band_profile(path, -0.1, 0.1, end_cut=cut)
    assert isinstance(segments[1], geom2d.Arc)
    x = 5 - math.sqrt(1.5**2 - 0.1**2)
    assert segments[0].p1 == pytest.approx((x, -0.1))


def test_p17_validacao_com_juncoes(model, tmp_path):
    import ifcopenshell.validate

    model.commit(cmd.create_rectangle(model.doc, model.type14, model.terreo, (0, 0), (8, 5)))
    model.wall((4, 0), (4, 5))
    model.commit(cmd.create_arc_wall(model.doc, model.type14, model.terreo, (8, 1), (9.5, 2.5),
                                     (8, 4), ref_line="axis"))
    ifc = model.reopen(tmp_path)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, log)
    assert log.statements == []
    assert len(_rels(ifc)) == 4 + 2 + 2
