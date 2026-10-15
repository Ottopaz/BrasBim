---
documento: Interface e núcleo — alças da parede no 3D, topo inclinado e empena, parede tombada; ponta de parede unida move só a parede
requisito: RF-ELE-01, RF-ELE-17, RF-NUC-05, RF-UI-03
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-15
status: aprovado
revisor: OTTO (aprovado em 2026-10-15, pontos (a)–(h) aceitos)
---

# Parede no 3D: alças, topo inclinado e parede tombada

## 1. Propósito
Pedidos do revisor em 2026‑10‑15:

1. **Ponta de parede unida move só a parede escolhida** (decidido pelo revisor; já
   implementado, §2).
2. **Alças da parede no 3D** para editar comprimento, posição, altura, base, topo e
   inclinação direto na vista 3D (§3).
3. **Topo inclinado e empena** (§4) e **parede tombada**, fora do prumo (§5). As duas
   formas estão **fora** do escopo de `parede.md` aprovada (§1, §11); esta spec propõe as
   alterações nela (§6).

Ordem de implementação proposta: §3 com altura e base → §4 (topo) → §5 (tombada). Cada
etapa com seus testes.

## 2. Ponta de parede unida *(decidido em 2026‑10‑15)*
Altera spec 02 §4.1 e spec 05 §3:

- Arrastar a **alça de ponta**, digitar o número da alça e mudar **Comprimento** ou
  **Ângulo** no painel movem **só a parede escolhida**. As junções são recalculadas pela
  geometria: se a ponta sai do encontro, a junção se desfaz.
- **Ctrl ao soltar** leva junto as paredes com ponta no mesmo lugar (o padrão antigo).
- A alça do **meio** não muda: as vizinhas acompanham e Ctrl solta (spec 02 §4.2).
- Teste: UI15 e UI43 atualizados (commit `bf03c62`).

## 3. Alças da parede no 3D
Com a ferramenta Selecionar, **uma parede reta selecionada sozinha** mostra no 3D:

| Alça | Onde | Arrastar | Número digitado (quadro de medidas) |
|---|---|---|---|
| Ponta (2) | base, nas pontas da linha de referência | no plano do pavimento, como a alça de ponta da planta (§2) | Comprimento |
| Face | meio da face esquerda, a meia altura | perpendicular à parede, no plano do pavimento: desloca a parede paralela (vizinhas acompanham, Ctrl solta) | Distância |
| Topo | meio da aresta de cima (ou cada vértice do topo, §4) | vertical | Altura |
| Base | meio da aresta de baixo | vertical | Deslocamento da base |
| Inclinação | 0,30 m para fora da face, na altura do topo | perpendicular à parede | Inclinação (°) — §5 |

- Alças desenhadas como quadrados de tamanho fixo na tela (como na planta); a alça sob o
  cursor fica cheia. O quadro de medidas mostra o valor durante o arrasto.
- **Arraste vertical:** o raio do cursor encontra o plano vertical que passa pela alça e
  está de frente para a câmera; vale o z desse ponto. *Snap* nas cotas dos pavimentos e
  na grade (0,10 m); Alt desliga.
- **Altura** (topo plano): com topo "pavimento de cima", muda o **deslocamento do topo**;
  com topo "altura fixa", muda a **altura fixa**. Não muda o modo.
- Arco: só pontas, topo e base nesta etapa (sem face, sem inclinação, sem topo de §4).
- Várias paredes selecionadas: sem alças (como na planta).
- Uma alça ativa a cada vez; clique e solte sem arrastar prende a alça ao cursor (como na
  planta, spec 02 §4).
- Operação: `wall.edit` (estado completo), como as alças da planta. Nenhuma nova.

## 4. Topo inclinado e empena

### 4.1 Formas
Campo **Topo** no painel (grupo Altura), parede reta:

| Forma | Parâmetros no painel | Exemplo |
|---|---|---|
| Plano | o de hoje (pavimento de cima ou altura fixa) | — |
| Inclinado | altura no início, altura no fim *ou* ângulo | parede sob telhado de uma água |
| Empena | altura nas pontas, altura da cumeeira *ou* ângulo, posição da cumeeira (padrão: meio) | oitão de telhado de duas águas |
| Livre | lista de pontos (distância, altura) | recortes diversos |

- Alturas medidas **da base da parede**; ângulo em graus a partir da horizontal.
- No 3D, cada vértice do topo vira uma alça (§3): arrastar na vertical muda a altura;
  a cumeeira também anda ao longo da parede (o ponto é tirado do plano vertical da
  parede).
- Mudar o comprimento da parede mantém as alturas e reposiciona os pontos
  proporcionalmente (a cumeeira no meio continua no meio).
- **Abertura** (porta) que ultrapasse o topo em qualquer ponto do vão: recusada, com o
  motivo, como as outras verificações de abertura.

