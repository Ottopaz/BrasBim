# Imagens e modelos do site

Como refazer o que o site (`site/`) mostra quando o programa mudar. Tudo sai do próprio
BrasBim: modelo, capturas de tela e gravações. Rode da raiz do repositório, com o `.venv`.
As capturas abrem janelas do programa na tela por alguns minutos.

## Torre de 30 pavimentos (abertura e cartões)

```sh
python exemplos/torre_parametrica.py saida 30                 # ~10 min, grava saida/torre.ifc
python scripts/compactar_glb.py saida/torre.ifc site/modelos/torre.glb   # ~17 min, ~3,5 MB
```

As imagens fixas da torre (`site/imagens/torre-*.jpg`) são o próprio `site/torre.js`
fotografado com o site servido localmente (`python -m http.server 8765` dentro de `site/`)
e um navegador sem janela. Parâmetros da página: `?parado&limpo&vista=frente|aerea|baixo|topo`
e `&noite`. Exemplo com o Chrome:

```sh
chrome --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars \
  --virtual-time-budget=30000 --window-size=1600,1000 --screenshot=torre-aerea.png \
  "http://127.0.0.1:8765/?parado&limpo&vista=aerea"
```

`torre-abertura.jpg` usa `--window-size=1800,920` e `vista=frente` (a proporção da abertura).

## Projeto em equipe (`equipe.gif`, `equipe.jpg`)

```sh
python scripts/site/gif_equipe.py saida/torre.ifc quadros/gifeq 15
```

Duas janelas no mesmo processo: Ana compartilha (porta 47913, só nesta máquina), Bruno
entra, os dois editam o Pavimento 15. O nome do computador aparece como "escritorio".

## Assistente (`assistente.gif`, `assistente.jpg`)

```sh
python scripts/site/captura_assistente.py quadros/ia "Faça uma casa de campo 3 quartos, 1 suíte, 1 banheiro, sala, cozinha, lavanderia, varanda e piscina."
```

Precisa do Claude Code instalado (`claude`) e usa a conta de quem roda. Salva um quadro por
segundo e o diário da sessão em `quadros/ia/diarios/`.

Depois das duas gravações:

```sh
python scripts/site/montar_gifs.py quadros site/imagens        # precisa do Pillow
```

## Prancha da casa de campo (`prancha.jpg`)

```sh
python scripts/site/prancha.py quadros/ia/diarios/<sessao>.json quadros/prancha
```

Refaz a casa do Assistente pelo diário, cota as paredes do contorno, cria o corte A, monta
a prancha A3 em 1:100 (carimbo com dados de exemplo) e exporta o PDF. A imagem é a página
do PDF (`quadros/prancha/prancha.png`), reduzida para 1600 px de largura.
