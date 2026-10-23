# Contexto de desenvolvimento

Estado do trabalho para retomar numa sessão nova. Atualizar ao fim de cada etapa.
Regras do projeto: `CLAUDE.md` e `cleanroom/PROCESSO.md` (nunca acessar `_restrito/` nem
`tools/`).

*Atualizado em 2026‑10‑23 (pacote de precisão implementado, spec/ui 23 em revisão).*

> **Onde paramos (2026‑10‑23, fim do dia):** **pacote de precisão** feito
> (`spec/ui/23-precisao.md`, em revisão; seção "Pacote de precisão — como ficou" abaixo):
> atração em todos os elementos com interseção, perpendicular, centro e tangente e
> marcador por tipo; setas travam X/Y; Enter repete a última ferramenta; Deslocar
> paralela, Aparar/estender e Concordar; Selecionar semelhantes; Ctrl+R gira 90°; Ctrl+K
> paleta de comandos. Ao ler o código, viu-se que o número digitado **já** abria o quadro
> sem Tab: a comparação foi corrigida. Próximo: **item 2 do roteiro** (projeto legal),
> depois da revisão da spec 23 (pontos §13).

> **Antes (2026‑10‑23, manhã):** todas as specs passaram a ter seção "Fontes"
> (`c361693`). Foi feita a **comparação das funcionalidades atuais com a pesquisa**
> (`reports/Comparacao BrasBim x pesquisa.md`); o revisor aprovou a ordem: precisão antes
> do projeto legal.

> **Antes (2026‑10‑21):** pacotes 14–18, salvamento automático (spec/ui 21),
> importar DXF/DWG (spec/ui 22) e terreno por curvas pegas do desenho feitos. O revisor
> pediu que o desenvolvimento passe a se basear no que Archicad, Revit e AutoCAD fazem
> (e no que usuários reclamam), não só no uso dele: foi feita uma **pesquisa ampla** em
> fontes públicas (`reports/Pesquisa Archicad Revit AutoCAD.md`, 758 fontes, notas em
> `research_notes/`). Dela saiu o **roteiro abaixo** ("Roteiro a partir da pesquisa"),
> que passa a orientar os próximos pacotes. Registro de fontes consolidado em
> `cleanroom/REGISTRO-DE-FONTES.md`; licenças em `THIRD_PARTY_NOTICES.md`. **Fluxo do
> MVP** continua: spec curta "em revisão" + implementação na sequência. Prints do revisor
> em `feedback/prints/` só como descrição de função. Continuam abertos os itens 0 e 0b.

> **Como retomar (sessão nova):**
> 1. Ler este arquivo, `CLAUDE.md`, `cleanroom/PROCESSO.md` e a pasta `feedback/`.
> 2. Pedir ao revisor a revisão da spec/ui 23 (pontos §13) e testar no aplicativo:
>    setas, Enter, as três ferramentas do grupo Edição, Ctrl+R, Ctrl+K, Exibir > Atração.
> 3. Depois: **item 2** (projeto legal). Antes da spec, ler no relatório as recomendações
>    1, 2, 3 e 8 e as notas `normas_e_projeto_legal_brasil.md`,
>    `archicad_documentacao_colaboracao.md` e `revit_documentacao_colaboracao.md`;
>    conferir as fontes marcadas "conferir".
> 4. Estado verificado em 2026‑10‑23: 682 testes passando, ruff limpo.
> 5. Decisões que são do revisor: (a) segunda rodada de pesquisa, que exige aumentar
>    `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` (cada sessão tem 200 buscas, divididas
>    entre os agentes); (b) instalar o ODA File Converter (opendesign.com) para abrir DWG;
>    (c) itens 0 e 0b das pendências (pilar `CardinalPoint`, revisão do assistente).

## Comandos
| Para | Comando |
|---|---|
| Testes (682 passando) | `.venv/Scripts/python -m pytest -q -p no:faulthandler` |
| Lint | `.venv/Scripts/ruff check brasbim tests exemplos scripts` |
| Aplicativo | `.venv/Scripts/python -m brasbim.ui.app [arquivo.ifc]` |
| Ícones | `.venv/Scripts/python scripts/gerar_icones.py` |
| Commit | `git commit -s` (DCO) |

## Specs
| Spec | Situação |
|---|---|
| `spec/elementos/parede.md`, `porta.md`, `janela.md` | aprovadas e implementadas (janela: JA01–JA14 em `tests/test_janela.py`) |
| `spec/01-modelo-de-dados.md` | rascunho vivo, atualizado a cada operação nova |
| `spec/ui/01` (0.1), `02-edicao` (0.2), `03-barras-e-icones`, `04-painel-de-propriedades`, `05-acabamento-parede-porta` | aprovadas e implementadas (testes UI01–UI50) |
| `spec/ui/06-planta-por-camadas` | aprovada e implementada (testes UI51–UI60) |
| `spec/ui/07-medidas-e-edicao-no-3d` | aprovada e implementada (testes UI61–UI72) |
| `spec/ui/08-parede-no-3d-topo-e-inclinacao` | aprovada e implementada (testes UI73–UI81), inclusive §4.3 (corte por trecho) |
| `spec/ui/09-janela` | aprovada e implementada (testes UI82–UI95 em `tests/test_interface_janela.py`) |
| `spec/ui/12-estrutura-refinamento` | aprovada e implementada (pacote 5; RC01–10 em `tests/test_recortes.py`, AL01–05 e LC01–03 em `test_laje.py` e `test_interface_estrutura.py`, ET01–02) |
| `spec/ui/13-documentacao-planta` | aprovada e implementada (pacote 6; `tests/test_documentacao.py`, `test_interface_documentacao.py`) |
| `spec/ui/14-cortes-e-fachadas` | aprovada e implementada (pacote 7; `tests/test_cortes.py`, `test_interface_cortes.py`) |
| `spec/ui/15-pranchas-e-pdf` | aprovada e implementada (pacote 8; `tests/test_pranchas.py`, `test_interface_pranchas.py`) |
| `spec/ui/16-assistente` | **em revisão**, implementado para teste (pacote 9; AS01–AS14 em `tests/test_assistente.py`, `test_interface_assistente.py`); pontos de revisão §9 |
| `spec/elementos/cobertura.md` | aprovada e implementada (pacote 10; CB01–CB13 em `tests/test_cobertura.py`, CB14–CB17 em `test_interface_cobertura.py`) |
| `spec/elementos/objeto-parametrico.md` | aprovada e implementada (pacote 13; OB01–OB21 em `tests/test_objetos*.py` e `test_interface_objetos.py`). Nome "objeto paramétrico" ("Objeto" nos menus), editor por formulário + prévia, fórmulas, escolha e visibilidade, preso à parede, aninhados; biblioteca com mobiliário, louças, eletrodomésticos e vegetação |
| `spec/ui/19-desenho-2d` | **em revisão**, implementada (pacote 14; D2D01–D2D08 em `tests/test_desenho_2d.py` e `test_interface_desenho_2d.py`) |
| `spec/ui/20-eixos-vaos-claraboia` | **em revisão**, implementada (pacotes 15–16; EV01–EV06 em `tests/test_eixos_vaos.py` e `test_interface_eixos.py`) |
| `spec/elementos/escada-terreno.md` | **em revisão**, implementada (pacotes 17–18; ET01–ET07 em `tests/test_escada_terreno.py`, ET08–ET09 em `test_interface_escada_terreno.py`) |
| `spec/ui/21-salvamento-automatico` | **em revisão**, implementada (RF-NUC-10; SA01–SA05 em `tests/test_salvamento_automatico.py`) |
| `spec/ui/23-precisao` | **em revisão**, implementada (pacote de precisão; PR01–PR05 e PR08–PR12 em `tests/test_precisao.py`, PR06, PR07, PR13–PR15 em `test_interface_precisao.py`); pontos de revisão §13 |
| `spec/ui/22-importar-desenho` | **em revisão**, implementada (RF-DOC-11 antecipado; ID01–ID06 em `tests/test_importar_desenho.py`) |
| `spec/ui/18-camadas` | aprovada e implementada (pacote 12; CM01–CM19 em `tests/test_camadas_organizacao.py` e `test_interface_camadas_organizacao.py`) |
| `spec/ui/17-tabelas` | aprovada e implementada (pacote 11; TB01–TB09 e TB11 em `tests/test_tabelas.py`, TB10 em `test_interface_tabelas.py`) |
| `spec/ui/11-aparencia` | **em revisão**, já implementada (tema em `ui/theme.py`, fonte Archivo em `ui/fonts/`; testes AP01–AP03) |
| `spec/elementos/laje.md`, `pilar.md`, `viga.md` e `spec/ui/10-laje-pilar-viga` | aprovadas e implementadas (pacote 4, básico; LA01–12 em `tests/test_laje.py`, PI01–14 em `test_pilar.py`, VI01–13 em `test_viga.py`, UI96–UI109 em `test_interface_estrutura.py`). `pilar.md` §11 (e): correção do `CardinalPoint` **a confirmar pelo revisor** |

