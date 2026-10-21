# Terreno, topografia e implantação: Archicad, Revit, AutoCAD/Civil 3D (estado em 2026)

Notas de pesquisa feitas só com fontes públicas na web (regra clean-room). Todas as fontes foram acessadas em **2026-10-21**. O texto resume com palavras próprias; não há transcrição de manuais. Nenhum material local de `_restrito/` ou `tools/` foi consultado.

Limitações da sessão: várias páginas retornaram HTTP 403 (buildingSMART, Arkance, Comunidade Graphisoft), e a cota de buscas da sessão acabou antes das buscas sobre exigências das prefeituras e sobre as entidades de terraplenagem do IFC 4.3. Esses pontos estão marcados em **Lacunas**.

---

## 1. Archicad: ferramenta Malha (Mesh), levantamento, SEO, reclamações

### Conclusão
No Archicad o terreno é uma **Malha** (polígono com pontos de cota e "cristas"/linhas de quebra), feita a partir de um DWG de curvas (varinha mágica sobre cada curva) ou de um arquivo XYZ. O recorte do terreno pelo edifício é feito com **Operações de Elementos Sólidos (SEO)**. Os pontos fracos são a falta de corte/aterro nativo confiável (o volume muda conforme a triangulação), a malha que não aparece cortada em planta e a necessidade de add-ons (p.ex. Architerra) para platôs e muros de arrimo.

