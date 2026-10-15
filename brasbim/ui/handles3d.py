# SPDX-License-Identifier: GPL-3.0-or-later
"""Alças da parede na vista 3D (``spec/ui/08-parede-no-3d-topo-e-inclinacao.md`` §3), sem
Qt: onde ficam, que medida mostram no quadro, que transação montam e o contorno da
pré-visualização. A vista traduz o mouse em ponto no plano (pontas, face) ou em cota z
(topo, base) e chama ``update``."""

from __future__ import annotations

import math

from brasbim.core import geom2d, snap
from brasbim.core.document import OpError
from brasbim.core.geom2d import Point
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import rebuild

PLANAR = ("start", "end", "face")  # arrastadas no plano do pavimento
VERTICAL = ("top", "base")  # arrastadas na vertical
_LABELS = {"start": ("length", "Comprimento"), "end": ("length", "Comprimento"),
           "face": ("distance", "Distância"), "top": ("height", "Altura"),
           "base": ("base", "Base")}
MIN_HEIGHT = 0.05


def wall_frame(doc, gid: str) -> tuple[dict, float, float]:
    """(estado, cota da base no mundo, altura) da parede."""
    state = cmd.read_state(doc, doc.get(gid, "IfcWall"))
    zb = rebuild.elevation(doc, state["storey"]) + state["base_offset"]
    return state, zb, rebuild.height(doc, state)


def wall_handles(doc, wall: snap.WallPath) -> list[tuple[str, tuple[float, float, float]]]:
    """(tipo, ponto 3D) das alças da parede; arco só pontas, topo e base (§3)."""
    _, zb, h = wall_frame(doc, wall.gid)
    path, frame = wall.path, wall.frame
    mid_t = path.t_end / 2
    center = frame.to_global(path.point((wall.ymin + wall.ymax) / 2, mid_t))
    out = [("start", (*path.start, zb)), ("end", (*path.end, zb))]
    if wall.straight:
        face = frame.to_global(path.point(wall.ymax, mid_t))
        out.append(("face", (*face, zb + h / 2)))
    out += [("top", (*center, zb + h)), ("base", (*center, zb))]
    return out


class WallHandle3D:
    """Arrasto de uma alça da parede no 3D (estado do arrasto + medida no quadro)."""

    def __init__(self, ctx, wall: snap.WallPath, kind: str):
        self.ctx, self.wall, self.kind = ctx, wall, kind
        self.state, self.zb, self.h = wall_frame(ctx.session.doc, wall.gid)
        self.storey_z = self.zb - self.state["base_offset"]
        self.fixed: dict[str, float] = {}
        self.moved = False
        self.sticky = False  # clique sem arrastar: a alça segue o cursor
        self.ctrl = False
        self.point: Point | None = None  # último ponto no plano (pontas, face)
        self.z: float | None = None  # última cota (topo, base)
        self.error: str | None = None
        self.tx = None
        self.anchor = None  # ponto 3D da alça (o plano vertical do arrasto passa por ele)

    @property
    def planar(self) -> bool:
        return self.kind in PLANAR

    # medida (quadro de medidas, spec/ui 07 §2)

    def value(self) -> float | None:
        key = _LABELS[self.kind][0]
        if key in self.fixed:
            return self.fixed[key]
        w = self.wall
        if self.kind in ("start", "end"):
            fixed = w.path.end if self.kind == "start" else w.path.start
            return math.dist(fixed, self.point) if self.point else w.path.length
        if self.kind == "face":
            return abs(self._offset()) if self.point else 0.0
        if self.kind == "top":
            return (self.z - self.zb) if self.z is not None else self.h
        return (self.z - self.storey_z) if self.z is not None else self.state["base_offset"]

    def fields(self):
        from brasbim.ui.tools import Field

        key, label = _LABELS[self.kind]
        return [Field(key, label, "m", self.value(), self.fixed.get(key))]

    def check(self, key: str, value: float) -> str | None:
        if key in ("length", "height") and value <= MIN_HEIGHT:
            return "medida pequena demais"
        return None

    # entrada

    def _offset(self) -> float:
        """Deslocamento da face (positivo para a esquerda) até o ponto atual."""
        return self.wall.frame.to_local(self.point)[1] - self.wall.ymax

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

    def build(self):
        doc, w, state = self.ctx.session.doc, self.wall, self.state
        value = self.fixed.get(_LABELS[self.kind][0])
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
        if self.kind == "top":
            height = value if value is not None else self.value()
            if height <= MIN_HEIGHT:
                raise OpError("altura pequena demais")
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
        state = dict(self.state)
        if self.tx is not None:
            for op in self.tx.ops:
                if op.op == "wall.edit" and op.id == self.wall.gid:
                    state.update(op.after or {})
        doc = self.ctx.session.doc
        try:
            path = geom2d.path_from_dict(state["path"])
            frame = geom2d.frame(path)
            local = geom2d.polygon(path.local_profile(self.wall.ymin, self.wall.ymax),
                                   arc_steps=48)
        except ValueError:
            return []
        ring = [frame.to_global(q) for q in local]
        zb = rebuild.elevation(doc, state["storey"]) + state["base_offset"]
        zt = zb + rebuild.height(doc, state)
        bottom = [(x, y, zb) for x, y in ring]
        top = [(x, y, zt) for x, y in ring]
        lines = [bottom + bottom[:1], top + top[:1]]
        corners = [ring[0], ring[len(ring) // 2 - 1], ring[len(ring) // 2], ring[-1]]
        lines += [[(x, y, zb), (x, y, zt)] for x, y in corners]
        return lines
