---
documento: Quantitativos e tabelas (quadro de esquadrias, quadro de áreas, tabelas configuráveis)
requisito: RF-QTD-01, RF-QTD-02, RF-QTD-03, RF-QTD-05
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: aprovado
revisor: OTTO
---

# Quantitativos e tabelas (pacote 11)

## 1. Propósito
Tirar do modelo as listas que o projeto precisa: o **quadro de esquadrias**, o **quadro
de áreas** e tabelas montadas pelo usuário, como "paredes por tipo com comprimento e área"
ou "volume de concreto da estrutura". Elas podem ser exportadas para planilha (CSV e
XLSX). As tabelas leem as quantidades que cada elemento já grava no IFC
(`Qto_*BaseQuantities`, RF-QTD-01), então o número da tabela é o mesmo do arquivo.

Fica de fora (V1): tabela na prancha (RF-QTD-04), editar propriedades pela tabela
(RF-QTD-06), fórmulas e colunas calculadas pelo usuário, filtros por propriedade
qualquer, orçamento com SINAPI (RF-QTD-07, V2).

## 2. Quantidades por elemento (RF-QTD-01)
Já existem. Esta spec só fixa o que cada tabela lê:

| Elemento | Conjunto | Quantidades usadas |
|---|---|---|
| Parede | `Qto_WallBaseQuantities` | `Length`, `Width`, `Height`, `NetSideArea`, `GrossSideArea`, `NetVolume` |
| Porta | `Qto_DoorBaseQuantities` | `Width`, `Height`, `Area` |
| Janela | `Qto_WindowBaseQuantities` | `Width`, `Height`, `Area` |
| Laje | `Qto_SlabBaseQuantities` | `NetArea`, `Perimeter`, `Width` (espessura), `NetVolume` |
| Pilar | `Qto_ColumnBaseQuantities` | `Length` (altura), `CrossSectionArea`, `NetVolume` |
| Viga | `Qto_BeamBaseQuantities` | `Length`, `CrossSectionArea`, `NetVolume` |
| Cobertura | `Qto_RoofBaseQuantities` + `BrasBim_Cobertura` | `NetArea` (telhado), `AreaProjecao` (em planta) |
| Ambiente | `Qto_SpaceBaseQuantities` | `NetFloorArea`, `GrossPerimeter`, `Height` |

**Contagem** é o número de elementos da linha. Um elemento de outro programa sem
quantidades aparece com o campo vazio, e o vazio conta como zero nos totais.

## 3. Tabela
Uma tabela é uma **definição** guardada no projeto: o que listar, quais colunas, filtro,
agrupamento e totais. Os valores são calculados na hora a partir do modelo, e ela se
atualiza sozinha quando o modelo muda.

### 3.1 Definição
| Campo | Valores | Padrão |
|---|---|---|
| Nome | texto | "Tabela N" |
| Categoria | paredes, portas, janelas, esquadrias (portas e janelas), lajes, pilares, vigas, coberturas, ambientes | — |
| Colunas | lista ordenada de campos da categoria (§3.2), cada uma com título editável | as do modelo |
| Filtro | pavimentos (todos ou uma lista); tipos (todos ou uma lista) | todos |
| Agrupar por | nenhum, ou um campo (ex.: tipo, pavimento) | nenhum |
| Linhas | **uma por elemento** ou **uma por grupo** (resumida: contagem e somas) | uma por elemento |
| Ordem | um campo, crescente ou decrescente | o do agrupamento, depois o código |
| Totais | sim ou não: subtotal por grupo e total geral, só nas colunas que somam | sim |

### 3.2 Campos por categoria
Os campos que **somam** (contagem, comprimentos, áreas e volumes) entram nos subtotais e
no total. Os outros mostram o valor quando ele é o mesmo em todo o grupo, e "vários"
quando não é.

