# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportar DWG/DXF (spec/ui/41-dwg-solidos-perfil-complexo.md §2): DG01–DG03."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import ezdxf
from ezdxf import recover

from brasbim.core import display_layers, pens
from brasbim.core.annotations import commands as ac
from brasbim.core.drawings import sheets
from brasbim.core.fillings import commands as fc
from brasbim.core.imports import libredwg
from brasbim.core.walls import commands as cmd
from brasbim.ui import dwg_export


def _casa(window):
    """Retângulo de paredes 6 × 4, porta na parede de baixo, cota e hachura."""
    s = window.session
    doc = s.doc
    s.run(lambda: cmd.create_rectangle(doc, window.toolbox.tools["wall"].options.type,
                                       s.storey, (0, 0), (6, 4)))
    south = min(doc.ifc.by_type("IfcWall"),
                key=lambda w: w.ObjectPlacement.RelativePlacement.Location.Coordinates[1]
                + abs(_angle(w)))
    s.run(lambda: fc.create_door_type(doc, "P1"))
    s.run(lambda: fc.create_door(doc, doc.ifc.by_type("IfcDoorType")[0], south, 2.0))
    s.run(lambda: ac.create_dimension(doc, s.storey, [(0, -1), (6, -1)]))
    s.run(lambda: ac.create_annotation(doc, "hatch", s.storey,
                                       outline=[[1, 1], [3, 1], [3, 2], [1, 2]],
                                       pattern="solid", color="#9C9A93"))
    s.run(lambda: ac.create_view(doc, "section", (3, -1), (3, 5), "left"))


def _angle(wall) -> float:
    """Direção da parede (0 = ao longo de x)."""
    axis = wall.ObjectPlacement.RelativePlacement.RefDirection
    return 0.0 if axis is None else abs(axis.DirectionRatios[1])


def _layer_names(doc) -> dict[str, str]:
    """Camada do BrasBim (nome) de cada ferramenta usada no teste."""
    config = display_layers.read_config(doc)
    return {lay["name"]: lay["id"] for lay in config["layers"]}


def test_dg01_planta_dxf_camadas_cores_espessuras(window, tmp_path):
    s = window.session
    _casa(window)
    path = tmp_path / "planta.dxf"
    n = dwg_export.export_item(s.doc, "plan", s.storey.GlobalId, str(path), "dxf")
    assert n > 0
    dxf = ezdxf.readfile(str(path))
    assert dxf.dxfversion == "AC1032"  # DXF 2018
    assert dxf.header["$INSUNITS"] == 5  # centímetros (resposta (a))
    msp = dxf.modelspace()
    used = {e.dxf.layer for e in msp}
    # Camadas do DWG = camadas do BrasBim, na ordem delas
    names = [lay.dxf.name for lay in dxf.layers]
    for name in ("Paredes", "Esquadrias", "Cotas", "Linhas e hachuras"):
        assert name in used, f"camada {name} sem nada"
    order = [n for n in names if n in _layer_names(s.doc)]
    expected = [lay["name"] for lay in display_layers.read_config(s.doc)["layers"]]
    assert order == [n for n in expected if n in order]
    # Em centímetros, na posição do projeto: as paredes vão de 0 a 600 cm (mais a
    # espessura para fora)
    xs = [x for e in msp.query("LWPOLYLINE[layer=='Paredes']")
          for x, *_ in e.get_points()]
    assert min(xs) == pytest.approx(0.0, abs=20) and max(xs) == pytest.approx(600, abs=20)
    # A cota: texto "6,00" (ou 600) e linhas na camada Cotas
    texts = [e.dxf.text for e in msp.query("TEXT[layer=='Cotas']")]
    assert texts, "o texto da cota vai"
    # A hachura sólida na cor dela (cor verdadeira) e a ACI mais próxima junto
    fills = list(msp.query("HATCH[layer=='Linhas e hachuras']"))
    assert any(h.dxf.true_color == ezdxf.rgb2int((0x9C, 0x9A, 0x93)) for h in fills)
    # Espessura da pena em cada objeto: a parede cortada sai com a pena de corte
    paper = pens.resolve(s.doc, None, paper=True)
    cut = max(e.dxf.lineweight for e in msp.query("LWPOLYLINE[layer=='Paredes']"))
    assert cut == dwg_export._lineweight(paper.weight("cut", 0.0005) * 1000) or cut >= 25
    thin = min(e.dxf.lineweight for e in msp.query("LWPOLYLINE"))
    assert thin < cut
    for e in msp.query("LWPOLYLINE"):
        assert e.dxf.hasattr("true_color") and e.dxf.color in range(1, 256)
    # Nada repetido entre a camada 0 e as outras
    assert not list(msp.query("LWPOLYLINE[layer=='0']"))


