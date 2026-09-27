"""Interface graphique PyQt6 de flexcomp.

Ce sous-package dépend du moteur de calcul (`flexcomp.core`,
`flexcomp.elements`), mais jamais l'inverse : le moteur reste utilisable
sans PyQt6 installé. La frontière est tenue par `flexcomp.gui.adaptateur`,
seul endroit où les unités de saisie sont converties vers celles du moteur.
"""

from flexcomp.gui.app import creer_application, lancer

__all__ = ["creer_application", "lancer"]
