# Especificação funcional do BrasBim (lado limpo)

Software BIM open source, **IFC‑nativo**: o modelo em memória e o arquivo do projeto
seguem o esquema IFC 4.3.

**Regras:** ver `../cleanroom/PROCESSO.md`. Toda spec cita só fontes de `../cleanroom/FONTES.md`.
Nada de `_restrito/`.

## Estrutura
```
spec/
  00-visao-geral.md        escopo, público, princípios (IFC-nativo, open source, pt-BR)
  01-modelo-de-dados.md    entidades IFC usadas, identidade (GlobalId), histórico/undo
  02-geometria.md          representações, booleanos, níveis de detalhe
  03-documentacao.md       planta, corte, fachada, cotas, folhas/pranchas, PDF
  04-interoperabilidade.md IFC, BCF, IDS, DWG, PDF
  05-objetos-parametricos.md
  06-api-e-scripts.md
  elementos/
    _MODELO.md             modelo para cada tipo de elemento
    parede.md, laje.md, pilar.md, viga.md, cobertura.md, porta.md, janela.md, espaco.md ...
```

## MVP proposto
Parede, laje, pilar, viga, cobertura simples, porta e janela, espaço (ambiente), pavimentos,
planta/corte/fachada com cotas, pranchas em PDF, IFC de entrada e saída, quantitativos básicos.
