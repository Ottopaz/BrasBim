# SPDX-License-Identifier: GPL-3.0-or-later
"""Malhas da vista 3D (``spec/ui/01-janela-e-ferramentas.md`` §4), sem Qt nem OpenGL.

Cada elemento é triangulado pelo ``ifcopenshell.geom`` em coordenadas do mundo e guardado
com cores já sombreadas (luz fixa), para a vista só desenhar. ``update`` refaz apenas os
GlobalIds informados pelo histórico; ``tessellations`` conta quantas triangulações foram
feitas (usado nos testes).

Também ficam aqui, sem Qt, a câmera da vista 3D e a escolha de elementos por raio
(``spec/ui/07-medidas-e-edicao-no-3d.md`` §3).
"""

from __future__ import annotations

import logging
import math
import zlib
from dataclasses import dataclass

import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np

log = logging.getLogger(__name__)

# Cores por material (RGB 0–1). Materiais sem cor própria recebem uma da paleta, sempre a
# mesma para o mesmo nome.
_MATERIAL_COLORS = {
    "Bloco cerâmico": (0.80, 0.55, 0.42),
    "Reboco": (0.86, 0.84, 0.80),
    "Concreto": (0.70, 0.70, 0.68),
    "Gesso acartonado": (0.92, 0.92, 0.90),
    "Montante de aço": (0.65, 0.68, 0.72),
    "Madeira": (0.62, 0.44, 0.27),
    "Vidro": (0.65, 0.80, 0.88),
}
_PALETTE = [(0.79, 0.64, 0.49), (0.62, 0.71, 0.78), (0.66, 0.77, 0.60), (0.83, 0.71, 0.51),
            (0.73, 0.64, 0.79), (0.79, 0.60, 0.60)]
_LIGHT = np.array([0.35, 0.5, 0.79]) / np.linalg.norm([0.35, 0.5, 0.79])


def material_color(element) -> tuple[float, float, float]:
    material = ifcopenshell.util.element.get_material(element)
    name = None
    if material is not None:
        if material.is_a("IfcMaterialLayerSetUsage"):
            material = material.ForLayerSet
        if material.is_a("IfcMaterialLayerSet"):
            layers = [la for la in material.MaterialLayers if la.Material is not None]
            if layers:
                name = max(layers, key=lambda la: la.LayerThickness or 0).Material.Name
        elif material.is_a("IfcMaterialConstituentSet"):
            items = [c for c in material.MaterialConstituents or [] if c.Material is not None]
            if items:
                name = items[0].Material.Name
        elif material.is_a("IfcMaterial"):
            name = material.Name
    if name in _MATERIAL_COLORS:
        return _MATERIAL_COLORS[name]
    key = name or element.is_a()
    return _PALETTE[zlib.crc32(key.encode()) % len(_PALETTE)]


@dataclass
class Mesh:
    vertices: np.ndarray  # (n, 3) float32, triângulos sem índice
    colors: np.ndarray  # (n, 3) float32
    edges: np.ndarray  # (m, 3) float32, pares de pontos
    base: tuple[float, float, float]


def _shaded(vertices: np.ndarray, color) -> np.ndarray:
    tri = vertices.reshape(-1, 3, 3)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(length > 0, length, 1)[:, None]
    light = 0.45 + 0.55 * np.abs(normals @ _LIGHT)
    return np.repeat(np.clip(np.outer(light, color), 0, 1), 3, axis=0).astype(np.float32)


