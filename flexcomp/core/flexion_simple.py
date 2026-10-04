"""Dimensionnement par assimilation à la flexion simple (EC2, méthode consacrée).

Cette méthode est le cœur commun aux trois éléments du projet (poteau, voûte,
voile) : le rapport PFA le souligne explicitement (§1.7, §3.3, §4.2).
Elle est donc factorisée ici une seule fois, et chaque `elements.*` l'appelle
avec sa propre géométrie/sollicitation plutôt que de la ré-implémenter.

Référence : cours INSA Rennes, Béton armé Chap. 11 §11.5.1-11.5.4 [2, p.96-97].
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from flexcomp.core.materials import Acier, Beton, EPS_CU2

# Moment réduit ultime en pivot B (frontière simple/double armature), pour
# un acier B500 et un béton <= C50/60 (valeur usuelle mu_lu ~ 0,372, cf.
# rapport PFA §1.4.3). Recalculé proprement à partir de alpha_AB si besoin.
MU_LU_DEFAUT = 0.372


@dataclass(frozen=True)
class ResultatFlexionSimple:
    """Sortie du calcul d'armatures en flexion simple équivalente."""

    mu_ed: float             # moment réduit sollicitant
    mu_lu: float              # moment réduit limite (frontière pivot A/B - double armature)
    armature_double: bool      # True si As2 (comprimée) est nécessaire
    alpha_u: float
    z_c: float                 # bras de levier (m)
    As1_flexion_simple: float   # mm² ou mm²/m
    As2_flexion_simple: float   # mm² ou mm²/m


def moment_reduit_limite(beton: Beton, acier: Acier) -> float:
    """Moment réduit limite mu_AB à la frontière pivot A / pivot B :
    mu_AB = 0,8.alpha_AB.(1 - 0,4.alpha_AB), alpha_AB = eps_cu2/(eps_cu2+eps_yd).

    (Rapport PFA, formulaire poteau §2.6.) Utiliser cette fonction plutôt que
    la constante MU_LU_DEFAUT si l'acier ou le béton s'écarte du cas usuel
    C25/30 + B500.
    """
    alpha_ab = EPS_CU2 / (EPS_CU2 + acier.eps_yd)
    return 0.8 * alpha_ab * (1 - 0.4 * alpha_ab)


def calcul_flexion_simple(
    moment_reduit_ed: float,
    b: float,
    d: float,
    d_prime: float,
    beton: Beton,
    acier: Acier,
    mu_lu: float | None = None,
) -> ResultatFlexionSimple:
    """Calcule les armatures pour un moment fictif M_Ed,A ramené aux aciers
    tendus, en flexion simple équivalente (EC2 méthode par pivots A/B).

    Args:
        moment_reduit_ed: mu_Ed,A = M_Ed,A / (b.d².fcd) (sans dimension).
        b: largeur de la section (m). d, d': hauteurs utiles (m).
        mu_lu: moment réduit limite ; si None, calculé via
            `moment_reduit_limite`.

    Returns:
        ResultatFlexionSimple avec As exprimées en mm² si b, d en mètres et
        fcd/fyd en MPa (cohérence d'unités : b.d².fcd est en MN.m, il faut
        donc multiplier moment_reduit par 1e6 côté appelant si le moment est
        fourni en kN.m — voir les modules `elements`, qui gèrent cette
        conversion explicitement pour éviter toute ambiguïté ici).
    """
    if mu_lu is None:
        mu_lu = moment_reduit_limite(beton, acier)

    armature_double = moment_reduit_ed > mu_lu

    if armature_double:
        alpha_u = 1.25 * (1 - math.sqrt(max(1 - 2 * mu_lu, 0.0)))
    else:
        alpha_u = 1.25 * (1 - math.sqrt(max(1 - 2 * moment_reduit_ed, 0.0)))

    z_c = d * (1 - 0.4 * alpha_u)

    if not armature_double:
        As1 = moment_reduit_ed * b * d**2 * beton.fcd * 1e6 / (z_c * acier.fyd)
        return ResultatFlexionSimple(
            mu_ed=moment_reduit_ed,
            mu_lu=mu_lu,
            armature_double=False,
            alpha_u=alpha_u,
            z_c=z_c,
            As1_flexion_simple=As1,
            As2_flexion_simple=0.0,
        )

    # Armature double : béton plafonné à mu_lu, le reste repris par As2.
    moment_limite = mu_lu * b * d**2 * beton.fcd  # MN.m
    moment_ed = moment_reduit_ed * b * d**2 * beton.fcd  # MN.m
    As2 = (moment_ed - moment_limite) * 1e6 / (acier.fyd * (d - d_prime))
    As1 = moment_limite * 1e6 / (z_c * acier.fyd) + As2

    return ResultatFlexionSimple(
        mu_ed=moment_reduit_ed,
        mu_lu=mu_lu,
        armature_double=True,
        alpha_u=alpha_u,
        z_c=z_c,
        As1_flexion_simple=As1,
        As2_flexion_simple=As2,
    )


def corriger_flexion_composee(
    As1_fs: float, As2_fs: float, N_Ed_kN: float, acier: Acier
) -> tuple[float, float]:
    """Corrige les armatures de flexion simple pour la flexion composée
    (rapport PFA §1.7) : As1 = As1_FS - N_Ed/fyd ; As2 = As2_FS.

    N_Ed en kN, positif en compression -> converti en N pour homogénéité
    avec fyd en MPa (N/mm²) et As en mm².
    """
    As1 = As1_fs - (N_Ed_kN * 1000.0) / acier.fyd
    return As1, As2_fs
