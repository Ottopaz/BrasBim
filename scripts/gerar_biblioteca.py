# SPDX-License-Identifier: GPL-3.0-or-later
"""Grava a biblioteca inicial de objetos (brasbim/core/objects/builtin.py) em
brasbim/library/objetos/ (spec/elementos/objeto-parametrico.md §4.5).

Uso: .venv/Scripts/python scripts/gerar_biblioteca.py
"""

from pathlib import Path

from brasbim.core.objects import builtin, library

OUT = Path(__file__).resolve().parents[1] / "brasbim" / "library" / "objetos"


def main() -> None:
    for name, makers in builtin.FILES.items():
        states = [s for make in makers for s in make()]
        path = OUT / name
        library.write_file(path, states)
        print(f"{path.relative_to(OUT)}: {len(states)} tipos")
    (OUT / "LICENCA.md").write_text(
        "# Biblioteca de objetos do BrasBim\n\n"
        "Objetos feitos do zero para o BrasBim, sob a licença Creative Commons Atribuição "
        "4.0 Internacional (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/deed.pt-br\n\n"
        "Gerada por `scripts/gerar_biblioteca.py` a partir de "
        "`brasbim/core/objects/builtin.py`. As medidas são as usuais no mercado brasileiro, "
        "como ponto de partida; a altura da bacia acessível fica a conferir na NBR 9050.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
