---
documento: Interface — janela (ferramenta, opções, tipos, planta, 3D, painel, alças) e ponto de referência nas ferramentas de criação
requisito: RF-ELE-06, RF-TIP-06, RF-UI-01, RF-UI-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15)
---

# Janela na interface

## 1. Propósito
Pacote 3 (etapa 3c): pôr na interface a janela da spec aprovada `spec/elementos/janela.md`,
já no padrão novo: ferramenta com ícone, barra **Opções**, **quadro de medidas** (Tab),
**mini-barra** da seleção, painel em blocos, alças na planta e no 3D, planta por plano de
corte (spec 06) e cor por material no 3D.

Tudo o que a janela faz igual à porta é dito aqui só como "como a porta", com a referência.
O núcleo da janela (IFC, operações, regras) é o de `janela.md`; esta spec acrescenta só
decisões de interface e o que falta no núcleo para elas.

**Nome na interface:** o elemento se chama **Janela**. Onde "janela" já era usado com outro
sentido (seleção por janela, janela principal), os textos daquelas funções não mudam; a
ferramenta, os menus e as mensagens do elemento sempre dizem "janela" junto do contexto
("Tipos de janela…", "Excluir janela").

## 2. Ferramenta Janela (`janela.md` §4)
Ícone próprio na barra **Ferramentas**, depois de Porta.

1. Com o cursor sobre uma parede reta, a pré-visualização mostra a janela **centrada no
   cursor** (com *snap* ao meio da parede, Alt desliga), como a porta (spec 01 §5.5).
2. O lado da parede em que está o cursor é o **abre para** (ou o **lado interno**, nos
   tipos sem giro; `janela.md` §2.4).
3. Junto ao cursor: as distâncias das bordas do vão às extremidades da parede (como a
   porta) e, abaixo, a linha **"peitoril 1,10 · verga 2,10"** (`janela.md` §4).
4. Clique cria a janela: `opening.create` → (`window_type.create` da variante, se faltar)
   → `window.create` → `filling.attach`. Posição que não cabe (fora da parede, sobre outro
   vão, verga acima do topo da parede, topo inclinado) aparece em vermelho e é recusada
   com o motivo.
5. Parede em arco: sem pré-visualização; a dica diz que janela em parede em arco ainda
   não é suportada (`janela.md` §1).
6. A ferramenta continua ativa para a próxima janela; Esc volta a Selecionar.
7. Na vista 3D, a ferramenta funciona como a porta (spec 07): o ponto vem da parede
   atingida pelo raio; a pré-visualização já aparece na altura do peitoril.

### 2.1 Ponto de referência (todas as ferramentas de criação)
Pedido do revisor em 2026‑10‑15: vale para **qualquer item a ser adicionado** — parede,
parede em arco, retângulo, porta, janela e as ferramentas de criação que vierem (laje,
pilar…). Fica nesta spec porque entra no pacote 3, mas é regra geral da interface.

**Pegar e soltar (igual para todas):**
- Com uma ferramenta de criação ativa, o usuário para o cursor sobre um **vértice** (cerca
  de 0,4 s, para não pegar todos os vértices por onde o cursor passa). O vértice ganha uma
  marca e passa a ser o **ponto de referência**. Vértices aceitos: os pontos de *snap* de
  extremidade e canto que já existem (pontas e cantos das faces das paredes, inclusive os
  cantos das junções, centros de arco) e os cantos dos vãos (portas, janelas, aberturas).
- Pegar outro vértice troca a referência. Ela é solta ao confirmar o ponto que ela ajudou
  a marcar, ao trocar de ferramenta ou com Esc (o primeiro Esc solta a referência; o
  seguinte faz o que fazia antes).
- Planta e 3D usam os mesmos vértices (no 3D, na cota da base dos elementos do pavimento).
- Mover, Copiar, Girar e Espelhar ficam fora nesta etapa. **Ponto de revisão (g).**

#### 2.1.1 Item com ponto livre (parede, arco, retângulo, futuros)
1. Com a referência pegada, quando o cursor passa perto (8 px) de uma das **direções
   ortogonais** que saem dela (0°, 90°, 180°, 270° no pavimento), aparece a linha de
   referência tracejada, do ponto até o cursor, e o cursor se prende a ela.
