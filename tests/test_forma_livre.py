# SPDX-License-Identifier: LGPL-3.0-or-later
"""Forma livre (spec/elementos/forma-livre.md): FL01–FL07 no núcleo. O resultado é
conferido no IFC."""

import json
import math
import struct

import ifcopenshell.util.element as ue
import numpy as np
import pytest
from conftest import snapshot

from brasbim.core import plan as plan_mod
from brasbim.core import transform
from brasbim.core.annotations import commands as ac
from brasbim.core.assistant.tools import Context, default_registry
from brasbim.core.delete import delete_elements
from brasbim.core.document import Document, OpError
from brasbim.core.drawings import section, views
from brasbim.core.freeform import commands as fc
from brasbim.core.freeform import elements as ff
from brasbim.core.freeform import importer, mesh, shapes
from brasbim.core.objects import commands as oc
from brasbim.core.objects import elements as objects
from brasbim.core.objects import library

RECIPE = [
    {"kind": "box", "name": "Assento", "size": [0.8, 0.7, 0.2], "radius": 0.06,
     "position": [0.4, 0.35, 0.3], "material": "Couro"},
    {"kind": "cone", "name": "Pé", "radius": 0.03, "top_radius": 0.02, "height": 0.3,
     "position": [0.1, 0.1, 0.0], "rotation": [8, 0, 0], "material": "Madeira"},
]


def _make(model, **options):
    options = {"name": "Poltrona", "category": "furniture", "object_type": "Poltrona",
               **options}
    tx = model.commit(fc.from_recipe(model.doc, model.terreo, RECIPE, (2.0, 3.0), **options))
    return model.doc.get(tx.ops[-1].id)


# FL01: o que vai para o IFC; desfazer, refazer e reabrir


def test_fl01_grava_no_ifc_desfaz_e_reabre(model, tmp_path):
    before = snapshot(model.doc.ifc)
    e = _make(model, angle=30.0, elevation=0.1)
    assert e.is_a("IfcFurniture") and e.Name == "Poltrona"
    assert (e.ObjectType, e.PredefinedType) == ("Poltrona", "USERDEFINED")
    assert ue.get_type(e) is None and ue.get_container(e) == model.terreo
    reps = {r.RepresentationIdentifier: r for r in e.Representation.Representations}
    assert reps["Body"].RepresentationType == "Tessellation"
    assert [i.is_a() for i in reps["Body"].Items] == ["IfcTriangulatedFaceSet"] * 2
    assert all(i.Closed and i.StyledByItem for i in reps["Body"].Items)
    assert reps["FootPrint"].Items[0].is_a("IfcGeometricCurveSet")
    assert ue.get_material(e).is_a("IfcMaterialConstituentSet")
    pset = ue.get_pset(e, ff.PSET)
    assert pset["Largura"] == pytest.approx(0.8) and pset["Altura"] == pytest.approx(0.5, abs=0.01)
    assert pset["Triangulos"] == mesh.triangle_count(ff.read_state(model.doc, e)["parts"])
    assert pset["Volume"] > 0.09
    state = ff.read_state(model.doc, e)
    assert [(p["name"], p["material"]) for p in state["parts"]] == [
        ("Couro", "Couro"), ("Madeira", "Madeira")]
    assert state["recipe"] == RECIPE and state["source"] == ""
    assert (state["point"], state["angle"], state["elevation"]) == ([2.0, 3.0], 30.0, 0.1)
    assert ff.is_freeform(e) and not objects.is_object(e)
    after = snapshot(model.doc.ifc)
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    model.history.redo()
    assert snapshot(model.doc.ifc) == after
    reopened = Document(model.reopen(tmp_path))
    (again,) = ff.all_freeforms(reopened)
    assert ff.read_state(reopened, again) == state
    # nome repetido ganha sufixo; recusas
    assert _make(model).Name == "Poltrona (2)"
    with pytest.raises(OpError, match="categoria inválida"):
        fc.from_recipe(model.doc, model.terreo, RECIPE, category="cadeira")
    with pytest.raises(OpError, match="pelo menos uma parte"):
        fc.create(model.doc, model.terreo, [])


# FL02: cada forma dá malha fechada, com a caixa e o volume esperados


