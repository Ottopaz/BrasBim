---
documento: Vistas — elevação interna, detalhe, folha de trabalho e câmera
requisito: spec/ui 34 §4 (grupo Vistas); RF-DOC-12, RF-DOC-14
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-29
status: aprovada (pontos de revisão como propostos)
revisor: OTTO ("ok" em 2026-10-29)
---

# Vistas: elevação interna, detalhe, folha de trabalho e câmera

## 1. Propósito
Completar o grupo **Vistas** da barra Ferramentas (spec/ui 34 §3), que hoje tem só Corte e
Fachada, com quatro ferramentas:

| Ferramenta | Para quê |
|---|---|
| **Elevação interna** | as paredes de um ambiente vistas de dentro (cozinha, banheiro), uma vista por parede |
| **Detalhe** | um pedaço de uma vista ampliado noutra escala, com anotação própria |
| **Folha de trabalho** | uma vista só 2D, com escala, para desenho livre (detalhe padrão, esquema, DWG de consultor) |
| **Câmera** | uma perspectiva posta na planta (olho e alvo), aberta no 3D e levada à prancha |

A base é a pesquisa complementar
(`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`,
§1–§4). Em cada ponto a spec diz o que fazemos **melhor** que os outros programas.

Fica de fora: percurso de câmera e animação, render, marcador de corte com degrau,
chamada de detalhe em vista 3D.

## 2. O que já existe e é reaproveitado
- Vista de corte e de fachada: `IfcAnnotation` na edificação, Pset `BrasBim_Vista` com o
  estado em JSON, operações `view.create/.edit/.delete`, desenho calculado por
  `core/drawings/section.py` e refeito quando o modelo muda (spec/ui 14).
- Vistas salvas, pôr na prancha (vivo, com recorte e moldura), lista no painel Projeto
  (spec/ui 25, 29).
- Câmera do 3D: órbita (alvo, distância, giro, inclinação), ângulo de visão fixo de 45°
  (`ui/scene3d.Camera`).
- Anotações 2D (`core/annotations`), hoje sempre contidas num pavimento.

## 3. Elevação interna

### 3.1 Criação
1. Ferramenta **Elevação interna** (grupo Vistas). Barra Opções: **Forma** = *Ambiente*
   (padrão) | *Retângulo* | *Polígono*; **Paredes** = *Todas* | *Escolher*.
2. *Ambiente:* um clique dentro de um ambiente (`IfcSpace`) pega o contorno dele. Sem
   ambiente sob o cursor, a dica pede o retângulo. *Retângulo/Polígono:* desenha-se o
   contorno como no ambiente.
3. A pré‑visualização mostra o contorno grosso e uma seta por lado, apontando para fora.
   Lados com menos de 30 cm são ignorados *(decisão do projeto: recuos de pilar e de
   batente não viram vista)*.
4. Com *Escolher*, um clique numa seta liga ou desliga aquele lado; Enter confirma.
   *(Tirado do Revit: escolher as direções no próprio marcador. Melhor que os dois: o
   contorno vem do ambiente com um clique, sem desenhar.)*
5. Um último clique põe o **marcador**. O padrão é o centro do ambiente, e a pré‑visualização
   acompanha o cursor.

Uma transação "Criar elevação interna" cria um **grupo** com uma vista por lado.

### 3.2 Nome e número *(decisão do projeto)*
- O grupo recebe o próximo número livre (1, 2…). As vistas recebem a letra do lado,
  começando pelo lado mais ao norte do projeto e seguindo no sentido horário: "1A",
  "1B"…
- Nome: "<nome do ambiente> — A" (ex.: "Cozinha — A"); sem ambiente: "Elevação interna
  1A". Renomear muda só a vista.

### 3.3 O que a vista mostra
Cada vista é desenhada pelo mesmo caminho do corte (spec/ui 14 §4), com:
- **Lado** = o segmento do contorno (A→B), olhando **para fora** do ambiente.
- **Plano de corte** paralelo ao lado, do lado de dentro, à distância **alcance**. O padrão
  é a maior distância do lado ao contorno, menos 1 cm, e o valor pode ser mudado. O que o
  plano corta (laje do piso, forro, viga) aparece cortado.
- **Alcance horizontal:** *Limitado* (padrão) recorta o desenho entre as pontas do lado e
  até a face de fora da parede que está nele (ou 30 cm além do lado, quando não há
  parede). *Ilimitado* mostra tudo o que se vê dali.
- **Alcance vertical:** do nível do pavimento até a altura do ambiente (o pé‑direito do
  `IfcSpace`). Sem ambiente, vai até o pavimento de cima. Pode ser mudado à mão em cada
  vista.
