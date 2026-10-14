---
documento: Interface — planta por nível de detalhe, estilos de material e cor por camada no 3D
requisito: RF-DOC-01, RF-DOC-02, RF-DOC-08, RF-TIP-03, RF-ELE-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: em revisão
revisor: —
---

# Planta por camadas e estilos de material

## 1. Propósito
Pacote 2 de 3 da ordem combinada com o revisor em 2026‑10‑14. Implementa o que as specs
aprovadas da parede já preveem e ainda não existe:

- os dois **níveis de detalhe** da planta (`parede.md` §7): simplificado (1:100) e por
  camadas (1:50), este com a **prioridade das camadas** nas junções (`parede.md` §6.2);
- o **plano de corte** configurável e as paredes **abaixo** e **acima** dele (`parede.md`
  §7);
- **estilos de material** gravados no IFC (cor do 3D e hachura de corte), retomando os
  pontos de revisão (b) e (c) da spec 03 §6;
- **cor por camada no 3D**, adiada da spec 05 §1 (ponto de revisão (c) dela).

Fora deste pacote: escala de impressão, pranchas e espessuras de linha configuráveis
(RF-DOC-03); prioridades por junção (`RelatingPriorities`/`RelatedPriorities`, V1);
transparência no 3D; cortes e fachadas.

## 2. Nível de detalhe da planta

**Exibir > Detalhe da planta** com duas opções exclusivas: **Simplificado** (padrão) e
**Por camadas**. Preferência do aplicativo, lembrada entre sessões, como as etiquetas de
porta (spec 05 §5). Nada vai para o IFC: quando houver vistas e pranchas (RF-DOC), o
detalhe passa a ser da vista.

### 2.1 Simplificado (1:100)
- Como hoje: cada parede cortada com a **representação do tipo** (spec 03 §6:
  preenchimento, hachura, linha de contorno).
- **Junções sem linhas internas** (`parede.md` §7): paredes **do mesmo tipo** que se tocam
  formam uma só mancha; o contorno é desenhado só na borda da união delas. Entre tipos
  diferentes a linha continua (cada tipo desenha a borda da sua união).
- Em X, a contínua continua por cima (spec 05 §7.1) quando os tipos são diferentes; com
  o mesmo tipo a união já resolve.

### 2.2 Por camadas (1:50)
Cada camada da parede vira uma faixa com o **estilo de corte do seu material** (§4).

- **Linhas:** a borda externa da parede (união, como em §2.1) usa a linha de contorno do
  tipo; as divisas **entre materiais diferentes** usam linha fina (0,18 mm, série da NBR
  8403, convertida para a tela como na spec 03 §6.1). Entre faixas do **mesmo material**
  não há linha, nem dentro da parede nem de uma parede para outra (ex.: reboco que
  contorna um canto é uma faixa só).
- **Hachura:** a do material, com espaçamento medido no modelo; a origem das linhas é a
  origem do pavimento, para que a hachura continue de uma parede para a outra.
- A representação do tipo (spec 03 §6) não é usada neste nível, a não ser a linha de
  contorno externa.
- Tipo de outra origem sem camadas utilizáveis (sem `IfcMaterialLayerSet`): desenhado como
  no simplificado.

### 2.3 Prioridade das camadas nas junções (`parede.md` §6.2)
Em cada junção (L, T ou X), a área de encontro das duas paredes é dividida entre as
camadas pela **prioridade** (`IfcMaterialLayer.Priority`, 0 a 100): a camada de maior
prioridade **avança** pela área de encontro, a de menor prioridade **para** nela. [IFC-ML]

Regra *(decisão do projeto, em palavras próprias)*:
1. A área desenhada de cada parede continua sendo a do corpo (com o recorte de junção da
   `parede.md` §6.2 e os vãos da planta); a união das paredes não muda.
2. Cada camada, nas extremidades com junção, é prolongada pela própria direção até
   atravessar a outra parede.
