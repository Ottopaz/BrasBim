# Contexto de desenvolvimento

Estado do trabalho para retomar numa sessão nova. Atualizar ao fim de cada etapa.
Regras do projeto: `CLAUDE.md` e `cleanroom/PROCESSO.md` (nunca acessar `_restrito/` nem
`tools/`).

*Atualizado em 2026‑10‑16 (pacote 9: assistente com IA, com memória e edição; spec em revisão).*

## Comandos
| Para | Comando |
|---|---|
| Testes (446 passando) | `.venv/Scripts/python -m pytest -q -p no:faulthandler` |
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

## Próximos passos (nesta ordem)
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
4b. Cobertura simples (RF-ELE-07): spec `spec/elementos/cobertura.md` em revisão
   (pontos §12 a–f); depois quantitativos e tabelas (RF-QTD-01 a 03, 05);
   em seguida mobiliário básico, salvamento automático, camadas e vistas 3D padrão.
5. **Teste de uso completo** (pedido do revisor: com o programa mais completo): modelar
   uma casa do começo ao fim e imprimir as pranchas; anotar em `feedback/`.
6. Depois (V1): detalhe por escala, DXF, detalhes ampliados, revisões, tabelas na prancha,
   conjuntos por etapa, pranchas de prefeitura (RF-DOC-08, 11 a 16); alças da estrutura
   no 3D.

## Pendências
- Assistente: a conversa não sobrevive a fechar o BrasBim; sem aviso de privacidade; só
  o conector Claude Code; a IA não cria pavimentos, estrutura nem cobertura; edição
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
