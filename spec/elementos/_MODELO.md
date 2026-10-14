---
elemento: <Nome>
entidade_ifc: <IfcXxx / PredefinedType>
autor: <nome>          # não pode constar em cleanroom/REGISTRO-DE-ACESSO.md
data: <AAAA-MM-DD>
status: rascunho | em revisão | aprovado
revisor: <nome>
---

# <Nome>

## 1. Propósito
O que o elemento representa na construção, em uma ou duas frases.

## 2. Mapeamento IFC
- Entidade e `PredefinedType`
- Representações (`Axis`, `Body`, `FootPrint`…)
- Material (`IfcMaterialLayerSetUsage`, `IfcMaterialProfileSetUsage`…)
- Property sets (`Pset_XxxCommon`) e quantidades (`Qto_XxxBaseQuantities`)
- Relações (`IfcRelVoidsElement`, `IfcRelContainedInSpatialStructure`, `IfcRelConnects…`)

## 3. Parâmetros
| Parâmetro | Tipo | Unidade | Padrão | Regras |
|---|---|---|---|---|

## 4. Criação (interação do usuário)
Modos de entrada, pontos clicados, *snap*, pré‑visualização. Descrever com palavras próprias.

## 5. Edição
Alças, mover/esticar/rotacionar, edição numérica.

## 6. Comportamento e regras geométricas
Junções com outros elementos, recortes, prioridades, casos de borda (com figuras próprias).

## 7. Representação 2D
Planta (corte/projeção/acima do plano), corte e fachada, níveis de detalhe, conforme ABNT NBR 6492.

## 8. Quantitativos
Áreas, volumes, comprimentos e como são calculados.

## 9. Critérios de aceite (testes)
- [ ] Caso 1: entrada → resultado esperado (verificável por IFC exportado)

## 10. Fontes públicas
- buildingSMART IFC 4.3: <link da entidade>
- <outras, conforme cleanroom/FONTES.md>
