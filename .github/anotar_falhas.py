# SPDX-License-Identifier: LGPL-3.0-or-later
"""Transforma a saída do pytest no CI em anotações do GitHub Actions.

Uso: ``python .github/anotar_falhas.py pytest.log <código de saída>``. Cada teste que
falhou vira uma anotação; se o processo caiu (falha de segmentação etc.), o último teste
que começou e a pilha do ``faulthandler`` viram outra. As anotações são públicas na página
do commit, ao contrário do log completo.
"""

import re
import sys


def escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


def main(path: str, code: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # no Windows, o console não é UTF-8
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    failed = [ln for ln in lines if re.match(r"^(FAILED|ERROR) ", ln)]
    for ln in failed[:40]:
        print(f"::error title=Teste::{escape(ln)}")

    fatal = next((i for i, ln in enumerate(lines) if "Fatal Python error" in ln), None)
    if fatal is not None:
        started = [ln for ln in lines[:fatal] if "::" in ln and not ln.startswith(" ")]
        last = started[-1] if started else "(nenhum)"
        stack = "\n".join(lines[fatal:fatal + 45])
        print(f"::error title=Queda do processo (código {code})::"
              f"{escape('Último teste: ' + last + chr(10) + stack)}")
    elif not failed:
        print(f"::error title=pytest saiu com {code}::{escape(chr(10).join(lines[-40:]))}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
