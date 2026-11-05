# Complemento: exportar IFC 2x3 e IFC 4 (2026‑11‑05)

Item I1 da revisão geral (`reports/Revisao geral antes do instalador (2026-10-30).md`):
"programas de estrutura e instalações usados no Brasil ainda leem melhor o 2x3";
RF‑INT‑01. Só fontes públicas; descreve **funções**, sem copiar nomes de comandos nem
diálogos.

## 1. O que já estava na pesquisa
- `interoperabilidade_openbim.md` §1: segundo uma tabela de terceiro (Newforma), o
  exportador IFC do Revit 2025–2027 tem o **IFC 2x3** como o esquema mais recomendado e
  não recomenda o 4.3; no Archicad o 4.3 aparece como "em breve". Inferência registrada lá:
  um programa nativo em 4.3 precisa de uma **exportação de compatibilidade IFC 2x3 /
  IFC 4**, ou não será lido pelos parceiros.
- Mesma nota: perdas recorrentes na troca (Psets mapeados à mão, eixos de parede,
  aberturas) e a certificação cobrir só a visão de referência.

## 2. Revit: opções da exportação (ajuda Autodesk, via busca)
- Escolhe‑se a **versão do IFC**; a ajuda de 2017 dizia que a "IFC 2x3 Coordination View
  2.0" era a exportação certificada padrão e a mais lida pelos outros sistemas; a de 2024
  manda usá‑la para exportar aço estrutural.
- **Quantidades base**: incluídas a partir da geometria, sem regra de medição.
- **Dividir paredes, pilares e dutos por pavimento**.
- **Só o que está visível na vista**: exporta os elementos visíveis da vista atual (os
  ocultos temporariamente ficam de fora, segundo a de 2019). —
  [IFC Export Setup Options (2017)](https://help.autodesk.com/cloudhelp/2017/ENU/Revit-DocumentPresent/files/GUID-E029E3AD-1639-4446-A935-C9796BC34C95.htm);
  [(2018)](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-DocumentPresent/files/GUID-E029E3AD-1639-4446-A935-C9796BC34C95.htm);
  [(2019)](https://help.autodesk.com/cloudhelp/2019/ENU/Revit-DocumentPresent/files/GUID-E029E3AD-1639-4446-A935-C9796BC34C95.htm);
  [(2024)](https://help.autodesk.com/cloudhelp/2024/ENU/Revit-DocumentPresent/files/GUID-E029E3AD-1639-4446-A935-C9796BC34C95.htm)

## 3. Archicad: tradutores de exportação (ajuda Graphisoft, via busca)
- Certificado em **IFC 2x3 Coordination View 2.0** (importar e exportar). No IFC 4, a
  visão de coordenação se divide em duas (referência e transferência de projeto), e a
  ajuda recomenda usar IFC 4 só quando se sabe que o programa de destino o lê. —
  [Model View Definitions (AC24)](https://help.graphisoft.com/AC/24/INT/_AC24_Help/115_IFC/115_IFC-46.htm);
  [(AC27)](https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-47.htm)
- As opções ficam num **conjunto salvo** (tradutor) que se duplica, ajusta e troca entre
  usuários. — [Import/Export Settings](https://helpcenter.graphisoft.com/?p=62997)
- Guia de terceiro para levar ao Revit: IFC 2x3, filtro de elementos (todos, ou só os
  estruturais para o engenheiro). —
  [ArchiCAD to Revit IFC Exchange](https://smart.macinteract.com/archicad-to-revit-ifc-exchange/)

## 4. O que o IfcOpenShell dá (lido no pacote instalado, 0.9)
- `ifcopenshell.util.schema.Migrator` converte IFC 4.3 → IFC 4 e IFC 4 → IFC 2x3, com
  mapas de classes e atributos. Com um projeto do BrasBim com quase tudo, o IFC 4 sai
  direto. O 2x3 não tem equivalente para 15 classes que o BrasBim usa:
  `IfcDoorType`/`IfcWindowType` (no 2x3: `IfcDoorStyle`/`IfcWindowStyle`),
  `IfcMaterialProfileSet(Usage)`, `IfcMaterialConstituentSet`, `IfcRelInterferesElements`,
  `IfcIndexedPolyCurve`/`IfcCartesianPointList`, `IfcTriangulatedFaceSet`,
  `IfcFurniture`, `IfcSanitaryTerminal`, `IfcGeographicElement`.
- No 2x3 o `OwnerHistory` é obrigatório em toda entidade com GlobalId.

## 5. O que levar para o BrasBim (vai para a spec/ui 47)
1. **Arquivo > Exportar IFC**, com a versão (IFC 2x3, IFC 4) e um **destino pronto**
   ("para estrutura e instalações": só o que importa ao engenheiro) — como o filtro dos
   tradutores, sem precisar montar um.
2. **Só o visível** (camadas e situação da janela), como no Revit.
3. Quantidades base sempre (o BrasBim já grava).
4. O que não existe no 2x3 vira o equivalente mais próximo, **sem perder o dado**:
   tipos de esquadria como estilos, perfil e constituintes como material, malha como
   faces, mobiliário como `IfcFurnishingElement`, terreno como peça genérica com o nome;
   recortes já estão no corpo.
5. **O arquivo exportado é conferido** pelo validador do esquema antes de gravar; o
   balão diz o que foi adaptado.

## 6. Lacunas
- As páginas da Autodesk e da Graphisoft foram vistas só pelo resumo do buscador.
- Falta a prova de abrir o arquivo no Revit, no Archicad, no Eberick e no QiBuilder:
  fica para o teste do revisor.
