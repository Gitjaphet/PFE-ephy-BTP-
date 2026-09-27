"""Armatures transversales (cadres) d'un poteau — EC2 §9.5.3 (rapport PFA §2.4)
et longueurs des barres pour la nomenclature de la planche de ferraillage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from flexcomp.core.barres import DIAMETRES_HA

COEF_RECOUVREMENT = 40   # longueur des barres longitudinales = hauteur totale + 40.Φ
COEF_CROCHET = 10        # crochet de cadre = 10.Φt


@dataclass(frozen=True)
class RepartitionCadres:
    """Cadres d'un poteau, longueurs en cm."""

    phi_t: int                  # diamètre des cadres (mm)
    s_max: int                  # espacement courant maximal (cm)
    s_crit: int                 # espacement réduit aux extrémités (cm)
    zones: tuple[tuple[int, int], ...]   # (nombre d'espacements, espacement) de bas en haut
    cote_a: float               # côté intérieur du cadre, dans le sens b (cm)
    cote_b: float               # côté intérieur du cadre, dans le sens h (cm)
    crochet: float              # longueur d'un crochet (cm)
    depart: float = 0.0         # distance plancher -> premier cadre (cm)

    @property
    def nombre(self) -> int:
        return sum(n for n, _ in self.zones) + 1

    @property
    def longueur(self) -> float:
        """Longueur développée d'un cadre (cm)."""
        return 2 * (self.cote_a + self.cote_b) + 2 * self.crochet

    def libelles(self) -> list[str]:
        """Libellés de la chaîne de cotes : « 5x9 », « 16x16 »…"""
        return [f"{n}x{s}" for n, s in self.zones]


def calculer_cadres(b_cm: float, h_cm: float, c_cm: float, hauteur_libre_cm: float,
                    phi_l_max: int, phi_l_min: int) -> RepartitionCadres:
    """Cadres selon l'EC2 §9.5.3 : Φt = max(6 ; Φl,max/4) ;
    s_max = min(20.Φl,min ; b ; 400 mm) ; s_crit = 0,6.s_max sur max(b ; h)
    à chaque extrémité."""
    phi_t = next(d for d in DIAMETRES_HA if d >= max(6.0, phi_l_max / 4))
    s_max = int(min(20 * phi_l_min / 10, min(b_cm, h_cm), 40.0))       # cm, arrondi inf.
    s_crit = max(int(0.6 * s_max), 5)
    l_crit = max(b_cm, h_cm)

    # Zone courante au pas s_max, zones d'extrémité au pas s_crit, de longueur >= l_crit ;
    # le reste (< 2.s_crit) devient la distance plancher -> premier cadre, cotée sur le plan.
    n_courant = max(int((hauteur_libre_cm - 2 * l_crit) // s_max), 0)
    while True:
        reste = hauteur_libre_cm - n_courant * s_max
        n_crit = int(reste // (2 * s_crit))
        if n_crit * s_crit >= l_crit or n_courant == 0:
            break
        n_courant -= 1
    depart = hauteur_libre_cm - n_courant * s_max - 2 * n_crit * s_crit
    zones = tuple(z for z in ((n_crit, s_crit), (n_courant, s_max), (n_crit, s_crit)) if z[0] > 0)

    return RepartitionCadres(
        phi_t=phi_t, s_max=s_max, s_crit=s_crit, zones=zones, depart=depart,
        cote_a=b_cm - 2 * c_cm, cote_b=h_cm - 2 * c_cm,
        crochet=COEF_CROCHET * phi_t / 10,
    )


def longueur_barre_longitudinale(hauteur_totale_cm: float, phi_mm: int) -> float:
    """Longueur d'une barre longitudinale (cm) = hauteur totale + recouvrement."""
    return hauteur_totale_cm + COEF_RECOUVREMENT * phi_mm / 10
