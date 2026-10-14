# Registro de acesso ao material restrito (`_restrito/`)

Quem consta aqui é "lado sujo": pode revisar a spec, mas não deve ser autor principal
do código dos módulos correspondentes.

| Data | Pessoa / agente | O que acessou | Finalidade |
|---|---|---|---|
| 2026‑10‑14 | Otávio | Toda a análise do Archicad 27 (`_restrito/`) | Estudo de arquitetura |
| 2026‑10‑14 | Sessão Claude Code (análise) | Gerou todo o conteúdo de `_restrito/` | Engenharia reversa estática de metadados |
| 2026‑10‑14 | Ruff (linter), em sessão Claude Code de configuração | Uma linha de código de `tools/` (filtro de arquivos `.dll`/`.exe`, sem relação com BIM), lida por engano ao analisar o repositório | Nenhuma; acesso acidental. `tools/` foi excluída do ruff e do Git. O conteúdo não foi usado em spec nem em código |
