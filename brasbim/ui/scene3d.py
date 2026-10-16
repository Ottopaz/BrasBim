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
from dataclasses import dataclass

import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import numpy as np

from brasbim.core import clip, geom2d, layers, materials, mesh_layers
from brasbim.core.document import OpError
from brasbim.core.structure import roofs
from brasbim.core.walls import rebuild
from brasbim.core.walls.wall import read_state as read_wall

log = logging.getLogger(__name__)

_LIGHT = np.array([0.35, 0.5, 0.79]) / np.linalg.norm([0.35, 0.5, 0.79])


def color_of(material) -> tuple[float, float, float]:
    """Cor do 3D: a do estilo gravado no ``IfcMaterial`` ou a padrão pelo nome
    (spec/ui 06 §4)."""
    found = materials.read_style(material) if material is not None else None
    style = found or materials.default_style(material.Name if material is not None else None)
    return materials.rgb(style["color"])


def material_color(element) -> tuple[float, float, float]:
    """Cor do elemento inteiro: a do material (a camada mais espessa num conjunto; o
    material do perfil no pilar e na viga)."""
    material = ifcopenshell.util.element.get_material(element)
    found = None
    if material is not None:
        if material.is_a("IfcMaterialLayerSetUsage"):
            material = material.ForLayerSet
        elif material.is_a("IfcMaterialProfileSetUsage"):
            material = material.ForProfileSet
        if material.is_a("IfcMaterialProfileSet"):
            profiles = [p for p in material.MaterialProfiles or [] if p.Material is not None]
            if profiles:
                found = profiles[0].Material
        elif material.is_a("IfcMaterialLayerSet"):
            layers = [la for la in material.MaterialLayers if la.Material is not None]
            if layers:
                found = max(layers, key=lambda la: la.LayerThickness or 0).Material
        elif material.is_a("IfcMaterialConstituentSet"):
            items = [c for c in material.MaterialConstituents or [] if c.Material is not None]
            if items:
                found = items[0].Material
        elif material.is_a("IfcMaterial"):
            found = material
    if found is None:
        return materials.rgb(materials.default_style(element.is_a())["color"])
    return color_of(found)


@dataclass
class Mesh:
    vertices: np.ndarray  # (n, 3) float32, triângulos sem índice
    colors: np.ndarray  # (n, 3) float32
    edges: np.ndarray  # (m, 3) float32, pares de pontos
    base: tuple[float, float, float]
    parts: dict | None = None  # parede por camadas: {material: triângulos (n, 3, 3)}
    glass: np.ndarray | None = None  # triângulos translúcidos (vidro), (n, 3) float32
    glass_colors: np.ndarray | None = None  # (n, 4): RGBA

    @property
    def all_vertices(self) -> np.ndarray:
        """Triângulos opacos e translúcidos juntos (escolha por raio e limites)."""
        if self.glass is None:
            return self.vertices
        return np.concatenate([self.vertices, self.glass])


def _shaded(vertices: np.ndarray, color) -> np.ndarray:
    tri = vertices.reshape(-1, 3, 3)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(normals, axis=1)
    normals = normals / np.where(length > 0, length, 1)[:, None]
    light = 0.45 + 0.55 * np.abs(normals @ _LIGHT)
    return np.repeat(np.clip(np.outer(light, color), 0, 1), 3, axis=0).astype(np.float32)


def _shading_of(ifc, name: str):
    """``IfcSurfaceStyleShading`` pelo nome que o IfcOpenShell dá ao material da face
    (``IfcSurfaceStyleShading-<id>``)."""
    try:
        entity = ifc.by_id(int(name.rsplit("-", 1)[1]))
    except (IndexError, ValueError, RuntimeError):
        return None
    return entity if entity.is_a("IfcSurfaceStyleShading") else None


