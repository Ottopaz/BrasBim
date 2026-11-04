---
documento: Unidades e casas decimais do projeto
requisito: RF-DOC (cotas e anotação); pedido do revisor em 2026-11-04
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-04
status: em revisão (etapa 1 implementada na sequência, como no fluxo do MVP)
revisor: OTTO
---

# Unidades e casas decimais do projeto

## 1. Propósito
Escolher **em que unidade e com quantas casas** cada tipo de medida aparece no desenho:
cotas lineares, de raio e de ângulo, cota de nível, cota em elevação, medidas das
esquadrias e áreas. Hoje tudo sai em metros com 2 casas (ângulo com 1), fixo no código.
O modelo continua exato, em metros no IFC: isto muda **só o texto mostrado**.

## 2. Uso
- Na **barra da vista** entra o botão **Unidades**, com o resumo da unidade das cotas
  ("m · 2 casas", "cm · 0 casas"). O menu traz os padrões prontos e **Unidades do
  projeto**, que abre a janela.
- **Padrões prontos** (um clique; mudam cota linear, raio e esquadria, que costumam andar
  juntos; nível, elevação, ângulo e área ficam):
  - Metros, 2 casas (projeto legal);
  - Centímetros, sem casas (executivo);
  - Milímetros, sem casas.
- **Janela Unidades do projeto**: uma linha por tipo de medida, com as colunas
  **Unidade**, **Casas** (0 a 4), **Mostrar a unidade** e **Ocultar zeros finais**, e um
  exemplo ao lado ("3,25" → "325"):

  | Tipo de medida | Onde aparece | Unidades | Padrão |
  |---|---|---|---|
  | Cota linear | cotas, cotas automáticas da parede | m, cm, mm | m, 2 |
  | Raio e diâmetro | cota de raio (R, Ø) | m, cm, mm | m, 2 |
  | Ângulo | cota de ângulo | graus decimais; graus, minutos e segundos | graus, 1 |
  | Cota de nível | marca de nível na planta | m, cm, mm | m, 2 (com sinal) |
  | Cota em elevação | níveis dos pavimentos nos cortes e fachadas | m, cm, mm | m, 2 (com sinal) |
  | Esquadrias | etiqueta L × A / peitoril na planta | m, cm, mm | m, 2 |
  | Área | área dos ambientes na planta | m², cm² | m², 2 |

- Mudar uma linha é uma ação que se desfaz (Ctrl+Z) e vale para toda a equipe no projeto
  compartilhado. "Restaurar o padrão" volta à tabela acima.
- Ocultar zeros finais: "3,50" → "3,5", "3,00" → "3". Mostrar a unidade põe o símbolo
  depois do número ("325 cm", "12,40 m²"); na área ele vem ligado.

## 3. No IFC
- Pset `BrasBim_Unidades` no `IfcProject`, propriedade `Config` (texto JSON com uma
  entrada por tipo de medida: unidade, casas, mostrar unidade, ocultar zeros). Sem o Pset
  vale o padrão (arquivos antigos ficam iguais).
- As unidades do IFC (`IfcUnitAssignment`, metros) **não** mudam: só o texto das
  anotações. Os textos das cotas não são gravados no IFC (são refeitos ao desenhar).
- Operação `units.set` (before/after = a configuração), serializável (desfazer, diário,
  equipe).

## 4. Fica para depois (etapa 2)
- **Unidade de trabalho**: digitar e ler medidas nos campos, quadro de medidas e barra de
  estado na unidade escolhida (hoje sempre metros). Mexe em todos os campos: spec própria.
- **Tabelas**: unidade e casas dos valores calculados (comprimento, área, volume), e se
  o total soma o mostrado ou o exato.
- **Padrões com nome** ligados a cada vista salva (ex.: planta de prefeitura em m e
  detalhe em cm no mesmo projeto).
- **Precisão extra** em sobrescrito (a casa seguinte arredondada a 5).

## 5. Testes
UN01 padrão igual ao de hoje (nenhum texto muda sem o Pset); UN02 cota linear em cm sem
casas e em mm, com e sem unidade, ocultar zeros; UN03 raio, ângulo (decimal e graus,
minutos e segundos), nível e elevação (com sinal), esquadria e área; UN04 gravar, reabrir
o arquivo e desfazer/refazer (`units.set`); UN05 interface: botão na barra da vista,
padrões prontos e a janela.

## 6. Pontos para o revisor
- (a) Os sete tipos de medida bastam? (O Archicad separa também o peitoril; aqui ele vai
  junto da esquadria.)
- (b) Os padrões prontos mudam só cota linear, raio e esquadria (proposta), ou tudo?
- (c) Na área, só m² e cm² (proposta), ou também hectare para o terreno?
- (d) A unidade de trabalho (§4) é a próxima etapa, ou as tabelas antes?
- (e) Precisão extra em sobrescrito (comum em cotas em cm com milímetro: 152⁵) interessa?

## 7. Fontes
`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_unidades.md` (ajuda do Archicad
18, 19, 20, 24 e 28 — unidades de trabalho, preferências de cota, unidades e regras de
cálculo —, documentação da API e fórum da Graphisoft).
