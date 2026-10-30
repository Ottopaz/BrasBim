# SPDX-License-Identifier: LGPL-3.0-or-later
"""Seções de pilar e viga e ponto de inserção (``pilar.md`` §2.2, §3.1; ``viga.md`` §2.4).

Seção::

    {"shape": "rect", "b": 0.20, "h": 0.40}   # IfcRectangleProfileDef (XDim, YDim)
    {"shape": "circle", "d": 0.30}            # IfcCircleProfileDef (Radius = d/2)
    {"shape": "custom", "profile": "<id>", "b": 0.20, "h": 0.40}   # perfil do projeto

No perfil do projeto (spec/ui 41 §4), ``b`` e ``h`` são a largura e a altura nominais; a
seção lida do tipo traz também ``name`` e ``parts`` (as partes já esticadas, como em
``profile_defs``). A origem do desenho é o ponto de inserção: o ``CardinalPoint`` não
desloca a seção.

O ponto de inserção é o ``CardinalPoint`` do IFC (1–9). Olhando na direção da extrusão,
a "esquerda" é o +x do perfil e o "topo" é o +y [IFC-CARD]. Visto de cima, num pilar
(extrudado para cima), a esquerda do IFC fica à direita no desenho: o canto inferior
esquerdo da planta é o ``CardinalPoint`` 3 (``PLAN_CARDINAL``).
"""

from __future__ import annotations

import math

MIN_SIZE = 0.01  # m (pilar.md §3.2, viga.md §3.2)
SHAPES = ("rect", "circle")
CUSTOM = "custom"

# Posição do quadradinho de 9 pontos (coluna, linha a partir de baixo, como na planta
# vista de cima) → CardinalPoint.
PLAN_CARDINAL = {(col, row): 3 * row + (2 - col) + 1 for col in range(3) for row in range(3)}


def validate(section: dict, shapes=SHAPES) -> None:
    shape = section.get("shape")
    if shape not in shapes:
        raise ValueError(f"seção inválida: {shape!r}")
    if shape == CUSTOM and not section.get("profile"):
        raise ValueError("seção sem perfil")
    sizes = (section["d"],) if shape == "circle" else (section["b"], section["h"])
    if any(s <= MIN_SIZE for s in sizes):
        raise ValueError(f"as dimensões da seção devem passar de {MIN_SIZE:.2f} m")


def size(section: dict) -> tuple[float, float]:
    """(largura em x, altura em y) da caixa da seção."""
    if section["shape"] == "circle":
        return section["d"], section["d"]
    return section["b"], section["h"]


def _parts(section: dict) -> list[dict]:
    parts = section.get("parts")
    if not parts:
        raise ValueError("seção de perfil sem as partes (leia pelo tipo)")
    return parts


def area(section: dict) -> float:
    if section["shape"] == CUSTOM:
        from brasbim.core import profile_defs

        return profile_defs.area(_parts(section))
    if section["shape"] == "circle":
        return math.pi * section["d"] ** 2 / 4
    return section["b"] * section["h"]


def perimeter(section: dict) -> float:
    if section["shape"] == CUSTOM:
        from brasbim.core import profile_defs

        return float(profile_defs.union(_parts(section)).length)
    if section["shape"] == "circle":
        return math.pi * section["d"]
    return 2 * (section["b"] + section["h"])


def insertion(section: dict, cardinal: int) -> tuple[float, float]:
    """Ponto de inserção nas coordenadas do perfil (centro da caixa na origem)."""
    if not 1 <= cardinal <= 9:
        raise ValueError(f"ponto de inserção inválido: {cardinal}")
    if section["shape"] == CUSTOM:
        return 0.0, 0.0
    w, h = size(section)
    col, row = (cardinal - 1) % 3, (cardinal - 1) // 3
    return ((0.5, 0.0, -0.5)[col] * w, (-0.5, 0.0, 0.5)[row] * h)


def mirrored_cardinal(cardinal: int) -> int:
    """``CardinalPoint`` que mantém o mesmo canto da seção depois de um espelho (o eixo y
    local se inverte)."""
    col, row = (cardinal - 1) % 3, (cardinal - 1) // 3
    return 3 * (2 - row) + col + 1


def extent(section: dict, cardinal: int) -> tuple[float, float, float, float]:
    """(xmin, xmax, ymin, ymax) da seção em relação ao ponto de inserção."""
    ix, iy = insertion(section, cardinal)
    if section["shape"] == CUSTOM:
        from brasbim.core import profile_defs

        x0, y0, x1, y1 = profile_defs.bounds(_parts(section))
    else:
        w, h = size(section)
        x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
    return x0 - ix, x1 - ix, y0 - iy, y1 - iy


def outline(section: dict, steps: int = 32) -> list[tuple[float, float]]:
    """Contorno da seção nas coordenadas do perfil, anti-horário. No perfil do projeto,
    o contorno de todas as partes juntas (partes soltas: a envoltória convexa)."""
    if section["shape"] == CUSTOM:
        from shapely.geometry import polygon as shapely_polygon

        from brasbim.core import profile_defs

        shape = profile_defs.union(_parts(section))
        if shape.geom_type != "Polygon":
            shape = shape.convex_hull
        ring = shapely_polygon.orient(shape, 1.0).exterior.coords[:-1]
        return [(float(x), float(y)) for x, y in ring]
    if section["shape"] == "circle":
        r = section["d"] / 2
        return [(r * math.cos(2 * math.pi * k / steps), r * math.sin(2 * math.pi * k / steps))
                for k in range(steps)]
    b, h = section["b"] / 2, section["h"] / 2
    return [(-b, -h), (b, -h), (b, h), (-b, h)]


def label(section: dict) -> str:
    """Seção em centímetros: "20 × 40" ou "Ø 30"."""
    def cm(v):
        return f"{v * 100:.1f}".rstrip("0").rstrip(".").replace(".", ",")

    if section["shape"] == CUSTOM:
        return section.get("name") or "perfil"
    if section["shape"] == "circle":
        return f"Ø {cm(section['d'])}"
    return f"{cm(section['b'])} × {cm(section['h'])}"


# --- IFC -------------------------------------------------------------------------------


def create(ifc, section: dict, name: str | None = None):
    if section["shape"] == "circle":
        return ifc.createIfcCircleProfileDef("AREA", name, None, float(section["d"]) / 2)
    return ifc.createIfcRectangleProfileDef("AREA", name, None, float(section["b"]),
                                            float(section["h"]))


def read(profile) -> dict | None:
    if profile is None:
        return None
    if profile.is_a("IfcCircleProfileDef"):
        return {"shape": "circle", "d": round(float(profile.Radius) * 2, 9)}
    if profile.is_a("IfcRectangleProfileDef"):
        return {"shape": "rect", "b": float(profile.XDim), "h": float(profile.YDim)}
    return None


def update(profile, section: dict) -> bool:
    """Muda as dimensões no próprio perfil; ``False`` se a forma mudou (perfil novo).
    O perfil do projeto é gravado por ``types`` (várias partes)."""
    if section["shape"] == "circle" and profile.is_a("IfcCircleProfileDef"):
        profile.Radius = float(section["d"]) / 2
        return True
    if section["shape"] == "rect" and profile.is_a("IfcRectangleProfileDef"):
        profile.XDim, profile.YDim = float(section["b"]), float(section["h"])
        return True
    return False
