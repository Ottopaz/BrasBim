# SPDX-License-Identifier: LGPL-3.0-or-later
"""Contas sobre a malha de uma forma livre (``spec/elementos/forma-livre.md`` §3, §7, §8):
caixa, volume, se é fechada, silhueta vista de cima, simplificação e junção de partes.

Uma **parte** é ``{"name", "material", "vertices": [[x, y, z], ...], "faces": [[i, j, k],
...]}``, no sistema local da forma livre. Sem Qt e sem IFC.
"""

from __future__ import annotations

import numpy as np
import shapely

from brasbim.core.document import OpError

DECIMALS = 4  # décimo de milímetro: o que se grava e o que se compara


def arrays(part: dict) -> tuple[np.ndarray, np.ndarray]:
    return (np.asarray(part["vertices"], dtype=float).reshape(-1, 3),
            np.asarray(part["faces"], dtype=np.int64).reshape(-1, 3))


def validate(parts) -> None:
    if not isinstance(parts, list) or not parts:
        raise OpError("a forma livre precisa de pelo menos uma parte com malha")
    for i, part in enumerate(parts):
        try:
            vertices, faces = arrays(part)
        except (KeyError, TypeError, ValueError):
            raise OpError(f"parte {i + 1}: malha inválida") from None
        if len(vertices) < 3 or len(faces) < 1 or not np.isfinite(vertices).all():
            raise OpError(f"parte {i + 1}: malha vazia")
        if faces.min() < 0 or faces.max() >= len(vertices):
            raise OpError(f"parte {i + 1}: face aponta para vértice que não existe")


def triangle_count(parts) -> int:
    return sum(len(p["faces"]) for p in parts)


def bounds(parts) -> tuple[float, float, float, float, float, float]:
    """(xmin, xmax, ymin, ymax, zmin, zmax) de todas as partes."""
    pts = np.vstack([arrays(p)[0] for p in parts])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    return tuple(float(c) for c in (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))


def size(parts) -> tuple[float, float, float]:
    b = bounds(parts)
    return b[1] - b[0], b[3] - b[2], b[5] - b[4]


def is_closed(part: dict) -> bool:
    """Cada aresta é usada por exatamente duas faces, uma em cada sentido."""
    _, faces = arrays(part)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    forward = {(int(a), int(b)) for a, b in edges}
    if len(forward) != len(edges):
        return False
    return all((b, a) in forward for a, b in forward)


def volume(parts) -> float | None:
    """Soma dos volumes das partes (as que se sobrepõem contam duas vezes); ``None`` se
    alguma parte é aberta."""
    total = 0.0
    for part in parts:
        if not is_closed(part):
            return None
        v, f = arrays(part)
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        total += float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    return total


def silhouette(parts, tolerance: float = 0.002) -> list[list[tuple[float, float]]]:
    """Contornos (anéis fechados, sem repetir o primeiro ponto) da forma vista de cima:
    a reunião dos triângulos projetados. O contorno de fora vem anti-horário; o de um
    furo, horário."""
    polygons = []
    for part in parts:
        v, f = arrays(part)
        tri = v[f][:, :, :2]
        a, b = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        area = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
        tri = tri[area > 1e-10]
        if len(tri):
            polygons.append(shapely.polygons(tri))
    if not polygons:
        return []
    union = shapely.union_all(np.concatenate(polygons), grid_size=1e-5)
    union = shapely.simplify(union, tolerance)
    rings = []
    for polygon in getattr(union, "geoms", [union]):
        if polygon.is_empty or polygon.geom_type != "Polygon":
            continue
        for k, ring in enumerate((polygon.exterior, *polygon.interiors)):
            coords = [(round(x, DECIMALS), round(y, DECIMALS)) for x, y in ring.coords[:-1]]
            if len(coords) < 3:
                continue
            if ring.is_ccw != (k == 0):  # de fora anti-horário; furo horário
                coords.reverse()
            rings.append(coords)
    return rings