@pytest.mark.parametrize(("shape", "size", "volume"), [
    ({"kind": "box", "size": [1, 2, 3]}, (1, 2, 3), 6.0),
    ({"kind": "box", "size": [1, 2, 3], "radius": 0.2}, (1, 2, 3), 5.81),
    ({"kind": "ellipsoid", "radii": [1, 2, 3]}, (2, 4, 6), 4 / 3 * math.pi * 6),
    ({"kind": "cone", "radius": 1, "height": 2}, (2, 2, 2), 2 * math.pi),
    ({"kind": "cone", "radius": 1, "top_radius": 0, "height": 3}, (2, 2, 3), math.pi),
    ({"kind": "tube", "path": [[0, 0, 0], [0, 0, 2]], "radius": 0.5}, (1, 1, 2), math.pi / 2),
    ({"kind": "tube", "path": [[0, 0, 0], [2, 0, 0]], "section": [0.2, 0.1]},
     (2, 0.2, 0.1), 0.04),
    ({"kind": "sections", "sections": [{"z": 0, "radii": [1, 1]}, {"z": 2, "radius": 1}]},
     (2, 2, 2), 2 * math.pi),
    ({"kind": "revolution", "profile": [[1, 0], [1, 2]]}, (2, 2, 2), 2 * math.pi),
    ({"kind": "revolution", "profile": [[1, 0], [1, 2]], "angle": 180}, (2, 1, 2), math.pi),
    ({"kind": "extrusion", "height": 0.5,
      "profile": [[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]]}, (2, 2, 0.5), 1.5),
])
def test_fl02_formas_fechadas(shape, size, volume):
    (part,) = shapes.build([shape])
    assert mesh.is_closed(part)
    assert mesh.size([part]) == pytest.approx(size, abs=1e-3)
    assert mesh.volume([part]) == pytest.approx(volume, rel=0.04)  # curvas em facetas


def test_fl02_rotacao_posicao_suave_e_limites():
    # caixa de 1 × 2 × 3 deitada (gira 90° em x): a altura vira profundidade
    (part,) = shapes.build([{"kind": "box", "size": [1, 2, 3], "rotation": [90, 0, 0],
                             "position": [5, 0, 0]}])
    b = mesh.bounds([part])
    assert (b[0], b[1]) == pytest.approx((4.5, 5.5))
    assert (b[3] - b[2], b[5] - b[4]) == pytest.approx((3, 2))
    # tubo suave e seções suaves continuam fechados
    for shape in ({"kind": "tube", "radius": 0.05, "smooth": True,
                   "path": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 1, 1]]},
                  {"kind": "sections", "smooth": True, "sections": [
                      {"z": 0, "radii": [1, 0.5]},
                      {"z": 1, "points": [[-1, -1], [1, -1], [1, 1], [-1, 1]]},
                      {"z": 2, "radius": 0.3, "twist": 30, "center": [0.2, 0]}]}):
        (part,) = shapes.build([shape])
        assert mesh.is_closed(part) and mesh.volume([part]) > 0
    # partes por material, na ordem; muitas formas caem de detalhe para caber
    parts = shapes.build([{"kind": "ellipsoid", "radii": [1, 1, 1], "material": m}
                          for m in ("Couro", "Madeira", "Couro")])
    assert [p["material"] for p in parts] == ["Couro", "Madeira"]
    many = shapes.build([{"kind": "ellipsoid", "radii": [1, 1, 1], "position": [i, 0, 0]}
                         for i in range(70)])
    assert mesh.triangle_count(many) <= shapes.PREFERRED
    # recusas, com o lugar
    for shape, text in (({"kind": "box", "size": [1, 0, 1], "name": "Encosto"},
                         "forma 1 'Encosto': 'size' tem medida ≤ 0"),
                        ({"kind": "esfera"}, "tipo 'esfera' não existe"),
                        ({"kind": "cone", "radius": 1}, "falta 'height'"),
                        ({"kind": "sections", "sections": [{"z": 1, "radius": 1},
                                                           {"z": 0, "radius": 1}]},
                         "'z' crescente"),
                        ({"kind": "revolution", "profile": [[-1, 0], [1, 1]]}, "raio ≥ 0")):
        with pytest.raises(OpError, match=text):
            shapes.build([shape])
    with pytest.raises(OpError, match="pelo menos uma forma"):
        shapes.build([])
    with pytest.raises(OpError, match=f"limite é {shapes.MAX_SHAPES}"):
        shapes.build([{"kind": "box", "size": [1, 1, 1]}] * (shapes.MAX_SHAPES + 1))