- **Contorno do ambiente:** retângulo grosso (0,5 mm) do recorte, piso a forro *(CG)*.
- **Título** embaixo, como no corte: "ELEVAÇÃO 1A — COZINHA" e a escala.
- Escala padrão **1:25** *(CG; usual em elevação interna)*.
- Mobiliário e objetos (`IfcFurniture`, `IfcSanitaryTerminal`…) aparecem, como no corte.
- Atualização **viva**, igual ao corte. *(Melhor que o Archicad, que pede "reconstruir"
  e, segundo relatos, às vezes não mostra nada: aqui o recorte vem do ambiente e o
  limite fica visível na planta.)*
- Se o ambiente muda de contorno, o grupo **não** se refaz sozinho. A vista mostra um aviso
  discreto no título da aba ("contorno mudou") e oferece **Refazer pelo ambiente** no botão
  direito do marcador. *(Decisão do projeto: refazer sozinho mudaria as letras das vistas
  já postas em prancha.)*

### 3.4 Marcador na planta *(CG)*
- Um círculo de 10 mm (papel) com o número do grupo, e um triângulo cheio encostado nele
  para cada vista, apontando para o lado. Dentro ou junto de cada triângulo fica a letra.
  Quando a vista está numa prancha, o círculo é dividido: em cima o número, embaixo o
  número da prancha (ver §4.4).
- O contorno do grupo aparece na tela em traço fino cinza tracejado. Ele não sai no
  papel e pode ser ligado ou desligado em **Exibir > Limites das vistas**.
- Aparece só no pavimento do grupo.
- Escolher o marcador escolhe o grupo. Mover, Girar e Excluir valem para o grupo; Mover só
  o marcador fica na alça do centro.
- Botão direito: **Abrir ▸** (as vistas), **Refazer pelo ambiente**, **Ligar/desligar
  lados…**.

### 3.5 IFC
- Cada vista é um `IfcAnnotation` com `ObjectType` "VistaInterna", **contido no
  pavimento**, com o estado em `BrasBim_Vista` (`kind` "interior"). Ao estado do corte
  (spec/ui 14 §2) somam‑se: `group` (número), `space` (GlobalId do `IfcSpace` ou nulo),
  `outline` (contorno do grupo, para o símbolo), `marker` (ponto), `reach` (alcance),
  `limited` (sim/não).
- A representação `Annotation` da vista é a seta dela, e o círculo vai junto na vista de
  menor letra. Quem abre o IFC em outro programa vê o marcador.
- Operações: as mesmas `view.*`. Excluir o grupo é uma transação com um `view.delete` por
  vista.

## 4. Detalhe

### 4.1 Criação
1. Ferramenta **Detalhe** (grupo Vistas). Vale na planta, no corte, na fachada, na
   elevação interna e na folha de trabalho.
2. Barra Opções: **Forma** = *Retângulo* (padrão) | *Polígono* | *Círculo*; **Ação** =
   *Nova vista* (padrão) | *Apontar para vista existente ▸* (lista de detalhes, folhas de
   trabalho e vistas salvas); **Escala** do detalhe (padrão: a metade da escala da origem
   arredondada para a série 1:1, 1:2, 1:5, 1:10, 1:20, 1:25; 1:50 → 1:20).
3. Desenha‑se o contorno e um clique põe o marcador (com linha de chamada até o contorno,
   se o marcador fica fora dele).

### 4.2 O que a vista mostra
- O **desenho da origem**, recortado pelo contorno e **redesenhado na escala do detalhe**.
  O nível de detalhe é sempre "por camadas" (spec/ui 06). As espessuras vêm da tabela de
  penas no papel, e textos e símbolos automáticos ficam no tamanho do papel.
- **Vivo:** muda quando o modelo muda, como o corte. *(Melhor que o Archicad, cujo detalhe
  é uma cópia 2D "explodida", com traços demais, que só se atualiza por comando manual.
  Mesmo comportamento da chamada do Revit.)*
- As anotações 2D da origem **não** entram por padrão. A opção **Trazer anotações da
  origem** mostra cotas e textos da origem que caem no contorno.
- **Anotação própria:** a aba do detalhe aceita as ferramentas de documentação (cota,
  texto, rótulo, hachura, linha, polilinha, círculo, arco, curva, ponto de apoio, figura).
  O que se desenha ali pertence ao detalhe (§6).
