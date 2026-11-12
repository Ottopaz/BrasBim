---
elemento: Forma livre
entidade_ifc: IfcFurniture / IfcSanitaryTerminal / IfcElectricAppliance / IfcGeographicElement / IfcBuildingElementProxy, com corpo em malha (`Tessellation`)
requisito: pedido do revisor em 2026-11-12 ("uma geometria de modelagem livre; em geometrias muito complexas, gerar o modelo assim em vez de objeto, já que o objeto é parametrizável")
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-12
status: aprovado (fase 1 implementada; "pode implementar", revisor em 2026-11-12)
revisor: OTTO
versão: 0.0.2
---

# Forma livre

Na interface o elemento se chama **Forma livre** (decisão do revisor, 2026-11-12). No
código, `freeform` (`core/freeform/`).

## 1. Propósito
Uma peça única, de geometria qualquer, que não vale a pena parametrizar: uma escultura,
uma poltrona de desenho autoral, uma luminária orgânica. O objeto paramétrico
(`objeto-parametrico.md`) serve ao que se repete e muda de medida; a forma livre guarda
**a geometria pronta**, em malha, sem definição, tipo nem parâmetros.

Outros programas têm um elemento de modelagem livre, que nasce de formas básicas, de uma
seleção convertida ou de revolução, e que só tem a elevação como parâmetro numérico
[H-MORPH]. Daqui vem só a função; nome, textos e comportamento são próprios.

**Fase 1 (esta spec):** o elemento, três formas de criar (Assistente, arquivo, converter
seleção) e as transformações básicas. **Fase 2 (spec futura):** editar vértices, arestas
e faces; gerador de 3D a partir de foto como conector.

## 2. Mapeamento IFC
- **Classe pela categoria**, a mesma tabela do objeto paramétrico (§2.1 de lá):
  Mobiliário, Louças e metais, Eletrodomésticos, Vegetação e Genérico
  (`IfcBuildingElementProxy`, onde entra a escultura, com `ObjectType` livre).
  `PredefinedType` = `USERDEFINED` e `ObjectType` = o que o usuário escrever.
- **Sem tipo:** não há `IfcRelDefinesByType`. Cada forma livre é uma ocorrência só.
- **Corpo:** representação `Body` / `Tessellation`, um `IfcTriangulatedFaceSet` por
  **parte** (grupo de faces com um material), fechado quando a malha for fechada
  (`Closed`). Cor por `IfcStyledItem` do material da parte. Já há malha no modelo no
  terreno (`core/terrain.py`) e nas operações de sólidos (`structure/solids.py`).
- **Planta:** representação `FootPrint` / `Curve2D` com a **silhueta** vista de cima
  (§7), gravada junto com o corpo. Outros programas IFC também a leem.
- **Posição:** `IfcLocalPlacement` no pavimento (ponto, elevação, rotação em z). A
  escala é aplicada aos vértices (não fica no posicionamento).
- **Material:** um `IfcMaterial` por parte, em `IfcMaterialConstituentSet`.
- **Pset `BrasBim_FormaLivre`:** marca o elemento e guarda a origem ("assistente",
  "arquivo poltrona.obj", "convertido de 3 elementos"), a descrição e, se criada pelo
  Assistente, a **receita** (as formas pedidas, em JSON, §4.1) para ele poder corrigir.
- **Quantidades:** `Qto_*BaseQuantities` não se aplica a todas as classes; grava‑se
  `BrasBim_FormaLivre.Volume` (só malha fechada) e a caixa (largura, profundidade,
  altura).
- Contida no pavimento por `IfcRelContainedInSpatialStructure`; camada padrão da
  categoria, como os objetos.

## 3. Parâmetros
| Parâmetro | Tipo | Padrão | Regras |
|---|---|---|---|
| Nome | texto | "Forma livre" | livre |
| Categoria | escolha | Genérico | muda a classe IFC (o `GlobalId` fica) |
| Ponto, rotação | [x, y], graus | clique | no pavimento |
| Elevação | comprimento | 0 | base da caixa acima do piso |
| Largura, profundidade, altura | comprimento | da malha | editar **estica** a malha naquele eixo; "manter proporção" ligado por padrão |
| Partes | lista | 1 | nome e material de cada uma |
| Triângulos, origem | só leitura | | |

**Limite de triângulos (ponto de revisão (a)):** até **20 000** por forma livre. Acima
disso a malha é **simplificada** ao entrar (agrupamento de vértices numa grade, feito
aqui, sem biblioteca nova) e o usuário é avisado de quantos triângulos tinha e com
quantos ficou. Abaixo de 20 000 nada muda. A peça feita de formas (§4.1) procura ficar em
até **9 000**: o detalhe das curvas (divisões de uma volta: 28, 20, 12 ou 8) é o maior
que cabe nisso.

