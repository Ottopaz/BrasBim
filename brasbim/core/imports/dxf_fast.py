# SPDX-License-Identifier: LGPL-3.0-or-later
"""Leitor rápido de DXF só para o desenho de referência (``spec/ui/22`` §7), sem Qt.

O ezdxf monta um objeto completo por entidade: um DWG de arquitetura com 170 mil linhas
leva dezenas de segundos. Aqui as tags do DXF (formato com especificação pública, *DXF
Reference*) são lidas direto e só se guarda a geometria que a referência usa: LINE,
LWPOLYLINE, POLYLINE (2D e 3D), ARC, CIRCLE, ELLIPSE, SPLINE, TEXT, MTEXT e POINT, com
INSERT e DIMENSION explodidos (o que está na camada "0" dentro de um bloco fica na
camada da inserção). Curvas viram polilinhas com desvio máximo ``chord`` (unidades do
arquivo). Entidades em espaço de papel ficam de fora.

Qualquer coisa fora do previsto levanta ``Unsupported``: quem chama volta ao ezdxf.
"""

from __future__ import annotations

import itertools
import math
import re

import numpy as np

UNITS_CODE = {4: "mm", 5: "cm", 6: "m"}
_MAX_DEPTH = 16
_MIN_SEGMENTS = 4
_MAX_SEGMENTS = 720


class Unsupported(Exception):
    """Arquivo que este leitor não trata (binário, estrutura inesperada)."""


# --- tags ----------------------------------------------------------------------------------


def _tags(data: bytes):
    if data.startswith(b"AutoCAD Binary DXF"):
        raise Unsupported("DXF binário")
    text = data.decode("utf-8", "surrogateescape")
    lines = text.splitlines()
    if len(lines) % 2:
        lines = lines[:-1]
    try:
        codes = [int(c) for c in lines[0::2]]
    except ValueError as e:
        raise Unsupported(f"código de grupo inválido: {e}") from e
    return codes, lines[1::2]


def _groups(codes, values):
    """Entidades: listas de (código, valor) que começam no código 0."""
    starts = np.flatnonzero(np.asarray(codes) == 0).tolist() + [len(codes)]
    for a, b in itertools.pairwise(starts):
        yield list(zip(codes[a:b], values[a:b], strict=True))


class _E:
    """Uma entidade: tipo e tags (os valores repetidos ficam em lista)."""

    __slots__ = ("cache", "first", "kind", "tags")

    def __init__(self, tags):
        self.kind = tags[0][1].strip()
        self.tags = tags
        self.cache = None  # curva já avaliada (entidade de bloco inserido várias vezes)
        self.first = {}
        for c, v in reversed(tags):  # o primeiro de cada código
            self.first[c] = v

    def get(self, code, default=None):
        return self.first.get(code, default)

    def f(self, code, default=0.0) -> float:
        v = self.get(code)
        return default if v is None else float(v)

    def i(self, code, default=0) -> int:
        v = self.get(code)
        return default if v is None else int(v)

    def text(self, code, default="") -> str:
        v = self.get(code)
        return default if v is None else v

    def all(self, code) -> list[str]:
        return [v for c, v in self.tags if c == code]


# --- geometria ----------------------------------------------------------------------------


def _ocs(entity: _E):
    """Matriz 3×3 do sistema do objeto (OCS) para o do desenho, ou None (identidade)."""
    if entity.get(210) is None and entity.get(220) is None:
        return None
    n = np.array([entity.f(210, 0.0), entity.f(220, 0.0), entity.f(230, 1.0)])
    length = np.linalg.norm(n)
    if length < 1e-12:
        return None
    n = n / length
    if abs(n[0]) < 1e-12 and abs(n[1]) < 1e-12 and n[2] > 0:
        return None
    if abs(n[0]) < 1 / 64 and abs(n[1]) < 1 / 64:
        ax = np.cross([0.0, 1.0, 0.0], n)
    else:
        ax = np.cross([0.0, 0.0, 1.0], n)
    ax = ax / np.linalg.norm(ax)
    ay = np.cross(n, ax)
    return np.column_stack([ax, ay, n])


