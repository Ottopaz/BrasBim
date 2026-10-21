---
documento: Importar desenho DXF e DWG como referência
requisito: RF-DOC-11 (importação de DXF/DWG como referência), antecipado para o MVP
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-21
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Importar desenho (DXF, DWG)

## 1. Propósito
Trazer para o projeto um desenho 2D de outro programa — o **levantamento topográfico**
em primeiro lugar — para desenhar por cima dele e, no terreno, pegar as linhas das
curvas de nível (spec do terreno, parte B).

## 2. Formatos
- **DXF**: lido diretamente (formato com documentação pública; biblioteca ezdxf, MIT).
- **DWG**: formato fechado. O BrasBim não o lê nem faz engenharia reversa dele: chama
  um **conversor externo** instalado pelo usuário, que gera um DXF temporário:
  1. ODA File Converter (gratuito, opendesign.com), achado na instalação padrão;
  2. ou o `dwg2dxf` do LibreDWG, se estiver no PATH.
  Sem conversor, a importação recusa com a orientação de instalar um deles ou salvar o
  arquivo como DXF no programa de CAD.

## 3. O que entra
- Linhas, polilinhas (2D e 3D), arcos, círculos, elipses e curvas (spline) viram
  polilinhas, com desvio máximo de 1 cm nos arcos; textos (TEXT, MTEXT) e pontos.
- Blocos e cotas são explodidos (as cotas viram linhas e textos); o que está na
  camada "0" dentro do bloco fica na camada da inserção (convenção do DXF). Hachuras e
  imagens ficam de fora (V1).
- **Cota da linha**: se todos os vértices têm a mesma cota (polilinha com elevação,
  polilinha 3D de curva de nível), ela é guardada; o terreno usa (parte B).
- **Unidade**: a do cabeçalho do arquivo ($INSUNITS), se mm, cm ou m; senão, o usuário
  escolhe (padrão metros).
- **Perto da origem**: desenho a mais de 10 km da origem (coordenadas UTM de
  levantamento) vem com o canto inferior esquerdo para (0, 0); dá para desmarcar.

## 4. IFC
Uma `IfcAnnotation` (`ObjectType` `DesenhoImportado`) por camada do arquivo, contida no
pavimento ativo, com o estado no Pset `BrasBim_Anotacao` (tipo `reference2d`: nome,
arquivo de origem, camada, linhas com a cota, textos e pontos) e a representação
`Annotation` com as linhas em `IfcIndexedPolyCurve` sobre `IfcCartesianPointList2D`
(uma entidade por linha, não uma por vértice) e os textos. [IFC-ANNOT]

## 5. Interface
- **Arquivo > Importar desenho (DXF, DWG)…**: escolhe o arquivo; a janela mostra o
  pavimento, as camadas do arquivo com quantas linhas, textos e pontos cada uma tem
  (todas marcadas), a unidade e "Trazer o desenho para perto da origem". Importar cria
  tudo numa transação (um desfazer). Depois, a planta enquadra o desenho.
- Os desenhos importados vão para a camada **Levantamento** (grupo Entorno), criada no
  conjunto inicial de camadas: ocultar e bloquear pelo painel Camadas.
- Cada camada do arquivo é um elemento: selecionar, mover, girar, espelhar, excluir.

## 6. Critérios de aceite (testes)
- [x] **ID01** Leitura: camadas, curvas com cota (polilinha com elevação e 3D), divisa
      fechada, bloco explodido na camada da inserção, círculo dentro de 1 cm, texto com
      ângulo, ponto com cota; desenho longe vem para a origem.
- [x] **ID02** Importar em metros um arquivo em mm, com desfazer/refazer e diário; IFC
      válido.
- [x] **ID03** Só as camadas escolhidas; planta; camada Levantamento; mover; achar a
      linha sob o cursor; excluir.
- [x] **ID04** DWG: sem conversor, recusa com a orientação; com conversor, importa.
- [x] **ID05** Recusas: unidade, nenhuma camada, arquivo que não é DXF.
- [x] **ID06** Interface: a janela de importação e o menu.

## 7. Desempenho
Levantamento com 20 000 polilinhas de 20 vértices: ler 6 s, importar 2 s, planta 0,5 s,
salvar 2 s (17 MB de IFC). Para isso a anotação do desenho importado não é refeita a
cada transação, e o diário da sessão serializa cada transação uma vez.

## 8. Fontes
DXF Reference (Autodesk, documentação pública); ezdxf (MIT); IFC 4.3 `IfcAnnotation`,
`IfcIndexedPolyCurve`, `IfcCartesianPointList2D` [IFC-ANNOT]. Conversores externos
usados como programas à parte. Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 9. Pontos de revisão
(a) DWG por conversor externo (o usuário instala o ODA File Converter);
(b) uma anotação por camada do arquivo;
(c) o desenho entra com traço fino preto (cor por camada do arquivo fica para depois);
(d) hachuras e imagens do arquivo não entram; cotas entram explodidas.