class Scene:
    """Malhas por GlobalId."""

    CLASSES = ("IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcColumn", "IfcBeam")

    def __init__(self):
        self.meshes: dict[str, Mesh] = {}
        self.tessellations = 0
        self._settings = ifcopenshell.geom.settings()
        self._settings.set("use-world-coords", True)

    def _wanted(self, entity) -> bool:
        return (entity is not None and any(entity.is_a(c) for c in self.CLASSES)
                and entity.Representation is not None)

    def _mesh(self, entity) -> Mesh | None:
        self.tessellations += 1
        try:
            shape = ifcopenshell.geom.create_shape(self._settings, entity)
        except RuntimeError as e:
            log.debug("sem geometria 3D para %s: %s", entity.GlobalId, e)
            return None
        g = shape.geometry
        verts = np.asarray(g.verts, dtype=np.float32).reshape(-1, 3)
        faces = np.asarray(g.faces, dtype=np.int64)
        edges = np.asarray(g.edges, dtype=np.int64)
        if not len(faces):
            return None
        color = material_color(entity)
        tri = verts[faces]
        return Mesh(tri, _shaded(tri, color), verts[edges], color)

    def load(self, ifc) -> None:
        self.meshes.clear()
        for cls in self.CLASSES:
            for entity in ifc.by_type(cls):
                if self._wanted(entity):
                    mesh = self._mesh(entity)
                    if mesh is not None:
                        self.meshes[entity.GlobalId] = mesh

    def update(self, ifc, changed: set[str]) -> None:
        for gid in changed:
            try:
                entity = ifc.by_guid(gid)
            except RuntimeError:
                entity = None
            if not self._wanted(entity):
                self.meshes.pop(gid, None)
                continue
            mesh = self._mesh(entity)
            if mesh is None:
                self.meshes.pop(gid, None)
            else:
                self.meshes[gid] = mesh

    def bounds(self) -> tuple[np.ndarray, np.ndarray] | None:
        if not self.meshes:
            return None
        lows = [m.vertices.min(axis=0) for m in self.meshes.values()]
        highs = [m.vertices.max(axis=0) for m in self.meshes.values()]
        return np.min(lows, axis=0), np.max(highs, axis=0)


    def pick(self, origin, direction, only=None) -> tuple[str, np.ndarray] | None:
        """Primeiro elemento atingido pelo raio: (GlobalId, ponto), ou None (spec/ui 07
        §3.1). ``only`` limita a busca a esses GlobalIds."""
        origin = np.asarray(origin, dtype=np.float64)
        direction = np.asarray(direction, dtype=np.float64)
        best = None
        for gid, mesh in self.meshes.items():
            if only is not None and gid not in only:
                continue
            low, high = mesh.vertices.min(axis=0), mesh.vertices.max(axis=0)
            if not _hits_box(origin, direction, low, high):
                continue
            t = ray_triangles(origin, direction, mesh.vertices.reshape(-1, 3, 3))
            if t is not None and (best is None or t < best[1]):
                best = (gid, t)
        if best is None:
            return None
        return best[0], origin + best[1] * direction

    def selection_bounds(self, gids) -> tuple[np.ndarray, np.ndarray] | None:
        meshes = [m for g, m in self.meshes.items() if g in gids]
        if not meshes:
            return None
        return (np.min([m.vertices.min(axis=0) for m in meshes], axis=0),
                np.max([m.vertices.max(axis=0) for m in meshes], axis=0))


