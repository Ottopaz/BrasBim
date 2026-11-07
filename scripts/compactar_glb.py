# SPDX-License-Identifier: LGPL-3.0-or-later
"""Modelo 3D leve para mostrar na web, a partir de um .glb do BrasBim ou direto do IFC.

Uso: python scripts/compactar_glb.py entrada.glb|entrada.ifc saida.glb

Junta todos os elementos de uma mesma cor numa malha só (poucas chamadas de desenho),
solda os vértices de mesma posição e grava com índices, sem normais: quem mostra calcula
a normal de cada face (sombreamento plano, como no próprio BrasBim). Perde a separação por
elemento: serve para apresentação, não para troca de dados (para isso, use o IFC).

Com um .ifc, a geometria vem do iterador do IfcOpenShell em várias threads (bem mais
rápido que elemento a elemento, para modelos grandes) e a cor é a do material do elemento
(``model_export.element_color``), como na exportação do programa.
"""

import json
import multiprocessing
import struct
import sys

import numpy as np

from brasbim.core.model_export import SKIP, read_glb

# cor e transparência -> lista de arrays de triângulos (n × 3 × 3, y para cima)
Grupos = dict[tuple[tuple[float, float, float], float], list[np.ndarray]]


def _array(doc, blob, index, comps):
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    start = view["byteOffset"] + acc.get("byteOffset", 0)
    return np.frombuffer(blob, np.float32, acc["count"] * comps, start).reshape(-1, comps)


def de_glb(entrada: str) -> Grupos:
    doc, blob = read_glb(entrada)
    grupos: Grupos = {}
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            r, g, b, a = doc["materials"][prim["material"]]["pbrMetallicRoughness"][
                "baseColorFactor"]
            pos = _array(doc, blob, prim["attributes"]["POSITION"], 3)
            grupos.setdefault(((r, g, b), a), []).append(pos)
    return grupos


def de_ifc(entrada: str) -> Grupos:
    import ifcopenshell
    import ifcopenshell.geom

    from brasbim.core import model_export
    from brasbim.core.document import Document

    doc = Document.open(entrada)
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    it = ifcopenshell.geom.iterator(settings, doc.ifc, multiprocessing.cpu_count())
    grupos: Grupos = {}
    if not it.initialize():
        return grupos
    while True:
        shape = it.get()
        element = doc.ifc.by_id(shape.id)
        if not any(element.is_a(c) for c in SKIP):
            v = np.array(shape.geometry.verts, dtype=np.float32).reshape(-1, 3)
            f = np.array(shape.geometry.faces, dtype=np.int64).reshape(-1, 3)
            if len(f):
                tri = v[f]                       # z para cima (IFC) ...
                tri = tri[..., [0, 2, 1]] * [1, 1, -1]  # ... y para cima (glTF)
                color, alpha = model_export.element_color(doc, element)
                key = (tuple(round(c, 4) for c in color), round(alpha, 3))
                grupos.setdefault(key, []).append(tri.reshape(-1, 3))
        if not it.next():
            break
    return grupos


def gravar(grupos: Grupos, saida: str) -> None:
    out = {"asset": {"version": "2.0", "generator": "BrasBim (compactado para a web)"},
           "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [],
           "materials": [], "accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}]}
    dados = bytearray()

    def view(b: bytes, target: int) -> int:
        while len(dados) % 4:
            dados.append(0)
        out["bufferViews"].append({"buffer": 0, "byteOffset": len(dados),
                                   "byteLength": len(b), "target": target})
        dados.extend(b)
        return len(out["bufferViews"]) - 1

    for (color, alpha), partes in grupos.items():
        pos = np.concatenate(partes).astype(np.float32)
        chave = np.round(pos * 1000).astype(np.int64)  # milímetro
        _, primeiro, indices = np.unique(chave, axis=0, return_index=True, return_inverse=True)
        pos = pos[primeiro]
        indices = indices.ravel().astype(np.uint32)
        material = {"name": "#" + "".join(f"{round(c * 255):02X}" for c in color),
                    "pbrMetallicRoughness": {"baseColorFactor": [*color, alpha],
                                             "metallicFactor": 0.0, "roughnessFactor": 0.9},
                    "doubleSided": True}
        if alpha < 1:
            material["alphaMode"] = "BLEND"
        out["materials"].append(material)
        out["accessors"] += [
            {"bufferView": view(indices.tobytes(), 34963), "componentType": 5125,
             "count": len(indices), "type": "SCALAR"},
            {"bufferView": view(pos.tobytes(), 34962), "componentType": 5126,
             "count": len(pos), "type": "VEC3",
             "min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()},
        ]
        n = len(out["accessors"])
        out["meshes"].append({"name": material["name"], "primitives": [{
            "attributes": {"POSITION": n - 1}, "indices": n - 2,
            "material": len(out["materials"]) - 1, "mode": 4}]})
        out["nodes"].append({"mesh": len(out["meshes"]) - 1})
        out["scenes"][0]["nodes"].append(len(out["nodes"]) - 1)

    while len(dados) % 4:
        dados.append(0)
    out["buffers"][0]["byteLength"] = len(dados)
    js = json.dumps(out, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    with open(saida, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(dados)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(dados), 0x004E4942) + bytes(dados))


if __name__ == "__main__":
    entrada, saida = sys.argv[1], sys.argv[2]
    gravar(de_ifc(entrada) if entrada.lower().endswith(".ifc") else de_glb(entrada), saida)
