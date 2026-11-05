# SPDX-License-Identifier: LGPL-3.0-or-later
"""Exportar 3D para apresentação: glTF binário (.glb) e OBJ + MTL (spec/ui 48).

Cada elemento com corpo é triangulado pelo ``ifcopenshell.geom`` em coordenadas do
mundo; as faces com estilo levam a cor do estilo, as sem estilo a do material do
elemento (``element_color``). O z do IFC vira o y dos formatos (eixo para cima deles).
Sem Qt e sem biblioteca nova: os dois formatos são escritos aqui.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np

from brasbim.core import materials
from brasbim.core.document import Document, OpError

FORMATS = ("glb", "obj")
SKIP = ("IfcSpace", "IfcOpeningElement", "IfcAnnotation", "IfcGrid",
        "IfcSpatialStructureElement", "IfcVirtualElement")


@dataclass
class Part:
    """Triângulos (n × 3 × 3, y para cima) de uma cor."""

    color: tuple[float, float, float]
    alpha: float
    triangles: np.ndarray


@dataclass
class Item:
    gid: str
    name: str
    ifc_class: str
    type_name: str | None
    storey: str | None
    parts: list[Part] = field(default_factory=list)

    @property
    def triangle_count(self) -> int:
        return sum(len(p.triangles) for p in self.parts)


# --- cores ------------------------------------------------------------------------------


def _layer_material(element, usage):
    layers = [la for la in usage.ForLayerSet.MaterialLayers if la.Material is not None]
    if not layers:
        return None
    from brasbim.core.structure import coverings

    if element.is_a("IfcWall"):
        return layers[0].Material  # o acabamento de um dos lados
    if element.is_a("IfcCovering") and coverings.predefined(element) == "CEILING":
        return layers[0].Material  # a face de baixo é a que se vê
    return layers[-1].Material  # laje e piso: a de cima


def element_material(element):
    """Material que dá a cor do elemento inteiro (acabamento da parede, camada de cima da
    laje e do piso, de baixo do forro, material do perfil)."""
    material = ifcopenshell.util.element.get_material(element)
    if material is None:
        return None
    if material.is_a("IfcMaterialLayerSetUsage"):
        return _layer_material(element, material)
    if material.is_a("IfcMaterialLayerSet"):
        layers = [la.Material for la in material.MaterialLayers if la.Material]
        return layers[0] if layers else None
    if material.is_a("IfcMaterialProfileSetUsage"):
        material = material.ForProfileSet
    if material.is_a("IfcMaterialProfileSet"):
        found = [p.Material for p in material.MaterialProfiles or () if p.Material]
        return found[0] if found else None
    if material.is_a("IfcMaterialConstituentSet"):
        found = [c.Material for c in material.MaterialConstituents or () if c.Material]
        return found[0] if found else None
    if material.is_a("IfcMaterialList"):
        return material.Materials[0] if material.Materials else None
    return material if material.is_a("IfcMaterial") else None


def element_color(doc: Document, element) -> tuple[tuple[float, float, float], float]:
    """(cor, opacidade) do elemento pelo material; sem material, a padrão da classe."""
    material = element_material(element)
    name = material.Name if material is not None else element.is_a()
    style = materials.style(doc, name) if material is not None else \
        materials.default_style(name)
    return materials.rgb(style["color"]), 1.0 - float(style.get("transparency") or 0.0)


def _styled(style) -> bool:
    """Estilo de verdade (o motor dá o nome da classe ou "DefaultMaterial" sem estilo)."""
    name = style.name or ""
    return not (name == "DefaultMaterial" or (name.startswith("Ifc")
                                              and not name.startswith("IfcSurfaceStyle")))


# --- coleta ------------------------------------------------------------------------------


def _storey_of(element):
    current = element
    for _ in range(8):
        found = (ifcopenshell.util.element.get_container(current)
                 or ifcopenshell.util.element.get_aggregate(current))
        if found is None or found.is_a("IfcBuildingStorey"):
            return found
        current = found
    return None


def _wanted(element, hidden: set[str]) -> bool:
    return (element.Representation is not None and element.GlobalId not in hidden
            and not any(element.is_a(c) for c in SKIP))


def collect(doc: Document, visible_only: bool = True) -> list[Item]:
    """Elementos com corpo, triangulados e separados por cor."""
    from brasbim.core import display_layers

    hidden = set(display_layers.hidden_ids(doc)) if visible_only else set()
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    items = []
    for element in sorted(doc.ifc.by_type("IfcProduct"), key=lambda e: e.GlobalId):
        if not _wanted(element, hidden):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
        except RuntimeError:
            continue
        g = shape.geometry
        verts = np.asarray(g.verts, dtype=np.float64).reshape(-1, 3)
        faces = np.asarray(g.faces, dtype=np.int64).reshape(-1, 3)
        if not len(faces):
            continue
        tri = verts[faces][:, :, [0, 2, 1]] * np.array([1.0, 1.0, -1.0])  # z para cima → y
        ids = np.asarray(g.material_ids, dtype=np.int64) if len(g.material_ids) \
            else np.zeros(len(faces), dtype=np.int64)
        fallback = element_color(doc, element)
        groups: dict[tuple, list[np.ndarray]] = {}
        for index, style in enumerate(g.materials):
            mask = ids == index
            if not mask.any():
                continue
            if _styled(style):
                d = style.diffuse
                color = (d.r(), d.g(), d.b())
                t = style.transparency
                alpha = 1.0 - (0.0 if t is None or math.isnan(t) else float(t))
            else:
                color, alpha = fallback
            key = (tuple(round(c, 4) for c in color), round(alpha, 4))
            groups.setdefault(key, []).append(tri[mask])
        if not g.materials:
            groups[(fallback[0], fallback[1])] = [tri]
        element_type = ifcopenshell.util.element.get_type(element)
        storey = _storey_of(element)
        label = element.Name or (element_type.Name if element_type else None) \
            or element.is_a()[3:]
        items.append(Item(element.GlobalId, label,
                          element.is_a(), element_type.Name if element_type else None,
                          storey.Name if storey is not None else None,
                          [Part(c, a, np.concatenate(t)) for (c, a), t in groups.items()]))
    return items


# --- glTF -------------------------------------------------------------------------------


def _normals(tri: np.ndarray) -> np.ndarray:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, length, out=np.zeros_like(n), where=length > 1e-12)
    n[(length[:, 0] <= 1e-12)] = (0.0, 1.0, 0.0)
    return np.repeat(n, 3, axis=0)


def gltf(items: list[Item], name: str = "BrasBim") -> tuple[dict, bytes]:
    """(JSON, buffer binário) de uma cena glTF 2.0."""
    blob = bytearray()
    doc = {"asset": {"version": "2.0", "generator": "BrasBim"}, "scene": 0,
           "scenes": [{"name": name, "nodes": []}], "nodes": [], "meshes": [],
           "materials": [], "accessors": [], "bufferViews": [],
           "buffers": [{"byteLength": 0}]}
    material_of: dict[tuple, int] = {}
    storeys: dict[str | None, int] = {}

    def view(data: bytes, target: int) -> int:
        while len(blob) % 4:
            blob.append(0)
        doc["bufferViews"].append({"buffer": 0, "byteOffset": len(blob),
                                   "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(doc["bufferViews"]) - 1

    def material(color, alpha) -> int:
        key = (color, alpha)
        if key not in material_of:
            m = {"name": f"#{''.join(f'{round(c * 255):02X}' for c in color)}",
                 "pbrMetallicRoughness": {"baseColorFactor": [*map(float, color),
                                                              float(alpha)],
                                          "metallicFactor": 0.0, "roughnessFactor": 0.9},
                 "doubleSided": True}
            if alpha < 1.0:
                m["alphaMode"] = "BLEND"
            doc["materials"].append(m)
            material_of[key] = len(doc["materials"]) - 1
        return material_of[key]

    for item in items:
        primitives = []
        for part in item.parts:
            pos = part.triangles.reshape(-1, 3).astype(np.float32)
            nrm = _normals(part.triangles).astype(np.float32)
            doc["accessors"].append({
                "bufferView": view(pos.tobytes(), 34962), "componentType": 5126,
                "count": len(pos), "type": "VEC3",
                "min": [float(v) for v in pos.min(axis=0)],
                "max": [float(v) for v in pos.max(axis=0)]})
            position = len(doc["accessors"]) - 1
            doc["accessors"].append({"bufferView": view(nrm.tobytes(), 34962),
                                     "componentType": 5126, "count": len(nrm),
                                     "type": "VEC3"})
            primitives.append({"attributes": {"POSITION": position,
                                              "NORMAL": len(doc["accessors"]) - 1},
                               "material": material(part.color, part.alpha), "mode": 4})
        if not primitives:
            continue
        doc["meshes"].append({"name": item.name, "primitives": primitives})
        doc["nodes"].append({"name": item.name, "mesh": len(doc["meshes"]) - 1,
                             "extras": {"GlobalId": item.gid, "ClasseIfc": item.ifc_class,
                                        "Tipo": item.type_name,
                                        "Pavimento": item.storey}})
        node = len(doc["nodes"]) - 1
        if item.storey not in storeys:
            doc["nodes"].append({"name": item.storey or "Sem pavimento", "children": []})
            storeys[item.storey] = len(doc["nodes"]) - 1
            doc["scenes"][0]["nodes"].append(storeys[item.storey])
        doc["nodes"][storeys[item.storey]]["children"].append(node)
    while len(blob) % 4:
        blob.append(0)
    doc["buffers"][0]["byteLength"] = len(blob)
    if not doc["materials"]:
        del doc["materials"]
    return doc, bytes(blob)


def write_glb(path, items: list[Item], name: str = "BrasBim") -> None:
    doc, blob = gltf(items, name)
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(blob)
    with open(path, "wb") as out:
        out.write(struct.pack("<4sII", b"glTF", 2, total))
        out.write(struct.pack("<I4s", len(text), b"JSON"))
        out.write(text)
        out.write(struct.pack("<I4s", len(blob), b"BIN\x00"))
        out.write(blob)


def read_glb(path) -> tuple[dict, bytes]:
    """JSON e buffer de um .glb (para conferir)."""
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError("GLB inválido")
    size, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        raise ValueError("GLB sem JSON")
    doc = json.loads(data[20:20 + size].decode("utf-8"))
    offset = 20 + size
    bsize, bkind = struct.unpack_from("<I4s", data, offset)
    if bkind != b"BIN\x00":
        raise ValueError("GLB sem buffer")
    return doc, data[offset + 8:offset + 8 + bsize]


# --- OBJ --------------------------------------------------------------------------------


def write_obj(path, items: list[Item]) -> Path:
    """OBJ e o MTL ao lado; devolve o caminho do MTL."""
    path = Path(path)
    mtl = path.with_suffix(".mtl")
    names: dict[tuple, str] = {}
    lines = [f"# BrasBim\nmtllib {mtl.name}\n"]
    count = 0
    for item in items:
        label = f"{item.name}_{item.gid}".replace(" ", "_")
        lines.append(f"o {label}\n")
        for part in item.parts:
            key = (part.color, part.alpha)
            if key not in names:
                names[key] = f"m{len(names) + 1}_" + "".join(
                    f"{round(c * 255):02X}" for c in part.color)
            lines.append(f"usemtl {names[key]}\n")
            pts = part.triangles.reshape(-1, 3)
            lines.append("".join(f"v {x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in pts))
            n = len(pts)
            lines.append("".join(f"f {count + i + 1} {count + i + 2} {count + i + 3}\n"
                                 for i in range(0, n, 3)))
            count += n
    path.write_text("".join(lines), encoding="utf-8")
    mtl.write_text("".join(
        f"newmtl {name}\nKd {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\nKa 0 0 0\nd {a:.4f}\n"
        f"illum 1\n\n" for (c, a), name in names.items()), encoding="utf-8")
    return mtl


# --- entrada ------------------------------------------------------------------------------


@dataclass
class Result:
    elements: int
    triangles: int

    def text(self, path: str) -> str:
        return (f"3D exportado ({self.elements} elementos, {self.triangles} triângulos): "
                f"{path}")


def export(doc: Document, path: str, visible_only: bool = True) -> Result:
    """Grava ``path`` em glTF binário (.glb) ou OBJ (.obj), pela extensão."""
    kind = Path(path).suffix.lower().lstrip(".")
    if kind not in FORMATS:
        raise OpError("use a extensão .glb ou .obj")
    items = collect(doc, visible_only)
    if not items:
        raise OpError("não há elementos 3D para exportar")
    name = Path(path).stem
    if kind == "glb":
        write_glb(path, items, name)
    else:
        write_obj(path, items)
    return Result(len(items), sum(i.triangle_count for i in items))
