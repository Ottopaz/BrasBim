# SPDX-License-Identifier: LGPL-3.0-or-later
"""Biblioteca de objetos em arquivos IFC (``spec/elementos/objeto-parametrico.md`` §4.1 a
§4.3), sem Qt.

Um arquivo de biblioteca é um IFC 4.3 com uma ``IfcProjectLibrary`` declarada no projeto
(``IfcRelDeclares``) e os tipos declarados nela, mais uma ocorrência de amostra de cada
tipo num pavimento "Amostras" (para outros programas mostrarem o objeto). Os tipos
aninhados vão no mesmo arquivo.

``Entry`` é um tipo lido de um arquivo; ``Index`` lê as pastas e guarda o que leu pela
data do arquivo; ``load`` monta a transação que traz tipos para o projeto; ``save`` grava
uma definição (e os tipos dela) num arquivo, substituindo a versão anterior.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell
import ifcopenshell.api.root

from brasbim.core import guid
from brasbim.core.document import Document, OpError
from brasbim.core.objects import commands as oc
from brasbim.core.objects import definition as od
from brasbim.core.objects import types as ot
from brasbim.core.ops import Op, Transaction

LIBRARY_NAME = "Biblioteca de objetos do BrasBim"
SAMPLE_STOREY = "Amostras"
SAMPLE_GAP = 0.5  # m entre as amostras


@dataclass
class Entry:
    """Um tipo de uma biblioteca."""
    file: str
    name: str
    definition: dict
    values: dict
    defaults: dict
    global_id: str = ""

    @property
    def object_id(self) -> str:
        return self.definition["object_id"]

    @property
    def version(self) -> int:
        return int(self.definition.get("version") or 1)

    @property
    def category(self) -> str:
        return self.definition["category"]

    def state(self) -> dict:
        return {"name": self.name, "definition": copy.deepcopy(self.definition),
                "values": copy.deepcopy(self.values), "defaults": copy.deepcopy(self.defaults),
                "library": {"file": self.file, "object_id": self.object_id,
                            "version": self.version}}


def builtin_folder() -> Path:
    """Biblioteca que vem com o BrasBim (só leitura, §4.1)."""
    return Path(__file__).resolve().parents[2] / "library" / "objetos"


def read_file(path) -> list[Entry]:
    """Tipos de objeto do BrasBim num arquivo IFC (os que têm a definição, §4.3)."""
    ifc = ifcopenshell.open(str(path))
    doc = Document(ifc)
    out = []
    for t in ot.all_types(doc):
        state = ot.read(t)
        out.append(Entry(str(path), state["name"], state["definition"], state["values"],
                         state["defaults"], t.GlobalId))
    return out


# --- índice -------------------------------------------------------------------------------


@dataclass
class Index:
    """Tipos das pastas da biblioteca, relidos só quando o arquivo muda (§4.1)."""
    folders: list = field(default_factory=list)
    _cache: dict = field(default_factory=dict)  # caminho → (data, [Entry])
    errors: dict = field(default_factory=dict)  # caminho → mensagem

    def files(self) -> list[Path]:
        out = []
        for folder in self.folders:
            folder = Path(folder)
            if folder.is_dir():
                out += sorted(folder.rglob("*.ifc"))
        return out

    def entries(self) -> list[Entry]:
        out = []
        seen = set()
        for path in self.files():
            key = str(path)
            seen.add(key)
            try:
                stamp = os.path.getmtime(path)
            except OSError:
                continue
            cached = self._cache.get(key)
            if cached is None or cached[0] != stamp:
                try:
                    self._cache[key] = (stamp, read_file(path))
                    self.errors.pop(key, None)
                except Exception as e:  # noqa: BLE001 - arquivo ruim não derruba o índice
                    self._cache[key] = (stamp, [])
                    self.errors[key] = str(e)
            out += self._cache[key][1]
        for key in [k for k in self._cache if k not in seen]:
            del self._cache[key]
        return out

    def find(self, object_id: str) -> list[Entry]:
        return [e for e in self.entries() if e.object_id == object_id]


def updates(doc: Document, index: Index) -> dict[str, Entry]:
    """Definições do projeto com versão mais nova na biblioteca: ``object_id`` → entrada."""
    out = {}
    newest: dict[str, Entry] = {}
    for e in index.entries():
        if e.object_id not in newest or e.version > newest[e.object_id].version:
            newest[e.object_id] = e
    for t in ot.all_types(doc):
        state = ot.read(t)
        lib = state["library"]
        if not lib:
            continue
        found = newest.get(lib.get("object_id"))
        if found is not None and found.version > int(lib.get("version") or 1):
            out[found.object_id] = found
    return out


# --- carregar no projeto ----------------------------------------------------------------------


def _closure(entries: list[Entry], wanted: list[Entry]) -> list[Entry]:
    """Os tipos pedidos e os aninhados que eles usam (procurados nas entradas dadas)."""
    by_name = {e.name: e for e in entries}
    out, stack = [], list(wanted)
    while stack:
        e = stack.pop(0)
        if any(x.name == e.name and x.object_id == e.object_id for x in out):
            continue
        out.append(e)
        for name in sorted(od.nested_refs(e.definition)):
            found = by_name.get(name)
            if found is not None:
                stack.append(found)
        for p in e.definition["params"]:
            if p["kind"] == "object_type":
                for name in sorted({p.get("value") or "", *(p.get("options") or [])}):
                    if name in by_name:
                        stack.append(by_name[name])
    # aninhados primeiro: o objeto de fora precisa deles já no projeto
    return out[::-1]


def load(doc: Document, entries: list[Entry], wanted: list[Entry],
         conflict: str = "keep") -> Transaction:
    """Transação que traz ``wanted`` (e os aninhados) para o projeto (§4.3).

    ``conflict`` para o tipo que já está no projeto (mesmo nome e mesma definição):
    ``keep`` (fica o do projeto), ``replace`` (valores e definição da biblioteca) ou
    ``new`` (carregado como novo tipo, nome com " (2)")."""
    if conflict not in ("keep", "replace", "new"):
        raise OpError(f"opção inválida: {conflict}")
    ops: list[Op] = []
    names: list[str] = []
    categories = []
    for e in _closure(entries, wanted):
        _, type_class = od.classes(e.definition)
        existing = next((t for t in doc.ifc.by_type(type_class) if t.Name == e.name), None)
        same = existing is not None and ot.is_object_type(existing) and \
            ot.definition_of(existing)["object_id"] == e.object_id
        state = e.state()
        if same and conflict == "keep":
            continue
        if same and conflict == "replace":
            current = ot.read(existing)
            after = {k: state[k] for k in ("definition", "values", "defaults", "library")
                     if current[k] != state[k]}
            if after:
                ops.append(Op("object_type.edit", existing.GlobalId,
                              before={k: copy.deepcopy(current[k]) for k in after},
                              after=after))
            continue
        state["name"] = oc.free_name(doc, e.name, type_class, names)
        names.append(state["name"])
        categories.append(e.category)
        ops.append(Op("object_type.create", guid.new(), data=state))
    layer_ops = []
    for category in dict.fromkeys(categories):
        for op in oc.layer_ops(doc, category):
            if (op.op, op.id) not in {(o.op, o.id) for o in layer_ops} and \
                    not any(o.op == "layer.defaults" and set(o.after) & set(op.after)
                            for o in layer_ops):
                layer_ops.append(op)
    label = f"Carregar {wanted[0].name}" if len(wanted) == 1 else "Carregar objetos"
    return Transaction(label, layer_ops + ops)


def update_from(doc: Document, entry: Entry) -> Transaction:
    """Atualizar da biblioteca (§4.3): a definição nova em todos os tipos dela, mantendo
    os valores que continuam valendo."""
    tx = oc.edit_definition(doc, entry.object_id, entry.definition, keep_version=True,
                            library={"file": entry.file, "object_id": entry.object_id,
                                     "version": entry.version})
    return Transaction(f"Atualizar {entry.definition['name']} da biblioteca", tx.ops)


# --- gravar ------------------------------------------------------------------------------------


def _declare(doc: Document, types: list) -> None:
    ifc = doc.ifc
    library = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcProjectLibrary",
                                                  name=LIBRARY_NAME)
    guid.stamp(library, doc.project.GlobalId, "library")
    library.UnitsInContext = doc.project.UnitsInContext
    ifc.create_entity("IfcRelDeclares", GlobalId=guid.derived(doc.project.GlobalId,
                                                              "declares/library"),
                      RelatingContext=doc.project, RelatedDefinitions=[library])
    if types:
        ifc.create_entity("IfcRelDeclares", GlobalId=guid.derived(library.GlobalId,
                                                                  "declares/types"),
                          RelatingContext=library, RelatedDefinitions=list(types))


def write_file(path, states: list[dict], samples: bool = True) -> None:
    """Grava os tipos (estados de ``types.read``) num arquivo de biblioteca novo."""
    from brasbim.core.ops.history import History
    from brasbim.core.walls import commands as wc

    doc = Document.new(name=LIBRARY_NAME)
    history = History(doc)
    gids = []
    # aninhados primeiro (o objeto de fora precisa deles)
    ordered = _order_states(states)
    for state in ordered:
        gid = guid.derived(state["definition"]["object_id"], f"type/{state['name']}")
        data = {**copy.deepcopy(state), "library": None}
        history.commit(Transaction("tipo", [Op("object_type.create", gid, data=data)]))
        gids.append(gid)
    if samples and gids:
        history.commit(wc.create_storey(doc, SAMPLE_STOREY, 0.0))
        storey = doc.storeys()[0]
        x = 0.0
        for gid in gids:
            t = doc.get(gid)
            if od.normalized(ot.read(t)["definition"])["hosting"] == "wall":
                continue  # sem parede, a amostra do objeto preso fica de fora
            state = ot.read(t)
            values = ot.evaluate(state)
            box = od.bounds(od.solids(state["definition"], values)) or (0, 0.5, 0, 0, 0, 0)
            point = (x - box[0], 0.0)
            try:
                history.commit(oc.create_object(doc, t, storey, point,
                                                gid=guid.derived(gid, "sample")))
            except OpError:
                continue
            x += (box[1] - box[0]) + SAMPLE_GAP
    _declare(doc, [doc.get(g) for g in gids])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def _order_states(states: list[dict]) -> list[dict]:
    names = {s["name"] for s in states}
    done, out = set(), []

    def visit(s, depth=0):
        if s["name"] in done or depth > od.MAX_NESTING + 1:
            return
        for ref in sorted(od.nested_refs(s["definition"]) & names):
            visit(next(x for x in states if x["name"] == ref), depth + 1)
        done.add(s["name"])
        out.append(s)

    for s in states:
        visit(s)
    return out


def save(doc: Document, path, object_id: str, type_gids=None) -> list[str]:
    """Gravar na biblioteca (§4.3): a definição e os tipos escolhidos (todos, sem
    ``type_gids``) no arquivo, novo ou existente; na mesma definição, substitui a versão
    anterior. Os aninhados vão junto. Devolve os nomes gravados."""
    path = Path(path)
    if path.resolve().is_relative_to(builtin_folder().resolve()):
        raise OpError("a biblioteca do BrasBim não pode ser gravada: grave uma cópia na "
                      "sua pasta")
    types = ot.types_of_definition(doc, object_id)
    if type_gids is not None:
        types = [t for t in types if t.GlobalId in set(type_gids)]
    if not types:
        raise OpError("nenhum tipo para gravar")
    states = [{**ot.read(t), "library": None} for t in types]
    names = {s["name"] for s in states}
    for s in list(states):  # aninhados que estão no projeto
        for ref in od.nested_refs(s["definition"]):
            found = ot.by_name(doc, ref)
            if found is not None and ref not in names:
                states.append({**ot.read(found), "library": None})
                names.add(ref)
    if path.exists():
        kept = [e.state() for e in read_file(path)
                if e.object_id != object_id and e.name not in names]
        states = [{**s, "library": None} for s in kept] + states
    write_file(path, states)
    return sorted(names)