## O que já existe
- Interface com barras móveis e ícones próprios, barra Opções por ferramenta, mini-barra
  junto à seleção (`ui/selection_bar.py`), painel de propriedades em pé ou deitado.
- Parede: tipos com representação na planta (Pset `BrasBim_RepresentacaoPlanta`),
  junções L/T/X, unir, desfazer junção (`SemJuncaoCom`), trocar a contínua, dividir,
  espelhar, comprimento e ângulo no painel, propriedades comuns.
- Porta: tipos, alças de largura, etiqueta na planta, propriedades comuns.
- Operações serializáveis com desfazer/refazer e diário de sessão (`feedback/diarios/`).
- Quadro de medidas junto ao cursor (`ui/measure_box.py`): Tab digita comprimento/ângulo
  (parede), largura/altura (retângulo), distância/ângulo (mover, copiar), ângulo (girar,
  espelhar), distância (dividir). Lógica sem Qt em `tools.py` (`fields`, `fix`, `confirm`,
  `polar_point`, `rect_corner`).
- Alças da parede no 3D (`ui/handles3d.py`, `View3D.handles`): pontas, face, topo, base;
  o arrasto vive em `SelectTool.drag3d` e usa o quadro de medidas.
- Vista 3D com seleção por clique, as mesmas ferramentas da planta (ponto = x, y do
  elemento atingido ou do plano do pavimento), fantasma das transformações, mini-barra e
  menu do botão direito (Mostrar na planta / Mostrar no 3D / Enquadrar). Câmera e raio
  sem Qt em `ui/scene3d.py` (`Camera`, `Scene.pick`, `ray_plane`).

## Spec 08 — como ficou (topo e tombada)
- Estado da parede: `top_shape` (`flat`/`slope`/`gable`/`free`), `top_profile`
  ([posição, altura a partir da base]; vazio no plano) e `tilt` (graus, + esquerda).
  Pset `BrasBim_Parede`: `FormaTopo`, `PerfilTopoPosicoes`/`PerfilTopoAlturas`
  (`IfcPropertyListValue`, refeitas a cada gravação: o IfcOpenShell não edita listas),
  `Inclinacao`.
- `core/walls/top.py`: formas (`slope`, `gable`, por ângulo), validação, altura em x,
  menor altura num vão, área lateral e volume sob o topo.
- `rebuild.set_body`: com perfil, `Clipping` (`IfcBooleanClippingResult` DIFFERENCE
  encadeado, um `IfcPolygonalBoundedHalfSpace` por trecho, plano com normal para cima e
  `AgreementFlag` falso; o primeiro e o último trecho vão até 1 m além da planta). Tombada:
  `ExtrudedDirection` (0, sen θ, cos θ), profundidade h/cos θ; `rebuild.band` já devolve a
  faixa alargada por 1/cos θ (junções e planta usam a base alargada).
- Tombada: `_assign_type` associa o `IfcMaterialLayerSet` direto; voltar a 0° refaz o
  `IfcMaterialLayerSetUsage`. Recusa com aberturas (`wall.TILT_WITH_OPENINGS`) e aviso em
  Mensagens para vizinha com inclinação diferente.
- `wall.edit` que muda só o `path` reescala o perfil; espelhar inverte o perfil.
- Painel: "Forma do topo" (o campo "Topo" antigo, pavimento de cima/altura fixa, continua
  para o topo plano), parâmetros de cada forma, "Pontos (distância altura; …)" no livre,
  "Inclinação (°)". Alças 3D `top0`…`topN` (interna anda no plano da parede) e `tilt`.

## Pacote 2 — como ficou (spec/ui 06)
- `core/clip.py` (booleanos com `pyclipr`), `core/layers.py` (regiões por camada com
  prioridade nas junções), `core/materials.py` (estilos, `material.edit`, biblioteca).
- `core/plan.py`: `storey_plan(doc, storey, show_below, detail, show_above)`. Plano
  `storeys.cut_height(storey)` medido da base da parede (`corte − base_offset`). Papéis:
  `wall` (cortada; só escolha, seleção e fantasma), `wall_view` (abaixo do plano, e as
  faces no peitoril, abertas), `wall_above` (tracejada; também vão acima do plano),
  `below` (pavimento de baixo). Topo inclinado: trechos com o topo ≤ plano em vista.
  Nicho atravessado recorta a face (`side` left = face ymax). Porta só aparece se o vão é
  atravessado. `Region(key, rings, fill)` e `Edge(rings, weight, color)`: simplificado
  = união por tipo (quem vem depois, a contínua em X, cobre os outros tipos); por
  camadas = `layers.regions` + `by_material`, divisas 0,18 mm e contorno do tipo por fora;
  tipos sem camadas usam a mancha do tipo.
- `ui/plan_view.py`: regiões com fundo e hachura ancorada na origem do pavimento
  (cruzada = duas famílias); espaçamento < 1 px não desenha (material) e < 3 px vira tom
  (tipo, como antes). `wall` só desenhada como destaque da seleção.
- `PlanContext.detail` / `show_above`; Exibir > Detalhe da planta (Simplificado / Por
  camadas) e Exibir > Elementos acima do plano de corte, guardados em `QSettings`
  (`detalhe_planta`, `acima_do_corte`). Coluna Plano de corte no painel do projeto (vazio =
  padrão); `cmd.edit_storey` troca 1,50 por `None` (o padrão não é gravado).
- 3D: `core/mesh_layers.py` (`split`: faces verticais por trechos da aresta recuada 1 mm;
  demais por interseção em planta e ear clipping; sobras < 1 mm² descartadas).
  `Scene.load(ifc, doc)` guarda o `Document`; paredes com camadas e não tombadas ganham
  `Mesh.parts` por material; cores por `materials.read_style`/`default_style`
  (`scene3d.color_of`). `Session.last_tx`: `material.edit` recarrega o 3D inteiro.
- `ui/materials_dialog.py`: Projeto > Materiais… e botão "…" na tabela de camadas do
  diálogo de tipos (coluna 4). Aplicar (ou trocar de material / fechar) grava
  `material.edit`.
- Mini-barra: some durante zoom (300 ms depois da roda), deslocamento e órbita, no 3D e
  na planta (`navigating`; relato de 2026‑10‑15).

## Pacote 3 — como ficou (spec/ui 09)
- Porta e janela compartilham o código: `doors.py` (ocorrência das duas; `KINDS`,
  `kind_of`, `type_common_defaults`), `commands.py` (`_Kind` DOOR/WINDOW; as funções
  `*_door` servem às duas; `create_window`, `*_window_type`, `hand`), `rebuild.py`
  (`rebuild_door` refaz as duas). Janela: `window_types.py` (estado com `code`,
  `partitioning`, `lining` com montantes/travessas em fração, `panels`), `params.py`
  (divisões, operações, mão e espelho dos caixilhos), `geometry.window_parts` (caixas com
  papel lining/framing/glazing; correr em trilhos alternados, sobrepostos sem montante).
- Cada peça do `Body` (porta e janela) tem `IfcStyledItem` com o `IfcSurfaceStyle` do
  material; `materials.ensure_style` grava o estilo padrão ao gravar o tipo. Estilo de
  material ganhou `transparency` (Vidro 0,6) em `IfcSurfaceStyleShading.Transparency`.
- Planta: `plan.window_symbol` (papéis `window_sash`, `window_glass` + os de porta),
  janela acima do plano em `door_hidden`, etiqueta "J1 / 1,20 × 1,00 / 1,10";
  `plan.window_elevation` desenha o tipo no diálogo. Vão sobre outro vão é recusado
  (`openings.check_fits(..., exclude=)`).
