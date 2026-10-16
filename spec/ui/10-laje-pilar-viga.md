---
documento: Interface — laje, pilar e viga (ferramentas, opções, tipos, painel, alças, planta e 3D), versão básica
requisito: RF-ELE-02, RF-ELE-03, RF-ELE-04, RF-TIP-06, RF-UI-01, RF-UI-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15)
---

# Laje, pilar e viga na interface

## 1. Propósito
Pacote 4: pôr no aplicativo o **básico** dos três elementos estruturais, nas specs
`spec/elementos/laje.md`, `pilar.md` e `viga.md`. A ideia, pedida pelo revisor em
2026‑10‑15, é ter primeiro todos os elementos principais (parede, porta, janela, laje,
pilar, viga) e depois refinar cada um pelo uso.

Fica no padrão das ferramentas atuais: ícone na barra Ferramentas, barra **Opções**,
quadro de medidas (Tab), ponto de referência (spec 09 §2.1), mini-barra, painel em
blocos, planta pelo plano de corte (spec 06) e cor por material no 3D.

**Fica de fora nesta etapa (refinamento seguinte):** aberturas na laje, laje pelo
contorno das paredes, recortes entre elementos no 3D e nos volumes, alças no 3D,
etiquetas de pilar e viga, laje inclinada.

## 2. Ferramentas
Três ícones novos na barra **Ferramentas**, depois de Janela, nesta ordem: **Pilar**,
**Viga**, **Laje** *(decisão do projeto: a ordem em que se costuma lançar a estrutura)*.
Todas continuam ativas depois de criar; Esc volta a Selecionar. Funcionam também na
vista 3D, com o ponto no plano do pavimento ativo ou no elemento atingido (spec 07).

### 2.1 Pilar (`pilar.md` §4)
1. A pré-visualização mostra a seção do pilar presa ao cursor, no ponto de inserção e
   no ângulo da barra Opções.
2. **Barra de espaço** gira a pré-visualização 90° (e atualiza o ângulo da barra Opções).
3. Pontos de atração: os de hoje (pontas, meios, cruzamentos e faces das paredes) e os
   cantos e o centro dos pilares existentes.
4. Clique cria: (`column_type.create`, se faltar) → `column.create`.
5. Tab: quadro com **X** e **Y** em relação ao ponto de referência, se houver um pegado
   (spec 09 §2.1.1); sem referência, o quadro mostra só o **Ângulo**.

### 2.2 Viga (`viga.md` §4)
Igual à ferramenta Parede no modo reta (spec 01 e 07): clique no início, clique no fim,
continua em cadeia a partir do último ponto; Esc ou duplo-clique encerra a cadeia. Tab:
comprimento e ângulo; linhas de referência a 0°/90° e cruzamentos (spec 09 §2.1.1). A
pré-visualização mostra as duas faces da viga, tracejadas, e a linha de referência.
Pontos de atração: os de hoje mais o centro e os cantos dos pilares.

### 2.3 Laje (`laje.md` §4)
Dois modos na barra Opções: **Polígono** e **Retângulo**.
- Polígono: cada clique é um vértice; fecha clicando no primeiro ponto (o cursor muda
  quando está sobre ele), com duplo-clique ou com Enter. Esc tira o último vértice; sem
  vértices, cancela. Tab: comprimento e ângulo do lado atual, como a parede.
- Retângulo: dois cantos; Tab: largura e altura, como o retângulo de paredes.
- A pré-visualização mostra o contorno e um fundo claro translúcido. Contorno que se
  cruza fica em vermelho e não fecha (mensagem com o motivo).
- Fechar cria: (`slab_type.create`, se faltar) → `slab.create`.

## 3. Barra Opções
| Ferramenta | Grupos |
|---|---|
| Pilar | Tipo (lista) e **Editar tipo**; Inserção (9 pontos num quadradinho clicável, só centro para seção circular); Ângulo; Base (deslocamento); Topo (pavimento/altura fixa e deslocamento) |
| Viga | Tipo e **Editar tipo**; Linha de referência (eixo, face esquerda, face direita); Topo (ligado a pavimento + deslocamento, ou cota fixa) |
| Laje | Tipo e **Editar tipo**; Modo (polígono, retângulo); Deslocamento do topo |

