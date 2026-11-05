---
documento: Instalador do BrasBim para Windows (.exe)
requisito: item "instalador" da revisão geral (2026-10-30)
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-05
status: aprovado pela delegação do revisor (2026-11-05, "siga a sequência") e implementado
revisor: OTTO
---

# Instalador do BrasBim (Windows)

## 1. Propósito
Hoje quem testa usa a pasta "pendrive" (`scripts/pendrive/`), que na primeira vez baixa o
Python e as bibliotecas (5 a 10 min, com internet). O instalador entrega o BrasBim pronto:
um `BrasBim-<versão>-Setup.exe` que instala em poucos segundos, sem internet e sem pedir
administrador.

## 2. O que o usuário vê
- Assistente em português: boas‑vindas, licença (GPL/LGPL, `COPYING`), pasta (padrão
  `%LOCALAPPDATA%\Programs\BrasBim`, só para o usuário), atalhos (menu Iniciar sempre;
  Área de Trabalho marcada por padrão), associar arquivos `.ifc` ao BrasBim (desmarcado
  por padrão: muitos já têm outro visualizador), instalar e "Abrir o BrasBim agora".
- Desinstalar pelo Windows (Configurações > Aplicativos) ou pelo menu Iniciar; os
  projetos, as preferências e as cópias de segurança do usuário ficam.
- Instalar uma versão nova por cima atualiza (mesmo identificador do aplicativo).

## 3. Conteúdo
- O BrasBim congelado com o Python e as bibliotecas (PyInstaller, pasta única, sem
  console): `BrasBim.exe` com o ícone da logo e os dados de versão.
- Os recursos do pacote: ícones, fonte, logo, biblioteca de objetos, perfis municipais.
- O conversor de DWG (GNU LibreDWG, GPL), baixado na montagem por
  `scripts/baixar_libredwg.py` (SHA‑256 conferido), se ainda não estiver em
  `brasbim/vendor`.
- `COPYING`, `COPYING.LESSER`, `THIRD_PARTY_NOTICES.md` e `README.md` na pasta do
  programa.

## 4. Montagem
- `python instalador/construir.py`: (1) LibreDWG, (2) PyInstaller com
  `instalador/brasbim.spec` em `dist/BrasBim/`, (3) teste de fumaça do congelado
  (`BrasBim.exe --verificar`: abre o núcleo e a interface sem tela, cria um projeto com
  parede, exporta IFC 2x3 e GLB e sai com 0), (4) Inno Setup com
  `instalador/brasbim.iss`, se o `ISCC.exe` existir, em `dist/`.
- Versão: a do `pyproject.toml` (`brasbim.__version__`).
- `--verificar` é só da montagem; a janela não abre.

## 5. Testes
- **IN01** `app.verify()` (o que o `--verificar` roda) passa no ambiente de
  desenvolvimento.
- **IN02** O `.spec` e o `.iss` citam a versão e os arquivos que existem (ícone, licenças).
- **IN03** (montagem, manual) `dist/BrasBim/BrasBim.exe --verificar` sai com 0; o
  Setup instala, abre, desinstala.

## 6. Fontes
PyInstaller (documentação pública, pyinstaller.org; licença GPL com exceção para o
programa empacotado); Inno Setup (jrsoftware.org; licença própria, livre para uso
comercial). Base própria: `scripts/pendrive/COMO-MONTAR.md`, spec/ui 22 §8 (LibreDWG).