- Interface: `WindowTool` e `DoorTool` (`_FillingTool`), Tab = balão Distância (+
  Peitoril na janela); mão/dobradiças só na barra Opções, painel e mini-barra. Ponto de
  referência em `Tool` (`acquire`, `release_reference`, `reference_marks`,
  `field_anchor`) e `_WallTool._track` (linhas 0/90°, cruzamento com o ponto anterior);
  vértices em `PlanContext.vertices`; a vista chama `acquire` após 0,4 s parada
  (`measure_box.DWELL_MS`, `restart_dwell`). Painel com Peitoril, Verga, Peitoril do
  piso, "Lado interno"; `WindowTypesDialog` com desenho; Exibir > Etiquetas de
  esquadrias (chave `etiquetas_porta` mantida); exclusão avisa "1 porta e 2 janelas".
- 3D: `scene3d._styled_mesh` (cor por peça pelos `IfcStyledItem`, vidro em
  `Mesh.glass`, desenhado com transparência em `View3D._paint_glass`);
  `handles3d.FillingHandle3D` (bordas, peitoril, verga/altura).
- Biblioteca J1–J6 em `ui/session.py`.

## Pacote 4 — como ficou (spec/ui 10)
- Núcleo em `core/structure/`: `profiles.py` (seções, `CardinalPoint`, `PLAN_CARDINAL`:
  posição no quadradinho de 9 pontos vista de cima → número do IFC), `types.py` (tipos
  de pilar/viga com `IfcMaterialProfileSet` e perfil compartilhado; tipo de laje com
  camadas de cima para baixo no estado e de baixo para cima no IFC), `columns.py`,
  `beams.py`, `slabs.py` (estado, leitura e gravação), `common.py` (tipo, pavimento, Pset
  comum, topo, nomes P1/V1, elementos de outra origem), `rebuild.py` (corpo, eixo,
  quantidades; viga reposicionada na cota do topo), `commands.py` (criar, editar, excluir,
  alças, `storey_delete_ops`).
- `assign_type` do IfcOpenShell cria sozinho o `IfcMaterial*Usage` da ocorrência: o
  GlobalId da relação é sempre carimbado depois (`common.stamp_material`).
- Contorno da laje: `slabs.clean` (anti-horário, sem repetidos/alinhados; recusa autointerseção
  e área nula); lido de volta do perfil do corpo. Os comandos já mandam o contorno limpo
  (senão o `before` do desfazer não confere).
- Outra origem: `foreign` = representação (`fragment.dump`), `placement` = posicionamento;
  mover/girar trocam só o `placement` (exige posicionamento relativo ao pavimento);
  espelhar é recusado. Na planta, contorno convexo do corpo.
- `core/transform.py`: as funções públicas separam pilar/viga/laje (`_structure`) das
  paredes e esquadrias (`_*_walls`, as de antes) e juntam tudo numa transação. Espelhar:
  pilar troca `CardinalPoint` de cima/baixo (`mirrored_cardinal`); viga troca face
  esquerda/direita.
- Planta (`core/plan.py`): `_structure` classifica pelo plano de corte do pavimento
  (cotas a partir do pavimento); lajes antes das paredes, pilares e vigas depois;
  `_carve` tira os pilares cortados das regiões e bordas das paredes; a viga leva as duas
  faces (abertas) e uma faixa `beam` para a escolha; tracejado recortado no pilar.
  `pick`: esquadria, pilar, viga, parede, laje; `in_rect`: laje só inteira.
- Interface: `ColumnTool`, `BeamTool` (subclasse de `WallTool`: cada clique cria uma viga;
  Esc/clique duplo encerra), `SlabTool` (polígono/retângulo; Esc tira o último vértice);
  opções próprias por ferramenta (`options_class` em `ToolBox.reset`); barra de espaço vai
  para a ferramenta (`tool.key("space")`) e, se ela não usar, continua deslocando a vista.
  Alças da estrutura em `SelectTool` (`_Grip`, `_structure_handles`, `_structure_build`).
  `toolbars.InsertionPicker` (9 pontos). Painel (`properties._column/_beam/_slab`,
  `_structures`), `types_dialog` (`_PlanStyleDialog` com a representação na planta,
  `ColumnTypesDialog`, `BeamTypesDialog`, `SlabTypesDialog`; representação "Padrão" =
  sem Pset). 3D: `material_color` lê `IfcMaterialProfileSet`; `scene3d._slab_layers` corta
  os triângulos da laje nas cotas das camadas.
- Biblioteca em `ui/session.py`; materiais Contrapiso e Laje pré-moldada em
  `materials.LIBRARY`.
- **Dimensões digitadas** (pedido do revisor, 2026‑10‑16): pilar e viga não usam lista de
  tipos na barra Opções nem no painel; b × h (ou Ø) são digitados. `commands.section_type`
  acha o tipo com a mesma seção, material e representação do tipo de partida, ou gera o
  `*_type.create` na mesma transação ("Pilar 25×60"; nome repetido ganha " (2)").
  `section=` em `create_column`, `create_beam(_chain)` e `edit_element` (só o elemento).
  As ferramentas guardam a seção (`ColumnTool.shape/b/h/d`, `_BeamOptions.b/h`) e o
  `type` só como tipo de partida. A laje continua escolhendo o tipo (camadas).

## Pacote 5 — como ficou (spec/ui 12)
- `core/structure/cuts.py`: `Piece` (prisma: contorno + cotas da edificação), `cuts_of`
  (quem corta este: classes de prioridade maior, pavimentos vizinhos, modos `through`,
  `top`, `bottom`; "inside" só avisa), `Frame` (plano e contorno do semiespaço no sistema
  do corpo; na viga o contorno fica no plano horizontal com z local = direção da viga),
  `clipped`, `removed_volume`/`removed_area` (fatias horizontais, união sem contar duas
  vezes; aberturas entram como `holes`), `sync_relations` (`IfcRelInterferesElements`),
  `cut_by` (quem este corta, para refazer).
- Derivação: `structure/rebuild.derive` refaz os alterados e depois os que eles cortam
  (inclusive paredes, por `walls.rebuild.rebuild_wall`, que também aplica os recortes);
  `common.remove` guarda em `doc.cut_victims` quem o excluído cortava.
- Corpo recortado: `Clipping` (o `SweptSolid` fica como primeiro operando; quem lê a laje
  desembrulha os `IfcBooleanResult`).
- `core/structure/slab_openings.py`: estado no Pset `BrasBim_AberturaLaje` (listas
  `ContornoX`/`ContornoY`, coordenadas do pavimento); corpo e posicionamento refeitos pela
  laje (`refresh`). `commands.outline_of`/`edit_outline` servem à laje e à abertura (as
  alças são as mesmas); `transform._structure` separa as aberturas soltas.
- `core/structure/rooms.py`: furo da união das paredes; afastamento por lado com a
  espessura da parede daquela face. `SlabTool` modo `room`, `SlabOpeningTool` (mini-barra
  "Abertura", em `SELECTION_TOOLS`).
- Etiquetas: `plan.Label` com `kind` e `angle`; `plan.structure_labels`; Exibir >
  Etiquetas de estrutura (`etiquetas_estrutura`).

## Pacote 6 — como ficou (spec/ui 13)
- `storeys.scale`/`paper(storey, mm)`: escala por pavimento; textos, etiquetas, cotas e
  símbolos medem *mm × escala* no modelo; `plan.Label.height` e a planta desenham na
  escala (fonte some abaixo de 3 px).
- `core/annotations/`: `prims.py` (Stroke, Text, Fill; gravação em `IfcGeometricCurveSet`,
  `IfcTextLiteralWithExtent`, `IfcAnnotationFillArea`, com estilos próprios que saem
  junto), `base.py` (registro `Kind`, estado em JSON no Pset `BrasBim_Anotacao`,
  operações genéricas), `drafting.py` (texto, linha, hachura, norte, cota de nível),
  `dimensions.py` (referências, `resolve`, `candidates`, `ref_at`, geometria; `refresh`
  guarda a posição dos pontos presos e marca `lost`), `spaces.py` (`IfcSpace` agregado,
  pé-direito calculado), `rebuild.py` (derivação, roda por último e usa `doc.changed`),
  `commands.py` (criar/editar/excluir, `auto_dimension_wall`, `mapped`).
