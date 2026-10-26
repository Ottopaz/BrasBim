---
documento: Seleção pelo cursor, como nos programas de CAD
requisito: RF-NUC-09 (complemento); spec/ui 02 §3.1 (janela) revista
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-26
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Seleção pelo cursor

## 1. Propósito
O revisor pediu que o cursor selecione como no AutoCAD, conforme o movimento do mouse.
Quem vem do CAD seleciona somando cliques e usando a direção da janela para escolher
entre "só o que está inteiro" e "o que toca". Respostas do revisor (2026‑10‑26): clique
**acumula**; **laço** ao arrastar; **destaque** ao passar o cursor; **janela também no
3D**.

## 2. Na planta (ferramenta Selecionar)
| Gesto | O que faz |
|---|---|
| Clique num elemento | **soma** à seleção |
| Shift + clique num elemento selecionado | **tira** da seleção |
| Clique no vazio, soltar, mover, clicar | **janela retangular** (2 cliques) |
| Segurar e arrastar no vazio | **laço**: contorno livre seguindo o cursor |
| Janela ou laço para a **direita** | só os elementos **inteiros dentro** (traço contínuo, azul) |
| Janela ou laço para a **esquerda** | os que estão dentro **e os que tocam** (traço tracejado, verde) |
| Shift ao fechar a janela ou o laço | **tira** da seleção o que pegou |
| Esc | cancela a janela em andamento; sem nada em andamento, **limpa** a seleção |
| Passar o cursor | o elemento sob o cursor fica **realçado** antes do clique |

- No laço, a direção é a do primeiro movimento (para a direita ou para a esquerda).
- Arrastar um elemento já selecionado continua movendo a seleção; as alças continuam
  como antes.
- Laje, ambiente e cobertura só entram inteiros, mesmo no cruzamento (spec/ui 10 §4.1).
- Elementos de camada bloqueada não são escolhidos nem realçados.
- O **cursor** da ferramenta Selecionar é uma cruz com um quadradinho de captura no
  meio (desenho próprio).

## 3. No 3D
- Clique num elemento soma; Shift + clique tira; Esc limpa.
- **Janela por 2 cliques** no vazio, com a mesma regra de direção; o que vale é o
  contorno do elemento projetado na tela (envoltória convexa).
- Arrastar com o botão esquerdo continua **girando** a câmera (por isso não há laço no
  3D).
- Destaque ao passar o cursor, como na planta.

## 4. Preferência
**Editar > Modo de seleção**: **Somar cliques (como no CAD)** — padrão — ou **Trocar a
seleção a cada clique** (o comportamento anterior: clique troca, Ctrl+clique soma,
arrastar no vazio faz a janela). Gravado nas preferências do usuário.

## 5. Critérios de aceite (testes)
- [ ] **SE01** Núcleo: elementos dentro de um polígono (laço) e que tocam o polígono;
      laje só inteira.
- [ ] **SE02** Planta: clique soma, Shift+clique tira, Esc limpa; clique no vazio abre a
      janela e o segundo clique fecha; direita = inteiros, esquerda = os que tocam;
      Shift tira.
- [ ] **SE03** Planta: laço por arrasto, direção pelo primeiro movimento; destaque sob o
      cursor; camada bloqueada fora.
- [ ] **SE04** 3D: clique soma; janela por dois cliques (direita/esquerda); destaque.
- [ ] **SE05** Modo "Trocar a seleção" devolve o comportamento anterior.

## 6. Fontes
- Pesquisa do projeto, `autocad.md` §1: seleção por janela (esquerda→direita, só o que
  está inteiro dentro) e por cruzamento (direita→esquerda, o que toca), além de cerca,
  laço e seleção rápida por propriedade (fonte citada lá). `interface_e_interacao.md`
  §2: comportamento janela/cruzamento em cada programa "sem fonte nesta rodada" —
  **conferir** na ajuda pública do AutoCAD (seleção por laço e PICKADD).
- Pedido e respostas do revisor (2026‑10‑26).
- Nenhum material de `_restrito/` nem de `tools/` foi usado. Cursor e cores próprios.

## 7. Pontos de revisão
(a) somar cliques como padrão (o oposto do Archicad e do Revit);
(b) janela retangular por dois cliques e laço ao arrastar (não pedido explicitamente, mas
    sem os dois cliques não haveria janela retangular);
(c) no 3D, sem laço (arrastar gira a câmera);
(d) cerca (*fence*) e seleção por propriedade ficam para depois (a seleção por
    semelhança já existe, spec/ui 23).