## 4. Criação

### 4.1 Pelo Assistente (spec/ui 54)
Ferramenta `create_freeform`: a IA descreve a peça por **formas**, e o BrasBim as
transforma numa malha só. Sem parâmetros para manter, o vocabulário é mais rico que o
das peças do objeto:

| Forma | Campos |
|---|---|
| Caixa | centro, medidas, **raio de canto** (0 = viva) |
| Elipsoide | centro, três raios |
| Cilindro / cone | base, altura, raio de baixo e de cima |
| Tubo | caminho 3D (pontos, reto ou suave), seção redonda (raio) ou retangular |
| Seções | contornos (pontos ou elipse) em alturas ou posições sucessivas, ligados entre si (afunila, torce, engorda) |
| Revolução | perfil (reto ou suave) em torno de um eixo, ângulo |
| Extrusão | perfil fechado, direção e comprimento |

Toda forma tem posição, **rotação nos três eixos**, material e nome da parte. As formas
podem se sobrepor (reunião sem booleano, como nas peças do objeto). Até 80 formas.

- `edit_freeform`: troca a receita (inteira ou algumas formas) e refaz a malha, mantendo
  o `GlobalId`. Só vale enquanto a forma livre tiver receita.
- `view_object` passa a aceitar o id de uma forma livre (as quatro vistas).
- **Regra para a IA:** peça regular, que se repete ou muda de medida → objeto
  paramétrico. Peça única, inclinada, curva ou esculpida → forma livre. Ela diz na
  resposta qual escolheu e por quê. Continuam valendo: medidas do usuário ou típicas,
  conferir na prévia, nada de marca na geometria.

### 4.2 De um arquivo
Arquivo > Importar > **Forma livre de arquivo…**: **OBJ**, **STL** e **GLB** (leitura
feita aqui; OBJ com os materiais do MTL viram partes). Diálogo próprio: nome, unidade
do arquivo (mm, cm, m), eixo para cima (Y ou Z), categoria, e as medidas e o número de
triângulos que a peça terá, com o aviso da simplificação (§3). A peça entra **no meio da
planta, selecionada**, e a mensagem pede para movê-la ao lugar (o clique para posicionar
fica para depois: ponto de revisão (f)). A licença do arquivo é do usuário.

### 4.3 Convertendo uma seleção
Editar > **Converter em forma livre**: objetos paramétricos e formas livres
selecionados viram **uma** forma livre (partes pelos materiais). Os originais são
excluídos na mesma transação (um passo de desfazer). Fase 1: só essas duas classes de
origem (ponto de revisão (b): paredes, lajes e o resto ficam para depois).

## 5. Edição
- Mover, girar, espelhar, copiar e excluir, pelos comandos de sempre (`core/transform`,
  `core/delete`). Elevação e medidas no painel Propriedades (§3).
- Trocar o material e o nome de cada parte; trocar a categoria; camada.
- **Operações** (serializáveis, com o estado completo para desfazer): `freeform.create`,
  `freeform.delete`, `freeform.edit`. A malha vai no dado da operação.
- **Não há** edição de vértice, aresta ou face nesta fase.

## 6. Comportamento
- Não se junta a paredes nem a outros elementos, não abre vão e não é hospedada.
- Fica fora das operações de sólidos (spec/ui 41) nesta fase (ponto de revisão (c)).
- **Desempenho:** a malha é triangulada uma vez e guardada pela cena 3D como os outros
  elementos; a planta usa só a silhueta gravada. Cada cópia leva a sua malha no IFC
  (simples; ponto de revisão (d): geometria compartilhada por `IfcMappedItem` se os
  arquivos crescerem).
- **Arestas no 3D:** só as quinas (ângulo entre faces acima do limite que a cena já usa,
  `feature_edges`) e o contorno; a malha não aparece como arame.

## 7. Representação 2D
- **Planta:** a silhueta vista de cima (reunião dos triângulos projetados, pelo
  shapely), em linha de vista. Acima do plano de corte do pavimento: tracejada, como os
  outros elementos altos. A planta **não** corta a malha na altura do plano nesta fase
  (ponto de revisão (e)).
- **Corte e fachada:** pelo mesmo caminho dos outros elementos (corpo cortado pelo
  plano; em vista, o contorno e as quinas). A conferir na implementação se o corte de
  malha aberta dá hachura ou só linha.

## 8. Quantitativos
Contagem por categoria e nome nas tabelas; volume quando a malha é fechada; caixa
(largura × profundidade × altura).