def _styled_mesh(entity, g, tri: np.ndarray, edges: np.ndarray, color) -> Mesh | None:
    """Esquadria com uma cor por peça (``IfcStyledItem`` do material, spec/ui 09 §7); as
    peças com transparência (vidro) vão à parte, para o desenho translúcido."""
    ids = np.asarray(g.material_ids, dtype=np.int64)
    if not len(ids) or 3 * len(ids) != len(tri):  # ``tri``: 3 vértices por face
        return None
    looks = []
    for material in g.materials:
        shading = _shading_of(entity.file, material.name)
        if shading is None or shading.SurfaceColour is None:
            looks.append((color, 0.0))
            continue
        c = shading.SurfaceColour
        looks.append(((c.Red, c.Green, c.Blue), float(shading.Transparency or 0.0)))
    if not looks:
        return None
    solid_tri, solid_col, glass_tri, glass_col = [], [], [], []
    for i, (rgb, transparency) in enumerate(looks):
        part = tri[np.repeat((ids == i) | ((ids < 0) & (i == 0)), 3)]
        if not len(part):
            continue
        flat = part.astype(np.float32).reshape(-1, 3)
        shaded = _shaded(flat, rgb)
        if transparency > 1e-6:
            glass_tri.append(flat)
            glass_col.append(np.c_[shaded, np.full(len(shaded), 1 - transparency)])
        else:
            solid_tri.append(flat)
            solid_col.append(shaded)
    if not solid_tri and not glass_tri:
        return None
    empty = np.zeros((0, 3), dtype=np.float32)
    return Mesh(np.concatenate(solid_tri) if solid_tri else empty,
                np.concatenate(solid_col) if solid_col else empty, edges, color,
                glass=np.concatenate(glass_tri) if glass_tri else None,
                glass_colors=(np.concatenate(glass_col).astype(np.float32)
                              if glass_col else None))


class Scene:
    """Malhas por GlobalId."""

    CLASSES = ("IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcColumn", "IfcBeam", "IfcRoof")

    def __init__(self):
        self.doc = None  # Document: com ele, paredes com cor por camada (spec/ui 06 §5)
        self.meshes: dict[str, Mesh] = {}
        self._layers: dict[str, dict] = {}  # por pavimento: {parede: [(material, anéis)]}
        self.tessellations = 0
        self._settings = ifcopenshell.geom.settings()
        self._settings.set("use-world-coords", True)

    def _wanted(self, entity) -> bool:
        if entity is None:
            return False
        if entity.is_a("IfcRoof"):  # a cobertura é a soma das águas (cobertura.md §2.1)
            return roofs.is_roof(entity)
        return (any(entity.is_a(c) for c in self.CLASSES) and entity.Representation is not None
                and not roofs.is_part(entity))

    def _roof_mesh(self, roof) -> Mesh | None:
        found = [m for m in (self._mesh(p) for p in roofs.parts_of(roof)) if m is not None]
        if not found:
            return None
        return Mesh(np.concatenate([m.vertices for m in found]),
                    np.concatenate([m.colors for m in found]),
                    np.concatenate([m.edges for m in found]), found[0].base)

    def _mesh(self, entity) -> Mesh | None:
        if entity.is_a("IfcRoof"):
            return self._roof_mesh(entity)
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
        if entity.is_a("IfcDoor") or entity.is_a("IfcWindow"):
            styled = _styled_mesh(entity, g, tri, verts[edges], color)
            if styled is not None:
                return styled
        layered = (self._split(entity, tri) if entity.is_a("IfcWall")
                   else _slab_layers(entity, tri) if entity.is_a("IfcSlab") else None)
        if layered is None:
            return Mesh(tri, _shaded(tri, color), verts[edges], color)
        names = {m.Name: m for m in self.doc.ifc.by_type("IfcMaterial")}
        parts_tri, parts_color = [], []
        for key, part in layered.items():
            c = color if key is None else color_of(names.get(key))
            parts_tri.append(part.astype(np.float32).reshape(-1, 3))
            parts_color.append(_shaded(parts_tri[-1], c))
        return Mesh(np.concatenate(parts_tri), np.concatenate(parts_color), verts[edges], color,
                    layered)

    def _split(self, wall, tri: np.ndarray) -> dict | None:
        """Triângulos da parede por material, pelas regiões das camadas (as mesmas da
        planta por camadas); ``None`` sem camadas ou tombada."""
        if self.doc is None:
            return None
        storey = ifcopenshell.util.element.get_container(wall)
        if storey is None or not storey.is_a("IfcBuildingStorey"):
            return None
        regions = self._storey_layers(storey).get(wall.GlobalId)
        if not regions:
            return None
        m = (ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)
             if storey.ObjectPlacement is not None else np.eye(4))
        flat = tri.reshape(-1, 3).astype(np.float64)
        local = (np.c_[flat, np.ones(len(flat))] @ np.linalg.inv(m).T)[:, :3]
        out = {}
        for key, part in mesh_layers.split(local, regions).items():
            pts = part.reshape(-1, 3)
            out[key] = (np.c_[pts, np.ones(len(pts))] @ m.T)[:, :3].reshape(-1, 3, 3)
        return out

    def _storey_layers(self, storey) -> dict:
        if storey.GlobalId not in self._layers:
            self._layers[storey.GlobalId] = _wall_layers(self.doc, storey)
        return self._layers[storey.GlobalId]

    def load(self, ifc, doc=None) -> None:
        if doc is not None:
            self.doc = doc
        self._layers.clear()
        self.meshes.clear()
        for cls in self.CLASSES:
            for entity in ifc.by_type(cls):
                if self._wanted(entity):
                    mesh = self._mesh(entity)
                    if mesh is not None:
                        self.meshes[entity.GlobalId] = mesh

    def update(self, ifc, changed: set[str]) -> None:
        self._layers.clear()
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
        lows = [m.all_vertices.min(axis=0) for m in self.meshes.values()]
        highs = [m.all_vertices.max(axis=0) for m in self.meshes.values()]
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
            verts = mesh.all_vertices
            low, high = verts.min(axis=0), verts.max(axis=0)
            if not _hits_box(origin, direction, low, high):
                continue
            t = ray_triangles(origin, direction, verts.reshape(-1, 3, 3))
            if t is not None and (best is None or t < best[1]):
                best = (gid, t)
        if best is None:
            return None
        return best[0], origin + best[1] * direction

    def selection_bounds(self, gids) -> tuple[np.ndarray, np.ndarray] | None:
        meshes = [m for g, m in self.meshes.items() if g in gids]
        if not meshes:
            return None
        return (np.min([m.all_vertices.min(axis=0) for m in meshes], axis=0),
                np.max([m.all_vertices.max(axis=0) for m in meshes], axis=0))