| Categoria | Campos |
|---|---|
| Todas | Pavimento, Tipo, Nome, Contagem, GlobalId |
| Paredes | Comprimento, Espessura, Altura, Área lateral (líquida, uma face), Área lateral bruta, Volume |
| Portas, janelas, esquadrias | Código (do tipo, ex. "P1", "J2"), Classe (porta ou janela), Largura, Altura, Peitoril, Área do vão, Operação (texto do tipo) |
| Lajes | Área, Perímetro, Espessura, Volume |
| Pilares | Seção ("20×40"), Altura, Volume |
| Vigas | Seção, Comprimento, Volume |
| Coberturas | Forma, Inclinação (%), Área do telhado, Área em planta |
| Ambientes | Número, Nome do ambiente, Área útil, Perímetro, Pé-direito |

Números com duas casas e vírgula decimal (ex.: "12,35"), unidade no título da coluna
("Área (m²)"). A contagem não tem casas.

### 3.3 Modelos prontos (RF-QTD-03)
**Nova tabela** oferece os modelos abaixo, que o usuário pode mudar depois:

| Modelo | Categoria | Colunas | Agrupar | Linhas |
|---|---|---|---|---|
| **Quadro de esquadrias** | esquadrias | Código, Tipo, Largura, Altura, Peitoril, Contagem | Tipo | uma por grupo |
| **Quadro de áreas** | ambientes | Número, Nome do ambiente, Área útil, Perímetro | Pavimento | uma por elemento, com subtotal por pavimento |
| **Paredes por tipo** | paredes | Tipo, Espessura, Comprimento, Área lateral, Volume | Tipo | uma por grupo |
| **Estrutura (concreto)** | pilares, vigas e lajes, cada um numa tabela | Tipo/Seção, Contagem, Volume | Tipo | uma por grupo |
| **Em branco** | escolhida | Tipo, Contagem | — | uma por elemento |

O **quadro de áreas** tem também uma linha de **área construída** por pavimento: a área
dentro do contorno externo das paredes, com as paredes incluídas (`rooms.
building_outline`, todas as edificações do pavimento). A área útil é a soma dos ambientes.
**Ponto de revisão** (o quadro de prefeitura muda de cidade para cidade; o modelo de
prefeitura é RF-DOC-16, V1).

## 4. Dados e IFC
- **Tabela:** `IfcAnnotation` com `ObjectType` "Tabela", contida na edificação e sem
  representação, com a definição em JSON no Pset `BrasBim_Tabela`, como a prancha
  (spec/ui 15 §4). Operações `table.create` / `.delete` / `.edit`. *(Decisão do
  projeto: o IFC não tem entidade padrão para a definição de uma tabela. `IfcTable` é
  um recurso para valores, sem GlobalId nem Psets, e os valores daqui são sempre
  recalculados.)*
- Excluir um pavimento ou um tipo que está no filtro de uma tabela o tira do filtro, na
  mesma transação. Se o filtro ficar vazio, a tabela passa a valer para todos.
- Os valores não ficam gravados no IFC: quem lê o arquivo calcula a partir das
  quantidades dos elementos, que estão lá.

## 5. Interface
- **Painel do projeto:** lista **Tabelas**, abaixo das pranchas, com **Nova tabela…**
  (escolhe o modelo, §3.3) e **Excluir**. O clique duplo abre a tabela numa aba, como a
  prancha.
- **Aba da tabela:** grade com cabeçalho, linhas de grupo (subtotal em negrito) e o
  total no fim. Clicar numa linha seleciona na planta os elementos dela; na linha de
  grupo, todos os do grupo. A aba se refaz a cada mudança do modelo.
- **Painel de propriedades da tabela** (com a aba ativa): nome, categoria, colunas (lista
  com marcar e desmarcar, subir e descer, e título editável), filtro de pavimentos e de
  tipos, agrupar por, linhas (por elemento ou por grupo), ordem e totais. Cada mudança é
  uma transação (`table.edit`), com desfazer.
- **Exportar:** botões na aba e **Arquivo > Exportar tabela…**:
  - **CSV:** separador `;`, vírgula decimal e UTF-8 com BOM, que é o que a planilha
    brasileira abre direto. Números sem separador de milhar, para continuarem números.
  - **XLSX:** uma planilha com o nome da tabela, cabeçalho em negrito, números como
    número (não texto) e a mesma ordem de linhas, grupos e totais. O arquivo é escrito
    pelo BrasBim com a biblioteca padrão do Python, sem dependência nova.
    **Ponto de revisão.**

