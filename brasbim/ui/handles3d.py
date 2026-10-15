# SPDX-License-Identifier: GPL-3.0-or-later
"""Alças da parede na vista 3D (``spec/ui/08-parede-no-3d-topo-e-inclinacao.md`` §3), sem
Qt: onde ficam, que medida mostram no quadro, que transação montam e o contorno da
pré-visualização. A vista traduz o mouse em ponto no plano (pontas, face, inclinação), em
cota z (topo, base) ou em ponto no plano vertical da parede (vértice interno do topo,
§4.1) e chama ``update``.

Alças: ``start``, ``end``, ``face``, ``top`` (topo plano) ou ``top0``…``topN`` (um vértice
por ponto do perfil do topo), ``base`` e ``tilt`` (inclinação, §5)."""

from __future__ import annotations

import math

from brasbim.core import geom2d, snap
from brasbim.core.document import OpError
from brasbim.core.geom2d import Point
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import params, rebuild, top

PLANAR = ("start", "end", "face", "tilt")  # arrastadas num plano horizontal
_LABELS = {"start": ("length", "Comprimento", "m"), "end": ("length", "Comprimento", "m"),
           "face": ("distance", "Distância", "m"), "top": ("height", "Altura", "m"),
           "base": ("base", "Base", "m"), "tilt": ("tilt", "Inclinação", "°")}
MIN_HEIGHT = 0.05
TILT_GAP = 0.30  # distância da alça de inclinação à face, no topo (§3)


def vertex_index(kind: str) -> int | None:
    """Índice do ponto do perfil da alça ``topN`` (None nas outras)."""
    return int(kind[3:]) if kind.startswith("top") and kind[3:].isdigit() else None


def _label(kind: str) -> tuple[str, str, str]:
    return _LABELS["top" if vertex_index(kind) is not None else kind]


def wall_frame(doc, gid: str) -> tuple[dict, float, float]:
    """(estado, cota da base no mundo, altura) da parede."""
    state = cmd.read_state(doc, doc.get(gid, "IfcWall"))
    zb = rebuild.elevation(doc, state["storey"]) + state["base_offset"]
    return state, zb, rebuild.height(doc, state)


def _at(wall: snap.WallPath, x: float, y: float, z_rel: float, zb: float,
        lean: float) -> tuple[float, float, float]:
    """Ponto 3D de (x, y) local na altura ``z_rel`` da base, com o tombamento ``lean``
    (tangente da inclinação)."""
    p = wall.frame.to_global(wall.path.point(y + z_rel * lean, x))
    return (p[0], p[1], zb + z_rel)


def wall_handles(doc, wall: snap.WallPath) -> list[tuple[str, tuple[float, float, float]]]:
    """(tipo, ponto 3D) das alças da parede; arco só pontas, topo e base (§3)."""
    state, zb, h = wall_frame(doc, wall.gid)
    path = wall.path
    lean = math.tan(math.radians(state["tilt"]))
    mid_t = path.t_end / 2
    center = (wall.ymin + wall.ymax) / 2
    out = [("start", (*path.start, zb)), ("end", (*path.end, zb))]
    if wall.straight:
        out.append(("face", _at(wall, mid_t, wall.ymax, h / 2, zb, lean)))
    profile = state["top_profile"]
    if profile:
        out += [(f"top{i}", _at(wall, x, center, z, zb, lean))
                for i, (x, z) in enumerate(profile)]
    else:
        out.append(("top", _at(wall, mid_t, center, h, zb, lean)))
    out.append(("base", _at(wall, mid_t, center, 0.0, zb, lean)))
    if wall.straight:
        out.append(("tilt", _at(wall, mid_t, wall.ymax + TILT_GAP, h, zb, lean)))
    return out


