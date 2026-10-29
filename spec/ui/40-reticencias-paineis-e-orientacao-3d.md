---
documento: Interação — sem reticências, painéis Pavimentos e Navegador, controle de orientação no 3D
requisito: RF-NUC-05 (interface); pedidos (a)–(c) do revisor em 2026-10-29, noite
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão
revisor: OTTO
---

# Sem reticências, painéis Pavimentos e Navegador, controle de orientação no 3D

## 1. Propósito
Três pedidos do revisor (CONTEXTO.md, 2026‑10‑29, noite), feitos nesta ordem: (b) tirar as
reticências "…" da interface; (c) dividir o painel Projeto em **Pavimentos** e
**Navegador**; (a) um controle de orientação no canto do 3D. O print
`feedback/prints/Controle3dBlender.png` vale só como descrição de função: o desenho, os
nomes e as cores do controle são do BrasBim.

## 2. Sem reticências
- Nenhum texto visível termina ou é cortado com "…": itens de menu (barra de menus e botão
  direito), botões, abas, títulos de aba, textos de ajuda dentro de campos, mensagens de
  andamento ("Lendo planta.dxf", não "Lendo planta.dxf…"). A convenção de alguns sistemas
  ("…" = abre um quadro) não é seguida: o quadro que abre já diz o que é.
- Botões que eram só "…" ganham ícone próprio com dica: estilo do material → ícone
  **paleta**; ações da combinação de camadas → ícone **opções** (três traços).
- Textos de ajuda com "…" no meio dizem o formato inteiro: "Pontos (x y; x y)".
- **Texto que não cabe não é cortado pelo Qt com "…"**: listas, árvores e tabelas cortam
  seco (sem reticências) e dão o texto inteiro na dica; as barras de abas não encurtam o
  título (aparecem as setas de rolar). Vale para o aplicativo todo, ligado na partida.
- Apelidos da linha de comando gravados com o nome antigo do menu (ex.:
  "Exibir/Salvar vista…") continuam valendo: o "…" é tirado ao ler.
- Comentários e docstrings do código não contam (não aparecem na tela).

## 3. Painéis Pavimentos e Navegador
Base na pesquisa: o Archicad organiza vistas e folhas num navegador com mapas separados
(pontos de vista do modelo, vistas salvas, folhas, conjuntos de publicação), e as folhas
mestras ficam no livro de folhas (`archicad_documentacao_colaboracao.md` §1); o Revit 2026
pôs o navegador de projeto em abas por tipo, e a pesquisa conclui que separar "o que existe
no modelo" de "vistas e folhas" ajuda (`revit_documentacao_colaboracao.md` §2). O plano das
barras (Fase 5, itens 42–44) leva isso a uma árvore única com busca; esta spec é o passo
anterior, pedido pelo revisor.

### 3.1 Pavimentos
- Painel próprio, **Pavimentos**, à esquerda, em cima: a tabela de hoje (Nome, Cota, Plano
  de corte, Escala; clique ativa, clique duplo edita) e embaixo dois botões de ícone com
  dica: **Novo pavimento** (+) e **Excluir pavimento** (×).

### 3.2 Navegador
- Painel **Navegador**, à esquerda, sob Pavimentos. No alto, uma fileira de botões de
  ícone (dica com o nome), um por seção; o botão da seção aberta fica marcado. Embaixo, o
  nome da seção em negrito com a quantidade ("Pranchas (3)"), a lista e, ao pé, as ações
  da seção em botões de ícone com dica (as que escolhem entre opções abrem a lista no
  clique).
- Seções, nesta ordem:
  1. **Cortes e fachadas**: a árvore de hoje, em grupos.
  2. **Vistas salvas**: a lista de hoje; ação Salvar vista.
  3. **Pranchas**: a árvore de hoje (prancha → desenhos); ações Nova prancha e Excluir.
  4. **Folhas mestras**: ações Nova (formatos), Duplicar e Excluir.
  5. **Tabelas**: ações Nova tabela (modelos) e Excluir.
  6. **Objetos**: a árvore de tipos; ações do objeto e Biblioteca.
