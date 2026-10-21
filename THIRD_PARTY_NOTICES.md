# Componentes de terceiros

O BrasBim (núcleo LGPL‑3.0‑or‑later, aplicativo GPL‑3.0‑or‑later) usa os componentes
abaixo, cada um sob a sua licença. Versões e licenças conferidas nos metadados dos
pacotes instalados em 2026‑10‑21 (`importlib.metadata`); ao trocar de versão, conferir
de novo. Nenhum código destes projetos foi copiado para o BrasBim: eles são usados como
bibliotecas.

## Dependências diretas

| Componente | Versão | Licença | Uso no BrasBim | Projeto |
|---|---|---|---|---|
| IfcOpenShell | 0.9.0 | LGPL‑3.0‑or‑later | Modelo IFC em memória, `ifcopenshell.api`, geometria (`ifcopenshell.geom`), validação | http://ifcopenshell.org |
| pyclipr | 0.1.8 | Boost Software License 1.0 (Clipper2, também BSL‑1.0) | Booleanos 2D da planta | https://github.com/drlukeparry/pyclipr |
| ezdxf | 1.4.5 | MIT | Leitura de DXF ao importar desenhos (spec/ui 22) | https://github.com/mozman/ezdxf |
| shapely | 2.2.0 | BSD‑3‑Clause (usa a GEOS, LGPL‑2.1) | Triangulação do terreno e testes de ponto em polígono | https://shapely.readthedocs.io |
| NumPy | 2.5.4 | BSD‑3‑Clause (com partes 0BSD, MIT, Zlib, CC0‑1.0) | Malhas 3D, terreno | https://numpy.org |
| PySide6 / Shiboken6 (Qt for Python) | 6.12.0 | LGPL‑3.0‑only (ou GPL‑2.0/3.0) | Interface | https://pyside.org |
| PyOpenGL | 3.1.10 | BSD | Vista 3D | https://mcfletch.github.io/pyopengl/ |

## Dependências indiretas (trazidas pelas de cima)

| Componente | Versão | Licença | Trazida por |
|---|---|---|---|
| lark | 1.3.1 | MIT | IfcOpenShell |
| isodate | 0.7.2 | BSD | IfcOpenShell |
| python-dateutil | 2.9.0.post0 | Apache‑2.0 ou BSD | IfcOpenShell |
| six | 1.17.0 | MIT | python-dateutil |
| pyparsing | 3.3.3 | MIT | IfcOpenShell, ezdxf |
| typing_extensions | 4.16.0 | PSF‑2.0 | IfcOpenShell, ezdxf |
| fontTools | 4.67.0 | MIT | ezdxf |

## Recursos embutidos

| Recurso | Licença | Onde |
|---|---|---|
| Fonte Archivo (Omnibus-Type, The Archivo Project Authors) | SIL Open Font License 1.1 | `brasbim/ui/fonts/` (texto da licença em `OFL.txt`) |
| Ícones | Próprios do BrasBim, GPL‑3.0‑or‑later | `brasbim/ui/icons/`, gerados por `scripts/gerar_icones.py` |

## Ferramentas de desenvolvimento (não distribuídas)

| Componente | Versão | Licença |
|---|---|---|
| pytest | 9.1.1 | MIT |
| ruff | 0.17.0 | MIT |

## Programas externos opcionais (não distribuídos)

Usados só se o usuário os instalar, chamados como programas à parte, para converter DWG
em DXF (spec/ui 22 §2):

| Programa | Licença | Observação |
|---|---|---|
| ODA File Converter | Gratuito, proprietário (Open Design Alliance) | O usuário aceita a licença dele ao instalar |
| LibreDWG (`dwg2dxf`) | GPL‑3.0‑or‑later | Programa separado; não ligado ao BrasBim |

## Compatibilidade

Todas as licenças acima permitem o uso pelo núcleo LGPL e pelo aplicativo GPL. Pontos de
atenção: a GEOS (LGPL‑2.1) e o Qt (LGPL‑3.0) exigem que o usuário possa trocar essas
bibliotecas; distribuídas como pacotes dinâmicos do Python, isso já ocorre. Rever este
arquivo antes de cada versão pública (`cleanroom/PROCESSO.md` §6).
