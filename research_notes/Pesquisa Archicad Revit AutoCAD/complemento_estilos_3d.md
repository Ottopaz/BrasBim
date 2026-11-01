# Complemento: estilos de apresentação da vista 3D (2026‑11‑01)

Pedido do revisor: "estudar as formas de apresentação 3D do Archicad para aplicarmos uma
parecida" (modelo sem as arestas que hoje aparecem, modelo todo branco etc.). Só fontes
públicas (ajuda oficial, documentação da API e fórum da Graphisoft), lidas pelos resumos
de busca. Fecha a lacuna "detalhes dos estilos 3D do Archicad" de
`visualizacao_apresentacao.md`. Descreve **funções**; nomes, textos e layout de diálogo não
são copiados.

## 1. O que o Archicad oferece (função)
- **Estilos 3D gravados com nome**, escolhidos por vista; cada estilo junta o motor, o modo
  e os efeitos. Fonte: [Help AC28 – 3D Styles](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-46.htm);
  [API – API_3DStyle](https://archicadapi.graphisoft.com/documentation/api_3dstyle).
- **Três modos:** arame (todas as arestas, inclusive as de trás; "difícil de ler" com
  muitos elementos), linhas ocultas (tira as linhas tapadas por sólidos; só no motor
  vetorial) e sombreado (faces sombreadas pela direção da luz). No motor acelerado por
  placa de vídeo só há arame e sombreado. Fontes: [Help AC27](https://help.graphisoft.com/AC/27/INT/_AC27_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-44.htm);
  [Help AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-44.htm);
  [Help AC21 – Appendix Settings](https://help.graphisoft.com/AC/21/INT/AC21Help/Appendix_Settings/Appendix_Settings-80.htm).
- **Modelo monocromático:** uma cor só para todas as superfícies e outra para os contornos
  (na API, um sinalizador e as duas cores); senão as cores vêm dos materiais. Mesma fonte
  da API.
- **Contornos no sombreado:** ligar/desligar e espessura em pixels (1 a 10 na API); em
  outra configuração, três níveis (desligado, rascunho, melhor). Desligar tira todas as
  arestas. Fontes: [API – shading contours](https://archicadapi.graphisoft.com/documentation/api_shadingcontoursid);
  [Fórum – contornos desligados](https://community.graphisoft.com/t5/Modeling/Window-and-door-sash-shows-in-3D-with-contours-off/m-p/143010).
- **Sombreado pelo sol:** desligado, faces iguais ficam com a mesma cor, qualquer que seja
  a orientação. Fonte: [Help AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-46.htm).
- **Sombras do sol na vista 3D** com o modelo monocromático e contornos ("modelo branco com
  sombra" é o uso comum em apresentação); as sombras de luminárias só no render. Fontes:
  [Fórum – sombras na janela 3D](https://community.graphisoft.com/t5/Modeling/Lamp-shadows-in-3D-window-not-rendering/m-p/664431);
  [Suporte Graphisoft – modelo branco para o cliente](https://support.graphisoft.com/hc/en-us/articles/27129059479057-How-can-I-present-a-white-model-to-my-client).
- **Efeito de modelo branco no render** (configurações de fotorrenderização), à parte da
  vista 3D. Mesma fonte do suporte.
- **Sombras suaves experimentais** (luz ambiente/indireta) num renderizador físico da vista
  3D. Fonte: [Help AC27 – renderizador físico experimental](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-32.htm).

## 2. Consequências para o BrasBim
- Precisamos de **estilos com nome**, escolhidos na barra da vista 3D, gravados na vista
  salva e usados na imagem da prancha.
- O "linhas ocultas" pode sair barato no OpenGL atual: faces pintadas com a cor do fundo e
  só as arestas que o teste de profundidade deixa passar.
- O monocromático (maquete branca) é só trocar a cor das malhas; o sombreado pela luz já
  existe (`_shaded`).
- **Contorno = arestas vivas e silhuetas**: hoje vão para a tela todas as arestas que o
  IfcOpenShell devolve; nas malhas facetadas (árvores, cilindros, faces trianguladas)
  aparecem as emendas entre faces quase no mesmo plano, que um desenhista não traçaria.
- Sombras projetadas do sol pedem sombreamento por mapa de sombras (shaders): fica para uma
  segunda etapa.