- O contorno vira a borda do desenho: linha fina com recorte limpo *(CG)*.
- Título: "DETALHE 3" e a escala.
- **Congelar em linhas** (botão direito no detalhe): cria uma **folha de trabalho** com o
  desenho atual convertido em linhas e hachuras 2D, mais as anotações do detalhe, e
  passa o marcador a apontar para ela. Pede confirmação, e desfazer desfaz. *(É a saída
  para quem quer mexer nos traços sem perder o detalhe vivo por acidente.)*

### 4.3 Marcador *(CG)*
- Na origem: o contorno em traço fino e um círculo de 10 mm com o número do detalhe. Se a
  vista apontada está numa prancha, o círculo é dividido, com o número do desenho em cima e
  o da prancha embaixo (§4.4).
- Alças: os vértices do contorno e o marcador. Mudar o contorno muda o detalhe.
- *Apontar para vista existente* põe só o marcador (com ou sem contorno), sem criar
  vista. *(Os dois programas têm. É o caminho dos detalhes padrão e dos DWG trazidos de
  fora.)*

### 4.4 Referência "número / prancha"
- O número de baixo do marcador é o da prancha onde está a vista apontada. O de cima é o
  número do desenho nessa prancha (spec/ui 36 §5.3); enquanto o desenho não tem número,
  vale o número do detalhe.
- Se a vista está em várias pranchas (permitido, spec/ui 25 §5), vale a **primeira** pela
  ordem das pranchas, e o painel do marcador deixa escolher outra. *(O Revit não deixa a
  vista em mais de uma folha; aqui ela pode estar em várias, e o marcador continua
  sabendo para onde apontar.)*
- Fora de prancha: só o número, o círculo inteiro.
- Vale também para a elevação interna (§3.4).

### 4.5 IFC
- `IfcAnnotation` com `ObjectType` "VistaDeDetalhe", contido na **edificação**, estado em
  `BrasBim_Vista` (`kind` "detail"): `name`, `number`, `source` (GlobalId da vista de
  origem ou do pavimento), `outline` (nas coordenadas da origem), `shape`, `marker`,
  `scale`, `source_notes` (sim/não), `target` (GlobalId apontado quando o marcador só
  aponta; nulo quando é a própria vista).
- A representação `Annotation` é o contorno e o marcador, nas coordenadas da planta quando
  a origem é um pavimento. Quando a origem é um corte, a representação fica vazia e o
  símbolo é desenhado pelo BrasBim *(decisão do projeto: o IFC não tem o sistema de
  coordenadas do corte)*.

## 5. Folha de trabalho

### 5.1 Criação
- **Projeto > Nova folha de trabalho** ou o botão **+** na lista de vistas: cria uma folha
  vazia com nome ("Folha de trabalho 1") e escala (padrão 1:20).
- Ferramenta **Folha de trabalho** (grupo Vistas), na planta ou num corte: desenha‑se um
  retângulo ou um polígono, e o desenho que está dentro é **copiado em linhas e hachuras
  2D** para uma folha nova, na escala da origem. Um clique põe o marcador (opcional: na
  barra Opções, **Marcador** = *Sim* | *Não*). As linhas repetidas são unidas e as
  sobrepostas são retiradas, antes de gravar. *(O próprio help do Archicad manda fazer
  essa limpeza à mão; aqui ela é automática.)*
- **Importar desenho…** (Arquivo, ou o botão direito na folha) traz um DWG/DXF para dentro
  da folha, pelo mesmo caminho da spec/ui 22. *(Equivale às vistas 2D com CAD
  importado do Revit.)*

### 5.2 O que é
- Só 2D: valem as ferramentas de documentação e de desenho 2D. As de modelagem ficam
  apagadas na barra enquanto a aba da folha está à frente.
- Não depende do modelo. Uma folha que nasceu de uma área do modelo **não** se atualiza
  *(é o que separa folha de detalhe: o detalhe é sempre vivo, a folha nunca)*.
- Abre em aba própria, com zoom, deslocamento, escala na barra de estado, camadas e
  atração como na planta.
- Vai para a prancha como as outras vistas (spec/ui 25 §5; spec/ui 36 §5).

### 5.3 IFC
- `IfcAnnotation` com `ObjectType` "FolhaDeTrabalho", contido na edificação, estado em
  `BrasBim_Vista` (`kind` "worksheet"): `name`, `number`, `scale`, `marker` (ponto e
  vista onde está, ou nulo), `outline`, `source` (de onde veio, só informação).
- As linhas, os textos, as cotas etc. são anotações 2D da folha (§6).

