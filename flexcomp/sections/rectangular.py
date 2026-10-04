"""Section rectangulaire en béton armé (poteau, voile, voûte).

Encapsule la géométrie brute (b, h, enrobage, diamètre de barre) et calcule
une fois pour toutes les grandeurs dérivées (d, d', Ac, rayon de giration)
utilisées par tous les modules `elements`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from flexcomp.core.exceptions import DonneesInvalidesError


@dataclass(frozen=True)
class SectionRectangulaire:
    """Section rectangulaire b x h avec une nappe d'armatures de chaque côté.

    Attributes:
        b: largeur de la section (m).
        h: hauteur totale de la section, dans le sens du moment étudié (m).
        enrobage_nominal: enrobage nominal cnom des armatures (m).
        diametre_barre: diamètre phi des barres longitudinales (m), utilisé
            pour positionner l'axe des nappes.
    """

    b: float
    h: float
    enrobage_nominal: float
    diametre_barre: float

    def __post_init__(self) -> None:
        for nom, valeur in (
            ("b", self.b),
            ("h", self.h),
            ("enrobage_nominal", self.enrobage_nominal),
            ("diametre_barre", self.diametre_barre),
        ):
            if valeur <= 0:
                raise DonneesInvalidesError(f"'{nom}' doit être strictement positif.")
        if self.d <= self.d_prime:
            raise DonneesInvalidesError(
                "Section trop mince : d <= d' compte tenu de l'enrobage et du diamètre."
            )

    @property
    def d(self) -> float:
        """Hauteur utile de la nappe tendue (fibre la plus éloignée du béton
        comprimé) : d = h - cnom - phi/2."""
        return self.h - self.enrobage_nominal - self.diametre_barre / 2

    @property
    def d_prime(self) -> float:
        """Position de la nappe comprimée depuis la fibre comprimée :
        d' = cnom + phi/2."""
        return self.enrobage_nominal + self.diametre_barre / 2

    @property
    def aire_beton(self) -> float:
        """Aire brute de béton Ac = b.h (m²)."""
        return self.b * self.h

    @property
    def rayon_giration_h(self) -> float:
        """Rayon de giration i = h/sqrt(12), pour le flambement dans le plan
        où h est la dimension fléchie."""
        return self.h / math.sqrt(12)

    @property
    def rayon_giration_b(self) -> float:
        """Rayon de giration i = b/sqrt(12), pour le flambement dans l'autre
        plan (vérification croisée d'un poteau, EC2 §9.5.1)."""
        return self.b / math.sqrt(12)

    @property
    def excentricite_limite(self) -> float:
        """Excentricité limite séparant section partiellement comprimée /
        entièrement tendue-comprimée : e_lim = h/2 - d' (rapport PFA §1.3, §3.3)."""
        return self.h / 2 - self.d_prime
