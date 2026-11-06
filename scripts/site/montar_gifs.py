# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta os GIFs do site a partir dos quadros gravados.

Uso: python scripts/site/montar_gifs.py pasta_dos_quadros site/imagens
(a pasta tem ia/q*.png, de captura_assistente.py, e gifeq/a*.png e b*.png, de gif_equipe.py).
Precisa do Pillow."""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

S = Path(sys.argv[1])
I = Path(sys.argv[2])
negrito = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)


def parecidos(a, b):
    d = ImageChops.difference(a.convert("L").resize((160, 90)), b.convert("L").resize((160, 90)))
    return max(d.getextrema()) < 12


def salvar_gif(quadros, duracoes, destino, cores=128):
    pal = [q.convert("RGB").quantize(colors=cores, method=Image.MEDIANCUT, dither=Image.NONE)
           for q in quadros]
    pal[0].save(destino, save_all=True, append_images=pal[1:], duration=duracoes, loop=0,
                optimize=True, disposal=1)
    print(destino, len(pal), round(Path(destino).stat().st_size / 1e6, 2), "MB")


# --- Assistente: janela inteira, quadros repetidos viram um quadro curto -------------------
arqs = sorted((S / "ia").glob("q*.png"))
quadros, dur = [], []
for f in arqs:
    im = Image.open(f).convert("RGB").resize((1280, 720), Image.LANCZOS)
    if quadros and parecidos(quadros[-1], im):
        dur[-1] = min(dur[-1] + 150, 900)
        continue
    quadros.append(im)
    dur.append(450)
dur[0] = 1500
dur[-1] = 5000
salvar_gif(quadros, dur, I / "assistente.gif")


# --- Equipe: as duas janelas lado a lado, só a planta e o painel Equipe --------------------
def recorte(arq, nome, cor):
    w = Image.open(arq).convert("RGB")
    planta = w.crop((418, 98, 1285, 915))          # planta
    equipe = w.crop((1292, 640, 1600, 980))         # painel Equipe
    alto = 56
    out = Image.new("RGB", (planta.width + equipe.width + 12, planta.height + alto), "white")
    d = ImageDraw.Draw(out)
    d.ellipse((16, 16, 40, 40), fill=cor)
    d.text((52, 12), nome, font=negrito, fill="#26222a")
    out.paste(planta, (0, alto))
    out.paste(equipe, (planta.width + 12, alto + planta.height - equipe.height))
    return out


a_arqs = sorted((S / "gifeq").glob("a*.png"))
b_arqs = sorted((S / "gifeq").glob("b*.png"))
quadros = []
for fa, fb in zip(a_arqs, b_arqs):
    a = recorte(fa, "Computador da Ana", "#E05A1A")
    b = recorte(fb, "Computador do Bruno", "#1F6FC4")
    pad = 20
    c = Image.new("RGB", (a.width * 2 + pad * 3, a.height + pad * 2), "#efe6ee")
    c.paste(a, (pad, pad))
    c.paste(b, (a.width + pad * 2, pad))
    quadros.append(c.resize((1600, round(1600 * c.height / c.width)), Image.LANCZOS))
dur = [700] * len(quadros)
dur[0] = 1500
dur[-1] = 4000
salvar_gif(quadros, dur, I / "equipe.gif", cores=96)
quadros[-1].save(I / "equipe.jpg", quality=86, optimize=True)
print("equipe", quadros[-1].size)