## 9. Critérios de aceite (testes)
- **FL01:** `freeform.create` grava a classe da categoria, o corpo `Tessellation` por
  parte, o `FootPrint` e o Pset; desfazer e refazer voltam ao mesmo IFC; reabrir o
  arquivo dá o mesmo estado.
- **FL02:** cada forma do §4.1 gera malha fechada com a caixa esperada (caixa com raio,
  elipsoide, cone, tubo suave, seções, revolução, extrusão), com rotação nos três eixos.
- **FL03:** `create_freeform` pelo Assistente: recusas com o lugar ("forma 3 'Encosto':
  raio ≤ 0"), limite de formas, receita gravada; `edit_freeform` refaz mantendo o
  `GlobalId`; sem receita, recusa.
- **FL04:** importar OBJ (com MTL), STL e GLB: unidade e eixo aplicados; malha de 100 000
  triângulos entra com ≤ 20 000 e o aviso; arquivo inválido recusado.
- **FL05:** converter dois objetos numa forma livre: uma ocorrência, partes pelos
  materiais, originais excluídos, um passo de desfazer.
- **FL06:** mover, girar, espelhar, copiar; mudar a altura estica a malha e a silhueta;
  trocar categoria muda a classe e mantém o `GlobalId`.
- **FL07:** planta mostra a silhueta (tracejada acima do plano de corte); corte e 3D
  mostram a peça; tabela conta por categoria.

## 10. Fontes públicas
- buildingSMART IFC 4.3: `IfcTriangulatedFaceSet`, `IfcBuildingElementProxy`,
  representação `Tessellation` e `FootPrint`.
- [H-MORPH] `research_notes/Pesquisa Archicad Revit AutoCAD/archicad_modelagem.md`,
  "Morph (modelagem livre)", a partir da ajuda pública citada lá (formas de criar,
  edição e limitações).
- `spec/elementos/objeto-parametrico.md` (categorias e classes) e
  `spec/ui/54-assistente-foto-e-objeto-novo.md` (Assistente).

## 11. Implementação (2026-11-12)
- Núcleo em `brasbim/core/freeform/`: `shapes.py` (as sete formas → malha fechada),
  `mesh.py` (caixa, volume, silhueta, quinas, simplificação), `elements.py` (estado,
  gravação e operações), `commands.py` (criar, editar, esticar, material da parte,
  converter), `importer.py` (OBJ, STL, GLB) e `plan.py` (silhueta na planta, com os
  papéis dos objetos).
- Ligações: `transform.py` (mover, girar, espelhar, copiar), `delete.py`,
  `display_layers.py` (camada da categoria, a mesma dos objetos), `plan.py`,
  `drawings/section.py`, `ui/scene3d.py`, `quantities/tables.py` (tabelas de objetos:
  "Forma livre" na coluna Objeto, o nome da peça na coluna Tipo), `ui/properties.py`,
  `ui/main_window.py` (Arquivo > Importar forma livre; Editar > Converter em forma
  livre) e `ui/freeform_dialog.py`.
- **Desempenho medido** (poltrona de 19 472 triângulos): pela triangulação genérica do
  IFC (`ifcopenshell.geom`) o 3D levava 4,9 s e o corte 5,2 s. O 3D e os cortes passaram
  a ler a malha gravada direto (`elements.world_parts`): 0,06 s e 0,4 s. A planta leva
  0,06 s (só a silhueta). Exportar 3D (glTF, OBJ) ainda usa o caminho genérico.
- Material novo na biblioteca de cores: **Couro**.
- Prévia para a IA (`ui/mesh_render.py`): cada vista é desenhada com memória de
  profundidade; a ordem aproximada da prévia do editor punha peças de trás na frente.
- Corte de malha: a seção sai como contorno, sem hachura (como os objetos).
- Teste de ponta a ponta (Claude Code 2.1.322, pelo painel, sem janela): "poltrona baixa
  e larga, estrutura de madeira torneada, percintas de couro e almofadão de couro mole
  que cai sobre os braços, 100 × 90 × 75 cm, assento a 38 cm". Em 119 s e 6 chamadas:
  forma livre de 26 formas, corrigida uma vez depois de olhar a prévia (a altura tinha
  ficado em 72,5 cm), caixa final de 1,00 × 0,90 × 0,75 m. A IA explicou por que
  escolheu forma livre e listou as medidas pedidas e as supostas.

## 12. Pontos de revisão
(a) limite de 20 000 triângulos; (b) converter só objetos e formas livres; (c) fora das
operações de sólidos; (d) uma malha por cópia; (e) planta pela silhueta inteira, sem
cortar na altura do plano; (f) a peça importada entra no meio da planta, sem clique para
posicionar.
