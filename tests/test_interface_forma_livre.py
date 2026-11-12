# SPDX-License-Identifier: GPL-3.0-or-later
"""Forma livre na interface (spec/elementos/forma-livre.md §4 a §6): Propriedades,
importar arquivo, converter a seleção, 3D e a prévia do Assistente. Qt sem tela."""

import base64
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import numpy as np
from conftest import snapshot
from PySide6.QtGui import QAction, QImage
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from brasbim.core.freeform import commands as fc
from brasbim.core.freeform import elements as ff
from brasbim.core.freeform import mesh
from brasbim.core.objects import commands as oc
from brasbim.core.objects import library
from brasbim.core.objects import types as ot
from brasbim.ui import mesh_render
from brasbim.ui.freeform_dialog import FreeformImportDialog

RECIPE = [
    {"kind": "box", "name": "Assento", "size": [0.8, 0.7, 0.2], "radius": 0.06,
     "position": [0.4, 0.35, 0.3], "material": "Couro"},
    {"kind": "cone", "name": "Pé", "radius": 0.03, "top_radius": 0.02, "height": 0.3,
     "position": [0.1, 0.1, 0.0], "material": "Madeira"},
]


def _make(window):
    s = window.session
    tx = fc.from_recipe(s.doc, s.storey, RECIPE, (1.0, 1.0), name="Poltrona",
                        category="furniture")
    assert s.run(tx)
    return tx.ops[-1].id


def _field(window, name):
    QApplication.processEvents()  # o painel se refaz depois do evento
    return next(w for g in window.properties.groups for n, w in g.rows if n == name)