2. O **balão** (quadro de medidas, spec 07 §2) mostra a **distância à referência**. Tab
   põe o foco nele; o número digitado marca o ponto na linha, a essa distância. Enter ou
   clique confirma o ponto.
3. Fora das linhas, o balão volta a ser o da ferramenta (comprimento/ângulo da parede,
   largura/altura do retângulo, spec 07 §2.1).
4. Vale para qualquer ponto da ferramenta: o 1º ponto da parede, os seguintes da cadeia,
   os pontos do arco e os cantos do retângulo. Com a linha de referência ativa, Shift
   (ortogonal em relação ao ponto anterior) é ignorado; o ponto mais forte é o da
   referência.
5. O cruzamento das linhas de referência com a linha ortogonal do ponto anterior (ex.:
   continuar a parede até alinhar com um canto) também prende o cursor. *(CG)*

#### 2.1.2 Item numa parede (porta, janela, futuras aberturas)
1. Pegar a referência como acima.
2. **Linha de referência:** ao voltar para a parede, aparece uma linha tracejada fina que
   sai do ponto de referência na direção da parede, até a **borda do vão mais próxima do
   ponto**. A distância é medida **ao longo da parede** (projeção do ponto na direção da
   parede), e só conta essa direção.
3. **Balão:** o quadro de medidas (spec 07 §2) aparece no meio da linha de referência com
   a distância atual, que acompanha o cursor.
4. **Tab** põe o foco no balão para digitar a distância; com ela fixada, a esquadria fica
   parada ali (o cursor ainda escolhe a parede e o lado). Na janela, Tab de novo vai para o
   **Peitoril**. Enter ou clique cria.
5. **Sem referência pegada:** a referência é a ponta da parede (canto da face) mais
   próxima do cursor.

Aqui não há linhas ortogonais: a parede já dá a direção. Campos do balão, na ordem do Tab:

| Ferramenta | Campos |
|---|---|
| Porta | Distância |
| Janela | Distância, Peitoril |

- Peitoril fixado vale para as próximas janelas até ser mudado (vira o valor da barra
  Opções). A distância é solta depois de criar, como nas outras ferramentas (spec 07 §2.2,
  item 7).

### 2.2 Mão e dobradiças
Como o Tab passa a ser do balão (§2.1), **na porta ele deixa de alternar as dobradiças**
(muda spec 01 §5.5 e §6, spec 03 §4.2 e spec 07 §2.2). A mão da janela e as dobradiças da
porta ficam nos botões **Esquerda / Direita** da barra Opções; depois de criada, no painel e
na mini-barra (Inverter mão / Inverter dobradiças). **Ponto de revisão (a).**

## 3. Barra Opções: Janela (spec 03 §4)
| Grupo | Controles |
|---|---|
| Tipo | Lista dos tipos de janela (sem as variantes de mão) e **Editar tipo** |
| Vão | Largura, Altura, Peitoril — vazios = padrão do tipo, mostrado em cinza |
| Mão | Esquerda, Direita (só nos tipos com mão) |
| Posição no marco | Alinhamento (lista) e deslocamento |

## 4. Janela selecionada

### 4.1 Seleção e movimento
- Clique seleciona a janela; ela tem prioridade sobre a parede, como a porta. Seleção por
  janela/cruzamento, Ctrl e Shift: como os outros elementos (spec 02 §3).
- **Arrastar a janela pelo meio** (planta): desliza na parede ou passa para outra parede
  reta, um único `opening.edit`, como a porta (spec 01 §4, PO10/PO11).
- Mover, Copiar e Girar com janelas: como a porta (spec 02 §6). Espelhar: como a porta
  (spec 05 §2): a janela vai para a posição espelhada e troca a mão (variante); janela
  sozinha na seleção é recusada ("espelhe a parede que contém a janela").
- Excluir: a janela sai com a sua abertura (`janela.md` §6.3). Parede com portas e janelas
  pede confirmação dizendo quantas de cada saem junto ("1 porta e 2 janelas").

### 4.2 Alças
| Vista | Alças | Arrasto |
|---|---|---|
| Planta | Bordas esquerda e direita do vão, no eixo da parede | Largura, mantendo a outra borda (como a porta, spec 05 §4) |
| 3D | Bordas esquerda e direita, **base** (peitoril) e **topo** (verga), no meio de cada lado do vão, na face da parede do lado "abre para" | Largura (como na planta); peitoril (mantém a **altura**: a janela sobe ou desce); verga (muda a altura, mantém o peitoril) |