class WallHandle3D:
    """Arrasto de uma alça da parede no 3D (estado do arrasto + medida no quadro)."""

    def __init__(self, ctx, wall: snap.WallPath, kind: str):
        self.ctx, self.wall, self.kind = ctx, wall, kind
        self.state, self.zb, self.h = wall_frame(ctx.session.doc, wall.gid)
        self.storey_z = self.zb - self.state["base_offset"]
        self.lean = math.tan(math.radians(self.state["tilt"]))
        self.index = vertex_index(kind)
        self.fixed: dict[str, float] = {}
        self.moved = False
        self.sticky = False  # clique sem arrastar: a alça segue o cursor
        self.ctrl = False
        self.point: Point | None = None  # último ponto no plano (pontas, face, inclinação)
        self.z: float | None = None  # última cota (topo, base)
        self.error: str | None = None
        self.tx = None
        self.anchor = None  # ponto 3D da alça (o plano vertical do arrasto passa por ele)

    @property
    def planar(self) -> bool:
        return self.kind in PLANAR

    @property
    def plane_z(self) -> float:
        """Cota do plano horizontal das alças planas."""
        return self.zb + {"face": self.h / 2, "tilt": self.h}.get(self.kind, 0.0)

    @property
    def in_wall_plane(self) -> bool:
        """Vértice interno do topo: anda também ao longo da parede (§4.1)."""
        n = len(self.state["top_profile"])
        return self.index is not None and 0 < self.index < n - 1

    # medida (quadro de medidas, spec/ui 07 §2)

    def value(self) -> float | None:
        key = _label(self.kind)[0]
        if key in self.fixed:
            return self.fixed[key]
        w = self.wall
        if self.kind in ("start", "end"):
            fixed = w.path.end if self.kind == "start" else w.path.start
            return math.dist(fixed, self.point) if self.point else w.path.length
        if self.kind == "face":
            return abs(self._offset()) if self.point else 0.0
        if self.kind == "tilt":
            return self._tilt() if self.point else self.state["tilt"]
        if self.index is not None:
            return (self.z - self.zb) if self.z is not None else \
                self.state["top_profile"][self.index][1]
        if self.kind == "top":
            return (self.z - self.zb) if self.z is not None else self.h
        return (self.z - self.storey_z) if self.z is not None else self.state["base_offset"]

    def fields(self):
        from brasbim.ui.tools import Field

        key, label, unit = _label(self.kind)
        return [Field(key, label, unit, self.value(), self.fixed.get(key))]

    def check(self, key: str, value: float) -> str | None:
        if key in ("length", "height") and value <= MIN_HEIGHT:
            return "medida pequena demais"
        if key == "tilt" and abs(value) > params.MAX_TILT:
            return f"inclinação fora do limite de ±{params.MAX_TILT:.0f}°"
        return None

    # entrada

    def _offset(self) -> float:
        """Deslocamento da face (positivo para a esquerda) até o ponto atual."""
        y = self.wall.frame.to_local(self.point)[1]
        return y - self.wall.ymax - self.h / 2 * self.lean

    def _tilt(self) -> float:
        """Inclinação (graus) que leva a face esquerda do topo a ``TILT_GAP`` do ponto."""
        y = self.wall.frame.to_local(self.point)[1] - TILT_GAP
        ymax0 = self.wall.ymax / rebuild.widening(self.state)  # face sem o alargamento
        angle = 0.0
        for _ in range(8):  # o alargamento da base depende do próprio ângulo
            angle = math.atan((y - ymax0 / math.cos(angle)) / self.h)
        degrees = math.degrees(angle)
        return max(-params.MAX_TILT, min(params.MAX_TILT, degrees))

    def snap_z(self, z: float, alt: bool, tol: float) -> float:
        """Cota com *snap* nas cotas dos pavimentos e na grade de 0,10 m (§3)."""
        if alt:
            return z
        for storey in self.ctx.session.doc.storeys():
            level = float(storey.Elevation or 0.0)
            if abs(z - level) <= tol:
                return level
        grid = self.ctx.grid
        return self.storey_z + round((z - self.storey_z) / grid) * grid

    def update(self, point: Point | None = None, z: float | None = None,
               ctrl: bool = False) -> None:
        if point is not None:
            self.point = point
        if z is not None:
            self.z = z
        self.ctrl = ctrl
        try:
            self.tx, self.error = self.build(), None
        except OpError as e:
            self.tx, self.error = None, str(e)

    def _vertex_profile(self, height: float) -> list[list[float]]:
        """Perfil com o vértice da alça na altura nova (e na posição nova, se interno)."""
        state = self.state
        profile = [list(p) for p in state["top_profile"]]
        i, last = self.index, len(profile) - 1
        if self.in_wall_plane and self.point is not None:
            x = self.wall.frame.to_local(self.point)[0]
            lo, hi = profile[i - 1][0], profile[i + 1][0]
            profile[i][0] = min(max(x, lo + geom2d.MIN_LENGTH), hi - geom2d.MIN_LENGTH)
        profile[i][1] = height
        if state["top_shape"] == "gable" and i in (0, last):
            profile[last - i][1] = height  # empena: as duas pontas na mesma altura
        return profile

    def build(self):
        doc, w, state = self.ctx.session.doc, self.wall, self.state
        value = self.fixed.get(_label(self.kind)[0])
        if self.kind in ("start", "end"):
            fixed = w.path.end if self.kind == "start" else w.path.start
            moving = w.path.start if self.kind == "start" else w.path.end
            target = self.point if self.point and math.dist(self.point, fixed) > 1e-9 \
                else moving
            if value is not None:
                d = math.dist(target, fixed)
                target = (fixed[0] + (target[0] - fixed[0]) * value / d,
                          fixed[1] + (target[1] - fixed[1]) * value / d)
            if math.dist(target, fixed) <= MIN_HEIGHT:
                raise OpError("comprimento pequeno demais")
            return cmd.move_wall_end(doc, w.gid, self.kind, target, carry=self.ctrl)
        if self.kind == "face":
            offset = self._offset() if self.point else 0.0
            if value is not None:
                offset = math.copysign(value, offset if abs(offset) > 1e-12 else 1.0)
            return cmd.offset_wall(doc, w.gid, offset, carry=not self.ctrl)
        if self.kind == "tilt":
            return cmd.edit_wall(doc, w.gid, tilt=value if value is not None else self.value())
        if self.index is not None or self.kind == "top":
            height = value if value is not None else self.value()
            if height <= MIN_HEIGHT:
                raise OpError("altura pequena demais")
            if self.index is not None:
                return cmd.edit_wall(doc, w.gid, top_profile=self._vertex_profile(height))
            if state["top_mode"] == "fixed":
                return cmd.edit_wall(doc, w.gid, fixed_height=height)
            return cmd.edit_wall(doc, w.gid, top_offset=state["top_offset"] + height - self.h)
        base = value if value is not None else self.value()
        new = {**state, "base_offset": base}
        if rebuild.height(doc, new) <= MIN_HEIGHT:
            raise OpError("a base ficaria acima do topo")
        return cmd.edit_wall(doc, w.gid, base_offset=base)

    # pré-visualização

    def outline(self) -> list[list[tuple[float, float, float]]]:
        """Arestas da parede com a mudança (contorno de baixo, de cima e verticais)."""
        state, after = dict(self.state), {}
        if self.tx is not None:
            for op in self.tx.ops:
                if op.op == "wall.edit" and op.id == self.wall.gid:
                    after.update(op.after or {})
        state.update(after)
        doc = self.ctx.session.doc
        try:
            path = geom2d.path_from_dict(state["path"])
            frame = geom2d.frame(path)
            k = rebuild.widening(state) / rebuild.widening(self.state)
            ymin, ymax = self.wall.ymin * k, self.wall.ymax * k
            local = geom2d.polygon(path.local_profile(ymin, ymax), arc_steps=48)
        except ValueError:
            return []
        zb = rebuild.elevation(doc, state["storey"]) + state["base_offset"]
        h = rebuild.height(doc, state)
        lean = math.tan(math.radians(state["tilt"]))
        profile = state["top_profile"]
        if profile and "path" in after and "top_profile" not in after:
            profile = top.scaled(profile, self.wall.path.length, path.length)  # como wall.edit

        def point(q, z_rel):
            x, y = frame.to_global((q[0], q[1] + z_rel * lean))
            return (x, y, zb + z_rel)

        def height_at(x):
            return top.at(profile, x) if profile else h

        bottom = [point(q, 0.0) for q in local]
        lines = [bottom + bottom[:1]]
        if isinstance(path, geom2d.LinePath):
            xs = [0.0, *(x for x, _ in profile[1:-1]), path.length]
            for y in (ymin, ymax):
                lines.append([point((x, y), height_at(x)) for x in xs])
            for x in (0.0, path.length):
                lines.append([point((x, ymin), height_at(x)), point((x, ymax), height_at(x))])
                lines += [[point((x, y), 0.0), point((x, y), height_at(x))]
                          for y in (ymin, ymax)]
            return lines
        upper = [point(q, h) for q in local]
        lines.append(upper + upper[:1])
        corners = [local[0], local[len(local) // 2 - 1], local[len(local) // 2], local[-1]]
        lines += [[point(q, 0.0), point(q, h)] for q in corners]
        return lines


# --- esquadria (spec/ui 09 §4.2) ------------------------------------------------------

_FILLING_LABELS = {"edge_start": ("width", "Largura"), "edge_end": ("width", "Largura"),
                   "sill": ("sill", "Peitoril"), "head": ("head", "Verga")}


def filling_handles(doc, wall: snap.WallPath, element) -> list[tuple[str, tuple]]:
    """Alças da porta ou janela selecionada sozinha: bordas do vão, base (só janela) e
    topo, no meio de cada lado, na face do lado "abre para"."""
    from brasbim.core.fillings import commands as fc
    from brasbim.core.fillings import doors
    from brasbim.core.walls import openings

    opening = fc.opening_of(element)
    if opening is None or not wall.straight:
        return []
    o = openings.read_state(opening)
    _, zb, _ = wall_frame(doc, wall.gid)
    y = wall.ymax if doors.read_state(element)["opens_to"] == "left" else wall.ymin
    x0, x1 = o["distance"], o["distance"] + o["width"]
    z0, z1 = zb + o["sill"], zb + o["sill"] + o["height"]

    def at(x, z):
        p = wall.frame.to_global((x, y))
        return (p[0], p[1], z)

    out = [("edge_start", at(x0, (z0 + z1) / 2)), ("edge_end", at(x1, (z0 + z1) / 2))]
    if element.is_a("IfcWindow"):
        out.append(("sill", at((x0 + x1) / 2, z0)))
    out.append(("head", at((x0 + x1) / 2, z1)))
    return out


class FillingHandle3D:
    """Arrasto de uma alça da esquadria no 3D, no plano vertical da parede: bordas mudam
    a largura (a outra borda fica), a base muda o peitoril (a altura fica), o topo muda a
    verga (o peitoril fica)."""

    planar = False
    in_wall_plane = True

    def __init__(self, ctx, wall: snap.WallPath, element, kind: str):
        from brasbim.core.fillings import commands as fc
        from brasbim.core.walls import openings

        self.ctx, self.wall, self.element, self.kind = ctx, wall, element, kind
        self.opening = openings.read_state(fc.opening_of(element))
        _, self.zb, _ = wall_frame(ctx.session.doc, wall.gid)
        self.storey_z = self.zb
        self.fixed: dict[str, float] = {}
        self.moved = self.sticky = self.ctrl = False
        self.point: Point | None = None
        self.z: float | None = None
        self.error: str | None = None
        self.tx = None
        self.anchor = None

    def _label(self):
        key, label = _FILLING_LABELS[self.kind]
        if key == "head" and not self.element.is_a("IfcWindow"):
            label = "Altura"
        return key, label

    def _span(self) -> tuple[float, float, float, float]:
        """(distância, largura, peitoril, altura) que a alça daria agora."""
        o = self.opening
        d, w, s, h = o["distance"], o["width"], o["sill"], o["height"]
        key = self._label()[0]
        value = self.fixed.get(key)
        if self.kind in ("edge_start", "edge_end"):
            x = self.wall.frame.to_local(self.point)[0] if self.point else None
            if self.kind == "edge_end":
                w = value if value is not None else (x - d if x is not None else w)
            else:
                end = d + w
                w = value if value is not None else (end - x if x is not None else w)
                d = end - w
        elif self.kind == "sill":
            s = value if value is not None else (self.z - self.zb if self.z is not None else s)
        elif value is not None:
            h = value - s if self.element.is_a("IfcWindow") else value  # verga ou altura
        elif self.z is not None:
            h = self.z - self.zb - s
        return d, w, s, h

    def value(self) -> float:
        _, w, s, h = self._span()
        key = self._label()[0]
        if key == "width":
            return w
        if key == "sill":
            return s
        return s + h if self.element.is_a("IfcWindow") else h

    def fields(self):
        from brasbim.ui.tools import Field

        key, label = self._label()
        return [Field(key, label, "m", self.value(), self.fixed.get(key))]

    def check(self, key: str, value: float) -> str | None:
        if key in ("width", "head") and value <= MIN_HEIGHT:
            return "medida pequena demais"
        if value < 0:
            return "a medida não pode ser negativa"
        return None

    def snap_z(self, z: float, alt: bool, tol: float) -> float:
        if alt:
            return z
        grid = self.ctx.grid / 10  # 1 cm
        return self.zb + round((z - self.zb) / grid) * grid

    def update(self, point: Point | None = None, z: float | None = None,
               ctrl: bool = False) -> None:
        if point is not None:
            self.point = point
        if z is not None:
            self.z = z
        self.ctrl = ctrl
        try:
            self.tx, self.error = self.build(), None
        except OpError as e:
            self.tx, self.error = None, str(e)

    def build(self):
        from brasbim.core.fillings import commands as fc

        d, w, s, h = self._span()
        if w <= MIN_HEIGHT or h <= MIN_HEIGHT:
            raise OpError("vão pequeno demais")
        o = self.opening
        changes = {k: v for k, v, old in (("distance", d, o["distance"]),
                                          ("width", w, o["width"]),
                                          ("base", s, o["sill"]), ("height", h, o["height"]))
                   if abs(v - old) > 1e-9}
        return fc.edit_door(self.ctx.session.doc, self.element, **changes)

    def outline(self) -> list[list[tuple[float, float, float]]]:
        d, w, s, h = self._span()
        lines = []
        for y in (self.wall.ymin, self.wall.ymax):
            pts = []
            for x, z in ((d, s), (d + w, s), (d + w, s + h), (d, s + h), (d, s)):
                p = self.wall.frame.to_global((x, y))
                pts.append((p[0], p[1], self.zb + z))
            lines.append(pts)
        return lines
