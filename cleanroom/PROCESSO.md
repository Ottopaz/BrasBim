# Processo clean‑room do BrasBim

> Objetivo: criar um software BIM **open source** e **IFC‑nativo** sem copiar expressão
> protegida de nenhum software proprietário (em especial o Archicad).
>
> Este documento não é parecer jurídico. Ele reduz o risco e documenta a boa‑fé, mas
> **não substitui um advogado** de propriedade intelectual/software, que deve revisá‑lo
> antes da primeira versão pública.

---

## 1. Por que clean‑room funciona

| O que a lei protege | O que a lei **não** protege |
|---|---|
| **Código** (fonte e objeto) como obra literária. Lei 9.609/98, art. 2º | **Ideias, procedimentos, sistemas, métodos**. Lei 9.610/98, art. 8º, I |
| Expressão específica: textos, ícones, layout gráfico, manuais | **Funcionalidade.** Lei 9.609/98, art. 6º, III: a semelhança entre programas *"por força das características funcionais de sua aplicação, da observância de preceitos normativos e técnicos, ou de limitação de forma alternativa para a sua expressão"* não é ofensa |
| **Marcas** (Archicad, Graphisoft, BIMx…). Lei 9.279/96 | Padrões abertos (IFC/ISO 16739, BCF, IDS) |
| **Patentes** (podem existir em outros países) | Conhecimento geral de arquitetura e construção |
| **Contrato** (EULA): obriga quem o aceitou | |

Clean‑room é a forma de **provar** que o código novo nasceu da funcionalidade e de
fontes públicas, e não de cópia.

## 2. Papéis

```
 ┌────────────────────┐   especificação funcional    ┌──────────────────┐   revisão   ┌──────────────────┐
 │  LADO SUJO         │ ───(sem código, sem nomes ──►│  REVISOR          │ ──────────► │  LADO LIMPO      │
 │  (contaminado)     │    internos, só fontes       │  (idealmente      │  spec/      │  (implementação) │
 │  viu _restrito/    │    públicas citadas)         │   jurídico)       │  aprovada   │  nunca viu       │
 └────────────────────┘                              └──────────────────┘             │  _restrito/      │
                                                                                     └──────────────────┘
```

**Recomendação para o BrasBim:** como o projeto é open source e a funcionalidade do
Archicad é amplamente documentada em público, **a especificação deve ser escrita só a
partir de fontes públicas** (`FONTES.md`). Nesse caso a análise em `_restrito/` nem é
necessária para o produto. Ela fica arquivada como estudo e não alimenta a spec.

- **Quem já viu `_restrito/`** (até agora: Otávio e a sessão de IA que fez a análise)
  pode **revisar** a spec. Não deve ser o autor principal do código de um módulo que
  corresponda ao que viu.
- **Assistentes de IA:** use sessões novas, abertas **sem acesso a `_restrito/`**, para
  escrever spec e código. O histórico da sessão de análise conta como contaminado.
- **Usar o Archicad como usuário não contamina.** Saber como uma ferramenta se
  comporta (o que ela faz) é conhecimento funcional livre. O proibido é olhar
  *como foi implementada* (binários, símbolos, código).

## 3. Regras de ouro

1. **Nada de material de `_restrito/` em `spec/` ou no código**: nomes de classes
   internas, estruturas de arquivo, símbolos, schemas extraídos de binários.
2. **Toda decisão da spec cita a fonte pública** (seção "Fontes" de cada documento).
3. **Vocabulário próprio ou do IFC.** Escreva "IfcSlab / laje", não nomes internos
   de outro software.
4. **Não copie textos, ícones, nomes de comandos, organização de menus ou diálogos.**
   Aceita‑se a convenção da indústria (ex.: "Parede", "Laje", "Corte").
5. **Sem formato `.pln`.** O BrasBim lê e grava **IFC** como formato nativo. Projetos
   do Archicad entram via exportação IFC feita pelo próprio usuário.
6. **Marcas:** não use "Archicad", "Graphisoft" nem "GDL" no nome do produto, em
   logos ou em marketing. Só se admite o uso nominativo e factual ("importa IFC
   exportado do Archicad"). Antes de lançar, faça busca de anterioridade do nome
   "BrasBim" no INPI.
7. **Patentes:** antes de distribuir fora do Brasil, faça uma busca básica de patentes
   da Graphisoft/Nemetschek sobre recursos que pretende reproduzir. No Brasil,
   programa de computador em si não é patenteável (Lei 9.279/96, art. 10, V), mas
   isso não vale para outros países.
8. **Não parar de seguir o EULA.** Quem aceitou o contrato do Archicad não faz mais
   engenharia reversa dele. A análise já feita se limitou a metadados e foi encerrada.
9. **Bibliotecas de terceiros** só com licença compatível (§5).

## 4. Rastreabilidade

- Cada documento em `spec/` tem cabeçalho com autor, data e **fontes públicas**.
- Cada contribuição de código vem com assinatura **DCO** e uma declaração clean‑room
  (`CONTRIBUTING.md`, modelo em `DECLARACAO-CONTRIBUIDOR.md`).
- Acesso a `_restrito/` fica registrado em `REGISTRO-DE-ACESSO.md`.
- O histórico do Git é a prova de autoria e de datas. Não reescreva o histórico.

## 5. Licença do projeto (recomendação)

| Opção | Quando escolher |
|---|---|
| **LGPL‑3.0‑or‑later** (núcleo) | Permite que empresas usem a biblioteca BIM e protege melhorias no núcleo. Compatível com OpenCascade (LGPL‑2.1 + exceção) e IfcOpenShell (LGPL‑3.0) |
| **GPL‑3.0‑or‑later** (aplicativo) | Obrigatório se derivar código do Bonsai (ex‑BlenderBIM) ou do FreeCAD BIM |

Sugestão: **núcleo LGPL‑3.0 + aplicativo GPL‑3.0**, ou tudo GPL‑3.0 se partirem do Bonsai.
Biblioteca de objetos: **CC BY 4.0**. Itens CC BY 4.0 da biblioteca do Archicad só
entram após verificar a licença de cada arquivo e com atribuição.
⚠️ Itens da biblioteca do Archicad vêm de `.lcf` extraído e devem ser tratados à parte,
com análise jurídica própria. Na dúvida, criem os objetos do zero.

## 6. Checklist antes da 1ª versão pública

- [ ] Advogado revisou este processo, a licença e o nome
- [ ] Busca INPI do nome/marca
- [ ] `_restrito/` fora de qualquer repositório remoto (conferir com `git ls-files`)
- [ ] Todas as specs com fontes públicas citadas
- [ ] Todos os commits com DCO
- [ ] Nenhum ícone, texto ou diálogo copiado (revisão visual)
- [ ] `THIRD_PARTY_NOTICES` com todas as dependências e licenças
