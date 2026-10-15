# Contexto de desenvolvimento

Estado do trabalho para retomar numa sessão nova. Atualizar ao fim de cada etapa.
Regras do projeto: `CLAUDE.md` e `cleanroom/PROCESSO.md` (nunca acessar `_restrito/` nem
`tools/`).

*Atualizado em 2026‑10‑15 (pacote 3 concluído: janela e ponto de referência, spec/ui 09).*

## Comandos
| Para | Comando |
|---|---|
| Testes (279 passando) | `.venv/Scripts/python -m pytest -q -p no:faulthandler` |
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

## Próximos passos (nesta ordem)
1. Uso do pacote 3 pelo revisor e ajustes pelo retorno em `feedback/`.
2. Combinar com o revisor o próximo pacote (candidatos: laje, cotas, nicho/vão livre na
   interface, pendências abaixo).

## Pendências
- Specs 01 §5.5/§6, 03 §4.2 e 07 §2.2 ainda dizem "Tab troca as dobradiças"; a spec 09
  §2.2 mudou isso (atualizar o texto delas).
- Peitoril fixado pelo balão não atualiza na hora o campo da barra Opções.
- Excluir o estilo de um material deixa o `IfcSurfaceStyle` ainda usado pelas peças das
  esquadrias (fica solto do material); estilo de corte do Vidro da biblioteca aparece
  como "nenhum" ao ler de volta (conferir `_read_cut` para corte sólido).
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
Interface limpa: ícones, opções só da ferramenta ativa, ações só com seleção; nada fixo
poluindo a tela. Desenvolvimento guiado pelo uso: no início da sessão, ler
`feedback/*.md` (observações) e `feedback/diarios/erro-*.md` (erros).