- As alças 3D andam no plano da parede e usam o quadro de medidas com o valor da alça
  (largura, peitoril ou verga), como as alças da parede (spec 08 §3).
- Posição que não cabe fica em vermelho e é recusada ao soltar.
- A **porta ganha as mesmas alças no 3D** (bordas e topo; a base da porta não tem alça),
  porque o código é o mesmo. **Ponto de revisão (b).**

### 4.3 Mini-barra
Com janelas selecionadas (sozinhas ou com outros elementos), além das ações comuns
(Mover, Copiar, Girar, Espelhar, Excluir), quando se aplicam:

| Ação | Ícone | Quando | O que faz |
|---|---|---|---|
| Inverter sentido | o da porta | sempre | Troca o "abre para" / lado interno (`window.edit`, `opens_to`) |
| Inverter mão | o das dobradiças | tipo com mão | Troca a variante de mão (`janela.md` §2.4) |

Com portas e janelas juntas, as duas ações valem para cada uma.

### 4.4 Painel de propriedades
Janela selecionada sozinha (blocos no arranjo deitado, spec 04):

| Grupo | Campos |
|---|---|
| Janela | Tipo (lista), Editar tipo…, Código (leitura, do tipo) |
| Vão | Largura, Altura, **Peitoril**, **Verga** (editar a verga muda a altura e mantém o peitoril, `janela.md` §3.1), Distância ao início. Se a base da parede tem deslocamento: **Peitoril do piso** (leitura, em relação ao piso do pavimento) |
| Abertura | "Abre para" ou "Lado interno" (o nome muda conforme o tipo, §2.4 de `janela.md`), Mão (só com mão), botões Inverter sentido / Inverter mão |
| Posição no marco | Alinhamento, Deslocamento; aviso se o marco é mais profundo que a parede (`janela.md` §6.1) |
| Quantidades (leitura) | Largura, Altura, Área, Perímetro (`Qto_WindowBaseQuantities`) |
| Propriedades comuns | §4.5 |
| Identificação (leitura) | `GlobalId`, origem; janela de outra origem com o mesmo aviso da porta (porta §6.6) |

Várias janelas: "Janelas (n)", com os campos comuns e "vários" onde diferem, como as
portas (spec 02 §9). Seleção com janelas e outros elementos: o painel de vários elementos
de hoje (contagem por tipo).

### 4.5 Propriedades comuns (`janela.md` §3.3; spec 05 §6)
| Campo | Propriedade | Edição |
|---|---|---|
| Código | `Reference` | leitura (vem do tipo) |
| Situação | `Status` | lista |
| Externa | `IsExternal` | caixa (padrão: sim) |
| Peitoril externo (pingadeira) | `HasSillExternal` | caixa |
| Peitoril interno | `HasSillInternal` | caixa |
| Resistência ao fogo | `FireRating` | texto |
| Desempenho acústico | `AcousticRating` | texto |
| Transmitância térmica | `ThermalTransmittance` | número, W/(m²·K) |

Os demais itens de `Pset_WindowCommon` ficam sem campo nesta etapa (só preservados se
vierem de um arquivo).

## 5. Tipos de janela
Menu **Projeto > Tipos de janela…**: a mesma janela de tipos da parede e da porta (spec 02
§8), com lista, Novo, Copiar, Excluir e o editor abaixo. As variantes de mão não aparecem
na lista; acompanham o tipo de origem (como a porta).

### 5.1 Editor
| Bloco | Campos |
|---|---|
| Geral | Nome, Código (`Reference`, ex.: `J1`) |
| Divisão | Lista com as 5 divisões de `janela.md` §2.2 (1 caixilho; 2 lado a lado; 2 um sobre o outro; 3 lado a lado; 3 um sobre o outro) |
| Caixilhos | Uma linha por posição (ex.: Esquerda, Direita), cada uma com a **Operação** (lista de `janela.md` §2.3; as com mão aparecem como "De abrir — dobradiças à esquerda" e "… à direita") |
| Dimensões padrão | Largura, Altura, Peitoril |
| Marco | Profundidade, Espessura |
| Montantes / Travessas | Espessura e posição de cada um, em **%** da largura (ou da altura, a partir da base). Só os que a divisão tem |
| Perfil do caixilho | Profundidade, Largura (vale para todos os caixilhos do tipo) |
| Materiais | Marco, Caixilho, Vidro, cada um com o botão "…" que abre Projeto > Materiais… nele (como a tabela de camadas, spec 06 §4.2) |

