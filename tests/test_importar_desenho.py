# SPDX-License-Identifier: LGPL-3.0-or-later
"""Importar desenho DXF/DWG (spec/ui/22-importar-desenho.md §6): ID01 a ID05."""

import math

import ezdxf
import pytest
from estrutura import check_history, valid

from brasbim.core import display_layers, plan, transform
from brasbim.core.annotations import base, reference
from brasbim.core.delete import delete_elements
from brasbim.core.document import OpError
from brasbim.core.imports import dxf

E0, N0 = 712_000.0, 7_462_000.0  # coordenadas UTM de um levantamento (m)


def levantamento(path, unit=6, scale=1.0):
    """DXF de um levantamento: curvas de nível com cota (LWPOLYLINE com elevação e
    POLYLINE 3D), divisa, árvore (bloco), texto de cota e ponto cotado."""
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = unit
    msp = doc.modelspace()
    for i, z in enumerate((100.0, 101.0, 102.0)):
        pts = [((E0 + x) * scale, (N0 + 2 + 4 * i + 0.5 * math.sin(x)) * scale)
               for x in range(0, 21, 2)]
        if i < 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer": "CURVAS", "elevation": z * scale})
        else:
            msp.add_polyline3d([(x, y, z * scale) for x, y in pts],
                               dxfattribs={"layer": "CURVAS"})
    msp.add_lwpolyline([(E0 * scale, N0 * scale), ((E0 + 20) * scale, N0 * scale),
                        ((E0 + 20) * scale, (N0 + 15) * scale), (E0 * scale, (N0 + 15) * scale)],
                       close=True, dxfattribs={"layer": "DIVISA"})
    tree = doc.blocks.new("ARVORE")
    tree.add_circle((0, 0), 1.5 * scale)
    tree.add_line((-1.5 * scale, 0), (1.5 * scale, 0))
    msp.add_blockref("ARVORE", ((E0 + 5) * scale, (N0 + 12) * scale),
                     dxfattribs={"layer": "VEGETACAO"})
    msp.add_text("101,50", height=0.25 * scale,
                 dxfattribs={"layer": "COTAS", "insert": ((E0 + 10) * scale, (N0 + 7) * scale),
                             "rotation": 30})
    msp.add_point(((E0 + 15) * scale, (N0 + 13) * scale, 102.4 * scale),
                  dxfattribs={"layer": "COTAS"})
    doc.saveas(path)
    return path


def test_id01_leitura(tmp_path):
    d = dxf.read(str(levantamento(tmp_path / "topo.dxf")))
    assert d.unit == "m" and d.source == "topo.dxf"
    assert set(d.layers) == {"CURVAS", "DIVISA", "VEGETACAO", "COTAS"}
    curves = d.layers["CURVAS"].lines
    assert sorted(line["z"] for line in curves) == [100.0, 101.0, 102.0]
    (border,) = d.layers["DIVISA"].lines
    assert border["closed"] and len(border["points"]) == 4
    tree = d.layers["VEGETACAO"].lines  # o bloco foi explodido: círculo e linha
    assert len(tree) == 2 and any(t["closed"] for t in tree)
    circle = next(t for t in tree if t["closed"])
    cx, cy = E0 + 5, N0 + 12
    assert all(abs(math.dist(p, (cx, cy)) - 1.5) < 0.011 for p in circle["points"])
    (text,) = d.layers["COTAS"].texts
    assert text["text"] == "101,50" and text["angle"] == pytest.approx(30)
    (point,) = d.layers["COTAS"].points
    assert point["z"] == pytest.approx(102.4)
    assert dxf.default_offset(d, "m") == pytest.approx((E0, N0))  # longe: vem para a origem


def test_id02_importar_em_metros(model, tmp_path):
    d = dxf.read(str(levantamento(tmp_path / "topo_mm.dxf", unit=4, scale=1000.0)))
    assert d.unit == "mm"

    def action():
        model.commit(dxf.import_drawing(model.doc, model.terreo, d, "mm",
                                        dxf.default_offset(d, "mm")))

    check_history(model, action)
    refs = [a for a in model.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)]
    assert len(refs) == 4
    by_layer = {base.read_state(a)["layer"]: base.read_state(a) for a in refs}
    assert by_layer["CURVAS"]["name"] == "Levantamento – CURVAS"
    border = by_layer["DIVISA"]["lines"][0]["points"]
    assert [tuple(q) for q in border] == [(0, 0), (20, 0), (20, 15), (0, 15)]
    assert sorted(line["z"] for line in by_layer["CURVAS"]["lines"]) == \
        pytest.approx([100, 101, 102])
    assert by_layer["COTAS"]["texts"][0]["height"] == pytest.approx(0.25)
    assert by_layer["COTAS"]["points"][0]["z"] == pytest.approx(102.4)
    assert valid(model.doc.ifc)


