# Complemento: exportar DWG, operações de sólidos e perfil complexo

> Pedido do revisor em 2026‑10‑29: "Exportar DWG, operação de elementos sólidos, perfil
> complexo… estude como é feito nos outros softwares". Só fontes públicas (ajuda oficial,
> fóruns, documentação de padrões e de software livre). Achados "via resultado de busca"
> vêm do resumo da página no buscador; abrir a página oficial ao fechar a spec.
> Complementa `archicad_modelagem.md` (SEO e perfis), `revit_modelagem_familias.md`
> (frisos) e a lacuna de DWG de `archicad_documentacao_colaboracao.md` §4.

## 1. Exportar DWG/DXF

### Achados citados
- **Archicad, tradutores DXF/DWG:** as camadas do arquivo podem vir das camadas do
  Archicad ou dos números de pena; pena → cor do AutoCAD pela cor mais próxima ou por uma
  tabela de conversão; a espessura das penas **não** vai no DWG (sugere-se pôr espessura
  por camada ou por cor; opção de pôr tudo BYLAYER). Prancha: "Salvar layout em" espaço do
  papel com os desenhos como blocos (o espaço do modelo fica vazio), espaço do modelo com
  viewport no papel, ou desenhos em XREF ligados. — [Save Options (DXF/DWG Translation
  Setup) AC29](https://help.graphisoft.com/AC/29/INT/_AC29_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-92.htm);
  [AC26](https://help.graphisoft.com/AC/26/INT/_AC26_Help/140_UserInterfaceDialogBoxes/140_UserInterfaceDialogBoxes-83.htm);
  [DXF-DWG Translator (comunidade)](https://community.graphisoft.com/t5/Data-Exchange-articles/DXF-DWG-Translator/ta-p/303454) (via resultado de busca)
- **Archicad, queixa:** XREF no espaço do papel mudando espessura e tipo de linha (certo
  no espaço do modelo). — [DWG export problem](https://community.graphisoft.com/t5/Collaborate-forum/DWG-export-problem/td-p/330433) (via resultado de busca)
- **Revit:** a configuração de exportação mapeia **categoria → camada**; "propriedades da
  categoria BYLAYER e sobrescritas BYENTITY" ou tudo BYLAYER com camadas novas para as
  sobrescritas. Vistas e vínculos nas folhas podem sair como **referências externas**
  (desligado: carimbo e modelo no mesmo arquivo). Coordenadas internas ou compartilhadas
  (estas não valem para folhas). Exporta a vista/folha atual ou um conjunto escolhido. —
  [General Options for DWG/DXF Export (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-A170C41E-7C8A-4D7D-A552-FBFB4BD604A0.htm);
  [Export to DWG or DXF (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-42C75024-4D71-4831-8910-2747168624A3.htm);
  [Layer Mapping (2014)](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-E0B73981-9496-43CD-A358-581FEF3A3008.htm) (via resultado de busca)
- **Escrever DWG em software livre:** o GNU LibreDWG (GPL‑3) grava DWG **só até R2000**;
  R2004+ está num ramo de desenvolvimento incompleto. Lê e grava DXF r13+. —
  [Manual do LibreDWG](https://www.gnu.org/software/libredwg/manual/LibreDWG.html);
  [OSArch wiki: Drawing (DWG)](https://wiki.osarch.org/drawing-dwg/) (via resultado de busca)
- **ODA File Converter:** grátis para baixar, mas a ODA diz que não distribui o programa
  (é exemplo do SDK); a redistribuição não está clara. O ezdxf só o usa se o usuário o
  instalar à parte. — [ODA: Viewer e File Converter](https://www.opendesign.com/node/3218);
  [ezdxf: ODA File Converter Support](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html) (via resultado de busca)
- **Bonsai/IfcOpenShell:** não há DWG nativo; o caminho usado é SVG → DXF (ezdxf) ou um
  exportador DXF experimental. — [OSArch: 2D drawings in dwg from IFC](https://community.osarch.org/discussion/1450/) (via resultado de busca)
- **Teste próprio (2026‑10‑29):** DXF R2000 gerado pelo ezdxf → `dxf2dwg.exe` do pacote
  oficial LibreDWG 0.14 win64 (o mesmo que o BrasBim já baixa, mesmo SHA‑256) → DWG
  AC1015; relido pelo `dwg2dxf`, voltaram camada, polilinha, hachura, texto e arco, com
  avisos (handles da hachura, MLEADERSTYLE). **Falta abrir num CAD comercial.**
- Já na pesquisa: prefeituras pedem PDF e às vezes DWF; não há regra oficial que exija DWG
  (`autocad.md`).

### Inferências
- Caminho do BrasBim: o desenho 2D que já existe (o mesmo da tela e do PDF; o
  `_DxfPainter` da exportação da área, spec/ui 38 §5) → DXF pelo ezdxf → DWG R2000 pelo
  `dxf2dwg` como programa separado (como o `dwg2dxf` hoje). R2000 abre em qualquer
  AutoCAD.
- Camadas: as **camadas do BrasBim** (como o Archicad), não categorias. Diferente do
  Archicad, a espessura da pena **vai** no DWG (lineweight por objeto), que é o que quem
  recebe espera.
- Prancha: começar pelo espaço do papel em mm com os desenhos como blocos (o modo mais
  simples e que imprime certo); viewport e XREF depois, testando num CAD.

## 2. Operações de sólidos

### Achados citados
- **Archicad (SEO):** alvo (modificado) e operador (não muda); **associativo**; tipos:
  subtração, subtração com extrusão para cima, para baixo, interseção e adição; a extrusão
  para cima deixa o operador cortar o topo do alvo sem envolvê-lo (cobertura aparando
  parede, laje abrindo terreno). Falhas comuns: prioridade de interseção e grupos de
  interseção de camada. Apagar o operador desfaz o resultado; o conselho é escondê-lo por
  camada. — [Solid Element Operations AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-326.htm);
  [Solid Element Operations in Archicad (comunidade)](https://community.graphisoft.com/t5/Design-articles/Solid-Element-Operations-in-Archicad/ta-p/303423) (via resultado de busca)
- **Revit:** "Cortar geometria" escolhe quem corta quem, independe da ordem de criação, e
  corta com vazios e também com sólidos de massas e famílias; "Unir geometria" funde faces e
  limpa arestas **sem tirar material**. Modelos no local cortam famílias de sistema
  (paredes, pisos, forros), não famílias carregáveis (pilares, vigas). Vazio que não
  cruza o sólido não corta. — [Cut Geometry (2018)](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-Model/files/GUID-7C940A08-1F62-465F-89BF-3800E3446FC3.htm);
  fórum Autodesk, "cut beam from ceiling/floor" e "unable to cut family instances with
  in place voids" (via resultado de busca)
- Já na pesquisa: os booleanos do Morph do Archicad **não** são associativos; um laje
  inclinada se faz subtraindo com a cobertura; forro como operador que tira o reboco acima
  (`archicad_modelagem.md`, `quantitativos_orcamento_sustentabilidade.md`).
- **IFC 4.3 (texto do esquema, lido no IfcOpenShell `util.doc`):**
  `IfcRelInterferesElements` é 1 a 1; `ImpliedOrder` diz se o `RelatingElement` é a
  origem e o `RelatedElement` o alvo; o `RelatingElement` "pode ser o elemento do qual a
  geometria de interferência deve ser subtraída", o `RelatedElement` "do qual não deve".
  `InterferenceType` é um identificador livre da natureza da interferência. 
  `IfcBooleanClippingResult` restringe operandos e operador do `IfcBooleanResult`.
  `IfcRelVoidsElement` liga 1 a 1 um elemento a um `IfcOpeningElement` e implica
  subtração; a representação "Body" não desconta os vazios. —
  [IfcRelInterferesElements 4.3](https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcRelInterferesElements.htm);
  [IfcRelVoidsElement 4.3](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcRelVoidsElement.htm);
  [Element Voiding 4.3](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/concepts/Object_Composition/Element_Voiding/content.html)
  (as páginas recusaram leitura automática; texto conferido no esquema)

### Inferências
- O IFC já tem a relação associativa: `IfcRelInterferesElements` (Relating = alvo,
  Related = operador, `ImpliedOrder` verdadeiro, `InterferenceType` = o tipo da operação).
  O resultado vai também na geometria do alvo (`IfcBooleanResult`/`IfcBooleanClippingResult`),
  para quem lê o IFC ver a forma certa sem entender a relação. Associativo de verdade, como
  o Archicad, e sem a armadilha do Morph.
- O recorte por cobertura que já existe entre pilar/viga/laje/parede (`structure/cuts.py`,
  semiespaços) é o mesmo mecanismo; a "subtração com extrusão para cima" por planos da
  cobertura cabe nele.
- Diferente do Archicad, apagar o operador desfaz a operação **com aviso** e a seleção
  mostra o alvo afetado (a queixa é perder o resultado sem perceber).

## 3. Perfil complexo

### Achados citados
- **Archicad:** perfis no gerenciador de perfis; servem a paredes, pilares, vigas,
  guarda‑corpos e alguns objetos; componentes desenhados com hachuras, cada um com material
  e papel núcleo/acabamento/outro; modificadores de **estiramento** horizontal e vertical
  opcionais (sem eles a seção não muda de tamanho no elemento; linhas de estiramento marcam
  a faixa que cresce); desde o AC22, **modificadores de deslocamento** com nome, que mudam
  a largura de camadas e aparecem na ficha do elemento. Limitações relatadas: poucos
  modificadores, só em arestas. Parede de perfil complexo não tem método trapézio/polígono;
  porta e janela nela têm um "plano da janela". —
  [Profile Manager AC25](https://help.graphisoft.com/AC/25/INT/_AC25_Help/040_ElementsVB/040_ElementsVB-58.htm);
  [Stretch Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm);
  [Parametric Profiles: Wall with offsetable skins](https://community.graphisoft.com/t5/Modeling/Parametric-Profiles-Wall-with-offsetable-skins/ta-p/303787);
  [complex profile and stretch modifiers](https://community.graphisoft.com/t5/Modeling/complex-profile-and-stretch-modifiers/m-p/333958) (via resultado de busca)
- **Revit:** famílias de perfil (laço fechado, uso declarado: friso de parede, rebaixo,
  genérico); frisos e rebaixos no tipo da parede com distância da base/topo, lado,
  deslocamento e se cortam a parede; vigas carregáveis são varreduras de um perfil. —
  [Use Profile Families (2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-Customize/files/GUID-62C3B203-3B8E-4798-8CF0-CC166F9BEBFA.htm);
  [Change the Wall Sweep Profile (2018)](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-Model/files/GUID-91B5D384-3494-41C0-B2A8-E24D0ACF830A.htm);
  [Create a Sweep (2023)](https://help.autodesk.com/cloudhelp/2023/ENU/RevitLT-Customize/files/GUID-E1A36DCB-C629-44BE-9400-2D02D13CF7F4.htm) (via resultado de busca)
- **IFC 4.3:** `IfcArbitraryClosedProfileDef` (contorno fechado) e
  `IfcArbitraryProfileDefWithVoids` (com furos, tipo AREA); `IfcCompositeProfileDef`
  junta ≥ 2 perfis do mesmo tipo, sem posição própria e sem recursão;
  `IfcMaterialProfileSet` com `IfcRelAssociatesMaterial` associa seção e material a
  vigas, pilares e afins, e o perfil do material tem de bater com a forma do elemento. —
  [IfcProfileDef](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcProfileDef.htm);
  [IfcCompositeProfileDef](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCompositeProfileDef.htm);
  [IfcArbitraryProfileDefWithVoids](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcArbitraryProfileDefWithVoids.htm) (via resultado de busca)

### Inferências
- Perfil complexo = `IfcMaterialProfileSet` em que cada componente é um
  `IfcMaterialProfile` (perfil fechado + material + categoria núcleo/acabamento); a forma
  é a varredura do conjunto (`IfcCompositeProfileDef`). Viga e pilar já usam
  `IfcMaterialProfileSetUsage` no BrasBim.
- Parede: a varredura vai ao longo do eixo (reta: `IfcExtrudedAreaSolid` deitado; curva:
  varredura por diretriz). **A confirmar:** se o IFC 4.3 lista "Material Profile Set
  Usage" entre os usos de material da `IfcWall` (a página não abriu); senão, o conjunto vai
  no tipo e a parede leva só a forma.
- Estiramento: o perfil-base fica com nome no projeto (atributo compartilhado, como no
  Archicad); cada elemento guarda a seção resolvida (largura e altura nominais); o IFC
  `IfcDerivedProfileDef` só faz transformação afim, não serve para estirar por faixas.

### Rodada 2 (2026‑10‑30): perfil em vários contextos
Pedido do revisor: "perfil complexo é fazer uma seção e poder aplicar em vários
contextos, laje, pilar, viga…; estude a ferramenta do Archicad". Páginas oficiais abertas
(AC18, AC24, AC28); fórum só pelo resumo do buscador ("conferir").
- **Onde se aplica:** parede, pilar, viga, peças de guarda‑corpo e objetos de biblioteca
  que tenham a opção de perfil (ex.: componentes de pele de vidro e escada). Cada perfil
  marca para quais ferramentas serve, e a lista de cada ferramenta só mostra esses. **Laje e
  cobertura não aparecem** em nenhuma página. —
  [Apply Profile to Element AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/040_ElementsVB/040_ElementsVB-56.htm);
  [Profile Manager Dialog Box AC21](https://help.graphisoft.com/AC/21/INT/AC21Help/Appendix_Settings/Appendix_Settings-67.htm) (via resultado de busca)
- **Forma:** a seção é extrudada perpendicular ao plano do desenho; o perfil salvo é um
  atributo compartilhado da ferramenta, e também se pode aplicar um perfil só a um
  elemento sem salvá‑lo. —
  [About Complex Profile Elements AC18](https://help.graphisoft.com/AC/18/INT/AC18Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-35.htm)
- **Origem:** na parede, a origem do editor é a linha de referência; na viga e no pilar, o
  eixo. O pilar de perfil perde a escolha dos 9 pontos de inserção (a âncora é a origem).
  Na viga de perfil, a altura se refere ao centro do perfil. — Profile Manager AC22,
  Column/Beam Tool Settings AC18/AC20 (via resultado de busca)
- **Esticar:** chaves de largura e altura; linhas de esticar marcam o que muda; por padrão
  coincidem com largura e altura nominais; arrastar no modelo estica. Só parede, viga e
  pilar. —
  [Stretch Modifiers AC28](https://help.graphisoft.com/AC/28/INT/_AC28_Help/025_Attributes/025_Attributes-63.htm)
- **Deslocamentos nomeados:** cotas que movem arestas por elemento (ancoradas em nó da
  hachura, ponto fixo ou duas arestas), editáveis na ficha e graficamente em planta, corte e
  3D, e que entram em etiquetas e tabelas. Só parede, viga e pilar. Fórum: arestas das
  duas faces de uma camada têm de estar na mesma cota para a camada acompanhar. —
  [Offset Modifiers AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-65.htm);
  [Create New Offset Modifier AC24](https://help.graphisoft.com/AC/24/INT/_AC24_Help/040_ElementsVB/040_ElementsVB-66.htm)
- **Vãos em parede de perfil:** uma "linha de referência do vão" no perfil diz onde portas
  e janelas assentam; sem ela, o vão usa a caixa envolvente do perfil. Reclamação
  recorrente: janela em posição diferente na planta e no 3D quando as camadas têm alturas
  diferentes (conferir). — fórum Graphisoft, "Window appears offset from Complex Profile
  wall", "Complex profile Opening Reference Line problem" (via resultado de busca)
- **O que falta lá (pedido antigo):** perfil em borda de laje e de cobertura (testeira,
  rufo, pingadeira, borda espessada do radier). Contornos: viga de perfil ao longo da
  borda (girada ou inclinada) + recorte por sólidos, ou laje grossa recortada (conferir). —
  fórum Graphisoft, "Applying complex profile to slab?", "roof edge/slab edge" (Wishes),
  "Residential: Fascia Trim Modeling" (via resultado de busca)
- **Para o BrasBim:** perfil como atributo do projeto com "serve para"; contextos parede,
  viga, pilar, guarda‑corpo **e** borda de laje/cobertura e caminho livre, que atendem o
  pedido antigo; linha de referência do vão no perfil (decide o ponto (i) junto). Vira a
  spec/ui 41 §4.1.

## Lacunas
- Abrir o DWG R2000 do LibreDWG num CAD comercial e num visualizador grátis.
- Uso de material da `IfcWall` em 4.3 (página oficial) e o que outros leitores IFC fazem
  com `IfcRelInterferesElements` (provavelmente ignoram; daí a forma já recortada).
- AutoCAD (SUBTRACT/UNION/INTERSECT em sólidos 3D) não foi pesquisado nesta rodada.
