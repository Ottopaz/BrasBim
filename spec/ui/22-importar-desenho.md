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
  um **conversor à parte**, que gera um DXF temporário (§8):
  1. ODA File Converter, só se o usuário já o tiver instalado (achado na instalação
     padrão);
  2. senão, o `dwg2dxf` do **GNU LibreDWG que vem com o BrasBim**;
  3. senão, o `dwg2dxf` do sistema (Linux: pacote `libredwg`).
  Sem nenhum deles, o BrasBim oferece baixar o LibreDWG (Windows) e tenta de novo.

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

**Revisão de 2026‑10‑28** (revisor: "o DWG está muito travado"), medida com o desenho
real do diário (planta de arquitetura, 72 camadas, 40 mil linhas, 150 mil pontos):

| | antes | depois |
|---|---|---|
| redesenhar a planta (deslocar, zoom) | 0,93 s | 0,04 s |
| editar o modelo (ex.: criar parede) | 0,80 s | 0,32 s |
| importar | 4,0 s | 3,0 s |

- A planta desenha cada anotação com caminhos em coordenadas do modelo, montados uma vez
  (um por espessura e tipo de linha) e levados à tela pela transformação do Qt
  (`PlanView._stroke_paths`); a planta nova reaproveita os caminhos das anotações que
  não mudaram. As formas de escolha das anotações não montam mais caminhos à toa.
- As primitivas do desenho importado ficam guardadas por anotação, pelos parâmetros e
  pela escala do pavimento (`annotations.base.CACHED`); cotas, etiquetas e outras que
  leem o resto do modelo continuam sendo refeitas.
- A planta lê o conteúdo de cada pavimento uma vez por montagem (`plan._decompose`), e o
  diário serializa sem copiar.
- A importação ainda grava cerca de 40 mil curvas no IFC (o desenho fica dentro do IFC);
  é o custo que sobra, só na hora de importar.
- **Erro corrigido:** texto ou nome de camada com bytes que não valem na codificação
  declarada (acentos em Windows‑1252) derrubava a importação (`RuntimeError: Attribute
  not set`, o IFC recusa substitutos isolados). `dxf._text` decodifica esses trechos como
  Windows‑1252 e tira caracteres de controle. Testes ID11 e ID12.

## 8. Conversor que vem com o BrasBim (2026‑10‑28)
Pedido do revisor: o usuário não deve ter de instalar programa nenhum para abrir DWG.
- **GNU LibreDWG 0.14** (GPL‑3.0‑or‑later, projeto GNU, escrito a partir de especificação
  pública): só `dwg2dxf.exe`, `libredwg-0.dll` e `libiconv-2.dll`, sem alteração, com o
  `LEIA-ME.txt` da licença e do código‑fonte (`core/imports/libredwg.py`). O ODA File
  Converter não pode ser redistribuído; o CADCraft/acadrust foi visto e descartado
  (pré‑alfa).
- Os binários **não vão para o git** (a DLL tem 31 MB): `libredwg.install` baixa o pacote
  oficial da versão fixada, confere o **SHA‑256** e extrai os três arquivos.
  `scripts/baixar_libredwg.py` põe em `brasbim/vendor/libredwg` (para o instalador; o
  wheel inclui a pasta); o aplicativo, quando falta, pergunta e baixa em
  `%LOCALAPPDATA%/BrasBim/libredwg`. Nada é instalado no sistema.
- Conversão: `dwg2dxf -y -o saída entrada`, sem janela de console; o LibreDWG pula objetos
  que não sabe ler e avisa no stderr; vale o DXF gerado (código de saída diferente de zero,
  com DXF, não recusa). Sem DXF, a recusa mostra a última linha do erro.
- Interface: o erro da importação também aparece numa janela (antes só em Mensagens);
  Arquivo > Abrir… aceita DWG e DXF e os importa no projeto aberto.
- Conferido com os DWG de exemplo do LibreDWG (versões 2000 a 2018): todas as camadas e
  entidades lidas; um bloco muito longe da origem no exemplo é do próprio arquivo (o DXF
  de referência tem o mesmo). A **escrita** de DWG do LibreDWG perde camadas, mas o
  BrasBim não escreve DWG.
- Testes: ID04 (sem conversor), ID07 (baixar e conferir), ID08 (conversão e erro), ID09
  (DWG reais, quando `BRASBIM_DWG_AMOSTRAS` aponta uma pasta), ID10 (interface: perguntar,
  baixar e tentar de novo).

## 9. Fontes
DXF Reference (Autodesk, documentação pública); ezdxf (MIT); IFC 4.3 `IfcAnnotation`,
`IfcIndexedPolyCurve`, `IfcCartesianPointList2D` [IFC-ANNOT]. Conversores externos
usados como programas à parte; GNU LibreDWG 0.14 (GPL‑3.0‑or‑later,
gnu.org/software/libredwg). Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 10. Pontos de revisão
(a) DWG por conversor à parte: o LibreDWG vem com o BrasBim (§8); o ODA só se o
    usuário já o tiver;
(b) uma anotação por camada do arquivo;
(c) o desenho entra com traço fino preto (cor por camada do arquivo fica para depois);
(d) hachuras e imagens do arquivo não entram; cotas entram explodidas.
(e) LibreDWG baixado na primeira vez, com pergunta (Windows); ODA, se instalado, tem
    preferência; Abrir… importa DWG/DXF no projeto aberto (§8).
