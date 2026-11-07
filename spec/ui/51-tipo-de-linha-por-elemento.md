---
documento: Tipo de linha por elemento
requisito: pedido do revisor no teste de uso (2026-11-07); RF-DOC-03 (espessuras e linhas)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-07
status: rascunho (pontos (a)–(e) no §8)
revisor: OTTO
---

# Tipo de linha por elemento

## 1. Propósito
No teste de uso de 2026‑11‑07 o revisor pediu: "todos os elementos construtivos eu tenho
que ter a possibilidade de escolher qual linha eu quero trabalhar, se é sólida, tracejada,
traço‑ponto etc.", **em cada elemento**. Hoje o tipo de linha é fixo pelo papel: corte e
vista contínuos, acima do plano e projeções tracejados. Esta spec deixa o usuário trocar o
tipo de linha de um elemento (ou de vários selecionados), sem mexer no tipo do elemento.

## 2. Tipos de linha
Lista fechada, com nomes próprios (NBR 8403 dá o uso de cada um nos desenhos técnicos):

| Chave | Nome na interface | Uso típico | Padrão (mm de papel) |
|---|---|---|---|
| `solid` | Contínua | contorno visível, corte | — |
| `dashed` | Tracejada | arestas invisíveis, acima do plano, projeção | 3 – 1,5 |
| `dashdot` | Traço e ponto | eixos, linha de simetria, plano de corte | 6 – 1,5 – 0,5 – 1,5 |
| `dashdotdot` | Traço e dois pontos | contorno de peça vizinha, posição extrema | 6 – 1,5 – 0,5 – 1 – 0,5 – 1,5 |
| `dotted` | Pontilhada | demolição, previsão, elementos futuros | 0,5 – 1 |
| `longdash` | Tracejada longa | divisa, limite de terreno | 8 – 2 |

O tamanho dos traços é em milímetros **de papel** (não muda com a escala), como já é nas
anotações (`DASH_PATTERNS`).

## 3. Uso
- **Ficha do elemento**, nova linha "Linha na planta" com três escolhas:
  - **Automática** (padrão): o que o BrasBim faz hoje, pelo papel (cortado contínuo,
    acima do plano tracejado, etc.);
  - um dos tipos do §2, que vale para **todas as linhas do elemento** na planta (corte,
    vista e projeção); a hachura e o preenchimento não mudam.
- Com vários elementos selecionados, a ficha mostra "vários" quando diferem; escolher
  aplica a todos (uma transação, Desfazer).
- Botão direito na planta: "Tipo de linha ▸" com a mesma lista.
- Vale para: parede, pilar, viga, laje, cobertura, forro, piso, escada, guarda‑corpo,
  porta, janela, abertura, objeto e ambiente (contorno). As anotações 2D (linha, polilinha,
  círculo, arco) já têm tipo de linha próprio e passam a ter a lista inteira do §2.

## 4. Onde aparece
- Planta (tela, prancha, PDF e DWG/DXF exportados: no DWG o tipo vira `linetype` com o
  nome do §2 em maiúsculas e o padrão).
- Cortes e fachadas: **ponto (b)**.
- O 3D não muda.

## 5. No IFC
- Pset `BrasBim_Linha` na ocorrência: `TipoLinha` (`IfcLabel`, a chave do §2). Sem o Pset
  = Automática.
- Proposta (ponto (d)): também gravar um `IfcStyledItem` com `IfcCurveStyle` na
  representação `FootPrint`/`Annotation` do elemento, `CurveFont` = `IfcCurveStyleFont`
  com o padrão do §2 (o IFC 4.3 define a fonte de curva por padrões de traço e espaço),
  para que outros programas leiam o tipo de linha.

## 6. Testes
- **TL01** escolher Tracejada numa parede: o Pset é gravado, as linhas da parede na
  planta saem tracejadas, a hachura não muda; Desfazer volta para Automática.
- **TL02** vários elementos de classes diferentes de uma vez; "vários" na ficha.
- **TL03** o PDF e o DXF exportados levam o tipo de linha.
- **TL04** abrir e salvar mantém o tipo; IFC válido no esquema.
- **TL05** interface: ficha e botão direito.

## 7. Fica para depois
- Tipos de linha do usuário (padrão próprio).
- Tipo de linha no tipo do elemento e por categoria (o revisor escolheu "em cada
  elemento").

## 8. Pontos para o revisor
- (a) A lista do §2 serve? Falta algum tipo que você usa?
- (b) O tipo escolhido vale **só na planta** (proposta) ou também em cortes e fachadas?
- (c) Uma escolha só para todas as linhas do elemento (proposta), ou separado por
  situação: linha de **corte**, de **vista** e de **projeção/acima do plano**?
- (d) Gravar também o `IfcCurveStyle` para outros programas (proposta: sim)?
- (e) Junto com o tipo, escolher também a **pena** (espessura e cor) do elemento, ou só o
  tipo de linha agora?

## 9. Fontes
- IFC 4.3 (buildingSMART, documentação pública): `IfcCurveStyle`, `IfcCurveStyleFont`,
  `IfcCurveStyleFontPattern`, `IfcPreDefinedCurveFont`, `IfcStyledItem`.
- ABNT NBR 8403 (aplicação de linhas em desenhos: tipos e larguras) e NBR 6492
  (representação de projetos de arquitetura), citadas pelo nome.
- Código atual do BrasBim: `brasbim/core/annotations/prims.py` (`DASHES`,
  `DASH_PATTERNS`), `brasbim/core/pens.py` (categorias de pena).
