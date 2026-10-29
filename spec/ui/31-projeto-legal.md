---
documento: Projeto legal (projeto para licenciamentos)
requisito: roteiro do CONTEXTO, item 2; recomendações 1, 2, 3 e 8 de reports/Pesquisa Archicad Revit AutoCAD.md
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-27
status: em revisão (fluxo do MVP: implementar por etapas, §8; etapas 1–3 feitas, §12–§14)
revisor: OTTO
---

# Projeto legal

## 1. Propósito
Gerar do modelo IFC as peças que a prefeitura pede para aprovar uma obra: elementos
coloridos por **situação** (existente, a construir, a demolir, a regularizar, a
transformar), **quadro de áreas** com índices urbanísticos, **quadro de esquadrias** e
**memorial descritivo**, com as regras de cada cidade num **perfil municipal**. A
pesquisa mostra que nenhum dos três programas comparados entrega isso pronto e que hoje o
caminho é "tabela de áreas → Excel → preenchimento à mão" [SIENGE-QA] [IFSC-K22].

Na interface aparecem os dois nomes: "Projeto legal (projeto para licenciamentos)". O
segundo é o nome da etapa na NBR 16636‑2 [USP-16636]; o primeiro, o do mercado.

## 2. Situação de cada elemento
- Todo elemento do modelo (paredes, lajes, pilares, vigas, coberturas, esquadrias,
  objetos, escadas, guarda‑corpos, terreno, ambientes) **e** toda anotação (cotas,
  textos, hachuras, linhas 2D, marcadores de corte e fachada) tem uma **situação**:

  | Situação (UI) | IFC `Status` (Pset comum) | `BrasBim_Intervencao.Situacao` |
  |---|---|---|
  | A construir (padrão) | `NEW` | `A_CONSTRUIR` |
  | Existente (manter) | `EXISTING` | `EXISTENTE` |
  | A demolir | `DEMOLISH` | `A_DEMOLIR` |
  | A regularizar | `EXISTING` | `A_REGULARIZAR` |
  | A transformar (adequar) | `EXISTING` | `A_TRANSFORMAR` |
  | Temporário | `TEMPORARY` | `TEMPORARIO` |

- Os valores do `Status` foram conferidos no esquema IFC 4.3 do IfcOpenShell (DEMOLISH,
  EXISTING, NEW, TEMPORARY, OTHER, NOTKNOWN, UNSET). "A regularizar" e "a transformar" não
  existem no IFC: vão no Pset próprio `BrasBim_Intervencao`, que vale para tudo; o
  `Status` do `Pset_<Classe>Common` é escrito junto quando a classe tem esse Pset (para
  outros programas lerem). Ambientes e anotações não têm `Status` comum: só o Pset próprio.
- Painel de propriedades: campo **Situação** (vale para a seleção toda). Mini‑barra:
  Situação ▸. Opções da ferramenta de criação: "Situação dos novos elementos" (padrão:
  A construir). Selecionar semelhantes ganha o critério Situação.
- Copiar herda a situação do original.
- Situação **não** é camada: um elemento existente continua na camada Paredes. As camadas
  seguem para ligar e desligar; a situação é filtro de vista (§3).

## 3. Vista por situação
- Cada vista (planta, corte, fachada, vista salva) tem o **filtro de situação**:
  *Projeto* (tudo, colorido pelo perfil), *Antes da obra* (existente + a demolir + a
  regularizar + a transformar, sem cor), *Depois da obra* (sem o "a demolir", sem cor) e
  *Sem cores*. Guardado na vista salva (spec/ui 25).
- Em *Projeto*, a cor de linha e a hachura de corte de cada elemento vêm do perfil
  municipal (§4); a cor vale para traço e preenchimento das paredes cortadas, as demais
  regras gráficas ficam.
- Imprimir em preto (spec/ui 27) imprime as situações por hachura, não por cor.
- Na legenda (§6) entram só as situações presentes no desenho.