# FL03: ferramentas do assistente


def _call(model, tool, **args):
    ctx = Context(model.doc, model.commit, model.terreo.GlobalId)
    result = default_registry().call(ctx, tool, args)
    text = result["content"][0]["text"]
    return (json.loads(text) if not result["isError"] else text), result["isError"]


def test_fl03_assistente_cria_e_corrige(model):
    out, error = _call(model, "create_freeform", name="Poltrona", category="furniture",
                       object_type="Poltrona", shapes=RECIPE, at=[1, 2], rotation=90,
                       description="medidas típicas")
    assert not error, out
    assert out["tem_receita"] and out["partes"] == ["Couro", "Madeira"]
    assert out["caixa"]["largura"] == pytest.approx(0.8)
    e = model.doc.get(out["id"])
    state = ff.read_state(model.doc, e)
    assert (state["source"], state["description"]) == ("assistente", "medidas típicas")
    listed, _ = _call(model, "describe_model")
    assert [f["id"] for f in listed["formas_livres"]] == [out["id"]]
    # corrigir: a lista inteira de formas, mesmo GlobalId
    taller = [{**RECIPE[0], "size": [0.8, 0.7, 0.5]}, RECIPE[1]]
    fixed, error = _call(model, "edit_freeform", id=out["id"], shapes=taller, at=[4, 4])
    assert not error, fixed
    assert fixed["id"] == out["id"] and fixed["ponto"] == [4, 4]
    assert fixed["caixa"]["altura"] == pytest.approx(0.8, abs=0.01)
    assert ff.read_state(model.doc, model.doc.get(out["id"]))["recipe"] == taller
    # recusas: com o lugar, e nada no histórico
    before, undo = snapshot(model.doc.ifc), len(model.history.undo_stack)
    text, error = _call(model, "create_freeform", name="X", at=[0, 0], shapes=[
        RECIPE[0], RECIPE[1], {"kind": "cone", "name": "Encosto", "radius": 0, "height": 1}])
    assert error and "forma 3 'Encosto': 'radius' ≤ 0" in text
    text, error = _call(model, "edit_freeform", id=model.wall().GlobalId, at=[0, 0])
    assert error and "não é forma livre" in text
    model.history.undo()  # a parede do teste
    assert snapshot(model.doc.ifc) == before and len(model.history.undo_stack) == undo
    # sem receita (esticada), as formas não podem ser trocadas
    model.commit(fc.resize(model.doc, e, height=1.0))
    text, error = _call(model, "edit_freeform", id=out["id"], shapes=RECIPE)
    assert error and "não foi feita de formas" in text


# FL04: importar arquivo


def _cube_obj(path, size=1000.0):
    s = size
    lines = ["mtllib x.mtl"] + [f"v {x} {y} {z}" for x in (0, s) for y in (0, s) for z in (0, s)]
    lines += ["usemtl Madeira", "f 1 2 4 3", "f 5 7 8 6", "usemtl Tecido", "f 1 5 6 2",
              "f 3 4 8 7", "f 1 3 7 5", "f 2 6 8 4"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _sphere_stl(path, rings=160):
    """Esfera fina em STL binário: muitos triângulos, para passar do limite."""
    lat = np.linspace(-math.pi / 2, math.pi / 2, rings)
    lon = np.linspace(0, 2 * math.pi, 2 * rings, endpoint=False)
    a, b = np.meshgrid(lat, lon, indexing="ij")
    grid = np.stack([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)], axis=-1)
    nxt = np.roll(grid, -1, axis=1)
    lower, upper, lower_n, upper_n = grid[:-1], grid[1:], nxt[:-1], nxt[1:]
    tris = np.concatenate([np.stack([lower, lower_n, upper_n], axis=2),
                           np.stack([lower, upper_n, upper], axis=2)]).reshape(-1, 3, 3)
    records = np.zeros(len(tris), dtype=np.dtype([
        ("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    records["v"] = tris
    path.write_bytes(bytes(80) + struct.pack("<I", len(tris)) + records.tobytes())
    return path, len(tris)


def _glb(path):
    """Tetraedro com y para cima (a regra do formato)."""
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1], [0, 2, 0]], dtype="<f4")
    index = np.array([0, 1, 2, 0, 3, 1, 1, 3, 2, 2, 3, 0], dtype="<u2")
    binary = points.tobytes() + index.tobytes()
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"mesh": 0, "translation": [5, 0, 0]}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1,
                                       "material": 0}]}],
           "materials": [{"name": "Bronze"}],
           "buffers": [{"byteLength": len(binary)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 48},
                           {"buffer": 0, "byteOffset": 48, "byteLength": 24}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3"},
                         {"bufferView": 1, "componentType": 5123, "count": 12,
                          "type": "SCALAR"}]}
    text = json.dumps(doc).encode()
    text += b" " * (-len(text) % 4)
    body = (struct.pack("<II", len(text), 0x4E4F534A) + text
            + struct.pack("<II", len(binary), 0x004E4942) + binary)
    path.write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)
    return path