## 4. Elemento selecionado

### 4.1 Seleção, alças e movimento (planta)
| Elemento | Clique seleciona por | Alças | Arrasto |
|---|---|---|---|
| Pilar | a seção | ponto de inserção | move o pilar |
| Viga | a faixa da viga (mesmo tracejada) | as duas pontas e o meio | estica a ponta (com quadro de medidas: comprimento) ou move |
| Laje | o interior (quando nenhum outro elemento está sob o cursor) e o contorno | vértices e meio dos lados | move o vértice ou desloca o lado paralelamente |

- **Prioridade do clique**, do mais alto para o mais baixo: porta/janela, pilar, viga,
  parede, laje. Assim, clicar dentro de um cômodo sobre a laje seleciona a laje, e
  clicar sobre a parede seleciona a parede.
- Mover, Copiar, Girar, Espelhar e Excluir funcionam com qualquer mistura de elementos
  (spec 02 §6). Cada elemento gera a sua operação `*.edit` (ou `*.create`, ao copiar)
  na mesma transação.
- Seleção por janela/cruzamento: pilar e viga como as paredes; a laje entra na seleção
  por janela só se estiver **inteira** dentro dela, mesmo no modo cruzamento
  *(decisão do projeto: evita pegar a laje sem querer ao selecionar paredes)*.
  **Ponto de revisão (c).**

### 4.2 Mini-barra
Só as ações comuns (Mover, Copiar, Girar, Espelhar, Excluir). Nenhuma ação própria
nesta etapa.

### 4.3 Painel de propriedades
| Elemento | Grupos e campos |
|---|---|
| Pilar | **Pilar**: Nome, Tipo, Editar tipo…, Seção (leitura: "20 × 40" ou "Ø 30"). **Posição**: X, Y, Ângulo, Inserção. **Altura**: Base (deslocamento), Topo (pavimento/altura fixa), Deslocamento do topo, Altura fixa. **Quantidades** (leitura). **Propriedades comuns**. **Identificação** |
| Viga | **Viga**: Nome, Tipo, Editar tipo…, Seção (leitura). **Geometria**: Comprimento, Ângulo, Linha de referência. **Altura**: Topo (ligado/cota fixa), Deslocamento ou Cota. **Quantidades**. **Propriedades comuns**. **Identificação** |
| Laje | **Laje**: Tipo, Editar tipo…, Espessura (leitura). **Altura**: Deslocamento do topo, Cota do topo e do fundo (leitura, em relação ao pavimento). **Quantidades**: Área, Perímetro, Volume. **Propriedades comuns**. **Identificação** |

Propriedades comuns (spec 05 §6): Código (`Reference`), Situação (`Status`), Estrutural
(`LoadBearing`), Externa (`IsExternal`), Resistência ao fogo (`FireRating`) e, na laje,
Desempenho acústico (`AcousticRating`). Vários do mesmo elemento: "Pilares (n)" etc., com
"vários" onde diferem (spec 02 §9).

## 5. Tipos
Menu **Projeto**: **Tipos de pilar…**, **Tipos de viga…**, **Tipos de laje…**, na mesma
janela de tipos (lista, Novo, Copiar, Excluir e editor; spec 02 §8).

| Elemento | Editor |
|---|---|
| Pilar | Nome; Seção (retangular/circular); b e h ou diâmetro; Material (com "…" para Materiais); Representação na planta; desenho da seção cotado |
| Viga | Nome; b e h; Material; Representação na planta; desenho da seção cotado |
| Laje | Nome; Função (Laje de piso / Laje sobre o solo); Camadas (tabela **de cima para baixo**, como a da parede); Representação na planta |

