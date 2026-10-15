---
documento: Interface — campos de medida ao desenhar (Tab), seleção e edição na vista 3D, mostrar a seleção na outra vista
requisito: RF-NUC-04, RF-NUC-05, RF-UI-03, RF-UI-04
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15, pontos (a)–(g) aceitos)
---

# Medidas ao desenhar e edição no 3D

## 1. Propósito
Três pedidos do revisor em 2026‑10‑15, feitos **antes** do pacote 2 (spec 06), que fica
para depois desta:

1. Ao desenhar, mostrar junto ao cursor a **medida e o ângulo**. **Tab** passa a digitar a
   medida; Tab de novo, o ângulo (§2).
2. **Selecionar, mover, copiar, girar e espelhar também na vista 3D** (§3).
3. Botão direito sobre a seleção: **Mostrar na planta** (no 3D) e **Mostrar no 3D** (na
   planta), para ver o mesmo elemento nas duas vistas (§4).

Nenhuma operação nova e nenhuma mudança no IFC: tudo continua gerando as operações que já
existem (`wall.create`, `wall.edit`, `opening.edit`, `door.edit`, `path_connection.*`…).

## 2. Campos de medida junto ao cursor

### 2.1 O que aparece
Enquanto uma ferramenta espera o próximo ponto, um pequeno quadro segue o cursor com os
**campos da ferramenta**. Cada campo mostra o valor que o cursor está dando agora (cinza)
ou um valor **fixado** (preto, com um cadeado).

| Ferramenta | Campos (na ordem do Tab) | Ângulo |
|---|---|---|
| Parede (reta), depois do 1º ponto | Comprimento, Ângulo | absoluto |
| Retângulo, depois do 1º canto | Largura (x), Altura (y) | — |
| Mover, Copiar, depois do ponto de base | Distância, Ângulo | absoluto |
| Girar, depois da direção de referência | Ângulo | relativo (o giro) |
| Espelhar, depois do 1º ponto | Ângulo do eixo | absoluto |
| Dividir, sobre a parede | Distância (ao início da parede) | — |
| Parede em arco | sem campos nesta etapa (ponto (f)) | — |

- Comprimentos em metros, com vírgula ou ponto, como hoje (`parse_number`).
- **Ângulo absoluto:** graus, 0° no eixo x do pavimento, positivo no sentido anti‑horário,
  como o campo Ângulo do painel (spec 05 §3). Mostrado entre −180° e 180°.
- O rótulo de medida que hoje aparece junto ao cursor (só o comprimento) passa a ser
  este quadro.
- O quadro aparece nas duas vistas (planta e 3D), onde estiver o cursor.

### 2.2 Teclado
1. **Tab** coloca o foco no **primeiro campo**, com o valor atual selecionado. Digitar
   substitui o valor.
2. **Tab** de novo **fixa** o valor digitado e passa ao próximo campo. Do último campo,
   volta ao primeiro. **Shift+Tab** volta um campo.
3. **Enter** fixa o campo em edição e **confirma o ponto**, como um clique. O que não foi
   fixado vem do cursor (com *snap* e Shift, como sempre).
4. **Esc** dentro do quadro solta todos os valores fixados e devolve o controle ao cursor.
   O próximo Esc age na ferramenta, como hoje.
5. Digitar um número **sem Tab** continua funcionando: abre o primeiro campo já com o
   algarismo. Assim, "3 Enter" faz uma parede de 3 m na direção do cursor, como hoje.
6. Campo apagado e Tab: o valor volta a acompanhar o cursor.
7. Depois de cada ponto confirmado, os valores fixados são soltos.

**Tab na ferramenta Porta** continua alternando as dobradiças (spec 01 §5.5): a porta não
tem campos.

### 2.3 Valor fixado e cursor
| Fixado | Ponto resultante |
|---|---|
| Comprimento | Na direção do cursor (já com *snap* e Shift), à distância fixada |
| Ângulo | Na direção fixada, à distância da **projeção** do cursor nessa direção |
| Os dois | Totalmente definido; mover o cursor não muda nada |
| Largura e/ou altura (Retângulo) | Cada lado fixado substitui o do cursor; o sinal vem do lado em que o cursor está |

- A pré‑visualização usa sempre o ponto resultante. A linha de guia do ângulo fixado
  aparece tracejada.
- Valor fora do aceitável (comprimento ≤ mínimo da parede, número inválido): o campo fica
  em vermelho, o ponto não é confirmado e Mensagens explica.

## 3. Vista 3D: seleção e edição

### 3.1 Mouse e teclado
| Ação | Resultado |
|---|---|
| Clique esquerdo (sem arrastar) | Ferramenta Selecionar: seleciona o elemento sob o cursor; vazio limpa a seleção. Outras ferramentas: dá um ponto à ferramenta (§3.2) |
| Ctrl + clique | Acrescenta ou retira da seleção, como na planta |
| Arrastar com o botão esquerdo | **Órbita**, como hoje (o clique só vale se o cursor andar menos de 4 px) |
| Arrastar com o botão do meio | Deslocar, como hoje |
| Roda | Aproximar, como hoje |
| Botão direito | Menu de contexto (§4); nas ferramentas de desenho, encerra, como na planta |
| Tab, Enter, Esc, números, Delete, Shift, Alt | Os mesmos da planta |