- `transform`: as funções públicas separam ambientes e anotações (`_annotations`); as de
  antes viraram `_*_core`. Cota copiada fica solta; cota movida junto com o elemento a
  que está presa continua presa.
- Interface: grupo Documentação na barra Ferramentas (`SpaceTool`, `DimensionTool`,
  `LevelTool`, `TextTool` com `ask`, `LineTool`, `HatchTool`, `NorthTool`); clique duplo
  num texto edita (`SelectTool.ask_text`); mini-barra Cotar; escala na barra de estado e
  no painel do projeto; Exibir > Número dos ambientes e Espessuras de linha.

## Pacote 7 — como ficou (spec/ui 14)
- `core/drawings/views.py`: vista = `IfcAnnotation` "VistaDeCorte"/"VistaDeFachada" na
  edificação, estado em JSON no Pset `BrasBim_Vista`, símbolo (`symbol`) gravado como
  `Annotation` e mostrado nas plantas (`plan.views`). Entra nos comandos e nas
  transformações das anotações (`annotations.commands`: `create_view`, `prefix_of`
  "view"; espelhar troca o lado).
- `core/drawings/section.py`: `draw(doc, view)` → `Drawing(items, texts)`; seção pela
  interseção dos triângulos com o plano (anéis por `_chain` + `clip.union`), camadas da
  parede pelas regiões de `layers.regions` cortadas pela linha da vista, camadas da laje
  por faixas de cota; vista além pelo pintor (faces brancas + arestas do sólido, do mais
  longe para o mais perto); `_annotate`: linha de piso, níveis, título. `pick` para a
  escolha na aba.
- Interface: `ui/section_view.py` (aba com zoom, deslocamento e clique; usa
  `PlanView._draw_region` para as hachuras), ferramentas Corte e Fachada (`ViewTool`),
  lista Vistas no painel do projeto (clique duplo abre), painel da vista, Exibir >
  Símbolos de corte (`simbolos_corte`). As abas são refeitas a cada mudança do modelo e
  fechadas quando a vista é excluída.

## Pacote 8 — como ficou (spec/ui 15)
- `core/drawings/sheets.py`: prancha = `IfcAnnotation` "Prancha" na edificação (JSON no
  Pset `BrasBim_Prancha`); `paper`, `frame`, `title_block`, `fold_marks`, `title_items`
  (quadro e carimbo como primitivas em mm), `view_bounds`/`view_size`/`free_spot`;
  comandos `create_sheet`, `edit_sheet`, `add_to_sheet`, `move_on_sheet`,
  `remove_from_sheet`, `delete_sheet`, `edit_project`; `refs_removed_ops` usado ao
  excluir vista (`annotations.commands.delete_ops`) e pavimento (`delete_storey`).
- `ui/paper.py`: `render_sheet` desenha o papel com os "pintores" `_PlanPainter` e
  `_SectionPainter`, que pegam os métodos de `PlanView`/`SectionView`; as espessuras
  usam `unit` (1 na tela; dpi/96 no papel) — `PlanView.unit`, `SectionView.unit`;
  `export_pdf` (QPdfWriter, 600 dpi, uma página por prancha, no tamanho do formato);
  `SheetView` (aba: arrastar vista, botão direito tira da prancha).
- Interface: lista Pranchas e botões no painel do projeto; painel da prancha (pôr
  planta ou vista); Arquivo > Exportar PDF… (Ctrl+P) e Dados do projeto….

## Pacote 9 — como ficou (spec/ui 16, protótipo)
- Pedido do usuário (2026‑10‑16): escrever o pedido dentro do BrasBim e uma IA instalada
  no PC desenhar no modelo aberto. Entrou antes das tabelas.
- `core/assistant/tools.py`: `Registry`/`Tool`/`Context` (doc, `commit`, pavimento);
  ferramentas `describe_model`, `layout_rooms`, `create_walls`, `insert_door`,
  `insert_window`, `create_slab`, `create_space`, `delete_elements`. Recusa (`OpError`)
  volta à IA como `isError`. Esquadria pelo centro: `_wall_at` acha a parede pela faixa
  (25 cm de folga).
- `core/assistant/layout.py`: cômodos (retângulos de eixo a eixo) → paredes externas e
  internas sem duplicar, `open_between`, `merge_kinds`, contorno interno do ambiente.
- `core/assistant/mcp.py`: `Handler` JSON-RPC (initialize, tools/list, tools/call, ping;
  `INSTRUCTIONS` para a IA) e `Server` HTTP em 127.0.0.1 com token Bearer e checagem de
  `Origin`. Sem dependência nova (não usa o SDK do MCP).
- `core/delete.py`: `delete_elements` (saiu de `main_window.delete_transaction`, que agora
  o chama). `walls.commands.create_walls` (paredes soltas numa transação).
  `History.squash(n, label)`: o pedido inteiro vira um passo de desfazer.
- `ui/assistant.py`: `AssistantPanel` (Exibir > Assistente, Ctrl+Shift+A, fechado por
  padrão), `ClaudeCode` (`claude -p --tools "" --strict-mcp-config --mcp-config …
  --allowedTools mcp__brasbim --output-format stream-json`), `_MainThread` (chamada do
  servidor roda na thread da interface), `plan_image`/`view_plan` (PNG com grade de 1 m).
- Teste real: casa de 3 quartos em 78 s, 24 chamadas, ~US$ 0,33 de uso do Claude Code.
- **Memória e edição** (pedido do usuário, 2026‑10‑16): conversa continuada
  (`AssistantPanel.conversation` = `session_id` dos eventos; `--resume`; botão Nova
  conversa; outro projeto esquece), linha de contexto `[BrasBim]` com pavimento e seleção
  (`tools.selection_note`), seleção do que mudou ao fim (`AssistantPanel.touched`).
  Ferramentas `move_wall` (offset com vizinhas + vértices dos ambientes nas faces,
  `_faces_spaces`), `edit_wall`, `edit_opening` (tipo novo sem medidas = medidas do tipo,
  centro mantido), `edit_space` (`refit`), `set_type`, `move_elements`,
  `rotate_elements`, `mirror_elements`. Teste real: três pedidos seguidos (desenhar,
  "aumente a sala 50 cm para o sul", "troque essa porta por uma de correr"), 8–10 s cada.
- Janela: Exibir > Painéis (Projeto, Propriedades, Mensagens, Assistente); Exibir >
  Pavimento acima/abaixo (Page Up/Page Down, `MainWindow.step_storey`); painel Projeto
  com largura mínima de 320 px (coluna Nome cortada).
- `types_dialog._clear_form` agora tira as linhas e apaga por `deleteLater`
  (`_dispose`): `removeRow` corrompia a memória (0xc0000374) de vez em quando no UI91, o
  que apareceu quando a largura do painel Projeto mudou.

## Pacote 10 — como ficou (cobertura simples, RF-ELE-07)
- Núcleo em `core/structure/roofs.py`: `IfcRoof` sem corpo, agregando uma `IfcSlab` por
  água (tipo `IfcSlabType` `ROOF`), peças posicionadas em relação à cobertura, sem
  contenção própria. Estado em JSON no Pset `BrasBim_Cobertura` (`Parametros`, com a
  lista `parts` em ordem) e `AreaProjecao`. Operações `roof.create/delete/edit`;
  `roofs.derive` refaz as coberturas quando o tipo muda.
- Geometria (`faces`): cada água é o plano por um lado do contorno de apoio; a
  superfície é o plano mais baixo em cada ponto (Sutherland–Hodgman em polígono
  convexo), então cumeeira e espigões saem sozinhos. Perfil no topo da água, extrusão
  perpendicular para baixo (`_part_frame`). Duas e quatro águas só em retângulo; quatro
  águas em quadrado = `PAVILION_ROOF`.
- **Peças fora das listas de laje**: `roofs.is_part` filtra `plan._contained`,
  `cuts.nearby` (senão a água "cortava" o topo das paredes), `dimensions.candidates`,
  `rebuild.affected`, `assistant.tools._contained`; `sc.is_structure` é falso para a
  peça e verdadeiro para a cobertura (que entrou em `sc.ELEMENTS` como `roof`). Corte:
  a peça responde pela cobertura (`section._owner`). 3D: `Scene` monta uma malha só para
  a `IfcRoof` (`_roof_mesh`) e ignora as peças.