def test_id03_planta_camada_e_edicao(model, tmp_path):
    d = dxf.read(str(levantamento(tmp_path / "topo.dxf")))
    model.commit(dxf.import_drawing(model.doc, model.terreo, d, "m", (E0, N0),
                                    layers={"CURVAS", "DIVISA"}))
    refs = [a for a in model.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)]
    assert len(refs) == 2
    p = plan.storey_plan(model.doc, model.terreo)
    drawn = dict(p.annotations)
    assert all(a.GlobalId in drawn for a in refs)
    border = next(a for a in refs if base.read_state(a)["layer"] == "DIVISA")
    assert display_layers.kind_of(border) == "reference2d"
    config = display_layers.read_config(model.doc)
    if config is not None:
        target = display_layers.default_layer(config, "reference2d")
        assert display_layers.layer_name(model.doc, target) == "Levantamento"
    model.commit(transform.move_elements(model.doc, [border.GlobalId], (1.0, 2.0)))
    assert base.read_state(border)["lines"][0]["points"][0] == pytest.approx([1, 2])
    found = reference.lines_near([(border.GlobalId, base.read_state(border))], (11, 2.05), 0.1)
    assert found and found[0][2] == 0
    model.commit(delete_elements(model.doc, [border.GlobalId])[0])
    assert model.doc.find(border.GlobalId) is None


def test_id04_dwg_por_conversor(model, tmp_path, monkeypatch):
    source = levantamento(tmp_path / "gerado.dxf")
    dwg = tmp_path / "topo.dwg"
    dwg.write_bytes(b"AC1032 falso")
    monkeypatch.setattr(dxf, "_oda_path", lambda: None)
    monkeypatch.setattr(dxf.shutil, "which", lambda name: None)
    with pytest.raises(OpError, match="ODA File Converter"):
        dxf.read(str(dwg))
    assert dxf.converter() is None

    def fake(path, folder):  # o conversor externo devolve o DXF equivalente
        out = tmp_path / "convertido.dxf"
        out.write_bytes(source.read_bytes())
        return str(out)

    monkeypatch.setattr(dxf, "dwg_to_dxf", fake)
    d = dxf.read(str(dwg))
    assert d.source == "topo.dwg" and "CURVAS" in d.layers


def test_id05_recusas(model, tmp_path):
    d = dxf.read(str(levantamento(tmp_path / "topo.dxf")))
    with pytest.raises(OpError, match="unidade"):
        dxf.import_drawing(model.doc, model.terreo, d, "pol")
    with pytest.raises(OpError, match="nenhuma camada"):
        dxf.import_drawing(model.doc, model.terreo, d, "m", layers=set())
    bad = tmp_path / "ruim.dxf"
    bad.write_text("isto não é DXF", encoding="utf-8")
    with pytest.raises(OpError, match="ruim.dxf"):
        dxf.read(str(bad))


def test_id06_interface(window, app, tmp_path):
    pytest.importorskip("PySide6")
    from brasbim.ui.import_dialog import ImportDialog

    path = str(levantamento(tmp_path / "topo.dxf"))
    dialog = ImportDialog(dxf.read(path), "Térreo")
    layers, unit, offset = dialog.choice()
    assert layers == {"CURVAS", "DIVISA", "VEGETACAO", "COTAS"}
    assert unit == "m" and offset == pytest.approx((E0, N0))  # longe: vem para a origem
    s = window.session
    assert window.import_drawing(path, choose=lambda d: ({"CURVAS", "DIVISA"}, "m", (E0, N0)))
    refs = [a for a in s.doc.ifc.by_type("IfcAnnotation") if reference.is_reference(a)]
    assert len(refs) == 2
    assert "Importado topo.dxf: 2 camadas, 4 linhas" in s.messages[-1]["text"]
    assert window.import_drawing(str(tmp_path / "nao_existe.dxf"), choose=None) is False
    assert s.messages[-1]["level"] == "recusa"
