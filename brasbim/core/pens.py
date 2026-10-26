# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tabelas de penas (spec/ui 27): cor e espessura de cada pena e a pena de cada categoria
de linha do desenho. É só representação: o modelo não muda. Sem Qt.

Operação: ``pens.edit`` (before/after: configuração inteira, ``None`` = sem configuração).

Configuração em JSON no Pset ``BrasBim_Penas`` do ``IfcProject``::

    {"current": "<id>", "tables": [{"id": "<id>", "name": "Padrão",
      "print_black": False,
      "pens": {"1": {"color": "#23272A", "weight": 0.13, "note": ""}, ...},
      "categories": {"cut": 5, "layer": 2, ...}}]}

Sem o Pset vale a tabela padrão, que reproduz o desenho de antes das penas.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from dataclasses import dataclass

import ifcopenshell.util.element

from brasbim.core import props
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register

PSET = "BrasBim_Penas"
INK, SOFT, FAINT = "#23272A", "#596064", "#BDBAB2"
# Cores "neutras" das bordas (tipos e materiais sem cor própria): seguem a pena.
NEUTRAL = {"#2B2A27", INK}
# Categoria → (rótulo, espessura de referência em mm, pena padrão). A referência é a
# espessura com que a categoria era desenhada antes das penas (spec/ui 13 §8).
CATEGORIES = {
    "cut": ("Elementos cortados (contorno)", 0.5, 5),
    "layer": ("Divisa entre camadas", 0.18, 2),
    "view": ("Elementos em vista", 0.25, 3),
    "above": ("Acima do plano de corte", 0.18, 2),
    "below": ("Pavimento de baixo", 0.13, 8),
    "opening": ("Portas e janelas", 0.25, 3),
    "swing": ("Giro de portas e folhas", 0.13, 7),
    "object": ("Mobiliário e objetos", 0.13, 7),
    "dimension": ("Cotas", 0.13, 1),
    "text": ("Textos e etiquetas", 0.25, 3),
    "drawing": ("Linhas e desenho 2D", 0.18, 2),
    "grid": ("Eixos de projeto", 0.13, 1),
    "symbol": ("Símbolos (norte, nível, corte e fachada)", 0.35, 4),
    "roof": ("Projeção da cobertura", 0.18, 2),
    "terrain": ("Terreno", 0.13, 1),
    "imported": ("Desenho importado", 0.13, 8),
}
DEFAULT_PENS = {
    1: (INK, 0.13, "fina"), 2: (INK, 0.18, ""), 3: (INK, 0.25, "média"),
    4: (INK, 0.35, ""), 5: (INK, 0.5, "grossa (corte)"), 6: (INK, 0.7, "muito grossa"),
    7: (SOFT, 0.13, "cinza escuro"), 8: (FAINT, 0.13, "cinza claro"),
    9: ("#C0392B", 0.25, "vermelho (a demolir)"), 10: ("#D68910", 0.25, "laranja"),
    11: ("#1F5FC4", 0.25, "azul"), 12: ("#1E8449", 0.25, "verde"),
}
MAX_PENS = 64
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Tipos de anotação (prefixo do ``base.Kind``) → categoria.
ANNOTATION_KINDS = {"dimension": "dimension", "radius_dim": "dimension",
                    "angle_dim": "dimension", "text": "text", "label": "text",
                    "line2d": "drawing", "circle2d": "drawing", "arc2d": "drawing",
                    "spline2d": "drawing", "hatch": "drawing", "revision": "symbol",
                    "north": "symbol", "level_mark": "symbol", "reference2d": "imported"}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def default_table(name: str = "Padrão", table_id: str = "padrao") -> dict:
    return {"id": table_id, "name": name, "print_black": False,
            "pens": {str(n): {"color": c, "weight": w, "note": note}
                     for n, (c, w, note) in DEFAULT_PENS.items()},
            "categories": {key: pen for key, (_, _, pen) in CATEGORIES.items()}}


def default_config() -> dict:
    return {"current": "padrao", "tables": [default_table()]}


def read_config(doc: Document) -> dict | None:
    values = ifcopenshell.util.element.get_pset(doc.project, PSET, should_inherit=False) or {}
    return json.loads(values["Parametros"]) if "Parametros" in values else None


def config(doc: Document) -> dict:
    """Configuração do arquivo ou a padrão (sem gravar)."""
    return read_config(doc) or default_config()


def table(cfg: dict, table_id: str | None) -> dict:
    """Tabela pelo código; sem ele (ou se não existe mais), a da janela."""
    by_id = {t["id"]: t for t in cfg["tables"]}
    return by_id.get(table_id) or by_id.get(cfg["current"]) or cfg["tables"][0]


@dataclass(frozen=True)
class Pen:
    color: str
    weight: float  # mm