def _wcs(pts, m):
    pts = np.asarray(pts, dtype=float)
    return pts if m is None else pts @ m.T


def _steps(radius: float, sweep: float, chord: float) -> int:
    if radius <= 0:
        return _MIN_SEGMENTS
    c = min(chord / radius, 1.0)
    step = 2 * math.acos(1 - c) if c < 1 else math.pi / 2
    n = math.ceil(abs(sweep) / max(step, 1e-6))
    return max(_MIN_SEGMENTS, min(n, _MAX_SEGMENTS))


def _arc(cx, cy, r, a0, a1, chord):
    """Pontos do arco de ``a0`` a ``a1`` (radianos, anti-horário)."""
    sweep = (a1 - a0) % (2 * math.pi) or 2 * math.pi
    n = _steps(r, sweep, chord)
    t = a0 + np.linspace(0.0, sweep, n + 1)
    return np.column_stack([cx + r * np.cos(t), cy + r * np.sin(t)])


def _bulged(pts, bulges, closed, chord):
    """Polilinha com arcos (``bulge`` = tangente de um quarto do ângulo)."""
    if not any(abs(b) > 1e-12 for b in bulges):
        return np.asarray(pts, dtype=float)
    out = []
    n = len(pts)
    for k in range(n if closed else n - 1):
        p, q, b = pts[k], pts[(k + 1) % n], bulges[k]
        if abs(b) < 1e-12:
            out.append(p)
            continue
        dx, dy = q[0] - p[0], q[1] - p[1]
        d = math.hypot(dx, dy)
        if d < 1e-12:
            continue
        angle = 4 * math.atan(b)
        r = d / (2 * math.sin(angle / 2))
        h = r * math.cos(angle / 2)  # do meio da corda ao centro
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        cx, cy = mx - h * dy / d, my + h * dx / d
        a0 = math.atan2(p[1] - cy, p[0] - cx)
        sweep = angle
        steps = _steps(abs(r), abs(sweep), chord)
        t = a0 + np.linspace(0.0, sweep, steps + 1)[:-1]
        out += np.column_stack([cx + abs(r) * np.cos(t), cy + abs(r) * np.sin(t)]).tolist()
    if not closed:
        out.append(pts[-1])
    return np.asarray(out, dtype=float)


def _spline(entity: _E, chord: float):
    """Pontos da SPLINE pela matemática de B-spline do ezdxf (poucas entidades: o custo
    não pesa), pelos pontos de controle ou, sem eles, pelos de passagem."""
    from ezdxf.math import BSpline, Vec3, fit_points_to_cad_cv

    def points(cx, cy, cz):
        xs, ys, zs = entity.all(cx), entity.all(cy), entity.all(cz)
        zs = zs + ["0"] * (len(xs) - len(zs))
        return [Vec3(float(x), float(y), float(z)) for x, y, z in zip(xs, ys, zs, strict=False)]

    degree = entity.i(71, 3)
    ctrl = points(10, 20, 30)
    knots = [float(v) for v in entity.all(40)]
    weights = [float(v) for v in entity.all(41)]
    if len(ctrl) > degree and len(knots) == len(ctrl) + degree + 1:
        try:
            return _bspline(np.array([tuple(v) for v in ctrl]), np.array(knots), degree,
                            np.array(weights) if len(weights) == len(ctrl) else None,
                            chord=chord)
        except (ValueError, FloatingPointError):
            curve = BSpline(ctrl, order=degree + 1, knots=knots,
                            weights=weights if len(weights) == len(ctrl) else None)
    else:
        fit = points(11, 21, 31)
        if len(fit) < 2:
            if len(ctrl) >= 2:
                return np.array([tuple(v) for v in ctrl])
            raise Unsupported("SPLINE sem pontos")
        start = Vec3(entity.f(12), entity.f(22), entity.f(32)) if entity.get(12) else None
        end = Vec3(entity.f(13), entity.f(23), entity.f(33)) if entity.get(13) else None
        curve = fit_points_to_cad_cv(fit, tangents=[start, end] if start and end else None)
    return np.array([tuple(v) for v in curve.flattening(chord)])


