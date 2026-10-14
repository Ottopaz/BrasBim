# SPDX-License-Identifier: GPL-3.0-or-later
"""Ferramentas da planta (``spec/ui/01-janela-e-ferramentas.md`` §5), sem Qt.

A vista traduz mouse e teclado em chamadas (``move``, ``press``, ``double``, ``release``,
``key``, ``numeric``, ``cancel``) com coordenadas do pavimento em metros, e desenha o que
``preview()`` e ``labels()`` devolvem. As ferramentas montam comandos do núcleo e os
aplicam pela sessão.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

from brasbim.core import geom2d, plan, snap
from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params
from brasbim.core.geom2d import Point
from brasbim.core.walls import commands as cmd
from brasbim.core.walls import openings
from brasbim.core.walls import params as wall_params
from brasbim.core.walls import types as wall_types
from brasbim.ui.session import Session

DRAG_START = 0.5  # fração de ``tol`` que o cursor precisa andar para começar a arrastar


def fmt(value: float) -> str:
    """Número em metros com vírgula decimal (spec/ui §2.1)."""
    return f"{value:.2f}".replace(".", ",")


def parse_number(text: str) -> float:
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError("vazio")
    return float(text)


@dataclass(frozen=True)
class Mods:
    shift: bool = False
    alt: bool = False
    ctrl: bool = False


@dataclass(frozen=True)
class Mark:
    """Traço de pré-visualização. ``style``: ``preview``, ``invalid`` ou ``gap``."""

    points: tuple[Point, ...]
    closed: bool = True
    style: str = "preview"


class PlanContext:
    """Sessão + dados do pavimento ativo que as ferramentas consultam."""

    def __init__(self, session: Session):
        self.session = session
        self.tol = 0.1  # distância de atração em metros (a vista atualiza pela escala)
        self.grid = 0.1
        self._plan = None
        self._walls = None

    def invalidate(self) -> None:
        self._plan = self._walls = None

    @property
    def plan(self) -> plan.Plan:
        if self._plan is None:
            storey = self.session.storey
            self._plan = plan.storey_plan(self.session.doc, storey) if storey else plan.Plan()
        return self._plan

    @property
    def walls(self) -> list[snap.WallPath]:
        if self._walls is None:
            storey = self.session.storey
            self._walls = snap.wall_paths(self.session.doc, storey) if storey else []
        return self._walls

    def snap(self, p: Point, mods: Mods, origin: Point | None = None,
             extra=()) -> snap.Snap:
        if mods.shift and origin is not None:
            return snap.Snap(snap.constrain(origin, p), "free")
        if mods.alt:
            return snap.Snap(tuple(p), "free")
        return snap.snap(self.walls, p, self.tol, self.grid, list(extra))


class Tool:
    name = ""
    label = ""

    def __init__(self, ctx: PlanContext):
        self.ctx = ctx
        self.cursor: Point | None = None
        self.snapped: snap.Snap | None = None

    @property
    def session(self) -> Session:
        return self.ctx.session

    def hint(self) -> str:
        return ""

    def preview(self) -> list[Mark]:
        return []

    def labels(self) -> list[tuple[Point, str]]:
        return []

    def move(self, p: Point, mods: Mods) -> None:
        self.cursor = p

    def press(self, p: Point, mods: Mods, button: str = "left") -> None:
        pass

    def release(self, p: Point, mods: Mods) -> None:
        pass

    def double(self, p: Point, mods: Mods) -> None:
        pass

    def key(self, key: str) -> bool:
        """Tecla da ferramenta (``enter``, ``tab``); devolve se foi usada."""
        return False

    def numeric(self, value: float) -> bool:
        return False

    def cancel(self) -> bool:
        """Esc: descarta o que estiver em andamento; devolve se havia algo."""
        return False


# --- Selecionar (§5.1) ------------------------------------------------------------------


class SelectTool(Tool):
    name, label = "select", "Selecionar"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.drag: dict | None = None

    def hint(self) -> str:
        if self.drag and self.drag.get("active"):
            return "Solte sobre uma parede reta para posicionar a porta (Esc cancela)"
        return "Clique para selecionar; Ctrl+clique soma; arraste uma porta para movê-la"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        selection = self.session.selection
        if gid and not mods.ctrl and gid in selection:
            entity = self.session.doc.find(gid)
            if entity is not None and entity.is_a("IfcDoor") and len(selection) == 1:
                self.drag = {"door": gid, "start": p, "active": False, "target": None}
                return
        self.session.select([gid] if gid else [], add=mods.ctrl)
        if gid and not mods.ctrl:
            entity = self.session.doc.find(gid)
            if entity is not None and entity.is_a("IfcDoor"):
                self.drag = {"door": gid, "start": p, "active": False, "target": None}

    def move(self, p, mods):
        super().move(p, mods)
        drag = self.drag
        if not drag:
            return
        if not drag["active"] and math.dist(p, drag["start"]) < self.ctx.tol * DRAG_START:
            return
        drag["active"] = True
        door = self.session.doc.find(drag["door"])
        drag["target"] = _door_target(self.ctx, door, p)

    def release(self, p, mods):
        drag, self.drag = self.drag, None
        if not drag or not drag["active"] or drag["target"] is None:
            return
        target = drag["target"]
        if target.get("error"):
            self.session.message(target["error"], "recusa")
            return
        door = self.session.doc.find(drag["door"])
        self.session.run(lambda: fc.edit_door(self.session.doc, door, wall=target["wall"],
                                              distance=target["distance"]))

    def cancel(self):
        if self.drag:
            self.drag = None
            return True
        return False

    def preview(self):
        if not self.drag or not self.drag.get("target"):
            return []
        return self.drag["target"]["marks"]

    def labels(self):
        if not self.drag or not self.drag.get("target"):
            return []
        return self.drag["target"]["labels"]


# --- paredes (§5.2–5.4) -----------------------------------------------------------------


class _WallOptions:
    """Opções comuns de criação de parede (§5.2, item 5)."""

    def __init__(self, session: Session):
        types = sorted(session.doc.ifc.by_type("IfcWallType"), key=lambda t: t.Name or "")
        self.type = types[0].GlobalId if types else None
        self.ref_line = "left_face"
        self.top = "storey"  # "storey" (pavimento de cima) ou "fixed"
        self.fixed_height = wall_params.DEFAULT_FIXED_HEIGHT

    def command_options(self) -> dict:
        out = {"ref_line": self.ref_line}
        if self.top == "fixed":
            out.update(top_mode="fixed", fixed_height=self.fixed_height)
        return out

    def band(self, doc) -> tuple[float, float]:
        wall_type = doc.find(self.type) if self.type else None
        thickness = wall_types.thickness(wall_type) if wall_type is not None else 0.14
        sense, offset = wall_params.layer_usage(self.ref_line, False, thickness)
        return wall_params.band(sense, offset, thickness)


def _band_mark(path: geom2d.Path, ymin: float, ymax: float, style="preview") -> Mark:
    frame = geom2d.frame(path)
    local = geom2d.polygon(path.local_profile(ymin, ymax), arc_steps=48)
    return Mark(tuple(frame.to_global(q) for q in local), True, style)


class _WallTool(Tool):
    def __init__(self, ctx, options: _WallOptions | None = None):
        super().__init__(ctx)
        self.options = options or _WallOptions(ctx.session)
        self.points: list[Point] = []

    def _point(self, p, mods) -> Point:
        origin = self.points[-1] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin, extra=self.points)
        return self.snapped.point

    def move(self, p, mods):
        super().move(p, mods)
        self._point(p, mods)

    def cancel(self):
        if self.points:
            self.points = []
            return True
        return False

    def _commit(self, build) -> None:
        if self.options.type is None:
            self.session.message("não há tipo de parede no projeto", "recusa")
        elif self.session.storey is None:
            self.session.message("não há pavimento ativo", "recusa")
        else:
            self.session.run(build)
        self.points = []

    def _band(self, a: Point, b: Point, style="preview") -> list[Mark]:
        try:
            path = geom2d.LinePath(a, b)
        except ValueError:
            return []
        return [_band_mark(path, *self.options.band(self.session.doc), style)]


class WallTool(_WallTool):
    name, label = "wall", "Parede"

    def hint(self):
        if not self.points:
            return "Clique o ponto inicial da parede"
        return ("Clique o próximo ponto; Enter, clique duplo ou botão direito encerra; "
                "digite um número para o comprimento; Esc descarta")

    def press(self, p, mods, button="left"):
        if button == "right":
            self.finish()
            return
        q = self._point(p, mods)
        if not self.points:
            self.points = [q]
        elif len(self.points) >= 3 and math.dist(q, self.points[0]) < 1e-6:
            self.finish(closed=True)
        elif math.dist(q, self.points[-1]) > geom2d.MIN_LENGTH:
            self.points.append(q)

    def double(self, p, mods):
        self.finish()

    def key(self, key):
        if key == "enter":
            self.finish()
            return True
        return False

    def numeric(self, value):
        if not self.points or value <= geom2d.MIN_LENGTH:
            return False
        last = self.points[-1]
        target = self.snapped.point if self.snapped else self.cursor
        dx, dy = (target[0] - last[0], target[1] - last[1]) if target else (1.0, 0.0)
        length = math.hypot(dx, dy)
        dx, dy = (dx / length, dy / length) if length > 1e-9 else (1.0, 0.0)
        self.points.append((last[0] + value * dx, last[1] + value * dy))
        return True

    def finish(self, closed: bool = False) -> None:
        points = list(self.points)
        if closed:
            points = points[:]  # o último ponto é o primeiro: create_chain fecha
        if len(points) < 2:
            self.points = []
            return
        options, doc, storey = self.options, self.session.doc, self.session.storey
        self._commit(lambda: cmd.create_chain(doc, options.type, storey, points, closed=closed,
                                              **options.command_options()))

    def preview(self):
        marks = []
        pts = list(self.points)
        if pts and self.snapped:
            pts.append(self.snapped.point)
        for a, b in itertools.pairwise(pts):
            marks += self._band(a, b)
        return marks

    def labels(self):
        if self.points and self.snapped:
            return [(self.snapped.point,
                     f"{fmt(math.dist(self.points[-1], self.snapped.point))} m")]
        return []


class ArcWallTool(_WallTool):
    name, label = "arc", "Parede em arco"

    def hint(self):
        return ["Clique o início do arco", "Clique um ponto do arco",
                "Clique o fim do arco"][min(len(self.points), 2)]

    def _arc(self, end: Point):
        try:
            return geom2d.arc_through(self.points[0], self.points[1], end)
        except (ValueError, ZeroDivisionError):
            return None

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self._point(p, mods)
        if len(self.points) < 2:
            if not self.points or math.dist(q, self.points[-1]) > geom2d.MIN_LENGTH:
                self.points.append(q)
            return
        if self._arc(q) is None:
            self.session.message("os três pontos não formam um arco", "recusa")
            return
        a, b = self.points
        options, doc, storey = self.options, self.session.doc, self.session.storey
        self._commit(lambda: cmd.create_arc_wall(doc, options.type, storey, a, b, q,
                                                 **options.command_options()))

    def preview(self):
        if not self.points or not self.snapped:
            return []
        end = self.snapped.point
        if len(self.points) == 1:
            return self._band(self.points[0], end)
        arc = self._arc(end)
        if arc is None:
            return []
        return [_band_mark(arc, *self.options.band(self.session.doc))]


class RectangleTool(_WallTool):
    name, label = "rectangle", "Retângulo"

    def hint(self):
        return "Clique o primeiro canto" if not self.points else "Clique o canto oposto"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self._point(p, mods)
        if not self.points:
            self.points = [q]
            return
        a = self.points[0]
        if abs(q[0] - a[0]) < geom2d.MIN_LENGTH or abs(q[1] - a[1]) < geom2d.MIN_LENGTH:
            self.session.message("o retângulo precisa de largura e profundidade", "recusa")
            return
        options, doc, storey = self.options, self.session.doc, self.session.storey
        self._commit(lambda: cmd.create_rectangle(doc, options.type, storey, a, q,
                                                  **options.command_options()))

    def preview(self):
        if not self.points or not self.snapped:
            return []
        (x0, y0), (x1, y1) = self.points[0], self.snapped.point
        (x0, x1), (y0, y1) = sorted((x0, x1)), sorted((y0, y1))
        corners = [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]
        marks = []
        for a, b in itertools.pairwise(corners):
            marks += self._band(a, b)
        return marks

    def labels(self):
        if not self.points or not self.snapped:
            return []
        a, b = self.points[0], self.snapped.point
        return [(b, f"{fmt(abs(b[0] - a[0]))} × {fmt(abs(b[1] - a[1]))} m")]


# --- porta (§5.5) -----------------------------------------------------------------------


def door_marks(doc, wall: snap.WallPath, distance: float, width: float, tstate: dict,
               opens_to: str, align: str, offset: float, style: str = "preview") -> list[Mark]:
    """Pré-visualização da porta no vão (posição de ``porta.md`` §6.1)."""
    lining = tstate["lining"]
    depth = lining["depth"] or (wall.ymax - wall.ymin)
    a, b = params.lining_band(align, offset, depth, wall.ymin, wall.ymax)
    frame = wall.frame
    if opens_to == "left":
        def to_wall(q):
            return (distance + q[0], a + q[1])
    else:
        def to_wall(q):
            return (distance + width - q[0], b - q[1])
    marks = [Mark(tuple(frame.to_global(q) for q in [
        (distance, wall.ymin), (distance + width, wall.ymin),
        (distance + width, wall.ymax), (distance, wall.ymax)]), True, "gap")]
    for _, pts, closed in plan.door_symbol(width, depth, tstate["operation_type"], lining,
                                           tstate["panels"]):
        marks.append(Mark(tuple(frame.to_global(to_wall(q)) for q in pts), closed, style))
    return marks


def _edge_labels(wall: snap.WallPath, distance: float, width: float) -> list[tuple[Point, str]]:
    frame, y = wall.frame, wall.ymax + 0.15
    before, after = distance, wall.path.length - distance - width
    return [(frame.to_global((distance / 2, y)), fmt(before)),
            (frame.to_global((distance + width + after / 2, y)), fmt(after))]


def _door_target(ctx: PlanContext, door, p: Point) -> dict | None:
    """Para onde a porta arrastada iria (§5.1): parede reta sob o cursor e distância."""
    hit = snap.wall_at(ctx.walls, p, ctx.tol)
    if hit is None or not hit.wall.straight:
        return None
    opening = fc.opening_of(door)
    o = openings.read_state(opening)
    width = o["width"]
    distance = hit.along - width / 2
    state = doors.read_state(door)
    error = None
    try:
        fc.edit_door(ctx.session.doc, door, wall=hit.wall.gid, distance=distance)
    except OpError as e:
        error = str(e)
    if state["foreign"] is None:
        tstate = door_types.read(ctx.session.doc.get(state["type"]))
    else:
        tstate = {**door_types.default_state("NOTDEFINED"), "lining": {"thickness": 0,
                                                                       "depth": None}}
    marks = door_marks(ctx.session.doc, hit.wall, distance, width, tstate, state["opens_to"],
                       state["align"], state["offset"], "invalid" if error else "preview")
    return {"wall": hit.wall.gid, "distance": distance, "error": error, "marks": marks,
            "labels": _edge_labels(hit.wall, distance, width)}


class DoorTool(Tool):
    name, label = "door", "Porta"

    def __init__(self, ctx):
        super().__init__(ctx)
        types = sorted(ctx.session.doc.ifc.by_type("IfcDoorType"), key=lambda t: t.Name or "")
        self.type = types[0].GlobalId if types else None
        self.width: float | None = None  # vazio = padrão do tipo
        self.height: float | None = None
        self.base: float | None = None
        self.align = "axis"
        self.offset = 0.0
        self.hinges = "left"
        self.target: dict | None = None

    def type_state(self) -> dict | None:
        door_type = self.session.doc.find(self.type) if self.type else None
        return door_types.read(door_type) if door_type is not None else None

    def handed_state(self) -> dict | None:
        """Estado do tipo com as dobradiças escolhidas (variante, se for o caso)."""
        tstate = self.type_state()
        if tstate is None:
            return None
        hand = params.hand_of(tstate["operation_type"])
        if hand is not None and hand != self.hinges:
            return door_types.mirrored(tstate, None)
        return tstate

    def hint(self):
        tstate = self.type_state()
        if tstate is None:
            return "Não há tipo de porta no projeto"
        hinge = ""
        if params.hand_of(tstate["operation_type"]) is not None:
            side = "esquerda" if self.hinges == "left" else "direita"
            hinge = f"; Tab troca as dobradiças (agora: {side})"
        return "Passe o cursor sobre uma parede reta e clique" + hinge

    def key(self, key):
        if key == "tab":
            self.hinges = "right" if self.hinges == "left" else "left"
            if self.cursor:
                self.move(self.cursor, Mods())
            return True
        return False

    def move(self, p, mods):
        super().move(p, mods)
        self.target = None
        tstate = self.handed_state()
        hit = snap.wall_at(self.ctx.walls, p, self.ctx.tol)
        if tstate is None or hit is None:
            return
        if not hit.wall.straight:
            self.target = {"error": "porta em parede em arco ainda não é suportada (V1)",
                           "marks": [], "labels": []}
            return
        defaults = tstate["defaults"]
        width = self.width or defaults["width"]
        height = self.height or defaults["height"]
        base = defaults["base"] if self.base is None else self.base
        along = hit.along
        length = hit.wall.path.length
        if not mods.alt and abs(along - length / 2) <= self.ctx.tol:
            along = length / 2  # snap ao meio da parede
        distance = along - width / 2
        opens_to = "left" if hit.left else "right"
        error = None
        try:
            wall = self.session.doc.get(hit.wall.gid)
            openings.check_fits(self.session.doc, wall, {
                **openings.default_state(), "wall": hit.wall.gid, "distance": distance,
                "width": width, "height": height, "sill": base})
        except OpError as e:
            error = str(e)
        self.target = {
            "wall": hit.wall.gid, "distance": distance, "width": width, "height": height,
            "base": base, "opens_to": opens_to, "error": error,
            "marks": door_marks(self.session.doc, hit.wall, distance, width, tstate, opens_to,
                                self.align, self.offset, "invalid" if error else "preview"),
            "labels": _edge_labels(hit.wall, distance, width),
        }

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        target = self.target
        if target is None:
            self.session.message("clique sobre uma parede", "recusa")
            return
        if target["error"]:
            self.session.message(target["error"], "recusa")
            return
        tstate = self.type_state()
        hinges = self.hinges if params.hand_of(tstate["operation_type"]) else None
        doc = self.session.doc
        self.session.run(lambda: fc.create_door(
            doc, self.type, target["wall"], target["distance"], target["width"],
            target["height"], target["base"], hinges=hinges, opens_to=target["opens_to"],
            align=self.align, offset=self.offset))
        self.move(p, mods)

    def preview(self):
        return self.target["marks"] if self.target else []

    def labels(self):
        return self.target["labels"] if self.target else []


TOOLS = (SelectTool, WallTool, ArcWallTool, RectangleTool, DoorTool)


@dataclass
class ToolBox:
    """Ferramenta ativa e opções que sobrevivem à troca de ferramenta (§7.1)."""

    ctx: PlanContext
    tools: dict = field(default_factory=dict)
    active: Tool | None = None

    def __post_init__(self):
        self.reset()

    def reset(self) -> None:
        """Recria as ferramentas (documento novo: tipos diferentes)."""
        wall_options = _WallOptions(self.ctx.session)
        self.tools = {}
        for cls in TOOLS:
            tool = cls(self.ctx, wall_options) if issubclass(cls, _WallTool) else cls(self.ctx)
            self.tools[cls.name] = tool
        name = self.active.name if self.active else "select"
        self.active = self.tools[name]

    def activate(self, name: str) -> Tool:
        if self.active is not None:
            self.active.cancel()
        self.active = self.tools[name]
        return self.active
