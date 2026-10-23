---
documento: Pacote de precisão (atração completa, teclado no traço, deslocar, aparar, concordar, semelhantes, giro rápido, paleta de comandos)
requisito: RF-DES-02 (atração a pontos), RF-NUC-09 (selecionar semelhantes), RF-NUC-05 (edição)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-23
status: em revisão (fluxo do MVP: implementado na sequência)
revisor: OTTO
---

# Pacote de precisão

## 1. Propósito
Item 1 do roteiro (`CONTEXTO.md`), vindo da comparação com a pesquisa
(`reports/Comparacao BrasBim x pesquisa.md` §3.1–3.2 e §4). Objetivo: desenhar e editar
com exatidão sem diálogo, com o mouse numa mão e o teclado na outra.

Já existe e **não muda**: quadro de medidas junto ao cursor (spec/ui 07 §2), que abre ao
digitar o primeiro algarismo, **sem Tab** (`ToolInput.tool_key`; a comparação dizia o
contrário e foi corrigida); ponto de referência por parada do cursor e linhas de
referência 0°/90° (spec/ui 09 §2.1); Shift = direção em passos de 45°; Alt = sem atração.

## 2. Atração em todos os elementos
### 2.1 De onde vêm os pontos
Um **índice de atração** do pavimento ativo, sem Qt (`core/snap.py`), feito a partir do
que a planta já desenha e refeito quando ela muda:
- **arestas** (segmentos) de todas as formas da planta (`Plan.shapes`: paredes, lajes,
  pilares, vigas, esquadrias, objetos, coberturas, escadas, guarda-corpos, ambientes) e
  de todos os traços das anotações (`Plan.annotations`: linhas 2D, hachuras, cotas,
  **desenho importado**, terreno);
- **curvas exatas**, quando o estado as conhece: caminho das paredes (reta ou arco),
  círculos e arcos 2D (centro e raio), linhas dos eixos de projeto;
- os pontos que a ferramenta passa (`extra`: os pontos já clicados, cantos e centro dos
  pilares, cruzamentos dos eixos), como hoje.

Elementos ocultos não atraem. Elementos de camada bloqueada **atraem** (não podem ser
escolhidos, mas servem de referência). Os segmentos ficam numa grade de baldes para que a
busca perto do cursor não percorra a planta toda.

### 2.2 Tipos de atração
| Tipo | Ponto | Precisa de ponto anterior |
|---|---|---|
| extremidade | ponta ou vértice de uma aresta, ponta do caminho da parede, pontos `extra` | não |
| interseção | cruzamento de duas arestas ou curvas perto do cursor | não |
| meio | meio de uma aresta, do caminho da parede ou de um arco | não |
| centro | centro de círculo, arco 2D ou parede em arco | não |
| perpendicular | pé da perpendicular do ponto anterior sobre a aresta | sim |
| tangente | ponto de tangência, a partir do ponto anterior, num círculo ou arco | sim |
| na borda | ponto mais próximo sobre uma aresta (substitui "na parede") | não |
| grade | grade de 10 cm, quando nada acima atrai | não |

Ordem de prioridade dentro da distância de atração (`tol`): extremidade e interseção,
depois meio, centro, perpendicular, tangente, na borda e grade. Entre pontos da mesma
prioridade ganha o mais próximo do cursor. O tipo "na parede" continua a informar a
parede (`Snap.wall`) quando a aresta é o caminho de uma parede, para as ferramentas de
porta e janela.

### 2.3 Liga e desliga
Menu **Exibir > Atração** com uma caixa por tipo (todos ligados por padrão) e "Desligar
toda a atração" (o mesmo que segurar Alt). A escolha vale para a sessão e fica gravada nas
preferências do usuário, não no projeto.

### 2.4 Marcador
Cada tipo tem um marcador próprio desenhado junto ao ponto, na cor de destaque do tema,
além do nome curto que já aparece (`KIND_LABEL`):
- extremidade: quadradinho cheio; interseção: cruz reta (+); meio: losango;
- centro: dois círculos concêntricos; perpendicular: ⊥; tangente: círculo com traço;
- na borda: traço curto ao longo da aresta; grade: só o ponto, sem nome.

A vista 3D mostra o mesmo ponto (já mostra) com o nome do tipo.