def _wall_layers(doc, storey) -> dict:
    """{parede: [(material, anéis)]} das paredes do pavimento, em coordenadas dele; só
    paredes com camadas e sem inclinação."""
    walls, pieces = [], {}
    for wall in ifcopenshell.util.element.get_decomposition(storey):
        if not wall.is_a("IfcWall"):
            continue
        try:
            state = read_wall(doc, wall)
            band = rebuild.band(doc, state)
            segments = rebuild.profile(doc, wall, band)
        except (OpError, ValueError):
            continue
        if abs(state.get("tilt") or 0.0) > 1e-9:
            continue
        walls.append(wall)
        pieces[wall.GlobalId] = [[band.frame.to_global(p) for p in geom2d.polygon(segments)]]
    out: dict = {}
    for r in layers.regions(doc, sorted(walls, key=lambda w: w.GlobalId), pieces):
        out.setdefault(r.owner, {}).setdefault(r.material, []).extend(r.rings)
    return {gid: [(m, clip.union(rings)) for m, rings in groups.items()]
            for gid, groups in out.items()}


def _clip_z(poly: list, z: float, keep_above: bool) -> list:
    """Polígono 3D cortado pelo plano horizontal ``z`` (fica a parte de cima ou de baixo)."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        p_in = p[2] >= z if keep_above else p[2] <= z
        q_in = q[2] >= z if keep_above else q[2] <= z
        if p_in:
            out.append(p)
        if p_in != q_in:
            t = (z - p[2]) / (q[2] - p[2])
            out.append(p + t * (q - p))
    return out


def _slab_layers(slab, tri: np.ndarray) -> dict | None:
    """Laje com camadas (spec/ui 10 §7): triângulos por material, cortados nas cotas das
    divisas, de baixo (camada 1) para cima. ``None`` com uma camada só."""
    usage = ifcopenshell.util.element.get_material(slab, should_inherit=False)
    if usage is None or not usage.is_a("IfcMaterialLayerSetUsage"):
        return None
    found = [(la.Material.Name if la.Material else None, float(la.LayerThickness or 0.0))
             for la in usage.ForLayerSet.MaterialLayers]
    if len(found) < 2:
        return None
    flat = tri.reshape(-1, 3, 3).astype(np.float64)
    z, top = float(flat[:, :, 2].min()), float(flat[:, :, 2].max())
    total = sum(t for _, t in found)
    if total <= 0 or abs((top - z) - total) > 1e-3:
        return None  # o corpo não é a pilha de camadas (outra origem)
    out: dict = {}
    for k, (name, thickness) in enumerate(found):
        z0, z1 = z, z + thickness
        z = z1
        lo, hi = (-np.inf if k == 0 else z0), (np.inf if k == len(found) - 1 else z1)
        pieces = []
        for t in flat:
            poly = _clip_z(_clip_z(list(t), lo, True), hi, False)
            if len(poly) < 3:
                continue
            pieces += [np.array([poly[0], poly[i], poly[i + 1]])
                       for i in range(1, len(poly) - 1)]
        if pieces:
            stacked = np.array(pieces)
            out[name] = (np.concatenate([out[name], stacked]) if name in out else stacked)
    return out or None


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