- `sc.create_roof`, `create_roof_over_walls` (`rooms.building_outline`: contorno externo
  da união das paredes, a edificação toda), `create_roof_rectangle`, `next_roof_name`;
  `edit_element` acerta `parts` quando a forma muda e o `side`; `delete_type` troca o tipo
  pela cobertura. Mover/girar/espelhar remapeiam o lado (`roofs.mapped_side`); copiar dá
  peças novas e "Cobertura N".
- Planta (`plan._roofs`, `roof_prims`): acima do plano, beiral tracejado (escolha só
  perto da linha, papel `roof_edge`); abaixo do plano, planta de cobertura com cumeeira,
  espigões, seta e "i = 30%" (papel `roof`); no pavimento de baixo, o beiral da
  cobertura de cima tracejado (não se escolhe).
- Interface: ferramenta Cobertura (`RoofTool`, depois da Laje; modo inicial Pelas
  paredes; etapa do lado na uma/duas águas com Enter = lado maior), barra Opções
  (forma, modo, inclinação %, beiral, apoio vazio = topo das paredes), painel
  (`PropertiesPanel._roof`), ícones `roof*.svg`. A ferramenta Laje não lista os tipos
  `ROOF`. Biblioteca: Telha cerâmica 5 cm, fibrocimento 3, metálica sanduíche 5, laje
  impermeabilizada 12 (materiais novos em `core/materials.py`).
- Assistente: `create_roof` (sem contorno = sobre as paredes), `edit_roof`,
  `describe_model` lista coberturas e separa tipos de laje e de cobertura; lados contados
  a partir de 1 para a IA.

## Pacote 11 — como ficou (spec/ui 17, tabelas)
- Núcleo em `core/quantities/tables.py`: tabela = `IfcAnnotation` "Tabela" na edificação,
  definição em JSON no Pset `BrasBim_Tabela`; operações `table.create/delete/edit`.
  `CATEGORIES` (walls, doors, windows, fillings, slabs, columns, beams, roofs, spaces),
  `fields_of` (campos com título, unidade, se somam e como ler: sempre das
  `Qto_*BaseQuantities`; código = `Reference` do Pset comum; peitoril = `sill` do vão;
  operação pelos nomes de `fillings.params.*_OPERATION_LABELS`, que saíram de
  `ui/types_dialog.py`). As águas da cobertura não entram em Lajes.
- `compute(doc, tabela ou estado)` → `Result` (colunas, linhas `element`/`group`/
  `subtotal`/`built`/`total`/`built_total`, cada uma com os GlobalIds). Ordem: grupo
  (pavimento pela cota), campo escolhido, depois código/número/nome em ordem natural
  ("J2" antes de "J10"). Campo que não soma mostra "vários" quando muda no grupo.
- Área construída: `rooms.building_rings` (novo; contornos externos de todas as
  edificações do pavimento, sem os furos dos cômodos), usado também por
  `building_outline`. Só no quadro de áreas agrupado por pavimento, na coluna da área útil.
- `TEMPLATES`: esquadrias, áreas, paredes por tipo, estrutura (cria três tabelas numa
  transação), em branco (com a categoria). `edit_table` com troca de categoria ajusta a
  definição (`fitted`). `refs_removed_ops`: excluir pavimento (`delete_storey`) ou tipo
  (`delete_wall_type`, `delete_door_type`, `structure.delete_type`) tira dos filtros.
- `core/quantities/export.py`: CSV (`;`, vírgula, BOM) e XLSX mínimo com `zipfile`
  (estilos negrito e "0.00", cadeias compartilhadas, nome de planilha limpo).
- Interface: lista Tabelas no painel do projeto (Nova tabela… com menu dos modelos,
  Excluir tabela), aba `ui/table_view.py` (`TableView`; clique seleciona, clique duplo
  mostra na planta, Exportar CSV/XLSX), Arquivo > Exportar tabela…; com a aba à frente o
  painel de propriedades é o da tabela (`PropertiesPanel.active_table`, posto por
  `MainWindow._tab_changed`): nome, categoria, colunas (marcar, título, subir/descer
  com os ícones novos `up`/`down`), agrupar, linhas, ordem, totais, área construída,
  filtro de pavimentos e tipos.
- Assistente: ferramenta `table` (só leitura) e linha nas `INSTRUCTIONS` para usá-la
  nas perguntas de quantidade.

## Pacote 12 — como ficou (spec/ui 18, camadas)
- **Nomes:** `core/layers.py`, `tests/test_camadas.py` e `test_interface_camadas.py` já eram
  das **camadas de material** da parede (pacote 2). As camadas de organização são
  `core/display_layers.py`, `ui/layers_panel.py` e `tests/test_*camadas_organizacao.py`.
- Definições em JSON no Pset `BrasBim_Camadas` do projeto (`Parametros`: grupos, camadas,
  combinações, `defaults` por ferramenta); `Document.new` grava o conjunto inicial
  (`display_layers.setup`). Exibição gravada só ao salvar (`Exibicao` + `LayerOn`/
  `LayerBlocked`, `write_display`; `Session.save`), lida em `Session.open`.
- Camada do elemento = `IfcPresentationLayerWithStyle` (`Identifier` = código) com todas
  as representações; águas da cobertura seguem a `IfcRoof` (`display_layers.owner`).
  `Document.element_layers` lembra a camada de cada elemento já visto (inclusive os
  excluídos): desfazer a exclusão devolve a camada sem mexer nos comandos de excluir.
- Derivação `sync` (`register_derive(..., last=True)`: roda depois de todos os corpos):
  elemento novo → camada padrão da ferramenta; representação nova herda a camada;
  representação que saiu do produto é tirada da camada e apagada (o `remove_deep2` não
  apaga o que a camada ainda cita); camada sem itens perde a entidade.
- Operações: `layer.create/delete/edit`, `layer_group.*`, `layer.order`, `layer.assign`,
  `layer_combination.*`, `layer.defaults`, `layers.setup/teardown` (organizar arquivo antigo
  ou de outra origem: `display_layers.organize`, chamado em `Session.open`; camadas que já
  estavam no arquivo vão para o grupo "Importadas" e são adotadas pelo nome).
- `display_layers.inherit`: copiar, espelhar com cópia e dividir acrescentam `layer.assign`
  para a cópia ficar na camada do original (por ferramenta e ordem de criação).
- Filtros: `plan._contained(storey, cls, doc)`, `_documentation`, símbolos de vista,
  `section.draw`, `Scene.apply_layers` (malhas guardadas em `_hidden`, sem tesselar de
  novo), `assistant.tools._contained`. Vão de parede oculta conta como atravessado (a
  esquadria segue a própria camada). `Plan.locked`: `pick`/`in_rect` pulam os
  bloqueados; `Session.select` tira ocultos e bloqueados; `Session.run` recusa criar em
  camada padrão bloqueada e mostra a oculta (`_show_created`).
- Interface: painel solto (Exibir > Painéis > Camadas, Ctrl+Shift+L, `MainWindow.layers`),
  campo Camada no painel de propriedades (seção Organização) e na barra Opções
  (`toolbars.tool_kind`), menu do botão direito (ocultar/bloquear/isolar a camada do
  elemento), combinação por vista da prancha (painel da prancha, `sheets.item_display`).
  Ícones `eye`, `eye_off`, `lock`, `unlock`, `layer_group`, `layer_new`, `layers_all`.
- `mcp.Server.do_POST` lê o corpo antes de responder (401/404 sem ler derrubavam a conexão
  no Windows: era a falha intermitente do AS06); corpo acima de 16 MB → 413.

