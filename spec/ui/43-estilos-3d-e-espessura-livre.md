---
documento: Estilos de apresentação do 3D e espessura livre de parede e laje
requisito: RF-VIS (vista 3D), RF-ELE (modelagem); pedidos do revisor em 2026-11-01
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-01
status: §2 aprovado e implementado em parte (2026-11-01); §3 em revisão
revisor: OTTO
---

# Estilos de apresentação do 3D e espessura livre de parede e laje

## 1. Propósito
Dois pedidos do revisor (2026‑11‑01):
1. o 3D de hoje (cores do material + todas as arestas que a geometria devolve) é **uma**
   forma de apresentação; faltam outras, como o modelo sem essas linhas e o modelo todo
   branco, a partir do estudo das apresentações 3D do Archicad;
2. editar a **espessura da parede e da laje** com qualquer valor, mantendo os tipos
   pré‑configurados.

Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_estilos_3d.md`.
Pontos para o revisor no §5.

## 2. Estilos do 3D

### 2.1 O que é um estilo
Um conjunto com nome de cinco escolhas:

| Escolha | Valores |
|---|---|
| Faces | cor do material · cor única (escolhida) · cor do fundo (sem faces) · sem faces (transparente) |
| Luz | sombreado pela direção da luz · chapado (faces iguais, mesma cor) |
| Arestas | contorno (arestas vivas e silhuetas) · todas (inclusive as de trás) · nenhuma |
| Espessura das arestas | 1 a 4 px |
| Cor das arestas | escolhida (padrão: cinza‑escuro) |

**Contorno** (novo): entra a aresta entre duas faces que fazem ângulo maior que 20°, a
aresta de borda e a silhueta. Some a emenda entre faces quase no mesmo plano (as faixas
das árvores, os triângulos das faces trianguladas). É provável que sejam essas as linhas
que incomodam hoje (ver §5 (a)).

### 2.2 Estilos de fábrica (nomes próprios)
1. **Colorido** — cor do material, sombreado, contorno 1 px. (O 3D de hoje, já sem as
   emendas.)
2. **Colorido sem linhas** — cor do material, sombreado, sem arestas.
3. **Maquete branca** — cor única branco‑gelo, sombreado, contorno 1 px cinza.
4. **Maquete branca sem linhas** — cor única, sombreado, sem arestas (volume puro).
5. **Desenho** — faces na cor do fundo, chapado, contorno 1,5 px preto: aparência de
   linhas ocultas, como um desenho técnico em perspectiva.
6. **Arame** — sem faces, todas as arestas (o modo que mostra o que fica atrás).

O vidro continua translúcido em todos (no branco, um cinza‑claro translúcido).

### 2.3 Onde se escolhe
- **Barra da vista do 3D:** lista "Estilo" com os de fábrica e os do usuário.
- **Exibir > Estilos do 3D**: diálogo para criar, duplicar, renomear e excluir estilos do
  usuário (os de fábrica não se apagam).
- A **vista 3D salva** guarda o estilo; a imagem dela na prancha usa o estilo gravado.
- Os estilos do usuário ficam **só na preferência de cada pessoa** (resposta (c),
  2026‑11‑04), não no IFC; o último estilo usado também.

### 2.4 Segunda etapa (fora desta entrega)
Sombras do sol (data, hora, norte do projeto) e sombra suave de ambiente pedem shaders
(o 3D de hoje usa OpenGL de função fixa). Entram depois, como opção "Sombras" no estilo.

### 2.5 Testes
E3D01 contorno tira as emendas de uma malha facetada (cilindro) e mantém as arestas
vivas de uma caixa; E3D02 cada estilo de fábrica produz as cores e as arestas esperadas
na cena (sem tela); E3D03 a vista salva guarda e devolve o estilo, e a imagem da prancha
o usa; E3D04 estilo do usuário gravado na preferência e relido.

## 3. Espessura livre de parede e laje

### 3.1 Uso
- Na **ficha** da parede e da laje, o campo **Espessura** passa a ser editável (hoje é só
  leitura). Na barra **Opções** das ferramentas Parede e Laje entra o campo Espessura ao
  lado do tipo: vazio = a do tipo.
- Digitar um valor diferente do tipo dá ao elemento uma **variante** do tipo com essa
  espessura; digitar a do tipo volta ao tipo original. Vale para vários elementos
  selecionados de uma vez.
- A lista de tipos continua com os pré‑configurados; as variantes aparecem recolhidas
  abaixo do tipo de origem ("Alvenaria 14 · 17 cm").

### 3.2 Qual camada muda
O tipo tem camadas (reboco + bloco + reboco). A diferença vai para a **camada que
estica**: a de categoria estrutural (`LoadBearing`); sem ela, a mais grossa. As outras
ficam iguais. Ex.: Alvenaria 14 (2,5 + 9 + 2,5) com 17 cm → 2,5 + 12 + 2,5. A camada que
estica não pode ficar com menos de 1 cm (recusa com mensagem).

### 3.3 No IFC
- A espessura no IFC é a soma das camadas do `IfcMaterialLayerSet` do **tipo**, e a
  ocorrência aponta para esse conjunto pelo `IfcMaterialLayerSetUsage`. Por isso a
  variante é um **tipo de verdade** (`IfcWallType` / `IfcSlabType`), com o próprio conjunto
  de camadas, e não um valor solto na ocorrência: qualquer programa que lê o IFC vê a
  espessura certa e as camadas certas.
- A variante guarda a origem no Pset `BrasBim_Variante` (`Origem` = GlobalId do tipo,
  `Espessura`). Mudar materiais ou camadas do tipo de origem atualiza as variantes
  (mantendo a espessura delas); a variante que fica sem nenhum elemento sai sozinha.
- Operações serializáveis (desfazer, equipe), como as variantes de mão das esquadrias.

### 3.4 Testes
EL01 parede com espessura digitada: variante criada, camada estrutural esticada, corpo,
junções e quantidades com a espessura nova; EL02 a segunda parede com a mesma espessura
usa a mesma variante; EL03 voltar à espessura do tipo apaga a variante sem uso; EL04
laje; EL05 mudar o material do tipo de origem chega à variante; EL06 interface (ficha e
barra Opções); desfazer/refazer e diário em todos.

## 4. Ordem
1. Espessura livre (§3): uma sessão. 2. Estilos do 3D (§2): uma sessão. 3. Sombras (§2.4)
depois.

## 4a. Andamento (2026‑11‑01)
O revisor pediu as vistas do 3D "urgentemente": o §2 entrou antes do §3.
- **Feito:** os seis estilos de fábrica (`brasbim/core/view_styles.py`); contorno com
  arestas vivas (> 20°), bordas e silhuetas calculadas pelo olho a cada quadro; escolha
  em Exibir > Estilo do 3D e no botão da barra da vista (só com o 3D à vista); o último
  estilo fica na preferência; a vista 3D salva grava `options.style` e a imagem da prancha
  o usa; o 3D da área herda o estilo. A janela do 3D passou a pedir profundidade de 24
  bits e 4 amostras: com 16 bits (padrão de algumas placas) as arestas de trás das peças
  finas vazavam pelas faces. **Causa real das "arestas invisíveis" (achada depois, no
  mesmo dia):** o QPainter do controle de orientação desliga o teste de profundidade ao
  fim de cada quadro, e ele só era ligado ao criar a janela; agora `draw_scene` refaz o
  estado a cada quadro (teste E3D05).
  Testes E3D01–E3D03 (`tests/test_estilos_3d.py`).
- **Falta do §2:** estilos do usuário (diálogo e Pset `BrasBim_Estilos3D`, E3D04).
- **Junto (pedido do mesmo dia):** alças da laje no 3D — vértices, meio dos lados, centro
  (mover livre), setas X e Y (mover só naquele eixo, com a distância no quadro de
  medidas) e seta Z (sobe e desce a laje: deslocamento do topo).

## 4b. Andamento (2026‑11‑04)
- **§3 feito:** `brasbim/core/type_variants.py` e a interface (ficha e barra Opções;
  variantes recuadas sob o tipo na ficha e na janela de tipos, fora das listas das
  ferramentas). Testes EL01–EL06.
- **E3D04** passa a ser só preferência do usuário (resposta (c)).

## 5. Pontos para o revisor
**Respostas (2026‑11‑04):** (a) era o defeito do teste de profundidade (corrigido; "3D
ótimo e adequado"); (b) os seis estilos servem; (c) estilos do usuário **só na preferência
de cada um** (não no IFC); (d) esticar a camada estrutural; (e) variantes recolhidas sob o
tipo de origem; (f) a ordem serve.

- (a) As "arestas invisíveis" que incomodam são as **emendas** das faces (faixas nas
  árvores, triângulos), ou linhas que aparecem **atrás** das paredes? Um print em
  `feedback/prints/` ajuda. (Na imagem do README não aparecem linhas atrás das faces.)
- (b) Os seis estilos de fábrica do §2.2 servem? Algum a mais ou a menos?
- (c) Estilos do usuário no IFC do projeto (proposta) ou só na preferência de cada um?
- (d) Espessura: esticar a camada estrutural (proposta) ou perguntar qual camada a cada
  vez?
- (e) Variantes recolhidas sob o tipo de origem (proposta) ou como tipos comuns na lista?
- (f) A ordem do §4 (espessura antes do 3D) serve?

## 6. Fontes
`research_notes/Pesquisa Archicad Revit AutoCAD/complemento_estilos_3d.md` (ajuda do
Archicad 21, 26, 27 e 28, documentação da API, fórum e suporte da Graphisoft);
`visualizacao_apresentacao.md`; especificação IFC 4.3 (`IfcMaterialLayerSetUsage`,
`IfcMaterialLayerSet`).
