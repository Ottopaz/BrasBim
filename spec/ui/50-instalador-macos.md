---
documento: Instalador do BrasBim para macOS (.dmg)
requisito: pedido do revisor (2026-11-06, "faça um instalador para mac"); par da spec/ui 49
autor: Claude Code (sessão limpa, sem acesso a _restrito/)
data: 2026-11-06
status: em revisão (implementado; falta testar num Mac de verdade)
revisor: OTTO
---

# Instalador do BrasBim (macOS)

## 1. Propósito
Entregar o BrasBim pronto para quem usa Mac, como o `Setup.exe` faz no Windows (spec/ui
49): uma imagem de disco `BrasBim-<versão>-macOS-<arquitetura>.dmg` com o `BrasBim.app`,
sem precisar de Python nem de internet. Desde 2026‑11‑06 o CI roda a suíte inteira no
macOS (verde no 3.12 e no 3.13), o que dá base para isto.

## 2. O que o usuário vê
- Abre o `.dmg`: o BrasBim, um atalho para Aplicativos, as licenças e um `LEIA-ME.txt`
  em português. Instala arrastando o BrasBim para Aplicativos.
- **Primeira abertura (sem assinatura da Apple):** o macOS avisa que não pode verificar o
  desenvolvedor. O LEIA-ME explica: abrir uma vez, depois Ajustes do Sistema >
  Privacidade e Segurança > "Abrir Mesmo Assim" (ou `xattr -dr com.apple.quarantine`).
  No macOS 15 o atalho antigo (botão direito > Abrir) deixou de servir.
- Barra de título sempre clara (`NSRequiresAquaSystemAppearance`), como o tema.
- Desinstalar: arrastar o BrasBim de Aplicativos para o Lixo; projetos e preferências
  ficam.

## 3. Conteúdo
- O BrasBim congelado (PyInstaller, `BrasBim.app`), com o ícone `brasbim.icns`
  (gerado por `scripts/gerar_logo.py` junto do `.ico`, PNG de 16 a 512 px).
- Os recursos do pacote (ícones, fonte, logo, biblioteca, perfis) e as licenças.
- **Sem conversor de DWG:** o LibreDWG do BrasBim é o binário do Windows. No Mac a
  exportação já cai em "Gravar em DXF" e a importação aceita DXF.
- Duas imagens: **Apple Silicon** (arm64) e **Intel** (x86_64). Uma por arquitetura, em
  vez de um binário universal, porque as bibliotecas (IfcOpenShell, PySide6) vêm do pip
  numa arquitetura só.

## 4. Montagem
- Precisa de um Mac. Esta máquina de desenvolvimento é Windows, então a montagem fica no
  GitHub Actions: `.github/workflows/instalador-mac.yml`, em `macos-latest` (arm64) e
  `macos-15-intel`. Roda à mão (Actions > Instalador macOS > Run workflow), quando a
  receita muda e em etiquetas `v*` (aí anexa os `.dmg` ao lançamento, como pré‑lançamento).
- `python instalador/construir_mac.py`:
  1. PyInstaller com `instalador/brasbim_mac.spec`, que gera `dist/BrasBim.app`;
  2. `BrasBim.app/Contents/MacOS/BrasBim --verificar`, o mesmo teste de fumaça do
     Windows (núcleo e interface sem tela, IFC 2x3 e GLB, logo);
  3. `codesign --verify` da assinatura *ad hoc* que o PyInstaller põe (sem nenhuma
     assinatura, o Apple Silicon não abre);
  4. `hdiutil create` (UDZO) e `hdiutil verify`.
- Identificador `io.github.ottopaz.brasbim`; versão a do `pyproject.toml`.

## 5. Pontos para o revisor
- (a) **Assinatura e autenticação da Apple.** Sem elas, a primeira abertura exige o passo
  do §2. Para tirar o aviso é preciso uma conta Apple Developer (US$ 99/ano), um
  certificado "Developer ID Application" e a autenticação (`notarytool`) no workflow, com
  os segredos no GitHub. Decisão do revisor.
- (b) **Abrir `.ifc` com clique duplo no Finder:** o macOS manda o arquivo por evento
  (`QFileOpenEvent`), não pela linha de comando; o BrasBim ainda não trata. Sem isso a
  associação não foi declarada no `Info.plist`. Proposta: tratar o evento e declarar
  `.ifc` como "Alternativo" (não toma o lugar de outro visualizador).
- (c) **DWG no Mac:** montar o LibreDWG para macOS (compilar no CI) ou ficar só no DXF.
- (d) **Validar num Mac de verdade:** o 3D (OpenGL no macOS fica no perfil 2.1 de
  compatibilidade; linhas com mais de 1 px podem sair finas), a barra de ferramentas
  (o UI34 falha no macOS: a doca não estreita para uma coluna), atalhos (Ctrl ↔ ⌘) e
  menus (o Qt leva Sobre/Preferências para o menu do aplicativo).

## 6. Testes
- **IN04** A receita do Mac cita o que existe (`brasbim.icns`, `iniciar.py`, licenças),
  o identificador e a versão; o nome do `.dmg` traz versão e arquitetura; o LEIA-ME diz
  como abrir sem assinatura e que DWG é só no Windows; o `.icns` é válido (cabeçalho,
  tamanho total, blocos PNG de 16 a 512).
- **IN05** (montagem, no CI) `construir_mac.py` passa: `--verificar` sai com 0,
  `codesign --verify` e `hdiutil verify` passam, o `.dmg` sai como artefato.
- **IN06** (manual, num Mac) abrir o `.dmg`, arrastar, abrir pelo passo do §2, criar uma
  parede, ver o 3D, salvar e exportar.

## 7. Fontes
PyInstaller (pyinstaller.org: "macOS-specific options", `BUNDLE`, `info_plist`, assinatura
ad hoc); Apple, documentação pública de `Info.plist`
(`NSRequiresAquaSystemAppearance`, `LSApplicationCategoryType`), `hdiutil(1)`,
`codesign(1)`, formato ICNS (tipos `icp4`–`ic09` com PNG); GitHub Actions (executores
`macos-latest`, `macos-15-intel`). Base própria: spec/ui 49.