3. As camadas de todas as paredes do pavimento, da maior prioridade para a menor, ocupam
   a parte do seu prolongamento que ainda está livre dentro da união.
4. Empate: primeiro a parede contínua (`RelatingElement` da junção), depois a camada mais
   espessa, depois o GlobalId. Camada sem prioridade conta como 0.

Efeito esperado, com a biblioteca inicial (bloco 80, reboco 20):

| Junção | Resultado |
|---|---|
| L entre duas alvenarias | Os blocos se encontram no canto; o reboco externo dá a volta no canto sem emenda; o reboco interno das duas para no bloco |
| T de alvenaria em alvenaria | O bloco da que chega atravessa o reboco da contínua e encosta no bloco dela; o reboco da contínua é interrompido ali |
| T de drywall em alvenaria | Se o montante tem prioridade entre a do reboco e a do bloco (ex.: 40), ele atravessa o reboco e encosta no bloco; o gesso (20, empate com o reboco) para na face do reboco, porque a alvenaria é a contínua |
| X entre alvenarias iguais | Os blocos se fundem no cruzamento; os rebocos das duas são interrompidos |

- No 3D e no IFC o corpo continua recortado pela espessura total (`parede.md` §6.2, MVP);
  a prioridade só muda o desenho das camadas (planta e cor por camada do 3D, §5).
- Prioridade se edita na tabela de camadas do diálogo de tipos (já existe).

## 3. Plano de corte

### 3.1 Altura do plano
- Por **pavimento**, em metros acima da cota do pavimento. Padrão **1,50 m**
  (`parede.md` §7, a confirmar na NBR 6492).
- Edição: nova coluna **Plano de corte** na tabela de pavimentos do painel do projeto
  (ao lado de Cota). Valor igual ao padrão não é gravado.
- Gravação *(decisão do projeto)*: Pset próprio **`BrasBim_Pavimento`** no
  `IfcBuildingStorey`, propriedade `AlturaPlanoCorte` (`IfcPositiveLengthMeasure`). Sem o
  Pset, vale o padrão. Operação: `storey.edit` ganha o campo `cut_height` (`None` = padrão);
  `storey.create` aceita o campo. Nenhuma operação nova; atualizar
  `spec/01-modelo-de-dados.md`.

### 3.2 O que a planta mostra (`parede.md` §7)
`z0` e `z1` = base e topo da parede, em relação à cota do pavimento; `c` = plano de corte.

| Situação | Condição | Desenho |
|---|---|---|
| **Cortada** | `z0 ≤ c < z1` | Como em §2 (preenchimento ou camadas) |
| **Abaixo** (em vista) | `z1 ≤ c` | Só o contorno, linha média (0,25 mm), sem preenchimento. Ex.: mureta, platibanda baixa |
| **Acima** | `z0 > c` | Contorno tracejado fino (0,18 mm), sem preenchimento. Ex.: parede sobre viga, bandeira alta |

- **Exibir > Elementos acima do plano de corte** liga e desliga o tracejado (padrão:
  ligado). Preferência do aplicativo.
- Paredes abaixo e acima também se selecionam pelo contorno.
- Ordem de desenho: acima, abaixo, cortadas (as cortadas cobrem as outras).

### 3.3 Vãos (`parede.md` §7)
Vãos da parede cortada, conforme a faixa `[base, base + altura]` do vão:

| Vão | Desenho |
|---|---|
| O plano atravessa o vão | Interrompe a parede (como hoje). Se a base do vão é maior que zero (peitoril), as duas faces da parede no trecho aparecem em linha média, como **parede em vista** |
| Vão todo abaixo do plano | Nada muda na planta (a parede está cortada acima dele) |
| Vão todo acima do plano | Contorno do vão em tracejado fino sobre a parede, com a mesma opção de §3.2 |

