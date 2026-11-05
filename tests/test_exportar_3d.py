# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exportar 3D em glTF e OBJ (spec/ui 48, G01–G05)."""

import numpy as np
import pytest
from casa_completa import build
from estrutura import bounds

from brasbim.core import materials
from brasbim.core import model_export as me
from brasbim.core.document import OpError


@pytest.fixture(scope="module")
def casa():
    return build()


@pytest.fixture(scope="module")
def glb(casa, tmp_path_factory):
    path = tmp_path_factory.mktemp("g") / "casa.glb"
    result = me.export(casa.doc, str(path))
    return result, *me.read_glb(path)


def _node(doc, gid):
    return next(n for n in doc["nodes"] if n.get("extras", {}).get("GlobalId") == gid)


def _positions(doc, blob, node):
    out = []
    for p in doc["meshes"][node["mesh"]]["primitives"]:
        acc = doc["accessors"][p["attributes"]["POSITION"]]
        view = doc["bufferViews"][acc["bufferView"]]
        out.append(np.frombuffer(blob, np.float32, acc["count"] * 3,
                                 view["byteOffset"]).reshape(-1, 3))
    return np.concatenate(out)


def test_g01_glb_valido_com_um_no_por_elemento(casa, glb):
    result, doc, blob = glb
    assert doc["asset"]["version"] == "2.0" and len(blob) == doc["buffers"][0]["byteLength"]
    assert all(v["byteOffset"] % 4 == 0 for v in doc["bufferViews"])
    wall = casa.doc.ifc.by_type("IfcWall")[0]
    node = _node(doc, wall.GlobalId)
    assert node["extras"]["ClasseIfc"] == "IfcWall"
    assert node["extras"]["Tipo"] == "Alvenaria 14"
    roots = {doc["nodes"][i]["name"]: doc["nodes"][i] for i in doc["scenes"][0]["nodes"]}
    assert {"Térreo", "Superior"} <= set(roots)
    assert doc["nodes"].index(node) in roots[node["extras"]["Pavimento"]]["children"]
    gids = {n["extras"]["GlobalId"] for n in doc["nodes"] if "extras" in n}
    assert not {s.GlobalId for s in casa.doc.ifc.by_type("IfcSpace")} & gids
    assert result.elements == len(gids) and result.triangles > 100


def test_g02_cores(casa, glb):
    _, doc, _ = glb
    wall = casa.doc.ifc.by_type("IfcWall")[0]
    p = doc["meshes"][_node(doc, wall.GlobalId)["mesh"]]["primitives"][0]
    color = doc["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorFactor"]
    expected = materials.rgb(materials.style(casa.doc, "Reboco")["color"])
    assert color[:3] == pytest.approx(list(expected), abs=1e-3)
    window = casa.doc.ifc.by_type("IfcWindow")[0]
    alphas = [doc["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorFactor"][3]
              for p in doc["meshes"][_node(doc, window.GlobalId)["mesh"]]["primitives"]]
    assert min(alphas) < 1.0 and max(alphas) == 1.0
    assert any(m.get("alphaMode") == "BLEND" for m in doc["materials"])


def test_g03_z_vira_y(casa, glb):
    _, doc, blob = glb
    wall = casa.doc.ifc.by_type("IfcWall")[0]
    pts = _positions(doc, blob, _node(doc, wall.GlobalId))
    lo, hi = bounds(wall)  # no IFC, z para cima
    assert pts[:, 1].min() == pytest.approx(lo[2], abs=1e-4)
    assert pts[:, 1].max() == pytest.approx(hi[2], abs=1e-4)
    assert -pts[:, 2].max() == pytest.approx(lo[1], abs=1e-4)  # y do IFC vira −z


def test_g04_obj_e_mtl(casa, tmp_path):
    path = tmp_path / "casa.obj"
    me.export(casa.doc, str(path))
    text = path.read_text(encoding="utf-8")
    mtl = path.with_suffix(".mtl").read_text(encoding="utf-8")
    wall = casa.doc.ifc.by_type("IfcWall")[0]
    assert "mtllib casa.mtl" in text and f"_{wall.GlobalId}\n" in text
    assert text.count("\no ") >= len(casa.doc.ifc.by_type("IfcWall"))
    assert "usemtl" in text and "Kd " in mtl and "\nd 0." in mtl
    lines = text.splitlines()
    faces = [line for line in lines if line.startswith("f ")]
    count = sum(1 for line in lines if line.startswith("v "))
    assert max(int(i) for line in faces for i in line.split()[1:]) == count


def test_g05_so_o_visivel(casa, tmp_path):
    column = casa.doc.ifc.by_type("IfcColumn")[0]
    casa.doc.extra_hidden = {column.GlobalId}
    try:
        assert column.GlobalId not in {i.gid for i in me.collect(casa.doc)}
        assert column.GlobalId in {i.gid for i in me.collect(casa.doc, visible_only=False)}
    finally:
        casa.doc.extra_hidden = None
    with pytest.raises(OpError, match="extensão"):
        me.export(casa.doc, str(tmp_path / "casa.fbx"))
