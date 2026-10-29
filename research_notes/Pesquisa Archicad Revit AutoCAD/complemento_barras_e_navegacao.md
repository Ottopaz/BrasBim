# Complemento: travar, recortar pela cobertura, ordem de desenho, ocultar, projeção paralela, andar, zoom anterior, girar a vista, pegar/aplicar ajustes, pavimento de referência e situação em um clique

> Pesquisa clean-room, só com fontes públicas na web. Data de acesso de todas as URLs: **2026-10-29**.
> Fase 0 do plano `reports/Plano barras e navegador (prints 2026-10-29).md`: cobre os itens sem fonte
> (9, 16, 20, 21, 23, 24, 31, 32, 3, 8) e o item 46 (explicado pelo revisor).
> Tudo está resumido com palavras próprias. Os nomes de comandos servem só para identificar a função
> descrita; o BrasBim usa vocabulário próprio. Nada foi lido de `_restrito/` nem de `tools/`, e nenhum
> binário foi inspecionado.
> **Método:** desta vez os achados vêm todos dos resumos da busca na web, sem abrir as páginas
> **(via resultado de busca)**. Antes de fechar cada spec, abrir a página oficial citada e conferir. Os
> fóruns valem como relato de uso, não como documentação.

## 1. Travar elemento (item 9)