## Pacote 13 — como ficou (objetos paramétricos)
- Núcleo em `core/objects/`: `formula.py` (linguagem própria com vírgula decimal e `;`,
  analisador sem `eval`; `parse`, `names`, `infer`, `evaluate`, `calc`), `definition.py`
  (definição em dicionário: parâmetros, peças, símbolo; `problems` com o lugar de cada
  erro, `evaluate` em ordem de dependência, `solids`, `nested`, `symbol_items`, `bounds`,
  `handle_shift`), `types.py` (`object_type.*`: tipo IFC da categoria **sem**
  `RepresentationMaps`, Pset `BrasBim_DefinicaoObjeto` com a definição e os valores em
  JSON, `BrasBim_Parametros` com os valores como propriedades IFC, Pset comum com
  `Reference` e nominais, `IfcMaterialConstituentSet` por papel, origem por
  `IfcRelAssociatesLibrary`), `elements.py` (`object.*`: corpo por ocorrência,
  `IfcStyledItem` por peça, `Annotation` do símbolo desenhado, `Box`; aninhados
  agregados com GlobalIds `guid.derived(objeto, "part/<peça>/<cópia>")`), `shapes.py`
  (peças → itens IFC, com o espelho na própria geometria), `hosting.py` (preso à parede:
  posição relativa à parede, `IfcRelConnectsElements`, vão `IfcOpeningElement` com o Pset
  `BrasBim_VaoObjeto`), `plan.py` (papéis `object`, `object_fill`, `object_above`,
  `object_box`, `plant`, `plant_fill`; símbolo automático por altura do topo),
  `mesh.py` (malha aproximada para prévia e miniatura), `library.py` (`IfcProjectLibrary`
  + amostras; `Index`, `load` manter/substituir/novo, `update_from`, `save`),
  `builtin.py` (27 objetos, 53 tipos; `scripts/gerar_biblioteca.py` grava
  `brasbim/library/objetos/`), `commands.py` (criar, editar, trocar tipo, alça,
  soltar/prender, `apply_definition` do editor), `rebuild.py` (tipo e parede mudados
  refazem as ocorrências).
- `walls.openings.of_wall` deixa de fora o vão do objeto; `of_wall(..., objects=True)`
  no desenho, no corpo, nas quantidades e na sobreposição.
- Integrações: excluir (objetos antes das paredes; a parede leva os presos, cascata
  "N objetos"), transformações (`transform._with_objects`), camadas (`object:<categoria>`;
  Mobiliário e Vegetação no conjunto inicial, Equipamentos criada no primeiro uso por
  `commands.layer_ops`), planta (`plan._objects`, escolha pela caixa), 3D (aninhados na
  malha do objeto de fora), cortes, tabelas (categorias de objeto, `param:<nome>`, modelo
  "Lista de mobiliário e equipamentos"), assistente (`list_objects`, `insert_object`,
  `edit_object`).
- Interface: ferramenta Objeto (`tools.ObjectTool`, depois da Cobertura), barra Opções
  (`object_widgets.TypePicker` com busca e miniaturas), painel Biblioteca de objetos
  (`library_panel.py`, Ctrl+Shift+B, pastas do usuário em `QSettings`
  `biblioteca/pastas`), lista Objetos no painel Projeto (menu de ações dos tipos), painel
  de propriedades (`_object`, `_objects`), alças `obj:<parâmetro>` no `SelectTool`,
  mini-barra (Trocar tipo, Editar tipo, Selecionar todos deste tipo, Soltar da parede),
  menu do botão direito, Exibir > Etiquetas de objetos (`etiquetas_objetos`), Projeto >
  Biblioteca de objetos / Pastas da biblioteca / Novo objeto…, editor
  (`object_editor.py`) e diálogo Editar tipo (`object_dialogs.py`). Ícones `object`,
  `library`, `swap_type`, `select_same`, `detach`, `view_plan`, `view_3d`, `folder`.

## Pacotes 14–16 — como ficou (spec/ui 19 e 20)
- `core/annotations/drawing2d.py`: `circle2d`, `arc2d` (`arc_from_points`), `spline2d`
  (Catmull-Rom), `radius_dim` (presa por `ref` a círculo, arco ou parede em arco;
  `curve_of`, `curves_near`, `refresh_radius` na derivação), `angle_dim`, `label` (`field`
  free/type/name/code; `label_text`) e `revision` (nuvem, `next_revision`). Camadas
  padrão no conjunto inicial e `display_layers.FALLBACK` (ferramenta parecida) em
  arquivo antigo. Ferramentas em `tools.py` (`_ClickTool`, `CircleTool`, `ArcTool`,
  `SplineTool`, `RadiusDimTool`, `AngleDimTool`, `LabelTool`, `RevisionTool`).
- `core/grids.py`: `IfcGrid` na edificação, estado em `BrasBim_Eixos`, `grid.*`;
  desenho como anotação em todo pavimento (`plan._documentation`), cruzamentos no snap
  (`PlanContext.grid_points`), transformações (`transform._grid_ops`). `GridTool`.
- Vão e nicho: `WallOpeningTool` (subclasse de `_FillingTool`), papel `opening_box` na
  planta (escolha), `walls.commands.is_wall_opening`/`delete_opening`, painel
  `_wall_opening`; a mini-barra do vão só tem Excluir.
- `core/structure/skylights.py`: `IfcWindow` `SKYLIGHT` que preenche um vão (Pset
  `BrasBim_VaoClaraboia`, fora de `slab_openings.of_slab`) na laje ou na água da
  cobertura sob o centro, no plano do topo (`support`); `skylight.*`, derivação pela
  laje/cobertura/tipo, cascata ao excluir o apoio, acompanha mover/girar o apoio
  (`transform._skylight_ops`). `SkylightTool`, painel `_skylight`, papéis
  `window_skylight`/`window_glass`.

## Pacote de precisão — como ficou (spec/ui 23)
- `core/snap.py`: `SnapIndex` (arestas em baldes de 2 m, extremidades, círculos/arcos
  exatos) feito por `build_index(doc, storey, plan)` a partir de `Plan.shapes` e dos
  traços de `Plan.annotations` (desenho importado incluído); `polyline_parts` não trata
  como extremidade vértice com desvio < 12° (curva aproximada). `snap(...)` ganhou
  `index`, `origin` (perpendicular, tangente) e `kinds`; tipos e prioridade em `KINDS`,
  `_TIERS`, `KIND_LABEL`. Sem índice, o comportamento antigo continua igual.
- `PlanContext`: `index`, `snap_kinds`/`snap_off` (Exibir > Atração, `QSettings`
  `atracao/tipos` e `atracao/desligada`), `axis_lock` + `toggle_axis` (setas;
  `Snap.source` = ponto atraído antes da projeção), `last_tool` (Enter na seleção vazia,
  `SelectTool.key` → sinal `tool_requested` das vistas). Marcadores em
  `plan_view.snap_marker`.
- `core/edits.py`: `offset_element` (parede reta e em arco, linha 2D, círculo, arco,
  laje, ambiente, hachura; copiar ou mover), `trim_extend` (linha 2D por trechos entre
  cruzamentos; parede reta até o eixo da outra; Shift estende), `fillet` (linhas com
  raio → arco 2D novo; paredes só raio 0). `walls.commands.create_wall_path` e
  `set_wall_ends` (junções pelas regras de sempre).
- `core/select_similar.py` (`CRITERIA`, `similar`): mini-barra "Selecionar semelhantes"
  (substituiu "Selecionar todos deste tipo") e Editar > Selecionar semelhantes.
- Interface: `OffsetTool`, `TrimTool`, `FilletTool` (grupo Edição na barra Ferramentas,
  `toolbars.EDIT_TOOLS`, ícones `offset`, `trim`, `fillet`, `palette`), Editar > Girar 90°
  (`MainWindow.rotate_quarter`, Ctrl+R / Ctrl+Shift+R), paleta Ctrl+K
  (`ui/command_search.py` sem Qt, com `SYNONYMS`; `ui/command_palette.py`).
- Fica para depois (spec §10): prévia do aparar, rastreamento a 45°, aritmética no
  quadro, guias, cota viva, cópia em série, arco entre paredes.

## Roteiro a partir da pesquisa (2026‑10‑21)
Base: `reports/Pesquisa Archicad Revit AutoCAD.md`, seção "Recomendações priorizadas"
(23 itens, valor × esforço). Tese: o BrasBim ganha na **última milha brasileira**
(prancha da prefeitura, quadro de áreas, quantitativo SINAPI, IFC que o engenheiro usa) e
na velocidade de entrada, não copiando a profundidade de modelagem dos três. Cada item
passa pelo fluxo spec → implementação com testes de IFC; conferir as fontes marcadas
"conferir" antes de citá-las na spec. Ordem revista em 2026‑10‑23 a partir de
`reports/Comparacao BrasBim x pesquisa.md` (aprovada pelo revisor): a precisão subiu
para o item 1.

