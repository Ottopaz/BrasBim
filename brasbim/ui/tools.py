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
import re
from dataclasses import dataclass, field

from brasbim.core import (
    edit_state,
    edits,
    geom2d,
    guides,
    plan,
    selection_area,
    snap,
    storeys,
    transform,
)
from brasbim.core.annotations import base as annotation_base
from brasbim.core.annotations import commands as ac
from brasbim.core.annotations import dimensions as annotation_dims
from brasbim.core.annotations import drafting, drawing2d, spaces
from brasbim.core.document import OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.fillings import door_types, doors, params, window_types
from brasbim.core.geom2d import Point
from brasbim.core.objects import commands as object_cmd
from brasbim.core.objects import elements as objects
from brasbim.core.objects import formula, hosting
from brasbim.core.objects import plan as object_plan
from brasbim.core.objects import types as object_types
from brasbim.core.structure import beams, columns, profiles, roofs, rooms, slab_openings, slabs
from brasbim.core.structure import commands as sc
from brasbim.core.structure import common as structure_common
from brasbim.core.structure import types as st_types
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


_COORDS = re.compile(r"^x\s*([+-]?[\d.,]+)\s*;?\s*y\s*([+-]?[\d.,]+)$", re.IGNORECASE)
_COPIES = re.compile(r"^x\s*(\d+)$", re.IGNORECASE)


def _calc(text: str) -> float:
    """Conta com o analisador das fórmulas dos objetos (nunca ``eval``)."""
    try:
        node = formula.parse(text)
        if formula.infer(node, {}) != formula.NUMBER:
            raise ValueError(f"não é um número: {text!r}")
        return float(formula.evaluate(node, {}))
    except formula.FormulaError as e:
        raise ValueError(f"conta inválida: {text!r} ({e})") from None


def parse_entry(text: str, measured: float | None = None, signed: bool = False):
    """Texto de um campo do quadro de medidas (spec/ui 30 §8, §9): ``("value", número)``,
    ``("point", (x, y))`` para ``x5 y3`` ou ``("copies", n)`` para ``x5``.

    Contas valem (``1,20+0,15``); operador no início ou no fim faz a conta com o valor
    medido (``+0,15``, ``/3``, ``2*``). ``-`` no início só é conta em campo sem sinal
    (``signed`` falso): num ângulo ou numa cota, ``-30`` é o número. ``ValueError`` com o
    motivo."""
    text = text.strip()
    if not text:
        raise ValueError("vazio")
    m = _COORDS.match(text)
    if m:
        return "point", (parse_number(m.group(1)), parse_number(m.group(2)))
    m = _COPIES.match(text)
    if m:
        return "copies", int(m.group(1))
    head, tail = text[0], text[-1]
    before = head in "+*/" or (head == "-" and not signed and len(text) > 1)
    after = not before and tail in "+-*/" and len(text) > 1
    if not before and not after:
        return "value", _calc(text)
    if measured is None:
        raise ValueError("ainda não há medida para a conta")
    if before:
        return "value", _calc(f"({measured:.10f}){head}({text[1:]})")
    return "value", _calc(f"({text[:-1]}){tail}({measured:.10f})")


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
    negative: bool = False  # aceita valor negativo: "-0,15" é o número, não uma conta

    @property
    def signed(self) -> bool:
        return self.negative or self.unit == "°"

    def text(self, value: float | None = None) -> str:
        value = self.value if value is None else value
        if value is None:
            return ""
        if not self.unit:  # contagem
            return str(round(value))
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


# Atração forte: vence a linha-guia (spec/ui 37 §3); as outras cedem a ela.
STRONG_SNAPS = ("end", "inter", "mid", "center", "perp", "tan")
REFERENCE_SNAPS = ("end", "inter", "mid", "center")  # viram ponto de referência (§2)


class PlanContext:
    """Sessão + dados do pavimento ativo que as ferramentas consultam."""

    def __init__(self, session: Session):
        self.session = session
        self.tol = 0.1  # distância de atração em metros (a vista atualiza pela escala)
        self.grid = 0.1
        self.input_view = None  # vista (planta ou 3D) que recebeu o último movimento
        self._plan = None
        self._walls = None
        self._vertices = None
        self._columns = None
        self._grid_points = None
        self.detail = "simple"  # Exibir > Detalhe da planta (spec/ui 06 §2)
        self.show_above = True  # Exibir > Elementos acima do plano de corte (§3.2)
        self.snap_kinds = set(snap.KINDS)  # Exibir > Atração (spec/ui 23 §2.3)
        self.snap_off = False  # Exibir > Atração > Desligar toda a atração
        self.axis_lock: tuple[str, Point] | None = None  # seta: ("x" | "y", origem) (§3.1)
        self.guides_on = True  # Exibir > Atração > Linhas-guia (spec/ui 37 §4)
        self.references: list[Point] = []  # pontos de referência (spec/ui 37 §2)
        self.tracked: guides.Tracked | None = None  # guia em uso no último ``snap``
        self.last_tool: tuple[str, str] | None = None  # (nome, rótulo): Enter repete (§3.2)
        self.last_point: Point | None = None  # último ponto clicado ou digitado (ui/24 §4)
        self.last_origin: Point | None = None  # ponto anterior do último ``snap``
        # Seleção (spec/ui 28): somar cliques (como no CAD) ou trocar a cada clique.
        self.accumulate = True
        self.hover: str | None = None  # elemento realçado sob o cursor
        self.area: selection_area.Area | None = None  # área de seleção (spec/ui 38 §2)
        # Chave Escolher travados (spec/ui 39 §5): desligada, o clique e a janela não pegam
        # os travados; a atração continua.
        self.pick_locked = True
        # Giro da vista da planta (spec/ui 39 §3), em radianos: a grade, as guias, o Shift
        # e as setas seguem a tela.
        self.view_angle = 0.0
        self._index = None

    def invalidate(self) -> None:
        self._plan = self._walls = self._vertices = self._columns = None
        self._grid_points = self._index = None

    def invalidate_grid(self) -> None:
        """A grade girou com a vista (spec/ui 39 §3); o modelo não mudou."""
        self.axis_lock = None

    @property
    def plan(self) -> plan.Plan:
        if self._plan is None:
            storey = self.session.storey
            self._plan = (plan.storey_plan(self.session.doc, storey, detail=self.detail,
                                           show_above=self.show_above)
                          if storey else plan.Plan())
            if not self.pick_locked:
                self._plan.locked |= edit_state.locked_ids(self.session.doc)
        return self._plan

    @property
    def walls(self) -> list[snap.WallPath]:
        if self._walls is None:
            storey = self.session.storey
            self._walls = snap.wall_paths(self.session.doc, storey) if storey else []
        return self._walls

    @property
    def vertices(self) -> list[Point]:
        """Vértices que podem virar ponto de referência (spec/ui 09 §2.1): pontas dos
        caminhos, centros de arco, cantos das paredes (com as junções) e dos vãos."""
        if self._vertices is None:
            found: dict[tuple, Point] = {}

            def add(q):
                found.setdefault((round(q[0], 6), round(q[1], 6)), (float(q[0]), float(q[1])))

            doc = self.session.doc
            for w in self.walls:
                for q in w.ends():
                    add(q)
                if not w.straight:
                    r = w.path.radius if w.path.ccw else -w.path.radius
                    add(w.frame.to_global((0.0, r)))
                wall = doc.find(w.gid)
                for opening in openings.of_wall(wall) if w.straight and wall else []:
                    try:
                        o = openings.read_state(opening)
                    except OpError:
                        continue
                    for x in (o["distance"], o["distance"] + o["width"]):
                        for y in (w.ymin, w.ymax):
                            add(w.frame.to_global((x, y)))
            for s in self.plan.shapes:
                if s.role in ("wall", "wall_view") and s.closed:
                    for q in s.points:
                        add(q)
            self._vertices = list(found.values())
        return self._vertices

    @property
    def column_points(self) -> list[Point]:
        """Cantos e centro dos pilares do pavimento (pontos de atração, spec/ui 10 §2)."""
        if self._columns is None:
            found: list[Point] = []
            for shapes in self.plan.owners("column").values():
                pts = [q for s in shapes if s.closed for q in s.points]
                if pts:
                    found += pts
                    found.append((sum(q[0] for q in pts) / len(pts),
                                  sum(q[1] for q in pts) / len(pts)))
            self._columns = found
        return self._columns

    @property
    def index(self) -> snap.SnapIndex:
        """Arestas e curvas de todos os elementos visíveis (spec/ui 23 §2.1)."""
        if self._index is None:
            storey = self.session.storey
            self._index = (snap.build_index(self.session.doc, storey, self.plan)
                           if storey else snap.SnapIndex())
        return self._index

    def snap(self, p: Point, mods: Mods, origin: Point | None = None,
             extra=()) -> snap.Snap:
        self.last_origin = origin
        self.tracked = None
        lock = self.axis_lock if origin is not None and self.axis_lock else None
        if lock is not None and math.dist(lock[1], origin) > 1e-9:
            lock = self.axis_lock = None  # o ponto anterior mudou: a trava caiu
        if mods.shift and origin is not None and lock is None:
            return snap.Snap(snap.constrain(origin, p, base=self.view_angle), "free")
        if mods.alt or self.snap_off:
            found = snap.Snap(tuple(p), "free")
        else:
            found = snap.snap(self.walls, p, self.tol, self.grid,
                              list(extra) + self.grid_points, self.index, origin,
                              self.snap_kinds, self.view_angle)
            if lock is None and self.guides_on:
                found = self._guide(p, found, origin)
        if lock is None:
            return found
        q = found.point
        a = self.view_angle + (0.0 if lock[0] == "x" else math.pi / 2)
        u = (math.cos(a), math.sin(a))  # eixo da tela travado pela seta
        t = (q[0] - origin[0]) * u[0] + (q[1] - origin[1]) * u[1]
        q = (origin[0] + t * u[0], origin[1] + t * u[1])
        attracted = found.kind not in ("free", "grid")
        return snap.Snap(q, found.kind if attracted else "free", found.wall,
                         found.point if attracted else None)

    def _guide(self, p: Point, found: snap.Snap, origin: Point | None) -> snap.Snap:
        """Linhas-guia (spec/ui 37 §3): ponto atraído forte fica (e mostra as guias que
        passam por ele); senão, guia, cruzamento de guias ou de guia com aresta."""
        turn = math.degrees(self.view_angle)
        lines = guides.guides_from(self.references, origin,
                                   tuple((a + turn) % 180.0 for a in guides.ANGLES))
        if not lines:
            return found
        on_guide = guides.through(found.point, lines, self.tol * 0.02)
        if found.kind in STRONG_SNAPS or (found.kind == "grid" and on_guide):
            self.tracked = on_guide  # o ponto atraído já está alinhado: só mostra a guia
            if found.kind == "grid" and len(on_guide.guides) > 1:
                return snap.Snap(found.point, "inter")  # cruzamento de guias na grade
            return found
        segments = [(s.a, s.b) for s in self.index.segments_near(p, self.tol)]
        self.tracked = guides.track(p, lines, self.tol, segments)
        if self.tracked is None:
            return found
        if not self.tracked.crossing and "grid" in self.snap_kinds and self.grid:
            self.tracked = guides.round_along(self.tracked, self.grid)  # passo da grade
        return snap.Snap(self.tracked.point, "inter" if self.tracked.crossing else "guide")

    def acquire(self, p: Point) -> bool:
        """Cursor parado sobre um ponto (extremidade, interseção, meio, centro): ele vira
        ponto de referência (spec/ui 37 §2). Até ``guides.MAX_REFS``; o mais antigo sai."""
        found = snap.snap(self.walls, p, self.tol, None,
                          self.vertices + self.column_points + self.grid_points, self.index,
                          None, set(REFERENCE_SNAPS) & self.snap_kinds | {"end"})
        if found.kind not in REFERENCE_SNAPS:
            return False
        q = found.point
        if any(math.dist(q, r) < 1e-9 for r in self.references):
            return False
        self.references = (self.references + [q])[-guides.MAX_REFS:]
        return True

    def clear_references(self) -> bool:
        if not self.references:
            return False
        self.references, self.tracked = [], None
        return True

    def guide_marks(self) -> list[Mark]:
        """Um x em cada ponto de referência e as guias em uso, passando do cursor."""
        r = max(self.tol, 0.01) * 0.6
        marks = []
        for x, y in self.references:
            marks += [Mark(((x - r, y - r), (x + r, y + r)), False, "reference"),
                      Mark(((x - r, y + r), (x + r, y - r)), False, "reference")]
        if self.tracked is not None:
            q = self.tracked.point
            for g in self.tracked.guides:
                d = math.dist(g.source, q)
                if d < 1e-9:
                    continue
                ux, uy = (q[0] - g.source[0]) / d, (q[1] - g.source[1]) / d
                reach = d + max(self.tol, 0.01) * 6
                marks.append(Mark((g.source, (g.source[0] + reach * ux,
                                              g.source[1] + reach * uy)), False, "guide"))
        return marks

    def toggle_axis(self, axis: str) -> bool:
        """Seta: trava (ou solta) o eixo a partir do ponto anterior (spec/ui 23 §3.1)."""
        if self.last_origin is None:
            return False
        if self.axis_lock is not None and self.axis_lock[0] == axis:
            self.axis_lock = None
        else:
            self.axis_lock = (axis, self.last_origin)
        return True

    def axis_marks(self) -> list[Mark]:
        if self.axis_lock is None or self.last_origin is None:
            return []
        if math.dist(self.axis_lock[1], self.last_origin) > 1e-9:
            return []
        return [_guide(self.last_origin, 0.0 if self.axis_lock[0] == "x" else 90.0, self.tol)]

    @property
    def grid_points(self) -> list[Point]:
        """Cruzamentos dos eixos de projeto (spec/ui 20 §2): pontos de atração."""
        if self._grid_points is None:
            from brasbim.core import grids

            found = []
            for g in grids.all_grids(self.session.doc):
                try:
                    found += grids.intersections(grids.read_state(g))
                except OpError:
                    continue
            self._grid_points = found
        return self._grid_points


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
        self.tracking: dict | None = None  # guia em uso: origem, dir, ponto, distância

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

    # pontos de referência e linhas-guia (spec/ui 09 §2.1, 37)

    creates = False  # ferramenta de criação: aceita ponto de referência
    guided = False  # aceita ponto de referência sem criar (mover, copiar, girar…)

    @property
    def reference(self) -> Point | None:
        """Ponto de referência em uso: o da guia em que o cursor está, senão o mais novo."""
        if self.tracking is not None:
            return self.tracking["source"]
        t = self.ctx.tracked
        g = t.reference() if t is not None else None
        if g is not None:
            return g.source
        return self.ctx.references[-1] if self.ctx.references else None

    def acquire(self, p: Point | None = None) -> bool:
        """Cursor parado sobre um ponto: ele vira ponto de referência (spec/ui 37 §2)."""
        p = p if p is not None else self.cursor
        if not (self.creates or self.guided) or p is None or not self.ctx.acquire(p):
            return False
        self.tracking = None
        self.fixed.pop("ref", None)
        if self.cursor is not None:
            self.move(self.cursor, self.mods)
        return True

    def release_reference(self) -> bool:
        if not self.ctx.clear_references():
            return False
        self.tracking = None
        self.fixed.pop("ref", None)
        if self.cursor is not None:
            self.move(self.cursor, self.mods)
        return True

    def field_anchor(self) -> Point | None:
        """Onde fica o quadro de medidas (no meio da linha de referência); None = cursor."""
        if self.tracking is None:
            return None
        (x0, y0), (x1, y1) = self.tracking["source"], self.tracking["point"]
        return ((x0 + x1) / 2, (y0 + y1) / 2)

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

    def escape(self) -> bool:
        """Esc da vista; ``cancel`` também vale na troca de ferramenta."""
        return self.cancel()


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


def _object_marks(doc, op, style="preview") -> list[Mark]:
    """Símbolo do objeto com o estado novo de um ``object.edit`` (alça, pré-visualização)."""
    element = doc.find(op.id)
    if element is None:
        return []
    state = {**objects.read_state(doc, element), **(op.after or {})}
    try:
        _, _, built = objects.resolve(doc, state)
        if state["host"] is not None:
            frame = hosting.local_frame(doc, state["host"], built)
            origin, angle = frame["point"], frame["angle"]
        else:
            origin, angle = state["point"], state["angle"]
    except OpError:
        return []
    a = math.radians(angle)
    c, s_ = math.cos(a), math.sin(a)
    k = -1.0 if built.mirror else 1.0
    return [Mark(tuple((origin[0] + c * k * x - s_ * y, origin[1] + s_ * k * x + c * y)
                       for x, y in points), closed, style)
            for points, closed, _ in object_plan.local_symbol(built)]


def _structure_marks(doc, tx, style="preview") -> list[Mark]:
    """Pilares, vigas e lajes da transação na forma nova (operações ``*.edit``)."""
    marks = []
    for op in tx.ops:
        if op.op == "object.edit":
            marks += _object_marks(doc, op, style)
            continue
        prefix, _, kind = op.op.partition(".")
        if op.op == "slab_opening.edit":
            marks.append(Mark(tuple(tuple(q) for q in op.after["outline"]), True, style))
            continue
        if kind != "edit" or prefix not in ("column", "beam", "slab", "roof"):
            continue
        element = doc.find(op.id)
        if element is None:
            continue
        state = {**sc.read_state(doc, element), **(op.after or {})}
        if state["foreign"] is not None:
            continue
        try:
            ring = (columns.outline(doc, state) if prefix == "column" else
                    beams.outline(doc, state) if prefix == "beam" else
                    [tuple(q) for q in state["outline"]])
        except (OpError, ValueError, ZeroDivisionError):
            continue
        marks.append(Mark(tuple(ring), True, style))
    return marks


def moving_shapes(ctx: PlanContext, gids) -> list[plan.Shape]:
    """Desenho da seleção na planta, com as portas das paredes selecionadas."""
    selected = set(gids)
    doc = ctx.session.doc
    for gid in list(selected):
        slab = doc.find(gid)
        if slab is not None and slab.is_a("IfcSlab"):
            selected |= {o.GlobalId for o in slab_openings.of_slab(slab)}
    out = [s for s in ctx.plan.shapes if s.owner in selected and s.role != "below"]
    for owner, shapes in sorted(ctx.plan.owners(("door", "window")).items()):
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


@dataclass(frozen=True)
class _Grip:
    """Dono de uma alça de pilar, viga ou laje (as paredes usam ``snap.WallPath``)."""

    gid: str


def object_handles(doc, element) -> list[tuple[str, Point, Point]]:
    """Alças dos parâmetros de comprimento do objeto (objeto-parametrico.md §5.1):
    (``obj:<parâmetro>``, ponto, direção para fora), na borda da caixa que envolve."""
    from brasbim.core.objects import definition as od

    try:
        state = objects.read_state(doc, element)
        _, tstate, built = objects.resolve(doc, state)
    except OpError:
        return []
    if built.box is None or element.ObjectPlacement is None:
        return []
    storey = doc.find(state["storey"])
    m = object_plan._matrix(storey, element)
    k = -1.0 if built.mirror else 1.0
    x0, x1, y0, y1, _, _ = built.box
    out = []
    for p in od.handle_params(tstate["definition"]):
        axis, side = p["handle"]["axis"], p["handle"]["side"]
        if axis == "z":
            continue
        end = side != "start"
        if axis == "x":
            local, outward = ((x1 if end else x0), (y0 + y1) / 2), ((1.0 if end else -1.0), 0.0)
        else:
            local, outward = ((x0 + x1) / 2, (y1 if end else y0)), (0.0, (1.0 if end else -1.0))
        q = m @ [k * local[0], local[1], 0.0, 1.0]
        d = m @ [k * outward[0], outward[1], 0.0, 0.0]
        out.append((f"obj:{p['name']}", (float(q[0]), float(q[1])),
                    (float(d[0]), float(d[1]))))
    return out