def test_fl04_importa_obj_stl_e_glb(model, tmp_path):
    # OBJ em milímetros, com dois materiais: duas partes, cubo de 1 m no centro da base
    parts, info = importer.read(_cube_obj(tmp_path / "cubo.obj"), unit="mm")
    assert [p["name"] for p in parts] == ["Madeira", "Tecido"]
    assert info["triangles"] == info["kept"] == 12
    assert info["size"] == pytest.approx((1, 1, 1))
    assert mesh.bounds(parts) == pytest.approx((-0.5, 0.5, -0.5, 0.5, 0, 1))
    tx = model.commit(fc.create(model.doc, model.terreo, parts, (1, 1), name="Cubo",
                                source="arquivo cubo.obj"))
    assert ff.box_of(ff.read_state(model.doc, model.doc.get(tx.ops[-1].id)))[
        "altura"] == pytest.approx(1.0)
    # STL binário grande: simplificado para caber no limite
    path, count = _sphere_stl(tmp_path / "esfera.stl")
    assert count > shapes.MAX_TRIANGLES
    parts, info = importer.read(path, unit="m", limit=shapes.MAX_TRIANGLES)
    assert info["triangles"] == count and info["kept"] <= shapes.MAX_TRIANGLES
    assert info["kept"] > 2000 and info["size"] == pytest.approx((2, 2, 2), abs=0.05)
    # STL em texto
    text = tmp_path / "t.stl"
    text.write_text("solid t\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\n"
                    "vertex 0 1 0\nendloop\nendfacet\nendsolid t\n", encoding="utf-8")
    assert importer.read(text)[1]["kept"] == 1
    # GLB: y para cima vira z; a translação do nó vale; o material vira a parte
    parts, info = importer.read(_glb(tmp_path / "t.glb"))
    assert [p["name"] for p in parts] == ["Bronze"]
    assert info["size"] == pytest.approx((1, 1, 2))  # a altura (y do arquivo) é z
    # recusas
    bad = tmp_path / "x.glb"
    bad.write_bytes(b"isto nao e glb, nem de longe")
    for path, text in ((tmp_path / "x.fbx", "formato não aceito"), (bad, "não é um arquivo GLB"),
                       (tmp_path / "falta.obj", "não foi possível ler")):
        with pytest.raises(OpError, match=text):
            importer.read(path)
    empty = tmp_path / "vazio.obj"
    empty.write_text("v 0 0 0\n", encoding="utf-8")
    with pytest.raises(OpError, match="nenhuma face"):
        importer.read(empty)


# FL05: converter objetos em forma livre


