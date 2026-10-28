# Pasta do BrasBim para pendrive

Para quem testa em outro PC, sem conhecimento técnico (2026-10-28). Monta uma pasta só
com o que roda o programa, a partir do último commit (nada fora do git, exceto o
conversor de DWG):

```sh
D="E:/Otavio/Nova pasta/BrasBim para pendrive/BrasBim"
rm -rf "$D" && mkdir -p "$D"
git archive --format=tar HEAD brasbim pyproject.toml README.md COPYING COPYING.LESSER \
    THIRD_PARTY_NOTICES.md feedback/README.md exemplos | tar -x -C "$D"
cp -r brasbim/vendor "$D/brasbim/"          # LibreDWG (scripts/baixar_libredwg.py)
cp scripts/pendrive/{"Abrir o BrasBim.bat",LEIA-ME.txt,requisitos.txt} "$D/"
```

- `Abrir o BrasBim.bat`: na 1ª vez instala o Python 3.14.3 (python.org, só para o
  usuário), cria o ambiente em `%LOCALAPPDATA%\BrasBim\ambiente` e um atalho na Área de
  Trabalho; depois só abre (`pythonw -m brasbim.ui.app`, com a pasta como diretório atual).
- O ambiente fica fora da pasta por causa do limite de 260 caracteres do Windows: o
  PySide6 tem caminhos muito fundos. Pelo mesmo motivo, só `PySide6_Essentials` (o
  BrasBim usa QtCore, QtGui, QtWidgets, QtOpenGL, QtOpenGLWidgets e QtSvg).
- `requisitos.txt` fixa as versões testadas; atualizar quando mudar o `.venv` de
  desenvolvimento ou entrar um módulo Qt novo.
- Os arquivos `.bat`, `.txt` precisam de fim de linha CRLF.
