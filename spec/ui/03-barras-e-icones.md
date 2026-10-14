---
documento: Interface — barras móveis, ícones, barra de opções, mini-barra da seleção e representação da parede na planta (versão 0.3 da interface)
requisito: RF-UI-01, RF-UI-02, RF-UI-03, RF-TIP-03 (parcial), RF-DOC-02 (parcial)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: em revisão
revisor: OTTO
---

# Barras, ícones e representação da parede

## 1. Propósito
Retorno de uso do revisor sobre a 0.2 (2026‑10‑14): a janela tem texto e botões demais
sempre visíveis. Esta versão reorganiza a interface:

1. Ferramentas em **barras móveis**, que o usuário põe no topo, na base, nas laterais ou
   soltas.
2. **Ícones** no lugar de texto; o nome aparece ao passar o mouse.
3. As opções de uma ferramenta (ex.: Parede) aparecem numa **barra de opções** só quando
   ela está ativa.
4. Mover, copiar, girar e outras ações sobre o selecionado aparecem numa **mini-barra
   junto à seleção**, só quando há seleção.
5. A **representação da parede na planta** (contorno, preenchimento, linha) passa a ser
   escolhida no **tipo de parede** e gravada no IFC.

Revoga, da spec 0.1: "sem ícones" (§1, §6 e ponto de revisão (b)) e as opções da
ferramenta no painel de propriedades (§7.1). Da spec 0.2: os botões Dividir, Mover, Copiar
e Girar na barra principal (§2). O resto continua valendo.

## 2. Barras

```
 ┌ Ferramentas ┐   ┌ Opções: Parede ────────────────────────────────────────────────┐
 │ ⬚  ▭  ⌐    │   │ [reta][arco][retângulo] │ Tipo [Alvenaria 14 ▾] ✎ │ ref [◧][◫][◨] │
 └────────────┘   │ │ Topo [Pavimento de cima ▾]                                       │
                  └──────────────────────────────────────────────────────────────────┘
 ┌ Histórico ┐
 │ ↶  ↷      │
 └───────────┘
```
(desenho esquemático; os ícones reais são os de §3)

| Barra | Conteúdo | Quando aparece |
|---|---|---|
| **Ferramentas** | Selecionar, Parede, Porta (e as ferramentas de criação que vierem: janela, laje…) | Sempre |
| **Histórico** | Desfazer, Refazer | Sempre (pode ser fechada; Ctrl+Z/Ctrl+Y continuam) |
| **Opções** | Opções da ferramenta de criação ativa (§4) | Só com uma ferramenta de criação ativa |

- São barras de ferramentas comuns do Qt: arrastando pela alça, vão para qualquer borda da
  janela ou ficam soltas. Posição, borda e visibilidade são lembradas entre sessões (como
  os painéis, spec 0.1 §2). *(CG)*
- Menu **Exibir > Barras**: liga e desliga cada barra; **Exibir > Reorganizar barras**
  volta à posição inicial (Ferramentas à esquerda, Opções e Histórico no topo).
- A barra Opções troca de conteúdo conforme a ferramenta, mas é uma barra só (a posição
  escolhida vale para todas as ferramentas).

## 3. Ícones
- **Desenho próprio**, feito para o BrasBim: traço fino (1,5 px em 24 × 24), uma cor,
  cantos retos, sem imitar ícones de outros programas. Cada ícone é um arquivo SVG em
  `brasbim/ui/icons/`, sob a licença do aplicativo (GPL‑3.0‑or‑later). *(decisão do
  projeto; cleanroom/PROCESSO.md §3.4)*
- A cor do traço segue a cor de texto do tema do sistema (claro ou escuro); ícone ativo
  ou marcado usa a cor de destaque.
- **Dica ao passar o mouse:** nome e, em seguida, o uso em uma linha, ex.: "Parede reta —
  clique os pontos; Enter, clique duplo ou botão direito encerra". O mesmo texto vai para
  a barra de estado.
- Ícones previstos nesta versão: selecionar, parede reta, parede em arco, retângulo de
  paredes, porta, desfazer, refazer, mover, copiar, girar, dividir, excluir, inverter
  sentido, inverter dobradiças, linha de referência (face esquerda, eixo, face direita),
  dobradiças (esquerda, direita), editar tipo.
- Menus continuam com texto (e o ícone ao lado, quando houver).

## 4. Barra de opções

### 4.1 Parede
Um único ícone **Parede** na barra Ferramentas; a forma é escolhida na barra de opções.

| Grupo | Controles |
|---|---|
| Forma | Reta (cadeia), Em arco, Retângulo — ícones exclusivos (um marcado) |
| Tipo | Lista dos tipos de parede, com uma amostra da representação do tipo (§6) ao lado do nome; botão **Editar tipo** abre a janela de tipos (spec 0.2 §8) já no tipo escolhido |
| Linha de referência | Face esquerda, Eixo, Face direita — ícones exclusivos |
| Topo | Lista "Pavimento de cima" / "Altura fixa"; com altura fixa, campo da altura |

