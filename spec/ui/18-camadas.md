---
documento: Camadas de organização (grupos, visibilidade, bloqueio e combinações)
requisito: RF-NUC-08, RF-NUC-04 (filtro por camada)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-20
status: aprovado (implementado)
revisor: OTTO
---

# Camadas (pacote 12)

## 1. Propósito
Organizar o modelo para **mostrar só o que interessa** em cada momento e em cada desenho.
Exemplos: esconder o mobiliário para cotar a planta, ver só a estrutura, bloquear as
paredes enquanto se desenha o forro, ou guardar um "jeito de mostrar" para a planta da
prefeitura e outro para a planta executiva, ou uma combinação por etapa da obra (layout,
demolição, construção, elétrica, hidráulica…).

Cada elemento fica em **uma camada**. As camadas ficam reunidas em **grupos** (por
exemplo, Estrutura → Pilares, Vigas, Lajes). Uma **combinação** guarda, com um nome, o
estado de todas as camadas (visível ou oculta, livre ou bloqueada), e ele pode ser
reaplicado de uma vez.

Ficam de fora (V1): grupos dentro de grupos, cor e espessura forçadas por camada,
camada mostrada em arame no 3D, camada por vista de prancha
sem combinação, filtro de seleção por camada no diálogo de busca, e camadas que mudam
com a escala (RF-DOC-08).

## 2. Mapeamento IFC
- **Camada no arquivo** = `IfcPresentationLayerWithStyle`:
  - `Name` é o nome da camada. `Identifier` é o código estável do BrasBim (no formato do
    GlobalId, 22 caracteres), que continua o mesmo quando a camada é renomeada.
  - `LayerOn`, `LayerBlocked` e `LayerFrozen` (este último sempre `.F.`) guardam o estado
    de exibição **gravado ao salvar** (§5.1). `LayerStyles` fica vazio.
  - `AssignedItems` lista as **representações** (`IfcShapeRepresentation`) de cada
    elemento da camada: `Body`, `Axis`, `FootPrint`, `Annotation` etc.
- O IFC exige pelo menos um item em `AssignedItems`. Por isso a entidade só existe
  enquanto a camada tem elementos: é criada com o primeiro e apagada com o último.
- A **lista de camadas, os grupos e as combinações** ficam em JSON no Pset
  `BrasBim_Camadas` do `IfcProject`, como as tabelas (spec/ui 17). Ficam ali a ordem, o
  grupo de cada camada, inclusive das vazias, as combinações, a camada padrão de cada
  ferramenta e (`state`) o estado de exibição gravado ao salvar. Quando a camada tem
  entidade, `LayerOn`/`LayerBlocked` e o `state` do JSON são iguais.
- **Outro programa abre o arquivo** e vê as camadas pelo padrão IFC (nome e
  ligada/desligada). Os grupos e as combinações são só do BrasBim.
- **Arquivo de outra origem** com `IfcPresentationLayerAssignment`: cada camada lida
  entra na lista, num grupo "Importadas". Um elemento sem camada fica na pseudo-camada
  **"Sem camada"**, que só vive no JSON e pode ser ocultada e bloqueada como as outras.
- **Camada do elemento:** é a camada da representação `Body`. Sem `Body`, vale a da
  primeira representação que tiver camada. Ao mudar a camada, todas as representações do
  elemento vão para a camada nova.
- Quando um corpo é refeito (`props.replace_representation` e as outras trocas de
  representação), a representação nova **herda a camada** da antiga. Sem isso, editar
  uma parede tiraria a parede da camada.

## 3. Camadas e grupos
| Campo | Valores | Regras |
|---|---|---|
| Nome | texto | Único no projeto, sem diferenciar maiúsculas. Não pode ser vazio |
| Grupo | um grupo ou nenhum | Um nível só (decisão do revisor; grupo dentro de grupo fica para o V1) |
| Visível | sim/não | |
| Bloqueada | sim/não | Desenhada e usada pelo snap, mas não pode ser selecionada nem editada |

O grupo tem só nome e ordem. Ligar ou desligar o olho do grupo, ou o cadeado, muda todas
as camadas dele. Quando as camadas discordam, o grupo mostra o estado "misto".