def _bspline(ctrl, u, degree, weights=None, samples=None, chord=None):
    """Pontos da B-spline (racional, se ``weights``) pelas funções de base de Cox–de Boor,
    calculadas para todas as amostras de uma vez."""
    n = len(ctrl)
    lo, hi = u[degree], u[n]
    if not hi > lo:
        raise ValueError("nós degenerados")
    if samples is None:  # pelo tamanho do polígono de controle e a tolerância
        length = float(np.linalg.norm(np.diff(ctrl[:, :2], axis=0), axis=1).sum())
        per_span = 1 if degree == 1 else             max(2, min(32, math.ceil(0.5 * math.sqrt(length / max(chord or length, 1e-12)))))
        samples = 1 + per_span * (n - degree)
    count = samples
    t = np.linspace(lo, hi, count)
    basis = ((u[:-1] <= t[:, None]) & (t[:, None] < u[1:])).astype(float)
    last = int(np.nonzero(u[:-1] < hi)[0].max())  # o fim fecha no último trecho
    basis[t >= hi, :] = 0.0
    basis[t >= hi, last] = 1.0
    for p in range(1, degree + 1):
        dl = u[p:-1] - u[:-p - 1]
        dr = u[p + 1:] - u[1:-p]
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(dl > 0, (t[:, None] - u[:-p - 1]) / dl, 0.0) * basis[:, :-1]
            b = np.where(dr > 0, (u[p + 1:] - t[:, None]) / dr, 0.0) * basis[:, 1:]
        basis = a + b
    basis = basis[:, :n]
    if weights is None:
        return basis @ ctrl
    wb = basis * weights
    return (wb @ ctrl) / wb.sum(axis=1)[:, None]


_MTEXT_CODES = re.compile(r"\\[ACFHQTWfhpcqtw][^;]*;|\\[LlOoKk]|[{}]")


def _mtext(value: str) -> str:
    value = value.replace("\\P", "\n").replace("\\~", " ").replace("\\\\", "\x00")
    value = re.sub(r"\\S([^^/#;]*)[\^/#]([^;]*);", r"\1/\2", value)
    value = _MTEXT_CODES.sub("", value)
    value = value.replace("\\{", "{").replace("\\}", "}").replace("\x00", "\\")
    return value


def _special(value: str) -> str:
    for code, char in (("%%c", "Ø"), ("%%C", "Ø"), ("%%d", "°"), ("%%D", "°"),
                       ("%%p", "±"), ("%%P", "±"), ("%%%", "%")):
        value = value.replace(code, char)
    return value


# --- leitura -------------------------------------------------------------------------------