class Resolved:
    """Penas de uma tabela prontas para desenhar: ``pen(categoria)`` e ``scale``."""

    def __init__(self, tbl: dict, black: bool = False):
        self.table = tbl
        self.black = black
        self._pens = {}
        for key, (_, ref, default) in CATEGORIES.items():
            number = str(tbl["categories"].get(key, default))
            data = tbl["pens"].get(number) or {"color": INK, "weight": ref}
            self._pens[key] = Pen(INK if black else data["color"], float(data["weight"]))

    def pen(self, category: str) -> Pen:
        return self._pens.get(category) or Pen(INK, CATEGORIES.get(category, ("", 0.25))[1])

    def number(self, n: int) -> Pen:
        """A pena de número ``n`` (moldura dos desenhos na prancha, spec/ui 29 §4)."""
        data = self.table["pens"].get(str(n)) or {"color": INK, "weight": 0.25}
        return Pen(INK if self.black else data["color"], float(data["weight"]))

    def color(self, category: str) -> str:
        return self.pen(category).color

    def scale(self, category: str) -> float:
        """Quanto a espessura da categoria muda em relação à de referência (§3)."""
        ref = CATEGORIES.get(category, ("", 0.0))[1]
        return self.pen(category).weight / ref if ref else 1.0

    def weight(self, category: str, weight: float) -> float:
        """Espessura de uma linha da categoria que seria ``weight`` na tabela padrão."""
        return weight * self.scale(category)


def resolve(doc: Document, table_id: str | None = None, paper: bool = False) -> Resolved:
    """Penas da tabela ``table_id`` (ou da janela); ``paper``: prancha/PDF, onde "Imprimir
    em preto" vale (§3)."""
    tbl = table(config(doc), table_id)
    return Resolved(tbl, black=paper and bool(tbl.get("print_black")))


DEFAULT = Resolved(default_table())


def annotation_category(doc: Document, element) -> str:
    """Categoria das linhas de uma anotação da planta pelo dono (§2)."""
    if element is None:
        return "drawing"
    if element.is_a("IfcAnnotation"):
        from brasbim.core.annotations import base
        from brasbim.core.drawings import views

        if views.is_view(element):
            return "symbol"
        kind = base.kind_of(element)
        return ANNOTATION_KINDS.get(kind.prefix, "drawing") if kind is not None else "drawing"
    if element.is_a("IfcGrid"):
        return "grid"
    if element.is_a("IfcRoof"):
        return "roof"
    if element.is_a("IfcGeographicElement"):
        return "terrain"
    return "view"  # escada, guarda-corpo


# --- operação ---------------------------------------------------------------------------


def validate(cfg: dict) -> None:
    tables = cfg.get("tables") or []
    if not tables:
        raise OpError("é preciso ao menos uma tabela de penas")
    ids = [t.get("id") for t in tables]
    if len(set(ids)) != len(ids) or not all(ids):
        raise OpError("códigos de tabela de penas repetidos")
    if cfg.get("current") not in ids:
        raise OpError("a tabela da janela não existe")
    names = [(t.get("name") or "").strip() for t in tables]
    if not all(names) or len({n.lower() for n in names}) != len(names):
        raise OpError("cada tabela de penas precisa de um nome próprio")
    for t in tables:
        pens = t.get("pens") or {}
        if not pens or len(pens) > MAX_PENS:
            raise OpError(f"a tabela precisa de 1 a {MAX_PENS} penas")
        for number, pen in pens.items():
            if not number.isdigit() or int(number) < 1:
                raise OpError(f"número de pena inválido: {number!r}")
            if not _COLOR.match(pen.get("color") or ""):
                raise OpError(f"cor inválida na pena {number}")
            if not 0 < float(pen.get("weight") or 0) <= 5:
                raise OpError(f"espessura inválida na pena {number}")
        unknown = set(t.get("categories") or {}) - set(CATEGORIES)
        if unknown:
            raise OpError(f"categorias desconhecidas: {sorted(unknown)}")
        for key, number in (t.get("categories") or {}).items():
            if str(number) not in pens:
                raise OpError(f"a categoria {CATEGORIES[key][0]} usa a pena {number}, "
                              "que não existe")


def _edit(doc: Document, op: Op) -> set[str]:
    current = read_config(doc)
    check_before(op, {"config": current})
    after = (op.after or {}).get("config")
    if after is None:
        props.remove_pset(doc, doc.project, PSET)
    else:
        validate(after)
        props.write_pset(doc, doc.project, PSET, {"Parametros": doc.ifc.createIfcText(
            json.dumps(after, ensure_ascii=False, sort_keys=True))})
    return {doc.project.GlobalId}


register("pens.edit", _edit, invert_swap)


def edit_config(doc: Document, new: dict, label: str = "Editar tabelas de penas"
                ) -> Transaction:
    validate(new)
    current = read_config(doc)
    if new == (current or default_config()):
        return Transaction(label, [])
    return Transaction(label, [Op("pens.edit", doc.project.GlobalId,
                                  before={"config": copy.deepcopy(current)},
                                  after={"config": copy.deepcopy(new)})])


def use_table(doc: Document, table_id: str) -> Transaction:
    """Tabela da janela (Exibir > Tabela de penas, §4)."""
    cfg = copy.deepcopy(config(doc))
    cfg["current"] = table_id
    return edit_config(doc, cfg, "Usar tabela de penas")
