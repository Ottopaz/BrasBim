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

**Revisão de 2026‑10‑28** (revisor: "o DWG está muito travado"; "o DWG deve ser
importado apenas como linhas, não como modelos IFC, justamente para ser rápido e leve").
Medido com o DWG real do revisor (planta de arquitetura com mobiliário: 174 mil linhas,
13 mil splines em blocos, 72 camadas) e com outro de 40 mil linhas.

- **Só linhas, cópia compacta no IFC** (escolha do revisor): a anotação do desenho
  importado **não tem geometria IFC**; as linhas ficam num bloco compactado nos
  parâmetros (`linework.Lines.pack`: coordenadas quantizadas a 0,01 mm, em diferenças
  sucessivas, comprimidas, base64), junto com textos e pontos. O projeto abre igual em
  outra máquina sem o DWG; outros programas IFC não veem as linhas. As operações levam o
  mesmo texto compactado (o diário cai de 33 MB para 1,8 MB). Arquivos antigos, com a
  lista de linhas, continuam sendo lidos e passam para o compactado na primeira
  transformação.
- **Linhas em arrays** (`core/linework.py`): trechos, cantos, busca por distância e
  transformação afim são feitos com numpy, sem um objeto por linha. A planta guarda
  `Plan.bulk` (sem forma de escolha por linha); escolha, janela, laço, enquadramento e
  atração (`SnapIndex.bulk`) consultam os arrays. Na tela, um caminho do Qt por camada,
  montado uma vez e levado pela transformação; traço fino sem suavização.
- **Leitor próprio de DXF** (`core/imports/dxf_fast.py`), só da geometria, direto das
  tags (DXF Reference, especificação pública): LINE, LWPOLYLINE (com arcos), POLYLINE,
  ARC, CIRCLE, ELLIPSE, SPLINE (B‑spline avaliada com numpy; por pontos de passagem, pela
  matemática do ezdxf), TEXT, MTEXT (direção 11/21), POINT; INSERT (inclusive em matriz e
  espelhado) e DIMENSION (com o deslocamento 12/22/32) explodidos; espaço de papel fora.
  O ezdxf (leitura normal, e a de recuperação só se ela falhar) fica de reserva para o
  que o leitor próprio não entende (binário, cota fora do plano, arquivo sem ENTITIES).
  Conferido contra o ezdxf nos dois DWG do revisor: mesmas camadas, linhas, textos,
  pontos e extensão; curvas dentro do desvio de 10 mm.

| DWG real (174 mil linhas) | antes | depois |
|---|---|---|
| ler o DXF convertido | 19,5 s (ezdxf com recuperação: mais) | 5,8 s |
| importar (gravar no projeto) | 13,2 s | ~1 s |
| mover o mouse (Selecionar / Parede) | ~1 s / ~4 s por movimento | ~0,06 s |
| redesenhar | 0,11 s | 0,04 s |
| criar parede | 1,25 s | 0,18 s |
| IFC salvo | — (dezenas de MB) | 1,8 MB em 0,1 s |

Do clique em Importar até o desenho na tela: ~11 s (2,8 s de conversão pelo LibreDWG,
5,8 s de leitura, o resto para compactar e montar o desenho uma vez).

- **Erro corrigido:** texto ou nome de camada com bytes fora da codificação declarada
  (Windows‑1252) derrubava a importação (`RuntimeError: Attribute not set`).
  `dxf._text` decodifica esses trechos e tira caracteres de controle.
- Testes ID11–ID12 (`tests/test_importar_desenho.py`) e ID13–ID18
  (`tests/test_desenho_leve.py`).

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
usados como programas à parte; código do ezdxf (MIT, aberto) lido para a regra do
deslocamento das cotas; GNU LibreDWG 0.14 (GPL‑3.0‑or‑later,
gnu.org/software/libredwg). Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 10. Pontos de revisão
(a) DWG por conversor à parte: o LibreDWG vem com o BrasBim (§8); o ODA só se o
    usuário já o tiver;
(b) uma anotação por camada do arquivo;
(c) o desenho entra com traço fino preto (cor por camada do arquivo fica para depois);
(d) hachuras e imagens do arquivo não entram; cotas entram explodidas.
(e) LibreDWG baixado na primeira vez, com pergunta (Windows); ODA, se instalado, tem
    preferência; Abrir… importa DWG/DXF no projeto aberto (§8).
(f) Desenho importado só como linhas compactadas no IFC, sem geometria IFC (§7).
(g) Matriz de inserção (MINSERT) traz todas as cópias; o leitor anterior trazia uma (§7).
