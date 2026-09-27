"""
flexcomp — Calcul des éléments en béton armé travaillant en flexion composée
selon l'Eurocode 2 (NF EN 1992-1-1).

Projet de Fin d'Année — JEPHY Marinho, Master I Génie Civil,
École Supérieure Polytechnique d'Antsiranana (Promotion Mahery, 2025-2026).

Architecture :
    flexcomp.core        -> matériaux, constantes EC2, exceptions, unités
    flexcomp.sections     -> géométrie des sections (rectangulaire, etc.)
    flexcomp.elements     -> modèles de calcul par type d'élément
                             (poteau, voûte, mur porteur)
    flexcomp.results      -> structures de données immuables pour les résultats
    flexcomp.reporting     -> mise en forme des résultats (console, futur PDF/HTML)

Chaque `elements.*` est un objet qui reçoit une géométrie + des matériaux à la
construction, puis expose des méthodes de calcul pures (aucun état mutable
caché) retournant des dataclasses de `flexcomp.results`. Cette séparation
permet de brancher une interface graphique (PyQt6) ou une API web plus tard
sans toucher au moteur de calcul.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("flexcomp")
except PackageNotFoundError:  # package non installé, exécution depuis les sources
    __version__ = "0.1.0-dev"

__all__ = ["__version__"]
