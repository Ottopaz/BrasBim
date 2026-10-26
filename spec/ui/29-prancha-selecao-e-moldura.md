---
documento: Seleção na prancha e na folha mestra; limite e moldura dos desenhos na prancha
requisito: spec/ui 15 §5 (aba da prancha), spec/ui 26 §4 (folha mestra), spec/ui 28 (seleção)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-26
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Seleção na prancha e moldura dos desenhos

## 1. Propósito
Pedidos do revisor (2026‑10‑26), ao testar as specs 25–28:
1. O cursor e as formas de seleção têm de funcionar na **montagem das pranchas** e na
   **folha mestra** do mesmo jeito que na planta (spec/ui 28).
2. Cada desenho posto na prancha mostra um **retângulo tracejado com o limite** do
   desenho; o usuário pode **mudar esse limite** e pôr uma **moldura** impressa, de linha
   contínua, tracejada ou traço‑ponto, com uma **pena** da tabela de penas, ou deixá‑la
   **sem moldura**.

## 2. Seleção na prancha e na folha mestra
Mesmos gestos da planta (spec/ui 28 §2), sobre os desenhos da prancha (planta, corte,
vista salva) e sobre as linhas e textos da folha mestra:

| Gesto | O que faz |
|---|---|
| Clique num item | **soma** à seleção |
| Shift + clique | **tira** da seleção |
| Clique no vazio, soltar, mover, clicar | **janela** (2 cliques) |
| Segurar e arrastar no vazio | **laço** |
| Para a **direita** / para a **esquerda** | só os **inteiros** (contínuo, azul) / também os que **tocam** (tracejado, verde) |
| Shift ao fechar | tira o que pegou |
| Esc | cancela a janela; sem nada em andamento, **limpa** |
| Passar o cursor | **realce** do item sob o cursor |
| Arrastar um item | move a seleção inteira (o item não selecionado entra nela) |
| Delete | prancha: **tira da prancha** os desenhos selecionados; folha mestra: apaga |

- O cursor é o mesmo da planta (cruz com o quadradinho de captura).
- **Editar > Modo de seleção** vale aqui também: no modo "Trocar a seleção a cada
  clique", clique troca, Ctrl+clique soma e arrastar no vazio faz a janela.
- Mover vários desenhos (ou vários itens da folha mestra) é **uma** transação.

## 3. Limite do desenho na prancha
- Todo desenho na prancha tem um **limite**: o retângulo que ele ocupa no papel. Na tela
  ele aparece **tracejado, em cinza** (não sai no PDF). **Exibir > Limites dos desenhos
  na prancha** liga e desliga esse traço na tela (preferência do usuário).
- Padrão: o limite **acompanha o desenho** (cresce quando o modelo cresce).
- Com **um** desenho selecionado aparecem **alças** nos cantos e no meio dos lados do
  limite. Arrastar uma alça **recorta** o desenho: o que fica fora do limite não é
  desenhado (tela e PDF); o lado oposto fica parado no papel. O limite recortado é
  guardado nas coordenadas do modelo, então o recorte continua no mesmo lugar do
  desenho quando o modelo muda.
- Botão direito no desenho: **Ajustar o limite ao desenho** volta ao padrão.
- Vista 3D na prancha: não tem recorte (o tamanho dela é a largura no papel, spec/ui 25
  §5), só moldura.

## 4. Moldura
- Botão direito no desenho (ou em vários selecionados): **Moldura…** abre um quadro curto:
  **Mostrar moldura** (desligado por padrão), **Tipo de linha** (contínua, tracejada,
  traço‑ponto, os mesmos das linhas 2D) e **Pena** (as penas da tabela de penas em uso,
  com número, espessura e cor; spec/ui 27).
- A moldura é desenhada sobre o limite, na tela e no PDF, com a cor e a espessura da
  pena ("Imprimir em preto" vale). Sem moldura, nada sai no papel.
- Dados: no item da prancha (Pset `BrasBim_Prancha`, JSON `Parametros`), `limit`
  ([x0, y0, x1, y1] em m do desenho; ausente = acompanha o desenho) e `frame`
  ({`show`, `dash`, `pen`}).

## 5. Critérios de aceite (testes)
- [x] **PS01** Núcleo: mover vários desenhos e tirar vários da prancha numa transação;
      `limit` e `frame` gravados no IFC, validados e desfeitos.
- [x] **PS02** Núcleo: com `limit`, o tamanho e o centro do desenho seguem o limite; o
      recorte pela alça mantém o lado oposto parado no papel.
- [x] **PS03** Prancha: clique soma, Shift tira, Esc limpa; janela por dois cliques
      (direita = inteiros, esquerda = os que tocam); laço; realce; arrastar move a
      seleção; Delete tira da prancha.
- [x] **PS04** Folha mestra: os mesmos gestos sobre linhas e textos; arrastar move
      todos os selecionados.
- [x] **PS05** Moldura no PDF com a pena e o tipo de linha; sem moldura, nada.

## 6. Fontes
- Pedido do revisor (2026‑10‑26).
- Seleção: spec/ui 28 e as fontes citadas lá (pesquisa do projeto, `autocad.md` §1).
- Limite e moldura — como os três resolvem (acesso em 2026‑10‑26, por resultado de busca:
  **conferir** na página inteira antes de citar como fato; sem copiar nomes de UI):
  - Archicad: o desenho na folha tem um contorno que só aparece na tela e se liga e
    desliga nas opções de exibição, separado de uma borda imprimível com pena e tipo de
    linha; o contorno pode acompanhar o desenho ou ser redimensionado à mão, recortando
    ([Graphisoft Community, bordas dos desenhos no layout](https://community.graphisoft.com/t5/Documentation/Border-lines-around-drawings-on-layout/m-p/212041/highlight/true);
    [moldura automática × manual](https://community.graphisoft.com/t5/Documentation/VIEW-EDGE-quot-AUTO-ADJUST-quot-OR-quot-MANUAL-quot-EXPLAIN/td-p/142401)).
    Queixa registrada lá: o usuário não controla a aparência do contorno de tela — aqui a
    moldura impressa tem pena e tipo de linha próprios.
  - Revit: a região de recorte da vista se mostra ou se oculta e se ajusta por alças
    ([Autodesk Help, Showing or Hiding Crop Regions](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-47430A55-A8F0-4894-A636-14E0A29182D3.htm)).
  - AutoCAD: a borda da janela de papel não tem opção própria de ocultar; a prática é
    pô‑la numa camada que não imprime
    ([Autodesk Forums, ocultar a borda da viewport](https://forums.autodesk.com/t5/autocad-forum/viewport-border-showing-on-print/m-p/7979089);
    [Arkance, camada congelada e recorte](https://ukcommunity.arkance.world/hc/en-us/articles/21550812943762-AutoCAD-Tip-Freezing-Viewport-Layer-removes-clipping-boundary-from-viewport)).
    Aqui o limite de tela e a moldura impressa são coisas separadas desde o início.
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Nomes, cursor e cores
  próprios.

## 7. Pontos de revisão
(a) arrastar um desenho não selecionado já o move (na planta, o arrasto de um elemento
    não selecionado não faz nada no modo de somar cliques);
(b) recorte só retangular (polígono fica para depois);
(c) moldura por desenho, não por prancha; sem título da vista (fica para o item
    "vistas na prancha com grade", roteiro item 2).