def _structure_handles(doc, gid: str) -> list[tuple[str, Point]]:
    """Alças na planta (spec/ui 10 §4.1): ponto de inserção do pilar, pontas e meio da
    viga, vértices e meio dos lados da laje. Elementos de outra origem não têm alças."""
    element = doc.find(gid)
    if objects.is_object(element):
        return [(which, q) for which, q, _ in object_handles(doc, element)]
    if slab_openings.is_slab_opening(element):
        return _outline_handles(slab_openings.read_state(element)["outline"])
    if element is not None and element.is_a("IfcSpace"):
        state = spaces.read_state(element)
        return _outline_handles(state["outline"]) + [("space_label",
                                                      spaces.label_point(state))]
    if element is not None and annotation_base.kind_of(element) is annotation_dims.DIMENSION:
        state = annotation_base.read_state(element)
        pts = annotation_dims.points(doc, state)
        d, n = annotation_dims.frame(state, pts)
        ts = [(p[0] - pts[0][0]) * d[0] + (p[1] - pts[0][1]) * d[1] for p in pts]
        t, off = (min(ts) + max(ts)) / 2, state["offset"]
        return [("dim_offset", (pts[0][0] + d[0] * t + n[0] * off,
                                pts[0][1] + d[1] * t + n[1] * off))]
    if element is None or not sc.is_structure(element):
        return []
    state = sc.read_state(doc, element)
    if state["foreign"] is not None:
        return []
    if element.is_a("IfcColumn"):
        return [("column", tuple(state["point"]))]
    if element.is_a("IfcBeam"):
        (x0, y0), (x1, y1) = state["start"], state["end"]
        return [("beam_start", (x0, y0)), ("beam_end", (x1, y1)),
                ("beam_mid", ((x0 + x1) / 2, (y0 + y1) / 2))]
    return _outline_handles(state["outline"])


def _outline_handles(outline) -> list[tuple[str, Point]]:
    """Vértices e meio dos lados (laje e abertura na laje)."""
    pts = [tuple(q) for q in outline]
    n = len(pts)
    return ([(f"slab_v{i}", q) for i, q in enumerate(pts)]
            + [(f"slab_e{i}", ((pts[i][0] + pts[(i + 1) % n][0]) / 2,
                               (pts[i][1] + pts[(i + 1) % n][1]) / 2)) for i in range(n)])


def _edge_offset(outline, index: int, q: Point) -> float:
    """Afastamento de ``q`` à reta do lado ``index`` da laje, positivo para fora."""
    a, b = outline[index], outline[(index + 1) % len(outline)]
    length = math.dist(a, b)
    return ((q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0])) / length