## 4. Perfil municipal
- Arquivo JSON aberto e versionado (`brasbim/perfis/<uf>-<cidade>.json`), com `versao`,
  `fonte` (documento da prefeitura e data de acesso) e:
  - `cores`: situação → cor e hachura;
  - `escalas`: implantação, plantas, cortes e fachadas;
  - `planta`: `completa` ou `simplificada` (sem compartimentação interna nem aberturas,
    como São Paulo pede [SP-PECAS]);
  - `quadro_de_areas`: linhas e índices exigidos (§5) e regras de área computável;
  - `selo`: campos obrigatórios (vão para a folha mestra, spec/ui 26);
  - `notas`: textos obrigatórios (ex.: "a aprovação não reconhece a propriedade" [ARARAS]
    [JACAREI]);
  - `pdf`: tamanho máximo (Curitiba: 3 MB [CURITIBA]) e espaço reservado ao carimbo de
    aprovação na última prancha.
- O projeto guarda o perfil escolhido **copiado** dentro do IFC (`IfcProject`, Pset
  `BrasBim_PerfilMunicipal`, JSON), para abrir igual em outra máquina; Projeto > Perfil
  municipal… escolhe, mostra a fonte e permite editar a cópia do projeto.
- Perfis que vêm junto, só com o que tem fonte pública:
  - **Genérico** (padrão): A construir vermelho, Existente preto, A demolir amarelo, A
    regularizar azul, A transformar verde;
  - **Araras/SP** (POP 001/21): preto ou azul = conservar, vermelho = construir, amarelo
    = demolir, verde = a transformar [ARARAS];
  - **Jacareí/SP**: implantação 1:200, arquitetura 1:100, quadro de áreas com piscina à
    parte [JACAREI];
  - **São Paulo/SP**: projeto simplificado 1:100 [SP-PECAS];
  - **Curitiba/PR**: PDF ≤ 3 MB, espaço para o carimbo na última prancha [CURITIBA].
  Londrina fica fora até a fonte primária ser conferida (só trecho de busca; as cores são
  o inverso das de Araras).

## 5. Quadro de áreas
- Tabela nova do tipo "Quadro de áreas" (spec/ui 17), refeita a cada mudança no modelo.
  Fonte: `IfcSpace` (contorno = `GrossFloorArea`, spec/ui 13 §3.3) por pavimento,
  terreno (área do lote = área do contorno do `IfcSite`/terreno, ou o valor digitado
  "de escritura") e a situação dos ambientes.
- Cada ambiente ganha a **classificação de área**: computável, não computável (com o
  motivo: varanda, garagem, ático…), descoberta, permeável e "fora do total" (piscina
  [JACAREI]). Pset `BrasBim_QuadroDeAreas`. O perfil diz as regras padrão (ex.: varanda
  até N m² não computável); o usuário pode trocar ambiente a ambiente.
- Linhas: área por pavimento e por situação (existente, a construir, a regularizar, a
  demolir), total construído, computável e não computável, área do terreno (real e de
  escritura), área livre, permeável. Índices: **TO** = projeção / terreno, **CA** =
  computável / terreno, **taxa de permeabilidade** = permeável / terreno; comparados com
  os máximos/mínimos digitados para o lote (vêm do zoneamento, não do perfil).
- **Memória de cálculo**: cada número abre a lista de ambientes e a conta (Jacareí pede
  a memória [JACAREI]); exporta CSV como as outras tabelas.
- Quadros da NBR 12721 (incorporação) ficam para depois.

## 6. Peças na prancha
- **Legenda de situações** (anotação nova): amostra de cor/hachura e nome das situações
  presentes, vinda do perfil.
- **Quadro de áreas** e **quadro de esquadrias** vão para a prancha como as tabelas
  (spec/ui 17). O quadro de esquadrias usa as colunas: código, quantidade, L × H,
  peitoril, tipo, material e situação, agrupado por código (já existe a base nos tipos de
  porta e janela, códigos P1/J1).
- **Notas obrigatórias** do perfil entram no carimbo como campo `{notas}`.
- Exportar PDF avisa quando o arquivo passa do limite do perfil (não comprime sozinho) e
  quando a última prancha não tem o espaço livre do carimbo de aprovação.

