"""Voile en béton armé, EC2 §12.6 et §9.6.

Suit le rapport PFA (Partie 1 Chapitre 4, Partie 2 Chapitre 3) :
    1. longueur efficace l0 = beta.lw, élancement lambda
    2. trois vérifications du voile non armé : forces axiales (§12.6.1),
       effort tranchant (§12.6.3), flambement (§12.6.5)
    3. si les trois vérifications passent et lambda <= 86 : voile non armé
       possible (armatures minimales nulles, ferraillage de peau seulement)
    4. sinon : dimensionnement classique en flexion composée, identique au
       poteau (flexion dans le plan du voile, bcalc=hw, hcalc=b)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from flexcomp.core.armatures_reglementaires import as_min_voile_flexion
from flexcomp.core.exceptions import DonneesInvalidesError
from flexcomp.core.flexion_simple import calcul_flexion_simple, corriger_flexion_composee
from flexcomp.core.materials import Acier, Beton
from flexcomp.results.dataclasses import (
    ArmaturesSection,
    ResultatMurPorteur,
    Sollicitation,
    VerificationEffortTranchant,
    VerificationFlambementVoile,
    VerificationForcesAxiales,
)


@dataclass(frozen=True)
class MurPorteur:
    """Voile en béton armé, console verticale encastrée en pied.

    Attributes:
        hauteur_libre: hauteur libre du voile lw (m).
        longueur_calcul: longueur de la bande de calcul b (m).
        epaisseur: épaisseur hw (m).
        beta: coefficient de longueur efficace (tableau 12.1 EC2 §12.6.5),
            dépend des conditions de rive (1,0 si encastré tête+pied par
            planchers avec bords verticaux libres, valeur du rapport PFA).
        enrobage_nominal: pour le calcul de d, d'.
    """

    hauteur_libre: float
    longueur_calcul: float
    epaisseur: float
    beta: float
    beton: Beton
    acier: Acier
    enrobage_nominal: float = 0.03

    def __post_init__(self) -> None:
        for nom, val in (
            ("hauteur_libre", self.hauteur_libre),
            ("longueur_calcul", self.longueur_calcul),
            ("epaisseur", self.epaisseur), ("beta", self.beta),
        ):
            if val <= 0:
                raise DonneesInvalidesError(f"'{nom}' doit être strictement positif.")

    @property
    def l0(self) -> float:
        """Longueur efficace : l0 = beta.lw."""
        return self.beta * self.hauteur_libre

    @property
    def elancement(self) -> float:
        """lambda = l0/i, i = hw/sqrt(12)."""
        i = self.epaisseur / math.sqrt(12)
        return self.l0 / i

    @property
    def d(self) -> float:
        return self.longueur_calcul - self.enrobage_nominal - 0.005  # cf. rapport : b - 0,05

    @property
    def d_prime(self) -> float:
        return self.enrobage_nominal + 0.005

    # ------------------------------------------------------------------
    # Vérification 1 — forces axiales (EC2 §12.6.1)
    # ------------------------------------------------------------------
    def verifier_forces_axiales(self, N_Ed: float, e: float) -> VerificationForcesAxiales:
        """N_Rd1 = fcd,pl.b.hw.(1 - 2e/hw), en kN. `e` est l'excentricité
        dans l'épaisseur (et non e1=M/N dans le plan — attention à ne pas
        les confondre, cf. rapport PFA, mise en garde §5.1/figure)."""
        N_Rd1 = (
            self.beton.fcd_pl * self.longueur_calcul * self.epaisseur
            * (1 - 2 * e / self.epaisseur) * 1000.0
        )
        return VerificationForcesAxiales(N_Ed=N_Ed, N_Rd1=N_Rd1)

    # ------------------------------------------------------------------
    # Vérification 2 — effort tranchant (EC2 §12.6.3)
    # ------------------------------------------------------------------
    def verifier_effort_tranchant(self, V_Ed: float, N_Ed: float) -> VerificationEffortTranchant:
        """tau_cp = 1,5.V_Ed/(b.hw) <= f_cvd = sqrt(fctd,pl.(fctd,pl+sigma_cp))."""
        tau_cp = 1.5 * (V_Ed * 1000.0) / (self.longueur_calcul * self.epaisseur * 1e6)
        # V_Ed kN->N, b.hw en m² -> mm² (x1e6) : tau en N/mm² = MPa
        sigma_cp = min(
            (N_Ed * 1000.0) / (self.longueur_calcul * self.epaisseur * 1e6),
            self.beton.sigma_c_lim_els,
        )
        f_cvd = math.sqrt(
            max(self.beton.fctd_pl * (self.beton.fctd_pl + sigma_cp), 0.0)
        )
        return VerificationEffortTranchant(tau_cp=tau_cp, f_cvd=f_cvd)

    # ------------------------------------------------------------------
    # Vérification 3 — flambement (EC2 §12.6.5)
    # ------------------------------------------------------------------
    def verifier_flambement(self, N_Ed: float, e_tot: float) -> VerificationFlambementVoile:
        phi = min(
            1.14 * (1 - 2 * e_tot / self.epaisseur) - 0.02 * self.l0 / self.epaisseur,
            1 - 2 * e_tot / self.epaisseur,
        )
        N_Rd12 = (
            self.longueur_calcul * self.epaisseur * self.beton.fcd_pl * phi * 1000.0
        )
        return VerificationFlambementVoile(
            lambda_calcule=self.elancement, lambda_limite=86.0, phi=phi,
            N_Ed=N_Ed, N_Rd12=N_Rd12,
        )

    def excentricite_totale_flambement(self, e: float) -> float:
        """e_tot = e + max(l0/400 ; hw/30 ; 20mm), pour la vérif. flambement."""
        ei = max(self.l0 / 400, self.epaisseur / 30, 0.020)
        return e + ei

    # ------------------------------------------------------------------
    # Synthèse : peut-on traiter le mur comme non armé ?
    # ------------------------------------------------------------------
    def verifier_non_arme(
        self, N_Ed: float, V_Ed: float, e: float
    ) -> ResultatMurPorteur:
        """Effectue les 3 vérifications et conclut sur l'armature
        minimale requise (rapport PFA §4.3, §5.4-5.6)."""
        e_tot_flamb = self.excentricite_totale_flambement(e)

        v1 = self.verifier_forces_axiales(N_Ed, e)
        v2 = self.verifier_effort_tranchant(V_Ed, N_Ed)
        v3 = self.verifier_flambement(N_Ed, e_tot_flamb)

        calculable_non_arme = v1.verifie and v2.verifie and v3.verifie and self.elancement <= 86

        notes = []
        if calculable_non_arme:
            notes.append(
                "Les 3 vérifications et λ ≤ 86 sont satisfaites : "
                "voile calculable comme non armé (ferraillage de peau + épingles seulement)."
            )
        else:
            notes.append(
                "Au moins une vérification n'est pas satisfaite, ou λ > 86 : "
                "le voile doit être calculé comme armé (méthode du poteau)."
            )

        return ResultatMurPorteur(
            verif_forces_axiales=v1,
            verif_effort_tranchant=v2,
            verif_flambement=v3,
            calculable_non_arme=calculable_non_arme,
            notes=tuple(notes),
        )

    # ------------------------------------------------------------------
    # Dimensionnement armé (flexion composée DANS LE PLAN du voile)
    # ------------------------------------------------------------------
    def dimensionner_arme(self, sollicitation: Sollicitation) -> ArmaturesSection:
        """Flexion composée dans le plan du voile, méthode identique au
        poteau, avec bcalc=hw, hcalc=b (rapport PFA §4.5, §5.7)."""
        e1 = sollicitation.excentricite_1er_ordre
        ei = max(self.l0 / 400, self.epaisseur / 30, 0.020)
        e_tot = e1 + ei
        M_Ed_star = sollicitation.N * e_tot

        d, d_prime = self.d, self.d_prime
        h_calc = self.longueur_calcul
        M_Ed_A = M_Ed_star + sollicitation.N * (d - h_calc / 2)
        mu_ed_a = M_Ed_A * 1e-3 / (self.epaisseur * d**2 * self.beton.fcd)

        resultat_fs = calcul_flexion_simple(
            mu_ed_a, self.epaisseur, d, d_prime, self.beton, self.acier
        )
        As1, As2 = corriger_flexion_composee(
            resultat_fs.As1_flexion_simple, resultat_fs.As2_flexion_simple,
            sollicitation.N, self.acier,
        )
        as_min = as_min_voile_flexion(self.epaisseur, d, self.beton, self.acier)

        return ArmaturesSection(
            As1=max(As1, as_min), As2=max(As2, 0.0), As_min=as_min,
            commentaire="Flexion composée dans le plan (aciers d'about, chaînages verticaux).",
        )