- **Desenho do tipo** ao lado dos campos: a janela vista de dentro, nas dimensões padrão,
  com marco, montantes, travessas, caixilhos e o símbolo de abertura de cada caixilho
  (§6.2). Atualiza a cada campo alterado, antes de Aplicar.
- Trocar a divisão refaz a lista de caixilhos: posições novas ganham a operação do
  primeiro caixilho; posições que continuam mantêm a sua.
- Aplicar grava `window_type.edit` (e o da variante, se houver), e as janelas do tipo são
  refeitas.

### 5.2 Biblioteca inicial (`janela.md` §3.4)
Projeto novo ganha, junto com as paredes e portas (spec 01 §3):

| Nome | Código | Divisão / operação | Largura × altura | Peitoril |
|---|---|---|---|---|
| J1 – correr 2 folhas 120 | J1 | 2 lado a lado, correr / correr | 1,20 × 1,00 | 1,10 |
| J2 – correr 2 folhas 150 | J2 | 2 lado a lado, correr / correr | 1,50 × 1,20 | 1,10 |
| J3 – maxim-ar 60 | J3 | 1 caixilho, maxim-ar | 0,60 × 0,60 | 1,50 |
| J4 – basculante 60 | J4 | 1 caixilho, basculante | 0,60 × 0,40 | 1,70 |
| J5 – de abrir 2 folhas | J5 | 2 lado a lado, de abrir esq. / dir. | 1,00 × 1,20 | 1,10 |
| J6 – fixa | J6 | 1 caixilho, fixo | 1,00 × 1,00 | 1,10 |

Materiais: "Alumínio" (marco e caixilho) e "Vidro", com estilos padrão (spec 06 §4).

## 6. Planta

### 6.1 Em relação ao plano de corte (spec 06 §3.3)
| Situação | Desenho |
|---|---|
| Plano atravessa o vão | Parede interrompida; faces da parede no peitoril em vista (já existe); símbolo da janela (§6.2) |
| Janela toda acima do plano (ex.: basculante alto) | Contorno do marco em tracejado fino, com a opção Exibir > Elementos acima do plano de corte |
| Janela toda abaixo do plano | Nada (a parede está cortada acima dela; como os vãos em spec 06 §3.3) |

`janela.md` §7 fala em "linhas de projeção" para a janela abaixo do plano; com a parede
cortada acima, essas linhas ficariam escondidas dentro da parede, por isso nada é desenhado.

### 6.2 Símbolo (`janela.md` §7)
No sistema da janela (x ao longo do vão, y na profundidade):

| Peça / operação | Desenho |
|---|---|
| Marco | Duas peças cortadas, preenchidas, nas bordas do vão (como o marco da porta) |
| Montante | Peça cortada, preenchida, na posição do tipo |
| Fixo, maxim-ar, tombar, basculante, pivotante, guilhotina | Caixilho fechado: duas linhas finas (as faces do perfil) e a linha do vidro no meio |
| Correr | Caixilhos em **trilhos paralelos**, deslocados na profundidade e sobrepostos na largura do montante; seta curta no sentido de abrir de cada caixilho móvel |
| De abrir, oscilobatente | Caixilho aberto a 90° e arco de giro em linha fina, para o lado "abre para", como a porta |

- Divisão "um sobre o outro" (travessa): a planta mostra o caixilho cortado pelo plano; se
  o plano passa na travessa, o de baixo.
- Igual nos dois detalhes de planta (Simplificado / Por camadas), como a porta (spec 06
  §3.3).
- Janela de outra origem: retângulo do vão na espessura do marco, como a porta.

### 6.3 Etiqueta (`janela.md` §7; spec 05 §5)
- Código (`J1`) e, na segunda linha opcional, **largura × altura / peitoril**
  (`1,20 × 1,00 / 1,10`).
