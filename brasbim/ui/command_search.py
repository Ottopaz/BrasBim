# SPDX-License-Identifier: GPL-3.0-or-later
"""Busca da paleta de comandos (``spec/ui/23-precisao.md`` §9), sem Qt.

A busca ignora acento e caixa e aceita as letras na ordem com outras no meio ("pard"
acha "Parede"); começo de palavra e começo do nome valem mais. Cada ferramenta de
elemento também responde pelo nome da classe IFC e por termos usuais (sinônimos).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# ferramenta → sinônimos (classe IFC e termos usuais)
SYNONYMS = {
    "wall": ("IfcWall", "muro", "alvenaria"),
    "arc": ("IfcWall", "parede curva"),
    "rectangle": ("IfcWall", "caixa de paredes"),
    "door": ("IfcDoor", "esquadria"),
    "window": ("IfcWindow", "esquadria", "caixilho"),
    "wall_opening": ("IfcOpeningElement", "abertura", "nicho"),
    "column": ("IfcColumn", "coluna"),
    "beam": ("IfcBeam",),
    "slab": ("IfcSlab", "piso", "contrapiso"),
    "roof": ("IfcRoof", "telhado", "água"),
    "skylight": ("IfcWindow", "zenital"),
    "stair": ("IfcStair", "degrau", "lance"),
    "railing": ("IfcRailing", "corrimão", "parapeito"),
    "object": ("IfcFurnishingElement", "mobiliário", "móvel", "bloco"),
    "grid": ("IfcGrid", "malha"),
    "terrain": ("IfcGeographicElement", "topografia", "curvas de nível"),
    "space": ("IfcSpace", "cômodo", "sala", "área"),
    "dimension": ("IfcAnnotation", "medida", "dimensão"),
    "text": ("IfcAnnotation", "escrever"),
    "line2d": ("IfcAnnotation", "traço", "desenho 2D"),
    "hatch": ("IfcAnnotation", "preenchimento"),
    "section": ("corte vertical",),
    "elevation": ("vista", "elevação"),
    "offset": ("paralela", "equidistante"),
    "trim": ("cortar", "prolongar", "alongar"),
    "fillet": ("canto", "arredondar", "raio"),
}


@dataclass(frozen=True)
class Command:
    key: str  # identificador único (nome da ferramenta ou do menu)
    label: str
    where: str = ""  # menu ou grupo de onde vem
    shortcut: str = ""
    words: tuple[str, ...] = field(default=())  # sinônimos


def normalize(text: str) -> str:
    """Sem acento, minúsculo, sem reticências."""
    text = unicodedata.normalize("NFKD", text.replace("…", ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def _score(query: str, target: str) -> float | None:
    """Pontos da busca em ``target`` (None: as letras não aparecem na ordem)."""
    if not query:
        return 0.0
    if target.startswith(query):
        return 100.0 - len(target) * 0.01
    pos = target.find(query)
    if pos >= 0:
        start = pos == 0 or not target[pos - 1].isalnum()
        return (80.0 if start else 60.0) - pos * 0.1
    i, gaps, first, starts = 0, 0, None, 0
    for k, c in enumerate(target):
        if i < len(query) and c == query[i]:
            if first is None:
                first = k
            if k == 0 or not target[k - 1].isalnum():
                starts += 1
            i += 1
        elif first is not None and i < len(query):
            gaps += 1
    if i < len(query):
        return None
    return 40.0 + 3 * starts - gaps * 0.5 - (first or 0) * 0.2


def score(query: str, command: Command) -> float | None:
    q = normalize(query)
    found = [_score(q, normalize(command.label))]
    found += [None if s is None else s - 5 for s in
              (_score(q, normalize(w)) for w in command.words)]
    found = [s for s in found if s is not None]
    return max(found) if found else None


def search(query: str, commands: list[Command], recent: list[str] = ()) -> list[Command]:
    """Comandos que atendem à busca, os melhores primeiro; com a busca vazia, os
    recentes primeiro e depois a ordem original."""
    if not query.strip():
        rank = {key: i for i, key in enumerate(recent)}
        return sorted(commands, key=lambda c: rank.get(c.key, len(rank)))
    scored = [(s, i, c) for i, c in enumerate(commands)
              if (s := score(query, c)) is not None]
    recent_bonus = set(recent)
    return [c for s, _, c in sorted(scored, key=lambda t: (
        -(t[0] + (2 if t[2].key in recent_bonus else 0)), t[1]))]