- **Elemento sob o cursor:** o primeiro triângulo atingido pelo raio que sai do olho e
  passa pelo cursor. Porta dentro da parede: vale a mais próxima do olho.
- A **ferramenta ativa é a mesma** nas duas vistas (a caixa de ferramentas é única):
  escolher Mover na planta e clicar no 3D funciona, e vice‑versa.
- A **mini-barra da seleção** aparece também no 3D, junto à projeção da seleção na tela,
  com as mesmas ações (spec 03 §5).
- **Fora desta etapa:** seleção por janela no 3D, alças no 3D, arrastar a seleção para
  mover no 3D (no 3D, arrastar é sempre órbita; ponto (c)).

### 3.2 Ponto dado no 3D
As ferramentas trabalham no plano do pavimento (x, y). No 3D, o ponto é:

1. Se o raio atinge um elemento: o **(x, y) do ponto atingido**. Clicar no topo do canto
   de uma parede dá o canto, mesmo a 2,80 m de altura.
2. Senão: a interseção do raio com o **plano de trabalho**, horizontal na cota do
   pavimento ativo. Raio paralelo ao plano não dá ponto.
3. Depois, o *snap* do pavimento ativo, como na planta (tolerância em pixels convertida
   para metros na profundidade do ponto). O marcador de *snap* aparece no plano de
   trabalho.

Pavimento das ferramentas no 3D:
- Desenhar (parede, porta…): no pavimento ativo.
- Transformar (mover, copiar, girar, espelhar): age sobre a seleção, esteja em que
  pavimento estiver (as transformações são em x, y). Se toda a seleção é de um mesmo
  pavimento, o plano de trabalho passa a ser o dele enquanto a ferramenta estiver ativa.
- **Selecionar no 3D um elemento de outro pavimento não muda o pavimento ativo** (ponto
  (b)). Para isso existe Mostrar na planta (§4).

### 3.3 Pré‑visualização no 3D
- **Mover, Copiar, Girar, Espelhar:** cópia fantasma (semitransparente) das malhas
  selecionadas na posição resultante, mais as marcas da planta desenhadas no plano de
  trabalho (linha de base, eixo, arco do ângulo).
- **Desenhar parede e porta:** as marcas da planta (contorno da faixa da parede, folha da
  porta) desenhadas como linhas no plano de trabalho, na cor de pré‑visualização (ponto
  (d)). Posição recusada: em vermelho, como na planta.
- Ao confirmar, as malhas são refeitas pelo histórico, como já acontece (`Scene.update`).

### 3.4 Seleção nas duas vistas
A seleção já é uma só (`Session.selection`): o que se seleciona no 3D fica destacado na
planta, e vice‑versa, sem nada a fazer. Elemento de outro pavimento fica selecionado, mas
só aparece na planta quando o pavimento dele estiver ativo.

## 4. Mostrar a seleção na outra vista
Com a ferramenta Selecionar, o **botão direito sobre um elemento** primeiro o seleciona
(se não estava selecionado; Ctrl acrescenta) e abre um menu curto:

| Na vista | Itens |
|---|---|
| 3D | **Mostrar na planta**, Enquadrar a seleção |
| Planta | **Mostrar no 3D**, Enquadrar a seleção |

Botão direito no vazio: o menu só com Enquadrar tudo (Home).

**Mostrar na planta:**
1. Torna ativo o pavimento do elemento clicado (com seleção de vários pavimentos, vale o
   do elemento clicado).
2. Mostra a planta: no modo em abas, troca para a aba Planta; lado a lado, não muda nada.
3. Enquadra a seleção daquele pavimento com margem de 20 % de cada lado, sem passar da
   aproximação máxima (elemento pequeno não ocupa a tela inteira).

**Mostrar no 3D:**
1. Mostra o 3D (aba ou lado a lado, como acima).
2. Centra a órbita no centro da caixa da seleção e ajusta a distância para a caixa caber,
   **mantendo a direção da câmera**.

**Enquadrar a seleção:** o mesmo, na própria vista.

Também no menu Exibir, com atalhos: **Mostrar na planta** (Ctrl+Shift+P) e **Mostrar no
3D** (Ctrl+Shift+3), habilitados com seleção. Nenhuma das duas vistas passa a seguir a
seleção sozinha (ponto (e)).

## 5. Implementação (notas)
- **Campos:** em `ui/tools.py`, sem Qt: cada ferramenta declara `fields()` (nome, unidade,
  valor do cursor) e aceita `fix(nome, valor | None)`; o cálculo do §2.3 fica num auxiliar
  testável. `numeric()` atual vira "fixar o primeiro campo e confirmar". O quadro é um
  widget comum às duas vistas.