## 6. Anotações que pertencem a uma vista *(decisão do projeto)*
Hoje toda anotação é contida num pavimento. As anotações de detalhe e de folha de trabalho
passam a pertencer à **vista**:
- No estado da anotação (`BrasBim_Anotacao`), `storey` dá lugar a `view` (GlobalId da
  vista). A anotação fica contida na edificação, e a vista a **agrega**
  (`IfcRelAggregates`, vista → anotações), assim quem abre o IFC vê o que é de cada
  detalhe.
- As coordenadas ficam no sistema da vista (*u*, *v* em metros do modelo; na folha de
  trabalho, x e y do papel ÷ escala). Os tamanhos em mm de papel usam a escala da vista em
  vez da do pavimento (`storeys.paper` ganha a escala como parâmetro).
- Excluir a vista exclui as anotações dela na mesma transação.
- Camadas: valem as mesmas (spec/ui 18).

## 7. Câmera

### 7.1 Criação
1. Ferramenta **Câmera** (grupo Vistas), na planta. Barra Opções: **Altura do olho** (padrão
   1,60 m acima do pavimento), **Altura do alvo** (padrão igual à do olho), **Abertura**
   (ângulo de visão horizontal; padrão 60°, de 20° a 120°).
2. Clique no **olho**, depois no **alvo**. A pré‑visualização mostra o cone de visão na
   planta. *(Mesmos dois cliques do Revit.)*
3. Nasce "Câmera 1" (próximo número livre) e a aba 3D **não** muda sozinha.

### 7.2 Na planta
- O símbolo é um pequeno corpo de câmera no olho, as duas linhas do cone e um ponto no
  alvo, em traço fino. Aparece **só na tela**, nunca no papel nem no PDF *(como no
  Archicad)*. Aparece no pavimento onde foi posta.
- **Exibir > Câmeras**: liga ou desliga todas. As câmeras também podem ir para uma camada,
  ao contrário do Archicad, onde a única forma de escondê‑las é a exibição "nenhuma".
- Alças: olho, alvo e as duas pontas do cone (mudam a abertura). **Arrastar uma alça com
  a câmera aberta no 3D move o 3D junto, ao vivo.** *(Melhor que o Revit, onde a câmera
  só aparece na planta depois do comando "mostrar câmera".)*

### 7.3 Abrir e atualizar
- Clique duplo na câmera (na planta ou na lista de vistas): a aba 3D vai para a câmera, com
  a abertura dela. O 3D passa a usar o ângulo de visão da câmera; hoje é fixo em 45°.
- Navegar no 3D depois **não** muda a câmera. Para gravar a posição nova, usa‑se **Gravar
  na câmera** (botão direito na câmera ou na aba 3D, enquanto ela veio de uma câmera).
  *(Decisão do projeto: girar o 3D para olhar outra coisa não estraga a perspectiva já
  posta em prancha.)*
- **Nova câmera daqui** (aba 3D, botão direito): cria uma câmera na posição atual do 3D.
- Não há câmera ortogonal: o 3D do BrasBim é sempre em perspectiva.

### 7.4 Na prancha
Entra como a vista 3D salva (spec/ui 25 §5): imagem do 3D gerada ao desenhar a prancha e
ao exportar o PDF, com largura no papel e proporção guardadas na câmera (padrão 160 mm,
proporção 3:2).

### 7.5 IFC
- `IfcAnnotation` com `ObjectType` "Camera", contido no **pavimento**, estado em
  `BrasBim_Vista` (`kind` "camera"): `name`, `eye` [x, y, z], `target` [x, y, z]
  (z absoluto), `fov` (graus), `aspect`, `width` (mm no papel).
- A representação `Annotation` é o símbolo da planta. Ela fica numa camada que não é
  impressa *(o IFC não tem entidade de câmera)*.

## 8. Painel Projeto e paleta
- A aba "Cortes e fachadas" passa a se chamar **Vistas**, com grupos recolhíveis na
  ordem Cortes, Fachadas, Elevações internas (por grupo), Detalhes, Folhas de trabalho e
  Câmeras. Clique duplo abre, e o botão direito tem Abrir, Renomear, Pôr na prancha ▸ e
  Excluir.
- Paleta de comandos e linha de comando: as quatro ferramentas no grupo Vistas, mais "Nova
  folha de trabalho".
- Ícones: símbolos planos, como as outras ferramentas de vista (spec/ui 34 §2).
  *Elevação interna:* um quadrado com quatro triângulos para fora. *Detalhe:* um círculo
  com linha de chamada para um retângulo tracejado. *Folha de trabalho:* uma folha com um
  traço. *Câmera:* um corpo de câmera com o cone.

