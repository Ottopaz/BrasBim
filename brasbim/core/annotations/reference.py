# SPDX-License-Identifier: LGPL-3.0-or-later
"""Desenho importado (DXF/DWG) como referência 2D na planta
(``spec/ui/22-importar-desenho.md`` §3 e §7).

Uma anotação por camada do arquivo de origem, com as linhas já em metros e no sistema do
pavimento. **Só linhas de referência:** a anotação não ganha geometria IFC; as linhas
ficam compactadas nos parâmetros (``linework.Lines.pack``), para importar, desenhar e
salvar depressa mesmo com centenas de milhares de linhas::

    {"name": "Levantamento – CURVAS", "source": "topo.dwg", "layer": "CURVAS",
     "packed": "<linhas compactadas>", "count": 3,
     "texts": [{"at": [x, y], "text": "101,50", "height": 0.25, "angle": 0.0}, ...],
     "points": [{"at": [x, y], "z": 101.5 | null}, ...]}

``z`` é a cota que a linha (ou o ponto) trazia no arquivo, quando constante: as curvas
de nível de um levantamento costumam vir com ela (§4). Arquivos de antes guardavam
``"lines": [{"points", "closed", "z"}, ...]``: continuam sendo lidos (``lines_of``).
"""

from __future__ import annotations

from brasbim.core.annotations import base
from brasbim.core.annotations.prims import Prims, Stroke, Text
from brasbim.core.document import OpError
from brasbim.core.linework import Lines

WEIGHT = 0.13  # mm: traço fino da referência
CROSS = 1.0  # mm de papel: meia cruz do ponto

# Linhas já abertas, pelo texto compactado (o mesmo texto vem de novo a cada leitura).
_opened: dict[str, Lines] = {}


def pack_lines(lines) -> dict:
    """Campos ``packed`` e ``count`` a partir de ``Lines`` ou de dicionários."""
    found = lines if isinstance(lines, Lines) else Lines.from_dicts(lines)
    text = found.pack()
    _opened[text] = found
    return {"packed": text, "count": len(found)}


def lines_of(state) -> Lines:
    """As linhas da anotação (do texto compactado ou do formato antigo)."""
    if "lines" in state and not state.get("packed"):
        return Lines.from_dicts(state["lines"])
    text = state.get("packed") or ""
    if not text:
        return Lines.from_dicts([])
    found = _opened.get(text)
    if found is None:
        if len(_opened) > 64:
            _opened.clear()
        found = _opened[text] = Lines.unpack(text)
    return found


def _validate(state) -> None:
    try:
        found = lines_of(state)
    except (ValueError, OSError, KeyError) as e:
        raise OpError(f"linhas do desenho importado ilegíveis: {e}") from e
    import numpy as np

    if len(found) and (np.diff(found.starts) < 2).any():
        raise OpError("linha do desenho importado com menos de 2 pontos")


def _build(doc, storey, state) -> Prims:
    from brasbim.core import storeys

    out = Prims()
    lines = lines_of(state)
    if len(lines):
        out.bulk.append((lines, WEIGHT))
    for t in state["texts"]:
        out.texts.append(Text(tuple(t["at"]), t["text"], t["height"], t["angle"], "left",
                              "bottom"))
    k = storeys.paper(storey, CROSS)
    for p in state["points"]:
        x, y = p["at"]
        out.strokes += [Stroke(((x - k, y), (x + k, y)), False, WEIGHT),
                        Stroke(((x, y - k), (x, y + k)), False, WEIGHT)]
    return out


def _mapped(state, fn, turn, mirrored, moving) -> dict:
    def m(p):
        q = fn(tuple(p))
        return [float(q[0]), float(q[1])]

    out = {
        **pack_lines(lines_of(state).mapped(fn)),
        "texts": [{**t, "at": m(t["at"]),
                   "angle": (-t["angle"] + turn) % 360.0 if mirrored
                   else (t["angle"] + turn) % 360.0} for t in state["texts"]],
        "points": [{**p, "at": m(p["at"])} for p in state["points"]],
    }
    if "lines" in state:  # formato antigo: passa para o compactado
        out["lines"] = None
    return out


REFERENCE = base.Kind("reference2d", "desenho importado", None, "DesenhoImportado",
                      {"name": "Desenho importado", "source": "", "layer": "",
                       "packed": "", "count": 0, "texts": [], "points": []},
                      _build, _mapped, validate=_validate, geometry=False)
base.register_kind(REFERENCE)


def is_reference(element) -> bool:
    kind = base.kind_of(element)
    return kind is not None and kind.prefix == "reference2d"


def lines_near(owners, p, tol: float) -> list[tuple[float, str, int, dict]]:
    """Linhas de desenho importado perto de ``p``, da mais próxima: (distância,
    GlobalId, índice, linha). ``owners``: [(GlobalId, estado)]."""
    out = []
    for gid, state in owners:
        lines = lines_of(state)
        found, dist = lines.near(p, tol)
        if not len(found):
            continue
        which = lines.segments()[2][found]
        best: dict[int, float] = {}
        for i, d in zip(which.tolist(), dist.tolist(), strict=True):
            best[i] = min(d, best.get(i, d))
        out += [(d, gid, i, lines.line(i)) for i, d in best.items()]
    return sorted(out, key=lambda e: e[0])
