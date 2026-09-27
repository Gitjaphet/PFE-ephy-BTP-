"""Dataclasses de résultats, communes à tous les éléments (`flexcomp.elements`).

Toutes ces classes sont immuables (frozen=True) : un résultat de calcul est
un instantané, jamais modifié après coup. Si un paramètre change, on relance
le calcul et on obtient un nouveau résultat — cela élimine toute une classe
de bugs (résultat affiché qui ne correspond plus aux données saisies).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CasSection(Enum):
    """Les trois cas de flexion composée (rapport PFA §1.1)."""

    PARTIELLEMENT_COMPRIMEE = "partiellement_comprimee"
    ENTIEREMENT_TENDUE = "entierement_tendue"
    ENTIEREMENT_COMPRIMEE = "entierement_comprimee"


@dataclass(frozen=True)
class Sollicitation:
    """Couple (effort normal, moment fléchissant) à un état limite donné.

    Convention de signe (cf. rapport PFA §1.1) : N > 0 en compression,
    N < 0 en traction. M est le moment par rapport au centre de gravité de
    la section de béton seul.
    """

    N: float          # effort normal (kN), positif en compression
    M: float          # moment fléchissant (kN.m)

    @property
    def excentricite_1er_ordre(self) -> float:
        """e1 = M/N (m si N en kN et M en kN.m). Lève ZeroDivisionError si
        N = 0 : à l'appelant de gérer ce cas particulier (traction pure)."""
        return self.M / self.N


@dataclass(frozen=True)
class EffetsSecondOrdre:
    """Résultat de la prise en compte des effets du second ordre (EC2 §5.8)."""

    lambda_calcule: float
    lambda_limite: float
    second_ordre_necessaire: bool
    excentricite_1er_ordre: float
    excentricite_imperfection: float
    excentricite_2nd_ordre: float
    excentricite_totale: float
    excentricite_min: float
    moment_calcul: float          # M*_Ed = N_Ed . e_tot (kN.m)


@dataclass(frozen=True)
class ArmaturesSection:
    """Sections d'acier calculées pour une section transversale.

    As1 est conventionnellement la nappe tendue (ou la plus sollicitée),
    As2 la nappe comprimée (ou la moins sollicitée), au sens du rapport PFA.
    """

    As1: float                     # mm² (par mètre pour un voile/voûte)
    As2: float                     # mm² (par mètre pour un voile/voûte)
    As_min: float                  # mm² — section minimale réglementaire (par nappe)
    As_max: Optional[float] = None  # mm² — section maximale réglementaire (par nappe)
    cas: Optional[CasSection] = None
    commentaire: str = ""


@dataclass(frozen=True)
class VerificationELS:
    """Résultat d'une vérification à l'état limite de service."""

    sigma_beton: float
    sigma_beton_limite: float
    sigma_acier: Optional[float] = None
    sigma_acier_limite: Optional[float] = None

    @property
    def beton_verifie(self) -> bool:
        return self.sigma_beton <= self.sigma_beton_limite

    @property
    def acier_verifie(self) -> Optional[bool]:
        if self.sigma_acier is None or self.sigma_acier_limite is None:
            return None
        return self.sigma_acier <= self.sigma_acier_limite

    @property
    def verifie(self) -> bool:
        acier_ok = self.acier_verifie
        return self.beton_verifie and (acier_ok is None or acier_ok)


@dataclass(frozen=True)
class ResultatPoteau:
    """Résultat complet du dimensionnement d'un poteau rectangulaire."""

    sollicitation_elu: Sollicitation
    effets_2nd_ordre: EffetsSecondOrdre
    cas: CasSection
    moment_reduit: Optional[float]
    armatures: ArmaturesSection
    verification_els: Optional[VerificationELS] = None
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SectionCritiqueVoute:
    """Section courante la plus sollicitée d'une voûte à trois articulations."""

    x: float                # abscisse le long de la portée (m)
    moment: float            # moment fléchissant M(x) (kN.m)
    effort_normal: float      # effort normal N(x) (kN)
    angle_rad: float          # pente de l'arc en x (rad)
    excentricite_geo: float   # e_geo = |M|/N (m)


@dataclass(frozen=True)
class ResultatVoute:
    """Résultat complet du calcul d'une voûte à trois articulations."""

    poussee_horizontale: float   # H (kN/m)
    rayon_arc: float              # R (m)
    moments_aux_rotules: tuple[float, float, float]  # doit être ~(0, 0, 0)
    section_critique: SectionCritiqueVoute
    effets_2nd_ordre: EffetsSecondOrdre
    verification_12_6: "VerificationFlambementVoile"
    armatures: ArmaturesSection


@dataclass(frozen=True)
class VerificationForcesAxiales:
    """EC2 §12.6.1 — résistance aux forces axiales d'un mur/voûte non armé."""

    N_Ed: float
    N_Rd1: float

    @property
    def verifie(self) -> bool:
        return self.N_Ed <= self.N_Rd1


@dataclass(frozen=True)
class VerificationEffortTranchant:
    """EC2 §12.6.3 — résistance à l'effort tranchant d'un mur non armé."""

    tau_cp: float
    f_cvd: float

    @property
    def verifie(self) -> bool:
        return self.tau_cp <= self.f_cvd


@dataclass(frozen=True)
class VerificationFlambementVoile:
    """EC2 §12.6.5 — résistance au flambement d'un mur/voûte non armé."""

    lambda_calcule: float
    lambda_limite: float
    phi: float
    N_Ed: float
    N_Rd12: float

    @property
    def elancement_ok(self) -> bool:
        return self.lambda_calcule <= self.lambda_limite

    @property
    def verifie(self) -> bool:
        return self.elancement_ok and self.N_Ed <= self.N_Rd12


@dataclass(frozen=True)
class ResultatMurPorteur:
    """Résultat complet de la vérification / du dimensionnement d'un mur porteur."""

    verif_forces_axiales: VerificationForcesAxiales
    verif_effort_tranchant: VerificationEffortTranchant
    verif_flambement: VerificationFlambementVoile
    calculable_non_arme: bool
    armatures: Optional[ArmaturesSection] = None
    notes: tuple[str, ...] = field(default_factory=tuple)