### Achados com fonte
- **Três modos de ajuste ao inserir pontos novos numa malha existente.** (1) *Ajustar às cristas do usuário*: o ponto novo cai na superfície atual, só as cristas definidas pelo usuário mantêm a cota, e a triangulação interna é refeita. (2) *Ajustar a todas as cristas*: todas as cristas mantêm a cota e a triangulação não muda; é o modo mais preciso, mas pode gerar muitas cristas. (3) *Sem ajuste*: o ponto recebe a cota definida nas configurações da malha, e as cristas do usuário cruzadas mantêm a cota. Retirado da ajuda do AC21, "Add New Points to the Mesh". — [Graphisoft Help AC21](https://help.graphisoft.com/AC/21/INT/AC21Help/03_1_Elements_Virtual_Building/03_1_Elements_Virtual_Building-110.htm)
- **Para inserir um único ponto numa crista** (conselho de moderador): selecionar a malha, ativar a ferramenta Malha com método poligonal, dar duplo clique no local e escolher "ajustar às cristas do usuário". Um usuário relatou que isso não funcionava em versões antigas. — [Graphisoft Community: Adding a single point to mesh](https://community.graphisoft.com/t5/Modeling/Adding-a-single-point-to-mesh/m-p/589981)
- **Curvas do topógrafo → malha:** desenhar o contorno externo com a ferramenta Malha e depois usar a varinha mágica sobre cada curva de nível para acrescentar pontos, digitando a cota Z de cada uma. As cristas do usuário podem ser ocultadas em planta pela opção de seleção de cristas (aba Planta e Corte → Contornos). — [Graphisoft Help Center (p=86593)](https://helpcenter.graphisoft.com/?p=86593)
- **Em pt-BR, Comunidade Graphisoft Brasil:** um artigo de instrutor certificado ensina a explodir o DWG do levantamento para usar as curvas como base da malha ("Modele terrenos usando cotas reais de topografia"; só o resumo da busca foi lido, porque a página deu 403). — [Comunidade Graphisoft – Modelagem](https://community.graphisoft.com/t5/Modelagem/Modele-terrenos-usando-cotas-reais-de-topografia/ta-p/399099)
- **Acrescentar uma curva a uma malha existente:** selecionar a malha, ativar a ferramenta e usar a varinha mágica sobre a curva, o que acrescenta só a curva em vez de criar uma malha nova. — [Comunidade Graphisoft – Seleção de curvas de nível](https://community.graphisoft.com/t5/Modelagem/Sele%C3%A7%C3%A3o-de-curvas-de-n%C3%ADvel/m-p/605431)
- **Importação de pontos XYZ:** o menu Arquivo > Interoperabilidade > "Place Mesh from Surveyors Data" (em versões antigas ficava no menu Design) lê .txt/.xyz com linhas de três números e ID opcional. Aceita ponto e vírgula ou espaço como separador; linhas não numéricas viram comentário. No diálogo se escolhem a unidade, a posição (clique ou zero do arquivo) e a cota do Zero do Projeto acima do nível do mar. — [Archicad 28 Help: Other Formats Opened by Archicad](https://help.graphisoft.com/AC/28/INT/_AC28_Help/120_Interoperability/120_Interoperability-7.htm); [Graphisoft Support: How to import a TXT file](https://support.graphisoft.com/hc/en-us/articles/23273448569361-How-to-import-a-TXT-file)
- **Boa prática citada por especialista do fórum:** uma única malha para o relevo, com lajes para os revestimentos (caminhos, vias, grama, brita). As lajes acompanham a malha via SEO, e as curvas dentro da faixa da via são apagadas e redesenhadas nas bordas. — [Graphisoft Community: Terrain road issue](https://community.graphisoft.com/t5/Modeling/Terrain-road-issue/td-p/378056)
- **Malha nunca aparece cortada em planta**: para ver um corte real é preciso um Documento 3D. Para malhas de pavimento que somem no corte, usa-se o SEO para remover a parte inferior, ou lajes/coberturas no lugar (thread de 2025, AC28). — [Graphisoft Community: Plan section not cutting terrain](https://community.graphisoft.com/t5/Documentation/Plan-section-not-cutting-terrain/td-p/648791/highlight/true)
- **Corte e aterro, reclamações:** o volume da malha muda quando se acrescentam pontos sobre as curvas existentes (sem mudar o relevo) ou uma linha de talvegue, porque o Archicad triangula ligando todos os pontos e a triangulação altera o volume. Um teste simples deu volumes diferentes para a mesma geometria. Contornos citados pelos usuários: medir a malha existente, alterar as curvas para o projeto e medir de novo; o volume aparece na paleta de informação e nas tabelas (que consideram o SEO). Também há pedido de cálculo nativo de corte/aterro, e o SEO às vezes não corta a maior parte do terreno até que a malha seja dividida. — [Graphisoft Community: Mesh volume calculation accuracy](https://community.graphisoft.com/t5/Modeling/Mesh-volume-calculation-accuracy/td-p/187154); [Can I calculate cut/fill with mesh tool](https://community.graphisoft.com/t5/Collaboration-with-other/Can-I-calculate-cut-fill-with-mesh-tool/m-p/179286); [Measure Cut and Fill volume in 3D model](https://community.graphisoft.com/t5/Modeling/Measure-Cut-and-Fill-volume-in-3D-model/td-p/202841)
- **Integração com Grasshopper:** um usuário (2024) relatou que o plug-in aceitava só pontos, sem cristas nem curvas, e por isso não vinham curvas para a planta. — [Graphisoft Community: Rhino plug-in for mesh limitation](https://community.graphisoft.com/t5/Parametric-design/Rhino-plug-in-for-mesh-limitation/td-p/600656/highlight/true)
- **Add-on Architerra** (curso da Nordic BIM): modelagem do terreno com **platôs e muros de arrimo**, sinal de que essas operações não são fortes no produto nativo. — [Nordic BIM – Architerra Fundamentals](https://www.nordicbim.com/en/training/architerra-fundamentals)
- **Artigo da Graphisoft sobre como gerar curvas de nível de malhas sem cristas** (só a introdução foi lida). — [Graphisoft Community: Creating Contour Lines of Meshes without Ridges](https://community.graphisoft.com/t5/Design-articles/Creating-Contour-Lines-of-Meshes-without-Ridges/ta-p/336860)

### Inferências
- O fluxo DWG → malha via varinha mágica, curva a curva, é trabalhoso. O BrasBim já faz "terreno por curvas pegas do DWG", que é o equivalente direto. O diferencial possível é selecionar todas as curvas de uma camada de uma vez e ler a cota da elevação da polilinha ou de um texto próximo.
- Dar ao usuário controle das **linhas de quebra/cristas** é essencial: o problema de volume do Archicad nasce de triangulação sem restrições. Usar uma triangulação de Delaunay com restrições (curvas e linhas de quebra como arestas obrigatórias) reduz o problema.
- Separar o "relevo" (uma superfície) dos "revestimentos" (elementos finos que se ajustam ao relevo) é um padrão consolidado, e a recomendação do fórum mostra que funciona bem.

### Lacunas
- Não confirmei se o Archicad 28 ou 29 (2025/2026) trouxe uma ferramenta nova de terreno/implantação. A busca não retornou notas de versão sobre isso.
- Não consegui ler o artigo pt-BR completo (403) nem tutoriais de platô e talude nativos no Archicad.

---

## 2. Revit: Toposólido (2024+) e superfície topográfica legada

### Conclusão
O Revit 2024 trocou a superfície topográfica (Toposurface) pelo **Toposólido** (sólido com espessura e camadas). Ele é criado por esboço, por importação de CAD/CSV ou, a partir do 2025, por face de massa. Trouxe **Subdividir** (no lugar de Sub-região), **Escavar** (no lugar do Platô de edificação, ou building pad, removido no 2024) e **Região graduada**, que trabalha por fases. O volume escavado aparece nas propriedades. As principais reclamações são a falta de linhas de quebra, a edição de pontos lenta, as linhas de dobra visíveis na edição, a aparência facetada (atenuada no 2025 pelo sombreamento suave) e as fases das subdivisões/escavações.

### Achados com fonte
- **Criar a partir de importação:** Toposólido > Criar a partir de importação > a partir de CAD (escolhendo o DWG vinculado e as camadas com dados 3D, como curvas) ou a partir de arquivo de pontos (CSV). O mesmo guia observa que o Revit **não tem linhas de quebra**, o que dificulta controlar a forma. — [Arkance UK (anexo PDF, resumo de busca)](https://ukcommunity.arkance.world/hc/en-us/article_attachments/21570315565074)
- **Subdividir** substituiu Sub-região no 2024: desenha-se um contorno sobre o toposólido e definem-se material e espessura; a subdivisão pode ter deslocamento em relação ao toposólido pai. — [BIMPure: Revit 2024](https://bimpure.com/blog/revit-2024)
- **Região graduada (ajuda do Revit LT 2026):** duas opções, copiar o toposólido exatamente ou criar um novo só com os pontos do perímetro. O original é marcado como demolido na fase atual e a cópia como nova nessa fase. O Revit pode relatar corte e aterro do terreno para estimar custos. Muitos pontos deixam o software lento; é possível simplificar e depois conferir as curvas. — [Autodesk Help: Create a Graded Region (Revit LT 2026)](https://help.autodesk.com/cloudhelp/2026/ENU/RevitLT-Model/files/GUID-31E2EF0E-875C-4A68-958E-A06E5F2C0838.htm)
- **Reclamação sobre fases:** a região graduada também demole as subdivisões e escavações associadas, e as escavações não respeitam fases como portas e janelas respeitam paredes. — [Autodesk Revit Ideas (fases em sub-elementos)](https://forums.autodesk.com/t5/revit-ideas/different-phasing-workset-amp-design-option-settings-for/idc-p/12270608/highlight/true)
- **Novidades do Revit 2025:** *Escavar* remove o toposólido acima de um piso, cobertura, platô ou outro toposólido, mas não preenche embaixo do piso, então é preciso editar manualmente. *Toposólido por face* de massa. *Snap XYZ*, que encaixa em outras geometrias como linhas de um TIN do CAD. *Sombreamento suave*, para apresentações. Nós de Dynamo para toposólido (no 2024 era preciso criar uma toposurface e converter). O artigo chama o toposólido do 2024 de "infame" por ter perdido o building pad. — [CAD Notes: Revit 2025 toposolid enhancements](https://www.cad-notes.com/revit-2025-toposolid-enhancements/)
- **Volume:** a ajuda em vídeo de 2026 diz que as propriedades do toposólido mostram o volume escavado total, com detalhamento por escavação, e recomenda o sombreamento suave porque o terreno graduado fica facetado. — [Autodesk Help: Video Working with Toposolids (2026)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Model/files/GUID-5633F482-820E-471B-8E22-238F7D6264C0.htm)
- **Limitações do sombreamento suave:** os padrões de superfície não aparecem e não é possível pintar ou sobrescrever materiais. — [Arkance EMEA: Revit 2025 Improved Toposolid Functionality](https://emea.support.arkance.world/hc/cs/articles/36471259538578-Revit-2025-Improved-Toposolid-Functionality)
- **Reclamações de edição:** editar pontos ficou muito mais lento que na toposurface (o Revit retriangula em tempo real). Na edição aparecem "linhas de dobra" que capturam o snap, e as curvas só aparecem ao sair do modo de edição. As curvas podem cruzar de forma estranha; um contorno usado é deslocar pontos em ±0,1. — [Autodesk Revit Ideas: Graphics & method for modifying toposolid](https://forums.autodesk.com/t5/revit-ideas/graphics-amp-method-for-modifying-toposolid/idc-p/12880176/highlight/true)
- **Corte/aterro no primeiro build do 2024** não funcionou para um usuário (relato possivelmente desatualizado). — [Autodesk Forum: Cut and Fill: No Response](https://forums.autodesk.com/t5/revit-architecture-forum/cut-and-fill-no-response/m-p/12316286)
- **Interop com Civil 3D:** o Revit não lê superfícies do Civil diretamente. As opções são exportar para AutoCAD, simplificar e vincular o DWG para criar o terreno a partir da camada, ou usar LandXML pela extensão *Roads and Terrain* / *Site Designer*. Um usuário relata que as linhas de quebra do LandXML se perdem ao importar como toposólido. — [Autodesk Forum: Civil 3D surface to Revit](https://forums.autodesk.com/t5/civil-3d-forum/civil-3d-surface-to-revit/td-p/8276233); [SOFiSTiK Forum: Terrain as Toposolid](https://forum.sofistik.de/t/terrain-as-toposolid-instead-of-generic/6139); [Aplitop TcpMDT: exporting LandXML surfaces to Revit](https://www.aplitop.com/Products/TcpMDT/v8/help/en/referencia/exporting_landxml_surfaces_to_revit.htm)

### Inferências
- A trajetória do Revit (superfície → sólido com espessura/camadas, subdivisões como elementos próprios, escavação por elementos) é um bom modelo conceitual para o BrasBim. Os erros dele mostram o que evitar: retirar o platô antes de existir um substituto, gerar curvas só fora do modo de edição e não ter linhas de quebra.
- A ligação com fases (existente × proposto) é central para corte/aterro e para a prancha da prefeitura (terreno natural × terreno projetado). O BrasBim deve guardar as duas superfícies explicitamente e calcular o volume entre elas.

### Lacunas
- Não li a ajuda oficial completa de Escavar, Subdividir e Criar a partir de importação (o artigo da Arkance deu 403).
- Não está confirmado se o Revit 2026/2027 acrescentou linhas de quebra ou platô.

---

## 3. AutoCAD / Civil 3D

### Conclusão
O Civil 3D é a referência para terreno: **superfícies TIN** montadas por camadas de dados (curvas, pontos, linhas de quebra, contornos/limites), superfícies de volume (TIN entre duas superfícies), objetos de terraplenagem (grading/feature lines) e corredores. Os arquitetos em geral **recebem** os dados do Civil como DWG simplificado ou LandXML, sem modelar no Civil.

### Achados com fonte
- **Superfície TIN:** é criada vazia e preenchida com dados de curvas, linhas de quebra e contornos. As curvas podem ser polilinhas 2D ou 3D com X, Y e Z. Os **contornos (boundaries)** são polilinhas fechadas que controlam quais triângulos aparecem; as áreas ocultas não entram no cálculo de área e volume. — [Autodesk Civil 3D 2025 Tutorial: Creating and Adding Data to a Surface](https://help.autodesk.com/cloudhelp/2025/ENU/Civil3D-Tutorials/files/GUID-899731B5-0B6A-451E-9CF2-0DCF00FA9B64.htm)
- **Comandos de superfície:** CreateSurface (TIN ou grade), AddSurfaceBreaklines, AddSurfaceBoundaries, AddSurfaceContours e CreateSurfaceComposite (volume composto entre duas superfícies). — [Autodesk Civil 3D 2026: Surfaces Command Reference](https://help.autodesk.com/cloudhelp/2026/ENU/Civil3D-UserGuide/files/GUID-DB28F66C-41F2-4171-8F9A-BB549DF3362E.htm)
- **Exportação de feature lines** de corredores junto com alinhamentos via LandXML (voltado para equipamentos de obra). — [Trimble Access: LandXML road export from Civil 3D](https://help.fieldsystems.trimble.com/trimble-access/2022.10/en/LandXMLroad-export-from-Civil3D.htm)
- **Rotas para arquitetos** (seção 2): DWG explodido/simplificado ou LandXML com superfícies EG (terreno existente) e FG (terreno acabado). — [Autodesk Forum: Civil 3D surface to Revit](https://forums.autodesk.com/t5/civil-3d-forum/civil-3d-surface-to-revit/td-p/8276233)

### Inferências
- O modelo "superfície = conjunto de fontes de dados (curvas, pontos, linhas de quebra, contorno externo, furos)", com regeneração quando uma fonte muda, é o que o BrasBim deve imitar. Isso combina com ifcopenshell (a superfície final vira um IfcTriangulatedFaceSet ou TIN) e com transações serializáveis (cada fonte é uma operação).
- Corte/aterro pelo método de superfície de volume (diferença TIN-TIN dentro de um contorno) é o padrão técnico e não sofre o problema de triangulação do Archicad, desde que as duas superfícies sejam combinadas numa malha comum.
- Importar LandXML (superfícies TIN e pontos) é uma interoperabilidade valiosa para receber dados de topógrafos e engenheiros civis no Brasil.

### Lacunas
- Não detalhei os objetos de terraplenagem (grading, feature lines, taludes por inclinação ou distância) nem corredores pela ajuda oficial; a cota de buscas acabou.
- Não pesquisei rotulagem de curvas (contour labels) no Civil 3D.

---

## 4. Georreferenciamento (SIRGAS 2000 / UTM, IFC 4.3) e formatos de levantamento

### Conclusão
No IFC 4.3 o georreferenciamento é feito com **IfcMapConversion** (escala, rotação em Z e translação para Leste, Norte e altura ortométrica) apontando para um **IfcProjectedCRS** (p.ex. "EPSG:31983", SIRGAS 2000 / UTM 23S). Archicad e Revit escrevem esses dados no IFC4, mas a leitura nos visualizadores é irregular. No Brasil o referencial é SIRGAS 2000 (EPSG:4674), com fusos UTM 18S a 25S (p.ex. 22S = 31982, 23S = 31983).

### Achados com fonte
- **IfcMapConversion** liga o sistema local de engenharia ao CRS do mapa: aplica escala nos eixos, rotação anti-horária em Z e translação por Eastings, Northings e OrthogonalHeight. O **IfcMapConversionScaled** permite fatores por eixo. — [IFC 4.3.2.0 IfcMapConversion](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcMapConversion.htm) (via resumo de busca; o fetch direto deu 403)
- **IfcProjectedCRS** identifica o CRS do mapa. Os atributos MapProjection e MapZone identificam a projeção; para 3D deve ser um CRS composto, do qual se identifiquem o datum geodésico e o vertical. — [IFC 4.3 IfcProjectedCRS](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcProjectedCRS.htm)
- **Suporte prático:** num teste da OSArch, só o BlenderBIM (hoje Bonsai) exibiu IfcProjectedCRS e IfcMapConversion. Ferramentas de federação (p.ex. BIMcollab Zoom) usam coordenadas locais. Revit, Civil 3D, 12d, Tekla e Archicad conseguem escrever as entidades. — [OSArch: Is there any other software that uses IfcProjectedCRS and IfcMapConversion?](https://community.osarch.org/discussion/1618/)
- **SIRGAS 2000 / UTM:** EPSG:31983 = UTM 23S (48°W a 42°W), CRS base EPSG:4674, substitui SIRGAS 1995. EPSG:31982 = UTM 22S (54°W a 48°W). EPSG:6210 = UTM 23N. — [spatialreference.org EPSG:31983](https://spatialreference.org/ref/epsg/31983/); [EPSG:31982](https://spatialreference.org/ref/epsg/31982/)
- **Archicad:** o objeto Ponto de Levantamento (Survey Point) define a origem global (X=Y=Z=0) do IFC, orientada pelo Norte do Projeto. Na exportação, o IfcSite pode ficar na Origem do Projeto ou no Ponto de Levantamento (para evitar grandes deslocamentos no arquivo). As preferências de georreferência ficam em Preferências do Projeto > Localização. No IFC2x3 os dados vão para ePSet_ProjectedCRS e ePSet_MapConversion. Há relato de perda de Leste/Norte na exportação. — [Graphisoft Help Center: Survey Point](https://helpcenter.graphisoft.com/?p=63066); [Central Innovation: Exporting IFC from Archicad – Location](https://centralinnovation.com/resources/exporting-ifc-from-archicad-location); [OSArch Wiki: Archicad IFC geolocation](https://wiki.osarch.org/archicad-ifc-geolocation/); [Graphisoft Community: IFC and the Survey Point Object](https://community.graphisoft.com/t5/Collaboration-with-other/IFC-and-the-Survey-Point-Object/m-p/297828)
- **Revit:** o exportador IFC (versões 19.4 / 20.2 / 21.1+) aceita coordenadas globais nativas só para IFC4. As coordenadas vão no Ponto Base do Projeto com fator de escala combinado, e na exportação se escolhem "Project Base Point" e o código EPSG, gerando um IfcMapConversion. No IFC2x3 é preciso uma toposurface exportada como IfcSite. A Autodesk desaconselha a opção "Shared Coordinates", exceto por compatibilidade; projetos em UTM distantes da origem podem distorcer e errar alturas. O Ponto Base do Projeto vira o zero no visualizador. — [OSArch Wiki: Revit IFC geolocation](https://wiki.osarch.org/revit-setup-for-openbim-revit-ifc-geolocation/); [Autodesk: How to control coordinates when exporting from Revit to IFC](https://autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-control-coordinates-when-exporting-from-Revit-to-IFC.html); [Pix4D Community](https://community.pix4d.com/t/export-ifc-from-revit-geolocation/29413); [bim-me-up: Revit, IFC and coordinate systems](https://bim-me-up.com/en/revit-ifc-and-coordinate-systems/)
- **Formatos:** XYZ/TXT de pontos (Archicad), CSV de pontos e DWG com curvas 3D (Revit), LandXML (Civil 3D → Revit e outros) e polilinhas 2D/3D com elevação (Civil 3D). Fontes nas seções 1 a 3.

### Inferências
- O BrasBim deve oferecer um diálogo de **localização do projeto** com uma lista de EPSG SIRGAS 2000 (fusos 18S a 25S e alguns N), um ponto local de referência (Leste/Norte/cota) e a rotação do Norte verdadeiro, e gravar IfcMapConversion + IfcProjectedCRS (com IfcMapConversionScaled se necessário). Ao importar um DWG em UTM, detectar coordenadas grandes e oferecer o deslocamento automático para a origem local (o problema que o Revit e o Archicad sofrem).
- Ler e escrever CSV/XYZ de pontos e LandXML são entradas baratas e de alto valor. Nuvens de pontos (LAS/E57) podem ficar como referência visual numa etapa posterior.

### Lacunas
- Não verifiquei nesta sessão a documentação IBGE (resolução que define o SIRGAS 2000 como oficial), as alturas (ortométrica × elipsoidal, modelo hgeoHNOR/MAPGEO) nem a tabela completa dos fusos.
- Não pesquisei nuvens de pontos (LAS/E57) no Archicad e no Revit (Recap), nem o fluxo de drones; a cota de buscas acabou.
- As páginas de IfcGeographicElement (PredefinedType TERRAIN), IfcEarthworksCut e IfcEarthworksFill do IFC 4.3 deram 403. Pelo conhecimento prévio, o IFC 4.3 tem essas entidades para terreno e terraplenagem, mas **não verifiquei** nesta sessão; é preciso confirmar no site da buildingSMART antes de citar na spec.

---

## 5. Prática brasileira: levantamento planialtimétrico, NBR 13133, implantação para prefeitura

### Conclusão
A NBR 13133 (execução de levantamento topográfico) é a norma de referência citada em termos de referência públicos para o levantamento planialtimétrico. Ela define equidistância de curvas, densidade de pontos por declividade e classes de nivelamento. Há conflito sobre a edição vigente (1994 × 2021). As exigências municipais de planta de situação/implantação com curvas, platôs e corte/aterro **não foram pesquisadas a fundo** (a cota de buscas acabou).

### Achados com fonte
- **A NBR 13133 é exigida** em termo de referência público (MPMG) para levantamento topográfico planialtimétrico. — [MPMG – Termo de referência (PDF)](https://transparencia.mpmg.mp.br/licitacao/arquivo/11501/download)
- **Edição da norma:** um artigo de 2023 usa a NBR 13133/2021; outro trabalho cita a de 1994. A edição vigente deve ser confirmada na ABNT. — [Unijuí – Salão do Conhecimento](https://publicacoeseventos.unijui.edu.br/index.php/salaoconhecimento/article/view/25443/24049); [Revista Brasileira de Cartografia (UFU)](https://seer.ufu.br/index.php/revistabrasileiracartografia/article/download/44407/23482/184382)
- **Escala 1:500:** um estudo relata equidistância de curvas de 1 m e densidade mínima de pontos por hectare conforme a declividade (p.ex. ≥ 45 pontos/ha acima de 20%). — [Tecnia (IFG)](https://periodicos.ifg.edu.br/tecnia/article/download/176/665/2567) (via resumo de busca; conferir no texto)
- **Classes de nivelamento IN a IVN**; a IIN vale para cotas de pontos de segurança e poligonais em projetos básicos e executivos (fonte de questão de concurso, conferir na norma). — [Qconcursos](https://www.qconcursos.com/questoes-de-concursos/questoes/c1fdb26a-86)
- **O levantamento planialtimétrico serve de base** para estimar custos da obra pelos pontos altos e baixos e pelas curvas, o que inclui corte e aterro. — [Unijuí](https://publicacoeseventos.unijui.edu.br/index.php/salaoconhecimento/article/view/25443/24049)
- **Platô e talude no Archicad** são vendidos como recursos do add-on Architerra (seção 1), sinal de demanda não atendida nativamente. — [Nordic BIM – Architerra](https://www.nordicbim.com/en/training/architerra-fundamentals)

### Inferências
- O fluxo típico brasileiro (DWG planialtimétrico do topógrafo, com curvas a cada 1 m, pontos cotados, divisas e RN, em UTM/SIRGAS 2000 → implantação com platôs, taludes e muros de arrimo → prancha de implantação/situação para a prefeitura com curvas, cotas de platô e, às vezes, quadro de corte/aterro) pede no BrasBim: (a) importar o DWG georreferenciado; (b) terreno natural por curvas/pontos com linhas de quebra; (c) **platô** (região plana com cota e talude de inclinação definida, p.ex. 1:1,5 em corte e 1:2 em aterro, valores a confirmar em norma) que gera o terreno projetado; (d) muro de arrimo como alternativa ao talude; (e) volumes de corte/aterro entre o terreno natural e o projetado; (f) curvas e cotas na planta com rótulos.
- As exigências de prefeitura variam por município. Convém tratar a "prancha de implantação" como um modelo configurável.

### Lacunas
- **Exigências municipais** de planta de situação/implantação (curvas de nível, cotas de platô, perfis, quadro de corte/aterro) não foram pesquisadas; a cota de buscas acabou.
- **Taludes típicos** (inclinações de corte/aterro, NBR 11682 sobre estabilidade de encostas) e **muros de arrimo** não foram pesquisados.
- **Canais brasileiros do YouTube/blogs** sobre terreno em Revit/Archicad: só o artigo da Comunidade Graphisoft Brasil foi localizado.
- **Outras ferramentas** (Vectorworks Site Model, Bonsai/BlenderBIM, SketchUp Sandbox, Twinmotion, QGIS) não foram pesquisadas nesta sessão.
