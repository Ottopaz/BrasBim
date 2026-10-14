---
documento: Modelo de dados — operações serializáveis
requisito: RF-NUC-01, RF-NUC-02
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-14
status: rascunho (aguarda revisão)
---

# Operações serializáveis

Formato das operações que alteram o modelo IFC. Origem: rascunho da spec da parede
(`spec/elementos/parede.md` §5.2), já implementado em `brasbim/core/ops`.

## 1. Operação
Registro JSON, unidades SI (m, rad), coordenadas no plano do pavimento:

```json
{"op": "wall.edit", "id": "<GlobalId>", "before": {"base_offset": 0.0}, "after": {"base_offset": 0.1}}
```

| Campo | Uso |
|---|---|
| `op` | Nome da operação (`<objeto>.<ação>`) |
| `id` | GlobalId do objeto criado, alterado ou excluído |
| `data` | Estado completo (criar/excluir). Excluir guarda o estado para poder desfazer |
| `before` / `after` | Só os campos alterados (editar). `before` serve para detectar conflito: a edição é rejeitada se o estado atual for outro |

Toda operação é invertível sozinha: `create` ↔ `delete` (mesmo `data`), e `edit` troca
`before` com `after`.

## 2. Transação
`{"label": "Criar parede", "ops": [...]}`. Uma ação do usuário é uma transação, aplicada
inteira ou não aplicada (se uma operação falha, as anteriores são desfeitas). Desfazer
aplica a inversa (operações invertidas, em ordem reversa). O diário registra tudo o que
foi aplicado, inclusive desfazer e refazer. Reaplicado num modelo vazio com o mesmo
projeto, o diário reproduz o mesmo IFC.

## 3. Efeitos derivados
Não são registrados. Quem aplica a operação os recalcula: corpo, recortes de junção,
`IfcMaterialLayerSetUsage` e quantidades. Entidades derivadas recebem GlobalId
determinístico (UUID v5 do GlobalId do dono + papel, ex.: `"<parede>/pset/BrasBim_Parede"`),
para que refazer e reaplicar produzam os mesmos GlobalIds. *(decisão do projeto)*

## 4. Operações existentes
| `op` | Dados | Situação |
|---|---|---|
| `storey.create` / `.delete` / `.edit` | `name`, `elevation` | Provisória (sem spec de pavimento) |
| `wall_type.create` / `.delete` | `name`, `predefined_type`, `object_type`, `layers[]` | `create` provisória (RF-TIP-01) |
| `wall_type.edit` | `name`, `layers` | parede §5.2 |
| `wall.create` / `.delete` / `.edit` | `name`, `type`, `storey`, `path`, `ref_line`, `flip_layers`, `base_offset`, `top_mode`, `top_storey`, `top_offset`, `fixed_height`, `common` | parede §5.2 |
| `wall.split` / `wall.merge` | `path` (caminho original), `at` (ponto), `new` (GlobalId da 2ª parte) | parede §5.1, §5.2; `wall.merge` é só a inversa |
| `path_connection.create` / `.delete` | `relating`, `related` (GlobalIds das paredes), `relating_type`, `related_type` (`ATSTART` \| `ATEND` \| `ATPATH`) | parede §5.2, §6.2 |
| `opening.create` / `.delete` / `.edit` | `wall`, `kind` (`OPENING` \| `RECESS`), `distance`, `width`, `height`, `sill`, `depth`, `side` (`left` \| `right`) | parede §5.2, §6.3 |
| `filling.attach` / `.detach` | `id` = GlobalId do elemento que preenche; `opening` | parede §5.2, §6.3 |
| `door_type.create` / `.delete` / `.edit` | `name`, `predefined_type`, `operation_type`, `lining` (`thickness`, `depth`, `casing_thickness`, `casing_depth`, `threshold_thickness`), `panels[]` (`operation`, `position`, `width`, `depth`), `materials` (`lining`, `framing`, `glazing`), `defaults` (`width`, `height`, `base`), `variant` | porta §5.2 |
| `door.create` / `.delete` / `.edit` | `name`, `type`, `opens_to` (`left` \| `right`), `align` (`left_face` \| `axis` \| `right_face`), `offset`, `common` | porta §5.2 |

Caminho (`path`):
- Reta: `{"kind": "line", "start": [x, y], "end": [x, y]}`
- Arco: `{"kind": "arc", "start", "end", "radius", "ccw": bool, "large": bool}`.
  `large` distingue o arco maior que meia volta, porque raio + sentido + extremidades não
  bastam. *(decisão do projeto)*

`ref_line`: `axis` | `left_face` | `right_face`. `top_mode`: `storey` | `fixed`.
`common`: propriedades de `Pset_WallCommon` que diferem do padrão.

Aberturas: `id` = GlobalId do `IfcOpeningElement`. `distance` vai do início da parede ao
começo da abertura, ao longo do caminho; `sill` é a base da abertura em relação à base da
parede; `depth` e `side` (face de entrada) só valem para nicho. *(decisão do projeto)*
Excluir uma parede gera, na mesma transação e nesta ordem: `filling.detach`,
`door.delete`, `opening.delete`, `path_connection.delete` e `wall.delete` (spec da
parede §6.4, porta §6.4). Elementos de outra origem que preenchem a abertura só são
desligados.

Portas: `id` = GlobalId do `IfcDoor`. Largura, altura, distância e base são da abertura
(`opening.*`). Criar uma porta gera `opening.create`, `door.create` e `filling.attach`;
excluir gera `filling.detach`, `door.delete` e `opening.delete` (este último só se o vão
não for mantido). Posição, `OverallWidth`/`OverallHeight`, contenção, corpo e
quantidades da porta são derivados. `opens_to` é gravado no sentido do eixo x do
posicionamento da porta; `align` e `offset` no Pset `BrasBim_Esquadria`.

Dividir: `wall.split` encurta a parede até o ponto (projetado no caminho) e cria a 2ª
parte com o mesmo estado. Os comandos completam a ação na mesma transação: `opening.edit`
leva as aberturas depois do ponto para a nova parede, e `path_connection.*` refaz as
junções (inclusive a L colinear entre as duas partes). A inversa `wall.merge` exige que a
2ª parte já esteja sem aberturas e junções; a ordem invertida da transação garante isso.
*(decisão do projeto)*

Junções: `id` = GlobalId da `IfcRelConnectsPathElements`. Os comandos detectam as junções e geram
estas operações na mesma transação da criação, edição ou exclusão da parede.

## 5. Pendências
- Janelas (RF-ELE-06) entram na cascata como as portas.
- Reserva de elementos (RF-COL-02): uma operação declara quais GlobalIds exige reservados.
