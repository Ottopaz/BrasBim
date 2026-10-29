# Complemento: elevação interna, detalhe, folha de trabalho, câmera, polilinha, ponto de apoio, figura e desenho

> Pesquisa clean-room, só com fontes públicas na web. Data de acesso de todas as URLs: **2026-10-29**.
> Feita para a spec/ui 34 §4. Fecha as lacunas declaradas em `archicad_documentacao_colaboracao.md`
> (§1, Gaps), `revit_documentacao_colaboracao.md` (§1, Gaps) e `autocad.md` (§3, Lacunas).
> Tudo está resumido com palavras próprias. Os nomes de comandos e ferramentas servem só para
> identificar a função descrita. Nada foi lido de `_restrito/` nem de `tools/`, e nenhum binário foi
> inspecionado.
> Observação de método: o help do Archicad tem páginas de várias versões. Usei a mais nova que
> abriu (AC27–AC30); quando só abriu uma versão antiga, a nota diz qual. As páginas `view/RVT/2026` do
> help da Autodesk deram 404 no fetch; as mesmas páginas (mesmo GUID) abriram na forma `cloudhelp/2024`.
> O que veio só do resumo da busca está marcado "(via resultado de busca)".

## 1. Elevação interna

### Resumo
Archicad e Revit tratam a elevação interna como um marcador posto na planta, dentro do ambiente,
que gera uma vista para cada parede. O Archicad gera um grupo de vistas a partir do contorno do
ambiente, com uma vista por lado, e limita a vista ao contorno. No Revit, o mesmo marcador de
elevação liga até quatro direções por caixas de marcar, e a seta se encosta na parede.

### Achados citados
- **Archicad: grupo de vistas a partir do contorno.** A ferramenta só cria vistas novas: não existe
  marcador de elevação interna "só de referência", que aponte para outra vista. Cada elevação é uma
  vista própria no mapa do projeto, e as vistas ficam num grupo, mesmo quando há uma só. Status,
  exibição e atualização seguem as regras do corte. — [Interior Elevations (AC27)](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-48.htm); [AC27 050_ViewsVB-49](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-49.htm)
- **Archicad: como se põe.** Ativa-se a ferramenta e desenha-se o contorno do ambiente por retângulo
  ou polígono, ou com um clique numa zona. Depois o cursor vai até o ponto de onde se olha (setas
  mostram as direções) e um clique põe os marcadores. Cada lado do contorno vira uma vista
  perpendicular a ele. Os marcadores ficam no meio de cada lado ou no centro do ambiente. Escolher
  qualquer lado do contorno escolhe o grupo, mas cada lado continua com ajustes próprios. Uma vista
  não passa de um grupo para outro. — [AC27 050_ViewsVB-50](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-50.htm)
- **Archicad: alcance horizontal.** Há duas opções. "Limitado" é o padrão e vai até o contorno (ou até a
  espessura da parede, quando o contorno é uma parede). "Infinito" mostra tudo o que se vê. Uma
  opção de incluir áreas vizinhas só pode ser escolhida antes de pôr o grupo. — [AC27 050_ViewsVB-52](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-52.htm)
- **Archicad: alcance vertical.** As cotas limite são medidas do zero do projeto ou do pavimento de
  origem, com valor próprio em cada lado. Uma opção pega a altura da zona. — [AC27 050_ViewsVB-53](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-53.htm)