- Excluir um tipo em uso pede outro tipo para os elementos que o usam (como a parede).
- **Biblioteca** de projeto novo: os tipos de `laje.md` §3.4, `pilar.md` §3.4 e
  `viga.md` §3.4, mais os materiais Contrapiso, Laje pré‑moldada e Reboco (se ainda não
  existirem), com estilos próprios.

## 6. Planta (por plano de corte, spec 06)

### 6.1 Ordem de desenho
De baixo para cima: lajes → paredes (com portas e janelas) → pilares → vigas →
etiquetas e alças.

### 6.2 Cada elemento
- **Laje:** como em `laje.md` §7. No pavimento a que pertence, o contorno em linha fina,
  sem fundo por padrão.
- **Pilar:** como em `pilar.md` §7. Cortado: fundo do material (Concreto: sólido cinza
  da biblioteca) e contorno grosso; as regiões e as linhas das paredes são **recortadas**
  pela seção (`core/clip.py`), nos dois níveis de detalhe.
- **Viga:** como em `viga.md` §7. Acima do plano: as duas faces tracejadas, sempre
  visíveis. Onde a viga encontra um pilar cortado, o tracejado não é desenhado dentro da
  seção do pilar.

## 7. Vista 3D
- Corpos dos três elementos com a cor do material (Concreto da biblioteca para pilar e
  viga; na laje com camadas, uma cor por camada, como a parede com camadas, spec 06 §4).
- Seleção por clique, mini-barra, menu do botão direito, "Mostrar na planta" e as
  ferramentas de transformação: como a parede.
- Sobreposições (laje × parede, viga × pilar) aparecem como estão no modelo: sem
  recortes nesta etapa.
- Sem alças no 3D nesta etapa.

## 8. Pavimentos
- Mudar a cota de um pavimento refaz os pilares e vigas ligados a ele (como as paredes)
  e as lajes dele (que acompanham o pavimento).
- **Excluir pavimento** continua só para pavimento vazio (spec 02 §7); lajes, pilares e
  vigas contam como elementos na mensagem de recusa. Pilares de outros pavimentos com
  topo nele passam a altura fixa, e vigas a cota fixa, com a altura atual, na mesma
  transação (como as paredes).

## 9. Núcleo: o que falta
- `core/structure/` (sem Qt): `profiles.py` (perfis retangular e circular, ponto de
  inserção → `CardinalPoint`, deslocamento do perfil), `columns.py`, `beams.py`,
  `slabs.py`, `types.py` (os três tipos), `commands.py` (`column.*`, `beam.*`, `slab.*` e
  `*_type.*`, `laje.md` §5.2, `pilar.md` §5.2, `viga.md` §5.2), `rebuild.py`.
- `core/plan.py`: papéis novos `slab`, `column`, `column_view`, `column_above`, `beam`,
  `beam_view`, `beam_above`, e o recorte das paredes pelos pilares cortados.
- `core/transform.py`: mover, girar e espelhar para os três.
- Quantidades e Psets dos três; leitura de IFC de outra origem (corpo preservado).
- Aceites LA01–LA12, PI01–PI14, VI01–VI13 como testes do núcleo.
- Atualizar `spec/01-modelo-de-dados.md` com as operações novas.

## 10. Ícones novos
Pilar (seção quadrada com hachura), Viga (duas linhas paralelas tracejadas sobre dois
apoios), Laje (placa em perspectiva), no estilo da spec 03 §3; o quadradinho de 9 pontos
da inserção do pilar.

## 11. Critérios de aceite (testes)
Pavimentos Térreo (0,00) e Superior (2,80), plano de corte 1,50.

- [x] **UI96** Ferramenta Pilar com "Pilar 20×40", clique em (2, 3): pilar criado com a
      transação de §2.1; barra de espaço antes do clique cria com ângulo 90°.
- [x] **UI97** Pilar com atração no canto de uma junção em L de paredes; inserção canto
      inferior esquerdo na barra Opções: o canto do pilar fica no ponto.