O ícone Parede lembra a última forma usada. Os valores valem até serem mudados na sessão
(como na spec 0.1 §7.1).

### 4.2 Porta
| Grupo | Controles |
|---|---|
| Tipo | Lista dos tipos de porta e **Editar tipo** |
| Vão | Largura, altura e base (vazios = padrão do tipo, mostrado em cinza) |
| Dobradiças | Esquerda, Direita — ícones exclusivos (Tab continua alternando) |
| Posição no marco | Alinhamento (lista) e deslocamento |

### 4.3 Painel de propriedades
Sem seleção, o painel mostra só o pavimento ativo e a dica "Clique num elemento da planta
para ver e editar as propriedades". Com seleção, continua como nas specs 0.1 §7 e 0.2 §9.

## 5. Mini-barra da seleção
Barra pequena de ícones que aparece **na planta, junto à seleção**, com as ações sobre os
elementos selecionados.

- **Quando aparece:** ferramenta Selecionar ativa, seleção não vazia e nenhuma ação em
  andamento (arrasto, alça, janela). Some durante a ação e volta ao terminar. Esc com a
  mini-barra visível limpa a seleção.
- **Onde:** acima do canto superior direito do retângulo que envolve a seleção na tela, a
  12 px dele; se não couber, abaixo do canto inferior direito; sempre dentro da vista.
  Acompanha zoom e arrasto da vista.
- **Conteúdo** (só os que se aplicam à seleção):

| Ação | Aplica-se a | Comportamento |
|---|---|---|
| Mover | qualquer seleção | ferramenta Mover da spec 0.2 §6.1 |
| Copiar | qualquer seleção | spec 0.2 §6.2 |
| Girar | seleção com parede | spec 0.2 §6.3 |
| Dividir | exatamente uma parede | ferramenta Dividir da spec 0.2 §5, **restrita à parede selecionada** |
| Inverter sentido | só portas | `flip_opening` em cada porta (spec 0.2 §9) |
| Inverter dobradiças | só portas com mão | `flip_hinges` em cada porta |
| Excluir | qualquer seleção | Editar > Excluir (spec 0.1 §5.1, com a confirmação de portas) |

- Mover, Copiar, Girar e Dividir terminam voltando a Selecionar, com a mesma seleção
  (Copiar, ao terminar com Esc).
- As mesmas ações ficam também no menu **Editar** (Mover, Copiar, Girar, Dividir), para
  quem prefere o menu. Elas não ficam mais na barra principal.
- **Exibir > Mini-barra da seleção** liga e desliga a mini-barra (padrão: ligada).

## 6. Representação da parede na planta, no tipo (RF-TIP-03 parcial)

### 6.1 Parâmetros
| Parâmetro | Valores | Padrão |
|---|---|---|
| Preenchimento | Nenhum, Sólido, Hachura | Sólido |
| Cor do preenchimento | cor RGB | cinza médio (o atual da planta) |
| Hachura: ângulo | graus | 45° |
| Hachura: espaçamento | metros, medidos no modelo | 0,10 m |
| Linha de contorno: espessura | 0,13 / 0,18 / 0,25 / 0,35 / 0,50 / 0,70 mm (série da ABNT NBR 8403) | 0,50 mm |
| Linha de contorno: cor | cor RGB | preto |

- A espessura da linha é convertida para a tela a 96 ppp (0,50 mm ≈ 1,9 px), com mínimo de
  1 px. Escala de impressão e níveis de detalhe ficam para pranchas (RF-DOC).
- Pavimento de baixo (spec 0.1 §3) e seleção continuam com as cores da planta, não as do
  tipo.
- Desenho por camadas (uma faixa por camada, com a cor do material): **ponto de revisão
  (c)**, proposto para versão posterior.

### 6.2 Gravação no IFC *(decisão do projeto)*
Pset próprio no `IfcWallType`, **`BrasBim_RepresentacaoPlanta`**:

| Propriedade | Tipo IFC | Exemplo |
|---|---|---|
| `Preenchimento` | `IfcLabel` | `NENHUM`, `SOLIDO`, `HACHURA` |
| `CorPreenchimento` | `IfcLabel` | `#9C9A93` |
| `AnguloHachura` | `IfcPlaneAngleMeasure` (graus, unidade do projeto) | `45` |
| `EspacamentoHachura` | `IfcPositiveLengthMeasure` | `0.10` |
| `EspessuraLinha` | `IfcPositiveLengthMeasure` (metros: 0,0005 = 0,50 mm) | `0.0005` |
| `CorLinha` | `IfcLabel` | `#2B2A27` |

- Sem o Pset (tipo de outra origem ou anterior a esta versão), valem os padrões.
- Operação: `wall_type.edit` ganha o campo `plan_style` (before/after: o dicionário de
  §6.1); `wall_type.create` aceita `plan_style`. Nenhuma operação nova. Atualizar
  `spec/01-modelo-de-dados.md`.
- Mudar a representação de um tipo redesenha a planta; o 3D não muda (a cor do 3D vem do
  material, spec 0.1 §4).