- Posição: no meio do vão, do lado oposto ao "abre para", a 0,30 m da face — no tipo sem
  giro, isso põe a etiqueta do lado externo. **Ponto de revisão (c).**
- O menu Exibir passa a ter **Etiquetas de esquadrias** (porta e janela juntas) no lugar de
  "Etiquetas de porta"; **Medidas na etiqueta** vale para as duas. A preferência já gravada
  da porta continua valendo para o item novo.

## 7. Vista 3D
- Corpo do núcleo (`janela.md` §6.2): marco, montantes, travessas, caixilhos e vidro.
- **Cor por peça:** marco e montantes/travessas com o estilo do material do marco,
  caixilhos com o do caixilho, vidro com o do vidro. O **vidro é translúcido** (estilo
  padrão de "Vidro" com transparência 0,6), desenhado depois das peças opacas.
- No IFC, cada peça do `Body` leva um `IfcStyledItem` com o `IfcSurfaceStyle` do seu
  material (o mesmo estilo de spec 06 §4), para que outros programas mostrem as cores e o
  vidro. *(decisão do projeto; a porta passa a fazer o mesmo com marco e folha.)*
  **Ponto de revisão (d).**
- Seleção por clique, mini-barra, menu do botão direito e "Mostrar na planta": como a
  porta.

## 8. Núcleo: o que falta (`janela.md` §2–§8)
- `core/fillings/window_types.py`, `windows.py` e `window.*`/`window_type.*` em
  `commands.py`, aproveitando da porta tudo o que é comum (abertura, posição no marco,
  variante de mão, conversão de outra origem). O que hoje é "da porta" e serve às duas
  passa a ser de "esquadria" no código, sem mudar operações nem o IFC da porta.
- `geometry.window_boxes` (corpo, `janela.md` §6.2), `plan.window_symbol` (§6.2) e
  `plan.window_elevation` (desenho do tipo, §5.1), sem Qt e com testes.
- Verificações de abertura comuns à porta e à janela: verga acima do topo (inclusive topo
  inclinado), parede tombada.
- Aceites `JA01`–`JA14` de `janela.md` §9 como testes do núcleo.
- Atualizar `spec/01-modelo-de-dados.md` com `window_type.*` e `window.*`.

## 9. Ícones novos
Só o da ferramenta **Janela** (estilo da spec 03 §3). Inverter sentido e Inverter mão
reaproveitam os ícones da porta.

## 10. Critérios de aceite (testes)
Parede reta de 5 m, 14 cm, 2,80 m, como em `janela.md` §9.

- [x] **UI82** Ferramenta Janela com J1, cursor do lado esquerdo a 2,10 m do início: cria a
      janela com o vão em 1,50–2,70, peitoril 1,10, `opens_to = left`; a transação tem as
      operações de §2, item 4; desfazer volta tudo.
- [x] **UI83** Sem referência pegada, cursor perto do fim da parede, Tab `0,30` Tab `1,20`
      Enter: vão a 0,30 m do fim (borda direita em 4,70) e peitoril 1,20; a próxima janela
      já sugere peitoril 1,20.
- [x] **UI83a** Parar o cursor 0,4 s sobre a borda de uma porta existente (vão em
      1,00–1,86) pega a referência; voltar à parede à direita dela, Tab `0,50` Enter: a
      janela começa em 2,36; a linha de referência e o balão aparecem; Esc solta a
      referência. Passar rápido pelo vértice não pega.
- [x] **UI83b** Porta: o mesmo com Tab `0,15` a partir do canto interno de uma junção em L;
      Tab não troca mais as dobradiças; os botões da barra Opções trocam.
- [x] **UI83c** Parede: pegar a ponta (5, 0) de uma parede existente, levar o cursor para a
      direita perto do eixo x: linha de referência e balão "distância"; Tab `1,20` Enter
      põe o 1º ponto da parede nova em (6,20, 0). Longe das linhas, o balão volta a ser
      comprimento/ângulo.
- [x] **UI83d** Retângulo: com a referência num canto (0, 0), o 1º canto por Tab `0,50` na
      vertical vai a (0, 0,50); continuar a parede até o cruzamento com a linha vertical de
      outro canto prende o cursor no cruzamento.
- [x] **UI84** Verga acima do topo (peitoril 2,00 com altura 1,00 numa parede de 2,80) e
      janela sobre a porta: vermelho e recusa com motivo.