## 7. Memorial descritivo
- Projeto > Memorial descritivo…: texto gerado do modelo em seções na ordem de Araras
  [ARARAS]: dados da obra, fundação, estrutura, paredes, esquadrias, cobertura,
  impermeabilização, revestimentos, soleiras e peitoris, forro, pintura, pavimentação,
  louças e metais, instalações, limpeza. Cada seção lista os tipos usados com materiais e
  camadas (paredes: tipo, espessura e camadas; esquadrias: o quadro resumido; cobertura:
  tipo e inclinação), com a situação.
- O texto gerado é editável e guardado no projeto (Pset do `IfcProject`); "Refazer do
  modelo" atualiza só as seções não editadas à mão. Exporta `.md` e PDF (`.docx` fica
  para depois).

## 8. Etapas de implementação (fluxo do MVP)
1. **Situação** (§2) com o Pset, o `Status`, painel, mini‑barra, opção de criação,
   copiar, selecionar semelhantes e o filtro de vista com cores do perfil Genérico (§3).
   **Feita** (§12).
2. **Perfil municipal** (§4): arquivo, cópia no IFC, diálogo, perfis prontos; cores e
   escalas aplicadas. **Feita** (§13).
3. **Quadro de áreas** (§5) com memória de cálculo e índices. **Feita** (§14).
4. **Peças na prancha** (§6): legenda, quadro de esquadrias, notas, aviso do PDF.
5. **Memorial descritivo** (§7).
Planta simplificada (sem compartimentação) e export DXF ficam para um pacote seguinte.

## 9. Critérios de aceite (testes)
- **PL01** Parede marcada "A demolir": `Pset_WallCommon.Status = DEMOLISH` e
  `BrasBim_Intervencao.Situacao = A_DEMOLIR`; "A regularizar" dá `EXISTING` +
  `A_REGULARIZAR`; desfazer volta; ambiente e cota só com o Pset próprio.
- **PL02** Copiar uma parede existente dá cópia existente; selecionar semelhantes por
  situação.
- **PL03** Filtro *Depois da obra* tira da planta a parede a demolir; *Projeto* pinta a
  parede a construir com a cor do perfil; vista salva guarda o filtro.
- **PL04** Perfil Araras copiado no IFC: abrir de novo mantém as cores mesmo sem o
  arquivo do perfil.
- **PL05** Lote 10 × 30 (300 m²), casa 8 × 10 com varanda 2 × 8 não computável: TO =
  (80 + 16)/300, CA = 80/300; memória de cálculo lista os ambientes.
  Mais: PL05b (lote de escritura e limites, atende/não atende), PL05c (classificação
  escolhida no ambiente, motivo, descoberta), PL05d (área por situação com paredes, a
  demolir fora da soma), PL05e (piscina à parte em Jacareí, tabela e CSV com a memória).
- **PL06** Quadro de esquadrias agrupa 3 janelas J1 e 2 portas P1 com L × H e peitoril.
- **PL07** Memorial gera as seções na ordem, com os tipos de parede e camadas; seção
  editada não muda ao refazer.
- **PL08** PDF acima do limite do perfil Curitiba avisa.
- **PL09** Perfis prontos válidos, com fonte; o que falta numa cidade vem do Genérico e o
  perfil diz quais cores são herdadas.
- **PL10** Hachura da situação nas paredes cortadas em Imprimir em preto; situações com a
  mesma cor e hachuras diferentes não se juntam; situação sem cor não é pintada.
- **PL11** Escolher o perfil com "Aplicar escalas" muda plantas, cortes e fachadas numa
  transação; corte e fachada novos nascem na escala do perfil.
- **PL12** Perfil inválido (nome, situação, cor, hachura, escala, planta, PDF) é recusado.

