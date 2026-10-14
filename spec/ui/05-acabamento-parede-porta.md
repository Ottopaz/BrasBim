---
documento: Interface — acabamento de parede e porta (espelhar, medidas no painel, alças e etiqueta da porta, propriedades comuns, junções manuais)
requisito: RF-NUC-05, RF-UI-02, RF-ELE-01, RF-ELE-05
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: em revisão
revisor: OTTO
---

# Acabamento de parede e porta

## 1. Propósito
Implementar, na interface e no que faltar do núcleo, itens já previstos nas specs
aprovadas da parede (`parede.md` §5.1, §6.2) e da porta (`porta.md` §5.1, §7) que ainda
não existem. Ordem combinada com o revisor em 2026‑10‑14 (pacote 1 de 3).

Padrão de interface da spec 03: ações sobre a seleção na **mini-barra**, campos no
**painel de propriedades**, ícones próprios com dica.

**Fora deste pacote:** cor por camada no 3D (`parede.md` §2.3) passa para o pacote 2
(camadas e estilos de material), porque depende de recortar o corpo da parede por camada,
o mesmo trabalho da planta em 1:50. O recurso de fatiar por camadas do IfcOpenShell
falha na geometria do BrasBim (verificado em 2026‑10‑14).

## 2. Espelhar (parede §5.1, porta §5.1, RF-NUC-05)
Ação **Espelhar** na mini-barra (seleção com parede) e no menu Editar.

1. Clique o primeiro ponto do eixo de simetria; 2. clique o segundo. Shift prende o eixo a
   múltiplos de 45°; *snap* como nas outras ferramentas. A pré-visualização mostra a
   seleção espelhada.
2. **Ctrl no segundo clique mantém o original** (espelha uma cópia).
3. Termina voltando a Selecionar, com a seleção (ou a cópia) selecionada.

Resultado: a **imagem espelhada** da seleção.

| Elemento | O que acontece | Operação |
|---|---|---|
| Parede | Caminho espelhado e **com o sentido invertido**, para que as camadas fiquem do lado espelhado (face externa continua externa) | `wall.edit` (caminho) |
| Abertura | Mesma posição espelhada: distância nova = comprimento − distância − largura | `opening.edit` |
| Porta | Abre para o lado espelhado (`opens_to` não muda, porque o sentido da parede inverteu) e **troca as dobradiças** (variante de mão, porta §2.2) | `door.edit` / `door_type.create` |
| Junções | Recalculadas pela geometria, como em Mover | `path_connection.*` |

