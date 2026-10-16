---
documento: Documentação 2 — cortes e fachadas gerados do modelo
requisito: RF-DOC-02, RF-DOC-03, RF-DOC-04, RF-DOC-07
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-16
status: em revisão
revisor: OTTO
---

# Documentação 2: cortes e fachadas (pacote 7)

## 1. Propósito
Segundo pacote de documentação: **cortes** e **fachadas** gerados do modelo e atualizados
sozinhos quando ele muda (RF-DOC-02), com o símbolo do corte na planta (RF-DOC-07). As
pranchas e o PDF são o pacote 8.

Fica de fora (V1): cotas e textos desenhados dentro do corte (só os automáticos de §5),
corte com degrau (linha de corte quebrada), vistas internas com profundidade limitada
por caixa, sombras e cores nas fachadas.

## 2. O que é uma vista
Uma **vista** é definida por uma linha na planta, de A para B, e pelo lado para onde se
olha (à **esquerda** de quem anda de A para B, por padrão):

| Tipo | Linha | O que mostra |
|---|---|---|
| **Corte** | atravessa o edifício | o plano vertical pela linha corta os elementos; mostra a seção cortada e, além dela, o que se vê |
| **Fachada** | fica fora do edifício | nada é cortado; mostra o que se vê do lado olhado |

Parâmetros: nome ("Corte A", "Fachada frontal"), tipo, pontos A e B, lado, profundidade
(quanto se vê além da linha; vazio = tudo), cotas inferior e superior mostradas (vazio =
do menor ao maior elemento), escala (como a planta, spec/ui 13 §2; padrão 1:50).

## 3. IFC
- `IfcAnnotation` com `ObjectType` "VistaDeCorte" (corte) ou "VistaDeFachada", contida
  na **edificação** (`IfcRelContainedInSpatialStructure`; atravessa os pavimentos)
  [IFC-ANNOT]. Representação `Annotation` (contexto `Plan`): a linha da vista e o
  símbolo (§6), para quem abre o arquivo em outro programa ver onde está o corte.
- Pset `BrasBim_Vista`: os parâmetros de §2 (em JSON, como as anotações do pacote 6).
- O desenho do corte **não** vai para o IFC: é calculado ao abrir a vista e ao imprimir
  *(decisão do projeto: o IFC não tem entidade padrão para o desenho gerado; ele é
  derivado do modelo, como a planta)*.
- Operações: `view.create` / `.delete` / `.edit`.

## 4. Como o desenho é gerado
Sem Qt, em `core/drawings/` *(decisão do projeto)*, a partir das malhas do
`ifcopenshell.geom` (as mesmas da vista 3D), no sistema da vista: *u* ao longo de A→B,
*v* para cima (cota da edificação) e *w* a profundidade para o lado olhado.

1. **Seção:** cada elemento cujo corpo atravessa o plano *w* = 0 é cortado: as
   interseções dos triângulos com o plano formam os contornos cortados, preenchidos com
   o estilo de corte do material (spec/ui 06 §4; parede com camadas, uma região por
   camada; viga, pilar e laje pelo material) e com contorno grosso.
2. **Vista além do plano:** os triângulos com *w* > 0 (até a profundidade) são projetados
   e desenhados do mais longe para o mais perto, cada um preenchido de branco; as
   **arestas** do elemento (as do sólido, não as diagonais da triangulação) vão junto, na
   profundidade delas. O que está na frente cobre o que está atrás *(algoritmo do pintor;
   decisão do projeto: dá o desenho de linhas ocultas sem depender de uma biblioteca de
   CAD; casos de sobreposição cíclica são raros em edificações e ficam como estão)*.
3. **Na fachada**, o passo 1 não existe (nada atravessa a linha).
4. **Terreno:** uma linha grossa na cota 0,00 de ponta a ponta (linha de piso) *(CG)*.

Classes desenhadas: parede, porta, janela (o vidro como contorno), laje, pilar, viga.
Ambientes e anotações não aparecem no corte.

Atualização: o desenho é refeito quando o modelo muda e a vista está aberta (o que
mudou fora da faixa da vista é ignorado).

## 5. O que o corte traz sozinho
- **Cotas de nível** de cada pavimento, do lado direito, com o símbolo do pacote 6
  ("+0,00", "+2,80"), e do topo de cada laje cortada quando difere do pavimento.
