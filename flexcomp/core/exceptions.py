"""Exceptions métier de flexcomp.

Toutes les erreurs prévisibles du domaine héritent de FlexcompError, ce qui
permet à une future interface (GUI, API) de les attraper sans intercepter
des erreurs de programmation (TypeError, etc.) par accident.
"""


class FlexcompError(Exception):
    """Racine de toutes les exceptions métier de flexcomp."""


class DonneesInvalidesError(FlexcompError):
    """Levée quand une donnée d'entrée viole une hypothèse du modèle
    (géométrie négative, matériau hors norme, élancement hors domaine, etc.)."""


class ElancementExcessifError(FlexcompError):
    """Levée quand l'élancement dépasse un domaine de validité de la méthode
    simplifiée (ex : lambda > 86 pour un voile non armé, EC2 §12.6.5)."""


class ConvergenceError(FlexcompError):
    """Levée quand une recherche itérative (ex : section critique d'une
    voûte) ne converge pas dans les bornes attendues."""