## 3. Teclado durante o traço
### 3.1 Setas travam o eixo
Com um ponto anterior (parede, viga, linha, laje, mover, copiar…):
- **→ ou ←** trava no eixo X do pavimento que passa pelo ponto anterior; **↑ ou ↓**
  trava no eixo Y. A mesma seta de novo, ou Esc, solta.
- Com a trava, o ponto é a projeção do cursor sobre a linha travada. Se o cursor atrai
  um ponto (extremidade, meio…), vale a **projeção desse ponto** na linha: assim se
  alinha a parede com o canto de outra sem linha auxiliar.
- A trava aparece como linha de guia tracejada e no quadro de medidas ("eixo X"); o
  comprimento digitado vale ao longo dela.
- A trava cai ao confirmar o ponto (o próximo trecho começa livre).

### 3.2 Enter repete a ferramenta
Na ferramenta Selecionar, sem nada em andamento e **sem seleção**, Enter reativa a última
ferramenta de criação usada (Parede, Laje, Linha, Porta…), com as opções que ela tinha.
A dica da barra de estado mostra "Enter: repetir <Ferramenta>". Com seleção, Enter
continua sem efeito (não muda a seleção por engano).

## 4. Deslocar paralela
Ferramenta **Deslocar paralela** (grupo Edição, depois de Espelhar):
1. Clique no elemento: parede (reta ou em arco), linha 2D, círculo ou arco 2D, contorno
   de laje, ambiente ou hachura.
2. O fantasma acompanha o cursor do lado em que ele está; a distância vai no quadro de
   medidas (digitar o número) ou vem do cursor. O lado é sempre o do cursor.
3. Clique confirma. A ferramenta continua ativa, com a mesma distância fixada, para o
   próximo elemento (Esc solta a distância; Esc de novo sai).

Barra Opções: **Copiar** (padrão: cria um elemento novo, igual ao original e deslocado)
ou **Mover o original**. Na parede a distância é medida entre os eixos (linha de
referência da parede); a cópia recebe o mesmo tipo, altura e topo, e as junções se
formam como em qualquer parede nova. Linha 2D: polilinha paralela (cantos em ponta);
círculo e arco: concêntricos (raio ± d; recusa se o raio ficar ≤ 0). Contornos fechados:
o polígono deslocado para fora ou para dentro com cantos em ponta (Clipper2), recusa se
sumir. Cada confirmação é uma transação (`create` do mesmo tipo, ou `edit` do original).

## 5. Aparar e estender
Ferramenta **Aparar/estender** (grupo Edição). Todas as arestas visíveis do pavimento
(o índice do §2.1) servem de **limite**, sem escolher limites antes.

**Linhas 2D** (cada segmento reto de uma polilinha 2D):
- Clique sobre um trecho que tem cruzamento com limite **do lado da ponta clicada ou
  entre dois cruzamentos**: o trecho entre os cruzamentos vizinhos ao clique sai (aparar).
  Se o trecho fica no meio da polilinha, ela se divide em duas linhas (a segunda é um
  elemento novo com o mesmo estilo).
- Clique perto de uma ponta solta que **não tem** cruzamento entre o clique e a ponta:
  a ponta avança até o primeiro limite à frente (estender). Shift + clique estende
  mesmo quando haveria o que aparar.
- O trecho que vai sair aparece em vermelho (`invalid`) antes do clique; a extensão
  aparece como fantasma.

**Paredes retas**: clique perto de uma ponta. Se a parede atravessa outra além dessa
ponta, a ponta recua até o **eixo** da outra; se não alcança, avança até o eixo da
primeira parede à frente. A junção (T ou L) se forma pelas regras de sempre ao gravar a
ponta sobre o caminho da outra parede. Paredes em arco: recusa no MVP.