- Criar uma prancha, folha mestra ou tabela abre a seção dela. A seção aberta é estado da
  janela (não vai para o IFC).
- Exibir > Painéis lista **Pavimentos** e **Navegador** no lugar de Projeto. A disposição
  gravada de antes não traz o painel antigo; os dois novos entram na posição padrão.

## 4. Controle de orientação no 3D
Pesquisa: os detalhes dos cubos e controles de vista de outros programas ficaram como
lacuna (`interface_e_interacao.md` §3, Gaps); as vistas prontas de cima, de lado e
isométricas aparecem no Archicad (`complemento_barras_e_navegacao.md` §5) e já existem no
BrasBim (Exibir > Vistas padrão). O controle dá acesso a elas num clique, a partir do
pedido do revisor.

- **Onde:** canto superior direito do 3D (também no 3D da área), cerca de 90 px, sem
  fundo; não pega o clique fora dele.
- **Desenho:** três eixos saindo do centro, que giram com a câmera. Na ponta positiva, um
  círculo cheio com a letra (**X** = leste, **Y** = norte, **Z** = para cima); na ponta
  negativa, um círculo menor só de contorno. Cores do tema: X avermelhado, Y esverdeado,
  Z azulado. O que está atrás é desenhado primeiro e mais apagado.
- **Passar o cursor** sobre um círculo o realça e dá a dica com o nome da vista: "Topo
  (+Z)", "De baixo (−Z)", "Do leste (+X)", "Do oeste (−X)", "Do norte (+Y)", "Do sul (−Y)".
- **Clicar** num círculo põe a câmera olhando daquela direção, com o mesmo centro e a mesma
  distância (não reenquadra). Clicar de novo no círculo da vista em que já se está dá a
  **vista inversa** (do leste → do oeste; topo → de baixo).
- **Arrastar** a partir do controle orbita, como arrastar no 3D. O clique e o arraste no
  controle nunca vão para a ferramenta ativa nem mudam a seleção.
- Exibir > Vistas padrão ganha **De baixo**.
- A troca é imediata (animação, se o revisor quiser, depois). Nada vai para o IFC.

## 5. Testes
- **RT01:** nenhum item de menu (barra e menus de contexto do painel), botão ou aba da
  janela e dos painéis tem "…"; listas, árvores e abas não cortam com reticências; o apelido
  gravado "menu:Exibir/Salvar vista…" vale para Exibir > Salvar vista.
- **NV01:** existem os painéis Pavimentos e Navegador (e não Projeto); a tabela de
  pavimentos ativa e cria pavimentos; o Navegador tem as seis seções na ordem do §3.2.
- **NV02:** criar prancha, folha mestra e tabela abre a seção de cada uma, e o título dá a
  quantidade.
- **OR01:** (sem Qt) na vista de topo, o círculo +Z fica no centro e +X à direita; na
  isométrica, os três positivos ficam na frente dos negativos.
- **OR02:** clicar em +X dá a vista do leste com o mesmo centro e distância; clicar de novo
  dá a do oeste; +Z e de novo dá o topo e de baixo.
- **OR03:** com a ferramenta Parede ativa, clicar no controle não cria parede nem muda a
  seleção; arrastar a partir dele orbita.

## 6. Fontes
- `research_notes/Pesquisa Archicad Revit AutoCAD/archicad_documentacao_colaboracao.md` §1
  (Navigator e folhas mestras no livro de folhas).
- `research_notes/Pesquisa Archicad Revit AutoCAD/revit_documentacao_colaboracao.md` §2
  (navegador com abas por tipo, 2026).
- `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §3 (lacuna dos
  controles de vista) e `complemento_barras_e_navegacao.md` §5 (vistas prontas).
- `reports/Plano barras e navegador (prints 2026-10-29).md`, itens 42–44 (Fase 5).
- Pedido do revisor e print `feedback/prints/Controle3dBlender.png` (descrição de função).