- [x] **UI85** Tipo de abrir 1 folha, mão Direita na barra Opções: cria a variante uma vez
      só; segunda janela com a mesma mão reaproveita a variante.
- [x] **UI86** Planta, plano 1,50: J1 com peitoril 1,10 mostra marco preenchido, dois
      caixilhos em trilhos paralelos e as faces da parede no peitoril; J4 (peitoril 1,70)
      aparece tracejada, e some com "Elementos acima do plano de corte" desligado.
- [x] **UI87** Etiqueta "J1" do lado oposto ao "abre para"; "Medidas na etiqueta" acrescenta
      "1,20 × 1,00 / 1,10"; desligar "Etiquetas de esquadrias" tira as de porta e janela.
- [x] **UI88** Painel: verga 2,30 → altura 1,20, peitoril 1,10 mantido (um
      `opening.edit`); com base da parede 0,20, "Peitoril do piso" mostra 1,30.
- [x] **UI89** Alças: na planta, a borda direita muda a largura com a esquerda fixa; no 3D,
      a alça da base com `1,30` digitado leva o peitoril a 1,30 e mantém a altura; a do
      topo com `2,30` muda só a altura.
- [x] **UI90** Mini-barra: Inverter sentido troca `opens_to`; Inverter mão troca para a
      variante; arrastar a janela para outra parede gera um único `opening.edit`.
- [x] **UI91** Tipos de janela: trocar J1 para "3 lado a lado" cria 3 caixilhos
      (`LEFT`/`MIDDLE`/`RIGHT`) e montantes em 33,3 % e 66,7 %
      (`TRIPLE_PANEL_VERTICAL`); as janelas do tipo são refeitas; o desenho do tipo mostra
      3 caixilhos.
- [x] **UI92** 3D: a janela tem peças com as cores de marco, caixilho e vidro; o vidro é
      translúcido; cada item do `Body` tem `IfcStyledItem`; clicar na janela a seleciona.
- [x] **UI93** Espelhar a parede com janela de abrir 1 folha troca a mão; excluir a parede
      com uma porta e duas janelas pede confirmação com "1 porta e 2 janelas".
- [x] **UI94** Projeto novo tem os tipos J1–J6 de §5.2 e os materiais Alumínio e Vidro.
- [x] **UI95** Os diários de UI82–UI93 reaplicados num projeto novo reproduzem o IFC.

## 11. Fontes públicas
- **JANELA**, **PORTA** — `spec/elementos/janela.md` e `porta.md` (aprovadas).
- **UI01–UI08** — specs de interface aprovadas, nas seções citadas.
- **IFC** — buildingSMART IFC 4.3: `IfcWindow`, `IfcWindowType`,
  `IfcWindowLiningProperties`, `IfcWindowPanelProperties`, `Pset_WindowCommon`,
  `Qto_WindowBaseQuantities`, `IfcStyledItem`, `IfcSurfaceStyle` (mesmas fontes de
  `janela.md` §10 e spec 06).
- **CG** — conhecimento geral de desenho arquitetônico brasileiro (símbolos de janela em
  planta, etiqueta com peitoril) e de aplicativos de CAD (alças nas bordas, desenho do tipo
  ao editar).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 12. Pontos de revisão
(a) Tab da porta deixa de trocar as dobradiças; dobradiças e mão só pelos botões da barra
    Opções (§2.2).
(b) Alças no 3D também para a porta (§4.2).
(c) Etiqueta do lado oposto ao "abre para" (§6.3): na maxim-ar, que abre para fora, a
    etiqueta fica do lado de dentro.
(d) `IfcStyledItem` por peça no corpo da janela e da porta, com vidro translúcido (§7).
(e) "Etiquetas de porta" vira "Etiquetas de esquadrias", um item só (§6.3).
(f) Ponto de referência (§2.1), pedido do revisor, para todas as ferramentas de criação:
    parada de 0,4 s para pegar o vértice; vértices aceitos; linhas só nas 4 direções
    ortogonais do pavimento (sem 45°) para o ponto livre; na parede, distância até a borda
    do vão mais próxima, ao longo da parede; referência solta ao confirmar o ponto.
(g) Mover, Copiar, Girar e Espelhar sem ponto de referência por enquanto (§2.1).