### 3.1 Conjunto inicial (projeto novo)
É só um ponto de partida. **Quem decide em que camada cada elemento fica é o usuário**
(decisão do revisor): ele cria, renomeia, agrupa e exclui camadas à vontade e escolhe a
camada padrão de cada ferramenta (§3.2) e a camada de cada elemento (§5).

| Grupo | Camadas | Recebem |
|---|---|---|
| Arquitetura | Paredes · Esquadrias · Pisos e lajes · Cobertura · Ambientes | parede; porta e janela; laje; cobertura; ambiente |
| Estrutura | Pilares · Vigas · Lajes estruturais | pilar; viga; (laje, se o usuário escolher) |
| Documentação | Cotas · Textos e rótulos · Linhas e hachuras · Símbolos | cotas; textos; linhas e hachuras 2D; norte, nível, símbolos de corte e fachada |
| Entorno | Terreno · Vegetação | (pacotes 13 e 18) |
| Interiores | Mobiliário | (pacote 13) |

O arquivo do BrasBim criado antes deste pacote ganha esse conjunto ao ser aberto, e os
elementos vão para a camada do seu tipo. Isso é uma transação "Organizar em camadas",
que pode ser desfeita.

### 3.2 Camada padrão de cada ferramenta
Cada ferramenta de criação tem uma camada padrão (a da tabela §3.1), que pode ser trocada
no campo **Camada** da barra Opções. A troca fica gravada no projeto (`BrasBim_Camadas`,
`defaults`). O assistente (spec/ui 16) usa as mesmas camadas padrão.

Se a camada padrão estiver **oculta** quando o elemento é criado, ela é mostrada na hora,
com uma mensagem ("Camada Paredes mostrada para exibir a parede criada"). Assim o elemento
desenhado nunca some. Se ela estiver **bloqueada**, a criação é recusada com uma mensagem
que sugere desbloquear.

## 4. Efeito na tela e nos desenhos
| | Oculta | Bloqueada |
|---|---|---|
| Planta, 3D, cortes e fachadas | não aparece | aparece normalmente |
| Pranchas e PDF | segue a combinação da vista (§6.2) | aparece |
| Seleção por clique ou janela, Tab entre elementos | não | não |
| Snap (pontas, faces, eixos) | não | **sim** |
| Alças, mini-barra, editar pelo painel, Del | — | não |
| Assistente | não aparece no `describe_model` | aparece, marcado como bloqueado; editar é recusado com o texto da recusa |
| Tabelas (spec/ui 17) | **contam** (a tabela fala do modelo, não da tela; ponto (c)) | contam |
| Geometria e junções | iguais: a camada só muda o que é mostrado, nunca o modelo | iguais |

Desenhos que dependem de outros elementos:
- **Esquadria:** segue a própria camada. Com Paredes oculta e Esquadrias visível, o
  símbolo da porta aparece sozinho. Com Esquadrias oculta, a parede é desenhada com o vão
  aberto.
- **Pavimento de baixo** (traço fino na planta) e **acima do plano de corte**: respeitam
  as camadas.
- **Cota associativa** a uma parede oculta continua visível, com a medida certa, se a
  camada Cotas estiver visível.

Elementos selecionados quando a camada deles é ocultada ou bloqueada saem da seleção.

## 5. Mudar a camada de elementos
- **Painel de propriedades:** campo **Camada** (lista agrupada) para um ou vários
  elementos. Com vários em camadas diferentes, o campo mostra "várias".
- **Menu do botão direito** sobre um elemento (planta e 3D): *Ocultar a camada deste
  elemento*, *Bloquear a camada deste elemento* e *Mostrar só a camada deste elemento*.
- Copiar ou colar mantém a camada. O elemento criado por *Dividir* fica na camada do
  original.

Operações novas (serializáveis, como as demais):
| Operação | Faz |
|---|---|
| `layer.create` / `layer.delete` / `layer.edit` | camada: nome, grupo, ordem (a exibição fica fora, §5.1) |
| `layer_group.create` / `.delete` / `.edit` | grupo: nome, ordem |
| `layer.assign` | elementos → camada (cria ou apaga as `IfcPresentationLayerWithStyle`) |
| `layer_combination.create` / `.delete` / `.edit` | combinação: nome e estados |
| `layer.defaults` | camada padrão de cada ferramenta |

**Excluir uma camada que tem elementos** pede a camada para onde eles vão, na mesma
transação. Excluir um grupo leva as camadas dele para "sem grupo" (não apaga as camadas).
A pseudo-camada "Sem camada" não pode ser excluída nem renomeada.