class _Reader:
    def __init__(self, chord: float):
        self.chord = chord
        self.blocks: dict[str, tuple[tuple[float, float, float], list[_E]]] = {}
        self.layers: dict[str, dict] = {}

    def layer(self, name: str) -> dict:
        return self.layers.setdefault(name, {"lines": [], "texts": [], "points": []})

    # Transformação da inserção: (matriz 2×2, deslocamento, escala z, deslocamento z,
    # giro em graus, espelhada).
    IDENTITY = (np.eye(2), np.zeros(2), 1.0, 0.0, 0.0, False)

    def add_line(self, pts3, closed, layer, xf):
        """``pts3``: [(x, y, z), ...] (lista ou array), no sistema do bloco."""
        if hasattr(pts3, "tolist"):
            pts3 = pts3.tolist()
        if len(pts3) < 2:
            return
        m, off, sz, oz, _, _ = xf
        (a, b), (c, d) = m.tolist() if hasattr(m, "tolist") else m
        ox, oy = float(off[0]), float(off[1])
        xy, zs = [], []
        for x, y, z in pts3:
            q = [a * x + b * y + ox, c * x + d * y + oy]
            if xy and abs(q[0] - xy[-1][0]) < 1e-9 and abs(q[1] - xy[-1][1]) < 1e-9:
                continue
            xy.append(q)
            zs.append(z * sz + oz)
        if closed and len(xy) > 2 and abs(xy[0][0] - xy[-1][0]) < 1e-9                 and abs(xy[0][1] - xy[-1][1]) < 1e-9:
            xy.pop()
            zs.pop()
        if len(xy) < 2:
            return
        constant = float(zs[0]) if max(zs) - min(zs) < 1e-6 else None
        self.layer(layer)["lines"].append({"points": xy, "closed": bool(closed and len(xy) > 2),
                                           "z": constant})

    def entity(self, e: _E, layer_parent, xf, depth, polyline=None):
        kind = e.kind
        layer = e.text(8, "0").strip() or "0"
        if layer_parent is not None and layer == "0":
            layer = layer_parent
        chord = self.chord
        if kind == "LINE":
            pts = [(e.f(10), e.f(20), e.f(30)), (e.f(11), e.f(21), e.f(31))]
            self.add_line(pts, False, layer, xf)
        elif kind in ("CIRCLE", "ARC"):
            r = e.f(40)
            if kind == "CIRCLE":
                xy = _arc(e.f(10), e.f(20), r, 0.0, 2 * math.pi, chord)[:-1]
            else:
                xy = _arc(e.f(10), e.f(20), r, math.radians(e.f(50)),
                          math.radians(e.f(51)), chord)
            pts = _wcs(np.column_stack([xy, np.full(len(xy), e.f(30))]), _ocs(e))
            self.add_line(pts, kind == "CIRCLE", layer, xf)
        elif kind == "LWPOLYLINE":
            xs, ys = e.all(10), e.all(20)
            bulges, current = [], None
            for c, v in e.tags:  # o bulge (42) vem depois do vértice a que pertence
                if c == 10:
                    if current is not None:
                        bulges.append(current)
                    current = 0.0
                elif c == 42 and current is not None:
                    current = float(v)
            if current is not None:
                bulges.append(current)
            pts = [(float(x), float(y)) for x, y in zip(xs, ys, strict=False)]
            closed = bool(e.i(70) & 1)
            elevation, ocs = e.f(38), _ocs(e)
            if ocs is None and not any(abs(b) > 1e-12 for b in bulges):
                self.add_line([(x, y, elevation) for x, y in pts], closed, layer, xf)
                return
            xy = _bulged(pts, bulges, closed, chord)
            if not len(xy):
                return
            pts3 = _wcs(np.column_stack([xy, np.full(len(xy), elevation)]), ocs)
            self.add_line(pts3, closed, layer, xf)
        elif kind == "POLYLINE":
            flags = e.i(70)
            if flags & (16 | 64):  # malha ou polyface: fora
                return
            vertices = polyline or []
            pts = [(v.f(10), v.f(20), v.f(30)) for v in vertices if not v.i(70) & 16]
            bulges = [v.f(42) for v in vertices if not v.i(70) & 16]
            closed = bool(flags & 1)
            if flags & 8:  # 3D
                self.add_line(np.array(pts, dtype=float).reshape(-1, 3), closed, layer, xf)
            else:
                xy = _bulged([p[:2] for p in pts], bulges, closed, chord)
                if not len(xy):
                    return
                z = e.f(30)
                pts3 = _wcs(np.column_stack([xy, np.full(len(xy), z)]), _ocs(e))
                self.add_line(pts3, closed, layer, xf)
        elif kind == "ELLIPSE":
            c = np.array([e.f(10), e.f(20), e.f(30)])
            a = np.array([e.f(11), e.f(21), e.f(31)])
            n = np.array([e.f(210, 0.0), e.f(220, 0.0), e.f(230, 1.0)])
            b = np.cross(n / (np.linalg.norm(n) or 1.0), a) * e.f(40, 1.0)
            t0, t1 = e.f(41, 0.0), e.f(42, 2 * math.pi)
            sweep = (t1 - t0) % (2 * math.pi) or 2 * math.pi
            steps = _steps(float(np.linalg.norm(a)), sweep, chord)
            t = t0 + np.linspace(0.0, sweep, steps + 1)
            full = abs(sweep - 2 * math.pi) < 1e-9
            pts = c + np.outer(np.cos(t), a) + np.outer(np.sin(t), b)
            self.add_line(pts[:-1] if full else pts, full, layer, xf)
        elif kind == "SPLINE":
            if e.cache is None:
                e.cache = _spline(e, chord).tolist()
            self.add_line(e.cache, bool(e.i(70) & 1), layer, xf)
        elif kind in ("TEXT", "MTEXT"):
            if kind == "MTEXT":
                value = _mtext("".join(e.all(3)) + e.text(1))
                angle = e.get(50)
                if angle is not None:  # em graus, como o ezdxf lê
                    angle = float(angle)
                elif e.get(11) is not None:
                    angle = math.degrees(math.atan2(e.f(21), e.f(11)))
                else:
                    angle = 0.0
            else:
                value = _special(e.text(1))
                angle = e.f(50)
            value = value.strip()
            if not value:
                return
            m, off, sz, _, turn, mirrored = xf
            at = np.array([e.f(10), e.f(20)]) @ m.T + off
            scale = math.sqrt(abs(np.linalg.det(m))) or 1.0
            self.layer(layer)["texts"].append({
                "at": [float(at[0]), float(at[1])], "text": value,
                "height": e.f(40, 1.0) * scale,
                "angle": ((-angle if mirrored else angle) + turn) % 360.0})
        elif kind == "POINT":
            m, off, sz, oz, _, _ = xf
            at = np.array([e.f(10), e.f(20)]) @ m.T + off
            self.layer(layer)["points"].append({"at": [float(at[0]), float(at[1])],
                                                "z": e.f(30) * sz + oz})
        elif kind in ("INSERT", "DIMENSION") and depth < _MAX_DEPTH:
            self.insert(e, layer, xf, depth)

    def insert(self, e: _E, layer, xf, depth):
        name = e.text(2).strip()
        if name not in self.blocks:
            return
        base, entities = self.blocks[name]
        if e.kind == "DIMENSION":
            # O bloco da cota está no sistema do desenho, deslocado pelo 12/22/32 quando
            # a cota foi copiada (como faz o ezdxf).
            if _ocs(e) is not None:
                raise Unsupported("cota fora do plano")
            local = (np.eye(2), np.array([e.f(12), e.f(22)]), 1.0, e.f(32), 0.0, False)
        else:
            sx, sy, sz = e.f(41, 1.0), e.f(42, 1.0), e.f(43, 1.0)
            rot = math.radians(e.f(50))
            ins = np.array([e.f(10), e.f(20), e.f(30)])
            ocs = _ocs(e)
            if ocs is not None:
                if ocs[2, 2] < 0:  # extrusão para baixo: x espelhado, giro ao contrário
                    ins = ocs @ ins
                    sx, rot = -sx, -rot
                else:
                    raise Unsupported("bloco inserido fora do plano")
            c, s = math.cos(rot), math.sin(rot)
            m = np.array([[c, -s], [s, c]]) @ np.diag([sx, sy])
            off = ins[:2] - m @ np.array(base[:2])
            local = (m, off, sz, ins[2] - base[2] * sz, math.degrees(rot) % 360.0,
                     sx * sy < 0)
        cols, rows = (max(e.i(70, 1), 1), max(e.i(71, 1), 1)) if e.kind == "INSERT"             else (1, 1)  # na cota, 70 e 71 são outra coisa
        dcol, drow = e.f(44), e.f(45)
        for row in range(rows):
            for col in range(cols):
                m, off, sz, oz, turn, mirrored = local
                if cols > 1 or rows > 1:
                    rot = math.radians(e.f(50))
                    shift = np.array([col * dcol, row * drow])
                    shift = np.array([[math.cos(rot), -math.sin(rot)],
                                      [math.sin(rot), math.cos(rot)]]) @ shift
                    off = off + shift
                pm, poff, psz, poz, pturn, pmir = xf
                combined = (pm @ m, pm @ off + poff, psz * sz, psz * oz + poz,
                            ((-turn if pmir else turn) + pturn) % 360.0, mirrored != pmir)
                self.run(entities, layer, combined, depth + 1)

    def run(self, entities, parent, xf, depth):
        i, n = 0, len(entities)
        while i < n:
            e = entities[i]
            paper = (e.get(67) or "").strip() == "1"  # espaço de papel: fora
            if e.kind == "POLYLINE":
                vertices = []
                i += 1
                while i < n and entities[i].kind == "VERTEX":
                    vertices.append(entities[i])
                    i += 1
                if i < n and entities[i].kind == "SEQEND":
                    i += 1
                if not paper:
                    self.entity(e, parent, xf, depth, vertices)
                continue
            if e.kind == "INSERT" and e.i(66):  # atributos: pula até o SEQEND
                if not paper:
                    self.entity(e, parent, xf, depth)
                i += 1
                while i < n and entities[i].kind in ("ATTRIB",):
                    i += 1
                if i < n and entities[i].kind == "SEQEND":
                    i += 1
                continue
            if not paper:
                self.entity(e, parent, xf, depth)
            i += 1


