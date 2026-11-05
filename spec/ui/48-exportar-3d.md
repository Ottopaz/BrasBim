---
documento: Exportar 3D (glTF e OBJ)
requisito: item I2 da revisão geral (2026-10-30)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-05
status: aprovado pela delegação do revisor (2026-11-05, "siga a sequência") e implementado (G01–G05)
revisor: OTTO
---

# Exportar 3D (glTF e OBJ)

## 1. Propósito
Levar o modelo a programas de render e apresentação (Blender, Twinmotion, D5, Lumion,
SketchUp) e a visualizadores web. O IFC não serve para isso (sem textura, e nem todos o
leem). Pesquisa: `research_notes/Pesquisa Archicad Revit AutoCAD/complemento_exportar_gltf.md`.

## 2. Uso
- **Arquivo > Exportar 3D (glTF, OBJ)…**: escolhe o arquivo; o formato vem da extensão:
  **.glb** (glTF binário, um arquivo só; padrão) ou **.obj** (mais o `.mtl` ao lado).
- Sai **o que está visível** (camadas e filtro de situação da janela), como o 3D mostra;
  para levar tudo, mostram-se todas as camadas antes (decisão ao implementar: sem quadro
  de opções, o arquivo é escolhido direto).
- O balão diz quantos elementos e triângulos foram.

## 3. Conteúdo
- Todo elemento com corpo 3D: paredes, esquadrias, pilares, vigas, lajes, coberturas,
  escadas, guarda‑corpos, forro e piso, objetos, terreno. Ambientes, aberturas e desenhos
  2D ficam de fora.
- **Material**: as cores do 3D do BrasBim (estilo de cada peça; sem estilo, a cor do
  material do elemento — o acabamento da parede, a camada de cima da laje e do piso, a de
  baixo do forro). Vidro com transparência. Sem iluminação embutida (o programa de render
  ilumina).
- **Estrutura (glTF)**: cena → um nó por pavimento → um nó por elemento, com o nome do
  elemento (ou da classe) e `extras` `{GlobalId, ClasseIfc, Tipo, Pavimento}`; malhas por
  material. **OBJ**: um objeto (`o`) por elemento, com o nome e o GlobalId.
- **Eixos**: metros; z do IFC vira y do glTF (o eixo para cima do formato); o OBJ segue o
  mesmo (os programas o leem com y para cima).

## 4. Testes
- **G01** GLB válido (cabeçalho, JSON, buffer alinhado), um nó por elemento com GlobalId
  e classe, agrupado por pavimento.
- **G02** Cores: a do material da parede (acabamento) e o vidro transparente.
- **G03** Eixo: a altura da parede vira y.
- **G04** OBJ + MTL: um objeto por elemento, `usemtl`, `Kd` e `d`.
- **G05** Só o visível; interface (Arquivo > Exportar 3D e balão).

## 5. Fontes
Complemento da pesquisa §1–§2. Formato glTF 2.0 (especificação pública da Khronos,
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html);
OBJ/MTL (formato aberto de uso comum). Base própria: `ui/scene3d.py` (cores do 3D).