- Nicho (`RECESS`) atravessado pelo plano: a face da parede é recortada na profundidade
  do nicho (`parede.md` §7). Não há ferramenta de nicho na interface ainda; o desenho vale
  para nichos vindos do núcleo ou de arquivos.
- Portas: símbolo como hoje (porta §7), sempre que o vão é atravessado pelo plano.

## 4. Estilos de material

### 4.1 Parâmetros
| Parâmetro | Valores | Padrão |
|---|---|---|
| Cor (3D) | cor RGB | da biblioteca (§4.4) ou da paleta atual, pelo nome |
| Corte: padrão | Nenhum, Sólido, Linhas, Cruzado | da biblioteca, ou Nenhum |
| Corte: cor do fundo | cor RGB ou nenhuma | nenhuma (Sólido: obrigatória) |
| Corte: ângulo | graus | 45° |
| Corte: espaçamento | metros, medidos no modelo | 0,05 m |
| Corte: cor das linhas | cor RGB | preto da planta (`#2B2A27`) |

- Cruzado = duas famílias de linhas, no ângulo e a 90° dele, com o mesmo espaçamento.
- Espaçamento menor que 1 px na tela: a hachura não é desenhada (fica só o fundo), para
  não virar mancha nem pesar.

### 4.2 Diálogo
**Projeto > Materiais…**: lista dos materiais do projeto à esquerda (com amostra da cor e
do corte); à direita, os campos de §4.1 do material escolhido e uma amostra grande do
corte. A tabela de camadas do diálogo de tipos ganha, ao lado do material, um botão
pequeno que abre este diálogo já no material da camada.

- Mudar um estilo é uma transação; a planta e o 3D se atualizam.
- Material sem estilo gravado aparece com os padrões, marcado "(padrão)"; gravar é só
  mudar um campo.
- Renomear e excluir materiais ficam fora deste pacote (o material é criado pelo nome ao
  editar as camadas, como hoje).

### 4.3 Gravação no IFC *(decisão do projeto sobre [IFC-MDR], [IFC-FAS], [IFC-FASH])*
`IfcMaterialDefinitionRepresentation` ligada ao `IfcMaterial`, com até duas
`IfcStyledRepresentation`, cada uma com um `IfcStyledItem` de um estilo só:

| Contexto | Estilo | Conteúdo |
|---|---|---|
| `Model` / `Body` | `IfcSurfaceStyle` (`Side = BOTH`) | `IfcSurfaceStyleShading` com `SurfaceColour` = cor (3D) |
| `Plan` / `Body` (`PLAN_VIEW`, criado se faltar) | `IfcFillAreaStyle` (`ModelOrDraughting = TRUE`: medidas no modelo) | Sólido: só `IfcColourRgb`. Linhas: um `IfcFillAreaStyleHatching` (+ `IfcColourRgb` se houver fundo). Cruzado: dois. Nenhum: sem esta representação |

`IfcFillAreaStyleHatching`: `HatchLineAppearance` = `IfcCurveStyle` com a cor das linhas
e espessura 0,18 mm; `StartOfNextHatchLine` = espaçamento (`IfcPositiveLengthMeasure`);
`HatchLineAngle` = ângulo (radianos, unidade do projeto); `PointOfReferenceHatchLine`
(obsoleto) e `PatternStart` não gravados.

- Materiais de outra origem com estilos: são lidos (cor de `IfcSurfaceStyleShading` ou
  `IfcSurfaceStyleRendering`; corte de `IfcFillAreaStyle` com cor e até duas hachuras);
  estilos que o BrasBim não entende (textura, hachura externa, ladrilho) são mantidos
  intactos e o material aparece com o padrão no que faltar. Editar o estilo troca só as
  representações dos contextos acima.
