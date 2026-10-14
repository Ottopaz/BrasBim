# BrasBim

Software BIM **open source** e **IFC‑nativo** (IFC 4.3 é o modelo de dados e o formato de arquivo), com foco no mercado brasileiro (ABNT, pt‑BR).

## Regra clean‑room (inegociável)
- **Nunca** ler, buscar, citar ou usar `_restrito/` (material de engenharia reversa; acesso bloqueado por hook em `.claude/`).
- Não fazer engenharia reversa de nenhum software proprietário. Nada de descompilar, desmontar ou inspecionar binários.
- Spec e código vêm só de fontes públicas: ver `cleanroom/FONTES.md`. Cada spec cita as fontes que usou.
- Não copiar textos, ícones, nomes de comandos ou layout de diálogos de outros softwares.
  Use vocabulário próprio ou do IFC.
- Sem leitura/escrita de `.pln`. Interoperabilidade via IFC, BCF, IDS.
- Processo completo: `cleanroom/PROCESSO.md`.

## Stack (decidida em 2026‑10‑14)
- **Python 3.12+**, app desktop multiplataforma
- **UI:** PySide6 (Qt 6) + viewport 3D em OpenGL
- **Núcleo BIM / IFC:** IfcOpenShell (o modelo em memória é IFC; `ifcopenshell.api` para editar)
- **Geometria:** OpenCascade via `ifcopenshell.geom`; booleanos 2D com Clipper2 (`pyclipr`)
- **Testes:** pytest. Todo recurso tem teste que valida o IFC gerado
- **Licença:** núcleo LGPL‑3.0‑or‑later, aplicativo GPL‑3.0‑or‑later (ver `cleanroom/PROCESSO.md` §5)
- Separar núcleo (`brasbim/core`, sem Qt) da interface (`brasbim/ui`), para que o núcleo seja testável e reutilizável

## Fluxo de trabalho
1. Especificar em `spec/` (modelo: `spec/elementos/_MODELO.md`) → revisão humana.
2. Implementar a partir da spec aprovada, com testes que verificam o IFC gerado.
3. Commits com `git commit -s` (DCO).

## Idioma
Documentação e UI em português (pt‑BR). Identificadores de código em inglês.
