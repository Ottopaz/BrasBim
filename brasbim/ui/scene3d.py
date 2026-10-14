# SPDX-License-Identifier: GPL-3.0-or-later
"""Malhas da vista 3D (``spec/ui/01-janela-e-ferramentas.md`` §4), sem Qt nem OpenGL.

Cada elemento é triangulado pelo ``ifcopenshell.geom`` em coordenadas do mundo e guardado
com cores já sombreadas (luz fixa), para a vista só desenhar. ``update`` refaz apenas os
GlobalIds informados pelo histórico; ``tessellations`` conta quantas triangulações foram
feitas (usado nos testes).
"""

from __future__ import annotations

import logging
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