### 5.1 Exibição fora do desfazer (decisão do revisor)
Mostrar, ocultar, bloquear, desbloquear, isolar e aplicar uma combinação **não são
operações**: não entram no desfazer nem no diário de sessão e não pedem reserva na
colaboração. São o estado de exibição **de quem está usando** (`Session.layer_state`),
como o zoom. Na colaboração, cada usuário vê as camadas do seu jeito.

- **Ao salvar**, o estado atual vai para `LayerOn`/`LayerBlocked` e para o `state` do JSON,
  direto no arquivo e sem transação. Assim outro programa abre o IFC como ele foi
  deixado.
- **Ao abrir**, o estado é lido de volta. Arquivo sem `state` abre com tudo visível e
  livre.
- O que **é** operação: criar, excluir, renomear e reordenar camadas e grupos, mudar o
  grupo de uma camada, `layer.assign`, a camada padrão das ferramentas e criar, editar ou
  excluir combinações.

## 6. Combinações
Uma combinação é um nome mais, para cada camada, visível ou oculta e livre ou bloqueada.

### 6.1 Na janela
- Lista **Combinação** no alto do painel Camadas. Escolher um nome aplica os estados
  (exibição, fora do desfazer, §5.1).
- Mudar qualquer camada depois disso deixa a lista em "(alterada)". *Atualizar
  combinação* grava o estado atual nela, e *Salvar como…* cria uma combinação nova.
- Camada criada depois da combinação: entra **visível e livre** nas combinações que já
  existem.
- Conjunto inicial (aprovado): **Tudo**, **Arquitetura** (sem Estrutura nem
  Documentação), **Estrutura** (só Estrutura e Cotas) e **Apresentação** (sem
  Documentação nem Ambientes).

### 6.2 Na prancha
Cada vista da prancha (spec/ui 15, `views[]`) ganha o campo opcional `combination`, com o
código da combinação. Sem ele, a vista mostra o estado atual da janela, como hoje. Com
ele, a vista desenha com os estados daquela combinação, **sem mudar** a janela. Assim a
mesma planta pode aparecer em duas pranchas, uma com cotas e outra sem.

## 7. Painel Camadas
Painel próprio (Exibir > Painéis > Camadas, Ctrl+Shift+L), **separado** dos outros
(decisão do revisor): abre solto, como janela flutuante, e lembra posição e tamanho
(`QSettings`). Não vira aba junto de Projeto ou Propriedades.
- **Busca** no alto: filtra a lista pelo nome enquanto se digita. Os grupos que têm
  camadas encontradas ficam abertos.
- Lista em árvore com os grupos e as camadas dentro deles. Em cada linha: o **olho**
  (visível), o **cadeado** (bloqueada), o nome (que muda com duplo clique) e o número de
  elementos.
- Clicar no olho com Alt mostra **só esta** camada ou grupo e oculta as outras. Alt de
  novo devolve o estado anterior.
- Arrastar uma camada para outro grupo ou outra posição.
- Botões pequenos com ícones próprios: *nova camada*, *novo grupo*, *excluir* e *mostrar
  todas*.
- Duplo clique no número de elementos seleciona os elementos visíveis da camada no
  pavimento atual.
- Barra Opções de cada ferramenta de criação: campo **Camada** (§3.2).

Ícones novos (olho, olho fechado, cadeado aberto, cadeado fechado, pasta do grupo)
desenhados em `scripts/gerar_icones.py`, no estilo dos outros.

## 8. Critérios de aceite (testes)
Casa de teste: retângulo de paredes (0, 0)–(8, 5), uma porta P1, uma janela J1, um pilar,
uma laje, um ambiente, uma cota e um texto, no Térreo.

- [x] **CM01** Projeto novo: grupos e camadas da §3.1 no `BrasBim_Camadas`. Cada elemento
      criado tem as representações em uma `IfcPresentationLayerWithStyle` com o nome
      certo, e o arquivo passa na validação de esquema.
- [x] **CM02** A camada sobrevive à edição: mover uma parede, mudar o tipo, a altura ou a
      forma do topo e desfazer deixa as representações novas na mesma camada, sem
      representação solta em `AssignedItems`.
