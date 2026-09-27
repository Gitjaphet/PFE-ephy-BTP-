"""Longueur de flambement, élancement et élancement limite (EC2 §5.8).

Référence : rapport PFA Partie 1.5 (tableau des longueurs de flambement) et
§1.6 (élancement limite lambda_lim = 20.A.B.C/sqrt(n)).
"""

from __future__ import annotations

import math
from enum import Enum

from flexcomp.core.exceptions import DonneesInvalidesError


class ConditionAppui(Enum):
    """Conditions d'appui d'un élément isolé, cf. rapport PFA §1.5."""

    DEUX_ENCASTREMENTS = "deux_encastrements"      # l0 = 0,5.l
    ENCASTREMENT_ROTULE = "encastrement_rotule"      # l0 = 0,7.l
    DEUX_ROTULES = "deux_rotules"                     # l0 = l  (structure contreventée)
    ENCASTREMENT_LIBRE = "encastrement_libre"         # l0 = 2.l (console)
    PORTIQUE_NON_INTEGRE = "portique_non_integre"     # élément contreventé, EC2 (5.15)
    PORTIQUE_INTEGRE = "portique_integre"             # élément non contreventé, EC2 (5.16)


_COEFFICIENT_L0 = {
    ConditionAppui.DEUX_ENCASTREMENTS: 0.5,
    ConditionAppui.ENCASTREMENT_ROTULE: 0.7,
    ConditionAppui.DEUX_ROTULES: 1.0,
    ConditionAppui.ENCASTREMENT_LIBRE: 2.0,
}


def longueur_flambement(longueur_libre: float, condition: ConditionAppui) -> float:
    """Longueur de flambement l0 pour un élément isolé (EC2, tableau simplifié).

    Pour les portiques (contreventés ou non), utiliser
    `longueur_flambement_portique` à la place.
    """
    if longueur_libre <= 0:
        raise DonneesInvalidesError("La longueur libre doit être strictement positive.")
    return _COEFFICIENT_L0[condition] * longueur_libre


def longueur_flambement_portique(
    longueur_libre: float, k1: float, k2: float, contrevente: bool
) -> float:
    """Longueur de flambement pour un poteau de portique, EC2 Annexe H / cours INSA.

    Args:
        k1, k2: souplesses relatives en pied et en tête (k = 0 pour un
            encastrement parfait, ce qui n'est jamais réellement atteint —
            EC2 recommande k >= 0,1 en pratique).
        contrevente: True si la structure est contreventée (rotation
            empêchée par un système de contreventement), False sinon.
    """
    if longueur_libre <= 0:
        raise DonneesInvalidesError("La longueur libre doit être strictement positive.")

    if contrevente:
        l0 = 0.5 * longueur_libre * math.sqrt(
            (1 + k1 / (0.45 + k1)) * (1 + k2 / (0.45 + k2))
        )
    else:
        terme_a = 1 + 10 * k1 * k2 / (k1 + k2)
        terme_b = (1 + k1 / (1 + k1)) * (1 + k2 / (1 + k2))
        l0 = longueur_libre * math.sqrt(max(terme_a, terme_b))
    return l0


def rayon_giration_rectangle(dimension: float) -> float:
    """Rayon de giration i = dimension/sqrt(12) pour une section rectangulaire,
    dans la direction où `dimension` est la hauteur de la section (EC2 §5.8.3.2)."""
    if dimension <= 0:
        raise DonneesInvalidesError("La dimension doit être strictement positive.")
    return dimension / math.sqrt(12)


def elancement(l0: float, rayon_giration: float) -> float:
    """Élancement géométrique lambda = l0/i."""
    if rayon_giration <= 0:
        raise DonneesInvalidesError("Le rayon de giration doit être strictement positif.")
    return l0 / rayon_giration


def elancement_limite(n: float, a: float = 0.7, b: float = 1.1, c: float = 0.7) -> float:
    """Élancement limite en deçà duquel les effets du second ordre peuvent
    être négligés (EC2 §5.8.3.1) : lambda_lim = 20.A.B.C/sqrt(n).

    A, B, C ont des valeurs forfaitaires (0,7 ; 1,1 ; 0,7) sauf calcul plus
    précis (fluage, ferraillage, moments d'extrémité).

    Args:
        n: effort normal réduit, n = N_Ed/(Ac.fcd).
    """
    if n <= 0:
        raise DonneesInvalidesError(
            "L'effort normal réduit n doit être positif (élément comprimé)."
        )
    return 20.0 * a * b * c / math.sqrt(n)