Sem cruzamento nem limite à frente: recusa com mensagem ("nada para aparar ou
estender aqui").

## 6. Concordar
Ferramenta **Concordar** (grupo Edição). Barra Opções: **raio** (padrão 0).
1. Clique no primeiro segmento (linha 2D reta ou parede reta) e no segundo.
2. Os dois são cortados ou estendidos até o ponto de encontro das retas; o lado que fica
   é o lado de cada um em que se clicou.
3. **Raio 0**: canto vivo. Nas paredes, as duas pontas vão ao cruzamento dos eixos e a
   junção L se forma.
4. **Raio > 0** (só linhas 2D no MVP): as duas linhas param nos pontos de tangência e um
   **arco 2D** novo, com o estilo da primeira, liga os dois. Recusa se o raio não couber
   nos segmentos.
5. Shift no segundo clique usa raio 0 sem mudar o raio guardado.

Recusa com segmentos paralelos, com parede em arco, ou com uma linha e uma parede. Uma
transação por concordância.

## 7. Selecionar semelhantes
Comando **Selecionar semelhantes** no menu Editar e na mini-barra da seleção (no lugar de
"Selecionar todos deste tipo", que vira o critério "mesmo tipo"). Submenu de critérios,
a partir dos elementos selecionados:
- **mesma classe IFC** (`IfcWall`, `IfcDoor`…);
- **mesmo tipo** (`IfcTypeObject` associado);
- **mesma classe e mesmo `PredefinedType`** (ou `ObjectType` quando `USERDEFINED`);
- **mesmo material** (o material ou o primeiro da composição);
- **mesma camada** (spec/ui 18).

Procura no pavimento ativo, em elementos visíveis e não bloqueados; com vários
selecionados, vale a união dos valores ("mesmo tipo" de duas paredes de tipos diferentes
seleciona os dois tipos). A função fica no núcleo (`core/select_similar.py`), sem Qt.

## 8. Girar 90°
**Ctrl+R** gira a seleção 90° anti-horário; **Ctrl+Shift+R**, horário. Centro: o centro
do retângulo que envolve a seleção na planta. Usa a mesma operação da ferramenta Girar
(uma transação, desfaz com Ctrl+Z). Também no menu Editar e na mini-barra.

## 9. Paleta de comandos
**Ctrl+K** abre um campo de busca no alto da janela com todas as ações dos menus e todas
as ferramentas. A lista filtra enquanto se digita; Enter executa a primeira (ou a
marcada com as setas); Esc fecha.
- Busca aproximada: sem acento e sem caixa, letras na ordem mesmo com outras no meio
  ("pard" acha "Parede"), com início de palavra valendo mais.
- **Sinônimos**: cada ferramenta de elemento também responde pelo nome da classe IFC e
  por termos usuais ("IfcWall", "muro", "alvenaria" → Parede; "IfcSlab", "piso" → Laje;
  "IfcSpace", "cômodo" → Ambiente…).
- As usadas recentemente vêm primeiro quando o campo está vazio.
- Cada linha mostra o nome, o menu de onde vem e o atalho, se houver.
- A lógica de busca é sem Qt (`ui/command_search.py`); a janela é `ui/command_palette.py`.

## 10. Fica para depois (mesma trilha)
Rastreamento a 45° e ângulos configuráveis, vários pontos de referência ao mesmo tempo,
aritmética no quadro ("2*", "+0,15"), linhas-guia persistentes e pontos de divisão, cota
viva editável, cópia em série, concordância com arco em paredes, aparar paredes em arco,
selecionar semelhantes no projeto todo.

## 11. Critérios de aceite (testes)
- **PR01** Índice: aresta de laje, linha 2D, linha do desenho importado e eixo de
  projeto dão extremidade e meio; elemento oculto não atrai; de camada bloqueada atrai.
- **PR02** Interseção de duas linhas 2D que se cruzam fora das pontas.
- **PR03** Centro de círculo 2D e de parede em arco.
- **PR04** Perpendicular e tangente a partir do ponto anterior; sem ponto anterior não
  aparecem.
- **PR05** Prioridade: extremidade vence meio e borda dentro da mesma `tol`; tipo
  desligado em Exibir > Atração não aparece.
- **PR06** Seta trava X/Y; com ponto atraído vale a projeção; a trava cai ao confirmar.
- **PR07** Enter na seleção vazia reativa a última ferramenta de criação; com seleção,
  não.
- **PR08** Deslocar parede 0,50 m: parede nova do mesmo tipo com eixo paralelo a 0,50 m
  no IFC; "Mover o original" muda a mesma parede; linha 2D, círculo e contorno de laje.
- **PR09** Aparar trecho do meio de uma linha 2D cruzada por duas: duas linhas no IFC;
  aparar a sobra de uma ponta; estender até uma linha; recusa sem limite.
- **PR10** Estender e aparar parede até o eixo de outra: junção T no IFC
  (`IfcRelConnectsPathElements`).
- **PR11** Concordar raio 0 em duas linhas e em duas paredes (junção L); raio 0,30 em
  duas linhas cria arco 2D tangente; paralelas recusam.
- **PR12** Selecionar semelhantes: classe, tipo, `PredefinedType`, material, camada;
  união com dois selecionados; só o pavimento ativo.
- **PR13** Ctrl+R gira 90° em torno do centro da seleção; Ctrl+Shift+R volta; uma
  transação.
- **PR14** Busca da paleta: "pard" acha Parede, "ifcwall" e "muro" também; sem acento;
  recentes primeiro com campo vazio.

## 12. Fontes públicas
Pesquisa do projeto: `reports/Pesquisa Archicad Revit AutoCAD.md` (seção "A velocidade
nasce de digitar sem foco") e notas `interface_e_interacao.md` §1–2, `autocad.md` §1,
`archicad_modelagem.md` §3. Ajuda pública lida para este pacote (trechos de busca,
**conferir** na página):
- Tipos de atração (extremidade, meio, centro, interseção, perpendicular, tangente,
  mais próximo): [Autodesk, Object Snap Tab (AutoCAD for Mac)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-MAC-Core/files/GUID-A782462F-F85C-4496-85A5-3D9A54548489.htm);
  [AutoCAD Web Help, Object Snaps](https://help.autodesk.com/cloudhelp/ENU/AutoCAD-Web-Help/files/Drafting-and-Creating/AutoCAD_Web_Help_Drafting_and_Creating_Osnap_html.html).
  Formas por tipo de ponto: [Autodesk, About Snaps (Revit 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-A3947840-1F30-41D7-AF75-B61687952A07.htm).
  Inferência por pontos, linhas e cores; setas travam o eixo: [SketchUp Help, Drawing basics](https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts).
- Deslocar paralela (distância ou por ponto, concêntrico em círculos, repetir com a
  mesma distância): [Autodesk, OFFSET (AutoCAD LT 2021)](https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-LT/files/GUID-C0E4246D-C420-42BD-A6FC-8B1852EFD005.htm);
  [About Offsetting Objects (2018)](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Core/files/GUID-704C1ADE-A4AE-4A85-8822-454ACAC1345A.htm).
- Aparar/estender com todos os objetos como limite e Shift para inverter:
  [Autodesk, About Trimming and Extending Objects (LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-725D3A7A-5E52-47F0-BA7A-7D15F9EF6D7F.htm).
- Concordar com raio 0 = canto vivo; Shift para raio 0 temporário:
  [Autodesk, FILLET (AutoCAD LT 2015)](https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-LT/files/GUID-64F8B700-23B3-4BD6-8C03-66121AA13E8F.htm).
- Enter/espaço repetem o último comando: [Autodesk, AutoCAD 2026 Getting Started, Basics](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-GettingStarted/files/GUID-5B6347C1-B458-4336-AB2A-C16AF161B755.htm).
- Selecionar todas as instâncias do mesmo tipo e filtro só por categoria (criticado):
  [CAD Notes](https://www.cad-notes.com/how-to-selectively-select-objects-in-revit/);
  [Archistar Academy](https://academy.archistar.ai/using-filter-selection-to-find-objects-in-revit).
- Girar 90° por atalho: [Graphisoft, Quickly Rotate Elements (AC29)](https://help.graphisoft.com/AC/29/INT/_AC29_Help/005_NewFeatures/005_NewFeatures-6.htm).
- Busca aproximada de comandos: [McNeel, The Rhino window (Rhino 8)](https://docs.mcneel.com/rhino/8/help/en-us/user_interface/rhino_window.htm).

IFC 4.3: `IfcRelConnectsPathElements` (junções), `IfcTypeObject`, `PredefinedType`,
`IfcRelAssociatesMaterial`, `IfcPresentationLayerAssignment`. CG: Ctrl+K para paleta de
comandos e Ctrl+R para girar são convenções comuns de vários programas; marcadores,
nomes ("Deslocar paralela", "Aparar/estender", "Concordar", "Selecionar semelhantes") e
regras de clique são deste projeto. Nada de texto, ícone ou diálogo foi copiado.

Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 13. Pontos de revisão
(a) marcadores do §2.4 (formas próprias; trocar se lembrarem demais outro programa);
(b) setas para travar eixo (alternativa: só Shift);
(c) Enter repete a ferramenta só com seleção vazia;
(d) Deslocar paralela copia por padrão;
(e) aparar/estender de parede leva a ponta ao **eixo** da outra (a junção cuida das
faces);
(f) concordância com raio só em linhas 2D no MVP;
(g) Selecionar semelhantes só no pavimento ativo;
(h) atalhos Ctrl+R / Ctrl+Shift+R e Ctrl+K.