- **Archicad: identificação e nome.** O grupo recebe um número, e o nome padrão leva a orientação
  (norte, sul…). Cada vista herda o nome do grupo ou recebe um próprio. — [AC27 050_ViewsVB-55](https://help.graphisoft.com/AC/27/INT/_AC27_Help/050_ViewsVB/050_ViewsVB-55.htm)
- **Archicad: dores relatadas.** Usuários abrem a elevação e não veem nada, ou veem elementos de fora
  do ambiente. As soluções propostas no fórum são reescolher a zona e o marcador ou ajustar a linha
  limite. — [Graphisoft Community, "Interior Elevation"](https://community.graphisoft.com/t5/Modeling/Interior-Elevation/td-p/86230); [Graphisoft Community, "Interior Elevations Help, Hints & Tips"](https://community.graphisoft.com/t5/Modeling/Interior-Elevations-Help-Hints-amp-Tips-Please/td-p/6535) (via resultado de busca)
- **Revit: um marcador para até quatro direções.** Elevações internas mostram paredes internas em
  detalhe, por exemplo de cozinhas e banheiros. A marca de elevação se encosta nas paredes quando é
  movida. Põe-se a marca perto da parede, e a seta gira para ficar perpendicular. Ao clicar no
  quadrado da marca aparecem caixas de marcar, e cada caixa marcada cria uma vista naquela direção.
  Clicar na seta mostra o plano de recorte, cuja largura se ajusta por alças. A seta só aparece na
  planta enquanto o recorte da vista cruza a faixa de vista da planta. — [About Elevation Views (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-819DC7D0-FDAC-420E-ABDD-2E944211F331.htm); [Create an Elevation View (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-2FFF0589-6793-4719-A081-EAFDFE940391.htm)

### Inferências
- O que o BrasBim aproveita das duas ideias é o contorno do ambiente (Archicad) e a escolha das
  direções no próprio marcador (Revit). Como o BrasBim já tem ambientes (`IfcSpace`) com contorno,
  um clique no ambiente basta. O recorte de cada vista sai do contorno, e não de alças ajustadas
  à mão.
- A dor "não aparece nada" vem de limites mal postos. Se a vista for desenhada a partir do contorno
  e da altura do ambiente, com o limite visível na planta, ela some.
- Atualização viva, como nos cortes do BrasBim (spec/ui 14 §4), evita o "reconstruir" manual.

## 2. Detalhe

### Resumo
No Archicad, o detalhe é um marcador com contorno posto numa vista. Ele gera uma vista nova só com
linhas e hachuras 2D tiradas do modelo, e essa vista só se atualiza por um comando de reconstruir.
O detalhe também pode ser independente (vazio) ou um marcador ligado a uma vista que já existe. No
Revit, o detalhe é uma "chamada" (callout), uma vista ampliada que continua sendo vista do modelo.
Ela pode apontar para uma vista 2D independente.

### Achados citados
- **Archicad: o que é.** O marcador de detalhe é posto numa planta, num corte, numa fachada, numa
  elevação interna, num documento 3D, numa folha de trabalho ou noutro detalhe. Ele cria uma vista de
  detalhe numa janela própria, listada no mapa do projeto. O marcador também pode só apontar para
  uma vista, vista salva ou desenho que já existe. O conteúdo gerado do modelo é uma cópia só 2D,
  que pode ser atualizada e receber linhas, textos e rótulos. Como a cópia "explodida" traz traços
  e hachuras demais, o próprio help recomenda juntá-los antes de editar. — [About Details (AC30)](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-62.html)
- **Archicad: como se põe.** Ativa-se a ferramenta com a opção de criar vista nova. O contorno pode
  ser polígono, retângulo ou retângulo girado; depois de desenhado, um clique põe o marcador. Uma
  forma "sem contorno" cria um marcador ligado a uma vista independente, sem origem no modelo. O
  marcador de origem pode aparecer com um preenchimento semitransparente na vista de origem. — [AC30 050_ViewsVB-63](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-63.html)
- **Archicad: conteúdo.** São só linhas e hachuras 2D dos elementos que estão dentro do contorno.
  Cotas e textos da origem não vêm por padrão (uma opção muda isso). Na janela do detalhe só valem
  as ferramentas 2D (linhas, hachuras, pontos, textos, figuras, cotas, símbolos 2D). O contorno
  aparece como linha no detalhe. — [AC30 050_ViewsVB-64](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-64.html)
- **Archicad: detalhe independente.** Começa vazio, sem origem, e não muda quando a planta muda. Serve
  para desenhar o que não está no modelo, como o detalhe de uma cerca. Pode ter marcador ou não; o
  que não tem pode ganhar um marcador ligado depois. — [AC30 050_ViewsVB-66](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-66.html)
- **Archicad: atualização.** Quando a vista de origem muda, é preciso mandar reconstruir o detalhe a
  partir dela, à mão. — [AC30 050_ViewsVB-69](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-69.html)
- **Archicad: marcadores em comum.** Corte, fachada, elevação interna, folha de trabalho e detalhe têm
  o mesmo comportamento de marcador: trocar o tipo, copiar, achar os marcadores ligados, conferir os
  marcadores e excluir o de origem. — [Managing Markers (AC30)](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-78.html)
- **Revit: detalhe e vista 2D.** A vista de desenho 2D (drafting view) guarda detalhes que não dependem
  do modelo e não mostra nenhum elemento dele. É desenhada com as ferramentas 2D (linhas de detalhe,
  regiões preenchidas, componentes de detalhe, isolamento, cotas, símbolos, texto). As chamadas
  postas nela têm de ser "de referência". Ela pode ser arrastada para uma folha. — [About Drafting Views (Revit LT 2023)](https://help.autodesk.com/cloudhelp/2023/ENU/RevitLT-DocumentPresent/files/GUID-7B76A2EA-F1F4-484B-AA96-2E2E53B56E49.htm)
- **Revit: chamada que aponta para outra vista.** Ao criar uma chamada ou um corte de detalhe numa
  planta, corte ou elevação, a opção de referência faz o marcador apontar para uma vista de detalhe
  ou 2D que já existe, achada por busca. Detalhes de CAD trazidos para uma vista 2D funcionam
  assim. — [Reference a Drafting View (Revit LT 2023)](https://help.autodesk.com/cloudhelp/2023/ENU/RevitLT-DocumentPresent/files/GUID-1E1D0833-8F29-4A09-BFE6-EEE4CABD4831.htm)
- **Revit: vista de detalhe.** Uma vista de detalhe é feita do modelo, e uma vista 2D é usada quando o
  detalhe não precisa da geometria do modelo. Os elementos do modelo podem aparecer esmaecidos na
  chamada, para separá-los do que foi desenhado por cima. — [Workflow: Detailing (Revit LT 2023)](https://help.autodesk.com/cloudhelp/2023/ENU/RevitLT-DocumentPresent/files/GUID-32C1E570-E77D-443D-AC64-E6E84C87AB7F.htm); [Create a Detail View (Revit LT 2023)](https://help.autodesk.com/cloudhelp/2023/ENU/RevitLT-DocumentPresent/files/GUID-34B3A4F2-8D79-4475-8AFD-D8C108F30130.htm) (via resultado de busca)
- **Dor relatada (Revit):** quem vem do CAD acha o detalhamento desajeitado e as vistas desconectadas
  umas das outras. — já registrado em `revit_documentacao_colaboracao.md` §1.

### Inferências
- O ponto fraco do Archicad é o detalhe "explodido" com reconstrução manual, e o próprio help
  admite que a cópia vem suja. O ponto forte do Revit é o detalhe continuar sendo vista do modelo
  (vivo). O melhor dos dois para o BrasBim é um detalhe **vivo**, que redesenha a origem recortada
  pelo contorno na escala do detalhe e recebe anotação 2D por cima, com uma ação explícita para
  "congelar em linhas" quando o usuário quiser editar os traços.
- O marcador que só aponta para outra vista (os dois programas têm) é necessário para detalhes
  padrão desenhados em 2D ou trazidos de DWG.

## 3. Folha de trabalho (vista 2D livre)

### Resumo
A folha de trabalho do Archicad e a vista de desenho 2D do Revit são o mesmo conceito: um espaço só
2D, com escala, para desenhos que não vêm do modelo (detalhes padrão, esquemas) ou para uma cópia
2D editável de parte do modelo.

### Achados citados
- **Archicad: propósito.** É uma janela 2D para desenhos baseados no modelo (planta ou corte parcial)
  ou feitos só em 2D (diagramas, organogramas), e serve bem para trabalhar com consultores que
  desenham em 2D. Os elementos do modelo entram como cópias 2D explodidas, e só as ferramentas 2D
  valem. Qualquer tipo de marcador pode ser ligado a uma folha de trabalho. Corte ou detalhe posto
  sobre uma folha de trabalho vira um desenho que não se atualiza pelo conteúdo dela. — [About Worksheets (AC28)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/050_ViewsVB/050_ViewsVB-72.htm)
- **Archicad: como se cria a partir do modelo.** Pode-se pegar a janela inteira com um clique (captura
  da tela) ou definir uma área por polígono ou retângulo; depois um clique põe o marcador. — [AC30 050_ViewsVB-73](https://help.graphisoft.com/AC/30/INT/Topics/050_ViewsVB/050_ViewsVB-73.html)
- **Archicad: detalhe padrão.** O caminho recomendado é criar uma folha de trabalho independente, pôr
  nela o desenho do detalhe e ligar um marcador de detalhe que aponta para o desenho na prancha. A
  comunidade avisa que juntar dados de outro arquivo traz camadas, tipos de linha e hachuras novos. — [Help Center, standard details](https://helpcenter.graphisoft.com/knowledgebase/25644/); [Graphisoft Community, "How to Use Standard Details in a Project"](https://community.graphisoft.com/t5/Documentation/How-to-Use-Standard-Details-in-a-Project/ta-p/303415) (via resultado de busca)
- **Archicad: diferença entre folha e detalhe, segundo usuários.** O detalhe exige contorno e a folha
  não. Os usuários não concordam sobre quando usar cada um. — [Graphisoft Community, "Difference between Worksheet and Detail Tool"](https://community.graphisoft.com/t5/Documentation/Difference-between-Worksheet-and-Detail-Tool/m-p/145445/highlight/true) (via resultado de busca; opinião, parte antiga)
- **Revit:** ver "vista de desenho 2D" no §2. Ela também pode receber um detalhe de CAD importado.

### Inferências
- Usuários confundem detalhe e folha de trabalho no Archicad. No BrasBim a separação pode ser
  simples: **Detalhe** é sempre vivo e vem do modelo; **Folha de trabalho** é sempre 2D livre, e
  pode nascer vazia, de um DWG importado ou de uma área do modelo congelada em linhas.

## 4. Câmera

### Resumo
No Archicad, a câmera é um ponto de vista em perspectiva posto na planta, com altura do olho e do
alvo, distância, ângulo de abertura e giro, organizado em percursos para animação. No Revit, a
câmera é posta na planta com dois cliques (olho e alvo). A vista 3D fica com o recorte e o campo de
visão ajustáveis, e a câmera reaparece na planta para ser arrastada.

### Achados citados
- **Archicad: parâmetros.** Para cada câmera há altura da câmera e do alvo (em relação ao zero do
  projeto), distância horizontal, azimute, ângulo do cone de visão e giro, além de posição do sol e
  pena. Os ajustes ficam numa paleta aberta junto com a planta, então dá para mexer na câmera sem
  fechar nada. — [Camera Tool Settings (AC29)](https://help.graphisoft.com/AC/29/INT/_AC29_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-42.htm)
- **Archicad: percursos e exibição.** As câmeras ficam em percursos (para o passeio animado), com
  movimento em polígono ou curva suave e quadros intermediários. Só uma câmera fica ativa por vez, e
  só ela mostra na planta o sol e o ângulo de visão. As câmeras nunca saem na impressão e não podem
  ser postas em camadas; para escondê-las na planta, a opção é a exibição "nenhuma". Projeções
  paralelas não aparecem na planta. — mesma fonte; [Camera Tool Settings (AC23)](https://help.graphisoft.com/AC/23/INT/_AC23_Help/140_UserInterfaceToolSettings/140_UserInterfaceToolSettings-43.htm) (via resultado de busca)
- **Revit: como se põe.** Abre-se uma planta, corte ou elevação, escolhe-se Câmera e clica-se o ponto
  do olho e depois o alvo. A vista criada recebe um nome sequencial. Sem a opção "perspectiva", a
  mesma ferramenta cria uma vista 3D ortogonal. — [Create a Perspective 3D View (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-BE8BAB99-53E3-4B8E-856A-20286FF8F8BB.htm); [Create an Orthographic 3D View (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-693A01C2-4EC2-440A-822C-DF5C11E50896.htm)
- **Revit: como se edita.** Um comando mostra a câmera, que aparece escolhida na planta, na elevação
  e em outras vistas. Arrasta-se o olho ou o alvo. As alturas do olho e do alvo também são
  propriedades da vista. O campo de visão muda pelas alças do recorte, e um comando devolve o alvo
  ao centro do recorte, porque o alvo pode sair do campo de visão durante a edição. — [Modify the Camera Position in a 3D View (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-DA6290AF-BE0B-43C5-9759-A874BAB5447B.htm); [Work in a 3D View (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-32B9E3E8-75C3-466D-A0E7-A8F377A851ED.htm)

### Inferências
- Os dois cliques do Revit (olho, alvo) e as alturas como campos numéricos são o caminho mais
  direto. Dos dois programas, o BrasBim fica com o melhor: a câmera visível na planta só na tela
  (Archicad), editável por alças na planta, e o 3D acompanhando ao vivo enquanto se arrasta.
- Percurso e animação podem esperar uma versão futura.
- O alvo que "escapa" do recorte no Revit é uma dor que o BrasBim evita guardando olho e alvo, e não
  um recorte.

## 5. Polilinha

### Resumo
As duas famílias de programa têm uma linha única feita de trechos retos e em arco. O AutoCAD tem as
opções mais completas na criação (arco tangente, por três pontos, por ângulo, centro, raio). O
Archicad tem continuar a partir da ponta, unir peças soltas, abrir e cortar com um clique, e
arredondar cantos.

### Achados citados
- **AutoCAD: criação.** Um único objeto 2D de trechos retos e em arco. Uma opção passa para arcos
  (tangentes ao trecho anterior por padrão) e outra volta às retas. O arco pode ser definido pela
  ponta final, pelo ângulo, pelo centro, pela direção, pelo raio ou por um segundo ponto (três
  pontos). Há também fechar, desfazer o último trecho, largura e meia largura, e um trecho de
  comprimento dado na direção do anterior. — [PLINE (AutoCAD 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Core/files/GUID-11883C70-6435-4F80-8FB4-F6E933B8FD94.htm)
- **AutoCAD: edição.** Linhas, arcos e polilinhas podem ser unidos numa polilinha só, e a polilinha
  escolhida tem opções próprias de edição e menu nas alças. — [To Join Polylines… (AutoCAD 2026)](https://help.autodesk.com/view/ACD/2026/ENU/?guid=GUID-19D69F56-9A1C-4277-AE9D-5C15DF27986F); [To Modify Polylines (AutoCAD 2026)](https://help.autodesk.com/view/ACD/2026/ENU/?guid=GUID-6242DF04-BD00-4A5D-891C-B131184D0D36) (via resultado de busca)
- **Archicad: criação.** As formas são polilinha, retângulo e retângulo girado. Cada clique termina
  um trecho e começa o seguinte; termina-se com OK ou clique duplo, e a tecla de apagar tira o último
  trecho. Para continuar uma polilinha que já existe, clica-se na ponta e escolhe-se continuar. —
  [Drawing Polylines and Chained Lines (AC28)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/070_Documentation/070_Documentation-23.htm)
- **Archicad: edição.** Há um comando que junta linhas, arcos e polilinhas que se tocam. Um clique com
  modificador num trecho abre a polilinha fechada ou a corta em duas. Explodir separa a polilinha
  em linhas soltas, e o padrão do tracejado pode correr pela polilinha toda ou recomeçar em cada
  trecho. — [Editing Polylines (AC28)](https://help.graphisoft.com/AC/28/INT/_AC28_Help/070_Documentation/070_Documentation-24.htm)
- **Archicad 24:** arredondar e chanfrar passaram a funcionar em polilinha, e a interseção passou a
  funcionar entre polilinhas e paredes, vigas e linhas. Na comunidade, arredondar um canto sem
  explodir aparece como dica. — [ARCHICAD 24 improves polyline editing](https://helpcenter.graphisoft.com/user-guide/127809); [Graphisoft Community, "what's the use of the polyline tool"](https://community.graphisoft.com/t5/Modeling/what-s-the-use-of-the-polyline-tool/td-p/39035) (via resultado de busca)

### Inferências
- O BrasBim já tem a linha em cadeia (`line2d`, lista de pontos). A polilinha com arcos é o mesmo
  elemento com um valor de curvatura por trecho, que é a forma usual de guardar arcos em polilinha
  (conhecimento geral do formato DXF). A exportação para DXF fica direta.
- O que funciona melhor e tem custo baixo: alternar reta/arco durante o desenho, curvar um trecho
  arrastando a alça do meio, arredondar um canto pelo menu do vértice, unir e separar.

## 6. Ponto de apoio ("hotspot")

### Resumo
No Archicad, o hotspot é um ponto marcado por uma cruzinha, que serve de apoio para a atração do
cursor e não sai na impressão. No AutoCAD, o equivalente é o objeto ponto, cuja aparência é
configurável. A atração "nó" pega pontos, e dividir/medir pontos ao longo de um objeto é um uso
típico.

### Achados citados
- **Archicad:** os hotspots são apoios de desenho que marcam nós importantes. Aparecem como uma pequena
  cruz, ajudam a posicionar elementos nas vistas 2D, não saem na impressão nem na plotagem e podem
  ser apagados quando não servem mais. Basta ativar a ferramenta e clicar. Há maneiras de pôr o ponto
  em relação a outro elemento, como o pé da perpendicular sobre uma parede, laje, linha ou borda de
  hachura. — [Help Center, hotspots](https://helpcenter.graphisoft.com/?p=55985); [Hotspot Tool Settings (AC21)](https://help.graphisoft.com/AC/21/INT/AC21Help/Appendix_Tools/Appendix_Tools-85.htm) (via resultado de busca; a página do Help Center redirecionou no fetch)
- **Archicad: usos relatados.** Os hotspots servem para apagar todos de uma vez escolhendo-os pelo tipo,
  como apoio no editor de perfis e como pontos de atração em objetos de biblioteca. — [Graphisoft Community, "Anyone using Hotspots?"](https://community.graphisoft.com/t5/Modeling/Anyone-using-Hotspots/m-p/113530/highlight/true); [Graphisoft Community, "Hotspots"](https://community.graphisoft.com/t5/Modeling/Hotspots/m-p/9255) (via resultado de busca)
- **AutoCAD:** o comando ponto cria um ponto, e um estilo de ponto (forma e tamanho, guardado no
  desenho) define como todos aparecem. Um uso conhecido é dividir ou medir pontos ao longo de um
  objeto. — [POINT (AutoCAD 2026)](https://help.autodesk.com/view/ACD/2026/ENU/?guid=GUID-3F5861A1-9A63-42A6-8F12-3395771BAA6D); [Point Style Dialog Box (AutoCAD 2026)](https://help.autodesk.com/view/ACD/2026/ENU/?guid=GUID-48AD2AE9-1EDE-4BF1-B3FA-F5B15225189E); [Have You Tried: Divide and Measure (AutoCAD 2026)](https://help.autodesk.com/view/ACD/2026/ENU/?guid=GUID-1823FF63-6952-47DD-89F8-29E4AA5B2582) (via resultado de busca)
- **IFC 4.3:** `IfcAnnotationTypeEnum` tem o valor `ASSUMEDPOINT`. Conferido na definição do esquema
  IFC4X3 que vem com o IfcOpenShell instalado (`ifcopenshell/express/rules/IFC4X3.py`, biblioteca
  LGPL; ver `cleanroom/FONTES.md`).

### Inferências
- O nome "hotspot" é do Archicad. No BrasBim, o nome próprio sugerido é **Ponto de apoio**.
- O que vale a pena: pôr com clique, a atração do cursor pegar o ponto, não imprimir por padrão,
  dividir um elemento em N partes iguais e apagar todos os pontos de uma vez.

## 7. Figura (imagem)

### Resumo
No Archicad, a figura é uma imagem embutida no arquivo do projeto, posta em qualquer vista 2D ou
prancha. Tem tamanho, resolução, transparência, giro e espelho, mas não tem número nem título e
não se atualiza. No AutoCAD e no Revit, a imagem é vinculada a um arquivo de fora (AutoCAD) ou
importada (Revit). O AutoCAD tem recorte, brilho, contraste, esmaecer e transparência.

### Achados citados
- **Archicad: figura.** A figura é uma imagem embutida no projeto, que entra em qualquer janela 2D
  (planta, corte, fachada, elevação interna, documento 3D, detalhe, folha de trabalho, prancha). Vem
  de um arquivo ou da área de transferência (colar uma imagem cria uma figura). Tem largura e altura,
  com ou sem manter a proporção, e resolução em ppi ligada ao tamanho. Há também transparência dos
  pixels brancos, espelho, giro relativo à vista ou absoluto, ponto de inserção (um de nove) e
  exportar uma cópia. Antes do clique, um contorno acompanha o cursor e se prende a nós e bordas. — [Figure (AC25, FRA)](https://help.graphisoft.com/AC/25/FRA/_AC25_Help/070_Documentation/070_Documentation-34.htm); [Figure Tool Settings (AC25, FRA)](https://help.graphisoft.com/AC/25/FRA/_AC25_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-41.htm)
- **Archicad: limitações.** Imagens embutidas aumentam muito o arquivo, e o help pede controle de
  tamanho e resolução. A figura não tem número nem título, não se atualiza a partir do arquivo e não
  aceita moldura de desenho. Uma figura pode servir de fundo para alinhar a vista. — mesmas fontes
- **Archicad: figura ou desenho, segundo usuários.** A figura estica em X e Y separadamente e tem
  transparência; o desenho trava a proporção. Um moderador não vê muito motivo para usar a figura
  além disso. — [Graphisoft Community, "Comparison of the Drawing and Figure Tools"](https://community.graphisoft.com/t5/Documentation/Comparison-of-the-Drawing-and-Figure-Tools/m-p/116011/highlight/true); [Graphisoft Community, "Figure Tool"](https://community.graphisoft.com/t5/Modeling/Figure-Tool/td-p/288761) (via resultado de busca)
- **AutoCAD: imagem vinculada.** O arquivo de imagem é vinculado como referência e atualizado ao abrir o
  desenho ou recarregar. Um quadro define o ponto de inserção, a escala e o giro. Na aba da imagem há
  brilho, contraste, esmaecer, recorte por contorno (e tirar o recorte), mostrar/ocultar e
  transparência. — [IMAGEATTACH (AutoCAD 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Core/files/GUID-0F75E36F-6138-424C-9510-5847CE1D8852.htm); [Image Ribbon Contextual Tab (AutoCAD 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Core/files/GUID-1F3E2CF5-3D96-4601-B9C3-73C550ED7A93.htm)
- **Revit: imagem.** Aceita BMP, JPEG, PNG, PDF e TIFF. A imagem é posta com um clique, movida
  arrastando e redimensionada pela alça do canto ou pelos campos de altura e largura. Pode ir para a
  folha ou para vistas do modelo. — [Add an Image to a Sheet (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-2044CD19-CBB7-4F7A-B9CF-A38FDB6C0950.htm); [Revit 2026 help, busca "image"](https://help.autodesk.com/view/RVT/2026/ENU/?query=image) (via resultado de busca)

### Inferências
- Para o BrasBim IFC-nativo, a imagem embutida no próprio IFC (textura binária) mantém o projeto num
  arquivo só, e é o caso do Archicad. O cuidado com o tamanho vira um aviso e uma opção de reduzir.
- O que nenhum dos três faz direto na ferramenta, e serve no Brasil (planta escaneada, levantamento
  em papel, foto aérea do lote), é **calibrar a escala clicando dois pontos da imagem e digitando a
  distância real**.

## 8. Desenho (pôr desenho na prancha)

### Resumo
No Archicad, a ferramenta Desenho põe arquivos de fora (DWG, DXF, DWF, PDF, imagem) num vínculo
atualizável, em vistas do modelo ou na prancha, com número, título, moldura e recorte. As vistas do
próprio projeto vão para a prancha por arrasto a partir do navegador. No Revit, as vistas vão para a
folha por arrasto ou pelo comando de pôr vista, e cada vista só pode estar numa folha.

### Achados citados
- **Archicad: o que põe.** A ferramenta põe um arquivo externo (DWG, DXF, DWF, PDF ou imagem) e guarda o
  vínculo com ele, que pode ser atualizado; é isso que a diferencia da figura. Vai para qualquer
  vista, menos o 3D e as tabelas. PDF de várias páginas abre a escolha da página. — [Drawing (AC25, FRA)](https://help.graphisoft.com/AC/25/FRA/_AC25_Help/070_Documentation/070_Documentation-35.htm)
- **Archicad: ajustes.** O número do desenho segue a prancha, a vista ou um valor próprio. O nome vem
  da vista, de um texto próprio ou do caminho do arquivo. A atualização é automática (ao abrir a
  prancha) ou manual, e o desenho de atualização manual fica guardado no projeto. A escala só existe
  na prancha. Há ainda giro, conjunto de penas, cores (tons de cinza ou preto e branco), fundo
  transparente, camadas do arquivo de origem (que podem ser escondidas), qualidade da prévia,
  moldura com recorte e título com estilo (só na prancha). — [Drawing Tool Settings (AC25, FRA)](https://help.graphisoft.com/AC/25/FRA/_AC25_Help/150_UserInterfaceToolSettings/150_UserInterfaceToolSettings-28.htm)
- **Archicad: limitações.** Na vista do modelo, o desenho não tem título nem número e não depende da
  escala. Quando o arquivo muda e o desenho é atualizado, aparecem as camadas novas e somem as
  apagadas. — mesmas fontes
- **Archicad: usos relatados.** O desenho tem número e título, que a figura não tem. Pode ser recortado
  e ter moldura, e a atualização pode ser automática ou manual. — [Graphisoft Community, "What is the difference between the Figure & Drawing tools"](https://community.graphisoft.com/t5/Documentation/What-is-the-difference-between-the-Figure-amp-Drawing-tools/td-p/115059/page/2) (via resultado de busca)
- **Revit: vista na folha.** A vista entra na folha arrastada do navegador ou pelo comando de pôr vista.
  Ela segue o cursor até o clique, e há alinhamento entre vistas e atração à folha. O título é
  editado com clique duplo, e o tipo da janela de vista pode esconder o título ou mudar a linha
  dele. A vista gira 90° e pode ser travada. **Cada vista só entra numa folha**; para repetir, é
  preciso duplicá-la. Legendas e tabelas podem entrar em várias folhas. — [Add Views to a Sheet (Revit 2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-D3E7FDC3-57AB-4497-AB87-D195476254C2.htm)

### Inferências
- No BrasBim, pôr vista na prancha já existe por arrasto e por menu (spec/ui 25 §5). O que falta é
  uma **ferramenta** na barra que faça as duas coisas no mesmo gesto, vista do projeto ou arquivo de
  fora, com número do desenho e título automáticos. O número na prancha é o que permite ao marcador
  de detalhe e de elevação interna mostrar "nº / prancha" sozinho.
- A regra "uma vista, uma folha" do Revit é uma limitação conhecida. O BrasBim já permite a mesma
  vista salva em várias pranchas (spec/ui 25 §5). A referência do marcador aponta para a primeira
  prancha, e o usuário pode escolher outra.

## Lacunas
- O detalhe e a folha de trabalho do Archicad foram lidos no AC30. Não abri as páginas sobre o
  marcador ligado (AC30 050_ViewsVB-65/-77) nem os quadros de ajuste completos dessas ferramentas.
- O hotspot do Archicad vem de resumos da busca e de uma página do AC21 que não foi aberta inteira.
- Os ajustes de figura e desenho foram lidos no help francês do AC25; o comportamento atual pode
  ser diferente.
- No Revit, não achei a página que diz se a câmera continua visível na planta depois de criada. Pelo
  passo "mostrar a câmera", ela parece ficar escondida.
- AutoCAD: a atração "nó" e as opções de moldura da imagem não foram confirmadas em página da Ajuda.
- **NBR 6492** (símbolos de chamada de detalhe e de elevação): o texto da norma não foi lido. As
  convenções de marcador usadas nas specs são conhecimento geral (CG).
