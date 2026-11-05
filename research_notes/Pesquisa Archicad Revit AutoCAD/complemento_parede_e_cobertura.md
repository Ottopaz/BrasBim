# Complemento: parede (e pilar) recortada pela cobertura (2026‑11‑05)

Item M2 da revisão geral (`reports/Revisao geral antes do instalador (2026-10-30).md`):
"recortar parede pela cobertura (oitão, parede sob telhado)", RF‑ELE‑17. Só fontes
públicas (ajuda oficial da Graphisoft e da Autodesk). Descreve **funções**; nomes de
comandos, textos e layout de diálogo não são copiados.

## 1. Archicad: recorte associativo pela cobertura ou casca
- O elemento que recorta é **sempre uma cobertura ou uma casca**; ele recorta qualquer
  elemento do modelo (parede, viga, pilar). Os elementos continuam separados, só que
  recortados um pelo outro. — [Trim Elements to Roof or Shell AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-90.htm)
- **Associativo:** mudar a inclinação da cobertura muda a parede recortada. Para mudar
  a relação, basta refazer o recorte. — mesma fonte.
- Coberturas recortadas entre si **agem como um corpo só** ao recortar outros
  elementos (ex.: duas coberturas que se encontram recortam a parede como uma). — mesma
  fonte; [Automatic Trim AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-92.htm)
- **Corpo de recorte** (a forma com que a cobertura corta, infinita para cima ou para
  baixo; só aparece no 3D se ligado): o padrão da cobertura é "das linhas de pivô para
  baixo"; outras escolhas: do contorno para baixo, extrusão para baixo, extrusão para
  cima; a casca tem ainda um corpo editável. — [Define Trimming Bodies AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-91.htm)
- **Automático** (vários elementos selecionados com as coberturas): o que fica fora da
  estrutura da cobertura é retirado, sem mais perguntas. **Manual:** escolhe‑se a
  cobertura e depois **a parte que fica** (destacada) ou a que sai. — Automatic Trim;
  [Manual Trim AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-95.htm)
- **Ver e desfazer:** o elemento selecionado mostra um ícone de ligações; passar o
  mouse destaca os ligados, clicar lista as ligações, cada uma com um botão de tirar; há
  também "tirar todas as ligações" no botão direito. Ligações em cadeia (parede presa à
  cobertura A, que está presa à B) recortam pela B também. — [Managing Element
  Connections AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-98.htm)
- **O comando antigo** (só cobertura de um plano) **não é associativo**: grava a forma
  recortada na parede, que fica estática mesmo se a cobertura sumir; recorta o topo ou a
  base; uma opção ajusta a altura da parede ao ponto mais alto recortado; parede
  atravessada pela cobertura é dividida em duas. Desfaz‑se com um "desfazer todos os
  recortes" próprio. — [Crop to Single-plane Roof AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-88.htm)
- **Problema conhecido:** parede inclinada recortada pela cobertura dá resultado
  inesperado; o contorno sugerido é usar casca. — [Trim Slanted Walls to Roof (base de
  conhecimento)](https://helpcenter.graphisoft.com/knowledgebase/25931/)

## 2. Revit: prender topo ou base da parede
- Depois de posta, a parede pode ter o **topo ou a base presos** a outro elemento no
  mesmo plano vertical: piso, cobertura, forro, plano de referência ou outra parede logo
  acima/abaixo. A altura **aumenta ou diminui** para chegar ao limite, e o contorno da
  parede acompanha quando o projeto muda (ex.: a inclinação). — [Attach Walls to Other
  Elements](https://help.autodesk.com/cloudhelp/2016/ENU/Revit-Model/files/GUID-ED60CE62-B955-45E9-9D7D-00F1552D858C.htm)
- Uso: selecionar as paredes, o comando, escolher topo ou base na barra de opções e
  clicar os alvos. Soltar: o comando inverso, alvo por alvo ou "soltar de todos". Não há
  outras opções (sem afastamento). — mesma fonte.
- **Fórum (via busca, não aberto):** o alvo tem de **cobrir a parede inteira** visto de
  cima, senão o comando falha; se o topo da parede está acima da cobertura, o programa
  pode prender a base em vez do topo; para tirar, a parede volta à altura de antes. —
  [Fórum Autodesk: wall attachment top to roof](https://forums.autodesk.com/t5/revit-architecture-forum/wall-attachment-top-to-roof/m-p/12333763);
  [is there a way to attach the base of a wall to a roof?](https://forums.autodesk.com/t5/revit-architecture-forum/is-there-a-way-to-attach-the-base-of-a-wall-to-a-roof/td-p/9522434)

## 3. O que o BrasBim já tem
- **Operações de sólidos** (spec/ui 41 §3): parede, pilar, viga e laje como alvo; a
  cobertura (as águas dela) como operador; "subtrair para cima" tira o operador e tudo
  acima dele, com `IfcRelInterferesElements` `SUBTRACT_UP` e semiespaços pelas faces de
  baixo do operador, limitados pela projeção delas em planta. Associativo.
- **Topo inclinado da parede** (spec/ui 08): perfil de topo à mão, por trechos.
- A cobertura sabe a **cota da face de baixo em cada ponto** (a mais baixa das águas,
  `roofs`), o que dá a altura que a parede precisa ter.

O que falta para "toda casa com telhado aparente": a parede **subir** até o telhado (o
oitão), sem o usuário calcular a altura do ponto mais alto, e continuar presa quando a
cobertura muda de inclinação, de cota ou de contorno.

## 4. O que levar para o BrasBim (vai para a spec/ui 45)
1. **Topo "na cobertura"** como um terceiro modo de topo da parede (além de pavimento e
   altura fixa), e também do pilar: a altura sai sozinha (o ponto mais alto da face de
   baixo da cobertura sobre a parede), e o que passa da cobertura é recortado. Junta o
   "sobe ou desce" do Revit com o recorte exato do Archicad.
2. **Associativo** pela relação de sólido que já existe (`SUBTRACT_UP`), sem gravar
   forma estática (o comando antigo do Archicad é o que os usuários evitam).
3. **Sem exigir que a cobertura cubra a parede inteira** (a falha mais citada no fórum
   do Revit): onde não há cobertura em cima, vale uma altura de reserva (ponto (b)).
4. **Várias coberturas** sobre a mesma parede recortam juntas (como o corpo único do
   Archicad), e a parede sobe até a mais alta.
5. **Prender várias de uma vez:** selecionar paredes e pilares e clicar a cobertura; e,
   ao criar uma cobertura, oferecer prender as paredes de baixo (ponto (c)).
6. **Soltar** volta ao modo e à altura de antes (guardados), como o Revit.
7. **Ver as ligações** na ficha, como já existe para os sólidos ("Recortado por").
8. Parede inclinada (tombada) e parede de perfil ficam fora na primeira entrega, com
   recusa e mensagem (o próprio Archicad tem problema com a inclinada).

## 5. Lacunas
- Não se achou, nas ajudas, como a parede recortada aparece na planta e nos
  quantitativos (área de face, volume) nos dois programas.
- Os tópicos do fórum do Revit não foram abertos (só o resumo da busca).
