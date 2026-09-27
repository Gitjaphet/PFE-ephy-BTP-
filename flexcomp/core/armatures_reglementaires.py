"""Sections d'armatures minimales et maximales réglementaires (EC2 §9.5, §9.6, §7.3).

Regroupées ici pour éviter que chaque `elements.*` ne recopie les mêmes
formules avec de subtiles variantes.
"""

from __future__ import annotations

from flexcomp.core.materials import Acier, Beton


def as_min_flexion(b: float, d: float, beton: Beton, acier: Acier) -> float:
    """Section minimale de flexion (EC2 §9.2.1.1) :
    As,min = max(0,26.fctm/fyk . b.d ; 0,0013.b.d).

    b, d en mètres -> As en mm² (b.d en m² x 1e6 pour repasser en mm²).
    """
    terme1 = 0.26 * beton.fctm / acier.fyk * b * d
    terme2 = 0.0013 * b * d
    return max(terme1, terme2) * 1e6


def as_min_poteau(N_Ed_kN: float, Ac: float, acier: Acier) -> float:
    """Section minimale totale d'armatures longitudinales d'un poteau
    (EC2 §9.5.2) : As,min = max(0,10.N_Ed/fyd ; 0,002.Ac).

    N_Ed en kN, Ac en m² -> As en mm².
    """
    terme1 = 0.10 * (N_Ed_kN * 1000.0) / acier.fyd  # mm²
    terme2 = 0.002 * Ac * 1e6  # mm²
    return max(terme1, terme2)


def as_max_poteau(Ac: float, hors_recouvrement: bool = True) -> float:
    """Section maximale d'armatures longitudinales d'un poteau (EC2 §9.5.2) :
    0,04.Ac hors recouvrement, 0,08.Ac au droit des recouvrements."""
    coefficient = 0.04 if hors_recouvrement else 0.08
    return coefficient * Ac * 1e6


def as_min_voile_flexion(b: float, d: float, beton: Beton, acier: Acier) -> float:
    """Section minimale de flexion pour un voile/voûte armé — même formule
    que `as_min_flexion` (rapport PFA §4.7, §4.8), rappelée séparément pour
    la lisibilité du code appelant."""
    return as_min_flexion(b, d, beton, acier)