def parse(data: bytes, chord_m: float = 0.01):
    """``(unidade, camadas)`` de um DXF ASCII; ``camadas``: nome → {"lines", "texts",
    "points"} como ``dxf.Layer``. ``chord_m``: desvio das curvas em metros."""
    codes, values = _tags(data)
    unit = None
    for i in range(len(codes) - 1):  # cabeçalho: 9 / $INSUNITS / 70 / valor
        if codes[i] == 9 and values[i].strip() == "$INSUNITS":
            try:
                unit = UNITS_CODE.get(int(values[i + 1].strip()))
            except ValueError:
                unit = None
            break
    section = None
    block = None
    blocks, entities, sections = [], [], set()
    for tags in _groups(codes, values):
        kind = tags[0][1].strip()
        if kind == "SECTION":
            section = next((v.strip() for c, v in tags if c == 2), None)
            sections.add(section)
        elif kind == "ENDSEC":
            section = None
        elif section == "BLOCKS":
            e = _E(tags)
            if kind == "BLOCK":
                block = (e.text(2).strip(), (e.f(10), e.f(20), e.f(30)), [])
            elif kind == "ENDBLK":
                if block is not None:
                    blocks.append(block)
                block = None
            elif block is not None:
                block[2].append(e)
        elif section == "ENTITIES":
            entities.append(_E(tags))
    if "ENTITIES" not in sections:
        raise Unsupported("sem a seção ENTITIES")
    per_unit = {"mm": 0.001, "cm": 0.01, "m": 1.0}.get(unit or "m", 1.0)
    reader = _Reader(chord_m / per_unit)
    for name, base, items in blocks:
        reader.blocks[name] = (base, items)
    reader.run(entities, None, _Reader.IDENTITY, 0)
    return unit, {name: layer for name, layer in reader.layers.items()
                  if layer["lines"] or layer["texts"] or layer["points"]}
