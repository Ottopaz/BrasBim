# SPDX-License-Identifier: GPL-3.0-or-later
"""Ferramentas da planta (``spec/ui/01-janela-e-ferramentas.md`` §5 e
``spec/ui/02-edicao.md`` §3–§6), sem Qt.

A vista traduz mouse e teclado em chamadas (``move``, ``press``, ``double``, ``release``,
``key``, ``numeric``, ``cancel``) com coordenadas do pavimento em metros, e desenha o que
``preview()`` e ``labels()`` devolvem. As ferramentas montam comandos do núcleo e os
aplicam pela sessão.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

from brasbim.core import geom2d, plan, snap, transform
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


def fmt_exact(value: float) -> str:
    """Como ``fmt``, mas sem perder milímetros (até 4 casas): campos que o usuário edita e
    que voltam ao modelo, como a espessura de uma camada."""
    text = f"{value:.4f}".rstrip("0")
    whole, _, decimals = text.partition(".")
    return f"{whole},{decimals.ljust(2, '0')}"


def block_grid(count: int, lines: int) -> list[tuple[int, int]]:
    """(linha, coluna) de cada campo num bloco do painel deitado (spec/ui 04 §3): de
    cima para baixo e, quando as linhas acabam, na coluna seguinte."""
    lines = max(1, lines)
    return [(i % lines, i // lines) for i in range(count)]


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
class Field:
    """Campo de medida junto ao cursor (spec/ui 07 §2): ``value`` é o que o cursor dá agora
    (None se ainda não há valor) e ``fixed`` o valor digitado, se houver."""

    key: str
    label: str
    unit: str  # "m" ou "°"
    value: float | None
    fixed: float | None = None

    def text(self, value: float | None = None) -> str:
        value = self.value if value is None else value
        if value is None:
            return ""
        if self.unit == "°":
            return f"{value:.1f}".replace(".", ",")
        return fmt(value)


def _degrees(dx: float, dy: float) -> float:
    """Ângulo absoluto em graus, 0° no eixo x, anti-horário, entre -180 e 180."""
    return math.degrees(math.atan2(dy, dx)) if math.hypot(dx, dy) > 1e-12 else 0.0


def polar_point(origin: Point, cursor: Point | None, length: float | None = None,
                angle: float | None = None) -> Point:
    """Ponto a partir de ``origin`` com comprimento e/ou ângulo (graus) fixados; o que não
    foi fixado vem do cursor (spec/ui 07 §2.3)."""
    cursor = cursor if cursor is not None else (origin[0] + 1.0, origin[1])
    dx, dy = cursor[0] - origin[0], cursor[1] - origin[1]
    if angle is not None:
        ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        dist = length if length is not None else dx * ux + dy * uy
    else:
        norm = math.hypot(dx, dy)
        if length is None:
            return tuple(cursor)
        ux, uy = (dx / norm, dy / norm) if norm > 1e-12 else (1.0, 0.0)
        dist = length
    return (origin[0] + dist * ux, origin[1] + dist * uy)


def rect_corner(a: Point, cursor: Point | None, width: float | None = None,
                height: float | None = None) -> Point:
    """Canto oposto do retângulo com largura e/ou altura fixadas; o sinal vem do lado em
    que o cursor está (spec/ui 07 §2.3)."""
    cursor = cursor if cursor is not None else (a[0] + 1.0, a[1] + 1.0)
    dx, dy = cursor[0] - a[0], cursor[1] - a[1]
    if width is not None:
        dx = math.copysign(width, dx if abs(dx) > 1e-12 else 1.0)
    if height is not None:
        dy = math.copysign(height, dy if abs(dy) > 1e-12 else 1.0)
    return (a[0] + dx, a[1] + dy)


@dataclass(frozen=True)
class Mark:
    """Traço de pré-visualização. ``style``: ``preview``, ``invalid``, ``gap``,
    ``window`` (seleção por janela) ou ``crossing`` (por cruzamento)."""

    points: tuple[Point, ...]
    closed: bool = True
    style: str = "preview"


class PlanContext:
    """Sessão + dados do pavimento ativo que as ferramentas consultam."""

    def __init__(self, session: Session):
        self.session = session
        self.tol = 0.1  # distância de atração em metros (a vista atualiza pela escala)
        self.grid = 0.1
        self.input_view = None  # vista (planta ou 3D) que recebeu o último movimento
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

    number_hint = "comprimento"

    def __init__(self, ctx: PlanContext):
        self.ctx = ctx
        self.cursor: Point | None = None
        self.snapped: snap.Snap | None = None
        self.finished = False  # a ferramenta terminou: a vista volta para Selecionar
        self.fixed: dict[str, float] = {}  # valores digitados nos campos (spec/ui 07 §2)
        self.mods = Mods()  # modificadores do último movimento (Enter confirma com eles)

    @property
    def session(self) -> Session:
        return self.ctx.session

    def hint(self) -> str:
        return ""

    def preview(self) -> list[Mark]:
        return []

    def labels(self) -> list[tuple[Point, str]]:
        return []

    def handles(self) -> list[tuple[Point, bool]]:
        """Alças a desenhar: (ponto, em destaque)."""
        return []

    def wants_number(self) -> bool:
        """Digitar um número abre o campo de entrada numérica."""
        return bool(self.fields())

    # campos de medida (spec/ui 07 §2)

    def fields(self) -> list[Field]:
        """Campos da ferramenta enquanto ela espera um ponto; vazio se não há."""
        return []

    def check(self, key: str, value: float) -> str | None:
        """Motivo para recusar o valor do campo, ou None."""
        return None

    def fix(self, key: str, value: float | None) -> str | None:
        """Fixa (ou solta, com None) o valor de um campo; devolve o motivo da recusa."""
        if value is None:
            self.fixed.pop(key, None)
        else:
            error = self.check(key, value)
            if error:
                return error
            self.fixed[key] = value
        if self.cursor is not None:
            self.move(self.cursor, self.mods)
        return None

    def release_fixed(self) -> None:
        self.fixed.clear()
        if self.cursor is not None:
            self.move(self.cursor, self.mods)

    def confirm(self) -> bool:
        """Enter no quadro: confirma o ponto como um clique (spec/ui 07 §2.2)."""
        if not self.fields():
            return False
        if self.cursor is None:
            self.cursor = (0.0, 0.0)
        self.press(self.cursor, self.mods)
        self.fixed.clear()
        return True

    def numeric(self, value: float) -> bool:
        """Número digitado sem Tab: fixa o primeiro campo e confirma."""
        fields = self.fields()
        if not fields:
            return False
        error = self.fix(fields[0].key, value)
        if error:
            self.session.message(error, "recusa")
            return True
        return self.confirm()

    def move(self, p: Point, mods: Mods) -> None:
        self.cursor = p
        self.mods = mods

    def press(self, p: Point, mods: Mods, button: str = "left") -> None:
        pass

    def release(self, p: Point, mods: Mods) -> None:
        pass

    def double(self, p: Point, mods: Mods) -> None:
        pass

    def key(self, key: str) -> bool:
        """Tecla da ferramenta (``enter``, ``tab``); devolve se foi usada."""
        return False

    def transform_fn(self):
        """Transformação 2D que a ferramenta aplicaria agora à seleção (fantasma no 3D,
        spec/ui 07 §3.3), ou None."""

    def cancel(self) -> bool:
        """Esc: descarta o que estiver em andamento; devolve se havia algo."""
        return False


# --- Selecionar (0.1 §5.1; 0.2 §3, §4) ---------------------------------------------------


def _band_marks_of(ctx: PlanContext, tx, style="preview") -> list[Mark]:
    """Paredes da transação na forma nova (operações ``wall.edit`` com caminho)."""
    bands = {w.gid: w for w in ctx.walls}
    marks = []
    for op in tx.ops:
        if op.op == "wall.edit" and "path" in (op.after or {}) and op.id in bands:
            w = bands[op.id]
            try:
                marks.append(_band_mark(geom2d.path_from_dict(op.after["path"]), w.ymin,
                                        w.ymax, style))
            except ValueError:
                continue
    return marks


def moving_shapes(ctx: PlanContext, gids) -> list[plan.Shape]:
    """Desenho da seleção na planta, com as portas das paredes selecionadas."""
    selected = set(gids)
    doc = ctx.session.doc
    out = [s for s in ctx.plan.shapes if s.owner in selected and s.role != "below"]
    for owner, shapes in sorted(ctx.plan.owners("door").items()):
        if owner in selected:
            continue
        host = transform.host_wall(doc.get(owner))
        if host is not None and host.GlobalId in selected:
            out += shapes
    return out


def _shape_marks(shapes, fn, style="preview") -> list[Mark]:
    return [Mark(tuple(fn(q) for q in s.points), s.closed, style) for s in shapes]


def _handle_points(w: snap.WallPath) -> list[tuple[str, Point]]:
    return [("start", w.path.start), ("end", w.path.end), ("mid", w.middle())]


class SelectTool(Tool):
    name, label = "select", "Selecionar"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.drag: dict | None = None

    def hint(self) -> str:
        d = self.drag
        if d and d["kind"] == "door" and d["active"]:
            return "Solte sobre uma parede reta para posicionar a porta (Esc cancela)"
        if d and d["kind"] == "handle":
            return ("Leve a alça e clique ou solte; Ctrl ao soltar leva as vizinhas da "
                    "ponta; digite um número para a medida; Esc cancela")
        if d and d["kind"] == "window":
            return ("Janela: para a direita, só elementos inteiros; para a esquerda, também "
                    "os que tocam; Ctrl soma à seleção")
        if d and d["kind"] == "move" and d["active"]:
            return "Solte para mover a seleção (Esc cancela)"
        return ("Clique para selecionar; Ctrl+clique soma; arraste no vazio para selecionar "
                "por janela; arraste as alças ou a seleção para editar")

    def wants_number(self) -> bool:
        return bool(self.drag and self.drag["kind"] == "handle" and self.drag["active"])

    # alças (§4)

    def _selected_walls(self) -> list[snap.WallPath]:
        selection = self.session.selection
        return [w for w in self.ctx.walls if w.gid in selection]

    def _door_handles(self) -> list[tuple]:
        """Alças nas bordas do vão da porta selecionada sozinha (spec/ui 05 §4)."""
        selection = self.session.selection
        if len(selection) != 1:
            return []
        door = self.session.doc.find(next(iter(selection)))
        opening = fc.opening_of(door) if door is not None and door.is_a("IfcDoor") else None
        host = openings.host(opening) if opening is not None else None
        wall = next((w for w in self.ctx.walls if host and w.gid == host.GlobalId), None)
        if wall is None or not wall.straight:
            return []
        o = openings.read_state(opening)
        y = (wall.ymin + wall.ymax) / 2
        return [(wall, "door_start", wall.frame.to_global((o["distance"], y)), door.GlobalId),
                (wall, "door_end", wall.frame.to_global((o["distance"] + o["width"], y)),
                 door.GlobalId)]

    def _all_handles(self) -> list[tuple]:
        """(parede, alça, ponto, porta) de todas as alças visíveis."""
        return [(w, which, q, None) for w in self._selected_walls()
                for which, q in _handle_points(w)] + self._door_handles()

    def _handle_at(self, p: Point) -> dict | None:
        found = [(math.dist(p, q), which == "mid", w.gid, which, w, door)
                 for w, which, q, door in self._all_handles() if math.dist(p, q) <= self.ctx.tol]
        if not found:
            return None
        *_, which, w, door = min(found, key=lambda f: (f[1], f[0], f[2], f[3]))
        return {"wall": w, "which": which, "door": door}

    def handles(self):
        hot = None
        if self.drag and self.drag["kind"] == "handle":
            hot = (self.drag["wall"].gid, self.drag["which"])
        elif self.cursor is not None and not self.drag:
            h = self._handle_at(self.cursor)
            hot = (h["wall"].gid, h["which"]) if h else None
        return [(q, hot == (w.gid, which)) for w, which, q, _ in self._all_handles()]

    def _door_resize(self, distance: float, width: float):
        """Porta com o vão de ``distance`` a ``distance + width`` (alça da porta)."""
        d = self.drag
        doc, door = self.session.doc, d["door"]
        d["want"] = (distance, width)

        def build():
            if width < 0.10:
                raise OpError("largura do vão pequena demais")
            return fc.edit_door(doc, door, width=width, distance=distance)

        at = d["wall"].frame.to_global((distance + width / 2, d["wall"].ymax + 0.15))
        return build, at, f"{fmt(width)} m"

    def _handle_build(self, p: Point, mods: Mods):
        """(função que monta a transação, ponto do rótulo, texto) para a alça em ``p``."""
        d = self.drag
        w, which, doc = d["wall"], d["which"], self.session.doc
        # Ponta: só esta parede; Ctrl leva as vizinhas (decisão de 2026-10-15, spec/ui 08
        # §2). Meio: as vizinhas acompanham; Ctrl solta (spec/ui 02 §4.2).
        carry = mods.ctrl if which in ("start", "end") else not mods.ctrl
        if which.startswith("door"):
            self.snapped = self.ctx.snap(p, Mods(alt=mods.alt))
            along = w.frame.to_local(self.snapped.point)[0]
            o = d["opening"]
            if which == "door_end":
                return self._door_resize(o["distance"], along - o["distance"])
            return self._door_resize(along, o["distance"] + o["width"] - along)
        if which in ("start", "end"):
            fixed = w.path.end if which == "start" else w.path.start
            self.snapped = self.ctx.snap(p, mods, fixed)
            q = self.snapped.point
            return (lambda: cmd.move_wall_end(doc, w.gid, which, q, carry=carry), q,
                    f"{fmt(math.dist(fixed, q))} m")
        self.snapped = self.ctx.snap(p, Mods(alt=mods.alt))
        q = self.snapped.point
        if w.straight:
            offset = w.frame.to_local(q)[1]
            return (lambda: cmd.offset_wall(doc, w.gid, offset, carry=carry), q,
                    f"{fmt(abs(offset))} m")
        return lambda: cmd.bend_arc_wall(doc, w.gid, q), q, ""

    def _handle_update(self, p: Point, mods: Mods) -> None:
        d = self.drag
        build, at, text = self._handle_build(p, mods)
        try:
            d["tx"], d["error"] = build(), None
            d["marks"] = _band_marks_of(self.ctx, d["tx"])
        except OpError as e:
            w = d["wall"]
            d["tx"], d["error"] = None, str(e)
            d["marks"] = [_band_mark(w.path, w.ymin, w.ymax, "invalid")]
        if d["which"].startswith("door"):
            d["marks"] = self._door_marks("invalid" if d["error"] else "preview")
        d["labels"] = [(at, text)] if text else []

    def _door_marks(self, style: str) -> list[Mark]:
        """Pré-visualização da porta com o vão novo (alça da porta)."""
        d = self.drag
        distance, width = d["want"]
        door = self.session.doc.get(d["door"])
        state = doors.read_state(door)
        tstate = (door_types.read(self.session.doc.get(state["type"]))
                  if state["foreign"] is None else
                  {**door_types.default_state("NOTDEFINED"),
                   "lining": {"thickness": 0, "depth": None}})
        return door_marks(self.session.doc, d["wall"], distance, max(width, 0.01), tstate,
                          state["opens_to"], state["align"], state["offset"], style)

    def _handle_commit(self) -> None:
        d, self.drag = self.drag, None
        self.snapped = None
        if d["error"]:
            self.session.message(d["error"], "recusa")
        elif d["tx"] is not None:
            self.session.run(d["tx"])

    def numeric(self, value):
        d = self.drag
        if not self.wants_number():
            return False
        w, which, doc = d["wall"], d["which"], self.session.doc
        cursor = self.snapped.point if self.snapped else self.cursor
        if which.startswith("door"):
            o = d["opening"]
            distance = o["distance"] if which == "door_end" else (
                o["distance"] + o["width"] - value)
            build, _, _ = self._door_resize(distance, value)
            self.drag = None
            try:
                tx = build()
            except OpError as e:
                self.session.message(str(e), "recusa")
                return True
            self.session.run(tx)
            return True
        if which in ("start", "end"):
            fixed = w.path.end if which == "start" else w.path.start
            moving = w.path.start if which == "start" else w.path.end
            target = cursor if cursor and math.dist(cursor, fixed) > 1e-9 else moving
            dx, dy = target[0] - fixed[0], target[1] - fixed[1]
            length = math.hypot(dx, dy)
            q = (fixed[0] + value * dx / length, fixed[1] + value * dy / length)
            build = lambda: cmd.move_wall_end(doc, w.gid, which, q, carry=False)
        elif w.straight:
            side = -1.0 if cursor and w.frame.to_local(cursor)[1] < 0 else 1.0
            build = lambda: cmd.offset_wall(doc, w.gid, side * value)
        else:
            return False
        self.drag = None
        self.session.run(build)
        return True

    # mouse

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        d = self.drag
        if d and d["kind"] == "handle":  # alça presa ao cursor (clique, mover, clique)
            self._handle_update(p, mods)
            self._handle_commit()
            return
        handle = None if mods.ctrl else self._handle_at(p)
        if handle:
            self.drag = {"kind": "handle", **handle, "start": p, "active": False,
                         "sticky": False, "tx": None, "error": None, "marks": [],
                         "labels": []}
            if handle["door"]:
                door = self.session.doc.get(handle["door"])
                self.drag["opening"] = openings.read_state(fc.opening_of(door))
            return
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        selection = self.session.selection
        entity = self.session.doc.find(gid) if gid else None
        is_door = entity is not None and entity.is_a("IfcDoor")
        if gid and not mods.ctrl and gid in selection:
            if is_door and len(selection) == 1:
                self.drag = {"kind": "door", "door": gid, "start": p, "active": False,
                             "target": None}
            else:
                base = self.ctx.snap(p, Mods(alt=mods.alt)).point
                self.drag = {"kind": "move", "gid": gid, "start": p, "base": base,
                             "active": False, "vector": None,
                             "shapes": moving_shapes(self.ctx, selection)}
            return
        if gid and not mods.ctrl and is_door:
            self.session.select([gid])
            self.drag = {"kind": "door", "door": gid, "start": p, "active": False,
                         "target": None}
            return
        self.drag = {"kind": "pending", "gid": gid, "start": p, "ctrl": mods.ctrl}

    def move(self, p, mods):
        super().move(p, mods)
        d = self.drag
        if not d:
            self.snapped = None
            return
        moved = math.dist(p, d["start"]) >= self.ctx.tol * DRAG_START
        kind = d["kind"]
        if kind == "pending":
            if moved:
                self.drag = {"kind": "window", "start": d["start"], "end": p,
                             "ctrl": d["ctrl"]}
            return
        if kind == "window":
            d["end"] = p
            return
        if kind == "handle":
            d["active"] = d["active"] or moved
            if d["active"]:
                self._handle_update(p, mods)
            return
        if not d["active"] and not moved:
            return
        d["active"] = True
        if kind == "door":
            door = self.session.doc.find(d["door"])
            d["target"] = _door_target(self.ctx, door, p)
        else:
            self.snapped = self.ctx.snap(p, mods, d["base"])
            q, base = self.snapped.point, d["base"]
            d["vector"] = (q[0] - base[0], q[1] - base[1])

    def release(self, p, mods):
        d = self.drag
        if not d:
            return
        kind = d["kind"]
        if kind == "handle":
            if not d["active"]:  # clique sem arrastar: a alça segue o cursor
                d["active"] = d["sticky"] = True
                return
            if not d["sticky"]:
                self._handle_update(p, mods)
                self._handle_commit()
            return
        self.drag = None
        self.snapped = None
        selection = self.session.selection
        if kind == "pending":
            if d["gid"] or not d["ctrl"]:
                self.session.select([d["gid"]] if d["gid"] else [], add=d["ctrl"])
            return
        if kind == "window":
            a, b = d["start"], d["end"]
            gids = self.ctx.plan.in_rect(a, b, crossing=b[0] < a[0])
            if d["ctrl"]:
                self.session.select(set(gids) - selection, add=True)
            else:
                self.session.select(gids)
            return
        if not d["active"]:
            if kind == "move":
                self.session.select([d["gid"]])
            return
        if kind == "door":
            target = d["target"]
            if target is None:
                return
            if target.get("error"):
                self.session.message(target["error"], "recusa")
                return
            door = self.session.doc.find(d["door"])
            self.session.run(lambda: fc.edit_door(self.session.doc, door,
                                                  wall=target["wall"],
                                                  distance=target["distance"]))
        elif kind == "move" and d["vector"] and math.hypot(*d["vector"]) > 1e-9:
            doc, gids, vector = self.session.doc, sorted(selection), d["vector"]
            self.session.run(lambda: transform.move_elements(doc, gids, vector))

    def cancel(self):
        if self.drag:
            self.drag = None
            self.snapped = None
            return True
        return False

    def preview(self):
        d = self.drag
        if not d:
            return []
        if d["kind"] == "door":
            return d["target"]["marks"] if d.get("target") else []
        if d["kind"] == "handle":
            return d["marks"] if d["active"] else []
        if d["kind"] == "window":
            (x0, y0), (x1, y1) = d["start"], d["end"]
            return [Mark(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), True,
                         "crossing" if x1 < x0 else "window")]
        if d["kind"] == "move" and d["active"] and d["vector"]:
            return _shape_marks(d["shapes"], geom2d.translation(d["vector"]))
        return []

    def labels(self):
        d = self.drag
        if not d:
            return []
        if d["kind"] == "door":
            return d["target"]["labels"] if d.get("target") else []
        if d["kind"] == "handle":
            return d["labels"] if d["active"] else []
        if d["kind"] == "move" and d["active"] and d["vector"] and self.snapped:
            return [(self.snapped.point, f"{fmt(math.hypot(*d['vector']))} m")]
        return []


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


def _guide(origin: Point, angle: float, tol: float) -> Mark:
    """Linha de guia do ângulo fixado (spec/ui 07 §2.3), longa para os dois lados."""
    reach = max(tol, 0.01) * 200
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return Mark(((origin[0] - reach * ux, origin[1] - reach * uy),
                 (origin[0] + reach * ux, origin[1] + reach * uy)), False, "guide")


class _WallTool(Tool):
    def __init__(self, ctx, options: _WallOptions | None = None):
        super().__init__(ctx)
        self.options = options or _WallOptions(ctx.session)
        self.points: list[Point] = []

    def _point(self, p, mods) -> Point:
        origin = self.points[-1] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin, extra=self.points)
        if self.points and self.fixed:
            self.snapped = snap.Snap(self._resolve(self.snapped.point), "free")
        return self.snapped.point

    def _resolve(self, q: Point) -> Point:
        """Ponto com os valores fixados nos campos (spec/ui 07 §2.3)."""
        return q

    def move(self, p, mods):
        super().move(p, mods)
        self._point(p, mods)

    def cancel(self):
        self.fixed.clear()
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
        return ("Clique o próximo ponto; Tab digita comprimento e ângulo; Enter, clique duplo "
                "ou botão direito encerra; Esc descarta")

    def fields(self):
        if not self.points:
            return []
        last = self.points[-1]
        q = self.snapped.point if self.snapped else None
        length = math.dist(last, q) if q else None
        angle = _degrees(q[0] - last[0], q[1] - last[1]) if q and length > 1e-9 else None
        return [Field("length", "Comprimento", "m", length, self.fixed.get("length")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def check(self, key, value):
        if key == "length" and value <= geom2d.MIN_LENGTH:
            return "comprimento pequeno demais"
        return None

    def _resolve(self, q):
        return polar_point(self.points[-1], q, self.fixed.get("length"), self.fixed.get("angle"))

    def press(self, p, mods, button="left"):
        if button == "right":
            self.finish()
            return
        q = self._point(p, mods)
        self.fixed.clear()
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
        if self.points and "angle" in self.fixed:
            marks.append(_guide(self.points[-1], self.fixed["angle"], self.ctx.tol))
        return marks


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
        return ("Clique o primeiro canto" if not self.points else
                "Clique o canto oposto; Tab digita largura e altura")

    def fields(self):
        if not self.points:
            return []
        a = self.points[0]
        q = self.snapped.point if self.snapped else None
        return [Field("width", "Largura", "m", abs(q[0] - a[0]) if q else None,
                      self.fixed.get("width")),
                Field("height", "Altura", "m", abs(q[1] - a[1]) if q else None,
                      self.fixed.get("height"))]

    def check(self, key, value):
        if value < geom2d.MIN_LENGTH:
            return "o retângulo precisa de largura e profundidade"
        return None

    def _resolve(self, q):
        return rect_corner(self.points[0], q, self.fixed.get("width"), self.fixed.get("height"))

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self._point(p, mods)
        self.fixed.clear()
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


# --- dividir (0.2 §5) -----------------------------------------------------------------------


class SplitTool(Tool):
    name, label = "split", "Dividir"
    number_hint = "distância ao início"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.target: dict | None = None
        self.only: set[str] | None = None  # pela mini-barra: só a parede selecionada

    def hint(self):
        which = "a parede selecionada" if self.only else "uma parede"
        return (f"Clique sobre {which} para dividi-la; digite um número para a distância ao "
                "início")

    def cancel(self):
        self.only = None
        return super().cancel()

    def fields(self):
        if self.target is None:
            return []
        return [Field("distance", "Distância", "m", self.target["along"],
                      self.fixed.get("distance"))]

    def check(self, key, value):
        wall = self._target_wall()
        if wall is not None and not 0 < value < wall.path.length:
            return "a distância deve ficar dentro da parede"
        return None

    def _target_wall(self) -> snap.WallPath | None:
        if self.target is None:
            return None
        return next((w for w in self.ctx.walls if w.gid == self.target["wall"]), None)

    def confirm(self):
        if self.target is None:
            return False
        value = self.fixed.get("distance")
        self.fixed.clear()
        if value is None:
            self._commit()
            return True
        return self._at_distance(value)

    def _aim(self, wall: snap.WallPath, q: Point) -> None:
        _, along, _ = wall.project(q)
        path = wall.path
        t = along if wall.straight else along / path.radius
        point = wall.frame.to_global(path.point(0.0, t))
        error = None
        try:
            cmd.split_wall(self.session.doc, wall.gid, point)
        except OpError as e:
            error = str(e)
        style = "invalid" if error else "preview"
        cross = tuple(wall.frame.to_global(path.point(y, t))
                      for y in (wall.ymin - 0.15, wall.ymax + 0.15))
        y = wall.ymax + 0.25
        self.target = {
            "wall": wall.gid, "point": point, "error": error, "along": along,
            "marks": [Mark(cross, False, style)],
            "labels": [(wall.frame.to_global(path.point(y, t / 2)), fmt(along)),
                       (wall.frame.to_global(path.point(y, (t + path.t_end) / 2)),
                        fmt(path.length - along))],
        }

    def move(self, p, mods):
        super().move(p, mods)
        self.target = None
        walls = [w for w in self.ctx.walls if self.only is None or w.gid in self.only]
        hit = snap.wall_at(walls, p, self.ctx.tol)
        if hit is None:
            self.snapped = None
            return
        s = self.ctx.snap(p, mods)
        q, _, _ = hit.wall.project(s.point)
        self.snapped = snap.Snap(q, s.kind if s.wall == hit.wall.gid else "path", hit.wall.gid)
        distance = self.fixed.get("distance")
        if distance is not None and 0 < distance < hit.wall.path.length:
            path = hit.wall.path
            t = distance if hit.wall.straight else distance / path.radius
            q = hit.wall.frame.to_global(path.point(0.0, t))
            self.snapped = snap.Snap(q, "free", hit.wall.gid)
        self._aim(hit.wall, q)

    def _commit(self) -> None:
        target = self.target
        if target is None:
            self.session.message("clique sobre uma parede", "recusa")
        elif target["error"]:
            self.session.message(target["error"], "recusa")
        else:
            doc = self.session.doc
            if self.session.run(lambda: cmd.split_wall(doc, target["wall"], target["point"]))                     and self.only is not None:
                self.only = None
                self.finished = True
        self.target = None

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        self._commit()

    def numeric(self, value):
        return self._at_distance(value)

    def _at_distance(self, value: float) -> bool:
        wall = self._target_wall()
        if wall is None:
            return False
        path = wall.path
        if not 0 < value < path.length:
            self.session.message("a distância deve ficar dentro da parede", "recusa")
            return True
        t = value if wall.straight else value / path.radius
        self._aim(wall, wall.frame.to_global(path.point(0.0, t)))
        self._commit()
        return True

    def preview(self):
        return self.target["marks"] if self.target else []

    def labels(self):
        return self.target["labels"] if self.target else []


# --- mover, copiar, girar (0.2 §6) ---------------------------------------------------------


class _SelectionTool(Tool):
    """Ferramenta que age sobre a seleção a partir de pontos clicados."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.points: list[Point] = []

    def _gids(self) -> list[str]:
        return sorted(self.session.selection)

    def _point(self, p, mods) -> Point:
        origin = self.points[-1] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin)
        if self.points and self.fixed:
            self.snapped = snap.Snap(self._resolve(self.snapped.point), "free")
        return self.snapped.point

    def _resolve(self, q: Point) -> Point:
        """Ponto com os valores fixados nos campos (spec/ui 07 §2.3)."""
        return polar_point(self.points[0], q, self.fixed.get("distance"),
                           self.fixed.get("angle"))

    def move(self, p, mods):
        super().move(p, mods)
        self._point(p, mods)

    def cancel(self):
        self.fixed.clear()
        if self.points:
            self.points = []
            return True
        return False

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        if not self.session.selection:
            self.session.message("selecione os elementos antes", "recusa")
            return
        q = self._point(p, mods)
        self.fixed.clear()
        self.click(q, mods)

    def click(self, q: Point, mods: Mods) -> None:
        raise NotImplementedError

    def _shapes(self) -> list[plan.Shape]:
        return moving_shapes(self.ctx, self._gids())


