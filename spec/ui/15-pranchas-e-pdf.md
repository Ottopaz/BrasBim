---
documento: Documentação 3 — pranchas com carimbo e exportação em PDF
requisito: RF-DOC-09, RF-DOC-10, RF-PRJ-06 (parte)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: aprovado
revisor: OTTO (aprovado em 2026-10-16)
---

# Documentação 3: pranchas e PDF (pacote 8)

## 1. Propósito
Último dos três pacotes de documentação: montar **pranchas** com plantas, cortes e
fachadas na escala, com margens, carimbo (legenda) e marcas de dobra, e **exportar em
PDF vetorial** para imprimir ou mandar à prefeitura (RF-DOC-09, RF-DOC-10).

Fica de fora (V1): DXF (RF-DOC-11), revisões no carimbo (RF-DOC-13), tabelas,
perspectivas e vistas 3D na prancha (RF-DOC-14), conjuntos por etapa e modelos de
prefeitura (RF-DOC-15, 16), recorte manual da área de cada vista.

## 2. Formatos, margens e carimbo *(CG; conferência com a NBR 16752 pendente)*
| Formato | Tamanho (mm) | Margem esquerda | Demais margens |
|---|---|---|---|
| A0 | 1189 × 841 | 25 | 10 |
| A1 | 841 × 594 | 25 | 10 |
| A2 | 594 × 420 | 25 | 7 |
| A3 | 420 × 297 | 25 | 7 |
| A4 | 297 × 210 | 25 | 7 |

- Orientação **horizontal** (padrão) ou vertical; o A4 também na vertical.
- Quadro: retângulo na margem, linha de 0,5 mm.
- **Carimbo** no canto inferior direito, dentro do quadro, com **178 mm** de largura (para
  ficar à vista com a folha dobrada em A4) e as linhas *(decisão do projeto)*:
  1. Nome do projeto (grande)
  2. Endereço da obra
  3. Proprietário
  4. Responsável técnico e registro (CAU ou CREA)
  5. Conteúdo da prancha (ex.: "Planta baixa do térreo")
  6. Escala(s) (das vistas da prancha, sem repetir: "1:50 / 1:100"), data e folha
     ("02/05")
- **Marcas de dobra**: traços curtos na borda do papel nas posições de dobra para o
  formato A4 (190 mm a partir da direita e a cada 190 mm; a primeira dobra horizontal
  a 297 mm de baixo) *(CG)*. Ponto de revisão (c).

## 3. Vistas na prancha
- Uma prancha tem vistas: a **planta** de um pavimento ou um **corte/fachada** (pacote
  7). Cada vista fica na escala dela (a do pavimento, spec/ui 13 §2, ou a da vista, spec/ui
  14 §2) e mostra tudo o que tem (o limite é o retângulo que cabe o desenho).
- Posição: o ponto do papel (mm, a partir do canto inferior esquerdo da folha) onde fica
  o centro da vista. Ao pôr uma vista nova, ela vai para o primeiro lugar livre da
  esquerda para a direita *(decisão do projeto)*; depois se arrasta.
- A planta na prancha é desenhada como na tela (spec/ui 06, 10, 12, 13), sem grade, sem
  seleção e sem as ferramentas; a vista de corte também (spec/ui 14). As espessuras de
  linha são as do papel (spec/ui 13 §8).

## 4. Dados e IFC
- **Prancha:** `IfcAnnotation` com `ObjectType` "Prancha", contida na edificação, com o
  estado em JSON no Pset `BrasBim_Prancha`: número ("01"), título (conteúdo), formato,
  orientação e as vistas (`[{"kind": "plan", "storey": GlobalId} | {"kind": "view",
  "view": GlobalId}, "at": [x, y] em mm]`). Operações `sheet.create` / `.delete` /
  `.edit`. *(Decisão do projeto: o IFC não tem entidade padrão para a prancha; ficando
  no arquivo, ela se reabre igual.)*
- **Dados do projeto para o carimbo** (parte de RF-PRJ-06): Pset `BrasBim_Projeto` no
  `IfcProject` com `Endereco`, `Proprietario`, `Responsavel`, `Registro`; o nome do
  projeto é o `IfcProject.Name`. Operação `project.edit`. (`IfcPostalAddress` e o
  responsável como `IfcPerson`: V1.)
- Vista que é excluída sai da prancha (a operação que exclui a vista leva o
  `sheet.edit`).

## 5. Interface
- Painel do projeto: lista **Pranchas** (abaixo das vistas): **Nova prancha** (A3
  horizontal, número seguinte), **Excluir**; clique duplo abre a prancha numa aba.
- **Aba da prancha:** o papel em escala na tela (zoom e deslocamento como a planta), com
  o quadro, o carimbo e as vistas desenhadas. Arrastar uma vista a move (uma transação
  ao soltar). Botão direito numa vista: **Tirar da prancha**.
- **Pôr na prancha:** no painel da prancha, uma lista com os pavimentos e as vistas para
  acrescentar.
- Painel da prancha: Número, Título, Formato, Orientação, lista das vistas; e
  **Projeto…** (abre os dados do carimbo: nome, endereço, proprietário, responsável,
  registro).
- **Arquivo > Exportar PDF…**: todas as pranchas (ou só a aberta), uma por página, no
  tamanho do formato, em vetor. Data do carimbo = a do dia da exportação.

## 6. Critérios de aceite (testes)
Térreo e Superior; retângulo de paredes (0, 0)–(6, 4); Corte A; escala 1:50.

- [x] **PR01** Nova prancha: `IfcAnnotation` "Prancha" na edificação, número "01", A3
      horizontal; a segunda é "02".
- [x] **PR02** Planta do Térreo na prancha 01: no papel, a largura do desenho das paredes
      é 6000 mm / 50 = 120 mm (± 1 mm).
- [x] **PR03** Corte A na prancha: aparece com o título "CORTE A"; excluir o Corte A o
      tira da prancha na mesma transação; desfazer volta.
- [x] **PR04** Carimbo com o nome do projeto, o proprietário e a folha "01/02"; a escala
      "1:50".
- [x] **PR05** Exportar PDF: um arquivo com 2 páginas de 420 × 297 mm.
- [x] **PR06** Mover uma vista na prancha (arrasto): `sheet.edit`; desfazer volta.
- [x] **PR07** O arquivo passa na validação de esquema; o diário reaplicado reproduz o IFC.

## 7. Fontes públicas
- IFC 4.3: `IfcAnnotation` e `IfcProject`, como em spec/ui 13 §11.
- **NBR 16752** (formatos, margens e legenda) e **NBR 13142** (dobramento): **texto não
  lido**; os valores acima são de conhecimento geral e ficam para conferência.
- **Qt** (`QPdfWriter`, licença LGPL do PySide6): geração do PDF.
- **CG**: carimbo no canto inferior direito, largura para dobra em A4, campos usuais
  (projeto, endereço, proprietário, responsável técnico, conteúdo, escala, data, folha).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 8. Pontos de revisão
(a) Pranchas guardadas no IFC como anotações com JSON (§4).
(b) Campos do carimbo (§2).
(c) Margens e marcas de dobra pelos valores usuais, a conferir na norma (§2).
(d) A3 horizontal como padrão da prancha nova (§5).