### Achados citados
- **Archicad: travar e destravar um a um.** Um elemento fica travado por três caminhos: está numa camada
  travada, foi travado pelo comando de travar (menu Editar), ou faz parte de um módulo vinculado. Em
  todos os casos o elemento **pode ser escolhido** e serve de referência para construir (atração),
  mas **não pode ser editado**. Destravar vale para a seleção, e "destravar todos" vale até para o que
  não está escolhido. Ao passar o cursor, a informação diz se o travado é o elemento ou a camada. —
  [Como travar/destravar (comunidade Graphisoft)](https://community.graphisoft.com/t5/Getting-started/How-to-Lock-Unlock-Elements-in-Archicad/ta-p/303879); [helpcenter.graphisoft.com/?p=76414](https://helpcenter.Graphisoft.com/?p=76414) (via resultado de busca)
- **Archicad: pedido antigo dos usuários.** Há pedidos para que o travado nem possa ser escolhido. Não
  há sinal de que exista essa opção. — [Prevent locked objects from being selectable](https://community.graphisoft.com/t5/Wishlist/Prevent-locked-objects-from-being-selectable/idc-p/292945/highlight/true) (via resultado de busca)
- **Revit: prender (pin).** O elemento preso mostra um alfinete quando escolhido; tirar o alfinete libera
  a edição. Um botão na barra de estado desliga a **escolha** de elementos presos, mas medir e cotar
  continuam valendo. Qualquer pessoa pode tirar o alfinete: é um aviso, não uma proteção. O aviso de
  "elemento preso" só aparece depois de terminado o mover, o que irrita. Usos típicos: eixos, níveis,
  vínculos e pontos de base. — [Arkance: pin](https://ukcommunity.arkance.world/hc/en-us/articles/21565910173586-Revit-Tip-Pin-down-objects-to-prevent-unintentional-model-changes); [Autodesk forum: aviso do elemento preso](https://forums.autodesk.com/t5/revit-ideas/pinned-element-warning-improvement/idc-p/13330490) (via resultado de busca)

### Inferências
- Os dois programas deixam o travado **escolhível** e **atraível** e só recusam a edição. Isso
  contraria a proposta do plano ("o travado não é escolhido"). Melhor: escolhível, atraível, com recusa
  **antes** de começar a arrastar (não no fim, como a queixa do Revit), e uma chave "escolher travados"
  na barra da vista.
- Guardar no IFC (resposta (c) recomendada) combina com o uso típico (eixos, vínculos), que precisa
  durar entre sessões.

## 2. Recortar pela cobertura (item 16)

### Achados citados
- **Archicad: recortar elementos pela cobertura ou casca.** A cobertura (ou casca) é sempre quem
  recorta; o recortado pode ser parede, viga, pilar etc. Com várias coberturas e outros elementos
  escolhidos, as coberturas se juntam num corpo só que corta o que fica para fora. Desde a versão 26 o
  recorte é **associativo**: mudar a inclinação da cobertura muda a parede. Refazer o recorte substitui o
  anterior, sem desfazer. Há um comando mais antigo, só para cobertura de um plano, que muda a
  parede de forma fixa. — [Trim Elements to Roof or Shell (AC28)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-90.htm); [AC30](https://help.graphisoft.com/AC/30/INT/Topics/040_ElementsVB/040_ElementsVB-90.html) (via resultado de busca)
- **Revit: prender topo/base da parede.** Escolhe-se a parede, depois topo ou base, depois a cobertura,
  laje, forro, plano de referência ou outra parede. A altura da parede se ajusta à superfície. Só a
  parte coberta pelo elemento se prende. As propriedades continuam mostrando a altura original, o que
  confunde. Há "soltar" um a um e "soltar todos". — [Attach Walls to Other Elements (2026)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-ArchDesign/files/GUID-ED60CE62-B955-45E9-9D7D-00F1552D858C.htm) (via resultado de busca)

### Inferências
- Associativo desde a primeira entrega, como na resposta (e) para sólidos. Na ficha da parede, mostrar
  "topo: recortado por <cobertura>" no lugar da altura original (evita a confusão relatada no Revit).
- A parte fora da cobertura fica como está (altura própria), como no Revit.

## 3. Ordem de desenho (item 20)

### Achados citados
- **Archicad:** trazer para a frente (por cima de tudo), mandar para trás (por baixo de tudo), um passo
  para a frente e um passo para trás, e voltar à ordem padrão. A ordem padrão já põe textos e cotas por
  cima; para uma hachura cobrir um texto, o texto tem de descer um passo. — [Display Order (AC27)](https://help.graphisoft.com/AC/27/INT/_AC27_Help/030_Interaction/030_Interaction-102.htm) (via resultado de busca)
- **AutoCAD / BricsCAD:** a mesma ideia, com "acima de" e "abaixo de" um objeto de referência escolhido.
  — [DRAWORDER (AutoCAD LT 2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-3DC76D6E-8F81-4803-8D0A-AA7541D6357E.htm); [Bricsys: Draw order](https://help.bricsys.com/en-us/document/bricscad/modifying-entities/draw-order) (via resultado de busca)

### Inferências
- Quatro ações (frente, trás, um passo, um passo) e "voltar ao padrão". O "acima de/abaixo de outro"
  pode vir depois. Só para anotações e hachuras, como já diz o plano.

## 4. Ocultar selecionados (item 21)

### Achados citados
- **Archicad:** ocultar a seleção no 3D pelo botão direito (desde a versão 25) e "mostrar tudo" com nada
  escolhido. Não dá para trazer de volta só alguns. — [Show hidden elements selectively (comunidade)](https://community.graphisoft.com/t5/Modeling/Show-hidden-elements-selectivly/m-p/385849) (via resultado de busca)
- **Revit:** ocultar/isolar **temporário** pela barra de baixo da vista. Some ao fechar o projeto,
  a menos que se torne permanente na vista. A vista mostra que está nesse estado, e um "restaurar"
  traz tudo de volta. — [Temporarily Hide or Isolate (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-A5E51D5E-8E18-4834-8A2F-8B4E3E6379A1.htm) (via resultado de busca)

### Inferências
- Confirma a resposta (d) recomendada: **só da sessão**. Junto vêm **isolar** (o contrário), um aviso
  visível na vista enquanto há algo oculto, e "mostrar tudo". "Tornar permanente" pode ser "guardar
  na vista salva", mais tarde.

## 5. Projeção paralela no 3D (item 23)

### Achados citados
- **Archicad:** alternância entre axonometria e perspectiva por atalho, menu e barra. Vistas prontas (de
  cima, de lado, isométricas…) e axonometria livre por ângulos dos eixos. A axonometria centra o modelo
  inteiro; a perspectiva tem ponto de vista e alvo. Para guardar a projeção, salva-se uma vista. —
  [3D Projections (AC30)](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-20.html) (via resultado de busca)
- **Revit:** a vista 3D padrão é ortográfica; caminhar e voar só funcionam em perspectiva (câmera). —
  [Navigating views (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-A3F4A7B5-225F-46D2-99D3-4C9771282DCA.htm) (via resultado de busca)

### Inferências
- Uma chave paralela/perspectiva no 3D. As vistas padrão do BrasBim (de cima, fachadas) passam a usar
  paralela. Andar (item 24) liga a perspectiva sozinho.

## 6. Andar pelo modelo (item 24)

### Achados citados
- **Archicad:** modo de exploração com teclado e mouse. Uma tecla liga o voo; desligado, a altura fica
  presa. Há teclas para subir e descer e um modificador para andar mais rápido. Só em perspectiva.
  Usuários reclamam que não há onde ver nem digitar a altura dos olhos; o visualizador BIMx usa 1,6 m
  acima do piso. — [Explore Model (AC27)](https://help.graphisoft.com/AC/27/INT/_AC27_Help/030_Interaction/030_Interaction-15.htm); [Eye height in Explore (comunidade)](https://community.graphisoft.com/t5/Wishes-forum/Eye-height-in-Walking-quot-Explore-Mode-quot/td-p/194164) (via resultado de busca)
- **Revit:** caminhar por "rodas" de navegação que seguem o cursor, só em vista de câmera; recomenda-se
  uma câmera própria para não estragar as vistas de apresentação. — [Use SteeringWheels to Create a Walkthrough (2024)](https://help.autodesk.com/cloudhelp/2024/ENU/RevitLT-GetStarted/files/GUID-50B7F160-E0DF-45F9-B78F-D5240F19B1C5.htm) (via resultado de busca)

### Inferências
- Altura dos olhos **visível e editável** (1,60 m acima do piso do pavimento), justo onde os usuários
  sentem falta. Andar começa numa câmera temporária, sem mexer na aba 3D principal.

## 7. Zoom anterior e seguinte (item 31)

### Achados citados
- **Archicad:** voltar e avançar pelos enquadramentos já usados, com 20 guardados; os botões ficam no pé
  da janela. Não confundir com ir para a vista anterior/seguinte do projeto. — [Navigating in 2D (comunidade)](https://community.graphisoft.com/t5/Getting-started/Navigating-in-2D/ta-p/303964) (via resultado de busca)
- **AutoCAD:** "zoom anterior" restaura até 10 enquadramentos; também "zoom janela", "extensão" e
  "escala". — [ZOOM (AutoCAD LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-66E7DB72-B2A7-4166-9970-9E19CC06F739.htm) (via resultado de busca)

### Inferências
- Pilha de enquadramentos por aba (uns 20), gravada ao parar o zoom ou o deslocamento (não a cada
  passo da roda). Fica na barra da vista, como já está no plano.

## 8. Girar a vista da planta (item 32)

### Achados citados
- **Archicad:** girar a orientação da janela por dois cliques (um vetor); o ângulo aparece num botão que
  volta a zero. A rotação vai com a vista salva. Textos podem ficar sempre na horizontal; os textos das
  cotas se ajustam sozinhos. Usuários relatam a rotação "escondida" em vistas salvas atrapalhando a
  prancha. — [Oriented View (AC18)](https://help.graphisoft.com/AC/18/INT/AC18Help/02_Interaction/02_Interaction-5.htm); [support: título girado na prancha](https://support.graphisoft.com/hc/en-us/articles/32853829223697-Why-is-the-drawing-title-rotated-on-a-layout-sheet) (via resultado de busca)
- **Revit:** gira-se o recorte da vista (o modelo gira ao contrário), só com a orientação "norte do
  projeto"; recomenda-se duplicar a vista antes. — [Rotating a View by the Crop Region (2014)](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-10044F8E-7DC4-46C8-9AF5-B7E0FB8AD751.htm) (via resultado de busca)

### Inferências
- Ângulo **sempre visível** na barra da vista (evita a rotação escondida), definido por dois cliques
  ou digitado, e um "voltar a 0°". Textos e etiquetas ficam legíveis (nunca de cabeça para baixo). Na
  prancha, a vista salva girada entra girada e o título fica na horizontal.

## 9. Pegar e aplicar ajustes (item 3)

### Achados citados
- **Archicad:** um modificador + clique pega os ajustes de um elemento, que viram o padrão da ferramenta
  daquele tipo; outro modificador + clique aplica a um elemento. Um "conjunto de transferência"
  escolhido diz quais ajustes passam. Não dá para escolher parâmetros um a um na hora. Queixa: o
  tamanho passa junto (um sofá de 1,80 m faz a cadeira ficar com 1,80 m). Desfaz como qualquer edição. —
  [Parameter Transfer (AC25)](https://help.graphisoft.com/AC/25/INT/_AC25_Help/030_Interaction/030_Interaction-102.htm); [Injecting parameters between different objects (comunidade)](https://community.graphisoft.com/t5/Modeling/Injecting-parameters-between-different-objects/td-p/232670) (via resultado de busca)
- **Revit:** casar tipo: clica-se no elemento de origem e depois nos de destino (ou numa janela de
  seleção); muda o **tipo**, e os parâmetros da instância ficam (a ajuda de 2018 diz assim; a de 2014
  dizia o contrário). Origem e destino têm de ser da mesma categoria. — [Match Type (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-Model/files/GUID-796061DB-5ED0-49FB-973D-2408CE54BF5D.htm) (via resultado de busca)

### Inferências
- Dois níveis, por padrão: **tipo e aparência** passam; **medidas próprias** (comprimento, largura de
  objeto) só passam se marcadas. Isso evita a queixa do sofá. Só entre elementos da mesma classe
  (parede→parede).

## 10. Pavimento de referência (item 8)

### Achados citados
- **Archicad:** a referência se escolhe numa lista na barra, num painel ou no menu Exibir. Opções
  **relativas** (pavimento de cima, de baixo, o anterior) mudam ao trocar de pavimento; para fixar um,
  escolhe-se qualquer vista do projeto. Cada vista aberta pode ter a sua referência. — [Choosing a Trace Reference (AC19)](https://help.graphisoft.com/AC/19/INT/AC19Help/02_Interaction/02_Interaction-128.htm) (via resultado de busca)
- **Revit:** "subposição" mostra outro nível no plano de corte da vista, olhando para baixo (como
  planta) ou para cima (como forro). Escolhe-se o nível de base e o de topo da faixa. — [About Underlays (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-F03617DC-541D-49CF-B40C-B2537175F561.htm) (via resultado de busca)

### Inferências
- Seletor na barra da vista: **relativo** (de baixo, padrão de hoje; de cima) ou **fixo** (um pavimento
  pelo nome). Desenho em cinza e não editável, como hoje.

## 11. Situação em um clique (item 46)

### Achados citados
- **Archicad:** escolhem-se os elementos e clica-se no ícone da situação (existente, a demolir, novo)
  numa paleta própria. **Com nada escolhido**, o clique define a situação dos **próximos** elementos
  criados (marcar "novo" antes de desenhar a obra nova). O padrão é "existente". — [Assign Renovation Status to Elements (AC27)](https://help.graphisoft.com/START/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-122.htm) (via resultado de busca)

### Inferências
- Os três botões fazem as duas coisas: com seleção, mudam a situação dela; sem seleção, escolhem a
  situação dos próximos elementos. Para não esquecer, o botão da situação corrente fica marcado. Usa a
  propriedade de situação que já existe (spec/ui 31).

## Lacunas
- Todos os achados vêm de resumos de busca; abrir as páginas oficiais antes de fechar cada spec.
- Travar: não achei fonte oficial do Archicad sobre como o travado aparece no IFC exportado.
- Andar: não achei fonte oficial de colisão com paredes nem de subir escadas.
- Zoom anterior: o número de passos (20 no Archicad, 10 no AutoCAD) vem de relato e da ajuda antiga.
- Girar a vista: só a ajuda AC17/AC18 descreve a ferramenta; nas versões novas o caminho mudou
  (relatos de fórum).