## 9. Critérios de aceite (testes)
| Id | Teste |
|---|---|
| VI01 | Elevação interna num ambiente retangular 4×3 m cria um grupo com 4 vistas "1A"–"1D", contidas no pavimento, com `kind` "interior" e `space` do ambiente |
| VI02 | Lado com menos de 30 cm não vira vista; *Escolher* desligando 2 setas cria 2 vistas |
| VI03 | O desenho da vista 1A mostra a parede do lado e um armário encostado nela, e não mostra a parede do ambiente vizinho (alcance limitado); com *Ilimitado* mostra |
| VI04 | O alcance vertical vai do pavimento ao pé‑direito do ambiente; laje do piso e do forro aparecem cortadas |
| VI05 | Mover um objeto dentro do ambiente muda o desenho da vista aberta (vivo) |
| VI06 | Excluir o marcador exclui o grupo inteiro numa transação; desfazer volta as 4 vistas |
| DT01 | Detalhe 1:20 numa planta 1:50: o desenho só tem o que cai no contorno, e o texto automático tem o mesmo tamanho no papel |
| DT02 | Mudar a parede de origem muda o detalhe (vivo) |
| DT03 | Uma cota posta no detalhe fica com `view` = o detalhe, é agregada por ele no IFC e some ao excluir o detalhe |
| DT04 | Marcador "Apontar para vista existente" não cria vista; com a vista apontada na prancha 03 como desenho 2, o marcador mostra "2" e "03" |
| DT05 | Congelar em linhas cria uma folha de trabalho com as linhas e passa o marcador para ela; desfazer volta ao detalhe vivo |
| FT01 | Nova folha de trabalho vazia: aceita linha, texto e cota; a ferramenta Parede fica apagada |
| FT02 | Folha a partir de uma área da planta: as linhas copiadas não mudam quando a parede muda depois |
| FT03 | Linhas sobrepostas da origem viram uma só na folha |
| CA01 | Câmera por dois cliques grava `eye` e `target` com as alturas da barra Opções, contida no pavimento |
| CA02 | Abrir a câmera põe o 3D no olho e no alvo com o ângulo da câmera; navegar não muda a câmera; Gravar na câmera muda |
| CA03 | O símbolo da câmera não sai no PDF da planta |
| CA04 | Câmera na prancha sai como imagem com a largura gravada |
| UI.. | Painel Vistas com os grupos; ferramentas no grupo Vistas da barra e na paleta |

## 10. Fontes
- Pesquisa complementar (2026‑10‑29):
  `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_vistas_e_documentacao.md`
  §1 (elevação interna: Archicad AC27 050_ViewsVB‑48 a ‑55; Revit 2024 "About/Create
  Elevation Views"), §2 (detalhe: Archicad AC30 050_ViewsVB‑62 a ‑69; Revit LT 2023
  drafting/callout), §3 (folha de trabalho: Archicad AC28/AC30), §4 (câmera: Archicad AC29
  Camera Tool Settings; Revit 2024 perspective/camera).
- IFC 4.3: `IfcAnnotation`, `IfcRelAggregates`, `IfcRelContainedInSpatialStructure`
  [IFC-ANNOT].
- **NBR 6492**: símbolos de chamada de detalhe e de elevação. **Texto não lido.** Os
  marcadores seguem convenções usuais (CG) e serão conferidos quando a norma for lida.
- CG: escala usual 1:25 de elevação interna; círculo dividido "número / prancha".
- Nada de `_restrito/`. Os nomes das ferramentas são nossos ("Folha de trabalho" e
  "Elevação interna" são termos correntes em pt‑BR; "Detalhe" e "Câmera", palavras comuns).

## 11. Pontos de revisão
(a) Elevação interna: letras a partir do lado mais ao norte, no sentido horário; escala
padrão 1:25 (§3.2–§3.3).
(b) O grupo não se refaz sozinho quando o ambiente muda; fica o aviso e a opção "Refazer
pelo ambiente" (§3.3).
(c) Detalhe sempre vivo; "Congelar em linhas" leva a uma folha de trabalho (§4.2).
(d) Anotações de detalhe e folha pertencem à vista, agregadas por ela no IFC (§6).
(e) Câmera: navegar no 3D não muda a câmera; grava‑se com "Gravar na câmera" (§7.3).
(f) Câmera com abertura padrão de 60° e o 3D passando a aceitar ângulo variável (§7.1, §7.3).
(g) Painel "Cortes e fachadas" renomeado para "Vistas", com grupos (§8).
(h) Ordem de implementação proposta: Câmera → Elevação interna → Folha de trabalho →
Detalhe (o detalhe depende das anotações por vista, §6, que a folha estreia).