## 10. Fontes
| Código | Documento |
|---|---|
| ARARAS | Prefeitura de Araras, *POP 001/21 Alvará de Construção* (araras.sp.gov.br), via `research_notes/.../normas_e_projeto_legal_brasil.md` §3 |
| JACAREI | Prefeitura de Jacareí, *Anexo XII Manual Técnico* (jacarei.sp.gov.br), idem |
| SP-PECAS | Prefeitura de São Paulo, *Peças gráficas de projeto (LOE 16.642/17)* (prefeitura.sp.gov.br), idem |
| CURITIBA | Prefeitura de Curitiba, *Manual do Autor do Projeto*, 2ª ed., 2020 (mid.curitiba.pr.gov.br), idem |
| SIENGE-QA | Sienge, *Quadro de áreas* (blog), idem |
| IFSC-K22 | Repositório IFSC, Karkotli 2022, idem (trecho de busca) |
| USP-16636 | USP e‑Disciplinas, *Gestão do processo de projeto* (trecho de busca), idem §2 |
| IFC43 | Esquema IFC 4.3 do IfcOpenShell: enumeração do `Status` dos Psets comuns (conferido em 2026‑10‑26) |

Conhecimento geral (CG): TO, CA e taxa de permeabilidade como razões de áreas. Nada de
`_restrito/` nem de `tools/`; nomes, textos e layout são próprios. Os filtros de reforma
e as fases dos outros programas foram citados na pesquisa só como existência do recurso;
a solução aqui (situação + perfil) é própria.

## 11. Pontos de revisão
(a) Situação em todo elemento e anotação, com o Pset próprio e o `Status` comum (§2).
(b) Situação separada das camadas; filtro por vista com quatro modos (§3).
(c) Perfil copiado dentro do IFC; Londrina fora até conferir (§4).
(d) Classificação de área por ambiente, com regras padrão do perfil (§5).
(e) Ordem das etapas (§8): situação primeiro.
(f) Memorial só em `.md` e PDF nesta etapa (§7).
(g) Obra nova (tudo *A construir*) sem cores na vista Projeto (§12).
(h) Parede cortada pintada inteira (traço e preenchimento) na cor da situação; existente
    sai preta cheia no perfil Genérico (§12).
(i) Situação dos novos elementos como botão com menu na barra Opções, igual para todas
    as ferramentas, não guardado no projeto (§12).
(j) Imprimir em preto sem hachura por situação até a etapa 2; 3D sem cores (§12).
(k) Hachura do perfil só em Imprimir em preto; na tela e na prancha em cores vale a cor
    sobre o preenchimento do tipo (§13).
(l) Hachuras do Genérico (próprias, sem fonte): a construir linhas 45°, existente cheia,
    a demolir sem hachura, a regularizar cruzada, a transformar linhas 135° (§13).
(m) Escalas de Araras (1:50 ou 1:100 na fonte) fixadas em 1:100; implantação 1:200 no
    Genérico e em Araras (§13).
(n) "Aplicar escalas" marcado por padrão no diálogo; a implantação fica guardada até
    existir uma vista de implantação (§13).
(o) Área construída = face externa das paredes ∪ ambientes cobertos; cômodo sem ambiente
    fica com a situação das paredes em volta; a demolir e temporário não somam (§14).
(p) Índices sobre a área de escritura quando digitada, senão a levantada (§14).
(q) Regras do Genérico (próprias, sem fonte): varanda/sacada/terraço coberto e ático não
    computáveis; quintal/pátio/terraço descoberto/piscina descobertos; jardim/gramado
    permeáveis; garagem fica computável (cada cidade decide) (§14).
(r) TO e TP mostrados em %, CA em número; limites do lote digitados no painel do quadro
    (§14).

## 12. Etapa 1 — como ficou (2026‑10‑27)
- **Núcleo** (`brasbim/core/intervention.py`, sem Qt): `SITUATIONS` (código, rótulo,
  `Status`), Pset `BrasBim_Intervencao.Situacao`; sem o Pset, a situação vem do `Status`
  comum (IFC de outra origem) ou é *A construir* — por isso uma obra nova não ganha Pset
  nenhum. O `Status` é escrito no `Pset_<Classe>Common` das classes que o têm no esquema
  (`STATUS_PSETS`: parede, porta, janela, laje, pilar, viga, cobertura e as águas,
  escada, guarda‑corpo, revestimento, proxy; conferido pelo teste PL01c). Objetos da
  biblioteca ficam só com o Pset próprio: o Pset comum deles é o do tipo.
- **Operação** `situation.set` (before/after `{"situation"}`; o `before` de quem já existia
  guarda também o `Status`, para o desfazer voltar exato). `set_situation` (uma
  transação para a seleção; o dono responde pelas peças: água → cobertura, peça → escada
  ou objeto).
