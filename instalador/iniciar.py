# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do BrasBim congelado (spec/ui 49): o mesmo de ``brasbim``."""

import sys

from brasbim.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
