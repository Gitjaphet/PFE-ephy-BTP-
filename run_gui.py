#!/usr/bin/env python3
"""Lance l'interface graphique de flexcomp.

Script de confort permettant de démarrer le logiciel sans installer le
package :

    python3 run_gui.py

Si le package est installé (`pip install -e .`), `python3 -m flexcomp.gui`
fait exactement la même chose.
"""

import sys
from pathlib import Path

# Permet l'exécution depuis les sources, sans installation préalable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from flexcomp.gui.app import lancer
except ImportError as erreur:
    if "PyQt6" in str(erreur):
        print(
            "PyQt6 n'est pas installé.\n\n"
            "Installez-le avec :\n"
            "    pip install PyQt6\n"
            "ou, si vous utilisez le venv du projet :\n"
            "    pip install -e \".[gui]\"",
            file=sys.stderr,
        )
        sys.exit(1)
    raise

if __name__ == "__main__":
    sys.exit(lancer())