- **Memória** `Document.element_situations` (como as camadas): desfazer uma exclusão
  devolve a situação; a derivação `sync` também repõe o `Status` quando um elemento
  regrava o Pset comum sem ele (escada, guarda‑corpo).
- **Copiar herda** (copiar, cópia em série, espelhar com cópia, dividir parede):
  `intervention.inherit`, com o mesmo pareamento das camadas, que virou
  `display_layers.copies`.
- **Interface**: campo **Situação** na seção Organização do painel (vale para a seleção
  toda, "vários" quando discordam); o antigo campo "Situação" das propriedades comuns,
  que só mexia no `Status`, saiu. Mini‑barra **Situação** (ícone `situation`) e Editar >
  Situação. Barra Opções de toda ferramenta de criação: botão **Situação dos novos
  elementos** (menu; vale até mudar, não vai para o IFC; `Session.new_situation`,
  `intervention.stamp_created` em `Session.run`). Selecionar semelhantes > Mesma situação.
- **Filtro de vista**: Exibir > Situação na vista (Projeto, Antes da obra, Depois da
  obra, Sem cores), guardado nas preferências (`situacao/vista`) e em
  `Document.situation_view`. O que o filtro tira entra nas ocultas
  (`display_layers.hidden_ids`): some da planta, do corte, do 3D e da seleção. Criar um
  elemento que o filtro esconde dá aviso em Mensagens. Vista salva guarda o filtro em
  `options.situation` (planta e corte) e o aplica ao desenhar (`saved_views.drawing`).
- **Cores** (perfil Genérico, `GENERIC_COLORS`; os outros perfis chegam na etapa 2): na
  vista Projeto, linhas de cada elemento e anotação pela cor da situação
  (`Plan.colors`, `Drawing.colors`); paredes cortadas agrupadas por tipo **e** situação,
  com a cor no traço e no preenchimento (`Region.tint`, `Edge.tint`); por camadas, a
  parede pintada não se divide em materiais. Temporário fica sem cor.
- **Decisões tomadas aqui** (revisar em (g)–(j)): projeto em que tudo é *A construir*
  (obra nova) não é pintado, para a obra nova não sair toda vermelha; Imprimir em preto
  tira as cores, mas a hachura por situação fica para a etapa 2 (vem do perfil); o
  filtro "Antes da obra" não mostra o temporário; o 3D só filtra, não pinta.
- Testes: PL01–PL03 (e PL01b, PL01c, PL02b) em `tests/test_projeto_legal.py`; PL01–PL03 da
  interface em `tests/test_interface_projeto_legal.py`.

## 13. Etapa 2 — como ficou (2026‑10‑28)
- **Perfis** em `brasbim/perfis/*.json` (`generico`, `sp-araras`, `sp-jacarei`,
  `sp-sao-paulo`, `pr-curitiba`), com `id`, `nome`, `versao`, `fonte` (documento e data de
  acesso), `cores` (situação → `cor`, `hachura`, `angulo`), `escalas` (`implantacao`,
  `plantas`, `cortes`, `fachadas`), `planta`, `quadro_de_areas`, `selo`, `notas` e `pdf`
  (`max_mb`, `carimbo_ultima_prancha`). Só o Genérico é completo; as cidades trazem só o
  que tem fonte e o resto vem do Genérico campo a campo (`municipal.resolve`), com a lista
  `herdado` das cores que não vieram da prefeitura (o diálogo mostra).
- **Núcleo** `brasbim/core/municipal.py` (sem Qt): cópia **resolvida** no Pset
  `BrasBim_PerfilMunicipal` do `IfcProject` (`Parametros`, JSON); sem o Pset vale o
  Genérico. Operação `municipal.set` (before/after `{"profile"}`); `choose` junta a cópia e
  `apply_scales` (escala das plantas em todos os pavimentos, `storey.edit`; de cortes e
  fachadas em todas as vistas, `view.edit`) numa transação. Corte e fachada novos nascem
  na escala do perfil (`view_scale`, em `annotations.commands.create_view`).
