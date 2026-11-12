# SPDX-License-Identifier: LGPL-3.0-or-later
"""Malha de arquivo para uma forma livre (``spec/elementos/forma-livre.md`` §4.2): OBJ
(com os materiais como partes), STL (texto ou binário) e GLB (glTF binário). Leitura
feita aqui, sem biblioteca nova. Sem Qt e sem IFC.

``read`` devolve as partes no sistema da forma livre: metros, z para cima, com o centro
da base da caixa na origem.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

from brasbim.core.document import OpError
from brasbim.core.freeform import mesh

FORMATS = (".obj", ".stl", ".glb")
UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0}
MAX_FILE = 200 * 1024 * 1024
MAX_SOURCE_TRIANGLES = 2_000_000


def _part(name: str, vertices, faces) -> dict | None:
    vertices = np.asarray(vertices, dtype=float).reshape(-1, 3)
    faces = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    if not len(faces) or not len(vertices):
        return None
    if faces.min() < 0 or faces.max() >= len(vertices):
        raise OpError("o arquivo tem faces que apontam para vértices que não existem")
    used, inverse = np.unique(faces, return_inverse=True)
    return {"name": name or "Corpo", "material": None,
            "vertices": vertices[used].tolist(), "faces": inverse.reshape(-1, 3).tolist()}


def _obj(path: Path) -> list[dict]:
    vertices, groups, current = [], {}, "Corpo"
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            head, _, rest = line.strip().partition(" ")
            if head == "v":
                vertices.append([float(c) for c in rest.split()[:3]])
            elif head == "usemtl":
                current = rest.strip() or "Corpo"
            elif head == "f":
                corner = []
                for token in rest.split():
                    index = int(token.split("/")[0])
                    corner.append(index - 1 if index > 0 else len(vertices) + index)
                faces = groups.setdefault(current, [])
                for k in range(1, len(corner) - 1):  # polígono em leque
                    faces.append((corner[0], corner[k], corner[k + 1]))
    return [p for name, faces in groups.items()
            if (p := _part(name, vertices, faces)) is not None]


def _stl(path: Path) -> list[dict]:
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
    if len(data) == 84 + 50 * count and count:  # binário
        records = np.frombuffer(data, dtype=np.dtype([
            ("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=count, offset=84)
        points = records["v"].reshape(-1, 3).astype(float)
    else:  # texto
        points = [[float(c) for c in line.split()[1:4]]
                  for line in data.decode("utf-8", "replace").splitlines()
                  if line.strip().startswith("vertex")]
        points = np.asarray(points, dtype=float).reshape(-1, 3)
        if len(points) % 3:
            raise OpError("STL com triângulo incompleto")
    part = _part(path.stem, points, np.arange(len(points)).reshape(-1, 3))
    return [part] if part is not None else []


_GLB_TYPES = {5120: "i1", 5121: "u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
_GLB_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _glb(path: Path) -> list[dict]:
    data = path.read_bytes()
    if data[:4] != b"glTF" or len(data) < 20:
        raise OpError("não é um arquivo GLB")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:
        raise OpError("GLB sem a descrição (JSON)")
    doc = json.loads(data[20:20 + length].decode("utf-8"))
    offset = 20 + length
    binary = b""
    if offset + 8 <= len(data):
        blen, bkind = struct.unpack_from("<II", data, offset)
        if bkind == 0x004E4942:
            binary = data[offset + 8:offset + 8 + blen]

    def accessor(index: int) -> np.ndarray:
        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        if view.get("buffer", 0) != 0:
            raise OpError("GLB com dados fora do arquivo não é lido")
        size = _GLB_SIZES[acc["type"]]
        dtype = np.dtype(_GLB_TYPES[acc["componentType"]])
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride") or dtype.itemsize * size
        if stride == dtype.itemsize * size:
            flat = np.frombuffer(binary, dtype=dtype, count=acc["count"] * size, offset=start)
            return flat.reshape(acc["count"], size)
        rows = [np.frombuffer(binary, dtype=dtype, count=size, offset=start + i * stride)
                for i in range(acc["count"])]
        return np.asarray(rows)

    def local(node: dict) -> np.ndarray:
        if "matrix" in node:
            return np.asarray(node["matrix"], dtype=float).reshape(4, 4).T
        m = np.eye(4)
        if "scale" in node:
            m = np.diag([*node["scale"], 1.0]) @ m
        if "rotation" in node:
            x, y, z, w = node["rotation"]
            r = np.eye(4)
            r[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
            m = r @ m
        if "translation" in node:
            t = np.eye(4)
            t[:3, 3] = node["translation"]
            m = t @ m
        return m

    materials = [m.get("name") or f"Material {i + 1}"
                 for i, m in enumerate(doc.get("materials") or [])]
    found: dict[str, tuple[list, list, int]] = {}

    def visit(index: int, parent: np.ndarray) -> None:
        node = doc["nodes"][index]
        m = parent @ local(node)
        if "mesh" in node:
            for primitive in doc["meshes"][node["mesh"]].get("primitives") or []:
                if primitive.get("mode", 4) != 4 or "POSITION" not in primitive["attributes"]:
                    continue
                points = accessor(primitive["attributes"]["POSITION"]).astype(float)
                points = points @ m[:3, :3].T + m[:3, 3]
                faces = (accessor(primitive["indices"]).astype(np.int64).reshape(-1, 3)
                         if "indices" in primitive
                         else np.arange(len(points)).reshape(-1, 3))
                name = materials[primitive["material"]] if primitive.get(
                    "material") is not None else "Corpo"
                v, f, n = found.setdefault(name, ([], [], 0))
                v.append(points)
                f.append(faces + n)
                found[name] = (v, f, n + len(points))
        for child in node.get("children") or []:
            visit(child, m)

    scenes = doc.get("scenes") or [{"nodes": list(range(len(doc.get("nodes") or [])))}]
    for root in scenes[doc.get("scene", 0)].get("nodes") or []:
        visit(root, np.eye(4))
    return [p for name, (v, f, _) in found.items()
            if (p := _part(name, np.vstack(v), np.vstack(f))) is not None]


_READERS = {".obj": _obj, ".stl": _stl, ".glb": _glb}


def read(path, unit: str = "m", up: str | None = None, limit: int | None = None
         ) -> tuple[list[dict], dict]:
    """Partes da malha do arquivo e um resumo (``{"triangles": lidos, "kept": gravados,
    "size": (largura, profundidade, altura)}``).

    ``unit``: unidade do arquivo (mm, cm, m). ``up``: eixo que aponta para cima no arquivo
    ("y" ou "z"); sem ele, "y" no GLB (é a regra do formato) e "z" nos outros. ``limit``:
    acima disso a malha é simplificada.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in _READERS:
        raise OpError(f"{path.name}: formato não aceito (use OBJ, STL ou GLB)")
    if unit not in UNITS:
        raise OpError(f"unidade inválida: {unit}")
    try:
        if path.stat().st_size > MAX_FILE:
            raise OpError(f"{path.name}: arquivo grande demais (mais de 200 MB)")
        parts = _READERS[suffix](path)
    except OpError:
        raise
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as e:
        raise OpError(f"não foi possível ler {path.name}: {e}") from None
    if not parts:
        raise OpError(f"{path.name} não tem nenhuma face")
    total = mesh.triangle_count(parts)
    if total > MAX_SOURCE_TRIANGLES:
        raise OpError(f"{path.name} tem {total} triângulos: simplifique no programa de "
                      "origem antes de importar")
    up = up or ("y" if suffix == ".glb" else "z")
    matrix = [[1, 0, 0], [0, 0, -1], [0, 1, 0]] if up == "y" else None  # y para cima → z
    parts = mesh.transformed(parts, scale=[UNITS[unit]] * 3, matrix=matrix)
    b = mesh.bounds(parts)
    parts = mesh.transformed(parts, offset=(-(b[0] + b[1]) / 2, -(b[2] + b[3]) / 2, -b[4]))
    parts = mesh.cleaned(parts)
    if not parts:
        raise OpError(f"{path.name}: a malha ficou sem faces nessa unidade (pequena demais)")
    if limit is not None and mesh.triangle_count(parts) > limit:
        parts = mesh.simplified(parts, limit)
    return parts, {"triangles": total, "kept": mesh.triangle_count(parts),
                   "size": mesh.size(parts)}
