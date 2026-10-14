# Retorno de uso

Observações de quem testa o BrasBim (`spec/ui/01-janela-e-ferramentas.md` §9).

- **Registrar:** no aplicativo, menu **Ajuda > Registrar observação…**. Escreva o que
  tentou fazer, o que esperava e o que aconteceu. A entrada vai para `AAAA-MM-DD.md`
  nesta pasta, junto com o contexto (ferramenta, seleção, últimas ações, mensagens).
- **Diários:** cada sessão grava o diário de transações em `diarios/` (fora do git). Ele
  reproduz a sessão exatamente e ajuda a achar a causa de um problema.
- **Erros inesperados:** o relatório vai para `diarios/erro-<data-hora>.md`.

Pode também escrever direto num arquivo `.md` desta pasta, à mão.