def crease_edges(vertices: np.ndarray, faces: np.ndarray, angle: float = 30.0) -> np.ndarray:
    """Arestas que se desenham numa malha (pares de índices de ``vertices``): as quinas
    (ângulo entre as faces maior que ``angle``) e as bordas. As divisões de uma superfície
    curva ou plana ficam de fora, para a malha não aparecer como arame (§6)."""
    vertices = np.asarray(vertices, dtype=float).reshape(-1, 3)
    faces = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    if not len(faces):
        return np.zeros((0, 2), dtype=np.int64)
    _, first, weld = np.unique(np.round(vertices, 5), axis=0, return_index=True,
                               return_inverse=True)
    weld = weld.reshape(-1)
    tri = vertices[faces]
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normals, axis=1)
    good = length > 1e-14
    normals[good] /= length[good][:, None]
    welded = weld[faces]
    pairs = np.concatenate([welded[:, [0, 1]], welded[:, [1, 2]], welded[:, [2, 0]]])
    owner = np.tile(np.arange(len(faces)), 3)
    keep = (pairs[:, 0] != pairs[:, 1]) & good[owner]
    pairs, owner = np.sort(pairs[keep], axis=1), owner[keep]
    if not len(pairs):
        return np.zeros((0, 2), dtype=np.int64)
    unique, inverse, counts = np.unique(pairs, axis=0, return_inverse=True,
                                        return_counts=True)
    inverse = inverse.reshape(-1)
    hard = counts != 2
    order = np.argsort(inverse, kind="stable")
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    two = np.flatnonzero(counts == 2)
    a, b = owner[order[starts[two]]], owner[order[starts[two] + 1]]
    cos = np.einsum("ij,ij->i", normals[a], normals[b])
    hard[two[cos < np.cos(np.radians(angle))]] = True
    return first[unique[hard]]


def transformed(parts, scale=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), matrix=None) -> list:
    """Cópia das partes com os vértices esticados (e girados por ``matrix`` 3 × 3) e
    deslocados. Escala negativa (espelho) inverte o sentido das faces."""
    scale = np.asarray(scale, dtype=float)
    flip = np.prod(scale) < 0 or (matrix is not None and np.linalg.det(matrix) < 0)
    out = []
    for part in parts:
        v, f = arrays(part)
        v = v * scale
        if matrix is not None:
            v = v @ np.asarray(matrix, dtype=float).T
        v = v + np.asarray(offset, dtype=float)
        out.append({**part, "vertices": np.round(v, DECIMALS).tolist(),
                    "faces": (f[:, ::-1] if flip else f).tolist()})
    return out


def merged(parts) -> list:
    """Junta as partes de mesmo material (e nome) numa só."""
    out: dict[tuple, dict] = {}
    for part in parts:
        v, f = arrays(part)
        key = (part.get("material") or None, part.get("name") or "Corpo")
        into = out.setdefault(key, {"name": key[1], "material": key[0], "v": [], "f": [],
                                    "n": 0})
        into["f"].append(f + into["n"])
        into["v"].append(v)
        into["n"] += len(v)
    return [{"name": p["name"], "material": p["material"],
             "vertices": np.round(np.vstack(p["v"]), DECIMALS).tolist(),
             "faces": np.vstack(p["f"]).tolist()} for p in out.values()]


def cleaned(parts) -> list:
    """Solda os vértices repetidos (no décimo de milímetro) e tira as faces degeneradas."""
    out = []
    for part in parts:
        v, f = arrays(part)
        unique, inverse = np.unique(np.round(v, DECIMALS), axis=0, return_inverse=True)
        f = inverse.reshape(-1)[f]
        keep = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])
        f = f[keep]
        if len(f):
            out.append({**part, "vertices": unique.tolist(), "faces": f.tolist()})
    return out


def simplified(parts, limit: int) -> list:
    """Reduz a malha a no máximo ``limit`` triângulos, agrupando os vértices numa grade
    cada vez mais grossa (as partes guardam a proporção de triângulos entre si)."""
    total = triangle_count(parts)
    if total <= limit:
        return parts
    lo = np.array(bounds(parts)[0::2])
    span = max(size(parts)) or 1.0
    cell = span / 200.0
    for _ in range(40):
        out = []
        for part in parts:
            v, f = arrays(part)
            keys = np.floor((v - lo) / cell).astype(np.int64)
            _, inverse, counts = np.unique(keys, axis=0, return_inverse=True,
                                           return_counts=True)
            inverse = inverse.reshape(-1)
            sums = np.zeros((len(counts), 3))
            np.add.at(sums, inverse, v)
            f2 = inverse[f]
            keep = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
            f2 = np.unique(f2[keep], axis=0)
            if len(f2):
                out.append({**part, "vertices": np.round(sums / counts[:, None],
                                                         DECIMALS).tolist(),
                            "faces": f2.tolist()})
        if out and triangle_count(out) <= limit:
            return out
        cell *= 1.25
    raise OpError("não foi possível simplificar a malha")