def test_fl05_converte_objetos(model):
    index = library.Index([library.builtin_folder()])
    entries = index.entries()
    wanted = [e for e in entries if e.name in ("Fogão 4 bocas", "Micro-ondas")]
    model.commit(library.load(model.doc, entries, wanted))
    from brasbim.core.objects import types as ot

    made = []
    for name, point in (("Fogão 4 bocas", (1.0, 1.0)), ("Micro-ondas", (2.0, 1.0))):
        tx = model.commit(oc.create_object(model.doc, ot.by_name(model.doc, name),
                                           model.terreo, point, angle=90.0))
        made.append(tx.ops[-1].id)
    before = snapshot(model.doc.ifc)
    undo = len(model.history.undo_stack)
    tx = model.commit(fc.convert(model.doc, made))
    assert len(model.history.undo_stack) == undo + 1
    assert all(model.doc.find(g) is None for g in made)
    assert not objects.all_objects(model.doc)
    (e,) = ff.all_freeforms(model.doc)
    assert e.GlobalId == tx.ops[-1].id and e.is_a("IfcElectricAppliance")
    state = ff.read_state(model.doc, e)
    assert state["point"] == [1.0, 1.0] and state["angle"] == 90.0
    assert state["source"] == "convertido de 2 elemento(s)" and state["recipe"] is None
    assert {p["material"] for p in state["parts"]} >= {"Inox", "Eletrodoméstico"}
    box = ff.box_of(state)
    # girados 90°: o micro-ondas está 1 m ao lado, que no sistema local do fogão é −y
    assert box["altura"] == pytest.approx(0.92 + 0.30, abs=0.03)  # micro-ondas a 0,92
    assert box["profundidade"] > 1.0
    model.history.undo()
    assert snapshot(model.doc.ifc) == before
    # recusas
    with pytest.raises(OpError, match="só objetos e formas livres"):
        fc.convert(model.doc, [model.wall().GlobalId])
    with pytest.raises(OpError, match="selecione"):
        fc.convert(model.doc, [])


# FL06: mover, girar, espelhar, copiar, esticar, categoria, excluir


def test_fl06_transformar_e_esticar(model):
    e = _make(model)
    gid = e.GlobalId
    doc = model.doc
    model.commit(transform.move_elements(doc, [gid], (1.0, -1.0)))
    assert ff.read_state(doc, doc.get(gid))["point"] == pytest.approx([3.0, 2.0])
    model.commit(transform.rotate_elements(doc, [gid], (0.0, 0.0), math.radians(90)))
    state = ff.read_state(doc, doc.get(gid))
    assert state["point"] == pytest.approx([-2.0, 3.0]) and state["angle"] == pytest.approx(90)
    assert state["recipe"] == RECIPE  # mover e girar não mexem na malha
    tx = model.commit(transform.copy_elements(doc, [gid], (5.0, 0.0)))
    (copy_gid,) = [op.id for op in tx.ops if op.op == "freeform.create"]
    copied = ff.read_state(doc, doc.get(copy_gid))
    assert copied["point"] == pytest.approx([3.0, 3.0]) and copied["parts"] == state["parts"]
    # espelhar: a malha vira no x local e continua fechada, com o mesmo volume
    volume = mesh.volume(state["parts"])
    model.commit(transform.mirror_elements(doc, [gid], (0.0, 0.0), (0.0, 1.0)))
    mirrored = ff.read_state(doc, doc.get(gid))
    assert mirrored["point"] == pytest.approx([2.0, 3.0]) and mirrored["recipe"] is None
    assert all(mesh.is_closed(p) for p in mirrored["parts"])
    assert mesh.volume(mirrored["parts"]) == pytest.approx(volume)
    assert mesh.bounds(mirrored["parts"])[1] == pytest.approx(0.0, abs=1e-3)  # x de −0,8 a 0
    # esticar: proporcional e por eixo; o centro da base fica
    e = doc.get(copy_gid)
    b0 = mesh.bounds(copied["parts"])
    model.commit(fc.resize(doc, e, height=1.0))
    grown = ff.read_state(doc, e)
    assert mesh.size(grown["parts"]) == pytest.approx(
        tuple(s * 1.0 / mesh.size(copied["parts"])[2] for s in mesh.size(copied["parts"])),
        abs=1e-3)
    b1 = mesh.bounds(grown["parts"])
    assert (b1[0] + b1[1]) / 2 == pytest.approx((b0[0] + b0[1]) / 2, abs=1e-3)
    assert b1[4] == pytest.approx(b0[4], abs=1e-3)
    model.commit(fc.resize(doc, e, width=2.0, proportional=False))
    assert mesh.size(ff.read_state(doc, e)["parts"]) == pytest.approx(
        (2.0, mesh.size(grown["parts"])[1], 1.0), abs=1e-3)
    footprint = ff.footprint(e)
    xs = [p[0] for ring in footprint for p in ring]
    assert max(xs) - min(xs) == pytest.approx(2.0, abs=0.01)  # a silhueta acompanha
    with pytest.raises(OpError, match="pequena demais"):
        fc.resize(doc, e, height=0.0)
    # categoria: outra classe IFC, o mesmo GlobalId
    model.commit(fc.edit(doc, e, category="proxy", name="Escultura"))
    e = doc.get(copy_gid)
    assert e.is_a("IfcBuildingElementProxy") and e.Name == "Escultura"
    assert ue.get_container(e) == model.terreo
    model.history.undo()
    assert doc.get(copy_gid).is_a("IfcFurniture")
    # material de uma parte
    model.commit(fc.set_part_material(doc, doc.get(copy_gid), 0, "Tecido"))
    assert ff.read_state(doc, doc.get(copy_gid))["parts"][0]["material"] == "Tecido"
    # excluir
    tx, _ = delete_elements(doc, [gid, copy_gid])
    assert tx.label == "Excluir" and {op.op for op in tx.ops} == {"freeform.delete"}
    model.commit(tx)
    assert not ff.all_freeforms(doc)
    model.history.undo()
    assert len(ff.all_freeforms(doc)) == 2