- **Operação nova** `material.edit`: `id` = **nome do material** (o `IfcMaterial` não tem
  GlobalId; o BrasBim nunca cria dois materiais com o mesmo nome; em arquivo de outra
  origem com nomes repetidos, vale para todos eles). `before`/`after`: `style`
  (`{"color", "cut": {"pattern", "background", "angle", "spacing", "line_color"}}`,
  `None` = sem estilo gravado). Invertível trocando `before` e `after`. Atualizar
  `spec/01-modelo-de-dados.md`.
- O Pset `BrasBim_RepresentacaoPlanta` do tipo (spec 03 §6.2) continua valendo para o
  simplificado; os estilos de material valem para o por camadas e para o 3D.

### 4.4 Biblioteca inicial *(CG, a revisar)*
| Material | Cor (3D) | Corte |
|---|---|---|
| Bloco cerâmico | `#CC8C6B` | Linhas 45°, 0,03 m |
| Reboco | `#DBD6CC` | Nenhum |
| Concreto | `#B3B3AD` | Sólido `#8A8A85` |
| Gesso acartonado | `#EBEBE6` | Nenhum |
| Montante de aço | `#A6ADB8` | Cruzado 45°, 0,02 m |
| Madeira | `#9E7045` | Linhas 30°, 0,015 m |
| Vidro | `#A6CCE0` | Sólido `#A6CCE0` |

Os tipos da biblioteca e os modelos de exemplo já gravam estes estilos ao criar os
materiais. As cores do 3D são as que hoje estão fixas no código, que passam a ser só o
padrão.

## 5. Cor por camada no 3D (`parede.md` §2.3)
- Cada camada da parede aparece no 3D com a **cor do material dela**, com a mesma
  divisão da planta por camadas (§2.3), inclusive nas junções.
- O **corpo no IFC não muda**: continua um `IfcExtrudedAreaSolid` só, com as aberturas
  (`parede.md` §2.2). A divisão é feita **só na exibição**, pelo BrasBim: o corpo
  triangulado pelo `ifcopenshell.geom` é recortado pelas faixas das camadas. O recurso de
  fatiar por camadas do IfcOpenShell não é usado (falha na geometria do BrasBim,
  verificado em 2026‑10‑14).
- Paredes de outra origem sem `IfcMaterialLayerSetUsage`, e portas: uma cor por elemento,
  como hoje, agora vinda do estilo do material.
- As arestas desenhadas no 3D continuam as do corpo (sem linhas entre camadas).

## 6. Implementação (notas para o núcleo)
- Booleanos 2D com Clipper2 (`pyclipr`, já previsto no stack; licença compatível com a
  LGPL), nova dependência do núcleo. Arcos viram polígonos com a mesma discretização de
  hoje.
- `core/plan.py` passa a montar a planta em três camadas de desenho (acima, abaixo,
  cortadas) e, no por camadas, regiões por material; a escolha de elementos continua pelo
  contorno da parede inteira.
- Recorte do 3D por camada no núcleo (sem Qt), testável: dado o corpo triangulado e as
  regiões das camadas, devolve triângulos por camada.

## 7. Critérios de aceite (testes)
- [ ] **UI51** Duas paredes do mesmo tipo em L, simplificado: a planta tem um contorno só
      (união), sem linha na junção; com tipos diferentes, a linha entre eles existe.
- [ ] **UI52** Por camadas, L entre alvenarias 14: regiões de bloco das duas unidas no
      canto; reboco externo uma faixa contínua em L; reboco interno das duas para no bloco;
      sem linha entre faixas do mesmo material.
- [ ] **UI53** Por camadas, T de alvenaria em alvenaria: o bloco da que chega toca o bloco
      da contínua e o reboco da contínua é interrompido; trocar as prioridades no tipo
      inverte o resultado.
- [ ] **UI54** Plano de corte 1,00 m num pavimento: mureta de 0,90 m aparece só em contorno
      (abaixo); parede com base a 1,20 m aparece tracejada (acima) e some ao desligar a
      opção; o Pset `BrasBim_Pavimento` tem `AlturaPlanoCorte = 1.0`; voltar a 1,50 remove
      a propriedade; desfazer volta.
