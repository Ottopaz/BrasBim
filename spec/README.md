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
  ui/
    01-janela-e-ferramentas.md  janela principal, planta, 3D, primeiras ferramentas
  elementos/
    _MODELO.md             modelo para cada tipo de elemento
    parede.md, laje.md, pilar.md, viga.md, cobertura.md, porta.md, janela.md, espaco.md ...
```

## MVP proposto
Parede, laje, pilar, viga, cobertura simples, porta e janela, espaço (ambiente), pavimentos,
planta/corte/fachada com cotas, pranchas em PDF, IFC de entrada e saída, quantitativos básicos.

## Fontes
Este índice não especifica comportamento; cada spec tem a sua seção "Fontes", reunida em
`../cleanroom/REGISTRO-DE-FONTES.md`. A lista do MVP é decisão do projeto, com base em:
- **IFC 4.3** (buildingSMART, `https://github.com/buildingSMART/IFC4.x-development`):
  classes dos elementos do MVP (`IfcWall`, `IfcSlab`, `IfcColumn`, `IfcBeam`, `IfcRoof`,
  `IfcDoor`, `IfcWindow`, `IfcSpace`, `IfcBuildingStorey`).
- **CG**: conhecimento geral do projeto de arquitetura no Brasil (o que um projeto
  residencial precisa entregar).

Nenhum material de `_restrito/` nem de `tools/` foi usado.