def _hits_box(origin, direction, low, high, pad=1e-6) -> bool:
    """O raio passa pela caixa? (teste por faixas)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / direction
        t1, t2 = (low - pad - origin) * inv, (high + pad - origin) * inv
    t1, t2 = np.nan_to_num(t1, nan=-np.inf), np.nan_to_num(t2, nan=np.inf)
    near = np.max(np.minimum(t1, t2))
    far = np.min(np.maximum(t1, t2))
    return far >= max(near, 0.0)


def ray_triangles(origin, direction, tri) -> float | None:
    """Menor distância (em unidades de ``direction``) do raio aos triângulos (n, 3, 3), pelo
    algoritmo de Möller e Trumbore (1997); None se não atinge nenhum."""
    tri = np.asarray(tri, dtype=np.float64)
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    p = np.cross(direction, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = origin - tri[:, 0]
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = (q @ direction) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-6)
    if not hit.any():
        return None
    return float(t[hit].min())


def ray_plane(origin, direction, z: float) -> np.ndarray | None:
    """Interseção do raio com o plano horizontal na cota ``z``; None se paralelo ou atrás."""
    if abs(direction[2]) < 1e-9:
        return None
    t = (z - origin[2]) / direction[2]
    if t <= 0:
        return None
    return np.asarray(origin, dtype=np.float64) + t * np.asarray(direction, dtype=np.float64)


class Camera:
    """Órbita em torno de ``target`` (spec/ui 01 §4): ``yaw`` e ``pitch`` em radianos."""

    FOVY = 45.0

    def __init__(self):
        self.target = np.zeros(3)
        self.distance = 20.0
        self.yaw, self.pitch = math.radians(-60), math.radians(30)

    def eye(self) -> np.ndarray:
        cp = math.cos(self.pitch)
        direction = np.array([cp * math.cos(self.yaw), cp * math.sin(self.yaw),
                              math.sin(self.pitch)])
        return self.target + self.distance * direction

    def axes(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(frente, direita, cima) da câmera, unitários."""
        forward = self.target - self.eye()
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, [0, 0, 1.0])
        right /= max(np.linalg.norm(right), 1e-12)
        return forward, right, np.cross(right, forward)

    def projection(self, aspect: float) -> np.ndarray:
        return perspective(self.FOVY, aspect, self.distance / 200, self.distance * 20)

    def view(self) -> np.ndarray:
        return look_at(self.eye(), self.target, np.array([0, 0, 1.0]))

    def ray(self, x: float, y: float, width: int, height: int):
        """Raio (origem, direção unitária) pelo pixel (x, y) da tela."""
        forward, right, up = self.axes()
        k = math.tan(math.radians(self.FOVY) / 2)
        aspect = width / max(height, 1)
        nx, ny = 2 * x / max(width, 1) - 1, 1 - 2 * y / max(height, 1)
        d = forward + right * nx * k * aspect + up * ny * k
        return self.eye(), d / np.linalg.norm(d)

    def project(self, point, width: int, height: int) -> tuple[float, float] | None:
        """Pixel do ponto 3D, ou None se está atrás da câmera."""
        forward, right, up = self.axes()
        v = np.asarray(point, dtype=np.float64) - self.eye()
        depth = float(v @ forward)
        if depth <= 1e-9:
            return None
        k = math.tan(math.radians(self.FOVY) / 2)
        aspect = width / max(height, 1)
        nx = float(v @ right) / (depth * k * aspect)
        ny = float(v @ up) / (depth * k)
        return (nx + 1) * width / 2, (1 - ny) * height / 2

    def pixel_size(self, point, height: int) -> float:
        """Tamanho de um pixel, em metros, na profundidade do ponto."""
        forward, _, _ = self.axes()
        depth = max(float((np.asarray(point) - self.eye()) @ forward), 1e-6)
        return 2 * depth * math.tan(math.radians(self.FOVY) / 2) / max(height, 1)

    def frame(self, low, high) -> None:
        """Centra a órbita na caixa e ajusta a distância, mantendo a direção (§4)."""
        low, high = np.asarray(low, dtype=np.float64), np.asarray(high, dtype=np.float64)
        self.target = (low + high) / 2
        self.distance = max(float(np.linalg.norm(high - low)) * 1.6, 2.0)


def perspective(fovy: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1 / math.tan(math.radians(fovy) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def look_at(eye, target, up) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def affine_of(fn) -> np.ndarray:
    """Matriz 3×3 (homogênea, em x, y) de uma transformação afim 2D dada como função."""
    o, ex, ey = fn((0.0, 0.0)), fn((1.0, 0.0)), fn((0.0, 1.0))
    return np.array([[ex[0] - o[0], ey[0] - o[0], o[0]],
                     [ex[1] - o[1], ey[1] - o[1], o[1]],
                     [0.0, 0.0, 1.0]])


def transformed(vertices: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Vértices (n, 3) com x, y transformados pela matriz 2D; z mantido."""
    out = vertices.astype(np.float32, copy=True)
    xy = vertices[:, :2].astype(np.float64)
    out[:, :2] = xy @ matrix[:2, :2].T + matrix[:2, 2]
    return out
