# SPDX-License-Identifier: LGPL-3.0-or-later
"""Torre paramétrica de 30 pavimentos, modelada pelos comandos do núcleo do BrasBim.

Uso: python exemplos/torre_parametrica.py [pasta_de_saida] [pavimentos]

Cada pavimento é a mesma planta (um quadrado de cantos arredondados) girada um pouco em
relação ao de baixo e com a largura variando com a altura. Por pavimento: laje de
concreto, pele de vidro recuada da borda da laje, brises verticais na borda, pilares
redondos e o núcleo de concreto. Grava ``torre.ifc`` (IFC 4.3).

O modelo da página do projeto (``site/modelos/torre.glb``) sai deste IFC por
``python scripts/compactar_glb.py torre.ifc site/modelos/torre.glb``.
"""

import math
import sys
import time
from pathlib import Path

from brasbim.core.document import Document
from brasbim.core.ops import History, Transaction
from brasbim.core.structure import commands as st
from brasbim.core.walls import commands as wc

PE_DIREITO = 3.4          # m, de piso a piso
GIRO_TOTAL = 90.0         # graus, da base ao topo
LADO = 30.0               # m, largura da planta na base
LADOS = 28                # segmentos da pele de vidro por pavimento
BRISES = 56               # brises por pavimento


def contorno(lado: float, giro: float, n: int, recuo: float = 0.0) -> list[tuple[float, float]]:
    """Superelipse (quadrado de cantos arredondados) de largura ``lado``, girada."""
    a = lado / 2 - recuo
    p = 4.0
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n + math.pi / n
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2 / p), c)
        y = a * math.copysign(abs(s) ** (2 / p), s)
        g = math.radians(giro)
        pts.append((round(x * math.cos(g) - y * math.sin(g), 4),
                    round(x * math.sin(g) + y * math.cos(g), 4)))
    return pts


def largura(i: int, total: int) -> float:
    """Largura do pavimento ``i``: incha no terço de baixo e afina até o topo."""
    h = i / max(total - 1, 1)
    return LADO * (1.0 + 0.10 * math.sin(math.pi * h * 1.4) - 0.18 * h * h)


def main(saida: Path, total: int = 30) -> None:
    t0 = time.perf_counter()
    doc = Document.new("Torre paramétrica")
    hist = History(doc)

    for i in range(total + 1):
        nome = "Térreo" if i == 0 else ("Cobertura" if i == total else f"Pavimento {i}")
        hist.commit(wc.create_storey(doc, nome, round(i * PE_DIREITO, 3)))
    pavimentos = doc.storeys()

    hist.commit(st.create_slab_type(doc, "Laje maciça 25", [
        {"material": "Contrapiso", "thickness": 0.05},
        {"material": "Concreto", "thickness": 0.20},
    ]))
    laje = doc.ifc.by_type("IfcSlabType")[0]
    hist.commit(wc.create_wall_type(doc, "Pele de vidro", [
        {"material": "Vidro", "thickness": 0.04, "category": "Finish"},
    ], predefined_type="SOLIDWALL"))
    hist.commit(wc.create_wall_type(doc, "Núcleo de concreto 30", [
        {"material": "Concreto", "thickness": 0.30, "category": "LoadBearing"},
    ], predefined_type="SOLIDWALL"))
    vidro, nucleo = doc.ifc.by_type("IfcWallType")
    hist.commit(st.create_column_type(doc, "Pilar redondo 70", {"shape": "circle", "d": 0.70}))
    hist.commit(st.create_column_type(doc, "Brise 12 × 60",
                                      {"shape": "rect", "b": 0.12, "h": 0.60},
                                      material="Alumínio"))
    pilar, brise = doc.ifc.by_type("IfcColumnType")

    for i, pav in enumerate(pavimentos):
        giro = GIRO_TOTAL * i / total
        lado = largura(i, total)
        hist.commit(st.create_slab(doc, laje, pav, contorno(lado, giro, 72)))
        if i == total:
            break  # a cobertura só tem a laje

        pele = contorno(lado, giro, LADOS, recuo=1.2)
        hist.commit(wc.create_chain(doc, vidro, pav, pele, closed=True, ref_line="axis"))
        hist.commit(wc.create_chain(doc, nucleo, pav, [(-5, -5), (5, -5), (5, 5), (-5, 5)],
                                    closed=True, ref_line="axis"))

        # brises na borda da laje, perpendiculares a ela
        borda = contorno(lado, giro, BRISES, recuo=0.35)
        ops = []
        for k, (x, y) in enumerate(borda):
            ax, ay = borda[k - 1]
            bx, by = borda[(k + 1) % BRISES]
            ang = math.degrees(math.atan2(by - ay, bx - ax)) + 90
            ops += st.create_column(doc, brise, pav, (x, y), angle=round(ang, 2),
                                    name=f"B{i}.{k + 1}").ops

        # pilares em anel, girando com a planta
        for k in range(12):
            t = 2 * math.pi * k / 12 + math.radians(giro)
            r = lado * 0.32
            ops += st.create_column(doc, pilar, pav,
                                    (round(r * math.cos(t), 3), round(r * math.sin(t), 3)),
                                    name=f"P{i}.{k + 1}").ops
        hist.commit(Transaction(f"Brises e pilares do pavimento {i}", ops))
        print(f"pavimento {i}: {time.perf_counter() - t0:.0f} s", flush=True)

    saida.mkdir(parents=True, exist_ok=True)
    doc.save(str(saida / "torre.ifc"))
    print(f"torre.ifc gravado em {time.perf_counter() - t0:.0f} s")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "."),
         int(sys.argv[2]) if len(sys.argv) > 2 else 30)
