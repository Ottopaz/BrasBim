---
documento: Salvamento automático e recuperação após falha
requisito: RF-NUC-10
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-10-21
status: em revisão (implementado para teste, fluxo do MVP)
revisor: OTTO
---

# Salvamento automático e recuperação (RF-NUC-10)

## 1. Propósito
Se o BrasBim fechar sem salvar (falha, falta de luz, o computador desligou), o trabalho
das últimas horas não se perde: na próxima abertura o programa oferece a cópia de
segurança mais recente.

## 2. Cópia de segurança
- A cada intervalo (padrão **5 min**), se o projeto mudou desde a última cópia, o
  BrasBim grava uma **cópia de segurança** em IFC numa pasta própria do usuário
  (`recuperacao/`), **sem tocar no arquivo do projeto**: salvar continua sendo uma
  decisão do usuário.
- Ao lado da cópia, um JSON com o arquivo original (ou nenhum, se o projeto não tem
  nome), a hora da cópia e um **sinal de vida** renovado a cada minuto enquanto o
  BrasBim está aberto.
- A gravação é atômica (arquivo temporário e troca de nome): uma falha no meio da
  gravação não estraga a cópia anterior.
- A barra de estado mostra "Cópia de segurança às 14:05" por alguns segundos; nada vai
  para o painel Mensagens.
- **Arquivo > Salvamento automático**: Desligado, a cada 2, 5 (padrão) ou 10 minutos;
  guardado nas preferências.

## 3. Quando a cópia é apagada
Ao salvar o projeto, ao abrir outro ou criar um novo (depois da pergunta "Salvar as
alterações?") e ao fechar o BrasBim normalmente. Ou seja: só sobra cópia quando o
programa não fechou direito.

## 4. Recuperação
- Na abertura, o BrasBim procura cópias **órfãs**: as que não são da própria sessão e
  cujo sinal de vida tem mais de 3 minutos (assim a cópia de outra janela do BrasBim
  aberta ao mesmo tempo não é oferecida).
- Para a mais recente, pergunta: "O BrasBim fechou sem salvar *Casa.ifc* (cópia de
  21/10 às 14:05). Recuperar?" — **Recuperar**, **Descartar** ou **Depois** (fica para a
  próxima abertura).
- Recuperar abre a cópia como projeto **modificado** e com o nome do arquivo original
  (Salvar grava nele); a cópia passa a ser a da sessão atual. Projeto sem nome volta sem
  nome. Descartar apaga a cópia.
- O desfazer começa vazio no projeto recuperado.

## 5. Critérios de aceite (testes)
- [x] **SA01** A cópia só é gravada se o projeto mudou; reaberta, reproduz o modelo; o
      arquivo do projeto não muda.
- [x] **SA02** Salvar, abrir outro, novo e fechar normalmente apagam a cópia.
- [x] **SA03** Sessão que não fechou: outra sessão acha a cópia órfã, recupera o
      modelo com o nome original e marcado como modificado; a cópia não é oferecida de
      novo.
- [x] **SA04** Cópia com sinal de vida recente (outra janela aberta) não é órfã.
- [x] **SA05** Interface: o relógio grava a cópia no intervalo escolhido no menu; a
      pergunta da abertura recupera ou descarta.

## 6. Fontes
Conhecimento geral de software (CG): gravação atômica por troca de nome, arquivo de
sinal de vida. Nenhum material de `_restrito/` nem de `tools/` foi usado.

## 7. Pontos de revisão
(a) cópia separada do arquivo do projeto (não grava por cima dele);
(b) intervalo padrão de 5 min;
(c) a gravação roda na mesma linha de execução da interface: num projeto muito grande
    pode haver uma pausa curta a cada cópia (medir no teste de uso).
