"""Matériaux réglementaires EC2 : béton et acier.

Toutes les classes sont des dataclasses *gelées* (frozen=True) : un matériau
est une donnée immuable une fois défini, ce qui évite les bugs de calculs qui
partagent un objet mutable modifié ailleurs dans le code.

Références :
    NF EN 1992-1-1 (EC2), §3.1 (béton) et §3.2 (aciers).
    Cours INSA Rennes — Béton Armé, Chapitre 11 (flexion composée).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from flexcomp.core.exceptions import DonneesInvalidesError

# Déformations limites conventionnelles (EC2 Tableau 3.1 / §3.1.7 et §3.2.7)
EPS_CU2 = 3.5e-3   # déformation ultime du béton (pivots A/B)
EPS_C2 = 2.0e-3    # déformation du béton au pivot C
ES_ACIER = 200_000.0  # module d'élasticité de l'acier, en MPa


@dataclass(frozen=True)
class Beton:
    """Béton selon EC2, défini par sa classe de résistance caractéristique.

    Attributes:
        fck: résistance caractéristique à la compression à 28 jours (MPa).
        gamma_c: coefficient partiel de sécurité béton (1.5 en situation
            durable/transitoire, 1.2 en situation accidentelle).
        alpha_cc: coefficient tenant compte des effets à long terme sur la
            résistance en compression (recommandé 1.0 en France, EC2 §3.1.6).
    """

    fck: float
    gamma_c: float = 1.5
    alpha_cc: float = 1.0

    def __post_init__(self) -> None:
        if self.fck <= 0:
            raise DonneesInvalidesError("fck doit être strictement positif (MPa).")
        if self.gamma_c <= 0:
            raise DonneesInvalidesError("gamma_c doit être strictement positif.")

    @property
    def fcd(self) -> float:
        """Résistance de calcul à la compression (MPa) : fcd = alpha_cc.fck/gamma_c."""
        return self.alpha_cc * self.fck / self.gamma_c

    @property
    def fcd_pl(self) -> float:
        """Résistance de calcul « plastique » utilisée pour poteaux entièrement
        comprimés / voiles / voûtes (EC2 §12.6, coefficient 0.8) : fcd,pl = 0,8.fcd."""
        return 0.8 * self.fcd

    @property
    def fctm(self) -> float:
        """Résistance moyenne à la traction (MPa), EC2 Tableau 3.1 : 0,3.fck^(2/3)
        (valable pour fck <= 50 MPa, cas des exemples de ce projet)."""
        return 0.3 * self.fck ** (2 / 3)

    @property
    def fctk_005(self) -> float:
        """Fractile 5% de la résistance à la traction, EC2 Tableau 3.1 :
        fctk,0.05 = 0,7.fctm."""
        return 0.7 * self.fctm

    @property
    def fctd_pl(self) -> float:
        """Résistance de calcul à la traction pour béton non armé (EC2 §12.6.3),
        combinant le fractile caractéristique et la réduction de 20% appliquée
        au béton non armé (EC2 §12.6, cf. rapport PFA §4.3) :
        fctd,pl = 0,8.fctk,0.05/gamma_c."""
        return 0.8 * self.fctk_005 / self.gamma_c

    @property
    def sigma_c_lim_els(self) -> float:
        """Contrainte de compression limite du béton à l'ELS : 0,6.fck (MPa)."""
        return 0.6 * self.fck

    @property
    def eps_cu2(self) -> float:
        return EPS_CU2

    @property
    def eps_c2(self) -> float:
        return EPS_C2

    def __repr__(self) -> str:  # pragma: no cover - confort d'affichage
        return f"Beton(C{self.fck:.0f}/{self.fck * 1.25:.0f}, fcd={self.fcd:.2f} MPa)"


@dataclass(frozen=True)
class Acier:
    """Acier pour béton armé selon EC2, défini par sa classe de résistance.

    Attributes:
        fyk: limite d'élasticité caractéristique (MPa), typiquement 500 pour
            du B500 (S500).
        gamma_s: coefficient partiel de sécurité acier (1.15 en situation
            durable/transitoire, 1.0 en situation accidentelle).
        Es: module d'élasticité (MPa), 200000 par convention EC2.
    """

    fyk: float = 500.0
    gamma_s: float = 1.15
    Es: float = ES_ACIER

    def __post_init__(self) -> None:
        if self.fyk <= 0:
            raise DonneesInvalidesError("fyk doit être strictement positif (MPa).")
        if self.gamma_s <= 0:
            raise DonneesInvalidesError("gamma_s doit être strictement positif.")

    @property
    def fyd(self) -> float:
        """Résistance de calcul (MPa) : fyd = fyk/gamma_s."""
        return self.fyk / self.gamma_s

    @property
    def eps_yd(self) -> float:
        """Déformation élastique de calcul : eps_yd = fyd/Es."""
        return self.fyd / self.Es

    @property
    def sigma_s_lim_els(self) -> float:
        """Contrainte de traction limite de l'acier à l'ELS : 0,8.fyk (MPa)."""
        return 0.8 * self.fyk

    def contrainte_pivot_c(self, eps_c2: float = EPS_C2) -> float:
        """Contrainte atteinte par l'acier lorsque le béton est au pivot C
        (section entièrement comprimée) : sigma_s = min(fyd ; Es.eps_c2)."""
        return min(self.fyd, self.Es * eps_c2)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Acier(B{self.fyk:.0f}, fyd={self.fyd:.2f} MPa)"


# Matériaux prédéfinis les plus courants (usage direct dans les scripts/tests)
C25_30 = Beton(fck=25.0)
C40_50 = Beton(fck=40.0)
B500B = Acier(fyk=500.0)