1. **Pacote de precisão** — **feito em 2026‑10‑23** (spec/ui 23, em revisão; o que
   segue é o escopo original). Itens 4 e 15 do relatório; comparação §3.1–3.2 e §4:
   - snap em todos os elementos visíveis e no desenho importado (lajes, pilares, linhas
     2D, eixos), com interseção, perpendicular, centro e tangente, e marcador por tipo
     (RF‑DES‑02, que o `REQUISITOS.md` põe no MVP);
   - número digitado sem Tab (a tecla numérica abre o quadro de medidas já preenchendo),
     setas travando X/Y, Enter no vazio repetindo a última ferramenta;
   - deslocar paralela, aparar/estender e concordar (raio 0 = canto vivo), para linhas 2D
     e paredes;
   - selecionar semelhantes por critérios IFC (classe, tipo, PredefinedType, material,
     pavimento, camada) em todas as categorias (RF‑NUC‑09);
   - girar 90° por atalho e paleta de comandos (Ctrl+K) com busca em pt‑BR.
   Depois, no mesmo eixo: alinhamento a 45° e ângulos configuráveis, aritmética no quadro
   de medidas, linhas‑guia, cota viva editável, cópia em série (RF‑NUC‑06).
2. **Pacote "projeto legal"** (itens 1, 2, 3 e 8 do relatório): status de intervenção
   por elemento (`Pset_*Common.Status` + Pset próprio para "a regularizar"/"a
   transformar"), **perfil municipal** versionado (escalas, selo, cores — invertidas entre
   cidades —, notas, limite de PDF, espaço do carimbo digital), **quadro de áreas**
   automático por regras municipais (computável, CA, TO, permeabilidade), memorial
   descritivo e quadro de esquadrias. Junto: regras gráficas por critério (base das cores
   de intervenção), **ambiente que se refaz sozinho** quando as paredes do contorno mudam
   (hoje só com a IA; sem isso o quadro de áreas fica errado), o novo fluxo de pôr vista
   na prancha com grade e alinhamento (pendência do revisor) e o **export DXF**.

Ajustes pequenos, a qualquer momento: vistas 3D padrão e câmera salva; pegar todas as
curvas de uma camada no terreno; código curto nas portas da biblioteca; teste de nó com
3+ paredes compostas; validação IDS se o `ifctester` do IfcOpenShell servir (conferir).

3. **Coordenação openBIM** (itens 5, 6, 7): validação IDS embutida (IDS dos cadernos
   brasileiros), export de compatibilidade IFC4 RV/IFC2x3 com bateria de ida e volta
   (Revit, Archicad, Eberick, QiBuilder), IFC de outras disciplinas como referência
   somente leitura, BCF 3.0.
4. **Documentação por regras** (item 9): cotas e etiquetas automáticas, numeração por
   regra, tabelas como planilha, vistas na prancha com grade.
5. **Quantitativos por critério de serviço** (item 10): vãos com limiar, revestimentos por
   ambiente, `IfcElementQuantity`, NBR 15965 e código SINAPI.
6. **Refino dos elementos** (itens 11, 12, 16): escada que recalcula com regras
   brasileiras e guarda-corpo de vidro; terreno com linhas de quebra, natural ×
   projetado, corte e aterro, platô com talude, SIRGAS 2000; nós de paredes compostas,
   laje inclinada, beirais diferentes.
7. **Desempenho do viewport e benchmark aberto** (item 13), **vistas 3D padrão e câmera
   salva** (pendências do MVP), apresentação regenerável e glTF (item 20).
8. **Biblioteca IFC brasileira** (item 14), histórico com autoria e opções (17),
   assistente com plano e diff (18), ponte 2D → BIM (19).
9. Depois: NBR 15575 simplificada (21), DWF para SP se ainda exigido (22), MEP mínimo e
   estrutura tipada (23). **Não fazer agora**: cálculo estrutural/instalações por NBR,
   render próprio, multiusuário no navegador, generativo, scan-to-BIM.