## 6. Assistente
Ferramenta `table` (só leitura): recebe a categoria, as colunas, o agrupamento e o
filtro, e devolve as linhas. Serve para perguntas como "quantos metros quadrados de
parede tem o térreo?" e "quantas janelas J1 tem a casa?". As instruções dizem para usar
`table` nas perguntas de quantidade, em vez de somar à mão os dados de
`describe_model`.

## 7. Critérios de aceite (testes)
Casa de teste: retângulo de paredes (0, 0)–(8, 5) e parede interna em x = 5, no Térreo;
duas portas P1, três janelas J1 e uma J2; ambientes Sala e Quarto.

- [x] **TB01** Quadro de esquadrias: uma linha por tipo, com P1 = 2, J1 = 3 e J2 = 1;
      Largura e Altura do tipo; total de 6.
- [x] **TB02** Quadro de áreas: área útil de cada ambiente igual a `NetFloorArea`;
      subtotal do Térreo = soma; a área construída do Térreo é a área do contorno
      externo das paredes.
- [x] **TB03** Paredes por tipo: o comprimento total é a soma de `Length`, e a área
      lateral a soma de `NetSideArea`, já sem os vãos.
- [x] **TB04** Filtro por pavimento e por tipo; agrupar por pavimento; ordem
      decrescente; "vários" no campo que muda dentro do grupo.
- [x] **TB05** A tabela acompanha o modelo: inserir uma porta, mudar uma largura ou
      desfazer muda as linhas sem tocar na definição.
- [x] **TB06** `table.create` / `.edit` / `.delete` com desfazer e refazer; o diário
      reaplicado reproduz o IFC; reabrir o arquivo traz a tabela; o arquivo passa na
      validação de esquema.
- [x] **TB07** Excluir um pavimento que está no filtro o tira do filtro, na mesma
      transação.
- [x] **TB08** CSV: `;`, vírgula decimal, BOM, cabeçalho com unidades, linhas de grupo e
      total.
- [x] **TB09** XLSX: o arquivo abre como zip válido do formato (planilha, estilos,
      cadeias); números como número; reler a planilha dá os mesmos valores.
- [x] **TB10** Interface: Nova tabela pelo modelo abre a aba; clicar numa linha
      seleciona os elementos; mudar a coluna no painel é uma transação.
- [x] **TB11** Assistente: `table` com esquadrias agrupadas por tipo devolve as
      contagens.

## 8. Fontes públicas
- IFC 4.3 (`IfcElementQuantity` e os `Qto_*BaseQuantities` de cada elemento;
  `IfcAnnotation`; `IfcTable`, só para registrar por que não foi usado), no repositório
  oficial da buildingSMART, como nas specs dos elementos.
- **RFC 4180** (CSV) e **ECMA-376 / ISO/IEC 29500** (Office Open XML, SpreadsheetML),
  públicos: o mínimo para escrever o XLSX (pacote, planilha, estilos, cadeias
  compartilhadas).
- **NBR 12721** (áreas para incorporação) e normas municipais de quadro de áreas:
  **texto não lido**. O quadro de áreas daqui é de conhecimento geral (área útil por
  ambiente e área construída por pavimento).
- **CG**: quadro de esquadrias usual no Brasil (código, tipo, dimensões, peitoril,
  quantidade); CSV com `;` e vírgula decimal nas planilhas em português.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 9. Pontos de revisão
(a) Tabelas guardadas no IFC como anotação com JSON, como a prancha (§4).
(b) Modelos prontos e as colunas deles (§3.3).
(c) Área construída no quadro de áreas, pela face externa das paredes (§3.3).
(d) XLSX escrito sem biblioteca nova (§5). A alternativa é a `openpyxl`, de licença
    MIT, que traria formatação mais rica.
(e) Clicar na linha seleciona os elementos na planta (§5).

**Decisões do revisor (2026‑10‑19):** (a) a (e) aprovados como estão: anotação com JSON;
os cinco modelos com as colunas do §3.3; área construída pela face externa das paredes;
XLSX com a biblioteca padrão; clique na linha seleciona na planta.