class MoveTool(_SelectionTool):
    name, label = "move", "Mover"
    number_hint = "distância"
    copies = False

    def hint(self):
        if not self.session.selection:
            return "Selecione os elementos antes de usar esta ferramenta"
        if not self.points:
            return "Clique o ponto de base"
        if self.copies:
            return ("Clique o destino de cada cópia; Tab digita distância e ângulo; "
                    "Esc termina")
        return "Clique o destino; Tab digita distância e ângulo; Esc cancela"

    def fields(self):
        if not self.points:
            return []
        v = self._vector(self.snapped.point) if self.snapped else None
        length = math.hypot(*v) if v else None
        angle = _degrees(*v) if v and length > 1e-9 else None
        return [Field("distance", "Distância", "m", length, self.fixed.get("distance")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def check(self, key, value):
        if key == "distance" and value <= 1e-9:
            return "a distância deve ser maior que zero"
        return None

    def _vector(self, q: Point) -> Point:
        base = self.points[0]
        return (q[0] - base[0], q[1] - base[1])

    def _apply(self, vector: Point) -> None:
        doc, gids = self.session.doc, self._gids()
        if self.copies:
            self.session.run(lambda: transform.copy_elements(doc, gids, vector))
            return
        self.session.run(lambda: transform.move_elements(doc, gids, vector))
        self.points = []
        self.finished = True

    def click(self, q, mods):
        if not self.points:
            self.points = [q]
            return
        vector = self._vector(q)
        if math.hypot(*vector) > 1e-9:
            self._apply(vector)

    def transform_fn(self):
        if not self.points or not self.snapped:
            return None
        return geom2d.translation(self._vector(self.snapped.point))

    def preview(self):
        fn = self.transform_fn()
        if fn is None:
            return []
        marks = [Mark((self.points[0], self.snapped.point), False)]
        if "angle" in self.fixed:
            marks.append(_guide(self.points[0], self.fixed["angle"], self.ctx.tol))
        return marks + _shape_marks(self._shapes(), fn)


class CopyTool(MoveTool):
    name, label = "copy", "Copiar"
    copies = True


class RotateTool(_SelectionTool):
    name, label = "rotate", "Girar"
    number_hint = "ângulo (graus)"
    STEP = 15.0  # Shift: múltiplos de 15°

    def __init__(self, ctx):
        super().__init__(ctx)
        self.shift = False

    def hint(self):
        if not self.session.selection:
            return "Selecione os elementos antes de usar esta ferramenta"
        return ["Clique o centro do giro",
                "Clique um ponto da direção de referência, ou Tab para digitar o ângulo",
                "Clique a direção final (Shift: múltiplos de 15°) ou digite o ângulo"][
            len(self.points)]

    def _point(self, p, mods) -> Point:
        self.shift = mods.shift
        self.snapped = self.ctx.snap(p, Mods(alt=mods.alt))
        return self.snapped.point

    def fields(self):
        if not self.points:
            return []
        angle = None
        if len(self.points) == 2 and self.snapped:
            raw = self._cursor_angle(self.snapped.point)
            angle = math.degrees(raw) if raw is not None else None
        return [Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def _cursor_angle(self, q: Point) -> float | None:
        c, r = self.points
        if math.dist(q, c) < 1e-9:
            return None
        angle = (math.atan2(q[1] - c[1], q[0] - c[0]) - math.atan2(r[1] - c[1], r[0] - c[0]))
        angle = (angle + math.pi) % (2 * math.pi) - math.pi
        if self.shift:
            step = math.radians(self.STEP)
            angle = round(angle / step) * step
        return angle

    def _angle(self, q: Point) -> float | None:
        if "angle" in self.fixed:
            return math.radians(self.fixed["angle"])
        return self._cursor_angle(q)

    def _apply(self, angle: float) -> None:
        doc, gids, center = self.session.doc, self._gids(), self.points[0]
        self.session.run(lambda: transform.rotate_elements(doc, gids, center, angle))
        self.points = []
        self.finished = True

    def click(self, q, mods):
        if len(self.points) < 2:
            if not self.points or math.dist(q, self.points[0]) > geom2d.MIN_LENGTH:
                self.points.append(q)
            return
        angle = self._angle(q)
        if angle is not None and abs(angle) > 1e-9:
            self._apply(angle)

    def confirm(self):
        if not self.points:
            return False
        angle = self.fixed.pop("angle", None)
        self.fixed.clear()
        if angle is not None:
            if abs(angle) > 1e-9 and self.session.selection:
                self._apply(math.radians(angle))
            return True
        if len(self.points) == 2 and self.cursor is not None:
            self.press(self.cursor, self.mods)
        return True

    def transform_fn(self):
        if not self.points or not self.snapped:
            return None
        if len(self.points) == 1 and "angle" not in self.fixed:
            return None
        angle = (math.radians(self.fixed["angle"]) if "angle" in self.fixed
                 else self._angle(self.snapped.point))
        return geom2d.rotation(self.points[0], angle) if angle is not None else None

    def preview(self):
        if not self.points or not self.snapped:
            return []
        c = self.points[0]
        fn = self.transform_fn()
        marks = [Mark((c, self.snapped.point if len(self.points) == 1 else self.points[1]),
                      False)]
        return marks + (_shape_marks(self._shapes(), fn) if fn else [])

    def labels(self):
        if len(self.points) < 2 or not self.snapped:
            return []
        angle = self._angle(self.snapped.point)
        if angle is None:
            return []
        return [(self.snapped.point, f"{math.degrees(angle):.1f}°".replace(".", ","))]


class MirrorTool(_SelectionTool):
    """Espelhar pelo eixo de dois pontos (spec/ui 05 §2); Ctrl no 2º clique mantém o
    original."""

    name, label = "mirror", "Espelhar"

    def hint(self):
        if not self.session.selection:
            return "Selecione os elementos antes de usar esta ferramenta"
        if not self.points:
            return "Clique o primeiro ponto do eixo de simetria"
        return ("Clique o segundo ponto do eixo (Shift: múltiplos de 45°; Ctrl mantém o "
                "original; Tab digita o ângulo do eixo); Esc cancela")

    def fields(self):
        if not self.points:
            return []
        a, q = self.points[0], self.snapped.point if self.snapped else None
        angle = (_degrees(q[0] - a[0], q[1] - a[1])
                 if q and math.dist(a, q) > 1e-9 else None)
        return [Field("angle", "Ângulo do eixo", "°", angle, self.fixed.get("angle"))]

    def _resolve(self, q):
        a = self.points[0]
        reach = max(math.dist(a, q), 1.0)
        return polar_point(a, q, reach, self.fixed.get("angle"))

    def click(self, q, mods):
        if not self.points:
            self.points = [q]
            return
        if math.dist(q, self.points[0]) <= geom2d.MIN_LENGTH:
            return
        doc, gids, a = self.session.doc, self._gids(), self.points[0]
        before = {w.GlobalId for w in doc.ifc.by_type("IfcWall")}
        if self.session.run(lambda: transform.mirror_elements(doc, gids, a, q, keep=mods.ctrl)) \
                and mods.ctrl:
            created = {w.GlobalId for w in doc.ifc.by_type("IfcWall")} - before
            self.session.select(created)
        self.points = []
        self.finished = True

    def transform_fn(self):
        if not self.points or not self.snapped:
            return None
        a, b = self.points[0], self.snapped.point
        if math.dist(a, b) <= geom2d.MIN_LENGTH:
            return None
        return geom2d.reflection(a, b)

    def preview(self):
        fn = self.transform_fn()
        if fn is None:
            return []
        return [Mark((self.points[0], self.snapped.point), False),
                *_shape_marks(self._shapes(), fn)]


TOOLS = (SelectTool, WallTool, ArcWallTool, RectangleTool, DoorTool, SplitTool, MoveTool,
         CopyTool, RotateTool, MirrorTool)
# Ferramentas que agem sobre a seleção (mini-barra, spec/ui 03 §5): ao terminar, ou com
# Esc, a vista volta para Selecionar.
SELECTION_TOOLS = ("move", "copy", "rotate", "mirror", "split")


# --- mini-barra da seleção (spec/ui 03 §5) -------------------------------------------------


def selection_actions(doc, gids) -> list[str]:
    """Ações da mini-barra que se aplicam à seleção, na ordem da barra."""
    elements = [doc.find(g) for g in sorted(gids)]
    elements = [e for e in elements if e is not None]
    if not elements:
        return []
    walls = [e for e in elements if e.is_a("IfcWall")]
    door_list = [e for e in elements if e.is_a("IfcDoor")]
    out = ["move", "copy"]
    if walls:
        out += ["rotate", "mirror"]
    if len(elements) == 1 and walls:
        out.append("split")
    if len(walls) == 2 and len(elements) == 2:
        out += _join_actions(doc, *walls)
    if door_list and len(door_list) == len(elements):
        out.append("flip_opening")
        hands = []
        for door in door_list:
            state = doors.read_state(door)
            tstate = (door_types.read(doc.get(state["type"]))
                      if state["type"] and state["foreign"] is None else None)
            hands.append(tstate and params.hand_of(tstate["operation_type"]))
        if all(hands):
            out.append("flip_hinges")
    out.append("delete")
    return out


def _join_actions(doc, a, b) -> list[str]:
    """Junções manuais que se aplicam a duas paredes (spec/ui 05 §7)."""
    out = []
    paths = [geom2d.path_from_dict(cmd.read_state(doc, w)["path"]) for w in (a, b)]
    if all(isinstance(p, geom2d.LinePath) for p in paths):
        lines = [geom2d.line_through(p.start, p.end) for p in paths]
        if geom2d.intersect(*lines):
            out.append("join")
    rels = [r for r in (*a.ConnectedTo, *a.ConnectedFrom)
            if r.is_a("IfcRelConnectsPathElements") and b in (r.RelatingElement,
                                                              r.RelatedElement)]
    if rels:
        out.append("unjoin")
        if any(r.RelatingConnectionType == r.RelatedConnectionType == "ATPATH" for r in rels):
            out.append("swap")
    return out


def bar_position(rect, size, view, gap: float = 12.0) -> tuple[float, float]:
    """Canto superior esquerdo da mini-barra (coordenadas da tela): acima do canto
    superior direito de ``rect`` (x0, y0, x1, y1); se não couber, abaixo do canto
    inferior direito; sempre dentro de ``view`` (largura, altura)."""
    _, y0, x1, y1 = rect
    w, h = size
    vw, vh = view
    x = x1 - w
    y = y0 - gap - h
    if y < 0:
        y = y1 + gap
    return (min(max(x, 0.0), max(vw - w, 0.0)), min(max(y, 0.0), max(vh - h, 0.0)))


@dataclass
class ToolBox:
    """Ferramenta ativa e opções que sobrevivem à troca de ferramenta (§7.1)."""

    ctx: PlanContext
    tools: dict = field(default_factory=dict)
    active: Tool | None = None
    wall_form: str = "wall"  # última forma de parede usada (spec/ui 03 §4.1)

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

    def check_types(self) -> None:
        """Depois de editar os tipos: opção que aponta para tipo excluído volta ao
        primeiro da lista."""
        doc = self.ctx.session.doc
        for tool in self.tools.values():
            holder = tool.options if isinstance(tool, _WallTool) else tool
            ifc_class = "IfcWallType" if isinstance(tool, _WallTool) else "IfcDoorType"
            if not hasattr(holder, "type") or (holder.type and doc.find(holder.type)):
                continue
            types = sorted(doc.ifc.by_type(ifc_class), key=lambda t: t.Name or "")
            holder.type = types[0].GlobalId if types else None

    def activate(self, name: str) -> Tool:
        if self.active is not None:
            self.active.cancel()
        self.active = self.tools[name]
        if name in ("wall", "arc", "rectangle"):
            self.wall_form = name
        return self.active
