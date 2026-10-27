# SPDX-License-Identifier: GPL-3.0-or-later
"""Sessão de trabalho do aplicativo (``spec/ui/01-janela-e-ferramentas.md`` §2, §8, §9.2).

Guarda documento, histórico, arquivo, pavimento ativo, seleção e mensagens. É o único
ponto da interface que aplica transações. Não depende de Qt: a janela se inscreve em
``listeners`` e é avisada com o nome do evento (``document``, ``model``, ``selection``,
``storey``, ``messages``, ``backup``).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from brasbim.core import display_layers
from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd
from brasbim.ui import recovery

MAX_MESSAGES = 200

# Biblioteca mínima do projeto novo (spec/ui §2.2; valores de parede §3.4 e porta §3.5;
# representação na planta, spec/ui 03 §6.4; estrutura, spec/ui 10 §5).
_WALL_STYLES = {
    "Alvenaria 14": {"fill": "solid", "fill_color": "#9C9A93", "hatch_angle": 45.0,
                     "hatch_spacing": 0.10, "line_weight": 0.0005, "line_color": "#2B2A27"},
    "Drywall 9,5": {"fill": "hatch", "fill_color": "#B9B6AE", "hatch_angle": 45.0,
                    "hatch_spacing": 0.05, "line_weight": 0.00035, "line_color": "#2B2A27"},
}
_WALL_TYPES = [
    ("Alvenaria 14", "SOLIDWALL", [
        {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
        {"material": "Bloco cerâmico", "thickness": 0.09, "category": "LoadBearing",
         "priority": 80},
        {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
    ]),
    ("Drywall 9,5", "PARTITIONING", [
        {"material": "Gesso acartonado", "thickness": 0.0125, "category": "Finish"},
        {"material": "Montante de aço", "thickness": 0.07},
        {"material": "Gesso acartonado", "thickness": 0.0125, "category": "Finish"},
    ]),
]
_DOOR_TYPES = [
    ("P1 – giro 80", "SINGLE_SWING_LEFT", 0.86),
    ("P2 – giro 70", "SINGLE_SWING_LEFT", 0.76),
    ("P3 – correr 2 folhas", "DOUBLE_DOOR_SLIDING", 1.66),
]
# Biblioteca de janelas (spec/ui 09 §5.2): nome, código, divisão, operações, padrões.
_SLIDE, _SIDE_L, _SIDE_R = "SLIDINGHORIZONTAL", "SIDEHUNGLEFTHAND", "SIDEHUNGRIGHTHAND"
_WINDOW_TYPES = [
    ("J1 – correr 2 folhas 120", "J1", "DOUBLE_PANEL_VERTICAL", [_SLIDE, _SLIDE],
     (1.20, 1.00, 1.10)),
    ("J2 – correr 2 folhas 150", "J2", "DOUBLE_PANEL_VERTICAL", [_SLIDE, _SLIDE],
     (1.50, 1.20, 1.10)),
    ("J3 – maxim-ar 60", "J3", "SINGLE_PANEL", ["TOPHUNG"], (0.60, 0.60, 1.50)),
    ("J4 – basculante 60", "J4", "SINGLE_PANEL", ["PIVOTHORIZONTAL"], (0.60, 0.40, 1.70)),
    ("J5 – de abrir 2 folhas", "J5", "DOUBLE_PANEL_VERTICAL", [_SIDE_L, _SIDE_R],
     (1.00, 1.20, 1.10)),
    ("J6 – fixa", "J6", "SINGLE_PANEL", ["FIXEDCASEMENT"], (1.00, 1.00, 1.10)),
]

# Estrutura (laje.md, pilar.md e viga.md §3.4): seções em metros, de concreto.
_COLUMN_TYPES = [(0.14, 0.30), (0.20, 0.20), (0.20, 0.40), (0.25, 0.50)]
_COLUMN_ROUND = [0.30]
_BEAM_TYPES = [(0.12, 0.30), (0.14, 0.40), (0.15, 0.40), (0.20, 0.50)]
_SLAB_TYPES = [
    ("Laje maciça 10 cm", "FLOOR", [("Concreto", 0.10)]),
    ("Laje 12 cm com contrapiso", "FLOOR",
     [("Contrapiso", 0.03), ("Concreto", 0.10), ("Reboco", 0.015)]),
    ("Laje pré-moldada 12 cm", "FLOOR", [("Laje pré-moldada", 0.12)]),
    ("Radier 15 cm", "BASESLAB", [("Concreto", 0.15)]),
    # Cobertura (cobertura.md §3.2): a espessura representa o telhado no desenho.
    ("Telha cerâmica", "ROOF", [("Telha cerâmica", 0.05)]),
    ("Telha de fibrocimento", "ROOF", [("Telha de fibrocimento", 0.03)]),
    ("Telha metálica sanduíche", "ROOF", [("Telha metálica", 0.05)]),
    ("Laje impermeabilizada 12 cm", "ROOF",
     [("Impermeabilização", 0.02), ("Concreto", 0.10)]),
]


def _cm(value: float) -> str:
    return f"{round(value * 100)}"


def feedback_dir() -> Path:
    """``feedback/`` do repositório, se o BrasBim roda de dentro dele; senão, na pasta do
    usuário."""
    repo = Path(__file__).resolve().parents[2]
    if (repo / "pyproject.toml").exists():
        return repo / "feedback"
    return Path.home() / "BrasBim" / "feedback"


class _MessageHandler(logging.Handler):
    def __init__(self, session: Session):
        super().__init__(logging.WARNING)
        self.session = session

    def emit(self, record: logging.LogRecord) -> None:
        self.session.message(record.getMessage(), "aviso")


class Session:
    def __init__(self, journal_dir: Path | None = None, recovery_dir: Path | None = None):
        self.listeners: list[Callable[[str], None]] = []
        self.messages: list[dict] = []
        self.journal_dir = journal_dir
        self.recovery_dir = recovery_dir  # cópias de segurança (spec/ui 21)
        self.recovery_path: Path | None = None
        self._handler = _MessageHandler(self)
        logging.getLogger("brasbim").addHandler(self._handler)
        self.new()

    def close(self) -> None:
        """Fechamento normal: a cópia de segurança não é mais necessária (spec/ui 21 §3)."""
        self.discard_backup()
        logging.getLogger("brasbim").removeHandler(self._handler)

    # --- avisos ----------------------------------------------------------------------

    def _emit(self, event: str) -> None:
        for listener in list(self.listeners):
            listener(event)

    def message(self, text: str, level: str = "info") -> None:
        self.messages.append({"time": datetime.now().strftime("%H:%M:%S"), "level": level,
                              "text": text})
        del self.messages[:-MAX_MESSAGES]
        self._emit("messages")

    # --- documento ---------------------------------------------------------------------

    def _attach(self, doc: Document, path: str | None, modified: bool = False) -> None:
        self.discard_backup()  # o projeto anterior foi salvo ou descartado (spec/ui 21 §3)
        self.doc = doc
        self.history = History(doc)
        self.history.listeners.append(self._on_history)
        self.path = path
        self.modified = modified
        self._changes = self._backed_up = 0  # mudanças feitas / já na cópia de segurança
        self._journal_cache: dict = {}  # transação → texto do diário
        self.selection: set[str] = set()
        self.last_changed: set[str] = set()
        self.last_tx = None  # última transação feita, desfeita ou refeita
        storeys = doc.storeys()
        ground = [s for s in storeys if (s.Elevation or 0.0) >= -1e-6]
        self.storey_id = (ground or storeys or [None])[0]
        self.storey_id = self.storey_id.GlobalId if self.storey_id is not None else None
        self.started = datetime.now()
        if self.recovery_dir is not None:
            self.recovery_path = self.recovery_dir / (
                f"{self.started:%Y-%m-%d_%H-%M-%S}_{os.getpid()}_{uuid.uuid4().hex[:8]}.ifc")
        self._emit("document")

    def new(self) -> None:
        """Projeto com Térreo, Superior e a biblioteca mínima, fora da pilha de desfazer."""
        doc = Document.new("Projeto")
        history = History(doc)
        history.commit(cmd.create_storey(doc, "Térreo", 0.0))
        history.commit(cmd.create_storey(doc, "Superior", 2.8))
        for name, predefined, layers in _WALL_TYPES:
            history.commit(cmd.create_wall_type(doc, name, layers, predefined_type=predefined,
                                                plan_style=_WALL_STYLES[name]))
        for name, operation, width in _DOOR_TYPES:
            history.commit(fc.create_door_type(doc, name, operation, code=name.split(" ")[0],
                                               defaults={"width": width}))
        for name, code, partitioning, operations, (w, h, base) in _WINDOW_TYPES:
            history.commit(fc.create_window_type(
                doc, name, partitioning, operations, code=code,
                defaults={"width": w, "height": h, "base": base}))
        for b, h in _COLUMN_TYPES:
            history.commit(sc.create_column_type(doc, f"Pilar {_cm(b)}×{_cm(h)}",
                                                 {"shape": "rect", "b": b, "h": h}))
        for d in _COLUMN_ROUND:
            history.commit(sc.create_column_type(doc, f"Pilar Ø{_cm(d)}",
                                                 {"shape": "circle", "d": d}))
        for b, h in _BEAM_TYPES:
            history.commit(sc.create_beam_type(doc, f"Viga {_cm(b)}×{_cm(h)}", b, h))
        for name, predefined, layers in _SLAB_TYPES:
            history.commit(sc.create_slab_type(
                doc, name, [{"material": m, "thickness": t} for m, t in layers], predefined))
        self._attach(doc, None)
        # O diário começa com o conteúdo inicial, para que reaplicá-lo reproduza a sessão.
        self.history.journal = list(history.journal)
        self._write_journal()

    def open(self, path: str) -> None:
        doc = Document.open(path)
        doc.display = display_layers.read_display(doc)  # spec/ui 18 §5.1
        self._attach(doc, path)
        self.message(f"Aberto: {path}")
        organize = display_layers.organize(doc)  # arquivo sem camadas (§3.1, CM12)
        if organize is not None:
            self.history.commit(organize)
            self.message("Projeto organizado em camadas (pode ser desfeito)")

    def save(self, path: str | None = None) -> None:
        path = path or self.path
        if not path:
            raise OpError("escolha onde salvar")
        display_layers.write_display(self.doc, self.doc.display)  # §5.1: só ao salvar
        self.doc.save(path)
        self.path = path
        self.modified = False
        self.discard_backup()  # spec/ui 21 §3
        self._backed_up = self._changes
        self.message(f"Salvo: {path}")
        self._emit("document")

    # --- cópia de segurança (spec/ui 21) -------------------------------------------------

    @property
    def backup_due(self) -> bool:
        return self.recovery_path is not None and self._changes != self._backed_up

    def backup(self, now: datetime | None = None) -> bool:
        """Grava a cópia de segurança se o projeto mudou desde a última (§2)."""
        if not self.backup_due:
            return False
        try:
            display_layers.write_display(self.doc, self.doc.display)
            recovery.write(self.doc, self.recovery_path, self.path, now or datetime.now())
        except (OSError, RuntimeError) as e:
            self.message(f"não foi possível gravar a cópia de segurança: {e}", "aviso")
            return False
        self._backed_up = self._changes
        self._emit("backup")
        return True

    def heartbeat(self, now: datetime | None = None) -> None:
        """Sinal de vida da cópia desta sessão (§2): ela não é oferecida a outra janela."""
        if self.recovery_path is not None:
            recovery.touch(self.recovery_path, now or datetime.now())

    def discard_backup(self) -> None:
        if getattr(self, "recovery_path", None) is not None:
            recovery.remove(self.recovery_path)

    def orphan_backups(self, now: datetime | None = None) -> list[dict]:
        """Cópias de sessões que não fecharam direito, da mais recente (§4)."""
        return recovery.orphans(self.recovery_dir, self.recovery_path, now or datetime.now())

    def recover(self, entry: dict) -> None:
        """Abre a cópia como projeto modificado, com o nome do arquivo original; ela
        passa a ser a cópia desta sessão (§4)."""
        doc = Document.open(str(entry["path"]))
        doc.display = display_layers.read_display(doc)
        self._attach(doc, entry["file"], modified=True)
        if self.recovery_path is not None:
            recovery.adopt(entry, self.recovery_path, datetime.now())
        else:
            recovery.remove(entry["path"])
        self.message(f"Projeto recuperado da cópia de segurança de "
                     f"{entry['saved']:%d/%m às %H:%M}; salve para guardar as alterações")

    def discard_orphan(self, entry: dict) -> None:
        recovery.remove(entry["path"])

    @property
    def storey(self):
        return self.doc.find(self.storey_id) if self.storey_id else None

    def set_storey(self, storey) -> None:
        self.storey_id = storey.GlobalId if storey is not None else None
        self.selection.clear()
        self._emit("storey")

    # --- transações --------------------------------------------------------------------

    def run(self, build: Callable[[], Transaction] | Transaction) -> bool:
        """Monta (se preciso) e aplica a transação. Recusas do núcleo viram mensagem."""
        try:
            tx = build() if callable(build) else build
            if not tx.ops:
                return False
            self._check_layers(tx)
            self.history.commit(tx)
        except OpError as e:
            self.message(str(e), "recusa")
            return False
        self._show_created(tx)
        return True

    # --- camadas (spec/ui 18) ----------------------------------------------------------

    @property
    def display(self) -> display_layers.Display:
        return self.doc.display

    def set_display(self, display: display_layers.Display) -> None:
        """Exibição das camadas (§5.1): não é operação. Elementos que ficaram ocultos ou
        bloqueados saem da seleção (§4)."""
        self.doc.display = display
        blocked = display_layers.hidden_ids(self.doc) | display_layers.locked_ids(self.doc)
        self.selection -= blocked
        self._emit("layers")
        self._emit("selection")

    def _check_layers(self, tx: Transaction) -> None:
        """Criação em camada bloqueada é recusada (§3.2)."""
        config = display_layers.read_config(self.doc)
        if config is None or not self.doc.display.locked:
            return
        for kind, _, _ in display_layers.created(tx, self.doc):
            target = display_layers.default_layer(config, kind) or display_layers.NONE
            if target in self.doc.display.locked:
                raise OpError(f"a camada {display_layers.layer_name(self.doc, target)} está "
                              "bloqueada; desbloqueie-a no painel Camadas para desenhar nela")

    def _show_created(self, tx: Transaction) -> None:
        """Elemento criado em camada oculta: a camada é mostrada, com aviso (§3.2)."""
        if not self.doc.display.hidden:
            return
        shown = []
        for _, gid, _ in display_layers.created(tx, self.doc):
            element = self.doc.find(gid)
            if element is None:
                continue
            target = display_layers.layer_of(self.doc, element) or display_layers.NONE
            if target in self.doc.display.hidden and target not in shown:
                shown.append(target)
        if shown:
            display = self.doc.display
            for target in shown:
                display = display.with_layer(target, visible=True)
            self.set_display(display)
            names = ", ".join(display_layers.layer_name(self.doc, x) for x in shown)
            self.message(f"Camada {names} mostrada para exibir o que foi criado")

    def undo(self) -> None:
        tx = self.history.undo()
        if tx is not None:
            self.message(f"Desfeito: {tx.label}")

    def redo(self) -> None:
        tx = self.history.redo()
        if tx is not None:
            self.message(f"Refeito: {tx.label}")

    def _on_history(self, kind: str, tx: Transaction, changed: set[str]) -> None:
        self.modified = True
        self._changes += 1
        self.last_changed = changed
        self.last_tx = tx
        self.selection = {g for g in self.selection if self.doc.find(g) is not None}
        if self.storey_id and self.doc.find(self.storey_id) is None:
            storeys = self.doc.storeys()
            self.storey_id = storeys[0].GlobalId if storeys else None
        self._write_journal()
        self._emit("model")

    def select(self, gids, add: bool = False) -> None:
        gids = {g for g in gids if g}
        if self.doc.display.hidden or self.doc.display.locked:  # spec/ui 18 §4
            gids -= display_layers.hidden_ids(self.doc) | display_layers.locked_ids(self.doc)
        if add:
            self.selection ^= gids
        else:
            self.selection = gids
        self._emit("selection")

    # --- diário (spec/ui §9.2) -------------------------------------------------------

    @property
    def journal_path(self) -> Path | None:
        if self.journal_dir is None:
            return None
        return self.journal_dir / f"{self.started:%Y-%m-%d_%H-%M-%S}.json"

    def _write_journal(self) -> None:
        path = self.journal_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Cada transação vira texto uma vez só (a importação de um desenho pode ter
            # muitos MB; refazer o JSON inteiro a cada clique ficaria lento).
            cache = self._journal_cache
            parts = []
            for tx in self.history.journal:
                key = id(tx)
                if key not in cache or cache[key][0] is not tx:
                    cache[key] = (tx, json.dumps(tx.to_dict(), ensure_ascii=False))
                parts.append(cache[key][1])
            head = json.dumps({"started": self.started.isoformat(timespec="seconds"),
                               "file": self.path}, ensure_ascii=False)[:-1]
            path.write_text(f'{head}, "transactions": [{", ".join(parts)}]}}',
                            encoding="utf-8")
        except OSError as e:
            logging.getLogger(__name__).debug("diário não gravado: %s", e)
