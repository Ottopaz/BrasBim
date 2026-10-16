# SPDX-License-Identifier: GPL-3.0-or-later
"""Sessão de trabalho do aplicativo (``spec/ui/01-janela-e-ferramentas.md`` §2, §8, §9.2).

Guarda documento, histórico, arquivo, pavimento ativo, seleção e mensagens. É o único
ponto da interface que aplica transações. Não depende de Qt: a janela se inscreve em
``listeners`` e é avisada com o nome do evento (``document``, ``model``, ``selection``,
``storey``, ``messages``).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from brasbim.core.document import Document, OpError
from brasbim.core.fillings import commands as fc
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import commands as sc
from brasbim.core.walls import commands as cmd

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
    def __init__(self, journal_dir: Path | None = None):
        self.listeners: list[Callable[[str], None]] = []
        self.messages: list[dict] = []
        self.journal_dir = journal_dir
        self._handler = _MessageHandler(self)
        logging.getLogger("brasbim").addHandler(self._handler)
        self.new()

    def close(self) -> None:
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

    def _attach(self, doc: Document, path: str | None) -> None:
        self.doc = doc
        self.history = History(doc)
        self.history.listeners.append(self._on_history)
        self.path = path
        self.modified = False
        self.selection: set[str] = set()
        self.last_changed: set[str] = set()
        self.last_tx = None  # última transação feita, desfeita ou refeita
        storeys = doc.storeys()
        ground = [s for s in storeys if (s.Elevation or 0.0) >= -1e-6]
        self.storey_id = (ground or storeys or [None])[0]
        self.storey_id = self.storey_id.GlobalId if self.storey_id is not None else None
        self.started = datetime.now()
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
            history.commit(fc.create_door_type(doc, name, operation,
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
        self._attach(Document.open(path), path)
        self.message(f"Aberto: {path}")

    def save(self, path: str | None = None) -> None:
        path = path or self.path
        if not path:
            raise OpError("escolha onde salvar")
        self.doc.save(path)
        self.path = path
        self.modified = False
        self.message(f"Salvo: {path}")
        self._emit("document")

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
            self.history.commit(tx)
        except OpError as e:
            self.message(str(e), "recusa")
            return False
        return True

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
            data = {"started": self.started.isoformat(timespec="seconds"),
                    "file": self.path,
                    "transactions": [tx.to_dict() for tx in self.history.journal]}
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            logging.getLogger(__name__).debug("diário não gravado: %s", e)