**Segunda rodada de pesquisa** (lacunas listadas no relatório: normas ABNT por acesso
legítimo, outras prefeituras, Bombeiros, IFC 4.3 com 403, softwares brasileiros, recursos
clássicos do AutoCAD) quando o limite de buscas da sessão permitir
(`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, decisão do revisor).

## Próximos passos anteriores (histórico)
Pedido do revisor (2026‑10‑16): seguir para o refinamento sem teste de uso agora (o teste
de uso fica para quando o programa estiver mais completo) e já incluir as ferramentas de
documentação do desenho técnico (`spec/REQUISITOS.md` §8).

0. Revisor confirmar a correção do `CardinalPoint` do pilar (`pilar.md` §11 (e)).
0b. Revisor testar o assistente (Exibir > Painéis > Assistente, Ctrl+Shift+A) e decidir
   os pontos da spec 16 §9;
   depois: aprovar a spec, pôr RF-IA-01 a 04 em `REQUISITOS.md`.
1. ~~Pacote 5~~ concluído.
2. ~~Pacote 6~~ concluído — documentação 1, anotação da planta: ambientes (`IfcSpace`, RF-AMB-01 a
   03), cotas lineares associativas e cota automática de paredes e vãos, cota de nível
   (RF-DOC-05), textos, linhas e hachuras 2D (RF-DOC-06), norte e símbolo de nível
   (RF-DOC-07), escala da vista (RF-DOC-04), espessuras de linha por categoria (RF-DOC-03).
3. ~~Pacote 7~~ concluído — documentação 2: cortes e fachadas gerados do modelo, com linhas ocultas
   removidas, e o símbolo de corte na planta (RF-DOC-02, RF-DOC-07).
4. ~~Pacote 8~~ concluído — documentação 3: pranchas A0–A4 com margens, carimbo editável e várias
   vistas (RF-DOC-09), exportação PDF vetorial (RF-DOC-10).
4b. ~~Cobertura simples (RF-ELE-07)~~ concluída (pacote 10); ~~tabelas~~ concluídas
   (pacote 11, RF-QTD-01 a 03 e 05). Agora: aprimorar o assistente dentro do software
   (pedido do revisor); depois mobiliário básico, salvamento automático, camadas e
   vistas 3D padrão.
4c. Pedido do revisor (2026‑10‑20), ferramentas básicas, nesta ordem:
   ~~12 camadas~~ concluído · ~~13 objetos paramétricos e biblioteca~~ concluído
   (pacote 13) ·
   14 desenho 2D: círculo, arco, curva livre (spline), cota de raio e de ângulo, rótulo,
   marcador de alteração · 15 eixos de projeto (`IfcGrid`) · 16 vão livre na parede
   (ferramenta) e claraboia · 17 escada e guarda-corpo/corrimão · 18 terreno (malha) ·
   19 detalhe ampliado · 20 pele de vidro · 21 forma livre (RF-ELE-15). Vistos no print
   da barra do revisor, opcionais: casca, luminária, vista interna, câmera (vista 3D
   salva), imagem inserida, ponto de referência. Texto, linha, hachura, cota linear e
   de nível já existem. Depois: salvamento automático, vistas 3D padrão, aprimorar o
   assistente (mais ferramentas; mais criativo).
5. **Teste de uso completo** (pedido do revisor: com o programa mais completo): modelar
   uma casa do começo ao fim e imprimir as pranchas; anotar em `feedback/`.
6. Depois (V1): detalhe por escala, DXF, detalhes ampliados, revisões, tabelas na prancha,
   conjuntos por etapa, pranchas de prefeitura (RF-DOC-08, 11 a 16); alças da estrutura
   no 3D.

## Pendências
- **Pacotes 17–18 concluídos (2026‑10‑21)**, spec `spec/elementos/escada-terreno.md` em
  revisão: núcleo (`core/structure/stairs.py`, `railings.py`, `core/terrain.py`), planta,
  corte, excluir, transformações, ferramentas, barra Opções, painéis, ícones e 3D
  (`scene3d`: `IfcStair` numa malha só com `_stair_mesh`, peças com cor por
  `_styled_class`, terreno com só o contorno nas arestas). Guarda-corpo de fora contorna
  o patamar em L e U (`railing/landing`). Testes ET01–ET09. Sem plataforma (corte e
  aterro) no terreno; sem degrau em leque.
- **Importar desenho DXF/DWG feito (2026‑10‑21, spec/ui 22):** `core/imports/dxf.py`
  (ezdxf; DWG pelo ODA File Converter ou `dwg2dxf`, chamados à parte; **o conversor não
  está instalado nesta máquina**), anotação `reference2d` por camada
  (`core/annotations/reference.py`, `compact`: `IfcIndexedPolyCurve`), camada inicial
  Levantamento, `ui/import_dialog.py`, Arquivo > Importar desenho.
- **Terreno por contorno e curvas feito (2026‑10‑21, escada-terreno.md §4 revisada,
  TR01–TR08):** estado com `boundary`, `boundary_z`, `curves`; superfície por Delaunay do
  GEOS (`terrain.surface`) com correção de patamar falso; ferramenta Terreno com modos
  Contorno/Pontos cotados; mini-barra do terreno com **Pegar linhas**
  (`PickCurvesTool`, clique ou Enter, traz a cota do DWG) e **Cota das curvas**
  (`CurveLevelTool`, sugestão = última + intervalo). Pendente: pegar várias linhas por
  janela; triangulação com as curvas como restrição (hoje ponto no meio do patamar).
- **Salvamento automático feito (2026‑10‑21, spec/ui 21):** `ui/recovery.py` (sem Qt) +
  `Session.backup/heartbeat/orphan_backups/recover`; cópia IFC separada do arquivo do
  projeto na pasta de dados do usuário (`QStandardPaths.AppLocalDataLocation/recuperacao`),
  a cada 5 min por padrão (Arquivo > Salvamento automático); sinal de vida a cada minuto;
  na abertura, `MainWindow.offer_recovery` oferece a cópia órfã mais recente. A gravação
  roda na linha da interface (medir em projeto grande). **Próximo:** vistas 3D padrão,
  câmera salva e o fluxo de pôr vista na prancha (a combinar com o revisor).
- Objetos (pacote 13): arrastar da biblioteca para a planta não existe (clique duplo
  ativa a ferramenta); a prévia e as miniaturas são aproximadas (sem OpenGL); o editor não
  desenha na prévia (V2); o símbolo automático não mostra o que fica sob uma peça mais
  alta; objeto preso só em parede reta e não tombada; parede dividida não leva o objeto
  para o trecho novo; vão do objeto não acompanha "copiar parede" sozinho (vai com o
  objeto); `Qto_*` não gravados (§8); tipo de outra origem sem a definição fica como está.
- Pranchas (revisor, 2026‑10‑20): pôr a vista na prancha (painel de propriedades da
  prancha > Pôr na prancha) "não está bom ainda"; refazer o fluxo depois, a combinar.
  Vista 3D com câmera salva ainda não existe.
- Camadas: arrastar no painel só testado pelo núcleo (`layer.order`/`layer.edit`, CM19);
  clique em elemento bloqueado não chega ao menu do botão direito (para desbloquear, só
  pelo painel); `inherit` liga cópia e original por ordem (se a conta não fecha, usa a
  camada comum ou a padrão); vista de prancha cuja combinação foi excluída volta a
  "Como na janela" sem aviso; `hidden_ids` percorre todos os elementos a cada planta
  (medir em projeto grande).
- Tabelas: as portas da biblioteca não têm código curto (o `Reference` é o nome do tipo,
  "P1 – giro 80", como na etiqueta da planta); as janelas têm ("J1"). Sem tabela na
  prancha, fórmulas e filtro por propriedade (V1); o pátio interno fechado por paredes
  conta na área construída.
- Cobertura: sem ajuste das paredes ao telhado (oitão: usar o topo em empena da parede);
  telhados em L/T, mansarda e beiral por lado ficam para o V1; a água com várias
  camadas aparece de uma cor só no 3D; alça do contorno numa cobertura de duas/quatro
  águas que deixa de ser retângulo é recusada.
- Assistente: a conversa não sobrevive a fechar o BrasBim; sem aviso de privacidade; só
  o conector Claude Code; a IA não cria pavimentos nem estrutura (cobertura já cria); edição
  manual durante o pedido impede o agrupamento no desfazer; ambientes só acompanham a
  parede movida pela IA (`move_wall`), não a movida à mão.
- Specs 01 §5.5/§6, 03 §4.2 e 07 §2.2 ainda dizem "Tab troca as dobradiças"; a spec 09
  §2.2 mudou isso (atualizar o texto delas).
- Peitoril fixado pelo balão não atualiza na hora o campo da barra Opções.
- Excluir o estilo de um material deixa o `IfcSurfaceStyle` ainda usado pelas peças das
  esquadrias (fica solto do material).
- Recortes: elemento inteiro dentro da altura do outro fica sem recorte (aviso); parede
  de topo inclinado ou tombada não é recortada; cada rebuild compara com todos os
  elementos dos pavimentos vizinhos (medir em projeto grande); `NetSideArea` da parede
  não desconta recortes; abertura de porta sob um recorte pode ser descontada duas vezes.
- Laje pelo cômodo: a laje não fica ligada às paredes (V1).
- Excluir pavimento e desfazer: a propriedade `PavimentoTopo` volta ao Pset da parede
  no fim da lista (ordem diferente, conteúdo igual; o `snapshot` dos testes acusa).
- Cortes: o desenho é refeito inteiro a cada mudança do modelo (medir em projeto
  grande); sobreposição cíclica no pintor fica como está; sem cotas nem textos dentro do
  corte; zmin/zmax só decidem em que plantas o símbolo aparece.
- Documentação: cota só prende em parede reta; pontos livres da cota sem alça (só o
  afastamento); texto de várias linhas só pelo clique duplo; vários ambientes ou
  anotações selecionados não têm painel próprio; as espessuras da NBR 8403 e as
  convenções da NBR 6492 seguem sem conferência com o texto das normas.
- Estrutura: painel com vários pilares/vigas/lajes só edita tipo (e topo da laje) e
  propriedades comuns; alças da estrutura só na planta; laje "Por camadas" na planta usa a
  representação do tipo, não as camadas; tipo de parede em uso continua sem pedir
  substituto (o de pilar/viga/laje pede).
- Ponto de referência fora de Mover/Copiar/Girar/Espelhar (spec 09, ponto (g)).
- Janela em parede em arco, 4+ caixilhos e `TRIPLE_PANEL_*` laterais: V1.
- Dividir parede com topo inclinado é recusado (falta repartir o perfil e juntá-lo de
  volta no `wall.merge`).
- Painel com várias paredes não mostra forma do topo nem inclinação.
- Planta e 3D por camadas: parede em arco sem vãos na planta (como antes) e sem corte por
  trecho no topo inclinado; parede tombada fica com uma cor só no 3D.
- Prioridade das camadas em junção de tipos diferentes em X: o contorno por tipo usa a
  ordem de desenho, as camadas usam a prioridade (podem divergir).
- 3D: cada edição recalcula as regiões do pavimento inteiro (sem cache entre edições);
  medir em projeto grande.
- Excluir porta de outra origem.
- Mover porta deve recalcular as vizinhas da parede do vão.
- Nicho e vão livre sem ferramenta na interface.
- 3D, fora da spec 07: seleção por janela, alças, arrastar para mover; parede em arco sem
  campos de medida.
- Vista 3D: a mini-barra é filha do `QOpenGLWidget`; nunca movê-la dentro do `paintGL`
  (deixava rastros ao orbitar; corrigido em 2ee0024).
- Testes de interface: a planta do `window` mede 464 × 530 px; com a origem do fixture
  (100, 600), pontos com y < 1,4 m caem fora e `QTest.mouseMove` não chega (os testes da
  spec 07 mudam a origem).

## Gosto do usuário
Aparência: cores, fonte e folha de estilo só em `ui/theme.py` (nunca cor fixa nos
módulos; teste AP02). Tema sempre claro, cobalto como único destaque.
Interface limpa: ícones, opções só da ferramenta ativa, ações só com seleção; nada fixo
poluindo a tela. Desenvolvimento guiado pelo uso: no início da sessão, ler
`feedback/*.md` (observações) e `feedback/diarios/erro-*.md` (erros).