### 4.2 Gravação no IFC *(decisão do projeto sobre [IFC-WALL], [IFC-PBHS])*
- O corpo continua sendo o `IfcExtrudedAreaSolid` da planta (com as junções), extrudado
  até a **maior** altura do topo.
- Representação `Body` passa a `Clipping`: `IfcBooleanClippingResult` (operador
  `DIFFERENCE`) do sólido com um `IfcPolygonalBoundedHalfSpace` **por trecho** do topo.
  O semiespaço tem como superfície o plano inclinado do trecho e é limitado por um
  polígono horizontal que cobre a faixa da parede só naquele trecho (com folga na
  espessura). [IFC-WALL figura do recorte por semiespaço limitado, IFC-PBHS]
- Topo plano continua `SweptSolid` (sem mudança no que já existe).
- `IfcMaterialLayerSetUsage` **continua**: o recorte do corpo é permitido na parede com
  camadas. [IFC-WALL]
- Parâmetros no Pset próprio da parede (`BrasBim_Parede`, já existente):
  `FormaTopo` (`PLANO`, `INCLINADO`, `EMPENA`, `LIVRE`), `PerfilTopoPosicoes` e
  `PerfilTopoAlturas` (`IfcPropertyListValue` de `IfcLengthMeasure`; posição ao longo da
  linha de referência, altura a partir da base). Plano: listas vazias.
- Quantidades (`Qto_WallBaseQuantities`): `Height` = maior altura; áreas laterais e
  volume calculados com o perfil recortado.

### 4.3 Planta
O corte da planta (spec 06 §3) passa a olhar a altura **em cada trecho**: onde o topo
está abaixo do plano de corte, a parede aparece como vista (abaixo), não cortada. Até o
pacote 2 estar pronto, a planta continua como hoje.

## 5. Parede tombada (fora do prumo)

### 5.1 Parâmetro
- **Inclinação**: ângulo em graus a partir da vertical, positivo para o lado **esquerdo**
  da parede (o lado da primeira camada). Limite: −45° a 45°. Padrão 0.
- No painel (grupo Altura) e pela alça de Inclinação no 3D (§3).
- A linha de referência **na base** fica no lugar; o topo se desloca
  `altura × tan(inclinação)` para o lado.
- As camadas mantêm a **espessura verdadeira** (medida perpendicular às faces).
- Só parede reta. Parede com abertura (porta, janela, nicho): recusada nesta etapa
  ("parede tombada ainda não aceita aberturas"); tombar uma parede com abertura também é
  recusado.
- Junções: calculadas na base, como hoje; o topo de duas paredes unidas com inclinações
  diferentes não fica casado (aviso em Mensagens). Fica para depois.

### 5.2 Gravação no IFC *(decisão do projeto sobre [IFC-WALL], [IFC-EAS])*
O IFC diz que parede com camadas tem extrusão **vertical**; parede com extrusão fora do
eixo z é do caso **sem** `IfcMaterialLayerSetUsage`. [IFC-WALL] Por isso, tombada:

- Corpo: `IfcExtrudedAreaSolid` da planta, com `ExtrudedDirection` inclinada
  (0, sen θ, cos θ) no sistema local (θ = inclinação; y local = lado esquerdo) e
  profundidade `altura / cos θ`, para a altura vertical ficar igual. A planta da base é
  alargada por `1 / cos θ`, para a espessura verdadeira ser a das camadas. [IFC-EAS]
- Material: a ocorrência **perde** o `IfcMaterialLayerSetUsage` e passa a usar o
  `IfcMaterialLayerSet` do tipo (associação direta). Voltar a 0° restaura o
  `IfcMaterialLayerSetUsage`. [IFC-WALL, IFC-MLSU]
- `Axis` continua na base. `Inclinacao` (`IfcPlaneAngleMeasure`, graus) no Pset
  `BrasBim_Parede`, para o BrasBim reabrir com o mesmo parâmetro.
- Topo inclinado (§4) e tombada juntos: o recorte é aplicado ao sólido inclinado.

## 6. Alterações em `parede.md` (se aprovada)
- §1 e §11: tirar "inclinadas" e "topo em rampa" do fora de escopo; citar esta spec.
- §2.2: `Body` `Clipping` deixa de ser V1 e passa a valer para topo inclinado/empena;
  linha nova para a tombada (`SweptSolid` com extrusão inclinada, sem
  `IfcMaterialLayerSetUsage`).
- §3 (parâmetros): forma do topo, perfil do topo, inclinação.
- §8 (quantidades): altura e áreas com o perfil recortado.
- `spec/01-modelo-de-dados.md`: chaves novas no estado de `wall.create`/`wall.edit`
  (`top_shape`, `top_profile`, `tilt`).

