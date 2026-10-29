---
documento: Interação — área de seleção (esticar, 3D da área, exportar e imprimir a área)
requisito: RF-NUC-05 (edição); pedido do revisor em 2026-10-29
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: em revisão (implementação por etapas: §2, §3 e §4 feitos; §5 a fazer)
revisor: OTTO
---

# Área de seleção

## 1. Propósito
Pedido do revisor: uma ferramenta para marcar uma **área** da planta (não elementos) e
agir sobre o que está nela. Escolhas do revisor (2026‑10‑29): nome **Área de seleção**;
primeira entrega com **Esticar**, **3D da área** e **Exportar/imprimir a área**.
Selecionar/editar o conteúdo (mover, copiar, excluir o que está dentro) fica para
depois (§7).

## 2. Ferramenta *(feito)*
- Ícone próprio no grupo **Edição** da barra Ferramentas; menu Editar > Área de seleção.
- Barra Opções: forma **Retângulo** (2 cliques, padrão) ou **Polígono** (cliques; fecha
  no primeiro ponto, Enter ou clique duplo), e alcance **Este pavimento** (contorno
  tracejado fino) ou **Todos os pavimentos** (tracejado grosso). Guias e atração valem
  ao desenhar (spec/ui 37).
- Só existe **uma** área por vez. Ela **fica** na planta ao trocar de ferramenta (para
  usar o 3D ou exportar depois) e sai com Esc na ferramenta Área de seleção, com Editar >
  Remover área de seleção ou ao desenhar outra. É da sessão: não vai para o IFC nem
  para o diário.
- A área não seleciona elementos e não tem alças; contorno tracejado na cor de destaque.
- Mover a área: com a ferramenta ativa, arrastar a partir de um ponto **dentro da área
  que não é vértice nem ponta de elemento** leva só a área.

## 3. Esticar *(feito)*
- Com a ferramenta ativa, arrastar a partir de um **vértice ou ponta dentro da área**
  (ou clicar nele e depois no destino; distância e ângulo no quadro de medidas) estica:
  todo ponto que define um elemento e está dentro da área (ou na borda) anda pelo vetor;
  os de fora ficam. A área anda junto.
  - parede: ponta(s) dentro; parede em arco mantém o ângulo central (o raio acompanha);
  - laje, cobertura, ambiente à mão, hachura, abertura na laje: os vértices dentro;
  - viga, linha 2D, cota e as demais anotações: os pontos dentro;
  - pilar, objeto solto, eixo, claraboia: andam inteiros se o ponto de inserção estiver
    dentro; objeto preso à parede só acompanha a parede;
  - elemento com todos os pontos dentro anda inteiro (é um mover).
- Elementos ocultos ou de camada bloqueada não esticam. O desenho importado (DWG) não
  estica. Com "Todos os pavimentos", estica nos pavimentos todos, numa transação.
- Uma transação "Esticar" (desfaz com Ctrl+Z); recusa "nada a esticar" se nenhum ponto
  muda. Junções das paredes refeitas como em mover.
- Não há esticar no 3D (o 3D só mostra a área).
- Paredes do pavimento de baixo, que a planta mostra em cinza, não contam como deste
  pavimento.

## 4. 3D da área *(feito)*
- Exibir > **3D da área** (também no botão direito da planta com a área desenhada).
- Abre uma aba **temporária** "3D da área" (não muda a aba 3D principal nem vistas
  salvas): mostra só os elementos que têm alguma parte dentro da área, **recortados**
  pelas paredes verticais da área (planos de corte); retângulo e polígono convexo
  recortam exato; polígono côncavo mostra os elementos inteiros que tocam a área.
- Pavimentos: "Este pavimento" mostra só o pavimento ativo; "Todos", o prédio todo.
- A aba acompanha o modelo; mudar a área atualiza a aba aberta. Sem área (removida),
  fica a última; abrir outro projeto fecha a aba.
- As faces cortadas saem fechadas (tampa na cor do elemento, mais escura).
- Feito: `scene3d.area_scene` (recorte das malhas do 3D principal, sem tesselar de novo;
  tampas por `_caps`) e `view3d.AreaView3D` (aba que fecha, refaz a cena ao pintar).