- **Raio e escolha:** em `ui/scene3d.py`, sem Qt nem OpenGL: `ray(px, py, câmera)`,
  `Scene.pick(origem, direção) -> (gid, ponto) | None` (Möller–Trumbore vetorizado com
  numpy, teste prévio pela caixa de cada malha) e `ray_plane(origem, direção, z)`.
  A matriz da câmera sai de `View3D` para funções puras, para os testes.
- **3D como segunda entrada das ferramentas:** `View3D` recebe a `ToolBox` e o
  `PlanContext`, traduz o mouse em ponto (§3.2) e chama `move/press/double/key/numeric`
  como a planta. As marcas (`preview()`) são desenhadas no plano de trabalho; as
  ferramentas de transformação expõem a matriz 2D corrente (`affine()`) para o fantasma.
- **Menus:** `QMenu` nas duas vistas; enquadrar a planta usa a caixa das formas de
  `plan.Plan` da seleção; o 3D usa a caixa das malhas.
- Mini-barra: uma instância por vista; aparece só na vista com o cursor ou com o foco.

## 6. Critérios de aceite (testes)
- [x] **UI61** Parede: 1º ponto em (0, 0), Tab, `3` Tab `90` Enter: a parede vai de (0, 0) a
      (0, 3); o IFC tem `IfcWall` com caminho de 3,00 m no eixo y.
- [x] **UI62** Parede com só o comprimento fixado em 2,5 e o cursor em (10, 10): o ponto é
      (1,768, 1,768). Só o ângulo fixado em 0° e o cursor em (4, 3): o ponto é (4, 0).
- [x] **UI63** Digitar `3` Enter sem Tab continua criando o segmento de 3 m na direção do
      cursor (comportamento de hoje).
- [x] **UI64** Esc no quadro solta os valores fixados; o 2º Esc descarta a parede em
      andamento. Comprimento 0 fica em vermelho e nada é criado.
- [x] **UI65** Retângulo com largura 4 e altura 3 digitadas: quatro paredes com o
      retângulo 4 × 3 a partir do 1º canto, para o lado do cursor.
- [x] **UI66** Mover com Distância 2 e Ângulo 180: `wall.edit` desloca o caminho 2 m em −x.
      Girar com Ângulo 90 gira 90° anti‑horário em torno do centro.
- [x] **UI67** `Scene.pick`: raio de cima sobre uma parede devolve a parede; raio que passa
      pela porta devolve a porta (mais próxima); raio no vazio devolve nada.
- [x] **UI68** Ponto no 3D: raio que atinge o topo do canto de uma parede dá o (x, y) do
      canto; raio no vazio dá a interseção com o plano do pavimento ativo; raio horizontal
      não dá ponto.
- [x] **UI69** Clique no 3D com Selecionar seleciona a parede, e a planta a mostra
      selecionada; Ctrl+clique acrescenta; clique no vazio limpa. Arrasto de 10 px orbita
      e não seleciona.
- [x] **UI70** Mover no 3D: base e destino clicados no 3D geram a mesma transação que os
      mesmos pontos na planta; o diário reaplicado reproduz o IFC.
- [x] **UI71** Mostrar na planta, com o elemento num pavimento que não é o ativo: o
      pavimento ativo muda, a aba Planta fica à frente e a seleção cabe na tela.
- [x] **UI72** Mostrar no 3D: o alvo da órbita é o centro da caixa da seleção e a direção
      da câmera não muda.

## 7. Fontes públicas
- **QT** — documentação pública do Qt for Python 6: `QOpenGLWidget`, `QMenu`,
  `QWidget.event` (tecla Tab), `QLineEdit`.
- **MT97** — T. Möller e B. Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection",
  *Journal of Graphics Tools* 2(1), 1997 (algoritmo de interseção raio–triângulo,
  publicado).
- **UI01**, **UI02**, **UI03**, **UI05** — specs de interface 01 §5.5, 02, 03 §5 e 05 §3
  (aprovadas).
- **CG** — conhecimento geral de aplicativos de CAD e modelagem: entrada numérica junto
  ao cursor com troca de campo pelo teclado, escolha de objetos por raio, menu de contexto
  para localizar o objeto em outra vista.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 8. Pontos de revisão
(a) Ângulo **absoluto** (0° = eixo x) na parede, em Mover e em Espelhar; relativo só em
    Girar (§2.1). Alternativa: ângulo relativo ao segmento anterior na parede.
(b) Selecionar no 3D não muda o pavimento ativo; só Mostrar na planta muda (§3.2).
(c) No 3D, arrastar com o botão esquerdo continua sendo órbita; mover só pela ferramenta
    Mover ou pela mini-barra; sem alças nem seleção por janela no 3D nesta etapa (§3.1).
(d) Pré‑visualização de desenho no 3D só em linhas no plano de trabalho, sem volume
    (§3.3).
(e) Mostrar na outra vista só pelo menu (botão direito, Exibir ou atalho); nenhuma vista
    acompanha a seleção sozinha (§4).
(f) Parede em arco sem campos nesta etapa (§2.1).
(g) Esta spec vai antes do pacote 2 (spec 06), que continua aprovado e espera.