## 7. Critérios de aceite (testes)
- [x] **UI73** Ponta de parede de retângulo arrastada sem Ctrl: só ela muda e a junção
      daquela ponta some; com Ctrl, a vizinha vai junto (§2; UI15 e UI43).
- [x] **UI74** 3D, parede selecionada sozinha: alças nas 2 pontas, face, topo e base
      (mais a de inclinação na etapa do §5); com duas paredes, nenhuma.
- [x] **UI75** 3D, arrastar a alça de topo até z = 2,50 numa parede de altura fixa
      2,80: `wall.edit` com altura fixa 2,50; digitar `3` com a alça presa dá 3,00. Com
      topo no pavimento de cima, muda o deslocamento do topo.
- [x] **UI76** 3D, alça de ponta e de face geram a mesma transação que as alças da planta.
- [x] **UI77** Empena 2,80 nas pontas e 4,00 na cumeeira, numa parede de 6 m: IFC com
      `IfcBooleanClippingResult` e dois `IfcPolygonalBoundedHalfSpace`; o sólido triangulado
      tem z máximo 4,00 em x = 3 e 2,80 nas pontas; `IfcMaterialLayerSetUsage` continua;
      `Qto_WallBaseQuantities.Height` = 4,00.
- [x] **UI78** Inclinado de 2,40 a 3,00: porta de 2,10 cabe; porta de 2,60 no início é
      recusada. Mudar o comprimento mantém as alturas.
- [x] **UI79** Tombar 10° uma parede de 14 cm e 2,80: `ExtrudedDirection` ≈ (0, 0,174,
      0,985), sem `IfcMaterialLayerSetUsage`, topo deslocado 0,494 m para a esquerda,
      espessura verdadeira 0,14; voltar a 0° restaura o `IfcMaterialLayerSetUsage`.
- [x] **UI80** Tombar parede com porta é recusado; porta em parede tombada é recusada.
- [x] **UI81** Salvar e reabrir: forma do topo, perfil e inclinação voltam iguais; os
      diários de UI75–UI79 reaplicados reproduzem o IFC.

## 8. Fontes públicas
Documentação IFC 4.3 no repositório oficial da buildingSMART, ramo `ifc4.3-main`,
consultada em 2026‑10‑15. Base:
`https://github.com/buildingSMART/IFC4.x-development/blob/ifc4.3-main/`

| Código | Documento |
|---|---|
| IFC-WALL | `docs/schemas/shared/IfcSharedBldgElements/Entities/IfcWall.md` (parede com camadas: espessura constante, extrusão vertical, `LayerSetDirection = AXIS2`; parede sem camadas: extrusão fora do eixo z permitida; `Body Clipping Geometry` com `IfcBooleanClippingResult` e semiespaços, figuras do recorte por `IfcPolygonalBoundedHalfSpace` e `IfcHalfSpaceSolid`) |
| IFC-PBHS | `docs/schemas/resource/IfcGeometricModelResource/Entities/IfcPolygonalBoundedHalfSpace.md` (contorno 2D fechado no plano xy da posição, extrudado ao longo de z; limita o semiespaço nas diferenças booleanas) |
| IFC-EAS | `docs/schemas/resource/IfcGeometricModelResource/Entities/IfcExtrudedAreaSolid.md` (`ExtrudedDirection`: qualquer direção não perpendicular ao z da posição) |
| IFC-MLSU | `docs/schemas/resource/IfcMaterialResource/Entities/IfcMaterialLayerSetUsage.md` |

Outras:
- **PAREDE** — `spec/elementos/parede.md` §1, §2, §11 (aprovada).
- **UI02**, **UI05**, **UI07** — specs de interface 02 §4, 05 §3 e 07 §3 (aprovadas).
- **CG** — conhecimento geral de modelagem de edifícios: oitão/empena sob telhado,
  parede inclinada, alças de altura em vistas 3D.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 9. Pontos de revisão
(a) Alças no 3D só com uma parede reta selecionada; arco só pontas, topo e base (§3).
(b) Altura pela alça muda deslocamento do topo ou altura fixa conforme o modo, sem trocar
    o modo (§3).
(c) Topo com quatro formas (plano, inclinado, empena, livre); alturas a partir da base;
    só parede reta (§4.1).
(d) Topo gravado como `Clipping` com um semiespaço limitado por trecho; camadas mantidas
    (§4.2).
(e) Inclinação de −45° a 45°, positiva para a esquerda, com espessura verdadeira (§5.1).
(f) Parede tombada sem `IfcMaterialLayerSetUsage` (o IFC exige extrusão vertical nas
    paredes com camadas) e sem aberturas nesta etapa (§5).
(g) Junções de paredes tombadas resolvidas só na base, com aviso (§5.1).
(h) Ordem: alças → topo → tombada, cada uma com seus testes; o pacote 2 (camadas) espera.