- [x] **UI98** Ferramenta Viga de (0, 0) a (5, 0) e depois a (5, 4): duas vigas em
      cadeia, cada uma com o seu `beam.create`; Tab `4` Enter no segundo trecho dá
      comprimento 4.
- [x] **UI99** Ferramenta Laje, Retângulo de (0, 0) a (5, 4): laje de 20 m²; Polígono em
      L com 6 cliques e fechando no primeiro ponto: laje com 6 vértices; contorno que se
      cruza não fecha.
- [x] **UI100** Planta do Térreo: pilar cortado preenchido e por cima da parede (a parede
      recortada); viga tracejada também com "Elementos acima do plano de corte"
      desligado; laje do Superior não aparece. Planta do Superior: a laje dele em
      contorno fino.
- [x] **UI101** Clique dentro do cômodo seleciona a laje; sobre a parede, a parede; sobre
      o pilar, o pilar. Seleção por janela que pega metade da laje não a inclui.
- [x] **UI102** Alças: arrastar a ponta da viga com `6` digitado deixa 6 m; arrastar um
      vértice da laje muda a área; arrastar o meio de um lado desloca o lado.
- [x] **UI103** Painel: mudar o deslocamento do topo da laje para −0,05 move a laje;
      mudar o topo do pilar para altura fixa 3,00 muda a altura; mudar o ângulo da viga
      gira em torno do ponto inicial.
- [x] **UI104** Mover, Girar e Espelhar uma seleção com parede, pilar, viga e laje: uma
      transação, um `*.edit` por elemento; desfazer volta tudo.
- [x] **UI105** Tipos: mudar "Pilar 20×40" para 25×50 refaz todos os pilares do tipo
      (mesmo `IfcRectangleProfileDef` com 0,25 × 0,50); tabela de camadas da laje de cima
      para baixo.
- [x] **UI106** 3D: os três aparecem com a cor do material; clique seleciona; laje com
      camadas mostra uma cor por camada.
- [x] **UI107** Mudar a cota do Superior para 3,00 refaz pilares e vigas ligados e a laje
      do Superior.
- [x] **UI108** Projeto novo tem os tipos das três bibliotecas e os materiais novos.
- [x] **UI109** Os diários de UI96–UI107 reaplicados num projeto novo reproduzem o IFC.

## 12. Fontes públicas
- **LAJE**, **PILAR**, **VIGA**: `spec/elementos/laje.md`, `pilar.md`, `viga.md` (em
  revisão, com as fontes IFC de cada uma).
- **UI01–UI09**: specs de interface aprovadas, nas seções citadas.
- **CG**: conhecimento geral de desenho arquitetônico brasileiro (pilar preenchido por
  cima da alvenaria, vigas tracejadas, contorno de laje) e de aplicativos de CAD
  (polígono fechado no primeiro ponto, giro de 90° com a barra de espaço, ponto de
  inserção num quadradinho de 9 pontos).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 13. Pontos de revisão
(a) **Pavimento de cada elemento**: a laje é do pavimento de que é o piso (topo na cota
    dele, espessura para baixo); a viga e o pilar são do pavimento em que são desenhados,
    com o topo no pavimento de cima. Num sobrado: paredes, pilares e vigas do Térreo
    sobem até 2,80, e a laje de 2,80 é desenhada no Superior.
(b) **Sobreposições aceitas** no 3D e nos volumes nesta etapa; só a planta recorta a
    parede pelo pilar.
(c) Laje só entra na seleção por janela se estiver inteira dentro dela (§4.1).
(d) Vigas sempre visíveis, tracejadas, na planta do pavimento delas (§6.2).
(e) Nomes automáticos P1, P2… e V1, V2… (sem etiqueta na planta por enquanto).
(f) Ordem dos ícones Pilar, Viga, Laje (§2) e barra de espaço para girar o pilar (§2.1).
(g) Bibliotecas e seções padrão (pilar 20×40, viga 14×40, laje maciça 10 cm).
