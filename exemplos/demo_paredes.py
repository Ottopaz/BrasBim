# SPDX-License-Identifier: LGPL-3.0-or-later
"""Demonstração: grava um IFC com paredes retas e em arco em dois pavimentos.

Uso: python exemplos/demo_paredes.py [saida.ifc]

Abra o arquivo em qualquer visualizador IFC. As junções L/T/X ainda não estão
implementadas, então os cantos aparecem sem recorte.
"""

import sys

from brasbim.core.document import Document
from brasbim.core.ops import History
from brasbim.core.walls import commands as cmd


def main(path: str) -> None:
    doc = Document.new("Demonstração de paredes")
    history = History(doc)
    history.commit(cmd.create_storey(doc, "Térreo", 0.0))
    history.commit(cmd.create_storey(doc, "Superior", 2.8))
    terreo, superior = doc.storeys()

    history.commit(cmd.create_wall_type(doc, "Alvenaria cerâmica 14", [
        {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
        {"material": "Bloco cerâmico", "thickness": 0.09, "category": "LoadBearing",
         "priority": 80},
        {"material": "Reboco", "thickness": 0.025, "category": "Finish", "priority": 20},
    ]))
    history.commit(cmd.create_wall_type(doc, "Drywall 9,5", [
        {"material": "Gesso acartonado", "thickness": 0.0125, "category": "Finish"},
        {"material": "Montante de aço", "thickness": 0.07},
        {"material": "Gesso acartonado", "thickness": 0.0125, "category": "Finish"},
    ], predefined_type="PARTITIONING"))
    alvenaria, drywall = doc.ifc.by_type("IfcWallType")

    # Térreo: retângulo 8 × 5 (face externa como referência, desenhado no sentido horário,
    # de modo que a parede fique para dentro), uma divisória e uma parede em arco.
    cantos = [(0, 0), (0, 5), (8, 5), (8, 0)]
    for a, b in zip(cantos, cantos[1:] + cantos[:1]):
        history.commit(cmd.create_wall(doc, alvenaria, terreo, a, b, ref_line="left_face"))
    history.commit(cmd.create_wall(doc, drywall, terreo, (4.5, 0.14), (4.5, 4.86),
                                   ref_line="axis"))
    history.commit(cmd.create_arc_wall(doc, alvenaria, terreo, (8, 1), (9.5, 2.5), (8, 4),
                                       ref_line="axis"))

    # Superior: platibanda de 1,10 m sobre o retângulo.
    for a, b in zip(cantos, cantos[1:] + cantos[:1]):
        history.commit(cmd.create_wall(doc, alvenaria, superior, a, b, ref_line="left_face",
                                       top_mode="fixed", fixed_height=1.10))

    doc.save(path)
    print(f"{len(doc.ifc.by_type('IfcWall'))} paredes gravadas em {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo_paredes.ifc")
