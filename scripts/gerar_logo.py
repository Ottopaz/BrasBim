# SPDX-License-Identifier: GPL-3.0-or-later
"""Gera os arquivos da marca a partir de ``logoBrasBim.png`` (desenho do revisor, fundo
branco): logo com fundo transparente, o símbolo (o B, sem o nome) em vários tamanhos para
os ícones e ``brasbim.ico`` para o Windows. Saída em ``brasbim/ui/logo/``.

Uso: ``python scripts/gerar_logo.py`` (refazer sempre que a logo mudar).
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "logoBrasBim.png"
OUT = ROOT / "brasbim" / "ui" / "logo"
SYMBOL_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
LOGO_WIDTH = 480  # logo inteira (Sobre, README)
PAD = 0.04  # margem em volta do símbolo, fração do lado


def to_array(image: QImage) -> np.ndarray:
    image = image.convertToFormat(QImage.Format_RGBA8888)
    w, h = image.width(), image.height()
    data = np.frombuffer(image.constBits(), np.uint8, image.bytesPerLine() * h)
    return data.reshape(h, image.bytesPerLine())[:, : w * 4].reshape(h, w, 4).copy()


def to_image(rgba: np.ndarray) -> QImage:
    h, w, _ = rgba.shape
    data = np.ascontiguousarray(rgba)
    return QImage(data.data, w, h, w * 4, QImage.Format_RGBA8888).copy()


def unwhite(rgb: np.ndarray) -> np.ndarray:
    """Tira o fundo branco: a cor de cada pixel vira cor + transparência que, sobre o
    branco, dão o mesmo resultado (as frestas brancas entre as fitas ficam vazadas)."""
    c = rgb[..., :3].astype(np.float64) / 255.0
    alpha = 1.0 - c.min(axis=2)
    alpha[alpha < 0.03] = 0.0  # ruído perto do branco
    safe = np.where(alpha > 0, alpha, 1.0)[..., None]
    color = np.clip((c - (1.0 - alpha[..., None])) / safe, 0.0, 1.0)
    out = np.dstack([color, alpha]) * 255.0
    return np.round(out).astype(np.uint8)


def bbox(alpha: np.ndarray, rows: slice = slice(None)) -> tuple[int, int, int, int]:
    mask = alpha[rows] > 8
    ys, xs = np.nonzero(mask)
    start = rows.start or 0
    return xs.min(), ys.min() + start, xs.max() + 1, ys.max() + 1 + start


def symbol_rows(alpha: np.ndarray) -> slice:
    """Linhas do B: acima da maior faixa vazia entre o desenho e o nome."""
    filled = (alpha > 8).any(axis=1)
    ys = np.nonzero(filled)[0]
    gaps = [(ys[i + 1] - ys[i], ys[i]) for i in range(len(ys) - 1)]
    _, end = max(gaps)
    return slice(0, end + 1)


def square(rgba: np.ndarray) -> np.ndarray:
    h, w, _ = rgba.shape
    side = int(max(h, w) * (1 + 2 * PAD))
    out = np.zeros((side, side, 4), np.uint8)
    y, x = (side - h) // 2, (side - w) // 2
    out[y:y + h, x:x + w] = rgba
    return out


def scaled(image: QImage, width: int, height: int | None = None) -> QImage:
    return image.scaled(width, height or width, Qt.KeepAspectRatio,
                        Qt.SmoothTransformation)


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, images: list[QImage]) -> None:
    """ICO com uma imagem PNG por tamanho (Windows Vista em diante)."""
    blobs = [png_bytes(i) for i in images]
    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries = b""
    for image, blob in zip(images, blobs, strict=True):
        side = image.width()
        entries += struct.pack("<BBBBHHII", side % 256, side % 256, 0, 0, 1, 32, len(blob),
                               offset)
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(blobs))


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    source = QImage(str(SOURCE))
    if source.isNull():
        print(f"não achei {SOURCE}")
        return 1
    rgba = unwhite(to_array(source))
    OUT.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = bbox(rgba[..., 3])
    logo = to_image(rgba[y0:y1, x0:x1])
    scaled(logo, LOGO_WIDTH, 10_000).save(str(OUT / "logo.png"))
    rows = symbol_rows(rgba[..., 3])
    x0, y0, x1, y1 = bbox(rgba[..., 3], rows)
    symbol = to_image(square(rgba[y0:y1, x0:x1]))
    for size in SYMBOL_SIZES:
        scaled(symbol, size).save(str(OUT / f"simbolo-{size}.png"))
    write_ico(OUT / "brasbim.ico", [scaled(symbol, s) for s in ICO_SIZES])
    print(f"logo e símbolo gravados em {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
