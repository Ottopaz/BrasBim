---
documento: Exportar IFC 2x3 e IFC 4
requisito: RF-INT-01; item I1 da revisão geral (2026-10-30)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-05
status: aprovado pela delegação do revisor (2026-11-05, "pode fazer o que julgar melhor"; "siga a sequência") e implementado (EX01–EX06)
revisor: OTTO
---

# Exportar IFC 2x3 e IFC 4

## 1. Propósito
O BrasBim grava IFC 4.3, mas o Revit recomenda o 2x3 e os programas brasileiros de
estrutura e instalações leem melhor o 2x3. Esta spec cria a exportação de compatibilidade:
o projeto continua em 4.3 e sai uma cópia em IFC 2x3 ou IFC 4, válida no esquema.

Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_exportar_ifc.md`.

## 2. Uso
- **Arquivo > Exportar IFC…**: escolhe o arquivo e as opções:
  - **Versão**: IFC 2x3 (padrão: é o que todos leem), IFC 4 ou IFC 4.3 (o próprio
    arquivo do projeto).
  - **Destino**: **Coordenação** (tudo o que é modelo; padrão) ou **Estrutura e
    instalações** (paredes, pilares, vigas, lajes, coberturas, escadas, aberturas e
    ambientes; sem mobiliário, terreno, forro e piso).
  - **Só o visível**: o que as camadas e o filtro de situação da janela mostram
    (desligado por padrão).
  - **Desenhos 2D** (cotas, textos, hachuras, vistas, pranchas e tabelas): só no IFC 4 e
    4.3; desligado por padrão. No 2x3 não vão.
  - **Propriedades do BrasBim** (Psets `BrasBim_*`): ligadas por padrão; desligadas, só os
    Psets padrão do IFC e as quantidades.
- As escolhas ficam guardadas para a próxima vez (configuração do aplicativo).
- Ao terminar, o balão diz a versão, quantos elementos foram e o que foi adaptado.

## 3. Adaptações do IFC 2x3
O que o 2x3 não tem vira o equivalente mais próximo:
- `IfcDoorType`/`IfcWindowType` → `IfcDoorStyle`/`IfcWindowStyle` (nome, operação,
  Psets do tipo).
- `IfcMaterialProfileSetUsage` (pilar, viga) → o material do perfil (ou
  `IfcMaterialList` com os das partes); `IfcMaterialConstituentSet` (objetos, esquadrias)
  → `IfcMaterialList`.
- `IfcTriangulatedFaceSet` (terreno, peças de malha) → `IfcFacetedBrep` fechado ou
  `IfcShellBasedSurfaceModel` aberto.
- `IfcIndexedPolyCurve` → `IfcPolyline`.
- `IfcFurniture` → `IfcFurnishingElement`; `IfcSanitaryTerminal` e
  `IfcElectricAppliance` → `IfcFlowTerminal`; `IfcGeographicElement` → 
  `IfcBuildingElementProxy` (o `ObjectType` guarda a classe de origem).
- `IfcRelInterferesElements` sai: os recortes já estão no corpo.
- Parede com `IfcMaterialLayerSetUsage` e eixo → `IfcWallStandardCase`, como a visão de
  coordenação 2.0 espera.
- Um `IfcOwnerHistory` (BrasBim, a data da exportação) em toda entidade com GlobalId.
- Os GlobalIds são os mesmos do projeto (os outros programas reconhecem o elemento numa
  nova exportação).

## 4. Regras
- O projeto aberto não muda; a exportação trabalha numa cópia.
- O arquivo é conferido pelo validador do esquema do IfcOpenShell; se falhar, nada é
  gravado e a mensagem diz o primeiro erro.
- IFC 4: a mesma conversão do IfcOpenShell (4.3 → 4), sem adaptação de classe.

## 5. Testes
- **EX01** IFC 4 de um projeto com quase tudo: válido no esquema, mesmos GlobalIds dos
  elementos.
- **EX02** IFC 2x3 do mesmo projeto: válido; parede como `IfcWallStandardCase`, porta com
  `IfcDoorStyle`, pilar com material, terreno e mobiliário adaptados, `OwnerHistory` em
  todos.
- **EX03** Destino Estrutura e instalações: sem mobiliário, terreno, forro e piso.
- **EX04** Só o visível: camada oculta fica de fora.
- **EX05** Sem propriedades do BrasBim: nenhum Pset `BrasBim_*`; com desenhos 2D no IFC 4:
  as anotações vão.
- **EX06** Interface: Arquivo > Exportar IFC, opções, balão.

## 6. Pontos para o revisor (decididos com as propostas)
- (a) Padrão IFC 2x3 — sim.
- (b) Destino Estrutura e instalações sem forro e piso — sim (o engenheiro não usa).
- (c) Abrir o arquivo no Revit, Archicad, Eberick e QiBuilder: fica com o revisor.

## 7. Fontes
Complemento da pesquisa §1–§4. Base própria: spec/ui 18 (camadas), spec/ui 31
(situação), spec/ui 41 §2 (exportar DWG).