- **Cores e hachuras**: `intervention.marks` (cor e hachura por elemento) substitui as
  cores fixas; `Plan.hatches` e `Region.hatch`; as paredes cortadas agrupam por tipo, cor
  **e** hachura. Em Imprimir em preto a região da situação sai com a hachura do perfil em
  preto (cheia = fundo preto), espaçamento 0,10 m (`SITUATION_HATCH_SPACING`). Corte e
  fachada ainda sem hachura por situação (só a cor).
- **Interface**: Projeto > Perfil municipal… (`ui/municipal_dialog.py`): perfil (a cópia
  do projeto primeiro, depois os prontos), fonte, abas Cores e hachuras | Escalas e
  entrega | Notas e selo (selo só para ver; entra na folha mestra na etapa 4) e "Aplicar
  as escalas do perfil…".
- **Guardado para depois**: `planta: simplificada` (pacote seguinte), `quadro_de_areas`
  (etapa 3), `selo`, `notas` e `pdf` (etapa 4).
- Testes: PL04, PL09–PL12 em `tests/test_perfil_municipal.py`; PL04 (diálogo) e PL10
  (prancha em preto) em `tests/test_interface_perfil_municipal.py`.

## 14. Etapa 3 — como ficou (2026‑10‑29)
- **Núcleo** `brasbim/core/quantities/legal_areas.py` (sem Qt). Classificação de cada
  ambiente (`CLASSES`: computável, não computável, descoberta, permeável, fora do total)
  no estado do ambiente (`area_class`, `area_reason`; Pset `BrasBim_QuadroDeAreas`,
  `Classificacao` e `Motivo`), então copiar, desfazer e excluir já a levam; `None` = regra
  do perfil pelo nome (`classify`: nome igual ou começando pela palavra; `ate_m2`
  opcional). O perfil ganhou `quadro_de_areas.regras` (validadas em `municipal.validate`);
  com `piscina_a_parte` (Jacareí) a piscina vai para "Fora do total".
- **Lote**: Pset `BrasBim_Lote` do `IfcSite` (JSON: `deed_area`, `to_max`, `ca_max`,
  `tp_min`, em fração), operação `lot.edit`, `edit_lot`. Área levantada = contorno dos
  terrenos (`terrain_area`).
- **Cálculo** (`compute` → linhas com ambientes e memória): por pavimento, a área
  construída (face externa das paredes ∪ ambientes computáveis e não computáveis) é
  repartida por situação: ambientes primeiro, depois paredes; cômodo sem ambiente fica com
  a situação das paredes em volta (`rooms.wall_rings`, novo). Linhas: situações e área
  construída por pavimento, totais por situação, construída total, não computável (com o
  motivo), computável, descoberta, fora do total por motivo, terreno levantado e de
  escritura, projeção (união em planta de todos os pavimentos), área livre, permeável e
  os índices do perfil (TO e TP em %, CA em número) com limite e "atende".
- **Tabela**: categoria `legal_areas` ("Quadro de áreas (projeto legal)", modelo próprio em
  Nova tabela…; fora do "Em branco"), colunas fixas Descrição | Área | Índice | Limite |
  Atende | Memória de cálculo. `Row.memo`. Na aba a coluna da memória fica escondida e a
  memória da linha escolhida aparece embaixo da grade; clicar seleciona os ambientes;
  "Atende" em verde/vermelho do tema. CSV e XLSX levam a memória (XLSX escreve sim/não).
- **Painéis**: ambiente ganhou o grupo Quadro de áreas (Classificação, com "Pelo perfil:
  …" mostrando a regra; Motivo para não computável e fora do total). O painel do quadro
  mostra só nome, categoria e Dados do lote (área levantada, escritura, TO máx. %, CA
  máx., permeabilidade mín. %). Sugestões de nome do ambiente: + Quintal, Jardim, Piscina.
- **Ficou para depois**: a planta não mostra a classificação; quadro na prancha (etapa 4);
  piscina como objeto (hoje é um ambiente com o nome); quadros da NBR 12721.
- Testes: PL05, PL05b–PL05e em `tests/test_quadro_de_areas.py`; PL05 da interface em
  `tests/test_interface_quadro_de_areas.py`.