- [ ] **UI55** Vão livre com base 1,00 e altura 1,20, plano a 1,50: a parede é interrompida e
      as faces no trecho aparecem como parede em vista; plano a 0,50: a parede não é
      interrompida.
- [ ] **UI56** Editar o material "Bloco cerâmico" para Cruzado 30°, 0,04 m, cor `#AA5533`:
      o IFC relido tem `IfcMaterialDefinitionRepresentation` com `IfcSurfaceStyle` (cor) no
      contexto Model/Body e `IfcFillAreaStyle` com duas `IfcFillAreaStyleHatching`
      (ângulos 30° e 120°, espaçamento 0,04) no Plan/Body; desfazer volta ao estado
      anterior; passa na validação de esquema.
- [ ] **UI57** Material de outra origem com `IfcSurfaceStyleRendering` e textura: a cor é
      lida; editar o corte mantém a textura.
- [ ] **UI58** 3D: parede de alvenaria 14 com porta tem triângulos com as cores do reboco e
      do bloco, a área de cada cor bate com a das faixas (faces laterais e topo), e a
      soma das áreas é a do corpo sem divisão.
- [ ] **UI59** A biblioteca inicial grava os estilos de §4.4; um modelo de exemplo aberto
      mostra a planta por camadas sem material "(padrão)".
- [ ] **UI60** Os diários de UI54–UI56 reaplicados num projeto novo reproduzem o IFC.

## 8. Fontes públicas
Documentação IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`,
consultada em 2026‑10‑14. Base:
`https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-MDR | `docs/schemas/resource/IfcRepresentationResource/Entities/IfcMaterialDefinitionRepresentation.md` (estilos por contexto, só `IfcStyledRepresentation`) |
| IFC-FAS | `docs/schemas/resource/IfcPresentationAppearanceResource/Entities/IfcFillAreaStyle.md` (sólido, uma ou duas hachuras, no máximo uma cor; `ModelOrDraughting`) |
| IFC-FASH | `docs/schemas/resource/IfcPresentationAppearanceResource/Entities/IfcFillAreaStyleHatching.md` (aparência, espaçamento, ângulo; duas instâncias para cruzado) |
| IFC-ML | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayer.md` (`Priority`) |

Outras:
- **PAREDE** — `spec/elementos/parede.md` §2.3, §6.2, §7 (aprovada).
- **UI03**, **UI05** — specs de interface 03 §6 e 05 §1, §7.1 (aprovadas).
- **IOS** — IfcOpenShell 0.9: módulo `ifcopenshell.api.style` (`add_style`,
  `add_surface_style`, `assign_material_style`) e `ifcopenshell.geom` (para a
  implementação).
- **NBR8403** — série de espessuras de linha, como na spec 03. **NBR6492** citada só por
  título; texto não lido.
- **CG** — conhecimento geral de desenho arquitetônico: detalhe por escala, prioridade de
  camadas em junções, convenções de hachura por material, elementos acima do plano em
  tracejado.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 9. Pontos de revisão
(a) Detalhe da planta como preferência do aplicativo (§2), até existirem vistas.
(b) Regra de prioridade e desempates (§2.3), e o resultado esperado na tabela.
(c) Plano de corte por pavimento, no Pset `BrasBim_Pavimento` (§3.1).
(d) Desenho de peitoril e de vão acima do plano (§3.3); espessuras 0,25 e 0,18 mm.
(e) Material identificado pelo nome na operação `material.edit` (§4.3).
(f) Estilo de corte no contexto `Plan`/`Body` e cor no `Model`/`Body` (§4.3).
(g) Biblioteca de estilos (§4.4), sobretudo concreto e montante.
(h) Cor por camada só na exibição, sem mudar o corpo do IFC (§5).