- Porta selecionada sem a sua parede, ou só portas: recusado ("espelhe a parede que
  contém a porta").
- Porta de outra origem na seleção: recusado (o corpo dela não seria espelhado).
- Porta sem mão (correr de 2 folhas, vaivém de 2 folhas…): só a posição muda.
- Nenhuma operação nova.

## 3. Comprimento e ângulo no painel (parede §5.1)
Parede reta selecionada, grupo **Geometria**:

| Campo | Edição |
|---|---|
| Comprimento | Mantém o início e a direção; move o fim. As vizinhas em L no fim acompanham (como a alça, spec 02 §4.1) |
| Ângulo | Graus, 0° no eixo x do pavimento, positivo no sentido anti-horário. Gira em torno do início, mantendo o comprimento; vizinhas em L no fim acompanham |

- Medidos na **linha de referência** (o caminho). O comprimento das quantidades
  (`Qto_WallBaseQuantities.Length`, no eixo) continua em leitura, como "Comprimento no
  eixo".
- Parede em arco: comprimento e raio em leitura.
- Vários elementos: estes campos não aparecem (não há valor comum útil).

## 4. Alças da porta (porta §5.1)
Porta selecionada sozinha mostra, na planta, **duas alças nas bordas do vão** (no eixo da
parede):

- Arrastar uma alça muda a **largura**, mantendo a outra borda no lugar
  (`opening.edit`: largura e distância). Um número digitado é a largura.
- Posição que não cabe fica em vermelho e é recusada, como no arrasto da porta.
- Mover a porta continua sendo arrastar pelo meio dela (spec 0.1 §5.1).
- Altura: no painel (a planta não mostra a altura). Alça de altura fica para as vistas de
  corte e fachada.

## 5. Etiqueta da porta (porta §7)
- A planta mostra, junto a cada porta, o **código** (`Pset_DoorCommon.Reference`, ex.:
  `P1`) e, numa segunda linha opcional, **largura × altura** do vão (`0,86 × 2,13`).
- Posição: no meio do vão, do lado da parede **oposto** ao da folha, a 0,30 m da face.
- Texto em tamanho fixo na tela (como os rótulos de medida), centralizado.
- **Exibir > Etiquetas de porta** liga e desliga; **Exibir > Medidas na etiqueta** liga e
  desliga a segunda linha. Preferências do aplicativo, lembradas entre sessões; nada vai
  para o IFC (porta §2.3).
- Porta de outra origem: o `Reference` dela; sem `Reference`, o nome; sem nome, sem
  etiqueta.

## 6. Propriedades comuns no painel (parede §3.3, porta §3.3)
Grupo **Propriedades comuns** no painel da parede e da porta (e na edição em lote, com
"vários"). Cada mudança é um `wall.edit` / `door.edit` do campo `common` (já existentes).
Valor igual ao padrão do tipo não é gravado como diferença.

| Campo | Propriedade IFC | Parede | Porta | Edição |
|---|---|---|---|---|
| Código | `Reference` | sim | sim (leitura: vem do tipo) | texto |
| Situação | `Status` | sim | sim | lista: nova, existente, a demolir, temporária |
| Externa | `IsExternal` | sim | sim | caixa |
| Estrutural | `LoadBearing` | sim | — | caixa |
| Resistência ao fogo | `FireRating` | sim | sim | texto (ex.: "EI 60") |
| Desempenho acústico | `AcousticRating` | sim | sim | texto |
| Transmitância térmica | `ThermalTransmittance` | sim | — | número, W/(m²·K) |
| Acessível | `HandicapAccessible` | — | sim | caixa |
| Saída de emergência | `FireExit` | — | sim | caixa |

[IFC: `Pset_WallCommon`, `Pset_DoorCommon`, IFC 4.3]

## 7. Junções manuais (parede §6.2)
Com **exatamente duas paredes** selecionadas, a mini-barra mostra as ações que se
aplicam:

| Ação | Quando | O que faz |
|---|---|---|
| **Unir** | Duas paredes retas não paralelas | Estende ou encurta as paredes pela própria direção até o cruzamento dos caminhos. Se o cruzamento cai no meio de uma delas, só a outra muda (junção T); se cai fora das duas, as duas mudam (junção L, a extremidade mais próxima do cruzamento vai até ele). Se havia "junção desfeita" entre elas, ela deixa de valer |
| **Desfazer junção** | As duas estão ligadas por uma junção | Remove a relação; as extremidades ficam retas. A decisão é **lembrada**: a junção não volta sozinha quando uma das paredes for editada |
| **Trocar a contínua** | Junção em X (as duas se cruzam pelo meio) | A outra parede passa a ser a contínua na planta (desenhada por cima, sem interrupção) |

- Junção em T não tem "trocar a contínua": a parede que chega é a que tem a extremidade
  no meio da outra (é geometria, não escolha).
- Ícones próprios: unir, desfazer junção, trocar a contínua.

### 7.1 Gravação *(decisão do projeto)*
- **Junção desfeita:** nova propriedade `SemJuncaoCom` no Pset `BrasBim_Parede` das duas
  paredes (`IfcText`, GlobalIds separados por espaço). No estado da parede, o campo
  `no_join` (lista de GlobalIds). A detecção automática de junções (`sync_ops`) ignora os
  pares listados em qualquer uma das duas. Editar/desfazer por `wall.edit` (campo
  `no_join`) — nenhuma operação nova; atualizar `spec/01-modelo-de-dados.md`.
- **Contínua em X:** é o `RelatingElement` da `IfcRelConnectsPathElements` (parede §6.2);
  trocar = `path_connection.delete` + `path_connection.create` com os papéis trocados.
  A sincronização automática mantém a relação existente (já é assim).
- **Planta em X:** a contínua é desenhada por último, com o fundo da planta por baixo do
  seu preenchimento, cobrindo as linhas da outra no cruzamento.

## 8. Ícones novos
espelhar, unir, desfazer junção, trocar a contínua — mesmo estilo da spec 03 §3.

## 9. Critérios de aceite (testes)
- [ ] **UI41** Espelhar um retângulo com porta pelo eixo x = 10: caminhos espelhados e
      invertidos, porta na posição espelhada, abrindo para o lado espelhado, com as
      dobradiças trocadas; 4 junções; desfazer volta tudo; Ctrl no segundo clique mantém o
      original e cria a cópia espelhada.
- [ ] **UI42** Espelhar só uma porta é recusado; espelhar parede com porta de outra
      origem é recusado.
- [ ] **UI43** Comprimento 5,00 → o fim se move e a vizinha em L acompanha; ângulo 90° numa
      parede de (0,0) a (4,0) leva o fim a (0,4).
- [ ] **UI44** Arrastar a alça direita da porta aumenta a largura com a borda esquerda
      fixa; digitar `0,90` define a largura; posição que não cabe é recusada.
- [ ] **UI45** A planta tem a etiqueta "P1" no lado oposto à folha; ligar "Medidas na
      etiqueta" acrescenta "0,86 × 2,13"; desligar "Etiquetas de porta" tira as duas.
- [ ] **UI46** Marcar "Externa" e escrever "EI 60" em Resistência ao fogo grava no
      `Pset_WallCommon`; voltar ao padrão remove a diferença; idem na porta
      (`HandicapAccessible`); em lote, 3 paredes numa transação.
- [ ] **UI47** Unir duas paredes perpendiculares soltas cria a junção L no cruzamento;
      uma que termina antes de uma parede longa vira T.
- [ ] **UI48** Desfazer junção remove a relação e grava `SemJuncaoCom` nas duas; mover uma
      delas não recria a junção; Unir volta a ligar e limpa `SemJuncaoCom`.
- [ ] **UI49** Trocar a contínua num X troca `RelatingElement`; editar uma das paredes
      mantém a escolha; a planta desenha a contínua por cima.
- [ ] **UI50** Os diários de UI41–UI49 reaplicados num projeto novo reproduzem o IFC.

## 10. Fontes públicas
- **PAREDE**, **PORTA** — `spec/elementos/parede.md` §3.3, §5.1, §6.2 e `porta.md` §2.2,
  §3.3, §5.1, §7 (aprovadas).
- **UI02**, **UI03** — specs de interface 0.2 e 03 (aprovadas).
- **IFC** — buildingSMART IFC 4.3: `Pset_WallCommon`, `Pset_DoorCommon`,
  `IfcRelConnectsPathElements`.
- **CG** — conhecimento geral de aplicativos de CAD: espelhar por eixo de dois pontos,
  estender até o cruzamento, etiquetas de esquadria.

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 11. Pontos de revisão
(a) Espelhar gera a imagem espelhada, com as dobradiças trocadas (§2). A `porta.md` §5.1
    fala em "preservar o lado físico"; aqui isso é lido como "o lado espelhado".
(b) Ctrl no segundo clique para espelhar uma cópia (§2).
(c) Cor por camada no 3D vai para o pacote 2 (§1).
(d) Etiqueta do lado oposto à folha, a 0,30 m (§5).
(e) Junção desfeita lembrada no Pset da parede (§7.1).
