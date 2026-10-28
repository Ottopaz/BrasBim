# SPDX-License-Identifier: LGPL-3.0-or-later
"""Muitas polilinhas em arrays (desenho importado de DWG/DXF, ``spec/ui/22`` §7), sem Qt.

Um DWG de arquitetura traz centenas de milhares de linhas: como objetos Python (uma
entidade IFC, uma forma de escolha e um segmento de atração por linha) ficam lentos. Aqui
elas são arrays numpy:

- ``coords`` (N, 2) em metros, ``starts`` (n + 1) com o início de cada linha em
  ``coords``, ``closed`` (n) e ``z`` (n, ``nan`` = sem cota constante);
- ``pack``/``unpack``: texto compacto para guardar no IFC e nas operações, com as
  coordenadas quantizadas a 0,01 mm, em diferenças sucessivas e comprimidas;
- ``segments``, ``corners``, ``near`` (busca vetorizada) e ``mapped`` (transformação).
"""

from __future__ import annotations

import base64
import io
import math

import numpy as np

QUANTUM = 1e-5  # m: 0,01 mm
CORNER_DEG = 12.0  # como snap.CORNER_DEG: vértice de curva aproximada não é canto


class Lines:
    def __init__(self, coords, starts, closed, z):
        self.coords = np.asarray(coords, dtype=float).reshape(-1, 2)
        self.starts = np.asarray(starts, dtype=np.int64)
        self.closed = np.asarray(closed, dtype=bool)
        self.z = np.asarray(z, dtype=float)
        self._segments = None
        self._corners = None

    def __len__(self) -> int:
        return len(self.closed)

    # --- conversão ----------------------------------------------------------------------

    @classmethod
    def from_dicts(cls, lines) -> Lines:
        """De ``[{"points": [[x, y], ...], "closed": bool, "z": float | None}, ...]``."""
        lengths = [len(line["points"]) for line in lines]
        coords = [p[:2] for line in lines for p in line["points"]]
        return cls(np.array(coords, dtype=float).reshape(-1, 2),
                   np.concatenate([[0], np.cumsum(lengths, dtype=np.int64)]),
                   [bool(line["closed"]) for line in lines],
                   [math.nan if line.get("z") is None else float(line["z"]) for line in lines])

    def line(self, i: int) -> dict:
        pts = self.coords[self.starts[i]:self.starts[i + 1]]
        z = self.z[i]
        return {"points": pts.tolist(), "closed": bool(self.closed[i]),
                "z": None if math.isnan(z) else float(z)}

    def to_dicts(self) -> list[dict]:
        return [self.line(i) for i in range(len(self))]

    def polylines(self):
        """``(pontos (k, 2), fechada)`` de cada linha, sem copiar."""
        for i in range(len(self)):
            yield self.coords[self.starts[i]:self.starts[i + 1]], bool(self.closed[i])

    def pack(self) -> str:
        q = np.round(self.coords / QUANTUM).astype(np.int64)
        deltas = np.diff(q, axis=0, prepend=np.zeros((1, 2), dtype=np.int64))
        buffer = io.BytesIO()
        np.savez_compressed(buffer, d=deltas, n=np.diff(self.starts).astype(np.int64),
                            c=self.closed.astype(np.uint8), z=self.z)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @classmethod
    def unpack(cls, text: str) -> Lines:
        with np.load(io.BytesIO(base64.b64decode(text))) as data:
            coords = np.round(np.cumsum(data["d"], axis=0) * QUANTUM, 5)
            starts = np.concatenate([[0], np.cumsum(data["n"])])
            return cls(coords, starts, data["c"].astype(bool), data["z"])

    def bounds(self) -> tuple[float, float, float, float] | None:
        if not len(self.coords):
            return None
        lo, hi = self.coords.min(axis=0), self.coords.max(axis=0)
        return float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])

    # --- geometria ----------------------------------------------------------------------

    def segments(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """``(a, b, linha, reta)``: pontas de cada trecho, a linha dele e se é aresta de
        verdade (as duas pontas são cantos)."""
        if self._segments is None:
            n = len(self.coords)
            line_of = np.repeat(np.arange(len(self)), np.diff(self.starts))
            inner = np.ones(max(n - 1, 0), dtype=bool)
            ends = self.starts[1:-1] - 1  # último ponto de cada linha, menos a última
            inner[ends[(ends >= 0) & (ends < n - 1)]] = False
            i = np.nonzero(inner)[0]
            j = i + 1
            shut = np.nonzero(self.closed & (np.diff(self.starts) > 2))[0]
            i = np.concatenate([i, self.starts[shut + 1] - 1])
            j = np.concatenate([j, self.starts[shut]])
            corner = self.corners()[1]
            self._segments = (self.coords[i], self.coords[j], line_of[i],
                              corner[i] & corner[j])
        return self._segments

    def corners(self) -> tuple[np.ndarray, np.ndarray]:
        """``(pontos, canto)``: os vértices que atraem como extremidade (pontas das
        abertas e desvio de ao menos ``CORNER_DEG``) e a marca de cada vértice."""
        if self._corners is None:
            n = len(self.coords)
            counts = np.diff(self.starts)
            line_of = np.repeat(np.arange(len(self)), counts)
            first = self.starts[:-1][line_of]
            last = self.starts[1:][line_of] - 1
            idx = np.arange(n)
            closed = self.closed[line_of] & (counts[line_of] > 2)
            prev = np.where(idx == first, np.where(closed, last, -1), idx - 1)
            nxt = np.where(idx == last, np.where(closed, first, -1), idx + 1)
            corner = (prev < 0) | (nxt < 0)
            mid = ~corner
            if mid.any():
                p, q, r = self.coords[prev[mid]], self.coords[mid], self.coords[nxt[mid]]
                a1 = np.arctan2(q[:, 1] - p[:, 1], q[:, 0] - p[:, 0])
                a2 = np.arctan2(r[:, 1] - q[:, 1], r[:, 0] - q[:, 0])
                turn = np.abs(np.degrees((a2 - a1 + np.pi) % (2 * np.pi) - np.pi))
                corner[mid] = turn >= CORNER_DEG
            self._corners = (self.coords[corner], corner)
        return self._corners

    def near(self, p, r: float) -> tuple[np.ndarray, np.ndarray]:
        """``(trechos, distâncias)`` a até ``r`` de ``p``: índices em ``segments``."""
        a, b, _, _ = self.segments()
        if not len(a):
            return np.empty(0, dtype=np.int64), np.empty(0)
        px, py = float(p[0]), float(p[1])
        box = ((np.minimum(a[:, 0], b[:, 0]) <= px + r) & (np.maximum(a[:, 0], b[:, 0]) >= px - r)
               & (np.minimum(a[:, 1], b[:, 1]) <= py + r)
               & (np.maximum(a[:, 1], b[:, 1]) >= py - r))
        k = np.nonzero(box)[0]
        if not len(k):
            return k, np.empty(0)
        d = distances((px, py), a[k], b[k])
        keep = d <= r
        return k[keep], d[keep]

    def mapped(self, fn) -> Lines:
        """Linhas levadas por ``fn`` (ponto → ponto). As transformações da planta são
        afins (mover, girar, espelhar, escalar): descobre-se a matriz por três pontos e
        confere-se num quarto; se não for afim, ponto a ponto."""
        x0, y0, x1, y1 = self.bounds() or (0.0, 0.0, 1.0, 1.0)
        w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
        base = np.array([(x0, y0), (x0 + w, y0), (x0, y0 + h)])
        img = np.array([fn((float(x), float(y))) for x, y in base], dtype=float)
        ux, uy = (img[1] - img[0]) / w, (img[2] - img[0]) / h
        matrix = np.column_stack([ux, uy])

        def affine(pts):
            return (pts - base[0]) @ matrix.T + img[0]

        probe = np.array([[x0 + 0.37 * w, y0 + 0.61 * h]])
        if np.allclose(affine(probe)[0], fn(tuple(probe[0])), atol=1e-9):
            coords = affine(self.coords)
        else:
            coords = np.array([fn((float(x), float(y))) for x, y in self.coords], dtype=float)
        return Lines(coords, self.starts, self.closed, self.z)


def distances(p, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distância de ``p`` a cada trecho ``a[i]``–``b[i]``."""
    d = b - a
    n = (d * d).sum(axis=1)
    t = np.where(n > 1e-18, ((p[0] - a[:, 0]) * d[:, 0] + (p[1] - a[:, 1]) * d[:, 1])
                 / np.where(n > 1e-18, n, 1.0), 0.0)
    t = np.clip(t, 0.0, 1.0)
    return np.hypot(p[0] - a[:, 0] - t * d[:, 0], p[1] - a[:, 1] - t * d[:, 1])