- **Ponto de revisão (b):** o IFC tem um caminho próprio para hachura de corte
  (`IfcFillAreaStyle` / `IfcFillAreaStyleHatching` na representação do material, e
  `IfcCurveStyle` para a linha), lido por outros programas. Proposta: Pset agora, porque o
  pedido é por tipo e o estilo do IFC é por material; gravar também os estilos de material
  quando houver desenho por camadas.

### 6.3 Onde se edita
- Janela **Tipos de parede** (spec 0.2 §8.1), grupo novo **Representação na planta**, com
  amostra ao vivo.
- Botão **Editar tipo** da barra de opções da Parede (§4.1) e do painel de propriedades da
  parede selecionada.

### 6.4 Biblioteca do projeto novo
"Alvenaria 14": sólido, cinza médio, linha 0,50 mm. "Drywall 9,5": hachura a 45°,
espaçamento 0,05 m, cinza claro, linha 0,35 mm. *(decisão do projeto, a revisar)*

## 7. Organização do código *(decisão do projeto)*
| Onde | O quê |
|---|---|
| `brasbim/ui/icons/*.svg` (novo) | Ícones de §3 |
| `brasbim/ui/icons.py` (novo) | Carrega o SVG e troca a cor do traço pela do tema |
| `brasbim/ui/toolbars.py` (novo) | Barras Ferramentas, Histórico e Opções (§2, §4) |
| `brasbim/ui/selection_bar.py` (novo) | Mini-barra da seleção (§5); a posição é calculada sem Qt em `tools.py` a partir dos limites da seleção |
| `brasbim/core/walls/types.py` | `plan_style` no estado do tipo e Pset de §6.2 |
| `brasbim/core/plan.py` | O desenho da parede leva o estilo do tipo (`Shape.style`) |
| `brasbim/ui/plan_view.py` | Desenha preenchimento, hachura e linha conforme o estilo |

## 8. Critérios de aceite (testes)
- [ ] **UI29** As barras Ferramentas, Histórico e Opções existem, são móveis para as quatro
      bordas e soltas, e a posição volta depois de fechar e abrir a janela.
- [ ] **UI30** Todo botão das barras tem ícone, sem texto visível, e dica com o nome.
- [ ] **UI31** Ativar Parede mostra a barra Opções com as três formas; escolher "Em arco"
      e clicar três pontos cria parede em arco; ativar Selecionar esconde a barra.
- [ ] **UI32** Trocar o tipo e a linha de referência na barra de opções vale para a
      próxima parede criada.
- [ ] **UI33** Selecionar uma parede mostra a mini-barra com Mover, Copiar, Girar,
      Dividir e Excluir, junto à parede e dentro da vista; selecionar só portas mostra
      Inverter sentido e Inverter dobradiças e esconde Girar e Dividir; sem seleção, ou
      durante um arrasto, a mini-barra não aparece.
- [ ] **UI34** Mover pela mini-barra gera a mesma transação da spec 0.2 (UI20) e volta a
      Selecionar; Dividir pela mini-barra só divide a parede selecionada.
- [ ] **UI35** Mudar o preenchimento de "Alvenaria 14" para hachura na janela de tipos gera
      um `wall_type.edit` com `plan_style`; o Pset `BrasBim_RepresentacaoPlanta` fica no
      tipo; a planta passa a desenhar hachura nas paredes do tipo; desfazer volta ao
      sólido; salvar e reabrir preserva o estilo.
- [ ] **UI36** Tipo sem o Pset (IFC de outra origem) é desenhado com os padrões de §6.1.

## 9. Fontes públicas
- **RF** — `spec/REQUISITOS.md` (RF-UI-01..03, RF-TIP-03, RF-DOC-02).
- **UI01**, **UI02** — specs 0.1 e 0.2 (aprovadas).
- **IFC** — buildingSMART IFC 4.3: `IfcPropertySet`, `IfcWallType`, `IfcFillAreaStyle`,
  `IfcFillAreaStyleHatching`, `IfcCurveStyle` (alternativa de §6.2).
- **NBR8403** — ABNT NBR 8403, série de espessuras de linha (0,13 a 2,0 mm).
- **QT** — documentação pública do Qt for Python 6: `QToolBar` (áreas permitidas,
  barras soltas), `QMainWindow.saveState`, `QIcon`, `QSvgRenderer`.
- **CG** — conhecimento geral de aplicativos de desktop: barras encaixáveis, dicas ao
  passar o mouse, barra de opções da ferramenta ativa, ações junto à seleção.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 10. Pontos de revisão
(a) Reorganização das barras e posição inicial (§2).
(b) Representação em Pset próprio no tipo, e não (ainda) nos estilos de material do IFC
    (§6.2).
(c) Desenho por camadas fica para depois (§6.1).
(d) Conteúdo e posição da mini-barra; Esc com a mini-barra visível limpa a seleção (§5).
(e) Padrões de representação da biblioteca inicial (§6.4).
