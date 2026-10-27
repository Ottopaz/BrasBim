---
documento: Projeto legal (projeto para licenciamentos)
requisito: roteiro do CONTEXTO, item 2; recomendações 1, 2, 3 e 8 de reports/Pesquisa Archicad Revit AutoCAD.md
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-27
status: em revisão (fluxo do MVP: implementar por etapas, §8)
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
2. **Perfil municipal** (§4): arquivo, cópia no IFC, diálogo, perfis prontos; cores e
   escalas aplicadas.
3. **Quadro de áreas** (§5) com memória de cálculo e índices.
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
- **PL06** Quadro de esquadrias agrupa 3 janelas J1 e 2 portas P1 com L × H e peitoril.
- **PL07** Memorial gera as seções na ordem, com os tipos de parede e camadas; seção
  editada não muda ao refazer.
- **PL08** PDF acima do limite do perfil Curitiba avisa.

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
