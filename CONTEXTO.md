# Contexto de desenvolvimento

Estado do trabalho para retomar numa sessão nova. Atualizar ao fim de cada etapa.
Regras do projeto: `CLAUDE.md` e `cleanroom/PROCESSO.md` (nunca acessar `_restrito/` nem
`tools/`).

*Atualizado em 2026‑10‑14.*

## Comandos
| Para | Comando |
|---|---|
| Testes (179 passando) | `.venv/Scripts/python -m pytest -q -p no:faulthandler` |
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
| `spec/ui/06-planta-por-camadas` | **em revisão**, aguarda o revisor (pontos (a)–(h) em §9) |

## O que já existe
- Interface com barras móveis e ícones próprios, barra Opções por ferramenta, mini-barra
  junto à seleção (`ui/selection_bar.py`), painel de propriedades em pé ou deitado.
- Parede: tipos com representação na planta (Pset `BrasBim_RepresentacaoPlanta`),
  junções L/T/X, unir, desfazer junção (`SemJuncaoCom`), trocar a contínua, dividir,
  espelhar, comprimento e ângulo no painel, propriedades comuns.
- Porta: tipos, alças de largura, etiqueta na planta, propriedades comuns.
- Operações serializáveis com desfazer/refazer e diário de sessão (`feedback/diarios/`).

## Próximos passos (nesta ordem)
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

## Gosto do usuário
Interface limpa: ícones, opções só da ferramenta ativa, ações só com seleção; nada fixo
poluindo a tela. Desenvolvimento guiado pelo uso: no início da sessão, ler
`feedback/*.md` (observações) e `feedback/diarios/erro-*.md` (erros).
