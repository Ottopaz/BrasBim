# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho importado só como linhas, leve e rápido (spec/ui/22-importar-desenho.md §7):
ID13 a ID18."""

import ezdxf
import pytest
from test_importar_desenho import E0, N0, levantamento

from brasbim.core import plan, snap, transform
from brasbim.core.annotations import base, reference
from brasbim.core.annotations import commands as ac
from brasbim.core.imports import dxf
from brasbim.core.linework import Lines


def _ezdxf_only(monkeypatch):
    monkeypatch.setattr(dxf, "_read_fast", lambda path, source: None)


def _summary(d):
    return {name: (len(layer.lines), len(layer.texts), len(layer.points))
            for name, layer in d.layers.items()}


def test_id13_leitor_rapido_igual_ao_ezdxf(tmp_path, monkeypatch):
    path = str(levantamento(tmp_path / "topo.dxf"))
    fast = dxf.read(path)
    _ezdxf_only(monkeypatch)
    slow = dxf.read(path)
    assert _summary(fast) == _summary(slow)
    assert fast.unit == slow.unit == "m"
    assert fast.bounds() == pytest.approx(slow.bounds(), abs=0.02)
    assert sorted(line["z"] for line in fast.layers["CURVAS"].lines) == [100.0, 101.0, 102.0]
    assert fast.layers["COTAS"].texts[0]["angle"] == pytest.approx(30.0)


def test_id14_casos_do_dxf(tmp_path, monkeypatch):
    """Espaço de papel fora, bloco espelhado (extrusão para baixo), arco em polilinha,
    spline, inserção em matriz e direção do MTEXT."""
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    block = doc.blocks.new("PECA")
    block.add_line((0, 0), (2, 0))
    block.add_line((0, 0), (0, 1), dxfattribs={"layer": "OUTRA"})
    msp.add_blockref("PECA", (10, 0), dxfattribs={"layer": "BLOCO", "rotation": 30})
    msp.add_blockref("PECA", (20, 0), dxfattribs={"layer": "ESPELHO",
                                                  "extrusion": (0, 0, -1), "rotation": 30})
    grid = msp.add_blockref("PECA", (0, 10), dxfattribs={"layer": "MATRIZ"})
    grid.dxf.column_count, grid.dxf.row_count = 3, 2
    grid.dxf.column_spacing, grid.dxf.row_spacing = 5, 4
    msp.add_lwpolyline([(0, 0, 0, 0, 1), (2, 0, 0, 0, 0)], format="xyseb",
                       dxfattribs={"layer": "ARCO"})  # meia-volta: bulge 1
    msp.add_spline([(0, 0), (1, 2), (3, 1), (4, 3)], dxfattribs={"layer": "CURVA"})
    msp.add_mtext("ROT", dxfattribs={"layer": "TXT", "insert": (0, 0),
                                     "text_direction": (0, 1, 0)})
    doc.layout("Layout1").add_line((0, 0), (999, 999), dxfattribs={"layer": "PAPEL"})
    path = tmp_path / "casos.dxf"
    doc.saveas(path)
    fast = dxf.read(str(path))
    _ezdxf_only(monkeypatch)
    slow = dxf.read(str(path))
    assert "PAPEL" not in fast.layers
    # A matriz (MINSERT) o ezdxf explode só a primeira cópia; aqui vêm todas.
    same = ("BLOCO", "ESPELHO", "ARCO", "CURVA")
    assert {k: _summary(fast)[k] for k in same} == {k: _summary(slow)[k] for k in same}
    for name in same:
        a = Lines.from_dicts(fast.layers[name].lines)
        b = Lines.from_dicts(slow.layers[name].lines)
        assert a.bounds() == pytest.approx(b.bounds(), abs=0.02), name
    assert len(fast.layers["MATRIZ"].lines) == 6
    top = max(abs(p[1]) for line in fast.layers["ARCO"].lines for p in line["points"])
    assert top == pytest.approx(1.0, abs=0.02)  # o arco do bulge, não a reta
    assert fast.layers["TXT"].texts[0]["angle"] == pytest.approx(90.0)


def test_id15_linhas_sem_geometria_ifc(model, tmp_path):
    d = dxf.read(str(levantamento(tmp_path / "topo.dxf")))
    tx = model.commit(dxf.import_drawing(model.doc, model.terreo, d, "m", (E0, N0)))
    assert all("lines" not in op.data and op.data["packed"] for op in tx.ops)
    refs = [a for a in model.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)]
    assert refs and all(a.Representation is None for a in refs)  # só os parâmetros
    assert not model.doc.ifc.by_type("IfcIndexedPolyCurve")
    curves = next(a for a in refs if base.read_state(a)["layer"] == "CURVAS")
    lines = reference.lines_of(base.read_state(curves))
    assert len(lines) == 3 and base.read_state(curves)["count"] == 3
    # Mover leva as linhas (transformação afim, em bloco) e desfaz.
    model.commit(transform.move_elements(model.doc, [curves.GlobalId], (1.0, 2.0)))
    moved = reference.lines_of(base.read_state(curves))
    assert moved.coords == pytest.approx(lines.coords + (1.0, 2.0))
    model.history.undo()
    assert reference.lines_of(base.read_state(curves)).coords == pytest.approx(lines.coords)


def test_id16_arquivo_antigo(model):
    """O formato de antes (lista de linhas) continua sendo lido e passa para o
    compactado quando é transformado."""
    tx = ac.create_annotation(model.doc, "reference2d", model.terreo, name="Antigo",
                              source="x.dxf", layer="A", texts=[], points=[])
    tx.ops[0].data["lines"] = [{"points": [[0, 0], [4, 0]], "closed": False, "z": None}]
    model.commit(tx)
    old = model.doc.get(tx.ops[0].id)
    assert reference.lines_of(base.read_state(old)).line(0)["points"] == [[0, 0], [4, 0]]
    assert plan.storey_plan(model.doc, model.terreo).pick((2.0, 0.01), 0.05) == old.GlobalId
    model.commit(transform.move_elements(model.doc, [old.GlobalId], (0.0, 1.0)))
    state = base.read_state(old)
    assert "lines" not in state and state["packed"]
    assert reference.lines_of(state).line(0)["points"] == [[0, 1], [4, 1]]
    model.history.undo()
    assert reference.lines_of(base.read_state(old)).line(0)["points"] == [[0, 0], [4, 0]]


def test_id17_escolha_selecao_e_atracao(model):
    lines = [{"points": [[0, 0], [10, 0], [10, 5]], "closed": False, "z": None},
             {"points": [[20, 0], [21, 1], [22, 0]], "closed": True, "z": None}]
    model.commit(ac.create_annotation(model.doc, "reference2d", model.terreo, name="R",
                                      source="x.dxf", layer="A", texts=[], points=[],
                                      **reference.pack_lines(lines)))
    (ref,) = [a for a in model.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)]
    p = plan.storey_plan(model.doc, model.terreo)
    assert [o for o, _ in p.bulk] == [ref.GlobalId]
    assert not [s for s in p.shapes if s.owner == ref.GlobalId]  # nenhuma forma por linha
    assert p.pick((5.0, 0.02), 0.05) == ref.GlobalId
    assert p.pick((5.0, 2.0), 0.05) is None
    assert p.bounds() == pytest.approx((0, 0, 22, 5))
    assert p.in_rect((-1, -1), (23, 6)) == [ref.GlobalId]
    assert p.in_rect((-1, -1), (11, 6)) == []  # janela: tem de estar inteiro
    assert p.in_rect((-1, -1), (11, 6), crossing=True) == [ref.GlobalId]
    index = snap.build_index(model.doc, model.terreo, p)
    s = snap.snap([], (10.03, 0.02), 0.1, index=index)
    assert (s.kind, s.point) == ("end", pytest.approx((10, 0)))
    assert snap.snap([], (5.0, 0.03), 0.1, index=index).kind == "mid"


def test_id18_linhas_em_arrays():
    lines = Lines.from_dicts([
        {"points": [[0, 0], [1, 0], [1, 1]], "closed": True, "z": None},
        {"points": [[5, 5], [6, 5]], "closed": False, "z": 101.5}])
    again = Lines.unpack(lines.pack())
    assert again.to_dicts() == lines.to_dicts()
    a, _, which, straight = lines.segments()
    assert len(a) == 4 and sorted(which.tolist()) == [0, 0, 0, 1] and straight.all()
    found, dist = lines.near((0.5, 0.05), 0.1)
    assert len(found) == 1 and dist == pytest.approx([0.05])
    turned = lines.mapped(lambda p: (-p[1], p[0]))  # 90°: afim
    assert turned.coords[:3].ravel() == pytest.approx([0, 0, 0, 1, -1, 1])
    bent = lines.mapped(lambda p: (p[0], p[1] + p[0] ** 2))  # não afim: ponto a ponto
    assert bent.coords[3:].ravel() == pytest.approx([5, 30, 6, 41])
