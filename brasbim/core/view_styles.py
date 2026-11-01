# SPDX-License-Identifier: LGPL-3.0-or-later
"""Estilos de apresentação da vista 3D (``spec/ui/43-estilos-3d-e-espessura-livre.md``
§2), sem Qt: um conjunto com nome de escolhas para as faces, a luz e as arestas.

Escolhas de cada estilo:

- ``faces``: ``material`` (cor do material), ``single`` (uma cor só, ``face_color``),
  ``background`` (cor do fundo: aparência de linhas ocultas) ou ``none`` (sem faces);
- ``light``: sombreado pela direção da luz (verdadeiro) ou chapado;
- ``edges``: ``contour`` (arestas vivas, bordas e silhuetas), ``all`` (todas, inclusive as
  emendas e as de trás das faces, se não há faces) ou ``none``;
- ``edge_width`` (px) e ``edge_color``.
"""

from __future__ import annotations

FACES = ("material", "single", "background", "none")
EDGES = ("contour", "all", "none")

_BASE = {"faces": "material", "face_color": "#F4F2EC", "light": True, "edges": "contour",
         "edge_width": 1.0, "edge_color": "#404040"}

# Estilos de fábrica (§2.2), na ordem da lista
FACTORY = [
    {"id": "colorido", "name": "Colorido"},
    {"id": "colorido_sem_linhas", "name": "Colorido sem linhas", "edges": "none"},
    {"id": "maquete_branca", "name": "Maquete branca", "faces": "single",
     "edge_color": "#6E6E6E"},
    {"id": "maquete_branca_sem_linhas", "name": "Maquete branca sem linhas",
     "faces": "single", "edges": "none"},
    {"id": "desenho", "name": "Desenho", "faces": "background", "light": False,
     "edge_width": 1.5, "edge_color": "#1E1E1E"},
    {"id": "arame", "name": "Arame", "faces": "none", "edges": "all",
     "edge_color": "#3A3A3A"},
]
FACTORY = [{**_BASE, **s} for s in FACTORY]
DEFAULT = "colorido"


def factory_ids() -> list[str]:
    return [s["id"] for s in FACTORY]


def get(style_id: str | None) -> dict:
    """Estilo pelo id; um id desconhecido (ou ``None``) dá o padrão."""
    return dict(next((s for s in FACTORY if s["id"] == style_id),
                     next(s for s in FACTORY if s["id"] == DEFAULT)))


def name_of(style_id: str | None) -> str:
    return get(style_id)["name"]


def rgb(color: str) -> tuple[float, float, float]:
    """"#RRGGBB" → (r, g, b) de 0 a 1."""
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