class SelectTool(Tool):
    name, label = "select", "Selecionar"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.drag: dict | None = None
        self.drag3d = None  # alça da parede no 3D (handles3d.WallHandle3D, spec/ui 08 §3)
        self.ask_text = None  # clique duplo num texto: pede o texto novo (posto pela janela)

    def double(self, p, mods):
        """Clique duplo num texto edita o texto (spec/ui 13 §6)."""
        doc = self.session.doc
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        element = doc.find(gid) if gid else None
        kind = annotation_base.kind_of(element) if element is not None else None
        if self.ask_text is None or kind not in (drafting.TEXT, drawing2d.LABEL):
            return
        if kind is drawing2d.LABEL and annotation_base.read_state(element)["field"] != "free":
            return  # o rótulo preso mostra o dado do elemento
        self.drag = None
        current = annotation_base.read_state(element)["text"]
        text = self.ask_text(current)
        if text is not None and text.strip() and text != current:
            self.session.run(lambda: ac.edit_element(doc, gid, text=text.strip("\n")))

    def hint(self) -> str:
        if self.drag3d is not None:
            return ("Leve a alça e solte (ou clique); Tab digita a medida; Ctrl ao soltar "
                    "inverte o que acompanha; Esc cancela")
        d = self.drag
        if d and d["kind"] == "door" and d["active"]:
            return "Solte sobre uma parede reta para posicionar a esquadria (Esc cancela)"
        if d and d["kind"] == "handle":
            return ("Leve a alça e clique ou solte; Ctrl ao soltar leva as vizinhas da "
                    "ponta; digite um número para a medida; Esc cancela")
        if d and d["kind"] in ("window", "lasso"):
            name = "Laço" if d["kind"] == "lasso" else "Janela"
            close = "solte" if d["kind"] == "lasso" or not d.get("clicks") else "clique"
            return (f"{name}: para a direita, só elementos inteiros; para a esquerda, "
                    f"também os que tocam; {close} para fechar; Shift tira da seleção; "
                    "Esc cancela")
        if d and d["kind"] == "move" and d["active"]:
            return "Solte para mover a seleção (Esc cancela)"
        if self.ctx.accumulate:
            text = ("Clique soma à seleção; Shift+clique tira; clique no vazio abre a "
                    "janela, arrastar no vazio faz o laço; Esc limpa")
        else:
            text = ("Clique para selecionar; Ctrl+clique soma; arraste no vazio para "
                    "selecionar por janela; arraste as alças ou a seleção para editar")
        if self.ctx.last_tool and not self.session.selection:
            text += f"; Enter: repetir {self.ctx.last_tool[1]}"
        return text

    def key(self, key):
        """Enter sem seleção e sem nada em andamento repete a última ferramenta de
        criação (spec/ui 23 §3.2): ``repeat`` fica com o nome, para a vista ativar."""
        if (key == "enter" and self.ctx.last_tool and self.drag is None
                and self.drag3d is None and not self.session.selection):
            self.repeat = self.ctx.last_tool[0]
            return True
        return False

    repeat: str | None = None

    def wants_number(self) -> bool:
        return self.drag3d is not None or bool(
            self.drag and self.drag["kind"] == "handle" and self.drag["active"])

    # alças no 3D (spec/ui 08 §3): o quadro de medidas fala com o arrasto

    def fields(self):
        return self.drag3d.fields() if self.drag3d is not None else []

    def check(self, key, value):
        return self.drag3d.check(key, value) if self.drag3d is not None else None

    def fix(self, key, value):
        h = self.drag3d
        if h is None:
            return super().fix(key, value)
        if value is None:
            h.fixed.pop(key, None)
        else:
            error = h.check(key, value)
            if error:
                return error
            h.fixed[key] = value
        h.update(ctrl=h.ctrl)
        return None

    def release_fixed(self):
        if self.drag3d is not None:
            self.drag3d.fixed.clear()
            self.drag3d.update(ctrl=self.drag3d.ctrl)
        else:
            super().release_fixed()

    def confirm(self):
        if self.drag3d is None:
            return super().confirm()
        self.commit3d()
        return True

    def commit3d(self) -> None:
        h, self.drag3d = self.drag3d, None
        if h.error:
            self.session.message(h.error, "recusa")
        elif h.tx is not None:
            self.session.run(h.tx)

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
        filling = door is not None and (door.is_a("IfcDoor") or door.is_a("IfcWindow"))
        opening = fc.opening_of(door) if filling else None
        host = openings.host(opening) if opening is not None else None
        wall = next((w for w in self.ctx.walls if host and w.gid == host.GlobalId), None)
        if wall is None or not wall.straight:
            return []
        o = openings.read_state(opening)
        y = (wall.ymin + wall.ymax) / 2
        return [(wall, "door_start", wall.frame.to_global((o["distance"], y)), door.GlobalId),
                (wall, "door_end", wall.frame.to_global((o["distance"] + o["width"], y)),
                 door.GlobalId)]

    def _every_handle(self) -> list[tuple]:
        """(dono, alça, ponto, porta) de todas as alças da seleção: paredes, portas e
        janelas, pilares, vigas e lajes."""
        doc = self.session.doc
        grips = [(_Grip(g), which, q, None) for g in sorted(self.session.selection)
                 for which, q in _structure_handles(doc, g)]
        return [(w, which, q, None) for w in self._selected_walls()
                for which, q in _handle_points(w)] + self._door_handles() + grips

    def _all_handles(self) -> list[tuple]:
        """As alças que se pegam: as dos travados ficam fora (spec/ui 39 §5)."""
        doc = self.session.doc
        return [h for h in self._every_handle()
                if not edit_state.is_locked(doc, h[3] or h[0].gid)]

    def locked_handles(self) -> list[Point]:
        """Alças dos travados escolhidos: desenhadas em cinza, com o cadeado."""
        doc = self.session.doc
        return [q for w, _, q, door in self._every_handle()
                if edit_state.is_locked(doc, door or w.gid)]

    def _refuse_locked(self, gids) -> bool:
        """A interface recusa antes de arrastar, com a mensagem do núcleo (§5)."""
        try:
            edit_state.ensure_unlocked(self.session.doc, gids)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return True
        return False

    def _handle_at(self, p: Point) -> dict | None:
        found = [(math.dist(p, q), which in ("mid", "beam_mid") or which.startswith(
                      "slab_e"), w.gid, which, w, door)
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

    def _object_value(self, gid: str, which: str, p: Point) -> tuple[float, Point]:
        """Valor novo do parâmetro da alça pelo cursor e o ponto do rótulo."""
        from brasbim.core.objects import definition as od

        doc = self.session.doc
        element = doc.get(gid)
        name = which[4:]
        handle = next(h for h in object_handles(doc, element) if h[0] == which)
        _, q, d = handle
        state = objects.read_state(doc, element)
        _, tstate, built = objects.resolve(doc, state)
        current = built.values[name.casefold()]
        delta = (p[0] - q[0]) * d[0] + (p[1] - q[1]) * d[1]
        param = od.param(tstate["definition"], name)
        step = 2.0 if param["handle"]["side"] == "symmetric" else 1.0
        value = current + step * delta
        if self.ctx.grid:
            value = round(value / 0.01) * 0.01  # centímetro
        return value, (q[0] + d[0] * delta, q[1] + d[1] * delta)

    def _structure_build(self, p: Point, mods: Mods):
        """Alça de pilar, viga ou laje (spec/ui 10 §4.1)."""
        d = self.drag
        gid, which, doc = d["wall"].gid, d["which"], self.session.doc
        if which.startswith("obj:"):
            self.snapped = snap.Snap(p, "free")
            value, at = self._object_value(gid, which, p)
            return (lambda: object_cmd.handle_value_ops(doc, gid, which[4:], value), at,
                    f"{fmt(value)} m")
        extra = self.ctx.column_points
        if which in ("beam_start", "beam_end"):
            state = sc.read_state(doc, doc.get(gid))
            fixed = tuple(state["end" if which == "beam_start" else "start"])
            self.snapped = self.ctx.snap(p, mods, fixed, extra=extra)
            q = self.snapped.point
            return (lambda: sc.move_beam_end(doc, gid, which[5:], q), q,
                    f"{fmt(math.dist(fixed, q))} m")
        if which.startswith("slab_e"):
            index = int(which[6:])
            self.snapped = self.ctx.snap(p, Mods(alt=mods.alt))
            offset = _edge_offset(sc.outline_of(doc, gid), index, self.snapped.point)
            return (lambda: sc.offset_slab_edge(doc, gid, index, offset), self.snapped.point,
                    f"{fmt(abs(offset))} m")
        self.snapped = self.ctx.snap(p, mods, extra=extra)
        q = self.snapped.point
        if which.startswith("slab_v"):
            return lambda: sc.move_slab_vertex(doc, gid, int(which[6:]), q), q, ""
        if which == "space_label":
            return lambda: ac.edit_element(doc, gid, label_at=list(q)), q, ""
        if which == "dim_offset":
            state = annotation_base.read_state(doc.get(gid))
            pts = annotation_dims.points(doc, state)
            _, n = annotation_dims.frame(state, pts)
            offset = (q[0] - pts[0][0]) * n[0] + (q[1] - pts[0][1]) * n[1]
            return lambda: ac.edit_element(doc, gid, offset=offset), q, f"{fmt(abs(offset))} m"
        base = dict(_structure_handles(doc, gid))[which]
        vector = (q[0] - base[0], q[1] - base[1])
        return lambda: transform.move_elements(doc, [gid], vector), q, ""

    def _handle_build(self, p: Point, mods: Mods):
        """(função que monta a transação, ponto do rótulo, texto) para a alça em ``p``."""
        d = self.drag
        w, which, doc = d["wall"], d["which"], self.session.doc
        if isinstance(w, _Grip):
            return self._structure_build(p, mods)
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
        doc = self.session.doc
        try:
            d["tx"], d["error"] = build(), None
            d["marks"] = (_band_marks_of(self.ctx, d["tx"])
                          + _structure_marks(doc, d["tx"]))
        except OpError as e:
            w = d["wall"]
            d["tx"], d["error"] = None, str(e)
            d["marks"] = ([] if isinstance(w, _Grip)
                          else [_band_mark(w.path, w.ymin, w.ymax, "invalid")])
        if d["which"].startswith("door"):
            d["marks"] = self._door_marks("invalid" if d["error"] else "preview")
        d["labels"] = [(at, text)] if text else []

    def _door_marks(self, style: str) -> list[Mark]:
        """Pré-visualização da porta com o vão novo (alça da porta)."""
        d = self.drag
        distance, width = d["want"]
        door = self.session.doc.get(d["door"])
        state = doors.read_state(door)
        window, tstate = _filling_tstate(self.session.doc, door)
        return door_marks(self.session.doc, d["wall"], distance, max(width, 0.01), tstate,
                          state["opens_to"], state["align"], state["offset"], style,
                          window, d["opening"]["height"])

    def _handle_commit(self) -> None:
        d, self.drag = self.drag, None
        self.snapped = None
        if d["error"]:
            self.session.message(d["error"], "recusa")
        elif d["tx"] is not None:
            self.session.run(d["tx"])

    def numeric(self, value):
        if self.drag3d is not None:
            return super().numeric(value)
        d = self.drag
        if not self.wants_number():
            return False
        w, which, doc = d["wall"], d["which"], self.session.doc
        cursor = self.snapped.point if self.snapped else self.cursor
        if isinstance(w, _Grip):
            return self._structure_numeric(value, cursor)
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

    def _structure_numeric(self, value: float, cursor: Point | None) -> bool:
        """Medida digitada no arrasto de uma alça: comprimento da viga, afastamento do
        lado da laje."""
        d = self.drag
        gid, which, doc = d["wall"].gid, d["which"], self.session.doc
        if which in ("beam_start", "beam_end"):
            state = sc.read_state(doc, doc.get(gid))
            fixed = state["end" if which == "beam_start" else "start"]
            moving = state["start" if which == "beam_start" else "end"]
            target = cursor if cursor and math.dist(cursor, fixed) > 1e-9 else moving
            dx, dy = target[0] - fixed[0], target[1] - fixed[1]
            n = math.hypot(dx, dy)
            q = (fixed[0] + value * dx / n, fixed[1] + value * dy / n)
            build = lambda: sc.move_beam_end(doc, gid, which[5:], q)
        elif which.startswith("slab_e"):
            index = int(which[6:])
            side = (-1.0 if cursor and _edge_offset(sc.outline_of(doc, gid), index, cursor) < 0
                    else 1.0)
            build = lambda: sc.offset_slab_edge(doc, gid, index, side * value)
        elif which.startswith("obj:"):  # a medida digitada é o valor do parâmetro
            build = lambda: object_cmd.handle_value_ops(doc, gid, which[4:], value)
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
        if d and d["kind"] == "window" and d.get("clicks"):  # 2º clique fecha a janela
            d["end"] = p
            self.drag = None
            self._finish_area(self.ctx.plan.in_rect(d["start"], p, crossing=p[0] <
                                                    d["start"][0]), mods)
            return
        if d and d["kind"] == "handle":  # alça presa ao cursor (clique, mover, clique)
            self._handle_update(p, mods)
            self._handle_commit()
            return
        handle = None if mods.ctrl or mods.shift else self._handle_at(p)
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
        from brasbim.core.structure import skylights

        is_door = entity is not None and (entity.is_a("IfcDoor") or entity.is_a("IfcWindow"))             and not skylights.is_skylight(entity)
        if gid and not mods.ctrl and not mods.shift and gid in selection:
            if is_door and len(selection) == 1:
                self.drag = {"kind": "door", "door": gid, "start": p, "active": False,
                             "target": None}
            else:
                base = self.ctx.snap(p, Mods(alt=mods.alt)).point
                self.drag = {"kind": "move", "gid": gid, "start": p, "base": base,
                             "active": False, "vector": None,
                             "shapes": moving_shapes(self.ctx, selection)}
            return
        if gid and not mods.ctrl and not mods.shift and is_door:
            self.session.select([gid], add=self.ctx.accumulate)
            self.drag = {"kind": "door", "door": gid, "start": p, "active": False,
                         "target": None}
            return
        self.drag = {"kind": "pending", "gid": gid, "start": p, "ctrl": mods.ctrl,
                     "shift": mods.shift}

    def move(self, p, mods):
        super().move(p, mods)
        d = self.drag
        if not d:
            self.snapped = None
            hover = self.ctx.plan.pick(p, self.ctx.tol) if self.ctx.accumulate else None
            self.ctx.hover = hover  # destaque sob o cursor (spec/ui 28 §2)
            return
        self.ctx.hover = None
        moved = math.dist(p, d["start"]) >= self.ctx.tol * DRAG_START
        kind = d["kind"]
        if kind == "pending":
            if moved and d["gid"] is None and self.ctx.accumulate:  # laço (spec/ui 28)
                self.drag = {"kind": "lasso", "start": d["start"], "points": [d["start"], p],
                             "crossing": p[0] < d["start"][0], "shift": d["shift"],
                             "ctrl": d["ctrl"]}
            elif moved and (d["gid"] is None or not self.ctx.accumulate):
                self.drag = {"kind": "window", "start": d["start"], "end": p,
                             "ctrl": d["ctrl"], "shift": d["shift"]}
            return
        if kind == "window":
            d["end"] = p
            return
        if kind == "lasso":
            if math.dist(p, d["points"][-1]) >= self.ctx.tol * 0.5:
                d["points"].append(p)
            return
        if kind == "handle":
            d["active"] = d["active"] or moved
            if d["active"]:
                self._handle_update(p, mods)
            return
        if not d["active"] and not moved:
            return
        if not d["active"] and self._refuse_locked(
                [d["door"]] if kind == "door" else sorted(self.session.selection)):
            self.drag = None  # o travado não sai do lugar (spec/ui 39 §5)
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
            if not self.ctx.accumulate:
                if d["gid"] or not d["ctrl"]:
                    self.session.select([d["gid"]] if d["gid"] else [], add=d["ctrl"])
                return
            if d["gid"] is None:  # clique no vazio: a janela segue o cursor (2 cliques)
                self.drag = {"kind": "window", "start": d["start"], "end": p,
                             "clicks": True, "ctrl": d["ctrl"], "shift": d["shift"]}
                return
            if d["shift"]:
                self.session.select(selection - {d["gid"]})
            else:
                self.session.select([d["gid"]], add=True)
            return
        if kind == "window":
            a, b = d["start"], d["end"]
            self._finish_area(self.ctx.plan.in_rect(a, b, crossing=b[0] < a[0]),
                              Mods(shift=d.get("shift", False) or mods.shift,
                                   ctrl=d["ctrl"]))
            return
        if kind == "lasso":
            self._finish_area(self.ctx.plan.in_polygon(d["points"], crossing=d["crossing"]),
                              Mods(shift=d["shift"] or mods.shift, ctrl=d["ctrl"]))
            return
        if not d["active"]:
            if kind == "move" and not self.ctx.accumulate:
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

    def _finish_area(self, gids, mods) -> None:
        """Fim da janela ou do laço (spec/ui 28 §2): soma, tira (Shift) ou, no modo
        antigo, troca a seleção (Ctrl soma)."""
        selection = self.session.selection
        if mods.shift:
            self.session.select(selection - set(gids))
        elif self.ctx.accumulate or mods.ctrl:
            self.session.select(set(gids) - selection, add=True)
        else:
            self.session.select(gids)

    def cancel(self):
        if self.drag or self.drag3d is not None:
            self.drag = self.drag3d = None
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
        if d["kind"] == "lasso":
            return [Mark(tuple(d["points"]), True,
                         "crossing" if d["crossing"] else "window")]
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

    type_class = "IfcWallType"

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
    options_class = _WallOptions

    def __init__(self, ctx, options=None):
        super().__init__(ctx)
        self.options = options or self.options_class(ctx.session)
        self.points: list[Point] = []

    creates = True

    def _extra(self) -> list[Point]:
        """Pontos de atração além dos das paredes."""
        return list(self.points)

    def _point(self, p, mods) -> Point:
        origin = self.points[-1] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin, extra=self._extra())
        tracked = self._track(p)
        if tracked is not None:
            if math.dist(tracked, self.snapped.point) > 1e-9:
                self.snapped = snap.Snap(tracked, "free")
        elif self.points and self.fixed:
            self.snapped = snap.Snap(self._resolve(self.snapped.point), "free")
        return self.snapped.point

    def _track(self, p: Point) -> Point | None:
        """Ponto na guia de um ponto de referência (spec/ui 37 §3), achada por
        ``ctx.snap``; com a distância digitada, a guia fica travada e o ponto vai a essa
        distância da referência, do lado do cursor."""
        fixed = self.fixed.get("ref")
        if fixed is not None and self.tracking is not None:  # direção travada
            ref, (ux, uy) = self.tracking["source"], self.tracking["dir"]
            sign = -1.0 if (p[0] - ref[0]) * ux + (p[1] - ref[1]) * uy < 0 else 1.0
            q = (ref[0] + sign * fixed * ux, ref[1] + sign * fixed * uy)
        else:
            t = self.ctx.tracked
            g = t.reference() if t is not None else None
            if g is None:
                self.tracking = None
                self.fixed.pop("ref", None)
                return None
            ref, (ux, uy), q = g.source, g.dir, t.point
        self.tracking = {"source": ref, "dir": (ux, uy), "point": q,
                         "distance": math.dist(ref, q)}
        return q

    def fields(self):
        if self.tracking is not None:
            return [Field("ref", "Distância", "m", self.tracking["distance"],
                          self.fixed.get("ref"))]
        return self.point_fields()

    def point_fields(self) -> list[Field]:
        return []

    def check(self, key, value):
        if key == "ref":
            return "a distância não pode ser negativa" if value < 0 else None
        return self.point_check(key, value)

    def point_check(self, key, value) -> str | None:
        return None

    def _consume_reference(self) -> None:
        """O ponto marcado solta a distância digitada; os pontos de referência ficam
        até Esc ou a troca de ferramenta (spec/ui 37 §2)."""
        self.tracking = None
        self.fixed.pop("ref", None)

    def _resolve(self, q: Point) -> Point:
        """Ponto com os valores fixados nos campos (spec/ui 07 §2.3)."""
        return q

    def move(self, p, mods):
        super().move(p, mods)
        self._point(p, mods)

    def cancel(self):
        if self.release_reference():
            return True
        self.fixed.clear()
        if self.points:
            self.points = []
            return True
        return False

    def preview(self):
        return self.shape_preview()

    def shape_preview(self) -> list[Mark]:
        return []

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

    def point_fields(self):
        if not self.points:
            return []
        last = self.points[-1]
        q = self.snapped.point if self.snapped else None
        length = math.dist(last, q) if q else None
        angle = _degrees(q[0] - last[0], q[1] - last[1]) if q and length > 1e-9 else None
        return [Field("length", "Comprimento", "m", length, self.fixed.get("length")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def point_check(self, key, value):
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
        self._consume_reference()
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

    def shape_preview(self):
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
        self._consume_reference()
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

    def shape_preview(self):
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

    def point_fields(self):
        if not self.points:
            return []
        a = self.points[0]
        q = self.snapped.point if self.snapped else None
        return [Field("width", "Largura", "m", abs(q[0] - a[0]) if q else None,
                      self.fixed.get("width")),
                Field("height", "Altura", "m", abs(q[1] - a[1]) if q else None,
                      self.fixed.get("height"))]

    def point_check(self, key, value):
        if value < geom2d.MIN_LENGTH:
            return "o retângulo precisa de largura e profundidade"
        return None

    def _resolve(self, q):
        return rect_corner(self.points[0], q, self.fixed.get("width"), self.fixed.get("height"))

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self._point(p, mods)
        self._consume_reference()
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

    def shape_preview(self):
        if not self.points or not self.snapped:
            return []
        (x0, y0), (x1, y1) = self.points[0], self.snapped.point
        (x0, x1), (y0, y1) = sorted((x0, x1)), sorted((y0, y1))
        corners = [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]
        marks = []
        for a, b in itertools.pairwise(corners):
            marks += self._band(a, b)
        return marks


# --- pilar, viga e laje (spec/ui 10 §2) --------------------------------------------------


def _first_type(session: Session, ifc_class: str) -> str | None:
    types = sorted(session.doc.ifc.by_type(ifc_class), key=lambda t: t.Name or "")
    if ifc_class == "IfcSlabType":  # os de cobertura ficam com a ferramenta Cobertura
        types = [t for t in types if t.PredefinedType != "ROOF"]
    preferred = {"IfcColumnType": "Pilar 20×40", "IfcBeamType": "Viga 14×40",
                 "IfcSlabType": "Laje maciça 10 cm"}.get(ifc_class)
    found = next((t for t in types if t.Name == preferred), types[0] if types else None)
    return found.GlobalId if found is not None else None


def _base_section(session: Session, ifc_class: str) -> dict:
    """Seção inicial da ferramenta: a do tipo padrão da biblioteca (20 × 40, 14 × 40)."""
    gid = _first_type(session, ifc_class)
    if gid is not None:
        return dict(st_types.section(session.doc.get(gid)))
    return ({"shape": "rect", "b": 0.20, "h": 0.40} if ifc_class == "IfcColumnType"
            else {"shape": "rect", "b": 0.14, "h": 0.40})


def _top_options(tool, fixed_key: str) -> dict:
    """Topo ligado ao pavimento de cima (com deslocamento) ou fixo (spec/ui 10 §3)."""
    if tool.top == "fixed":
        return {"top_mode": "fixed", fixed_key: getattr(tool, fixed_key)}
    return {"top_offset": tool.top_offset}


class ColumnTool(Tool):
    """Pilar (spec/ui 10 §2.1): um clique no ponto de inserção; barra de espaço gira 90°.
    As dimensões são digitadas na barra Opções; o tipo da seção é achado ou criado pelo
    núcleo (``commands.section_type``). ``type`` é só o tipo de partida (material e
    representação na planta)."""

    name, label = "column", "Pilar"
    type_class = "IfcColumnType"
    creates = True

    def __init__(self, ctx):
        super().__init__(ctx)
        self.type = _first_type(ctx.session, self.type_class)
        base = _base_section(ctx.session, self.type_class)
        self.shape = base["shape"]
        self.b, self.h = base.get("b", 0.20), base.get("h", 0.40)
        self.d = base.get("d", 0.30)
        self.insertion = (1, 1)  # quadradinho de 9 pontos: (coluna, linha), centro
        self.angle = 0.0
        self.base_offset = 0.0
        self.top = "storey"  # "storey" (pavimento de cima) ou "fixed"
        self.top_offset = 0.0
        self.fixed_height = structure_common.DEFAULT_TOP
        self.point: Point | None = None

    def section(self) -> dict:
        if self.shape == "circle":
            return {"shape": "circle", "d": self.d}
        return {"shape": "rect", "b": self.b, "h": self.h}

    @property
    def cardinal(self) -> int:
        if self.shape == "circle":
            return 5
        return profiles.PLAN_CARDINAL[self.insertion]

    def hint(self):
        ref = ("; Tab digita X e Y a partir dele" if self.reference is not None
               else "; pare o cursor num vértice para medir a partir dele")
        return f"Clique o ponto de inserção; barra de espaço gira 90°{ref}"

    def fields(self):
        if self.cursor is None:
            return []
        if self.reference is not None and self.point is not None:
            rx, ry = self.reference
            return [Field("dx", "X", "m", self.point[0] - rx, self.fixed.get("dx"), True),
                    Field("dy", "Y", "m", self.point[1] - ry, self.fixed.get("dy"), True)]
        return [Field("angle", "Ângulo", "°", self.angle)]

    def fix(self, key, value):
        if key == "angle":  # vale para os próximos pilares, como a barra Opções
            if value is not None:
                self.angle = (value + 180.0) % 360.0 - 180.0
            if self.cursor is not None:
                self.move(self.cursor, self.mods)
            return None
        return super().fix(key, value)

    def move(self, p, mods):
        super().move(p, mods)
        self.snapped = self.ctx.snap(p, mods, extra=self.ctx.vertices + self.ctx.column_points)
        q = self.snapped.point
        if self.reference is not None and ("dx" in self.fixed or "dy" in self.fixed):
            rx, ry = self.reference
            q = (rx + self.fixed.get("dx", q[0] - rx), ry + self.fixed.get("dy", q[1] - ry))
            self.snapped = snap.Snap(q, "free")
        self.point = q

    def key(self, key):
        if key == "space":
            self.angle = (self.angle + 90.0 + 180.0) % 360.0 - 180.0
            return True
        return False

    def cancel(self):
        self.fixed.clear()
        return self.release_reference()

    def _outline(self) -> list[Point] | None:
        if self.point is None:
            return None
        state = {"point": list(self.point), "cardinal": self.cardinal, "angle": self.angle}
        try:
            return columns.outline(self.session.doc, state, self.section())
        except (KeyError, ValueError):
            return None

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        if self.session.storey is None:
            self.session.message("não há pavimento ativo", "recusa")
            return
        doc, storey, q = self.session.doc, self.session.storey, self.point
        options = {"cardinal": self.cardinal, "angle": self.angle,
                   "base_offset": self.base_offset, **_top_options(self, "fixed_height")}
        self.session.run(lambda: sc.create_column(doc, self.type, storey, q,
                                                  section=self.section(), **options))
        self.fixed.clear()
        self.tracking = None
        self.move(p, mods)

    def preview(self):
        ring = self._outline()
        marks = [Mark(tuple(ring), True)] if ring else []
        return marks


class _BeamOptions:
    """Opções da ferramenta Viga (spec/ui 10 §3): b × h digitados; ``type`` é só o tipo
    de partida (material e representação na planta)."""

    type_class = "IfcBeamType"

    def __init__(self, session: Session):
        self.type = _first_type(session, self.type_class)
        base = _base_section(session, self.type_class)
        self.b, self.h = base["b"], base["h"]
        self.ref_line = "axis"
        self.top = "storey"
        self.top_offset = 0.0
        self.top_elevation = structure_common.DEFAULT_TOP

    def section(self) -> dict:
        return {"shape": "rect", "b": self.b, "h": self.h}

    def command_options(self) -> dict:
        return {"ref_line": self.ref_line, "section": self.section(),
                **_top_options(self, "top_elevation")}

    def band(self, doc) -> tuple[float, float]:
        b = self.b
        return {"axis": (-b / 2, b / 2), "left_face": (-b, 0.0),
                "right_face": (0.0, b)}[self.ref_line]


class BeamTool(WallTool):
    """Viga (spec/ui 10 §2.2): como a parede reta, mas cada trecho clicado já é uma viga
    e a cadeia segue do último ponto."""

    name, label = "beam", "Viga"
    options_class = _BeamOptions

    def hint(self):
        if not self.points:
            return "Clique o início da viga"
        return ("Clique o fim; a próxima viga começa nele; Tab digita comprimento e ângulo; "
                "Esc ou clique duplo encerra")

    def _extra(self):
        return list(self.points) + self.ctx.column_points

    def press(self, p, mods, button="left"):
        if button != "left":
            self.cancel()
            return
        q = self._point(p, mods)
        self._consume_reference()
        self.fixed.clear()
        if not self.points:
            self.points = [q]
            return
        a = self.points[-1]
        if math.dist(a, q) <= beams.MIN_LENGTH:
            return
        options, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is None:
            self.session.message("não há pavimento ativo", "recusa")
            return
        if self.session.run(lambda: sc.create_beam(doc, options.type, storey, a, q,
                                                   **options.command_options())):
            self.points = [q]

    def double(self, p, mods):
        self.points = []

    def key(self, key):
        if key == "enter":
            self.points = []
            return True
        return False

    def shape_preview(self):
        if not self.points or not self.snapped:
            return []
        a, b = self.points[-1], self.snapped.point
        marks = self._band(a, b)
        if marks:
            marks.append(Mark((a, b), False, "guide"))  # a linha de referência
        if "angle" in self.fixed:
            marks.append(_guide(a, self.fixed["angle"], self.ctx.tol))
        return marks


class _SlabOptions:
    """Opções da ferramenta Laje (spec/ui 10 §3)."""

    type_class = "IfcSlabType"

    def __init__(self, session: Session):
        self.type = _first_type(session, self.type_class)
        self.mode = "polygon"  # "rectangle" ou "room" (pelo cômodo, spec/ui 12 §4)
        self.boundary = "outer"  # contorno pelo cômodo: inner, axis, outer
        self.top_offset = 0.0


class SlabTool(_WallTool):
    """Laje (spec/ui 10 §2.3): polígono (fecha no primeiro ponto, com clique duplo ou
    Enter) ou retângulo por dois cantos."""

    name, label = "slab", "Laje"
    options_class = _SlabOptions

    def __init__(self, ctx, options=None):
        super().__init__(ctx, options)
        self.room: list | None = None  # contorno do cômodo sob o cursor (modo Pelo cômodo)

    def hint(self):
        if self.options.type is None:
            return "Não há tipo de laje no projeto"
        if self.options.mode == "room":
            return "Clique dentro de um cômodo fechado por paredes"
        if self.options.mode == "rectangle":
            return ("Clique o primeiro canto" if not self.points else
                    "Clique o canto oposto; Tab digita largura e altura")
        if not self.points:
            return "Clique o primeiro vértice da laje"
        return ("Clique o próximo vértice; feche no primeiro ponto, com clique duplo ou "
                "Enter; Tab digita comprimento e ângulo; Esc tira o último vértice")

    def _extra(self):
        return list(self.points) + self.ctx.vertices + self.ctx.column_points

    def _room(self, p) -> list | None:
        """Contorno do cômodo sob o cursor (modo Pelo cômodo), ou None."""
        storey = self.session.storey
        if storey is None:
            return None
        try:
            return rooms.room_outline(self.session.doc, storey, p, self.options.boundary)
        except OpError:
            return None

    def move(self, p, mods):
        if getattr(self.options, "mode", None) == "room":
            Tool.move(self, p, mods)
            self.snapped = snap.Snap(tuple(p), "free")
            self.room = self._room(p)
            return
        super().move(p, mods)

    def point_fields(self):
        if not self.points:
            return []
        q = self.snapped.point if self.snapped else None
        if self.options.mode == "rectangle":
            a = self.points[0]
            return [Field("width", "Largura", "m", abs(q[0] - a[0]) if q else None,
                          self.fixed.get("width")),
                    Field("height", "Altura", "m", abs(q[1] - a[1]) if q else None,
                          self.fixed.get("height"))]
        last = self.points[-1]
        length = math.dist(last, q) if q else None
        angle = _degrees(q[0] - last[0], q[1] - last[1]) if q and length > 1e-9 else None
        return [Field("length", "Comprimento", "m", length, self.fixed.get("length")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def point_check(self, key, value):
        if value <= geom2d.MIN_LENGTH:
            return "medida pequena demais"
        return None

    def _resolve(self, q):
        if self.options.mode == "rectangle":
            return rect_corner(self.points[0], q, self.fixed.get("width"),
                               self.fixed.get("height"))
        return polar_point(self.points[-1], q, self.fixed.get("length"),
                           self.fixed.get("angle"))

    def _closes(self, q: Point) -> bool:
        return len(self.points) >= 3 and math.dist(q, self.points[0]) <= max(self.ctx.tol,
                                                                              1e-6)

    def _problem(self, points) -> str | None:
        """Motivo para o contorno não fechar, ou None."""
        try:
            slabs.clean(points)
        except OpError as e:
            return str(e)
        return None

    def finish(self) -> None:
        points = list(self.points)
        if len(points) < 3:
            return
        problem = self._problem(points)
        if problem:
            self.session.message(problem, "recusa")
            return
        self._create(points)

    def _create(self, points) -> None:
        options, doc, storey = self.options, self.session.doc, self.session.storey
        if options.type is None or storey is None:
            self.session.message("não há tipo de laje ou pavimento ativo", "recusa")
        else:
            self.session.run(lambda: sc.create_slab(doc, options.type, storey, points,
                                                    top_offset=options.top_offset))
        self.points = []

    def _create_in_room(self, p) -> None:
        options, doc, storey = self.options, self.session.doc, self.session.storey
        if options.type is None or storey is None:
            self.session.message("não há tipo de laje ou pavimento ativo", "recusa")
            return
        self.session.run(lambda: sc.create_slab_in_room(doc, options.type, storey, p,
                                                        options.boundary,
                                                        top_offset=options.top_offset))

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        if getattr(self.options, "mode", None) == "room":
            self._create_in_room(p)
            self.room = None
            return
        q = self._point(p, mods)
        self._consume_reference()
        self.fixed.clear()
        if self.options.mode == "rectangle":
            if not self.points:
                self.points = [q]
                return
            (x0, y0), (x1, y1) = self.points[0], q
            if abs(x1 - x0) < geom2d.MIN_LENGTH or abs(y1 - y0) < geom2d.MIN_LENGTH:
                self.session.message("o retângulo precisa de largura e profundidade", "recusa")
                return
            self._create([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            return
        if self._closes(q):
            self.finish()
        elif not self.points or math.dist(q, self.points[-1]) > geom2d.MIN_LENGTH:
            self.points.append(q)

    def double(self, p, mods):
        if self.options.mode == "polygon":
            self.finish()

    def key(self, key):
        if key == "enter" and self.options.mode == "polygon":
            self.finish()
            return True
        return False

    def cancel(self):
        """Esc tira o último vértice; sem vértices, cancela (spec/ui 10 §2.3)."""
        if self.release_reference():
            return True
        self.fixed.clear()
        if self.points:
            if self.options.mode == "rectangle":
                self.points = []
            else:
                self.points.pop()
            return True
        return False

    def shape_preview(self):
        if getattr(self.options, "mode", None) == "room":
            return [Mark(tuple(tuple(q) for q in self.room), True)] if self.room else []
        if not self.points or not self.snapped:
            return []
        q = self.snapped.point
        if self.options.mode == "rectangle":
            (x0, y0), (x1, y1) = self.points[0], q
            return [Mark(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), True)]
        pts = list(self.points)
        if not self._closes(q):
            pts.append(q)
        style = "invalid" if len(pts) >= 3 and slabs.self_intersects(pts) else "preview"
        marks = [Mark(tuple(pts), len(pts) >= 3, style)]
        if "angle" in self.fixed:
            marks.append(_guide(self.points[-1], self.fixed["angle"], self.ctx.tol))
        return marks


def roof_types(doc) -> list:
    """Tipos de laje de cobertura (``ROOF``), para a ferramenta Cobertura."""
    return sorted((t for t in doc.ifc.by_type("IfcSlabType") if t.PredefinedType == "ROOF"),
                  key=lambda t: t.Name or "")


def floor_types(doc) -> list:
    """Tipos de laje que não são de cobertura, para a ferramenta Laje."""
    return sorted((t for t in doc.ifc.by_type("IfcSlabType") if t.PredefinedType != "ROOF"),
                  key=lambda t: t.Name or "")


class _RoofOptions:
    """Opções da ferramenta Cobertura (cobertura.md §4)."""

    type_class = "IfcSlabType"

    def __init__(self, session: Session):
        found = roof_types(session.doc)
        preferred = next((t for t in found if t.Name == "Telha cerâmica"),
                         found[0] if found else None)
        self.type = preferred.GlobalId if preferred is not None else None
        self.mode = "room"  # pelas paredes; polygon, rectangle
        self.boundary = "outer"  # contorno externo das paredes (§4)
        self.shape = "gable"
        self.slope = roofs.DEFAULT_SLOPE
        self.overhang = roofs.DEFAULT_OVERHANG
        self.base_height: float | None = None  # None: topo das paredes do pavimento


class RoofTool(SlabTool):
    """Cobertura (cobertura.md §4): contorno por polígono, retângulo ou pelas paredes;
    na uma e na duas águas, um clique escolhe o lado (Enter aceita o lado maior)."""

    name, label = "roof", "Cobertura"
    options_class = _RoofOptions

    def __init__(self, ctx, options=None):
        super().__init__(ctx, options)
        self.pending: list | None = None  # contorno à espera do lado
        self.side: int | None = None  # lado sob o cursor

    def base_height(self) -> float:
        if self.options.base_height is not None:
            return self.options.base_height
        storey = self.session.storey
        return roofs.wall_top(self.session.doc, storey) if storey is not None \
            else roofs.DEFAULT_BASE

    def hint(self):
        if self.options.type is None:
            return "Não há tipo de cobertura no projeto"
        if self.pending is not None:
            what = ("o lado mais baixo" if self.options.shape == "shed"
                    else "um lado paralelo à cumeeira")
            return f"Clique {what}; Enter aceita o lado maior; Esc volta"
        if self.options.mode == "room":
            return "Clique dentro da edificação: a cobertura apoia no contorno externo das paredes"
        return super().hint().replace("da laje", "do contorno")

    def _nearest_side(self, p) -> int:
        pts = self.pending
        n = len(pts)
        return min(range(n), key=lambda i: plan.distance_to_segment(
            tuple(p), tuple(pts[i]), tuple(pts[(i + 1) % n])))

    def _room(self, p) -> list | None:
        """Contorno externo das paredes em volta do cursor (§4), ou None."""
        storey = self.session.storey
        if storey is None:
            return None
        try:
            return rooms.building_outline(self.session.doc, storey, p)
        except OpError:
            return None

    def move(self, p, mods):
        if self.pending is not None:
            Tool.move(self, p, mods)
            self.snapped = snap.Snap(tuple(p), "free")
            self.side = self._nearest_side(p)
            return
        super().move(p, mods)

    def _create(self, points) -> None:
        self.points = []
        options = self.options
        if options.type is None or self.session.storey is None:
            self.session.message("não há tipo de cobertura ou pavimento ativo", "recusa")
            return
        try:
            outline = roofs.clean(points)
        except OpError as e:
            self.session.message(str(e), "recusa")
            return
        if options.shape in ("gable", "hip") and not roofs.is_rectangle(outline):
            self.session.message(roofs.RECT_ONLY, "recusa")
            return
        if options.shape in ("shed", "gable"):
            self.pending, self.side = outline, None
            return
        self._commit(outline, None)

    def _create_in_room(self, p) -> None:
        if self.session.storey is None:
            return
        outline = self._room(p)
        if outline is None:
            self.session.message("clique dentro de uma área fechada por paredes", "recusa")
            return
        self._create(outline)

    def _commit(self, outline, side) -> None:
        options, doc, storey = self.options, self.session.doc, self.session.storey
        self.pending = self.side = None
        self.session.run(lambda: sc.create_roof(
            doc, options.type, storey, outline, shape=options.shape, slope=options.slope,
            overhang=options.overhang, base_height=self.base_height(), side=side))

    def press(self, p, mods, button="left"):
        if self.pending is not None:
            if button == "left":
                self._commit(self.pending, self._nearest_side(p))
            return
        super().press(p, mods, button)

    def key(self, key):
        if self.pending is not None and key == "enter":
            self._commit(self.pending, None)
            return True
        return super().key(key)

    def cancel(self):
        if self.pending is not None:
            self.pending = self.side = None
            return True
        return super().cancel()

    def shape_preview(self):
        if self.pending is None:
            return super().shape_preview()
        pts = tuple(tuple(q) for q in self.pending)
        marks = [Mark(pts, True)]
        if self.side is not None:
            a, b = pts[self.side], pts[(self.side + 1) % len(pts)]
            marks.append(Mark((a, b), False, "reference"))
        return marks


class _OpeningOptions:
    """Opções da ferramenta Abertura na laje (spec/ui 12 §3.3)."""

    type_class = None

    def __init__(self, session: Session):
        self.mode = "rectangle"
        self.type = None


class SlabOpeningTool(SlabTool):
    """Abertura na laje selecionada (spec/ui 12 §3.3): polígono ou retângulo, inteiro
    dentro da laje. Chamada pela mini-barra; volta a Selecionar depois de criar."""

    name, label = "slab_opening", "Abertura na laje"
    options_class = _OpeningOptions

    def __init__(self, ctx, options=None):
        super().__init__(ctx, options)
        self.slab: str | None = None

    def hint(self):
        if self.slab is None:
            return "Selecione uma laje e use Abertura na mini-barra"
        if self.options.mode == "rectangle":
            return ("Clique o primeiro canto da abertura, dentro da laje" if not self.points
                    else "Clique o canto oposto; Tab digita largura e altura")
        return ("Clique os vértices da abertura, dentro da laje; feche no primeiro ponto, "
                "com clique duplo ou Enter")

    def _fits(self, points) -> bool:
        doc = self.session.doc
        slab = doc.find(self.slab) if self.slab else None
        if slab is None or len(points) < 3:
            return False
        try:
            outline = slabs.read_state(doc, slab)["outline"]
            return slab_openings.inside(slabs.clean(points), outline)
        except OpError:
            return False

    def _problem(self, points):
        found = super()._problem(points)
        if found is None and not self._fits(points):
            return "a abertura precisa ficar inteira dentro da laje"
        return found

    def _create(self, points) -> None:
        doc, slab = self.session.doc, self.slab
        if slab is None:
            self.session.message("selecione a laje antes", "recusa")
        elif self.session.run(lambda: sc.create_slab_opening(doc, slab, points)):
            self.finished = True
        self.points = []

    def shape_preview(self):
        marks = super().shape_preview()
        if not marks or not self.snapped:
            return marks
        first = marks[0]
        if first.closed and len(first.points) >= 3 and not self._fits(list(first.points)):
            marks[0] = Mark(first.points, True, "invalid")
        return marks


# --- documentação da planta (spec/ui 13) ------------------------------------------------


class _SpaceOptions:
    """Opções da ferramenta Ambiente (spec/ui 13 §3.3)."""

    type_class = None

    def __init__(self, session: Session):
        self.mode = "room"  # ou "polygon"
        self.boundary = "inner"  # o ambiente vai até a face interna das paredes
        self.name = spaces.DEFAULT_NAME
        self.height: float | None = None  # vazio = calculado
        self.type = "space"


class SpaceTool(SlabTool):
    """Ambiente pelo cômodo (um clique) ou por polígono (spec/ui 13 §3.3)."""

    name, label = "space", "Ambiente"
    options_class = _SpaceOptions

    def hint(self):
        if self.options.mode == "room":
            return "Clique dentro de um cômodo fechado por paredes"
        if not self.points:
            return "Clique o primeiro vértice do ambiente"
        return "Clique os vértices; feche no primeiro ponto, com clique duplo ou Enter"

    def _create_in_room(self, p) -> None:
        options, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is None:
            self.session.message("não há pavimento ativo", "recusa")
            return
        self.session.run(lambda: ac.create_space_in_room(doc, storey, p, name=options.name,
                                                         height=options.height))

    def _create(self, points) -> None:
        options, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is None:
            self.session.message("não há pavimento ativo", "recusa")
        else:
            self.session.run(lambda: ac.create_space(doc, storey, points, name=options.name,
                                                     height=options.height))
        self.points = []


class _HatchOptions:
    """Opções da ferramenta Hachura (spec/ui 13 §6)."""

    type_class = None

    def __init__(self, session: Session):
        self.mode = "rectangle"
        self.pattern = "solid"
        self.color = "#B3B3AD"
        self.angle = 45.0
        self.spacing = 2.0  # mm de papel
        self.type = "hatch"


class HatchTool(SlabTool):
    """Hachura 2D por polígono ou retângulo (spec/ui 13 §6)."""

    name, label = "hatch", "Hachura"
    options_class = _HatchOptions

    def hint(self):
        if self.options.mode == "rectangle":
            return "Clique dois cantos opostos da hachura"
        return "Clique os vértices da hachura; feche no primeiro ponto ou com Enter"

    def _create(self, points) -> None:
        o, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is not None:
            self.session.run(lambda: ac.create_annotation(
                doc, "hatch", storey, outline=points, pattern=o.pattern, color=o.color,
                angle=o.angle, spacing=o.spacing))
        self.points = []


class _LineOptions:
    """Opções da ferramenta Linha (spec/ui 13 §6)."""

    type_class = None

    def __init__(self, session: Session):
        self.weight = 0.25
        self.dash = "solid"
        self.type = "line2d"

    def band(self, doc):
        return (0.0, 0.0)


class LineTool(WallTool):
    """Linha 2D: clique os pontos; Enter, clique duplo ou botão direito encerra; clicar no
    primeiro ponto fecha (spec/ui 13 §6)."""

    name, label = "line2d", "Linha"
    options_class = _LineOptions

    def hint(self):
        if not self.points:
            return "Clique o primeiro ponto da linha"
        return ("Clique o próximo ponto; Tab digita comprimento e ângulo; Enter ou clique "
                "duplo encerra; clique no primeiro ponto fecha")

    def finish(self, closed: bool = False) -> None:
        points = list(self.points)
        self.points = []
        if closed and points and math.dist(points[-1], points[0]) < 1e-6:
            points.pop()
        if len(points) < 2:
            return
        o, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is not None:
            self.session.run(lambda: ac.create_annotation(
                doc, "line2d", storey, points=points, closed=closed, weight=o.weight,
                dash=o.dash))

    def shape_preview(self):
        pts = list(self.points)
        if pts and self.snapped:
            pts.append(self.snapped.point)
        return [Mark(tuple(pts), False)] if len(pts) >= 2 else []


class _PointTool(Tool):
    """Ferramenta de um clique (nível, texto) ou dois (norte)."""

    creates = True

    def move(self, p, mods):
        super().move(p, mods)
        self.snapped = self.ctx.snap(p, mods, extra=self.ctx.vertices)

    def _storey(self):
        storey = self.session.storey
        if storey is None:
            self.session.message("não há pavimento ativo", "recusa")
        return storey


class LevelTool(_PointTool):
    """Cota de nível: um clique (spec/ui 13 §5)."""

    name, label = "level_mark", "Nível"

    def hint(self):
        return "Clique onde vai a cota de nível"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        storey, q, doc = self._storey(), self.snapped.point, self.session.doc
        if storey is not None:
            self.session.run(lambda: ac.create_annotation(doc, "level_mark", storey, at=q))


class _TextOptions:
    def __init__(self):
        self.size = 2.5
        self.angle = 0.0
        self.align = "left"


class TextTool(_PointTool):
    """Texto: um clique e digita (spec/ui 13 §6). ``ask(atual)`` pede o texto (posto pela
    janela; devolve ``None`` se o usuário desistir)."""

    name, label = "text", "Texto"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.options = _TextOptions()
        self.ask = None

    def hint(self):
        return "Clique onde começa o texto e digite"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        storey, q, doc, o = self._storey(), self.snapped.point, self.session.doc, self.options
        if storey is None:
            return
        text = self.ask("") if self.ask is not None else None
        if not text or not text.strip():
            return
        self.session.run(lambda: ac.create_annotation(doc, "text", storey, at=q,
                                                      text=text.strip("\n"), size=o.size,
                                                      angle=o.angle, align=o.align))


class NorthTool(_PointTool):
    """Norte: clique a posição e a direção (spec/ui 13 §7)."""

    name, label = "north", "Norte"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.points: list[Point] = []

    def hint(self):
        return "Clique a posição do norte" if not self.points else "Clique a direção do norte"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        q = self.snapped.point
        if not self.points:
            self.points = [q]
            return
        a = self.points[0]
        self.points = []
        if math.dist(a, q) < geom2d.MIN_LENGTH:
            return
        storey, doc = self._storey(), self.session.doc
        angle = math.degrees(math.atan2(q[1] - a[1], q[0] - a[0]))
        if storey is not None:
            self.session.run(lambda: ac.create_annotation(doc, "north", storey, at=a,
                                                          angle=angle))

    def cancel(self):
        if self.points:
            self.points = []
            return True
        return False

    def preview(self):
        if not self.points or not self.snapped:
            return []
        return [Mark((self.points[0], self.snapped.point), False)]


# --- Eixos de projeto (spec/ui 20 §2) ------------------------------------------------------


def parse_spacings(text: str) -> list[float]:
    """"5; 4; 4" (ou "5 4 4") → [5, 4, 4]; vazio = um eixo só."""
    parts = [p for p in text.replace(";", " ").split() if p.strip()]
    return [parse_number(p) for p in parts]


class _GridOptions:
    type_class = None

    def __init__(self):
        self.u = "5; 5"
        self.v = "4; 4"
        self.first_number = "1"
        self.first_letter = "A"
        self.type = None


class GridTool(_PointTool):
    """Eixos de projeto: clique a origem e a direção do primeiro eixo (spec/ui 20 §2)."""

    name, label = "grid", "Eixos"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.options = _GridOptions()
        self.points: list[Point] = []

    def hint(self):
        return ("Clique a origem dos eixos (cruzamento do 1 com o A)" if not self.points
                else "Clique a direção dos eixos numerados (ângulo); Shift prende a 45°")

    def _state(self, origin, angle):
        from brasbim.core import grids

        o = self.options
        try:
            return {**grids.default_state(), "origin": list(origin), "angle": angle,
                    "u": grids.axes_from_spacings(parse_spacings(o.u), o.first_number),
                    "v": grids.axes_from_spacings(parse_spacings(o.v), o.first_letter)}
        except (OpError, ValueError):
            return None

    def _angle(self, q) -> float:
        a = self.points[0]
        if math.dist(a, q) < 1e-6:
            return 0.0
        return math.degrees(math.atan2(q[1] - a[1], q[0] - a[0]))

    def move(self, p, mods):
        Tool.move(self, p, mods)
        origin = self.points[0] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin=origin, extra=self.ctx.vertices)

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        q = self.snapped.point
        if not self.points:
            self.points = [q]
            return
        origin, angle = self.points[0], self._angle(q)
        self.points = []
        state = self._state(origin, angle)
        if state is None:
            self.session.message("espaçamentos dos eixos inválidos (ex.: 5; 4; 4)", "recusa")
            return
        from brasbim.core import grids

        doc, o = self.session.doc, self.options
        self.session.run(lambda: grids.create_grid(
            doc, origin, angle, parse_spacings(o.u), parse_spacings(o.v), o.first_number,
            o.first_letter))

    def cancel(self):
        if self.points:
            self.points = []
            return True
        return False

    def preview(self):
        from brasbim.core import grids

        if self.snapped is None or self.session.storey is None:
            return []
        origin = self.points[0] if self.points else self.snapped.point
        angle = self._angle(self.snapped.point) if self.points else 0.0
        state = self._state(origin, angle)
        if state is None:
            return []
        return [Mark(st.points, st.closed) for st in grids.prims(state,
                                                                  self.session.storey).strokes]


# --- Desenho 2D (spec/ui 19) -------------------------------------------------------------


def _anno_marks(session, prefix: str, state: dict, style: str = "preview") -> list[Mark]:
    """Pré-visualização de uma anotação pelo estado (as primitivas que ela vai ter)."""
    from brasbim.core.annotations import base as abase

    storey = session.storey
    if storey is None:
        return []
    kind = abase.KINDS[prefix]
    full = {**kind.defaults, **state, "storey": storey.GlobalId}
    try:
        kind.validate(full)
        built = kind.build(session.doc, storey, full)
    except (OpError, ValueError, ZeroDivisionError, KeyError):
        return []
    marks = [Mark(st.points, st.closed, style) for st in built.strokes if len(st.points) > 1]
    from brasbim.core.annotations.prims import text_box

    marks += [Mark(tuple(text_box(t)), True, "guide") for t in built.texts]
    return marks


class _CurveOptions:
    """Espessura e tipo de linha (círculo, arco e curva, spec/ui 19 §3)."""

    type_class = None

    def __init__(self, session: Session):
        self.weight = 0.18
        self.dash = "solid"
        self.type = None


class _ClickTool(_PointTool):
    """Ferramenta de alguns cliques; ``points`` guarda os já dados."""

    clicks = 2

    def __init__(self, ctx):
        super().__init__(ctx)
        self.points: list[Point] = []
        self.options = _CurveOptions(ctx.session)

    def cancel(self):
        if self.points:
            self.points.pop()
            return True
        return False

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        if self._storey() is None:
            return
        q = self.snapped.point
        if self.points and math.dist(q, self.points[-1]) < 1e-6:
            return
        self.points.append(q)
        if len(self.points) >= self.clicks:
            points, self.points = list(self.points), []
            self.finish(points)

    def finish(self, points) -> None:
        raise NotImplementedError

    def state(self, points) -> dict | None:
        return None

    def preview(self):
        if not self.points or self.snapped is None:
            return []
        state = self.state([*self.points, self.snapped.point])
        marks = _anno_marks(self.session, self.prefix, state) if state else []
        return marks or [Mark((*self.points, self.snapped.point), False, "guide")]

    def _create(self, state: dict) -> None:
        doc, storey = self.session.doc, self.session.storey
        self.session.run(lambda: ac.create_annotation(doc, self.prefix, storey, **state))


class CircleTool(_ClickTool):
    """Círculo: centro e um ponto (spec/ui 19 §3); Tab digita o raio."""

    name, label, prefix = "circle2d", "Círculo", "circle2d"

    def hint(self):
        return "Clique o centro do círculo" if not self.points else \
            "Clique um ponto do círculo; Tab digita o raio"

    def fields(self):
        if not self.points or self.snapped is None:
            return []
        return [Field("radius", "Raio", "m", math.dist(self.points[0], self.snapped.point),
                      self.fixed.get("radius"))]

    def check(self, key, value):
        return "o raio deve ser positivo" if value <= 0 else None

    def move(self, p, mods):
        super().move(p, mods)
        if self.points and "radius" in self.fixed:
            c = self.points[0]
            d = math.dist(c, self.snapped.point) or 1.0
            r = self.fixed["radius"]
            q = self.snapped.point
            self.snapped = snap.Snap((c[0] + (q[0] - c[0]) * r / d, c[1] + (q[1] - c[1]) * r / d),
                                     "free")

    def state(self, points):
        if len(points) < 2 or math.dist(points[0], points[1]) < 1e-6:
            return None
        return {"center": list(points[0]), "radius": math.dist(points[0], points[1]),
                "weight": self.options.weight, "dash": self.options.dash}

    def finish(self, points):
        state = self.state(points)
        self.fixed.clear()
        if state:
            self._create(state)


class ArcTool(_ClickTool):
    """Arco por três pontos: início, um ponto do arco e fim (spec/ui 19 §3)."""

    name, label, prefix = "arc2d", "Arco", "arc2d"
    clicks = 3

    def hint(self):
        return ["Clique o início do arco", "Clique um ponto do arco",
                "Clique o fim do arco"][min(len(self.points), 2)]

    def state(self, points):
        if len(points) < 3:
            return None
        try:
            fields = drawing2d.arc_from_points(*points[:3])
        except OpError:
            return None
        return {**fields, "weight": self.options.weight, "dash": self.options.dash}

    def preview(self):
        if len(self.points) == 1 and self.snapped is not None:
            return [Mark((self.points[0], self.snapped.point), False, "guide")]
        return super().preview()

    def finish(self, points):
        state = self.state(points)
        if state is None:
            self.session.message("os três pontos estão alinhados: não há arco", "recusa")
            return
        self._create(state)


class SplineTool(LineTool):
    """Curva livre: passa pelos pontos clicados (spec/ui 19 §3)."""

    name, label = "spline2d", "Curva"
    options_class = _LineOptions

    def hint(self):
        if not self.points:
            return "Clique o primeiro ponto da curva"
        return ("Clique os pontos por onde a curva passa; Enter ou clique duplo encerra; "
                "clique no primeiro ponto fecha")

    def finish(self, closed: bool = False) -> None:
        points = list(self.points)
        self.points = []
        if closed and points and math.dist(points[-1], points[0]) < 1e-6:
            points.pop()
        if len(points) < 2:
            return
        o, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is not None:
            self.session.run(lambda: ac.create_annotation(
                doc, "spline2d", storey, points=points, closed=closed, weight=o.weight,
                dash=o.dash))

    def shape_preview(self):
        pts = list(self.points)
        if pts and self.snapped:
            pts.append(self.snapped.point)
        if len(pts) < 2:
            return []
        return [Mark(tuple(drawing2d.spline(pts, False)), False)]


class _RadiusOptions:
    type_class = None

    def __init__(self):
        self.diameter = False
        self.type = None


class RadiusDimTool(_ClickTool):
    """Cota de raio: um ponto sobre o círculo, o arco ou a parede em arco, e onde vai o
    texto (spec/ui 19 §3)."""

    name, label, prefix = "radius_dim", "Cota de raio", "radius_dim"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.options = _RadiusOptions()
        self.target = None  # (GlobalId, centro, raio)

    def hint(self):
        if self.target is None:
            return "Clique sobre um círculo, um arco ou uma parede em arco"
        return "Clique onde vai o texto da cota"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        storey = self._storey()
        if storey is None:
            return
        if self.target is None:
            found = drawing2d.curves_near(self.session.doc, storey, p,
                                          max(self.ctx.tol, 0.05))
            if not found:
                self.session.message("clique sobre um círculo, um arco ou uma parede em arco",
                                     "recusa")
                return
            self.target = found[0]
            return
        state = self.state([p])
        self.target = None
        if state:
            self._create(state)

    def cancel(self):
        if self.target is not None:
            self.target = None
            return True
        return False

    def state(self, points):
        if self.target is None or not points:
            return None
        gid, center, radius = self.target
        q = points[-1]
        angle = math.degrees(math.atan2(q[1] - center[1], q[0] - center[0]))
        return {"center": list(center), "radius": radius, "angle": angle % 360.0,
                "diameter": self.options.diameter, "ref": gid}

    def preview(self):
        if self.target is None or self.snapped is None:
            return []
        return _anno_marks(self.session, self.prefix, self.state([self.cursor]))


class AngleDimTool(_ClickTool):
    """Cota de ângulo: vértice, um ponto em cada lado e a posição do arco."""

    name, label, prefix = "angle_dim", "Cota de ângulo", "angle_dim"
    clicks = 4

    def hint(self):
        return ["Clique o vértice do ângulo", "Clique um ponto do primeiro lado",
                "Clique um ponto do segundo lado", "Clique onde passa o arco da cota"][
            min(len(self.points), 3)]

    def state(self, points):
        if len(points) < 3:
            return None
        v, a, b = points[:3]
        r = math.dist(v, points[3]) if len(points) > 3 else min(math.dist(v, a),
                                                                 math.dist(v, b)) * 0.5
        return {"vertex": list(v), "a": list(a), "b": list(b), "radius": max(r, 1e-3)}

    def preview(self):
        if self.snapped is None or not self.points:
            return []
        if len(self.points) < 2:
            return [Mark((self.points[0], self.snapped.point), False, "guide")]
        return super().preview()

    def finish(self, points):
        state = self.state(points)
        if state:
            self._create(state)


class _LabelOptions:
    type_class = None

    def __init__(self):
        self.field = "type"  # o que o rótulo preso mostra (spec/ui 19 §3)
        self.type = None


class LabelTool(_ClickTool):
    """Rótulo: a ponta da seta (sobre o elemento) e onde vai o texto (spec/ui 19 §3).
    ``ask(atual)`` pede o texto quando o rótulo é livre."""

    name, label, prefix = "label", "Rótulo", "label"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.options = _LabelOptions()
        self.ask = None
        self.ref: str | None = None

    def hint(self):
        return ("Clique a ponta da seta (sobre o elemento que o rótulo descreve)"
                if not self.points else "Clique onde vai o texto")

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        if not self.points:
            self.move(p, mods)
            gid = self.ctx.plan.pick(p, self.ctx.tol)
            element = self.session.doc.find(gid) if gid else None
            self.ref = gid if element is not None and not element.is_a("IfcAnnotation") \
                else None
        super().press(p, mods, button)

    def state(self, points):
        if len(points) < 2:
            return None
        field = self.options.field if self.ref else "free"
        return {"at": list(points[0]), "text_at": list(points[1]), "ref": self.ref,
                "field": field, "text": "texto" if field == "free" else ""}

    def finish(self, points):
        state = self.state(points)
        if state is None:
            return
        if state["field"] == "free":
            text = self.ask("") if self.ask is not None else None
            if not text or not text.strip():
                return
            state["text"] = text.strip()
        self._create(state)
        self.ref = None


class _RevisionOptions:
    type_class = None

    def __init__(self, session: Session):
        self.mode = "rectangle"
        self.number = None  # vazio: o próximo livre
        self.note = ""
        self.type = "revision"


class RevisionTool(SlabTool):
    """Marcador de alteração: retângulo ou polígono (spec/ui 19 §3)."""

    name, label = "revision", "Alteração"
    options_class = _RevisionOptions

    def hint(self):
        if self.options.mode == "rectangle":
            return "Clique dois cantos opostos da área alterada"
        return "Clique os vértices da área alterada; feche no primeiro ponto ou com Enter"

    def _create(self, points) -> None:
        o, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is not None:
            number = o.number or drawing2d.next_revision(doc)
            self.session.run(lambda: ac.create_annotation(
                doc, "revision", storey, outline=points, number=number, note=o.note))
        self.points = []


class SkylightTool(_PointTool):
    """Claraboia: um clique sobre a laje ou a cobertura (spec/ui 20 §4); barra de espaço
    gira 90°; Tab digita o ângulo."""

    name, label = "skylight", "Claraboia"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.width, self.length, self.angle = 0.80, 1.20, 0.0

    def hint(self):
        return ("Clique o centro da claraboia sobre uma laje ou uma cobertura; barra de "
                "espaço gira 90°")

    def fields(self):
        return [Field("angle", "Ângulo", "°", self.angle)] if self.cursor is not None else []

    def fix(self, key, value):
        if key == "angle" and value is not None:
            self.angle = value % 360.0

    def key(self, key):
        if key == "space":
            self.angle = (self.angle + 90.0) % 360.0
            return True
        return False

    def _state(self):
        from brasbim.core.structure import skylights

        if self.snapped is None:
            return None
        return {**skylights.default_state(), "center": list(self.snapped.point),
                "width": self.width, "length": self.length, "angle": self.angle}

    def preview(self):
        from brasbim.core.structure import skylights

        state = self._state()
        if state is None:
            return []
        storey = self.session.storey
        host = skylights.host_at(self.session.doc, storey, state["center"]) if storey else None
        style = "preview" if host is not None else "invalid"
        return [Mark(tuple(skylights.outline(state)), True, style)]

    def press(self, p, mods, button="left"):
        from brasbim.core.structure import skylights

        if button != "left":
            return
        self.move(p, mods)
        storey = self._storey()
        if storey is None:
            return
        doc, q = self.session.doc, self.snapped.point
        self.session.run(lambda: skylights.create_skylight(doc, storey, q, self.width,
                                                           self.length, self.angle))


# --- Escada, guarda-corpo e terreno (escada-terreno.md) -------------------------------------


class _StairOptions:
    type_class = None

    def __init__(self):
        self.shape = "straight"
        self.width = 1.20
        self.turn = "left"
        self.railing = "both"
        self.type = None


class StairTool(_PointTool):
    """Escada: clique o início (canto direito do primeiro degrau, de quem sobe) e a
    direção de subida (escada-terreno.md §2.4); Tab digita o ângulo."""

    name, label = "stair", "Escada"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.options = _StairOptions()
        self.start: Point | None = None

    def hint(self):
        if self.start is None:
            return ("Clique o início da escada: o canto direito do primeiro degrau, de quem "
                    "sobe")
        return "Clique a direção de subida; Tab digita o ângulo; Shift prende a 45°"

    def move(self, p, mods):
        Tool.move(self, p, mods)
        self.snapped = self.ctx.snap(p, mods, origin=self.start, extra=self.ctx.vertices)

    def _angle(self) -> float:
        if "angle" in self.fixed:
            return self.fixed["angle"]
        if self.start is None or self.snapped is None:
            return 0.0
        q = self.snapped.point
        if math.dist(self.start, q) < 1e-6:
            return 0.0
        return _degrees(q[0] - self.start[0], q[1] - self.start[1])

    def fields(self):
        if self.start is None:
            return []
        return [Field("angle", "Ângulo", "°", self._angle(), self.fixed.get("angle"))]

    def _state(self):
        from brasbim.core.structure import stairs

        storey = self.session.storey
        if storey is None or self.snapped is None:
            return None
        o = self.options
        start = self.start if self.start is not None else self.snapped.point
        return {**stairs.default_state(), "storey": storey.GlobalId, "start": list(start),
                "angle": self._angle(), "shape": o.shape, "width": o.width, "turn": o.turn,
                "railing": o.railing}

    def press(self, p, mods, button="left"):
        from brasbim.core.structure import stairs

        if button != "left":
            return
        self.move(p, mods)
        storey = self._storey()
        if storey is None:
            return
        if self.start is None:
            self.start = self.snapped.point
            return
        start, angle, o = self.start, self._angle(), self.options
        if "angle" not in self.fixed and math.dist(start, self.snapped.point) < 1e-6:
            return  # o segundo clique precisa dar a direção
        self.start = None
        self.fixed.clear()
        doc = self.session.doc
        self.session.run(lambda: stairs.create_stair(
            doc, storey, start, angle, shape=o.shape, width=o.width, turn=o.turn,
            railing=o.railing))

    def cancel(self):
        self.fixed.clear()
        if self.start is not None:
            self.start = None
            return True
        return False

    def preview(self):
        from brasbim.core.structure import stairs

        state = self._state()
        if state is None:
            return []
        try:
            prims = stairs.plan_prims(self.session.doc, state,
                                      storeys.cut_height(self.session.storey))
        except (OpError, ValueError, ZeroDivisionError):
            return []
        return [Mark(st.points, st.closed) for st in prims.strokes]


class _RailingOptions:
    type_class = None

    def __init__(self, session: Session):
        self.height = 1.10
        self.base = 0.0
        self.spacing = 1.20
        self.type = None

    def band(self, doc):
        return (0.0, 0.0)


class RailingTool(LineTool):
    """Guarda-corpo solto: clique os pontos; Enter, clique duplo ou botão direito encerra;
    clicar no primeiro ponto fecha (escada-terreno.md §3)."""

    name, label = "railing", "Guarda-corpo"
    options_class = _RailingOptions

    def hint(self):
        if not self.points:
            return "Clique o primeiro ponto do guarda-corpo"
        return ("Clique o próximo ponto; Tab digita comprimento e ângulo; Enter ou clique "
                "duplo encerra; clique no primeiro ponto fecha")

    def finish(self, closed: bool = False) -> None:
        from brasbim.core.structure import railings

        points = list(self.points)
        self.points = []
        if closed and points and math.dist(points[-1], points[0]) > 1e-6:
            points.append(points[0])
        if len(points) < 2:
            return
        o, doc, storey = self.options, self.session.doc, self.session.storey
        if storey is not None:
            self.session.run(lambda: railings.create_railing(doc, storey, points, o.base,
                                                             o.height, o.spacing))


class _TerrainOptions:
    type_class = None

    def __init__(self, session: Session):
        self.mode = "outline"  # outline (contorno) ou points (pontos cotados)
        self.boundary_z: float | None = None  # cota do contorno; None = pelas curvas
        self.z = 0.0  # cota do próximo ponto
        self.interval = 1.0
        self.type = None

    def band(self, doc):
        return (0.0, 0.0)


class TerrainTool(LineTool):
    """Terreno (escada-terreno.md §4): desenhe o contorno (Enter ou clique no primeiro
    ponto fecha), ou, no modo de pontos cotados, clique os pontos com Tab para a cota de
    cada um (a cota digitada fica para os seguintes). Pelo menos 3 pontos."""

    name, label = "terrain", "Terreno"
    options_class = _TerrainOptions

    def __init__(self, ctx, options=None):
        super().__init__(ctx, options)
        self.zs: list[float] = []

    def hint(self):
        if self.options.mode == "outline":
            if not self.points:
                return "Clique o primeiro ponto do contorno do terreno"
            return ("Clique o próximo ponto do contorno; clique no primeiro ponto, Enter ou "
                    "clique duplo fecha")
        if not self.points:
            return "Clique o primeiro ponto do terreno; Tab digita a cota"
        return ("Clique o próximo ponto; Tab digita a cota; Enter, clique duplo ou botão "
                "direito encerra (pelo menos 3 pontos)")

    def point_fields(self):
        if self.options.mode == "outline":
            return super().point_fields()  # comprimento e ângulo do lado
        return [Field("z", "Cota", "m", self.options.z, self.fixed.get("z"), True)]

    def _resolve(self, q):
        return super()._resolve(q) if self.options.mode == "outline" else q

    def press(self, p, mods, button="left"):
        if self.options.mode == "outline":
            super().press(p, mods, button)
            return
        z = self.fixed.get("z", self.options.z)
        before = len(self.points)
        super().press(p, mods, button)
        if len(self.points) > before:
            self.zs = [*self.zs[:before], z]
            self.options.z = z

    def cancel(self):
        done = super().cancel()
        if not self.points:
            self.zs = []
        return done

    def finish(self, closed: bool = False) -> None:
        from brasbim.core import terrain

        o, doc = self.options, self.session.doc
        if o.mode == "outline":
            ring = list(self.points)
            self.points, self.zs = [], []
            if len(ring) < 3:
                if ring:
                    self.session.message("o contorno precisa de pelo menos 3 pontos", "recusa")
                return
            self.session.run(lambda: terrain.create_terrain(
                doc, interval=o.interval, boundary=ring, boundary_z=o.boundary_z))
            return
        points = [(*q, z) for q, z in zip(self.points, self.zs, strict=False)]
        self.points, self.zs = [], []
        if len(points) < 3:
            if points:
                self.session.message("o terreno precisa de pelo menos 3 pontos", "recusa")
            return
        self.session.run(lambda: terrain.create_terrain(doc, points, o.interval))

    def shape_preview(self):
        pts = list(self.points)
        if pts and self.snapped:
            pts.append(self.snapped.point)
        return [Mark(tuple(pts), len(pts) >= 3)] if len(pts) >= 2 else []

    def labels(self):
        if self.options.mode == "outline":
            return []
        return [(q, fmt(z)) for q, z in zip(self.points, self.zs, strict=False)]


class _TerrainCurveTool(Tool):
    """Base das ações sobre as curvas de um terreno selecionado (escada-terreno.md §4.4)."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.terrain: str | None = None  # GlobalId do terreno

    def _state(self):
        from brasbim.core import terrain as terrain_data

        element = self.session.doc.find(self.terrain) if self.terrain else None
        if element is None or not terrain_data.is_terrain(element):
            return None
        return terrain_data.read_state(element)

    def _tol(self) -> float:
        return max(self.ctx.tol, 0.05)

    def cancel(self):
        return False  # Esc encerra a ação e volta para Selecionar


class PickCurvesTool(_TerrainCurveTool):
    """Pegar linhas: a linha do desenho (importado ou 2D) sob o cursor vira curva de nível
    do terreno com um clique ou Enter; a cota que ela trazia vem junto (§4.4). Com Shift,
    vêm todas as linhas da mesma camada (spec/ui 30 §6)."""

    name, label = "terrain_pick", "Pegar linhas"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.hover: dict | None = None  # {"points", "closed", "z"}
        self.group: list[dict] = []  # com Shift: as linhas da camada da linha sob o cursor
        self._cache = (None, [])

    def hint(self):
        return ("Passe o cursor sobre uma linha do desenho e clique ou tecle Enter para pô-la "
                "no terreno como curva de nível; com Shift, todas as linhas da camada; Esc "
                "encerra")

    def _candidates(self) -> list[tuple[str, dict, str]]:
        """(GlobalId, {"lines": [...]}, camada) das linhas da planta que podem virar
        curva. A camada do desenho importado é a anotação (uma por camada do arquivo); a
        das linhas desenhadas, a camada de exibição."""
        from brasbim.core import display_layers

        current = self.ctx.plan
        if self._cache[0] is current:
            return self._cache[1]
        doc, out = self.session.doc, []
        for gid, prims in current.annotations:
            element = doc.find(gid)
            kind = annotation_base.kind_of(element)
            if kind is None:
                continue
            if kind.prefix == "reference2d":
                out.append((gid, annotation_base.read_state(element), gid))
            elif kind.prefix in ("line2d", "spline2d", "arc2d", "circle2d"):
                out.append((gid, {"lines": [
                    {"points": [list(q) for q in s.points], "closed": s.closed, "z": None}
                    for s in prims.strokes]},
                    f"camada:{display_layers.layer_of(doc, element)}"))
        self._cache = (current, out)
        return out

    def move(self, p, mods):
        from brasbim.core.annotations import reference

        super().move(p, mods)
        candidates = self._candidates()
        found = reference.lines_near([c[:2] for c in candidates], p, self._tol())
        self.hover = found[0][3] if found else None
        self.group = []
        if found and mods.shift:
            layer = next(c[2] for c in candidates if c[0] == found[0][1])
            self.group = [line for gid, state, other in candidates if other == layer
                          for line in reference.lines_of(state).to_dicts()]

    def _pick(self) -> None:
        from brasbim.core import terrain as terrain_data

        if self.hover is None:
            self.session.message("passe o cursor sobre uma linha do desenho", "recusa")
            return
        if self._state() is None:
            self.session.message("selecione um terreno antes", "recusa")
            return
        lines, doc = self.group or [self.hover], self.session.doc
        if not self.session.run(lambda: terrain_data.add_curves(doc, self.terrain, lines)):
            self.session.message("essa linha já está no terreno" if len(lines) == 1
                                 else "essas linhas já estão no terreno")

    def press(self, p, mods, button="left"):
        if button == "left":
            self.move(p, mods)
            self._pick()

    def key(self, key):
        if key == "enter":
            self._pick()
            return True
        return False

    def preview(self):
        return [Mark(tuple(tuple(q) for q in line["points"]), line["closed"])
                for line in self.group or ([self.hover] if self.hover else [])]

    def labels(self):
        if self.hover is None or self.cursor is None:
            return []
        if self.group:
            return [(self.cursor, f"{len(self.group)} linhas da camada")]
        z = self.hover["z"]
        return [(self.cursor, "sem cota" if z is None else f"cota {fmt(z)}")]


class CurveLevelTool(_TerrainCurveTool):
    """Cota das curvas: clique a curva do terreno e digite a cota (Enter aceita a
    sugestão, a última mais o intervalo das curvas) (§4.4)."""

    name, label = "terrain_level", "Cota das curvas"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.hover: int | None = None
        self.chosen: int | None = None
        self.last: float | None = None

    def hint(self):
        if self.chosen is None:
            return "Clique uma curva de nível do terreno (as tracejadas ainda não têm cota)"
        return "Digite a cota da curva e tecle Enter; clique outra curva para trocar"

    def move(self, p, mods):
        from brasbim.core import terrain as terrain_data

        super().move(p, mods)
        state = self._state()
        self.hover = terrain_data.curve_near(state, p, self._tol()) if state else None

    def suggestion(self) -> float | None:
        state = self._state()
        if state is None or self.chosen is None or self.chosen >= len(state["curves"]):
            return None
        z = state["curves"][self.chosen]["z"]
        if z is not None:
            return z
        return None if self.last is None else self.last + float(state["interval"])

    def fields(self):
        if self.chosen is None:
            return []
        return [Field("z", "Cota", "m", self.suggestion(), self.fixed.get("z"), True)]

    def _apply(self, z: float) -> None:
        from brasbim.core import terrain as terrain_data

        doc, index = self.session.doc, self.chosen
        if self.session.run(lambda: terrain_data.set_curve_level(doc, self.terrain, index, z)):
            self.last = z
        self.chosen = None
        self.fixed.clear()

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        if self.chosen is not None and "z" in self.fixed:
            self._apply(self.fixed["z"])
            return
        self.move(p, mods)
        if self._state() is None:
            self.session.message("selecione um terreno antes", "recusa")
            return
        if self.hover is None:
            self.session.message("clique sobre uma curva de nível do terreno", "recusa")
            return
        self.chosen = self.hover

    def key(self, key):
        if key == "enter" and self.chosen is not None:
            z = self.fixed.get("z", self.suggestion())
            if z is None:
                self.session.message("digite a cota da curva", "recusa")
            else:
                self._apply(z)
            return True
        return False

    def cancel(self):
        if self.chosen is not None:
            self.chosen = None
            self.fixed.clear()
            return True
        return False

    def preview(self):
        state = self._state()
        if state is None:
            return []
        marks = []
        for i, c in enumerate(state["curves"]):
            pts = tuple(tuple(q) for q in c["points"])
            if i == self.chosen:
                marks.append(Mark(pts, c["closed"], "preview"))
            elif i == self.hover:
                marks.append(Mark(pts, c["closed"], "guide"))
            elif c["z"] is None:
                marks.append(Mark(pts, c["closed"], "invalid"))
        return marks


class ViewTool(_PointTool):
    """Corte ou fachada (spec/ui 14 §7): clique A, clique B e clique do lado olhado."""

    kind = "section"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.points: list[Point] = []

    def hint(self):
        noun = "do corte" if self.kind == "section" else "da fachada"
        return [f"Clique o primeiro ponto da linha {noun}",
                f"Clique o segundo ponto da linha {noun}",
                "Clique do lado para onde se olha"][min(len(self.points), 2)]

    def _side(self, q) -> str:
        (ax, ay), (bx, by) = self.points[:2]
        cross = (bx - ax) * (q[1] - ay) - (by - ay) * (q[0] - ax)
        return "left" if cross >= 0 else "right"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        q = self.snapped.point
        if len(self.points) < 2:
            if not self.points or math.dist(q, self.points[0]) > geom2d.MIN_LENGTH:
                self.points.append(q)
            return
        a, b = self.points
        side, doc = self._side(q), self.session.doc
        self.points = []
        self.session.run(lambda: ac.create_view(doc, self.kind, a, b, side))

    def cancel(self):
        if self.points:
            self.points = []
            return True
        return False

    def preview(self):
        if not self.points or not self.snapped:
            return []
        if len(self.points) == 1:
            return [Mark((self.points[0], self.snapped.point), False)]
        from brasbim.core.drawings import views

        state = {**views.default_state(), "kind": self.kind, "a": list(self.points[0]),
                 "b": list(self.points[1]), "side": self._side(self.snapped.point),
                 "letter": "?", "name": "?",
                 "scale": storeys.scale(self.session.storey) if self.session.storey else 50}
        return [Mark(s.points, s.closed) for s in views.symbol(state).strokes]


class SectionTool(ViewTool):
    name, label = "section", "Corte"
    kind = "section"


class ElevationTool(ViewTool):
    name, label = "elevation", "Fachada"
    kind = "elevation"


DIM_DIRECTIONS = {"aligned": ("aligned", 0.0), "horizontal": ("fixed", 0.0),
                  "vertical": ("fixed", 90.0)}


class DimensionTool(_PointTool):
    """Cota (spec/ui 13 §4.5): clique os pontos (presos aos elementos quando há atração);
    com dois ou mais, um clique fora de qualquer ponto de elemento (ou Enter) posiciona a
    linha. Tab digita o afastamento."""

    name, label = "dimension", "Cota"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.direction = "aligned"
        self.items: list[tuple] = []  # (ponto, referência)
        self.hover: tuple | None = None

    def hint(self):
        if len(self.items) < 2:
            return "Clique os pontos a cotar (nos elementos, a cota fica presa a eles)"
        return ("Clique outros pontos para a cadeia, ou fora deles para posicionar a linha "
                "(Enter posiciona no cursor; Tab digita o afastamento)")

    def move(self, p, mods):
        super().move(p, mods)
        storey = self.session.storey
        ref = (annotation_dims.ref_at(self.session.doc, storey, self.snapped.point,
                                      self.ctx.tol) if storey is not None else None)
        point = (annotation_dims.resolve(self.session.doc, ref) if ref else None)
        self.hover = (tuple(point), ref) if point is not None else None
        if self.hover is not None:
            self.snapped = snap.Snap(self.hover[0], "end")

    def _state(self, offset: float) -> dict:
        direction, angle = DIM_DIRECTIONS[self.direction]
        return {"points": ac.dimension_points(self.items), "direction": direction,
                "angle": angle, "offset": offset}

    def _offset(self, q) -> float:
        state = self._state(0.0)
        pts = [tuple(i[0]) for i in self.items]
        _, n = annotation_dims.frame(state, pts)
        return (q[0] - pts[0][0]) * n[0] + (q[1] - pts[0][1]) * n[1]

    def fields(self):
        if len(self.items) < 2 or self.cursor is None:
            return []
        return [Field("offset", "Afastamento", "m", self._offset(self.cursor),
                      self.fixed.get("offset"), True)]

    def _commit(self, offset: float) -> None:
        storey, doc = self._storey(), self.session.doc
        items, (direction, angle) = list(self.items), DIM_DIRECTIONS[self.direction]
        self.items, self.fixed = [], {}
        if storey is not None:
            self.session.run(lambda: ac.create_dimension(doc, storey, items, direction, angle,
                                                         offset))

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        self.move(p, mods)
        if len(self.items) >= 2 and (self.hover is None or "offset" in self.fixed):
            self._commit(self.fixed.get("offset", self._offset(self.snapped.point)))
            return
        item = self.hover or (self.snapped.point, None)
        if self.items and math.dist(item[0], self.items[-1][0]) < 1e-6:
            return
        self.items.append(item)

    def confirm(self):
        if len(self.items) < 2:
            return False
        self._commit(self.fixed.get("offset", self._offset(self.cursor or (0.0, 0.0))))
        return True

    def key(self, key):
        if key == "enter" and len(self.items) >= 2:
            return self.confirm()
        return False

    def cancel(self):
        self.fixed.clear()
        if self.items:
            self.items = []
            return True
        return False

    def preview(self):
        if not self.items or self.cursor is None:
            return []
        if len(self.items) < 2:
            return [Mark((self.items[0][0], self.snapped.point), False)]
        storey = self.session.storey
        offset = self.fixed.get("offset", self._offset(self.cursor))
        prims = annotation_dims.DIMENSION.build(self.session.doc, storey, self._state(offset))
        return [Mark(st.points, st.closed) for st in prims.strokes]

    def labels(self):
        if len(self.items) < 2 or self.cursor is None:
            return []
        storey = self.session.storey
        prims = annotation_dims.DIMENSION.build(self.session.doc, storey,
                                                self._state(self._offset(self.cursor)))
        return [(t.at, t.text) for t in prims.texts]


# --- porta e janela (spec/ui 01 §5.5; spec/ui 09 §2) ------------------------------------


def _filling_tstate(doc, element) -> tuple[bool, dict]:
    """(é janela, estado do tipo) da esquadria; de outra origem, um tipo vazio."""
    window = element.is_a("IfcWindow")
    state = doors.read_state(element)
    if state["foreign"] is None and state["type"]:
        module = window_types if window else door_types
        return window, module.read(doc.get(state["type"]))
    return False, {**door_types.default_state("NOTDEFINED"),
                   "lining": {"thickness": 0, "depth": None}}


def door_marks(doc, wall: snap.WallPath, distance: float, width: float, tstate: dict,
               opens_to: str, align: str, offset: float, style: str = "preview",
               window: bool = False, height: float = 1.0) -> list[Mark]:
    """Pré-visualização da porta (ou da janela) no vão (posição de ``porta.md`` §6.1)."""
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
    if window:
        symbol = plan.window_symbol(width, height, tstate)
    else:
        symbol = plan.door_symbol(width, depth, tstate["operation_type"], lining,
                                  tstate["panels"])
    for _, pts, closed in symbol:
        marks.append(Mark(tuple(frame.to_global(to_wall(q)) for q in pts), closed, style))
    return marks


def _edge_labels(wall: snap.WallPath, distance: float, width: float) -> list[tuple[Point, str]]:
    frame, y = wall.frame, wall.ymax + 0.15
    before, after = distance, wall.path.length - distance - width
    return [(frame.to_global((distance / 2, y)), fmt(before)),
            (frame.to_global((distance + width + after / 2, y)), fmt(after))]


def _door_target(ctx: PlanContext, door, p: Point) -> dict | None:
    """Para onde a esquadria arrastada iria (§5.1): parede reta sob o cursor e distância."""
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
    window, tstate = _filling_tstate(ctx.session.doc, door)
    marks = door_marks(ctx.session.doc, hit.wall, distance, width, tstate, state["opens_to"],
                       state["align"], state["offset"], "invalid" if error else "preview",
                       window, o["height"])
    return {"wall": hit.wall.gid, "distance": distance, "error": error, "marks": marks,
            "labels": _edge_labels(hit.wall, distance, width)}


def face_ends(ctx: PlanContext, wall: snap.WallPath, left: bool) -> tuple[float, float]:
    """Começo e fim (x local) da face da parede do lado ``left`` (cantos do corpo, já com
    as junções); sem o desenho, as pontas do caminho (spec/ui 09 §2.1.2, item 5)."""
    y = wall.ymax if left else wall.ymin
    xs = [wall.frame.to_local(q)[0] for s in ctx.plan.shapes
          if s.owner == wall.gid and s.role in ("wall", "wall_view") for q in s.points
          if abs(wall.frame.to_local(q)[1] - y) < 1e-4]
    return (min(xs), max(xs)) if xs else (0.0, wall.path.length)


class _FillingTool(Tool):
    """Porta e Janela: tipo, vão, mão e posição no marco; distância por ponto de
    referência ao longo da parede (spec/ui 09 §2.1.2)."""

    creates = True
    type_class = ""
    types = door_types
    noun = ""

    def __init__(self, ctx):
        super().__init__(ctx)
        types = sorted(ctx.session.doc.ifc.by_type(self.type_class), key=lambda t: t.Name or "")
        self.type = types[0].GlobalId if types else None
        self.width: float | None = None  # vazio = padrão do tipo
        self.height: float | None = None
        self.base: float | None = None
        self.align = "axis"
        self.offset = 0.0
        self.hinges = "left"
        self.target: dict | None = None

    def type_state(self) -> dict | None:
        found = self.session.doc.find(self.type) if self.type else None
        return self.types.read(found) if found is not None else None

    def hand(self, tstate: dict) -> str | None:
        return params.hand_of(tstate["operation_type"])

    def handed_state(self) -> dict | None:
        """Estado do tipo com a mão escolhida (variante, se for o caso)."""
        tstate = self.type_state()
        if tstate is None:
            return None
        hand = self.hand(tstate)
        if hand is not None and hand != self.hinges:
            return self.types.mirrored(tstate, None)
        return tstate

    def hint(self):
        if self.type_state() is None:
            return f"Não há tipo de {self.noun} no projeto"
        ref = ("; pare o cursor num vértice para medir a partir dele" if self.reference is None
               else "; Esc solta a referência")
        return f"Passe o cursor sobre uma parede reta e clique; Tab digita a distância{ref}"

    # campos (spec/ui 09 §2.1)

    def fields(self):
        t = self.target
        if not t or "distance" not in t:
            return []
        return [Field("ref", "Distância", "m", t["ref_distance"], self.fixed.get("ref"))]

    def check(self, key, value):
        if value < 0:
            return "a distância não pode ser negativa"
        return None

    def cancel(self):
        self.fixed.clear()
        return self.release_reference()

    def _reference_x(self, wall: snap.WallPath, hit: snap.WallHit, along: float) -> float:
        """Abscissa (ao longo da parede) do ponto de referência."""
        if self.reference is not None:
            return wall.frame.to_local(self.reference)[0]
        start, end = face_ends(self.ctx, wall, hit.left)
        return start if abs(along - start) <= abs(along - end) else end

    def move(self, p, mods):
        super().move(p, mods)
        self.target = None
        tstate = self.handed_state()
        hit = snap.wall_at(self.ctx.walls, p, self.ctx.tol)
        if tstate is None or hit is None:
            return
        if not hit.wall.straight:
            self.target = {"error": f"{self.noun} em parede em arco ainda não é suportada (V1)",
                           "marks": [], "labels": []}
            return
        defaults = tstate["defaults"]
        width = self.width or defaults["width"]
        height = self.height or defaults["height"]
        base = defaults["base"] if self.base is None else self.base
        wall = hit.wall
        along = hit.along
        length = wall.path.length
        if not mods.alt and abs(along - length / 2) <= self.ctx.tol:
            along = length / 2  # snap ao meio da parede
        ref_x = self._reference_x(wall, hit, along)
        after = along >= ref_x  # a esquadria fica depois da referência
        fixed = self.fixed.get("ref")
        if fixed is not None:
            distance = ref_x + fixed if after else ref_x - fixed - width
        else:
            distance = along - width / 2
        ref_distance = distance - ref_x if after else ref_x - distance - width
        edge_x = distance if after else distance + width
        opens_to = "left" if hit.left else "right"
        error = None
        try:
            openings.check_fits(self.session.doc, self.session.doc.get(wall.gid), {
                **openings.default_state(), "wall": wall.gid, "distance": distance,
                "width": width, "height": height, "sill": base})
        except OpError as e:
            error = str(e)
        y = (wall.ymin + wall.ymax) / 2
        ref_point = (self.reference if self.reference is not None
                     else wall.frame.to_global((ref_x, wall.ymax if hit.left else wall.ymin)))
        ref_y = wall.frame.to_local(ref_point)[1]
        self.target = {
            "wall": wall.gid, "distance": distance, "width": width, "height": height,
            "base": base, "opens_to": opens_to, "error": error,
            "ref_distance": max(ref_distance, 0.0),
            "ref_line": (ref_point, wall.frame.to_global((edge_x, ref_y))),
            "marks": door_marks(self.session.doc, wall, distance, width, tstate, opens_to,
                                self.align, self.offset, "invalid" if error else "preview",
                                self.type_class == "IfcWindowType", height),
            "labels": _edge_labels(wall, distance, width) + self.size_labels(
                wall, distance, width, height, base, y),
        }

    def size_labels(self, wall, distance, width, height, base, y) -> list:
        return []

    def field_anchor(self) -> Point | None:
        t = self.target
        if not t or "ref_line" not in t:
            return None
        (x0, y0), (x1, y1) = t["ref_line"]
        return ((x0 + x1) / 2, (y0 + y1) / 2)

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
        hinges = self.hinges if self.hand(tstate) else None
        doc = self.session.doc
        self.session.run(lambda: fc.create_door(
            doc, self.type, target["wall"], target["distance"], target["width"],
            target["height"], target["base"], hinges=hinges, opens_to=target["opens_to"],
            align=self.align, offset=self.offset))
        self.fixed.pop("ref", None)
        self.move(p, mods)

    def preview(self):
        if not self.target:
            return []
        marks = list(self.target["marks"])
        if "ref_line" in self.target:
            marks.append(Mark(self.target["ref_line"], False, "guide"))
        return marks

    def labels(self):
        return self.target["labels"] if self.target else []


class DoorTool(_FillingTool):
    name, label = "door", "Porta"
    type_class = "IfcDoorType"
    types = door_types
    noun = "porta"


class WindowTool(_FillingTool):
    name, label = "window", "Janela"
    type_class = "IfcWindowType"
    types = window_types
    noun = "janela"

    def hand(self, tstate):
        return window_types.hand(tstate)

    def fields(self):
        out = super().fields()
        if out:
            out.append(Field("sill", "Peitoril", "m", self.target["base"]))
        return out

    def fix(self, key, value):
        if key == "sill":  # vale para as próximas janelas (spec/ui 09 §2.1)
            if value is not None and value < 0:
                return "o peitoril não pode ser negativo"
            self.base = value
            if self.cursor is not None:
                self.move(self.cursor, self.mods)
            return None
        return super().fix(key, value)

    def size_labels(self, wall, distance, width, height, base, y):
        at = wall.frame.to_global((distance + width / 2, wall.ymin - 0.25))
        return [(at, f"peitoril {fmt(base)} · verga {fmt(base + height)}")]


# --- dividir (0.2 §5) -----------------------------------------------------------------------


class _OpeningOptions2:
    """Opções da ferramenta Vão (spec/ui 20 §3)."""

    def __init__(self):
        self.kind = "OPENING"  # ou RECESS (nicho)
        self.width = 0.80
        self.height = 2.10
        self.sill = 0.0
        self.depth = 0.05


class WallOpeningTool(_FillingTool):
    """Vão passante ou nicho na parede (spec/ui 20 §3): como a porta, sem esquadria."""

    name, label = "wall_opening", "Vão"
    type_class = "IfcDoorType"  # não usa tipo; ``type_state`` dá as medidas da barra Opções
    noun = "vão"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.type = None
        self.options = _OpeningOptions2()

    def type_state(self) -> dict | None:
        o = self.options
        return {"defaults": {"width": o.width, "height": o.height, "base": o.sill},
                "operation_type": "NOTDEFINED"}

    def handed_state(self) -> dict | None:
        return self.type_state()

    def hand(self, tstate: dict) -> str | None:
        return None

    def hint(self):
        what = "o vão" if self.options.kind == "OPENING" else "o nicho"
        return (f"Passe o cursor sobre uma parede reta e clique para abrir {what}; Tab "
                "digita a distância")

    def move(self, p, mods):
        self.width = self.height = self.base = None
        # a porta desenha folha e marco: aqui só o retângulo do vão na faixa da parede
        Tool.move(self, p, mods)
        self.target = None
        hit = snap.wall_at(self.ctx.walls, p, self.ctx.tol)
        if hit is None:
            return
        if not hit.wall.straight:
            self.target = {"error": "vão em parede em arco ainda não é suportado (V1)",
                           "marks": [], "labels": []}
            return
        o = self.options
        wall, along = hit.wall, hit.along
        if not mods.alt and abs(along - wall.path.length / 2) <= self.ctx.tol:
            along = wall.path.length / 2
        ref_x = self._reference_x(wall, hit, along)
        after = along >= ref_x
        fixed = self.fixed.get("ref")
        if fixed is not None:
            distance = ref_x + fixed if after else ref_x - fixed - o.width
        else:
            distance = along - o.width / 2
        side = "left" if hit.left else "right"
        state = {**openings.default_state(), "wall": wall.gid, "kind": o.kind,
                 "distance": distance, "width": o.width, "height": o.height,
                 "sill": o.sill, "depth": o.depth if o.kind == "RECESS" else None,
                 "side": side}
        error = None
        try:
            openings.check_fits(self.session.doc, self.session.doc.get(wall.gid), state)
        except OpError as e:
            error = str(e)
        if o.kind == "RECESS":
            y0, y1 = ((wall.ymax - o.depth, wall.ymax) if side == "left"
                      else (wall.ymin, wall.ymin + o.depth))
        else:
            y0, y1 = wall.ymin, wall.ymax
        ring = tuple(wall.frame.to_global(q) for q in ((distance, y0), (distance + o.width, y0),
                                                       (distance + o.width, y1),
                                                       (distance, y1)))
        ref_point = (self.reference if self.reference is not None
                     else wall.frame.to_global((ref_x, wall.ymax if hit.left else wall.ymin)))
        edge_x = distance if after else distance + o.width
        ref_y = wall.frame.to_local(ref_point)[1]
        self.target = {
            "state": state, "error": error,
            "ref_distance": max(distance - ref_x if after else ref_x - distance - o.width, 0.0),
            "distance": distance,
            "ref_line": (ref_point, wall.frame.to_global((edge_x, ref_y))),
            "marks": [Mark(ring, True, "invalid" if error else "preview")],
            "labels": _edge_labels(wall, distance, o.width)}

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
        s, doc = target["state"], self.session.doc
        self.session.run(lambda: cmd.create_opening(
            doc, s["wall"], s["distance"], s["width"], s["height"], s["sill"], s["kind"],
            s["depth"], s["side"]))
        self.fixed.pop("ref", None)
        self.move(p, mods)


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

    guided = True  # pontos de referência e linhas-guia (spec/ui 37 §2)

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
    """Copiar; com o campo Cópias (ou ``x5`` no de distância), N cópias com o mesmo
    passo (spec/ui 30 §9)."""

    name, label = "copy", "Copiar"
    copies = True

    def __init__(self, ctx):
        super().__init__(ctx)
        self.count = 1

    def hint(self):
        text = super().hint()
        if self.points and self.session.selection:
            text += "; Cópias (ou x5 na distância) faz a cópia em série"
        return text

    def fields(self):
        out = super().fields()
        if out:
            out.append(Field("copies", "Cópias", "", float(self.count),
                             float(self.count) if self.count > 1 else None))
        return out

    def check(self, key, value):
        if key == "copies":
            if abs(value - round(value)) > 1e-9 or not 1 <= value <= transform.MAX_COPIES:
                return f"o número de cópias é inteiro, de 1 a {transform.MAX_COPIES}"
            return None
        return super().check(key, value)

    def fix(self, key, value):
        if key == "copies":  # vale para os próximos cliques, até Esc
            error = None if value is None else self.check(key, value)
            if error:
                return error
            self.count = 1 if value is None else round(value)
            if self.cursor is not None:
                self.move(self.cursor, self.mods)
            return None
        return super().fix(key, value)

    def release_fixed(self):
        self.count = 1
        super().release_fixed()

    def cancel(self):
        busy = super().cancel()
        self.count = 1
        return busy

    def _apply(self, vector):
        if self.count == 1:
            super()._apply(vector)
            return
        doc, gids, count = self.session.doc, self._gids(), self.count
        self.session.run(lambda: transform.copy_series(doc, gids, vector, count))

    def preview(self):
        marks = super().preview()
        fn = self.transform_fn()
        if fn is None or self.count == 1:
            return marks
        dx, dy = self._vector(self.snapped.point)
        shapes = self._shapes()
        for k in range(2, min(self.count, 50) + 1):  # fantasma das demais cópias
            marks += _shape_marks(shapes, geom2d.translation((k * dx, k * dy)))
        return marks


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
        classes = ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab", "IfcRoof")

        def found():
            return {e.GlobalId for c in classes for e in doc.ifc.by_type(c)}

        before = found()
        if self.session.run(lambda: transform.mirror_elements(doc, gids, a, q, keep=mods.ctrl)) \
                and mods.ctrl:
            self.session.select(found() - before)
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


# --- Objeto paramétrico (objeto-parametrico.md §4.4) ---------------------------------------

HOST_REACH = 0.60  # m: até onde, na frente da parede, o objeto preso ainda encosta nela


class ObjectTool(Tool):
    """Objeto paramétrico: um clique põe o tipo escolhido. Livre: barra de espaço gira 90°,
    Tab digita a rotação, Shift + clique e um segundo clique dão a direção da frente. Preso à
    parede: encosta na face mais próxima; Tab digita a distância e a altura."""

    name, label = "object", "Objeto"
    type_class = None  # tipos de objeto: a ferramenta confere o seu (``check_types`` pula)
    creates = True

    def __init__(self, ctx):
        super().__init__(ctx)
        self.type: str | None = None
        self.angle = 0.0
        self.mirror = False
        self.values: dict = {}  # parâmetros de ocorrência escolhidos na barra Opções
        self.point: Point | None = None
        self.first: Point | None = None  # Shift + clique: ponto, falta a direção
        self.host: dict | None = None
        self._cache = None
        self.on_missing_type = None  # sem tipo: a janela abre a biblioteca

    # tipo e cálculo

    def type_entity(self):
        doc = self.session.doc
        t = doc.find(self.type) if self.type else None
        if t is None or not object_types.is_object_type(t):
            self.type = None
            return None
        return t

    def type_state(self) -> dict | None:
        t = self.type_entity()
        return object_types.read(t) if t is not None else None

    def built(self):
        t = self.type_entity()
        if t is None:
            return None
        key = (t.GlobalId, repr(sorted(self.values.items())), self.mirror,
               len(self.session.history.undo_stack))
        if self._cache is None or self._cache[0] != key:
            tstate = object_types.read(t)
            values = object_types.stored_values(tstate["definition"],
                                                {**tstate["defaults"], **self.values},
                                                "occurrence")
            try:
                built = objects.build(self.session.doc, tstate, values, self.mirror)
            except OpError as e:
                self._cache = (key, None, str(e))
            else:
                self._cache = (key, built, None)
        return self._cache[1]

    def hosted(self) -> bool:
        built = self.built()
        return built is not None and built.definition["hosting"] == "wall"

    def set_type(self, gid: str | None) -> None:
        self.type, self.values, self.first = gid, {}, None
        if self.cursor is not None:
            self.move(self.cursor, self.mods)

    # campos

    def hint(self):
        if self.type_entity() is None:
            return "Escolha o objeto na barra Opções ou na biblioteca (Ctrl+Shift+B)"
        if self.hosted():
            return "Passe o cursor perto de uma parede e clique; Tab digita distância e altura"
        if self.first is not None:
            return "Clique a direção da frente do objeto; Esc cancela"
        return ("Clique o ponto de inserção; barra de espaço gira 90°; Shift + clique "
                "e um segundo clique dão a direção")

    def fields(self):
        if self.cursor is None or self.type_entity() is None:
            return []
        if self.hosted():
            if self.host is None:
                return []
            built = self.built()
            elevation = float(built.values.get("elevacao", 0.0)) if built else 0.0
            return [Field("distance", "Distância", "m", self.host["distance"],
                          self.fixed.get("distance")),
                    Field("elevation", "Altura", "m", elevation, self.fixed.get("elevation"))]
        return [Field("angle", "Rotação", "°", self.angle)]

    def fix(self, key, value):
        if key == "angle":
            if value is not None:
                self.angle = (value + 180.0) % 360.0 - 180.0
            if self.cursor is not None:
                self.move(self.cursor, self.mods)
            return None
        return super().fix(key, value)

    # movimento

    def _wall_hit(self, p: Point):
        walls = [w for w in self.ctx.walls if w.straight]
        return snap.wall_at(walls, p, max(self.ctx.tol, HOST_REACH))

    def move(self, p, mods):
        super().move(p, mods)
        if self.hosted():
            self.snapped = None
            self.point = p
            hit = self._wall_hit(p)
            built = self.built()
            if hit is None or built is None:
                self.host = None
                return
            box = built.box or (0, 0, 0, 0, 0, 0)
            wall = self.session.doc.find(hit.wall.gid)
            host = hosting.at_point(self.session.doc, wall, p, box[1] - box[0])
            if host is not None and "distance" in self.fixed:
                host["distance"] = self.fixed["distance"]
            self.host = host
            return
        self.host = None
        if self.first is not None:
            self.snapped = self.ctx.snap(p, mods, origin=self.first)
            q = self.snapped.point
            if math.dist(q, self.first) > 1e-6:
                # a frente (−y local) olha para o segundo ponto
                angle = math.degrees(math.atan2(q[1] - self.first[1], q[0] - self.first[0]))
                self.angle = (angle + 90.0 + 180.0) % 360.0 - 180.0
            self.point = self.first
            return
        self.snapped = self.ctx.snap(p, mods, extra=self.ctx.vertices)
        self.point = self.snapped.point

    def key(self, key):
        if key == "space" and not self.hosted():
            self.angle = (self.angle + 90.0 + 180.0) % 360.0 - 180.0
            return True
        return False

    def cancel(self):
        if self.first is not None:
            self.first = None
            return True
        self.fixed.clear()
        return self.release_reference()

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        if self.type_entity() is None:
            self.session.message("escolha o objeto na barra Opções ou na biblioteca",
                                 "recusa")
            if self.on_missing_type is not None:
                self.on_missing_type()
            return
        if self.session.storey is None:
            self.session.message("não há pavimento ativo", "recusa")
            return
        if not self.hosted() and mods.shift and self.first is None:
            self.move(p, mods)
            self.first = self.point
            return
        self.move(p, mods)
        doc, storey = self.session.doc, self.session.storey
        values = dict(self.values)
        if self.hosted():
            if self.host is None:
                self.session.message("clique perto de uma parede reta", "recusa")
                return
            if "elevation" in self.fixed:
                values["elevacao"] = self.fixed["elevation"]
            host = dict(self.host)
            self.session.run(lambda: object_cmd.create_object(
                doc, self.type, storey, (0.0, 0.0), mirror=self.mirror, values=values,
                host=host))
        else:
            point, angle = self.point, self.angle
            self.session.run(lambda: object_cmd.create_object(
                doc, self.type, storey, point, angle=angle, mirror=self.mirror,
                values=values))
        self.first = None
        self.fixed.clear()
        self.tracking = None
        self.move(p, mods)

    # desenho

    def _ghost(self) -> list[tuple[list[Point], bool]]:
        built = self.built()
        if built is None or self.point is None:
            return []
        if self.hosted():
            if self.host is None:
                return []
            try:
                frame = hosting.local_frame(self.session.doc, self.host, built)
            except OpError:
                return []
            origin, angle = frame["point"], frame["angle"]
        else:
            origin, angle = self.point, self.angle
        a = math.radians(angle)
        c, s_ = math.cos(a), math.sin(a)
        k = -1.0 if self.mirror else 1.0
        out = []
        for points, closed, _ in object_plan.local_symbol(built):
            out.append(([(origin[0] + c * k * x - s_ * y, origin[1] + s_ * k * x + c * y)
                         for x, y in points], closed))
        return out

    def preview(self):
        if self.type_entity() is None or self.cursor is None:
            return []
        style = "invalid" if self.hosted() and self.host is None else "preview"
        marks = [Mark(tuple(points), closed, style) for points, closed in self._ghost()]
        if self.first is not None:
            marks.append(Mark((self.first, self.cursor), False, "guide"))
        return marks

    def labels(self):
        if self._cache is not None and self._cache[2] and self.cursor is not None:
            return [(self.cursor, self._cache[2])]
        return []


# --- deslocar paralela, aparar/estender, concordar (spec/ui 23 §4–§6) ---------------------


def _geometry_marks(doc, element, changes: dict, style="preview") -> list[Mark]:
    """Fantasma do elemento com o estado novo (só o traço)."""
    if "path" in changes:
        path = changes["path"]
        frame = geom2d.frame(path)
        n = 1 if isinstance(path, geom2d.LinePath) else 24
        pts = [frame.to_global(path.point(0.0, path.t_end * k / n)) for k in range(n + 1)]
        return [Mark(tuple(pts), False, style)]
    if "radius" in changes:
        state = annotation_base.read_state(element)
        c, r = state["center"], changes["radius"]
        a0, a1 = (state.get("start", 0.0), state.get("end", 360.0))
        sweep = (a1 - a0) % 360.0 or 360.0
        pts = [(c[0] + r * math.cos(math.radians(a0 + sweep * k / 48)),
                c[1] + r * math.sin(math.radians(a0 + sweep * k / 48))) for k in range(49)]
        return [Mark(tuple(pts), False, style)]
    key = "points" if "points" in changes else "outline"
    closed = key == "outline" or annotation_base.read_state(element).get("closed", False)
    return [Mark(tuple(tuple(q) for q in changes[key]), closed, style)]


def _cursor_distance(doc, element, kind: str, q: Point) -> float:
    if kind == "wall":
        path = geom2d.path_from_dict(cmd.read_state(doc, element)["path"])
        return abs(path.offset(geom2d.frame(path).to_local(q)))
    if kind in ("circle2d", "arc2d"):
        state = annotation_base.read_state(element)
        return abs(math.dist(q, state["center"]) - state["radius"])
    if kind == "line2d":
        state = annotation_base.read_state(element)
        return edits.distance_to(state["points"], state.get("closed", False), q)
    state = (annotation_base.read_state(element) if element.is_a("IfcAnnotation")
             else ac.read_state(doc, element) if kind == "space"
             else sc.read_state(doc, element))
    return edits.distance_to(state["outline"], True, q)


class OffsetTool(Tool):
    """Deslocar paralela (spec/ui 23 §4): clique o elemento, depois o lado; a distância
    vem do cursor ou do quadro e continua fixada para o próximo elemento."""

    name, label = "offset", "Deslocar paralela"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.target: str | None = None
        self.copy = True  # barra Opções: Copiar / Mover o original

    def _element(self):
        return self.session.doc.find(self.target) if self.target else None

    def hint(self):
        if self.target is None:
            fixed = self.fixed.get("distance")
            extra = f" (distância fixada: {fmt(fixed)} m; Esc solta)" if fixed else ""
            return "Clique a parede, linha, círculo, arco ou contorno a deslocar" + extra
        return "Clique do lado para onde deslocar; digite a distância; Esc escolhe outro"

    def _distance(self) -> float | None:
        if "distance" in self.fixed:
            return self.fixed["distance"]
        element = self._element()
        if element is None or self.snapped is None:
            return None
        return _cursor_distance(self.session.doc, element,
                                edits.kind_of(self.session.doc, element), self.snapped.point)

    def fields(self):
        if self.target is None:
            return []
        return [Field("distance", "Distância", "m", self._distance(),
                      self.fixed.get("distance"))]

    def check(self, key, value):
        return "a distância deve ser positiva" if value <= 0 else None

    def move(self, p, mods):
        super().move(p, mods)
        self.snapped = self.ctx.snap(p, mods)

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        doc = self.session.doc
        if self.target is None:
            gid = self.ctx.plan.pick(p, self.ctx.tol)
            element = doc.find(gid) if gid else None
            if edits.kind_of(doc, element) is None:
                self.session.message("escolha uma parede, linha 2D, círculo, arco ou o "
                                     "contorno de laje, ambiente ou hachura", "recusa")
                return
            self.target = gid
            return
        self.move(p, mods)
        distance = self._distance()
        element = self._element()
        if element is None or not distance or distance <= 1e-6:
            return
        copy, q = self.copy, self.snapped.point
        self.session.run(lambda: edits.offset_element(doc, element, distance, q, copy))
        self.target = None

    def confirm(self):
        if self.target is None or self.cursor is None:
            return False
        self.press(self.cursor, self.mods)
        return True

    def numeric(self, value):
        error = self.fix("distance", value)
        if error:
            self.session.message(error, "recusa")
        return True

    def cancel(self):
        if self.target is not None:
            self.target = None
            return True
        if self.fixed:
            self.fixed.clear()
            return True
        return False

    def preview(self):
        element, distance = self._element(), self._distance()
        if element is None or not distance or self.snapped is None:
            return []
        try:
            changes = edits.offset_geometry(self.session.doc, element, distance,
                                            self.snapped.point)
        except OpError:
            return []
        return _geometry_marks(self.session.doc, element, changes)


class TrimTool(Tool):
    """Aparar/estender (spec/ui 23 §5): todas as arestas visíveis são limite."""

    name, label = "trim", "Aparar/estender"

    def hint(self):
        return ("Clique o trecho a aparar, ou perto da ponta solta para estender "
                "(Shift: estende); paredes retas vão até o eixo da outra")

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        doc = self.session.doc
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        element = doc.find(gid) if gid else None
        if edits.kind_of(doc, element) not in ("line2d", "wall"):
            self.session.message("clique numa linha 2D ou numa parede reta", "recusa")
            return
        index, extend = self.ctx.index, mods.shift
        self.session.run(lambda: edits.trim_extend(doc, element, p, index, extend))


class FilletTool(Tool):
    """Concordar (spec/ui 23 §6): dois cliques; raio na barra Opções (0 = canto vivo)."""

    name, label = "fillet", "Concordar"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.radius = 0.0
        self.first: tuple[str, Point] | None = None

    def hint(self):
        if self.first is None:
            return "Clique a primeira linha 2D ou parede reta, do lado que fica"
        return "Clique a segunda, do lado que fica (Shift: raio 0); Esc recomeça"

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        doc = self.session.doc
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        element = doc.find(gid) if gid else None
        if edits.kind_of(doc, element) not in ("line2d", "wall"):
            self.session.message("clique numa linha 2D ou numa parede reta", "recusa")
            return
        if self.first is None:
            self.first = (gid, p)
            return
        (g1, p1), self.first = self.first, None
        first, radius = doc.get(g1), 0.0 if mods.shift else self.radius
        self.session.run(lambda: edits.fillet(doc, first, p1, element, p, radius))

    def cancel(self):
        if self.first is not None:
            self.first = None
            return True
        return False

    def preview(self):
        if self.first is None:
            return []
        return [Mark(s.points, s.closed) for s in self.ctx.plan.shapes
                if s.owner == self.first[0]]


# --- Medir (spec/ui 30 §7) -------------------------------------------------------------


def _area_text(points) -> str:
    perimeter = sum(math.dist(a, b) for a, b in zip(points, [*points[1:], points[0]]))
    return (f"área {fmt(geom2d.polygon_area(list(points)))} m², "
            f"perímetro {fmt(perimeter)} m")


class MeasureTool(Tool):
    """Medir: cadeia de pontos com o total; fechar no primeiro ponto dá área e
    perímetro; Shift+clique num elemento mede o contorno dele. Não cria nada: o resultado
    vai para a barra de estado e para o painel Mensagens."""

    name, label = "measure", "Medir"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.points: list[Point] = []
        self.result = ""  # última medida (barra de estado)

    creates = True

    def hint(self):
        if not self.points:
            text = ("Clique o primeiro ponto; Shift+clique num elemento mede o contorno "
                    "dele")
        else:
            text = ("Clique o próximo ponto; no primeiro, fecha e dá a área; Enter ou "
                    "clique duplo encerra; Esc descarta")
        return f"{self.result}. {text}" if self.result else text

    def _point(self, p, mods) -> Point:
        origin = self.points[-1] if self.points else None
        self.snapped = self.ctx.snap(p, mods, origin, extra=self.points)
        if self.points and self.fixed:
            self.snapped = snap.Snap(polar_point(origin, self.snapped.point,
                                                 self.fixed.get("length"),
                                                 self.fixed.get("angle")), "free")
        return self.snapped.point

    def move(self, p, mods):
        super().move(p, mods)
        self._point(p, mods)

    def fields(self):
        if not self.points:
            return []
        last, q = self.points[-1], self.snapped.point if self.snapped else None
        length = math.dist(last, q) if q else None
        angle = _degrees(q[0] - last[0], q[1] - last[1]) if q and length > 1e-9 else None
        return [Field("length", "Distância", "m", length, self.fixed.get("length")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def check(self, key, value):
        if key == "length" and value <= 0:
            return "a distância deve ser maior que zero"
        return None

    def _report(self, text: str) -> None:
        self.result = text
        self.session.message(text)

    def _closes(self, q: Point) -> bool:
        return len(self.points) >= 3 and math.dist(q, self.points[0]) <= max(self.ctx.tol,
                                                                             1e-6)

    def press(self, p, mods, button="left"):
        if button == "right":
            self.finish()
            return
        if mods.shift and not self.points:
            self.measure_element(p)
            return
        q = self._point(p, mods)
        self.fixed.clear()
        if self._closes(q):
            points, self.points = self.points, []
            self._report(f"Medida: {_area_text(points)}")
        elif not self.points or math.dist(q, self.points[-1]) > 1e-9:
            self.points.append(q)

    def double(self, p, mods):
        self.finish()

    def key(self, key):
        if key == "enter":
            self.finish()
            return True
        return False

    def finish(self) -> None:
        points, self.points = self.points, []
        if len(points) < 2:
            return
        parts = [math.dist(a, b) for a, b in itertools.pairwise(points)]
        text = f"Medida: {fmt(sum(parts))} m"
        if len(parts) > 1:
            text += f" ({' + '.join(fmt(d) for d in parts)})"
        self._report(text)

    def measure_element(self, p: Point) -> None:
        """Área e perímetro do contorno de um elemento (o maior, se houver vários), ou o
        comprimento das linhas de uma anotação."""
        gid = self.ctx.plan.pick(p, self.ctx.tol)
        if gid is None:
            self.session.message("não há elemento sob o cursor", "recusa")
            return
        element = self.session.doc.find(gid)
        name = (getattr(element, "Name", None) or element.is_a()) if element else gid
        closed = [s.points for s in self.ctx.plan.shapes
                  if s.owner == gid and s.closed and len(s.points) >= 3]
        if closed:
            points = max(closed, key=lambda pts: geom2d.polygon_area(list(pts)))
            self._report(f"Medida de {name}: {_area_text(points)}")
            return
        strokes = [st for owner, prims in self.ctx.plan.annotations if owner == gid
                   for st in prims.strokes]
        strokes += [s for s in self.ctx.plan.shapes if s.owner == gid]
        length = 0.0
        for st in strokes:
            pts = list(st.points)
            if st.closed and len(pts) > 2:
                pts.append(pts[0])
            length += sum(math.dist(a, b) for a, b in itertools.pairwise(pts))
        if length <= 0:
            self.session.message(f"{name}: sem contorno para medir", "recusa")
            return
        self._report(f"Medida de {name}: comprimento {fmt(length)} m")

    def cancel(self):
        self.fixed.clear()
        if self.points:
            self.points = []
            return True
        return False

    def preview(self):
        pts = list(self.points)
        if pts and self.snapped:
            pts.append(self.snapped.point)
        marks = [Mark(tuple(pts), False)] if len(pts) >= 2 else []
        if len(pts) >= 3:
            marks.append(Mark((pts[-1], pts[0]), False, "gap"))
        if self.points and "angle" in self.fixed:
            marks.append(_guide(self.points[-1], self.fixed["angle"], self.ctx.tol))
        return marks

    def labels(self):
        pts = list(self.points)
        if not pts or not self.snapped:
            return []
        pts.append(self.snapped.point)
        out = [(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), fmt(math.dist(a, b)))
               for a, b in itertools.pairwise(pts) if math.dist(a, b) > 1e-9]
        total = sum(math.dist(a, b) for a, b in itertools.pairwise(pts))
        text = f"total {fmt(total)} m"
        if len(pts) >= 3:
            text += f"; {_area_text(pts)}"
        out.append((pts[-1], text))
        return out


# --- área de seleção (spec/ui 38 §2, §3) -----------------------------------------------------


class AreaTool(Tool):
    """Área de seleção: desenha a área (retângulo ou polígono), move a área e estica o que
    tem pontos dentro dela. A área fica no ``PlanContext`` ao trocar de ferramenta."""

    name, label = "selection_area", "Área de seleção"
    number_hint = "distância"
    creates = True
    STRETCH_SNAPS = ("end", "inter")  # vértice ou ponta: estica; outro ponto: move a área

    def __init__(self, ctx):
        super().__init__(ctx)
        self.shape = "rectangle"  # ou "polygon"
        self.all_storeys = False
        self.points: list[Point] = []
        self.pressed: Point | None = None  # 1º canto apertado: soltar longe fecha o retângulo
        self.drag: dict | None = None  # esticar ou mover a área: base, início, ativo, preso

    def hint(self):
        if self.drag is not None:
            verb = "esticar" if self.drag["kind"] == "stretch" else "mover a área"
            return f"Clique o destino para {verb}; Tab digita distância e ângulo; Esc cancela"
        if self.points:
            if self.shape == "rectangle":
                return "Clique o canto oposto; Tab digita largura e altura; Esc cancela"
            return ("Clique o próximo ponto; no primeiro, Enter ou clique duplo fecha; "
                    "Esc cancela")
        text = ("Clique o primeiro canto da área" if self.shape == "rectangle"
                else "Clique o primeiro ponto da área")
        if self.ctx.area is not None:
            text += ("; arraste um vértice dentro da área para esticar, ou outro ponto dentro "
                     "para mover a área; Esc remove a área")
        return text

    def _origin(self) -> Point | None:
        if self.drag is not None:
            return self.drag["base"]
        return self.points[-1] if self.points else None

    def _point(self, p, mods) -> Point:
        origin = self._origin()
        self.snapped = self.ctx.snap(p, mods, origin, extra=self.points)
        if origin is not None and self.fixed:
            self.snapped = snap.Snap(self._resolve(self.snapped.point), "free")
        return self.snapped.point

    def _drawing_rect(self) -> bool:
        return self.drag is None and self.shape == "rectangle" and bool(self.points)

    def _resolve(self, q: Point) -> Point:
        if self._drawing_rect():
            return rect_corner(self.points[0], q, self.fixed.get("width"),
                               self.fixed.get("height"))
        return polar_point(self._origin(), q, self.fixed.get("distance"),
                           self.fixed.get("angle"))

    def fields(self):
        origin = self._origin()
        if origin is None:
            return []
        q = self.snapped.point if self.snapped else None
        if self._drawing_rect():
            return [Field("width", "Largura", "m", abs(q[0] - origin[0]) if q else None,
                          self.fixed.get("width")),
                    Field("height", "Altura", "m", abs(q[1] - origin[1]) if q else None,
                          self.fixed.get("height"))]
        v = (q[0] - origin[0], q[1] - origin[1]) if q else None
        length = math.hypot(*v) if v else None
        angle = _degrees(*v) if v and length > 1e-9 else None
        return [Field("distance", "Distância", "m", length, self.fixed.get("distance")),
                Field("angle", "Ângulo", "°", angle, self.fixed.get("angle"))]

    def check(self, key, value):
        if key != "angle" and value <= 1e-9:
            return "o valor deve ser maior que zero"
        return None

    def move(self, p, mods):
        super().move(p, mods)
        d = self.drag
        if d is not None and not d["active"]:
            if math.dist(p, d["start"]) < self.ctx.tol * DRAG_START:
                return
            d["active"] = True
        self._point(p, mods)

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self._point(p, mods)
        self.fixed.clear()
        if self.drag is not None:  # destino depois de clicar a base (ou Enter no quadro)
            self._drop(q)
        elif self.points:
            self._add(q)
        elif self.ctx.area is not None and self.ctx.area.contains(q):
            kind = "stretch" if self.snapped.kind in self.STRETCH_SNAPS else "move"
            self.drag = {"kind": kind, "base": q, "start": p, "active": False,
                         "sticky": False}
        else:
            self.points, self.pressed = [q], p

    def release(self, p, mods):
        d, pressed, self.pressed = self.drag, self.pressed, None
        if d is not None:
            if not d["active"]:
                d["sticky"] = True  # clique sem arrastar: o destino é o próximo clique
            elif not d["sticky"]:
                self._drop(self._point(p, mods))
        elif (self.shape == "rectangle" and len(self.points) == 1 and pressed is not None
              and math.dist(p, pressed) >= self.ctx.tol * DRAG_START):
            self._add(self._point(p, mods))  # retângulo arrastado

    def double(self, p, mods):
        if self.shape == "polygon" and len(self.points) >= 3:
            self._finish(self.points)

    def key(self, key):
        if key == "enter" and self.shape == "polygon" and len(self.points) >= 3:
            self._finish(self.points)
            return True
        return False

    def _add(self, q: Point) -> None:
        if self.shape == "rectangle":
            if math.dist(q, self.points[0]) > 1e-9:
                self._finish(selection_area.Area.rectangle(self.points[0], q).points)
            return
        if len(self.points) >= 3 and math.dist(q, self.points[0]) <= self.ctx.tol:
            self._finish(self.points)  # fechou no primeiro ponto
        elif math.dist(q, self.points[-1]) > 1e-9:
            self.points.append(q)

    def _finish(self, points) -> None:
        self.points = []
        if not selection_area.valid(points):
            self.session.message("a área precisa ter largura e altura", "recusa")
            return
        self.ctx.area = selection_area.Area(tuple(points), self.all_storeys)

    def set_all_storeys(self, value: bool) -> None:
        """Alcance da área (barra Opções): vale também para a área já desenhada."""
        self.all_storeys = value
        area = self.ctx.area
        if area is not None:
            self.ctx.area = selection_area.Area(area.points, value)

    def touched(self, area: selection_area.Area) -> list[str]:
        """Elementos com algum ponto dentro: do pavimento ativo ou de todos."""
        if not area.all_storeys:
            return selection_area.touched(self.ctx.plan, area)
        doc, found = self.session.doc, {}
        for storey in doc.storeys():
            found.update(dict.fromkeys(selection_area.touched(
                plan.storey_plan(doc, storey, show_below=False), area)))
        return list(found)

    def _drop(self, q: Point) -> None:
        d, self.drag = self.drag, None
        vector = (q[0] - d["base"][0], q[1] - d["base"][1])
        area = self.ctx.area
        if area is None or math.hypot(*vector) <= 1e-9:
            return
        if d["kind"] == "move":
            self.ctx.area = area.moved(vector)
            return
        doc, gids = self.session.doc, self.touched(area)
        if not gids:
            self.session.message("nada a esticar: nenhum ponto dentro da área", "recusa")
        elif self.session.run(lambda: transform.stretch_elements(doc, gids, area, vector)):
            self.ctx.area = area.moved(vector)

    def cancel(self):
        busy = bool(self.points or self.drag)
        self.points, self.drag, self.pressed = [], None, None
        self.fixed.clear()
        return busy

    def escape(self):
        """Esc: descarta o que está em andamento; senão, remove a área (§2)."""
        if self.cancel():
            return True
        if self.ctx.area is not None:
            self.ctx.area = None
            return True
        return False

    def transform_fn(self):
        d = self.drag
        if d is None or not d["active"] or self.snapped is None:
            return None
        q, base = self.snapped.point, d["base"]
        return geom2d.translation((q[0] - base[0], q[1] - base[1]))

    def preview(self):
        q = self.snapped.point if self.snapped else self.cursor
        d = self.drag
        if d is not None:
            if not d["active"] or q is None:
                return []
            vector = (q[0] - d["base"][0], q[1] - d["base"][1])
            area = self.ctx.area
            marks = [Mark((d["base"], q), False),
                     Mark(area.moved(vector).points, True, "area")]
            if d["kind"] == "stretch":
                fn = selection_area.stretch_fn(area, vector)
                marks += _shape_marks(moving_shapes(self.ctx, self.touched(area)), fn)
            return marks
        if not self.points or q is None:
            return []
        if self.shape == "rectangle":
            return [Mark(selection_area.Area.rectangle(self.points[0], q).points, True,
                         "area")]
        return [Mark((*self.points, q), len(self.points) >= 2, "area")]


class RotateViewTool(Tool):
    """Girar a vista por dois cliques (spec/ui 39 §3): a direção do primeiro ao segundo
    ponto fica na horizontal da tela. Atração e guias valem. Não muda o modelo."""

    name, label = "view_rotate", "Girar a vista"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.start: Point | None = None

    def hint(self):
        if self.start is None:
            return "Clique o primeiro ponto da direção que deve ficar na horizontal"
        return "Clique o segundo ponto (Esc cancela)"

    def cancel(self):
        self.start = None
        super().cancel()

    def move(self, p, mods):
        super().move(p, mods)
        self.snapped = self.ctx.snap(p, mods, self.start)

    def preview(self):
        if self.start is None or self.snapped is None:
            return []
        return [Mark((self.start, self.snapped.point), False)]

    def press(self, p, mods, button="left"):
        if button != "left":
            return
        q = self.ctx.snap(p, mods, self.start).point
        if self.start is None:
            self.start = q
            return
        dx, dy = q[0] - self.start[0], q[1] - self.start[1]
        if math.hypot(dx, dy) < 1e-9:
            return
        view = self.ctx.input_view
        self.start = None
        if view is not None and hasattr(view, "set_rotation"):
            view.set_rotation(math.atan2(dy, dx))
        self.finished = True


TOOLS = (SelectTool, WallTool, ArcWallTool, RectangleTool, DoorTool, WindowTool,
         WallOpeningTool, ColumnTool,
         BeamTool, SlabTool, RoofTool, SkylightTool, StairTool, RailingTool, ObjectTool,
         GridTool, TerrainTool, PickCurvesTool, CurveLevelTool, SlabOpeningTool, SpaceTool, DimensionTool, LevelTool, TextTool,
         LineTool, SplineTool, CircleTool, ArcTool, RadiusDimTool, AngleDimTool, LabelTool,
         RevisionTool, HatchTool, NorthTool, SectionTool, ElevationTool, SplitTool, MoveTool, CopyTool, RotateTool,
         MirrorTool, OffsetTool, TrimTool, FilletTool, MeasureTool, AreaTool,
         RotateViewTool)
# Ferramentas que agem sobre a seleção (mini-barra, spec/ui 03 §5): ao terminar, ou com
# Esc, a vista volta para Selecionar.
SELECTION_TOOLS = ("move", "copy", "rotate", "mirror", "split", "slab_opening",
                   "terrain_pick", "terrain_level")


# --- mini-barra da seleção (spec/ui 03 §5) -------------------------------------------------


def selection_actions(doc, gids) -> list[str]:
    """Ações da mini-barra que se aplicam à seleção, na ordem da barra."""
    elements = [doc.find(g) for g in sorted(gids)]
    elements = [e for e in elements if e is not None]
    if not elements:
        return []
    walls = [e for e in elements if e.is_a("IfcWall")]
    from brasbim.core.structure import skylights

    door_list = [e for e in elements if (e.is_a("IfcDoor") or e.is_a("IfcWindow"))
                 and not skylights.is_skylight(e)]
    structure = [e for e in elements if sc.is_structure(e) or ac.is_annotation(e)]
    found_objects = [e for e in elements if objects.is_object(e)]
    free = [e for e in found_objects if objects.read_state(doc, e)["host"] is None]
    if all(cmd.is_wall_opening(e) for e in elements):  # vão e nicho (spec/ui 20 §3)
        return ["delete"]
    out = ["move", "copy"]
    if walls or structure or free or transform._misc(doc, [e.GlobalId for e in elements]):
        out += ["rotate", "mirror"]
    if len(elements) == 1 and walls and isinstance(
            geom2d.path_from_dict(cmd.read_state(doc, walls[0])["path"]), geom2d.LinePath):
        out.append("auto_dimension")
    if (len(elements) == 1 and elements[0].is_a("IfcSlab")
            and sc.read_state(doc, elements[0])["foreign"] is None):
        out.append("slab_opening")
    if len(elements) == 1 and walls:
        out.append("split")
    if len(walls) == 2 and len(elements) == 2:
        out += _join_actions(doc, *walls)
    if door_list and len(door_list) == len(elements):
        out.append("flip_opening")
        if all(fc.hand(doc, d) for d in door_list):
            out.append("flip_hinges")
    from brasbim.core import terrain as terrain_data

    if len(elements) == 1 and terrain_data.is_terrain(elements[0]):  # escada-terreno §4.4
        out += ["pick_curves", "curve_level"]
    if found_objects and len(found_objects) == len(elements):  # objeto-parametrico §5.1
        out.append("swap_type")
        if len({objects.read_state(doc, e)["type"] for e in found_objects}) == 1:
            out.append("edit_object_type")
        if len(found_objects) == 1 and not free:
            out.append("detach")
    out += ["select_similar", "situation"]  # spec/ui 23 §7, spec/ui 31 §2
    locked = [e for e in elements if edit_state.is_locked(doc, e)]
    out.append("unlock" if len(locked) == len(elements) else "lock")  # spec/ui 39 §5
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
        shared = {}  # as formas de parede dividem as mesmas opções
        self.tools = {}
        for cls in TOOLS:
            if issubclass(cls, _WallTool):
                options = shared.setdefault(cls.options_class,
                                            cls.options_class(self.ctx.session))
                tool = cls(self.ctx, options)
            else:
                tool = cls(self.ctx)
            self.tools[cls.name] = tool
        name = self.active.name if self.active else "select"
        self.active = self.tools[name]

    def check_types(self) -> None:
        """Depois de editar os tipos: opção que aponta para tipo excluído volta ao
        primeiro da lista."""
        doc = self.ctx.session.doc
        for tool in self.tools.values():
            holder = tool.options if isinstance(tool, _WallTool) else tool
            ifc_class = getattr(holder, "type_class", "IfcDoorType")
            if ifc_class is None or not hasattr(holder, "type") or (
                    holder.type and doc.find(holder.type)):
                continue  # sem tipo do IFC (abertura, ambiente, anotações) ou tipo válido
            types = sorted(doc.ifc.by_type(ifc_class), key=lambda t: t.Name or "")
            holder.type = types[0].GlobalId if types else None

    def activate(self, name: str) -> Tool:
        if self.active is not None:
            self.active.cancel()
            prev = self.active
            if prev.name != "select" and prev.name not in SELECTION_TOOLS:
                self.ctx.last_tool = (prev.name, prev.label)
        self.active = self.tools[name]
        self.ctx.axis_lock = None
        self.ctx.references, self.ctx.tracked = [], None  # spec/ui 37 §2
        if name in ("wall", "arc", "rectangle"):
            self.wall_form = name
        return self.active
