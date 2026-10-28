# SPDX-License-Identifier: LGPL-3.0-or-later
"""Perfil municipal do projeto legal (``spec/ui/31-projeto-legal.md`` §4 e §13), sem Qt.

- Perfis prontos em ``brasbim/perfis/*.json`` (abertos e versionados, cada um com a
  ``fonte``). Só o Genérico é completo; os das cidades trazem só o que tem fonte e o
  resto vem do Genérico (``resolve``).
- O projeto guarda o perfil escolhido **inteiro** (já resolvido) no Pset
  ``BrasBim_PerfilMunicipal`` do ``IfcProject`` (``Parametros``, JSON): abre igual em
  outra máquina, mesmo sem o arquivo do perfil. Sem o Pset vale o Genérico.
- Operação ``municipal.set`` (before/after ``{"profile": perfil | None}``).
- Aplicado nesta etapa: cores e hachuras de cada situação (``mark``), escala de cortes e
  fachadas novos (``view_scale``) e "Aplicar escalas" às plantas, cortes e fachadas
  (``apply_scales``). Quadro de áreas, selo, notas e PDF ficam guardados para as etapas
  3 e 4.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import ifcopenshell.util.element

from brasbim.core import intervention, props, storeys
from brasbim.core.document import Document, OpError
from brasbim.core.ops import Transaction
from brasbim.core.ops.base import Op, check_before, invert_swap, register

PSET = "BrasBim_PerfilMunicipal"
FOLDER = Path(__file__).resolve().parent.parent / "perfis"
GENERIC = "generico"
HATCHES = ("none", "solid", "lines", "cross")
SCALE_KEYS = (("implantacao", "Implantação"), ("plantas", "Plantas"),
              ("cortes", "Cortes"), ("fachadas", "Fachadas"))
PLANS = (("completa", "Completa"), ("simplificada", "Simplificada (sem compartimentação)"))
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def generic() -> dict:
    return _load(FOLDER / f"{GENERIC}.json")


def resolve(partial: dict) -> dict:
    """Perfil completo: o que falta em ``partial`` vem do Genérico (cores por situação,
    escalas e PDF campo a campo; o resto inteiro). ``herdado`` lista as situações cuja cor
    não veio do próprio perfil, para o diálogo mostrar (§13)."""
    base = generic()
    out = {**copy.deepcopy(base), **copy.deepcopy(partial)}
    own = partial.get("cores") or {}
    out["cores"] = {code: {**base["cores"][code], **own.get(code, {})}
                    for code in intervention.CODES}
    for key in ("escalas", "pdf", "quadro_de_areas"):
        out[key] = {**base[key], **(partial.get(key) or {})}
    out["herdado"] = [] if partial.get("id") == GENERIC else \
        [code for code in intervention.CODES if code not in own]
    return out


def builtin() -> list[dict]:
    """Perfis que vêm junto, resolvidos; o Genérico primeiro, os outros pelo nome."""
    found = [resolve(_load(p)) for p in sorted(FOLDER.glob("*.json"))]
    return sorted(found, key=lambda p: (p["id"] != GENERIC, p["nome"]))


def read(doc: Document) -> dict | None:
    values = ifcopenshell.util.element.get_pset(doc.project, PSET, should_inherit=False) or {}
    return json.loads(values["Parametros"]) if "Parametros" in values else None


def current(doc: Document) -> dict:
    """Perfil do projeto (a cópia gravada) ou o Genérico."""
    return read(doc) or resolve(generic())


# --- uso ---------------------------------------------------------------------------------


def mark(profile: dict, code: str) -> tuple[str | None, dict]:
    """Cor e hachura (``{"pattern", "angle"}``) de uma situação no perfil."""
    data = profile["cores"].get(code) or {}
    return data.get("cor"), {"pattern": data.get("hachura") or "none",
                             "angle": float(data.get("angulo", 45.0))}


def view_scale(doc: Document, kind: str) -> int:
    """Escala de um corte (``section``) ou fachada (``elevation``) novo."""
    key = "cortes" if kind == "section" else "fachadas"
    return int(current(doc)["escalas"].get(key) or storeys.DEFAULT_SCALE)


# --- operação ----------------------------------------------------------------------------


def validate(profile: dict) -> None:
    if not (profile.get("nome") or "").strip():
        raise OpError("o perfil municipal precisa de um nome")
    cores = profile.get("cores") or {}
    unknown = set(cores) - set(intervention.CODES)
    if unknown:
        raise OpError(f"situações desconhecidas no perfil: {sorted(unknown)}")
    for code, data in cores.items():
        color = data.get("cor")
        if color is not None and not _COLOR.match(color):
            raise OpError(f"cor inválida para {intervention.LABEL[code]}")
        if data.get("hachura", "none") not in HATCHES:
            raise OpError(f"hachura inválida para {intervention.LABEL[code]}")
    for key, label in SCALE_KEYS:
        value = (profile.get("escalas") or {}).get(key)
        if value is not None and not (isinstance(value, int) and 1 <= value <= 10000):
            raise OpError(f"escala inválida em {label}")
    if profile.get("planta", "completa") not in dict(PLANS):
        raise OpError("planta deve ser completa ou simplificada")
    size = (profile.get("pdf") or {}).get("max_mb")
    if size is not None and not 0 < float(size) <= 1000:
        raise OpError("tamanho máximo do PDF inválido")


def _set(doc: Document, op: Op) -> set[str]:
    check_before(op, {"profile": read(doc)})
    after = (op.after or {}).get("profile")
    if after is None:
        props.remove_pset(doc, doc.project, PSET)
    else:
        validate(after)
        props.write_pset(doc, doc.project, PSET, {"Parametros": doc.ifc.createIfcText(
            json.dumps(after, ensure_ascii=False, sort_keys=True))})
    return {doc.project.GlobalId}


register("municipal.set", _set, invert_swap)


def set_profile(doc: Document, profile: dict | None, label: str = "Perfil municipal"
                ) -> Transaction:
    """Grava a cópia do perfil no projeto (``None`` volta ao Genérico sem cópia)."""
    if profile is not None:
        validate(profile)
    current_ = read(doc)
    if profile == current_:
        return Transaction(label, [])
    return Transaction(label, [Op("municipal.set", doc.project.GlobalId,
                                  before={"profile": copy.deepcopy(current_)},
                                  after={"profile": copy.deepcopy(profile)})])


def apply_scales(doc: Document, profile: dict) -> Transaction:
    """Escala de plantas em todos os pavimentos e de cortes e fachadas em todas as vistas
    (§13). O que já está na escala fica como está."""
    from brasbim.core.drawings import views
    from brasbim.core.walls import commands

    scales = profile["escalas"]
    ops: list[Op] = []
    plans = scales.get("plantas")
    if plans:
        for storey in doc.ifc.by_type("IfcBuildingStorey"):
            if storeys.stored_scale(storey) != plans:
                ops += commands.edit_storey(doc, storey, scale=plans).ops
    for view in views.all_views(doc):
        state = views.read_state(view)
        value = scales.get("cortes" if state["kind"] == "section" else "fachadas")
        if value and state["scale"] != value:
            ops.append(Op("view.edit", view.GlobalId, before={"scale": state["scale"]},
                          after={"scale": value}))
    return Transaction("Aplicar escalas do perfil", ops)


def choose(doc: Document, profile: dict, scales: bool = False) -> Transaction:
    """Escolhe o perfil (cópia no IFC) e, se ``scales``, aplica as escalas dele, numa
    transação só."""
    from brasbim.core.ops.history import combine

    builders = [lambda: set_profile(doc, profile)]
    if scales:
        builders.append(lambda: apply_scales(doc, profile))
    return combine(doc, "Perfil municipal", builders)