@pytest.mark.skipif(libredwg.find_writer() is None and dwg_export.find_writer() is None,
                    reason="sem o dxf2dwg do LibreDWG (scripts/baixar_libredwg.py)")
def test_dg01_dwg_relido(window, tmp_path):
    s = window.session
    _casa(window)
    path = tmp_path / "planta.dwg"
    dwg_export.export_item(s.doc, "plan", s.storey.GlobalId, str(path), "dwg")
    data = path.read_bytes()
    assert data[:6] == b"AC1015"  # DWG 2000
    back = tmp_path / "relido.dxf"
    exe = libredwg.find()
    assert exe is not None
    libredwg.convert(exe, str(path), str(back))
    dxf, _ = recover.readfile(str(back))
    msp = dxf.modelspace()
    used = {e.dxf.layer for e in msp}
    assert {"Paredes", "Esquadrias", "Cotas", "Linhas e hachuras"} <= used
    original = ezdxf.readfile(str(_dxf_of(s, tmp_path)))
    for kind in ("LWPOLYLINE", "TEXT", "HATCH"):
        before = len(original.modelspace().query(kind))
        after = len(msp.query(kind))
        assert after == before, f"{kind}: {before} → {after}"
    weights = {e.dxf.lineweight for e in msp.query("LWPOLYLINE")}
    assert len(weights) > 1  # as espessuras das penas voltam
    # Textos à esquerda na linha de base (o dxf2dwg perde o ponto dos centrados): o
    # rótulo da porta fica junto dela, não no 0,0
    for text in msp.query("TEXT"):
        assert not text.dxf.get("halign", 0) and not text.dxf.get("valign", 0)
    (tag,) = [t for t in msp.query("TEXT") if t.dxf.text == "P1"]
    assert 200 < tag.dxf.insert[0] < 400 and 0 < tag.dxf.insert[1] < 100


def _dxf_of(s, tmp_path):
    path = tmp_path / "mesma.dxf"
    dxf = dwg_export.new_document("dwg")  # o DXF 2000 que vai para o conversor
    dwg_export.write_view(dxf, s.doc, dwg_export.item_of("plan", s.storey.GlobalId))
    dxf.saveas(str(path))
    return path


def test_dg01_corte_e_vista_salva(window, tmp_path):
    s = window.session
    _casa(window)
    view = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")
    path = tmp_path / "corte.dxf"
    assert dwg_export.export_item(s.doc, "view", view.GlobalId, str(path), "dxf") > 0
    dxf = ezdxf.readfile(str(path))
    assert "Paredes" in {e.dxf.layer for e in dxf.modelspace()}
    # Faces escondidas (cor do papel) não vão como linhas brancas
    white = ezdxf.rgb2int((255, 255, 255))
    assert not [e for e in dxf.modelspace() if e.dxf.get("true_color") == white]


def test_dg02_prancha_no_papel_com_blocos(window, tmp_path):
    s = window.session
    _casa(window)
    window.project.add_sheet({})
    (sheet,) = sheets.all_sheets(s.doc)
    s.run(lambda: sheets.add_to_sheet(s.doc, sheet, {"kind": "plan",
                                                     "storey": s.storey.GlobalId}))
    path = tmp_path / "prancha.dxf"
    dwg_export.export_item(s.doc, "sheet", sheet.GlobalId, str(path), "dxf")
    dxf = ezdxf.readfile(str(path))
    state = sheets.read_state(sheet)
    w, h = sheets.paper_of(s.doc, state)
    (name,) = [n for n in dxf.layouts.names() if n != "Model"]
    assert name == "Prancha 01"
    layout = dxf.layouts.get(name)
    assert dxf.header["$INSUNITS"] == 4  # mm de papel
    # Moldura e carimbo em linhas e textos na camada Prancha, dentro do papel
    frame = list(layout.query("LWPOLYLINE[layer=='Prancha']"))
    assert frame and list(layout.query("TEXT[layer=='Prancha']"))
    for e in frame:
        for x, y, *_ in e.get_points():
            assert -0.01 <= x <= w + 0.01 and -0.01 <= y <= h + 0.01
    # O desenho: um bloco em cm inserido na escala da vista
    (ref,) = layout.query("INSERT")
    den = sheets.scale_of(s.doc, state["views"][0])
    assert ref.dxf.xscale == pytest.approx(10 / den)
    assert tuple(ref.dxf.insert)[:2] == pytest.approx(tuple(state["views"][0]["at"]))
    block = dxf.blocks.get(ref.dxf.name)
    assert "Paredes" in {e.dxf.layer for e in block}
    xs = [x for e in block.query("LWPOLYLINE[layer=='Paredes']") for x, *_ in e.get_points()]
    assert max(xs) == pytest.approx(600, abs=20)  # em cm, na posição do projeto
    # A largura no papel: 6 m na escala → (600 cm × 10/den) mm
    assert (max(xs) - min(xs)) * ref.dxf.xscale == pytest.approx(6000 / den, rel=0.05)