## 5. Exportar e imprimir a área *(a fazer)*
- Arquivo > **Exportar área (PDF)…** e **Exportar área (DXF)…**: a planta do pavimento
  ativo (com as anotações visíveis) **recortada** pela área, na escala da vista, em
  folha do tamanho da área mais margem (PDF) ou em metros (DXF).
- Arquivo > **Imprimir área…**: o mesmo PDF pela impressora do sistema.
- Usa o desenho da planta que já gera PDF (spec/ui 15) com o recorte por polígono.

## 6. Onde está
- Núcleo sem Qt: `brasbim/core/selection_area.py` (`Area`, `contains`, `touched`,
  `stretch_fn`), `transform.stretch_elements`, `geom2d.stretched`.
- Interface: `AreaTool` em `brasbim/ui/tools.py` (a área fica em `PlanContext.area`;
  `Tool.escape` separa o Esc da vista do `cancel` da troca de ferramenta); contorno em
  `PlanView._draw_area`; barra Opções em `toolbars.py`; ícones `selection_area`,
  `area_rect`, `area_polygon`, `area_storey`, `area_all`.
- Na ferramenta, o quadro de medidas dá largura e altura no retângulo, e distância e
  ângulo ao esticar ou mover a área. O retângulo também sai arrastando do 1º canto.

## 7. Fica para depois
Selecionar o conteúdo (tudo ou por tipo), mover/copiar/excluir o conteúdo recortado,
área girada e pela varinha (contorno detectado), copiar e colar a área, área em cortes
e fachadas.

## 8. Critérios de aceite (testes)
- **AS01** Dentro, na borda e fora de polígono côncavo; polígono sem área recusado.
- **AS02** Esticar parede, laje e linha 2D pela ponta/vértices dentro; elemento longe da
  área não entra; IFC válido.
- **AS03** Elemento todo dentro anda inteiro.
- **AS04** Área que não pega nenhum ponto: recusa.
- **AS05** Ferramenta: retângulo, polígono, mover a área, esticar
  arrastando, Esc remove (`tests/test_area_selecao_ui.py`).
- **AS06** 3D da área: aba temporária só com os elementos da área, recortados; côncava
  inteiros; este pavimento ou todos (`tests/test_area_selecao_ui.py`).
- **AS07** *(a fazer)* Exportar PDF/DXF da área: só o que está dentro.

## 9. Fontes
- Ajuda pública Graphisoft (lida em 2026‑10‑29): Marquee Area (AC19,
  help.graphisoft.com/AC/19/INT/AC19Help/02_Interaction/02_Interaction-42.htm); Marquee
  Area Definition: Single Story or All Stories (AC18, …/AC18Help/02_Interaction/
  02_Interaction-47.htm); Show/View Marquee Area in 3D (AC18, …/02_Interaction-50.htm);
  Stretching with the Marquee Tool (AC20, …/AC20Help/02_Interaction/02_Interaction-88.htm);
  Copy/Paste Marquee Area (AC28, …/_AC28_Help/030_Interaction/030_Interaction-36.htm).
  Retirado: área retangular ou poligonal que não seleciona elementos; um pavimento ou
  todos; esticar pontos dentro e mover o que está todo dentro; arcos mantêm o ângulo
  central; 3D só do que toca a área; salvar o pedaço como PDF/DWG.
- Ajuda pública Autodesk: AutoCAD 2025 STRETCH por janela de cruzamento (objetos
  inteiros dentro se movem, os cortados esticam); Revit 2024/2025 Crop Region e Section
  Box (recorte da vista e caixa de corte 3D).
- Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/interface_e_interacao.md` §3
  (Selection Box do Revit sobrescreve o 3D padrão: aqui, aba temporária) e
  `archicad_modelagem.md` (área "grossa" para esticar em todos os pavimentos).
- Nada de `_restrito/`. "Área de seleção" e "Esticar" são termos comuns em pt‑BR.

## 10. Pontos de revisão
(a) A área fica na planta ao trocar de ferramenta (sai com Esc na própria ferramenta).
(b) Polígono côncavo no 3D mostra os elementos inteiros (sem recorte exato).
(c) Exportar usa a escala da vista e só o pavimento ativo, mesmo com "Todos".
