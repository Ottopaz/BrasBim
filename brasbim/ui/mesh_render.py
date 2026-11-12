# SPDX-License-Identifier: GPL-3.0-or-later
"""Imagem de uma malha em vistas fixas, sem OpenGL, para a IA conferir o que modelou
(``spec/ui/54-assistente-foto-e-objeto-novo.md`` §3.3, ``spec/elementos/forma-livre.md``
§4.1).

Cada vista é rasterizada com memória de profundidade (o que está na frente cobre o que
está atrás, mesmo com peças que se atravessam). As linhas saem da própria imagem: onde
muda a peça, onde a profundidade salta e onde a face vira de lado.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtGui import QColor, QImage

from brasbim.core import materials
from brasbim.ui import theme

_LIGHT = np.array([0.35, -0.55, 0.76])
_CREASE = math.cos(math.radians(32.0))


def _basis(azimuth: float, elevation: float) -> np.ndarray:
    """Linhas: u (direita), v (cima), w (para o olho), como ``object_preview._project``."""
    a, e = math.radians(azimuth), math.radians(elevation)
    return np.array([
        [math.cos(a), -math.sin(a), 0.0],
        [math.sin(a) * math.sin(e), math.cos(a) * math.sin(e), math.cos(e)],
        [-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)]])


def _rgb(material: str | None) -> np.ndarray:
    color = QColor(materials.default_style(material)["color"]) if material \
        else QColor(theme.INK_SOFT)
    return np.array([color.red(), color.green(), color.blue()], dtype=float)


def render(tris: np.ndarray, colors: np.ndarray, groups: np.ndarray, azimuth: float,
           elevation: float, width: int, height: int, background=(248, 248, 246),
           margin: float = 0.07) -> np.ndarray:
    """Imagem (altura, largura, 3) uint8 dos triângulos ``tris`` (n, 3, 3) com a cor base
    ``colors`` (n, 3) e o grupo ``groups`` (n,) de cada um."""
    image = np.empty((height, width, 3), dtype=np.uint8)
    image[:] = background
    if not len(tris):
        return image
    basis = _basis(azimuth, elevation)
    p = tris @ basis.T  # (n, 3, 3): u, v, w
    lo, hi = p.reshape(-1, 3).min(axis=0), p.reshape(-1, 3).max(axis=0)
    span = np.maximum(hi[:2] - lo[:2], 1e-9)
    scale = (1 - 2 * margin) * min(width / span[0], height / span[1])
    x = (p[:, :, 0] - (lo[0] + hi[0]) / 2) * scale + width / 2
    y = height / 2 - (p[:, :, 1] - (lo[1] + hi[1]) / 2) * scale
    w = p[:, :, 2]
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    length = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(length > 1e-14, length, 1.0)[:, None]
    facing = normals @ basis[2]
    normals = np.where((facing < 0)[:, None], -normals, normals)  # malha vista dos dois lados
    shade = 0.56 + 0.44 * np.clip(normals @ _LIGHT, 0.0, 1.0)
    rgb = np.clip(colors * shade[:, None], 0, 255)
    depth = np.full((height, width), -np.inf)
    owner = np.full((height, width), -1, dtype=np.int64)
    x0 = np.clip(np.floor(x.min(axis=1)).astype(int), 0, width - 1)
    x1 = np.clip(np.ceil(x.max(axis=1)).astype(int), 0, width - 1)
    y0 = np.clip(np.floor(y.min(axis=1)).astype(int), 0, height - 1)
    y1 = np.clip(np.ceil(y.max(axis=1)).astype(int), 0, height - 1)
    area = ((x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0])
            - (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0]))
    for i in np.flatnonzero(np.abs(area) > 1e-9):
        xs = np.arange(x0[i], x1[i] + 1) + 0.5
        ys = np.arange(y0[i], y1[i] + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        l1 = ((x[i, 1] - gx) * (y[i, 2] - gy) - (x[i, 2] - gx) * (y[i, 1] - gy)) / area[i]
        l2 = ((x[i, 2] - gx) * (y[i, 0] - gy) - (x[i, 0] - gx) * (y[i, 2] - gy)) / area[i]
        l3 = 1.0 - l1 - l2
        z = l1 * w[i, 0] + l2 * w[i, 1] + l3 * w[i, 2]
        window = depth[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1]
        hit = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9) & (z > window)
        if hit.any():
            window[hit] = z[hit]
            owner[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1][hit] = i
    seen = owner >= 0
    image[seen] = rgb[owner[seen]].astype(np.uint8)
    # linhas: muda a peça, salta a profundidade ou a face vira (comparando com o vizinho
    # da direita e com o de baixo)
    group = np.where(seen, groups[np.maximum(owner, 0)], -1)
    normal = np.where(seen[:, :, None], normals[np.maximum(owner, 0)], 0.0)
    flat = np.where(seen, depth, lo[2] - 1.0)
    jump = 0.035 * max(float((hi - lo).max()), 1e-9)
    line = np.zeros((height, width), dtype=bool)
    for axis in (0, 1):
        a = [slice(None), slice(None)]
        b = [slice(None), slice(None)]
        a[axis], b[axis] = slice(0, -1), slice(1, None)
        a, b = tuple(a), tuple(b)
        differ = (group[a] != group[b]) | (np.abs(flat[a] - flat[b]) > jump) \
            | (seen[a] & seen[b] & (np.einsum("ijk,ijk->ij", normal[a], normal[b]) < _CREASE))
        line[a] |= differ
    image[line] = (38, 38, 40)
    return image


def to_qimage(pixels: np.ndarray) -> QImage:
    height, width = pixels.shape[:2]
    data = np.ascontiguousarray(pixels)
    return QImage(data.tobytes(), width, height, 3 * width, QImage.Format_RGB888).copy()


def arrays(tris: list) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``[(triângulo, material, grupo), ...]`` → (triângulos, cores, grupos)."""
    if not tris:
        return np.zeros((0, 3, 3)), np.zeros((0, 3)), np.zeros(0, dtype=np.int64)
    palette: dict = {}
    points = np.asarray([t[0] for t in tris], dtype=float)
    colors = np.asarray([palette.setdefault(t[1], _rgb(t[1])) for t in tris])
    groups = np.asarray([t[2] for t in tris], dtype=np.int64)
    return points, colors, groups