- [x] **CM03** Camada vazia: tirar o último elemento apaga a entidade IFC e a camada
      continua no JSON. Pôr um elemento de volta cria a entidade de novo.
- [x] **CM04** Ocultar Paredes: `storey_plan`, `Scene` (3D) e o corte não têm nenhuma
      parede. A porta continua na planta. Seleção, janela de seleção e snap ignoram as
      paredes.
- [x] **CM05** Bloquear Paredes: as paredes são desenhadas e o snap acha a ponta, mas
      clique, janela de seleção, Del e as alças não pegam a parede.
- [x] **CM06** Grupo: desligar Estrutura desliga Pilares, Vigas e Lajes estruturais.
      Religar uma delas deixa o grupo "misto".
- [x] **CM07** `layer.assign` de vários elementos, com desfazer e refazer: o diário
      reaplicado reproduz o IFC. Reabrir o arquivo traz camadas, grupos e combinações.
- [x] **CM08** Excluir uma camada com elementos leva os elementos para a camada escolhida.
      Excluir um grupo mantém as camadas.
- [x] **CM09** Combinação: aplicar **Estrutura** deixa visíveis só Estrutura e Cotas.
      Mudar uma camada mostra "(alterada)". Uma camada criada depois entra visível nas
      combinações que já existem.
- [x] **CM10** Prancha: duas vistas da mesma planta, uma com a combinação **Tudo** e outra
      com **Arquitetura**. O PDF da segunda não tem pilar nem cota, e a janela não muda.
- [x] **CM11** Arquivo de outra origem com `IfcPresentationLayerAssignment`: as camadas
      aparecem no grupo "Importadas", e ocultar uma delas some com os elementos dela. Os
      elementos sem camada ficam em "Sem camada".
- [x] **CM12** Arquivo antigo do BrasBim (sem `BrasBim_Camadas`): abrir organiza os
      elementos em camadas, numa transação que pode ser desfeita.
- [x] **CM13** Criar uma parede com a camada Paredes oculta mostra a camada e avisa. Com a
      camada bloqueada, a criação é recusada.
- [x] **CM14** Interface: o olho no painel Camadas oculta as paredes na planta e no 3D.
      Alt + clique isola a camada. O campo Camada do painel de propriedades muda a camada
      de dois elementos numa transação só.
- [x] **CM15** Assistente: `describe_model` não lista elemento oculto, e `edit_wall` em
      parede bloqueada volta como erro.
- [x] **CM16** Exibição fora do desfazer: ocultar, bloquear e aplicar combinação não
      acrescentam nada ao histórico nem ao diário. Salvar grava `LayerOn`/`LayerBlocked` e o
      `state`, e reabrir traz o mesmo estado.
- [x] **CM17** Painel: a busca "cot" deixa só Cotas, com o grupo Documentação aberto.

## 9. Fontes públicas
- **IFC 4.3**: `IfcPresentationLayerAssignment` e `IfcPresentationLayerWithStyle`
  (atributos `Name`, `Identifier`, `AssignedItems` com pelo menos um item, `LayerOn`,
  `LayerFrozen`, `LayerBlocked`, `LayerStyles`) e `IfcLayeredItem`, no repositório
  oficial da buildingSMART (ifc43-docs.standards.buildingsmart.org).
- **IfcOpenShell** (LGPL): `ifcopenshell.api.layer` (`add_layer_with_style`,
  `assign_layer`, `unassign_layer`, `edit_layer`), conforme a documentação pública.
- **CG**: camadas para organizar desenho técnico existem nos programas de CAD e BIM em
  geral. O que vem daqui é só a função: ocultar, bloquear, agrupar e guardar estados com
  nome. Os nomes das camadas e dos grupos iniciais são próprios, em português.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 10. Decisões do revisor (2026-10-20)
a. Grupos de **um nível só**.
b. Ligar e desligar camadas **não** entra no desfazer (§5.1).
c. As tabelas **contam** os elementos ocultos.
d. O usuário define em que camada cada elemento fica. O conjunto inicial é só um ponto
   de partida (§3.1).
e. As combinações iniciais ficam como propostas.
f. O painel Camadas é **separado** (janela solta, §7).

Visto no print do revisor (`feedback/prints/vegetais.png`), só como função: combinações
usadas por etapa da obra e uma lista longa de camadas. Daí veio a busca do painel (§7).
