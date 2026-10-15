# Contexto de desenvolvimento

Estado do trabalho para retomar numa sessão nova. Atualizar ao fim de cada etapa.
Regras do projeto: `CLAUDE.md` e `cleanroom/PROCESSO.md` (nunca acessar `_restrito/` nem
`tools/`).

*Atualizado em 2026‑10‑15 (spec 07 implementada).*

## Comandos
| Para | Comando |
|---|---|
| Testes (192 passando) | `.venv/Scripts/python -m pytest -q -p no:faulthandler` |
| Lint | `.venv/Scripts/ruff check brasbim tests exemplos scripts` |
| Aplicativo | `.venv/Scripts/python -m brasbim.ui.app [arquivo.ifc]` |
| Ícones | `.venv/Scripts/python scripts/gerar_icones.py` |
| Commit | `git commit -s` (DCO) |

## Specs
| Spec | Situação |
|---|---|
| `spec/elementos/parede.md`, `porta.md`, `janela.md` | aprovadas (parede e porta implementadas; janela não) |
| `spec/01-modelo-de-dados.md` | rascunho vivo, atualizado a cada operação nova |
| `spec/ui/01` (0.1), `02-edicao` (0.2), `03-barras-e-icones`, `04-painel-de-propriedades`, `05-acabamento-parede-porta` | aprovadas e implementadas (testes UI01–UI50) |
| `spec/ui/06-planta-por-camadas` | **aprovada** (pontos (a)–(h) aceitos); implementação **em andamento** (retomar em `core/layers.py`) |
| `spec/ui/07-medidas-e-edicao-no-3d` | aprovada e implementada (testes UI61–UI72) |
| `spec/ui/08-parede-no-3d-topo-e-inclinacao` | **aprovada**; §2 implementado; alças, topo e tombada em andamento |

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
- Vista 3D com seleção por clique, as mesmas ferramentas da planta (ponto = x, y do
  elemento atingido ou do plano do pavimento), fantasma das transformações, mini-barra e
  menu do botão direito (Mostrar na planta / Mostrar no 3D / Enquadrar). Câmera e raio
  sem Qt em `ui/scene3d.py` (`Camera`, `Scene.pick`, `ray_plane`).

## Pacote 2 em andamento (spec/ui 06)
Feito:
- `brasbim/core/clip.py`: booleanos 2D com `pyclipr` (união, interseção, diferença,
  afastamento, recorte de polilinhas, semiplano). `pyclipr` instalado e em `pyproject.toml`.
- `storey.*` com `cut_height` (Pset `BrasBim_Pavimento`, `AlturaPlanoCorte`;
  `storeys.cut_height()`); `edit_storey` lê o estado completo. 179 testes passando.

Falta (desenho combinado):
- `core/layers.py`: regiões por camada. Base de cada camada = faixa crua da camada
  (prolongada pela tangente nas pontas) ∩ peças da própria parede. Nas pontas com junção
  (ATSTART/ATEND), extensão = faixa ∩ peças da vizinha, cortada no semiplano antes da
  primeira camada da vizinha com prioridade ≥ (menor projeção ao longo da tangente de
  saída). Atribuir por prioridade decrescente (desempate: contínua em X, mais espessa,
  GlobalId, índice), cada uma = (base ∪ extensão) − já atribuído. Prioridade vazia = 0.
- `core/plan.py`: corte relativo à base da parede (hoje usa 1,50 fixo sem descontar
  `base_offset`); papéis `wall` (cortada), `wall_view` (abaixo), `wall_above`
  (tracejada), linhas de peitoril e vão acima; nicho recortado; `Region` (mancha por
  tipo no simplificado; por material no por camadas) e `Edge` (contorno externo por tipo).
  Na vista, `wall` só desenha quando selecionada (sobreposição).
- `core/materials.py`: estilos (spec 06 §4), operação `material.edit` (id = nome),
  `IfcMaterialDefinitionRepresentation` com `IfcSurfaceStyle` (Model/Body) e
  `IfcFillAreaStyle` (contexto novo Plan/Body); biblioteca §4.4 gravada no projeto novo
  e no exemplo; registrar em `ops/base.HANDLER_MODULES`.
- 3D: recorte dos triângulos do corpo pelas regiões das camadas (faces verticais por
  intervalos ao longo da aresta, recuadas 1 mm para dentro; demais por interseção em xy);
  `Scene` precisa do `Document`.
- Interface: Exibir > Detalhe da planta, Exibir > Elementos acima do plano de corte,
  coluna Plano de corte no painel do projeto, Projeto > Materiais… e botão na tabela de
  camadas.
- Testes UI51–UI60; atualizar `spec/01-modelo-de-dados.md` (`cut_height`, `material.edit`).

## Próximos passos (nesta ordem)
0. **Spec 08** (aprovada em 2026‑10‑15): alças da parede no 3D → topo
   inclinado/empena → parede tombada. Exige alterar `parede.md` (§6 da spec 08).
1. **Pacote 2:** implementar `spec/ui/06-planta-por-camadas.md` depois de aprovada:
   detalhe da planta (simplificado e por camadas), prioridade das camadas nas junções,
   plano de corte por pavimento, paredes abaixo e acima do plano, estilos de material
   no IFC (`IfcSurfaceStyle`, `IfcFillAreaStyle`), operação `material.edit`, cor por
   camada no 3D (recorte feito pelo BrasBim, porque o fatiamento por camadas do
   IfcOpenShell falha com "Unexpected topology"). Testes UI51–UI60. Requer instalar
   `pyclipr` (Clipper2) e acrescentá-lo às dependências.
2. **Pacote 3 (etapa 3c):** janela (`janela.md`), no padrão novo da interface.

## Pendências
- Excluir porta de outra origem.
- Mover porta deve recalcular as vizinhas da parede do vão.
- Nicho e vão livre sem ferramenta na interface.
- 3D, fora da spec 07: seleção por janela, alças, arrastar para mover; parede em arco sem
  campos de medida.
- Testes de interface: a planta do `window` mede 464 × 530 px; com a origem do fixture
  (100, 600), pontos com y < 1,4 m caem fora e `QTest.mouseMove` não chega (os testes da
  spec 07 mudam a origem).

## Gosto do usuário
Interface limpa: ícones, opções só da ferramenta ativa, ações só com seleção; nada fixo
poluindo a tela. Desenvolvimento guiado pelo uso: no início da sessão, ler
`feedback/*.md` (observações) e `feedback/diarios/erro-*.md` (erros).
