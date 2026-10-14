# Como contribuir com o BrasBim

## 1. Regras clean‑room

O BrasBim é desenvolvido em clean‑room. Antes de contribuir, leia:

- `cleanroom/PROCESSO.md`: o processo e o porquê
- `cleanroom/FONTES.md`: fontes permitidas e proibidas
- `cleanroom/DECLARACAO-CONTRIBUIDOR.md`: declaração a incluir no seu primeiro PR

Nunca use material de engenharia reversa, código ou textos de software proprietário.

## 2. Fluxo

1. **Spec:** escreva ou atualize a especificação em `spec/` (modelo:
   `spec/elementos/_MODELO.md`), citando as fontes públicas.
2. **Revisão:** a spec precisa estar com `status: aprovado` antes da implementação.
3. **Código:** núcleo em `brasbim/core` (sem Qt), interface em `brasbim/ui`.
4. **Testes:** todo recurso tem teste pytest que valida o IFC gerado.
5. **Commit:** `git commit -s` (DCO 1.1, https://developercertificate.org).
   O CI recusa PRs com commits sem `Signed-off-by`.

## 3. Estilo

- Documentação e interface em português (pt‑BR); identificadores de código em inglês.
- `ruff check .` sem erros.
- Cabeçalho SPDX em todo arquivo de código: `LGPL-3.0-or-later` em `brasbim/core` e
  `tests/`, `GPL-3.0-or-later` em `brasbim/ui`.
