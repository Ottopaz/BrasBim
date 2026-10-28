# SPDX-License-Identifier: GPL-3.0-or-later
"""Põe o conversor de DWG (GNU LibreDWG, ``dwg2dxf``) em ``brasbim/vendor/libredwg``, para
o BrasBim já sair com ele (spec/ui 22 §8). Baixa o pacote oficial da versão fixada e
confere o SHA‑256; os binários não vão para o repositório.

Uso, na raiz do repositório: python scripts/baixar_libredwg.py
"""
import sys

from brasbim.core.imports import libredwg

if __name__ == "__main__":
    if not libredwg.supported():
        sys.exit("só há pacote pronto do LibreDWG para Windows; instale o pacote "
                 "libredwg do sistema")
    print(libredwg.install(libredwg.BUNDLED))