def test_dg03_sem_conversor_oferece_dxf(window, tmp_path, monkeypatch):
    s = window.session
    _casa(window)
    monkeypatch.setattr(dwg_export, "find_writer", lambda: None)
    asked = []
    monkeypatch.setattr(window, "ask_dwg_writer", lambda: asked.append(1) or "dxf")
    items = [("plan", s.storey.GlobalId, "Planta Térreo")]
    done = window.export_drawings(items, "dwg", str(tmp_path))
    assert asked and done == [str(tmp_path / "Planta Térreo.dxf")]
    assert (tmp_path / "Planta Térreo.dxf").is_file()
    # Desistir não grava nada
    monkeypatch.setattr(window, "ask_dwg_writer", lambda: "cancel")
    assert window.export_drawings(items, "dwg", str(tmp_path / "outra")) == []
    # Baixar: instala e grava DWG (aqui o download é trocado por um conversor falso)
    installed = []

    def fake_install(*_args, **_kwargs):
        installed.append(1)
        monkeypatch.setattr(dwg_export, "find_writer", lambda: "dxf2dwg")
        return "dwg2dxf"

    monkeypatch.setattr(libredwg, "install", fake_install)
    monkeypatch.setattr(window, "ask_dwg_writer", lambda: "download")
    monkeypatch.setattr(libredwg, "write_dwg",
                        lambda exe, src, out: Path(out).write_bytes(b"AC1015"))
    done = window.export_drawings(items, "dwg", str(tmp_path))
    assert installed and done == [str(tmp_path / "Planta Térreo.dwg")]


def test_dg03_install_extrai_o_dxf2dwg(tmp_path):
    import io
    import zipfile

    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as package:
        for name in (*libredwg.FILES, libredwg.WRITER):
            package.writestr(f"libredwg/bin/{name}", b"x")
    payload = data.getvalue()
    import hashlib

    old = libredwg.SHA256
    libredwg.SHA256 = hashlib.sha256(payload).hexdigest()
    try:
        libredwg.install(tmp_path, data=payload)
    finally:
        libredwg.SHA256 = old
    assert (tmp_path / libredwg.WRITER).is_file()
    assert "dxf2dwg" in (tmp_path / "LEIA-ME.txt").read_text(encoding="utf-8")


def test_dg_quadro_e_navegador(window, tmp_path, monkeypatch):
    from brasbim.ui.export_dialog import ExportDwgDialog, drawing_items

    s = window.session
    _casa(window)
    window.project.add_sheet({})
    groups = dict(drawing_items(s.doc))
    assert set(groups) == {"Plantas", "Cortes e fachadas", "Pranchas"}
    dialog = ExportDwgDialog(s.doc, str(tmp_path), {s.storey.GlobalId})
    assert [c[0] for c in dialog.chosen()] == ["plan"]
    assert dialog.fmt() == "dwg"
    assert "…" not in dialog.windowTitle()
    # Botão direito no Navegador: corte e prancha
    view = next(v for v in s.doc.ifc.by_type("IfcAnnotation") if v.ObjectType == "VistaDeCorte")
    texts = [a.text() for a in window.project.view_menu(view.GlobalId).actions()]
    assert "Exportar DWG" in texts
    (sheet,) = sheets.all_sheets(s.doc)
    texts = [a.text() for a in window.project.sheet_menu(sheet.GlobalId).actions()]
    assert "Exportar DWG" in texts
    path = window.export_dwg_item("view", view.GlobalId, str(tmp_path / "corte.dxf"))
    assert path == str(tmp_path / "corte.dxf")
    # Menu Arquivo
    menu = window.menuBar().actions()[0].menu()
    assert "Exportar DWG/DXF" in [a.text() for a in menu.actions()]


@pytest.mark.skipif(dwg_export.find_writer() is None,
                    reason="sem o dxf2dwg do LibreDWG (scripts/baixar_libredwg.py)")
def test_dg01_area_em_dwg(window, tmp_path):
    from brasbim.core.selection_area import Area

    s = window.session
    _casa(window)
    window.ctx.area = Area.rectangle((2.0, -1.0), (5.0, 1.0))
    path = window.export_area("dwg", str(tmp_path / "area"))
    assert path.endswith(".dwg") and Path(path).read_bytes()[:6] == b"AC1015"
    assert s.messages[-1]["text"].startswith("área exportada")