- **Título** embaixo: "CORTE A" (ou o nome da fachada) e a escala ("ESC. 1:50"), em 5 e
  3 mm *(CG)*.
- **Nomes dos pavimentos** junto às cotas de nível.

## 6. Símbolo na planta
- Corte: a linha de corte em traço e ponto grosso nas pontas e fino no meio, com uma
  seta em cada ponta apontando o lado olhado e a letra ("A") junto às setas *(CG)*.
- Fachada: uma seta com o nome junto, no meio da linha.
- Aparece na planta de todos os pavimentos que a vista atravessa (corte) ou de todos
  (fachada). Escolha, Mover, Girar, Espelhar e Excluir como as anotações; alças nas
  pontas A e B.

## 7. Interface
- Ferramentas **Corte** e **Fachada** no grupo Documentação: clique A, clique B, clique
  do lado olhado (a pré-visualização mostra as setas). Letra automática: A, B, C…
  (fachadas: "Fachada 1", "Fachada 2"…).
- Painel do projeto: lista **Vistas** abaixo dos pavimentos; clique duplo abre a vista.
- A vista abre numa aba própria ("Corte A") ao lado de Planta e 3D, com zoom e
  deslocamento como a planta, e com a escala na barra de estado. Selecionar no corte
  seleciona o elemento (e a seleção aparece na planta e no 3D).
- Painel com a vista selecionada (na planta ou na lista): Nome, Lado, Profundidade,
  Cotas mostradas, Escala.
- Exibir > Símbolos de corte (padrão ligado).

## 8. Critérios de aceite (testes)
Térreo (0,00) e Superior (2,80); retângulo de paredes de 14 cm (0, 0)–(6, 4) com topo no
Superior, uma porta de 0,80 × 2,10 na parede de baixo a 1,00 do início, laje de 10 cm no
Superior sobre o retângulo.

- [ ] **CF01** Corte de (3, −1) a (3, 5), olhando para a esquerda (−x): `IfcAnnotation`
      "VistaDeCorte" na edificação; o desenho tem as seções das duas paredes de baixo e
      de cima (largura 0,14, altura 2,80) e da laje (0,10 de altura, de 0 a 4 em *u*).
- [ ] **CF02** A seção da parede tem o preenchimento do estilo do material (por camadas:
      3 regiões).
- [ ] **CF03** A face interna da parede da esquerda (x = 0,14) aparece em vista entre as
      duas seções; nada do que fica atrás das paredes cortadas aparece por cima delas.
- [ ] **CF04** Cotas de nível "+0,00" e "+2,80" e o título "CORTE A".
- [ ] **CF05** Fachada de (−1, −2) a (7, −2) olhando para +y: a porta aparece na parede
      (contorno do vão); nada é cortado.
- [ ] **CF06** Mover a parede de cima para y = 5: o corte aberto mostra a seção em
      *u* = 5,07; desfazer volta.
- [ ] **CF07** Símbolo do corte nas plantas do Térreo e do Superior, com a letra A e as
      setas para −x.
- [ ] **CF08** O arquivo passa na validação de esquema; o diário reaplicado reproduz o
      IFC (as vistas inclusive).

## 9. Fontes públicas
- IFC 4.3: `IfcAnnotation` (contenção na estrutura espacial, representação 2D), como em
  spec/ui 13 §11.
- **IfcOpenShell** (LGPL, `cleanroom/FONTES.md`): as malhas por elemento
  (`ifcopenshell.geom`), já usadas na vista 3D. O módulo de desenho dele não é usado
  *(decisão do projeto: o estilo das linhas e as hachuras dos materiais ficam com o
  BrasBim)*.
- **NBR 6492**: representação de cortes e fachadas, **texto não lido**; convenções de
  conhecimento geral, a conferir.
- **CG**: convenções usuais (linha de corte em traço e ponto com setas e letra, cotas de
  nível no corte, título com a escala, linha de piso).

Nenhum material de `_restrito/` nem de `tools/` foi usado. Nenhum texto, ícone, nome de
comando ou layout de diálogo de outro software foi copiado.

## 10. Pontos de revisão
(a) O desenho do corte calculado e não gravado no IFC (§3).
(b) Algoritmo do pintor para as linhas ocultas (§4).
(c) Cotas de nível automáticas à direita e título com a escala (§5).
(d) Símbolo de corte: traço e ponto, setas e letra (§6).