def _cube_obj(path, size=100.0):
    s = size
    lines = [f"v {x} {y} {z}" for x in (0, s) for y in (0, s) for z in (0, 2 * s)]
    lines += ["usemtl Bronze", "f 1 2 4 3", "f 5 7 8 6", "f 1 5 6 2", "f 3 4 8 7",
              "f 1 3 7 5", "f 2 6 8 4"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_fl08_propriedades(window):
    s = window.session
    gid = _make(window)
    s.select([gid])
    QApplication.processEvents()
    panel = window.properties
    assert panel.groups[0].title == "Forma livre"
    names = [n for g in panel.groups for n, _ in g.rows]
    for expected in ("Nome", "Categoria", "Rotação (°)", "Elevação (m)", "Manter proporção",
                     "Largura (m)", "Profundidade (m)", "Altura (m)", "Couro", "Madeira",
                     "Triângulos", "GlobalId"):
        assert expected in names, expected
    # mudar a altura estica a malha (proporção ligada: as outras acompanham)
    before = mesh.size(ff.read_state(s.doc, s.doc.get(gid))["parts"])
    field = _field(window, "Altura (m)")
    field.setText("1,00")
    field.editingFinished.emit()
    after = mesh.size(ff.read_state(s.doc, s.doc.get(gid))["parts"])
    assert after[2] == pytest.approx(1.0, abs=1e-3)
    assert after[0] / before[0] == pytest.approx(1.0 / before[2], rel=1e-3)
    # sem a proporção, só a medida mudada
    _field(window, "Manter proporção").setChecked(False)
    field = _field(window, "Largura (m)")
    field.setText("2,00")
    field.editingFinished.emit()
    final = mesh.size(ff.read_state(s.doc, s.doc.get(gid))["parts"])
    assert final == pytest.approx((2.0, after[1], after[2]), abs=1e-3)
    # categoria muda a classe, o elemento continua selecionado
    combo = _field(window, "Categoria")
    combo.setCurrentIndex(combo.findData("proxy"))
    combo.activated.emit(combo.currentIndex())
    assert s.doc.get(gid).is_a("IfcBuildingElementProxy")
    # material de uma parte
    combo = _field(window, "Couro")
    combo.setCurrentIndex(combo.findData("Tecido"))
    combo.activated.emit(combo.currentIndex())
    assert ff.read_state(s.doc, s.doc.get(gid))["parts"][0]["material"] == "Tecido"


def test_fl09_importar_arquivo(window, tmp_path):
    s = window.session
    path = _cube_obj(tmp_path / "bloco.obj")
    # o diálogo mostra as medidas com a unidade escolhida
    dialog = FreeformImportDialog(path, window)
    assert dialog.name.text() == "bloco"
    assert "100,00 × 100,00 × 200,00 m" in dialog.summary.text()
    dialog.unit.setCurrentIndex(dialog.unit.findData("cm"))
    assert "1,00 × 1,00 × 2,00 m" in dialog.summary.text() and "12 triângulos" in \
        dialog.summary.text()
    assert dialog.buttons.button(QDialogButtonBox.Ok).isEnabled()
    assert dialog.choice() == {"name": "bloco", "unit": "cm", "up": "z", "category": "proxy"}
    # importar: a peça entra no meio da planta, selecionada
    gid = window.import_freeform(path, choose={"name": "Bloco", "unit": "cm",
                                               "category": "furniture"})
    assert gid and s.selection == {gid}
    e = s.doc.get(gid)
    state = ff.read_state(s.doc, e)
    assert e.is_a("IfcFurniture") and state["name"] == "Bloco"
    assert state["source"] == "arquivo bloco.obj" and state["recipe"] is None
    assert ff.box_of(state)["altura"] == pytest.approx(2.0)
    assert [p["name"] for p in state["parts"]] == ["Bronze"]
    center = window.plan.to_world(window.plan.rect().center())
    assert state["point"] == pytest.approx(list(center), abs=0.1)
    # arquivo ruim: recusa com mensagem, nada criado
    before = snapshot(s.doc.ifc)
    bad = tmp_path / "ruim.glb"
    bad.write_bytes(b"nao e glb")
    assert window.import_freeform(str(bad), choose={}) is None
    assert snapshot(s.doc.ifc) == before
    dialog = FreeformImportDialog(str(bad), window)
    assert not dialog.buttons.button(QDialogButtonBox.Ok).isEnabled()
    assert "GLB" in dialog.summary.text()
    actions = {a.text() for a in window.findChildren(QAction)}
    assert {"Importar forma livre (OBJ, STL, GLB)", "Converter em forma livre"} <= actions


def test_fl10_converter_a_selecao(window):
    s = window.session
    doc = s.doc
    entries = library.Index([library.builtin_folder()]).entries()
    assert s.run(library.load(doc, entries, [e for e in entries if e.name == "Fogão 4 bocas"]))
    tx = oc.create_object(doc, ot.by_name(doc, "Fogão 4 bocas"), s.storey, (2.0, 2.0))
    assert s.run(tx)
    other = _make(window)
    s.select([tx.ops[-1].id, other])
    undo = len(s.history.undo_stack)
    gid = window.convert_to_freeform()
    assert gid and s.selection == {gid} and len(s.history.undo_stack) == undo + 1
    (e,) = ff.all_freeforms(doc)
    assert e.GlobalId == gid and len(ff.read_state(doc, e)["parts"]) >= 3
    window.undo()
    assert len(ff.all_freeforms(doc)) == 1 and doc.find(tx.ops[-1].id) is not None
    # nada que sirva selecionado
    s.select([])
    assert window.convert_to_freeform() is None


def test_fl11_no_3d_e_na_previa_do_assistente(window):
    s = window.session
    gid = _make(window)
    scene_mesh = window.scene.meshes[gid]
    state = ff.read_state(s.doc, s.doc.get(gid))
    assert len(scene_mesh.vertices) == 3 * mesh.triangle_count(state["parts"])
    # arestas: só as quinas, bem menos que uma por triângulo
    assert 0 < len(scene_mesh.edges) < len(scene_mesh.vertices) / 3
    # duas cores (couro e madeira)
    assert len({tuple(np.round(c, 2)) for c in scene_mesh.colors[::7]}) > 2
    a = window.assistant
    before = snapshot(s.doc.ifc)
    result = a.execute("view_object", {"id": gid})
    assert not result["isError"], result
    picture, text = result["content"]
    image = QImage()
    assert image.loadFromData(base64.b64decode(picture["data"])) and image.width() == 840
    assert json.loads(text["text"])["caixa"]["largura"] == pytest.approx(0.8)
    assert snapshot(s.doc.ifc) == before
    result = a.execute("view_object", {"id": s.storey.GlobalId})
    assert result["isError"] and "não é forma livre" in result["content"][0]["text"]
    # ao fim do pedido, a forma livre criada fica selecionada
    a._prompt = "uma poltrona"
    made = a.execute("create_freeform", {"name": "Banco", "shapes": RECIPE, "at": [3, 3]})
    assert not made["isError"], made
    new = json.loads(made["content"][0]["text"])["id"]
    a._group()
    assert s.selection == {new}


def test_fl12_previa_respeita_a_profundidade():
    """Uma placa vermelha na frente (−y) de uma azul maior: de frente, o meio é vermelho e
    a borda, azul; por trás, tudo azul."""
    def plate(y, half, group):
        a, b, c, d = ([-half, y, 0.0], [half, y, 0.0], [half, y, 2 * half], [-half, y, 2 * half])
        return [(a, b, c), (a, c, d)], group

    front, back = plate(-1.0, 0.5, 0), plate(1.0, 1.0, 1)
    tris = np.array(back[0] + front[0], dtype=float)
    tris[2:, :, 2] += 0.5  # a da frente no meio da altura da de trás
    colors = np.array([[40, 40, 220]] * 2 + [[220, 40, 40]] * 2, dtype=float)
    groups = np.array([1, 1, 0, 0])
    image = mesh_render.render(tris, colors, groups, 0.0, 0.0, 120, 120)
    middle, edge = image[60, 60], image[60, 18]
    assert middle[0] > middle[2] and edge[2] > edge[0]
    behind = mesh_render.render(tris, colors, groups, 180.0, 0.0, 120, 120)
    assert behind[60, 60][2] > behind[60, 60][0]
    # o contorno entre as duas placas é desenhado (pixels escuros)
    assert (image.sum(axis=2) < 150).sum() > 50
    # a ordem dos triângulos não muda o resultado
    again = mesh_render.render(tris[::-1], colors[::-1], groups[::-1], 0.0, 0.0, 120, 120)
    assert (again == image).all()