# FL07: planta, corte e leitura direta da malha


def test_fl07_planta_e_corte(model):
    e = _make(model)
    doc = model.doc
    plan = plan_mod.storey_plan(doc, model.terreo)
    mine = [s for s in plan.shapes if s.owner == e.GlobalId]
    assert sorted({s.role for s in mine}) == ["object_box", "object_fill"]
    (outline,) = [s for s in mine if s.role == "object_fill"]
    xs, ys = [p[0] for p in outline.points], [p[1] for p in outline.points]
    assert (min(xs), max(xs)) == pytest.approx((2.0, 2.8), abs=0.01)  # posta em (2, 3)
    assert (min(ys), max(ys)) == pytest.approx((3.0, 3.7), abs=0.01)
    # toda acima do plano de corte: tracejada
    model.commit(fc.edit(doc, e, elevation=2.0))
    plan = plan_mod.storey_plan(doc, model.terreo)
    assert "object_above" in {s.role for s in plan.shapes if s.owner == e.GlobalId}
    model.history.undo()
    # vegetação usa os papéis de planta
    model.commit(fc.edit(doc, e, category="vegetation"))
    plan = plan_mod.storey_plan(doc, model.terreo)
    assert "plant_fill" in {s.role for s in plan.shapes if s.owner == e.GlobalId}
    model.history.undo()
    # malha no mundo, lida direto (sem a triangulação do IFC)
    e = doc.get(e.GlobalId)
    world = np.vstack([v for v, _, _ in ff.world_parts(e)])
    assert world[:, 0].min() == pytest.approx(2.0, abs=0.01)
    assert world[:, 2].max() == pytest.approx(0.5, abs=0.01)
    # corte que passa pela peça corta; fachada mostra em vista, sem o arame da malha
    model.commit(ac.create_view(doc, "section", (2.4, 2.0), (2.4, 5.0), "left"))
    model.commit(ac.create_view(doc, "elevation", (0.0, 0.0), (5.0, 0.0), "left"))
    cut, facade = (section.draw(doc, v) for v in views.all_views(doc))
    owned = lambda drawing, kind: [i for i in drawing.items
                                   if i.kind == kind and i.owner == e.GlobalId]
    assert owned(cut, "cut") and owned(facade, "face")
    triangles = mesh.triangle_count(ff.read_state(doc, e)["parts"])
    assert 0 < len(owned(facade, "edge")) < triangles / 2
    # creases: num cubo, as 12 arestas, sem as diagonais
    (cube,) = shapes.build([{"kind": "box", "size": [1, 1, 1]}])
    assert len(mesh.crease_edges(*mesh.arrays(cube))) == 12


def test_fl07_tabela_de_objetos_conta_as_formas_livres(model):
    from brasbim.core.quantities import tables

    shape = [{"kind": "box", "size": [1.0, 0.5, 2.0], "material": "Madeira"}]
    for name, category, at in (("Banco", "furniture", (0, 0)), ("Escultura", "proxy", (3, 0))):
        model.commit(fc.from_recipe(model.doc, model.terreo, shape, at, name=name,
                                    category=category))
    tx = model.commit(tables.create_table(model.doc, "objects"))
    result = tables.compute(model.doc, model.doc.get(tx.ops[-1].id))
    rows = [r.cells for r in result.rows]
    assert rows == [[None, "Forma livre", "Banco", 1], [None, "Forma livre", "Escultura", 1],
                    ["Total", None, None, 2]]
