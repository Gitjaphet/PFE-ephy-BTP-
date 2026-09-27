"""Point d'entrée de l'application graphique flexcomp.

Lancement :
    python3 -m flexcomp.gui        (package installé ou depuis la racine)
    python3 run_gui.py             (script de confort à la racine du projet)
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from flexcomp.gui.main_window import FenetrePrincipale
from flexcomp.gui.theme import feuille_de_style


def creer_application(argv: list[str] | None = None) -> QApplication:
    """Crée et configure l'objet QApplication.

    Isolé de `lancer()` pour que les tests puissent instancier l'application
    sans entrer dans la boucle d'événements.
    """
    application = QApplication(argv if argv is not None else sys.argv)
    application.setApplicationName("flexcomp")
    application.setApplicationDisplayName("flexcomp")
    application.setOrganizationName("ESP Antsiranana")
    application.setStyle("Fusion")  # base neutre, identique sur tous les OS
    application.setStyleSheet(feuille_de_style())
    return application


def lancer() -> int:
    """Lance l'application et retourne son code de sortie."""
    application = creer_application()
    fenetre = FenetrePrincipale()
    fenetre.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(lancer())
