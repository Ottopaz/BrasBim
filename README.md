# BrasBim

Software BIM **open source** e **IFC‑nativo** (IFC 4.3), com foco no mercado brasileiro
(ABNT, pt‑BR).

> Estado: fundação (versão 0.0.1). Ainda não há funcionalidade para o usuário final.

## Instalação para desenvolvimento

Requer Python 3.12 ou superior.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,ui]"
pytest
brasbim          # abre o aplicativo
```

## Organização

| Pasta | Conteúdo | Licença |
|---|---|---|
| `brasbim/core` | Núcleo BIM sobre IfcOpenShell, sem Qt | LGPL‑3.0‑or‑later |
| `brasbim/ui` | Aplicativo desktop (PySide6) | GPL‑3.0‑or‑later |
| `tests/` | Testes pytest que validam o IFC gerado | LGPL‑3.0‑or‑later |
| `spec/` | Especificação funcional (requisitos e elementos) | — |
| `cleanroom/` | Processo clean‑room, fontes permitidas, declarações | — |

Cada arquivo de código traz seu identificador SPDX. Textos das licenças: `COPYING`
(GPL‑3.0) e `COPYING.LESSER` (LGPL‑3.0).

## Contribuir

Leia `CONTRIBUTING.md`. Em resumo: spec aprovada antes do código, só fontes públicas
(`cleanroom/FONTES.md`) e commits com `git commit -s`.
