---
documento: Juntar IFC ao projeto (arrastar e soltar)
requisito: pedido do revisor no teste de uso (2026-11-07); RF-INT (interoperabilidade IFC)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-07
status: rascunho (pontos (a)–(f) no §8)
revisor: OTTO
---

# Juntar IFC ao projeto (arrastar e soltar)

## 1. Propósito
O revisor quer "importar modelos IFC só arrastando para dentro do BrasBim", e escolheu
que o arquivo arrastado **se junte ao projeto aberto** (não abra no lugar dele, nem fique
só como referência). Uso típico: trazer o estrutural (Eberick, QiBuilder, TQS), um
módulo, um mobiliário ou o projeto de um colega para dentro do modelo de arquitetura.

## 2. Uso
- Arrastar um ou mais `.ifc` do Explorador/Finder para a **planta ou o 3D**. O mesmo pelo
  menu **Arquivo > Juntar IFC…** (para quem não arrasta).
- Antes de juntar, um quadro curto:
  - **Pavimentos**: cada pavimento do arquivo vai para o pavimento do projeto de **mesma
    cota** (tolerância 1 cm) ou, sem cota igual, para um pavimento novo com o nome e a
    cota de lá (ponto (b)); a lista mostra a correspondência e deixa trocar.
  - **Posição**: na mesma origem (padrão: os arquivos do mesmo empreendimento costumam
    partilhar a origem) ou clicando o ponto de inserção na planta.
  - **O que trazer**: todos os elementos (padrão) ou só algumas classes (estrutura,
    paredes, mobiliário, instalações…).
- Depois: balão "N elementos juntados de <arquivo>" com **Desfazer**; os elementos
  ficam selecionados.
- Arrastar `.dwg`/`.dxf` continua indo para Importar desenho (spec/ui 22).
- Arrastar `.ifc` com o projeto vazio e sem nome: abre o arquivo como projeto (ponto (a)).

## 3. Regras
- **Elementos de outra origem**: entram como já entram os de um IFC aberto — corpo
  preservado, selecionáveis, movíveis, apagáveis, nas tabelas e no corte, sem os
  parâmetros do BrasBim (não viram parede paramétrica). Ponto (c).
- **Unidades e esquema**: arquivo em mm, cm ou pés é convertido para metros; IFC 2x3 e
  IFC 4 são migrados para o 4.3 (o caminho inverso do Exportar IFC, spec/ui 47).
- **GlobalId repetido** (o mesmo arquivo juntado duas vezes, ou um arquivo que veio deste
  projeto): pergunta se **substitui** os elementos de antes (atualização do estrutural) ou
  **junta como cópia** com GlobalIds novos. Ponto (d).
- Tipos, materiais e estilos vêm junto; material de mesmo nome que já existe no projeto
  é reaproveitado (ponto (e)).
- O projeto, o terreno e a edificação do arquivo não entram (fica o do projeto aberto);
  `IfcSite`/`IfcBuilding` extras viram só a correspondência de pavimentos.
- Georreferência: se os dois arquivos tiverem `IfcMapConversion`, a posição vem dela
  (ponto (f)); senão, a origem.

## 4. No IFC
- Elementos copiados com as representações, tipos (`IfcRelDefinesByType`), materiais,
  Psets e quantidades; contidos no pavimento correspondente
  (`IfcRelContainedInSpatialStructure`).
- Pset `BrasBim_Origem` em cada elemento juntado: `Arquivo` (nome), `Data`, `GlobalIdOriginal`
  (quando o GlobalId mudou) — para a atualização do ponto (d).
- Uma só transação: Desfazer tira tudo o que entrou.

## 5. Testes
- **JI01** juntar um IFC 4.3 com parede, laje e pilar em dois pavimentos: correspondência
  por cota, contagem, corpo igual ao de origem, IFC válido.
- **JI02** IFC 2x3 em milímetros: migrado e convertido.
- **JI03** GlobalId repetido: substituir e juntar como cópia.
- **JI04** Desfazer e Refazer.
- **JI05** interface: arrastar para a planta (evento de soltar com URL de arquivo), quadro
  de pavimentos, balão.

## 6. Fica para depois
- Referência vinculada (modelo por cima, só leitura, que atualiza quando o arquivo muda).
- Converter elementos de outra origem em paramétricos (parede, laje do BrasBim).

## 7. Desempenho
Arquivos grandes (centenas de MB) juntam em segundo plano, com barra de progresso e
Cancelar; o limite e a medição ficam para a implementação.

## 8. Pontos para o revisor
- (a) Projeto vazio e sem nome: arrastar **abre** o arquivo (proposta) ou junta mesmo
  assim?
- (b) Pavimento sem cota igual no projeto: criar pavimento novo (proposta) ou pôr no mais
  próximo?
- (c) Elementos juntados ficam como "de outra origem" (proposta, não editáveis como
  paramétricos), certo?
- (d) GlobalId repetido: perguntar substituir/copiar (proposta) ou sempre substituir
  (bom para atualizar o estrutural a cada revisão)?
- (e) Material com o mesmo nome: reaproveitar o do projeto (proposta, a cor e a hachura
  ficam as do BrasBim) ou trazer o de lá renomeado?
- (f) Posição: origem/georreferência (proposta) ou sempre pedir o ponto de inserção?

## 9. Fontes
- IFC 4.3 (buildingSMART, documentação pública): `IfcRelContainedInSpatialStructure`,
  `IfcBuildingStorey`, `IfcMapConversion`, `IfcRelDefinesByType`.
- IfcOpenShell 0.8 (documentação pública da API): `ifcopenshell.file.add`,
  `ifcopenshell.util.element.copy_deep`, `ifcopenshell.util.schema.Migrator`,
  `ifcopenshell.util.unit`.
- Pesquisa de como Archicad e Revit juntam/vinculam IFC (páginas públicas de ajuda): a
  fazer antes da aprovação, em `research_notes/.../complemento_juntar_ifc.md`.
