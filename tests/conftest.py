"""Configuration commune aux tests.

Force le rendu Qt « hors écran » : la suite de tests doit pouvoir tourner
sur une machine sans serveur graphique (intégration continue, connexion SSH,
conteneur), sans qu'aucune fenêtre ne s'ouvre réellement.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
