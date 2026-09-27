"""Poteau rectangulaire en flexion composée (EC2), les 3 cas de section.

Suit fidèlement l'organigramme du rapport PFA (Partie 1, Chapitre 2 et
Partie 2, Chapitre 1) :
    1. élancement + second ordre (méthode de la rigidité nominale)
    2. classification de la section (partiellement comprimée / entièrement
       tendue / entièrement comprimée)
    3. calcul des armatures à l'ELU selon le cas
    4. vérification des armatures min/max
    5. vérification à l'ELS (contrainte de compression du béton)

Convention de signe : N > 0 en compression, N < 0 en traction (rapport PFA §1.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from flexcomp.core.armatures_reglementaires import as_max_poteau, as_min_flexion, as_min_poteau
from flexcomp.core.elancement import (
    ConditionAppui,
    elancement,
    elancement_limite,
    longueur_flambement,
)
from flexcomp.core.exceptions import DonneesInvalidesError
from flexcomp.core.flexion_simple import (
    calcul_flexion_simple,
    corriger_flexion_composee,
    moment_reduit_limite,
)
from flexcomp.core.materials import Acier, Beton
from flexcomp.results.dataclasses import (
    ArmaturesSection,
    CasSection,
    EffetsSecondOrdre,
    ResultatPoteau,
    Sollicitation,
    VerificationELS,
)
from flexcomp.sections.rectangular import SectionRectangulaire
from flexcomp.core.elancement import longueur_flambement_portique


@dataclass(frozen=True)
class PoteauRectangulaire:
    """Poteau rectangulaire isolé, sollicité en flexion composée.

    Attributes:
        section: géométrie de la section (SectionRectangulaire).
        longueur_libre: hauteur libre du poteau l (m).
        condition_appui: conditions d'appui pour l0 (ConditionAppui).
        beton, acier: matériaux.
        a, b_coef, c: coefficients forfaitaires de lambda_lim (EC2 §5.8.3.1),
            valeurs recommandées 0,7 / 1,1 / 0,7 par défaut.
    """

    section: SectionRectangulaire
    longueur_libre: float
    condition_appui: ConditionAppui
    beton: Beton
    acier: Acier
    a: float = 0.7
    b_coef: float = 1.1
    c: float = 0.7
    k1: float = 0.1   # souplesse en pied (portiques)
    k2: float = 0.1   # souplesse en tête (portiques)

    @property
    def l0(self) -> float:
        if self.condition_appui in (ConditionAppui.PORTIQUE_NON_INTEGRE,
                                    ConditionAppui.PORTIQUE_INTEGRE):
            return longueur_flambement_portique(
                self.longueur_libre, self.k1, self.k2,
                contrevente=self.condition_appui is ConditionAppui.PORTIQUE_NON_INTEGRE,
            )
        return longueur_flambement(self.longueur_libre, self.condition_appui)

    @property
    def excentricite_min(self) -> float:
        """e0,min = max(20 mm ; h/30) — EC2 §6.1(4) (rapport PFA §1.6)."""
        return max(0.020, self.section.h / 30)

    # ------------------------------------------------------------------
    # Étape 1 — élancement et second ordre
    # ------------------------------------------------------------------
    def effets_second_ordre(self, sollicitation: Sollicitation) -> EffetsSecondOrdre:
        """Calcule l'élancement, détermine si le second ordre est nécessaire,
        et renvoie l'excentricité totale + le moment de calcul majoré.

        Méthode de la rigidité nominale (courbure nominale), EC2 §5.8.8.3,
        appliquée dans le plan de plus grande dimension h (flexion étudiée).
        """
        if sollicitation.N <= 0:
            raise DonneesInvalidesError(
                "Le calcul du second ordre suppose un effort de compression (N > 0)."
            )

        i_h = self.section.rayon_giration_h
        lam = elancement(self.l0, i_h)

        n = sollicitation.N / (self.section.aire_beton * self.beton.fcd * 1000.0)
        lam_lim = elancement_limite(n, self.a, self.b_coef, self.c)

        e1 = sollicitation.excentricite_1er_ordre
        ei = self.l0 / 400.0

        second_ordre_necessaire = lam > lam_lim
        if second_ordre_necessaire:
            k_phi = max(1.0, 1 + 0.35 * self.beton.fck / 200 + lam / 150)
            inv_r0 = self.acier.eps_yd / (0.45 * self.section.d)
            inv_r = 1.0 * k_phi * inv_r0  # Kr = 1 (approche simplifiée, cf. rapport)
            e2 = inv_r * self.l0**2 / (3.14159265358979**2)
        else:
            e2 = 0.0

        e_tot = e1 + ei + e2
        e_min = self.excentricite_min
        e_tot = max(e_tot, e_min)

        moment_calcul = sollicitation.N * e_tot

        return EffetsSecondOrdre(
            lambda_calcule=lam,
            lambda_limite=lam_lim,
            second_ordre_necessaire=second_ordre_necessaire,
            excentricite_1er_ordre=e1,
            excentricite_imperfection=ei,
            excentricite_2nd_ordre=e2,
            excentricite_totale=e_tot,
            excentricite_min=e_min,
            moment_calcul=moment_calcul,
        )

    def _effets_traction(self, sollicitation: Sollicitation) -> EffetsSecondOrdre:
        """Cas N <= 0 (traction) : pas de flambement, e0 = M_Ed/|N_Ed| tel quel
        (rapport PFA §2.1-2.2)."""
        e0 = sollicitation.M / abs(sollicitation.N) if sollicitation.N != 0 else 0.0
        return EffetsSecondOrdre(
            lambda_calcule=float("nan"),
            lambda_limite=float("nan"),
            second_ordre_necessaire=False,
            excentricite_1er_ordre=e0,
            excentricite_imperfection=0.0,
            excentricite_2nd_ordre=0.0,
            excentricite_totale=e0,
            excentricite_min=self.excentricite_min,
            moment_calcul=sollicitation.M,
        )

    # ------------------------------------------------------------------
    # Étape 2 — classification du cas de section
    # ------------------------------------------------------------------
    def classifier(self, N: float, e_tot: float) -> CasSection:
        """Détermine le cas de section à partir du signe de N et de la
        comparaison excentricité totale / excentricité limite (rapport PFA
        §1.3, §2.2, §3.3). Un critère approché ; pour les cas limites,
        `classifier_rigoureux` (moment réduit) tranche de façon fiable."""
        e_lim = self.section.excentricite_limite
        if N < 0:
            return CasSection.ENTIEREMENT_TENDUE
        if e_tot > e_lim:
            return CasSection.PARTIELLEMENT_COMPRIMEE
        return CasSection.ENTIEREMENT_COMPRIMEE

    def classifier_rigoureux(self, moment_reduit_ed_a: float, N: float) -> CasSection:
        """Classification fiable par moment réduit (rapport PFA §3.3) :
        mu_BC = lambda.(h/d).(1 - 0,5.lambda.(h/d)) avec lambda = eps_cu2/(eps_cu2+eps_yd)... 

        Utilise mu_AB comme frontière simple/double armature (cas 1) et une
        valeur mu_BC (pivot B/C) comme frontière avec le cas entièrement
        comprimé. Le rapport PFA calcule mu_BC = lambda.(h/d).(1-0,4.lambda.(h/d))
        avec lambda = 0,8 (position du plan de déformation limite).
        """
        if N < 0:
            return CasSection.ENTIEREMENT_TENDUE
        lam = 0.8
        h_sur_d = self.section.h / self.section.d
        mu_bc = lam * h_sur_d * (1 - 0.4 * lam * h_sur_d)
        if moment_reduit_ed_a > mu_bc:
            return CasSection.ENTIEREMENT_COMPRIMEE
        return CasSection.PARTIELLEMENT_COMPRIMEE

    # ------------------------------------------------------------------
    # Étape 3 — dimensionnement complet à l'ELU
    # ------------------------------------------------------------------
    def dimensionner(self, sollicitation_elu: Sollicitation) -> ResultatPoteau:
        """Enchaîne les étapes 1 à 4 de l'organigramme du rapport PFA et
        renvoie un ResultatPoteau complet.

        Les effets du second ordre (flambement) n'ont de sens que pour un
        effort de compression : pour N <= 0 (traction, cas 2), on construit
        directement l'excentricité e0 = M_Ed/|N_Ed| sans majoration, comme
        le fait le rapport PFA §2.1-2.2.
        """
        d, h, b = self.section.d, self.section.h, self.section.b

        if sollicitation_elu.N > 0:
            effets = self.effets_second_ordre(sollicitation_elu)
        else:
            effets = self._effets_traction(sollicitation_elu)

        # Moment fictif ramené aux aciers tendus (fibre à d) :
        M_Ed_A = effets.moment_calcul + sollicitation_elu.N * (d - h / 2)
        mu_ed_a = M_Ed_A * 1e-3 / (b * d**2 * self.beton.fcd) if b * d**2 > 0 else 0.0
        # (M en kN.m -> MN.m : *1e-3 ; b, d en m ; fcd en MPa=MN/m² -> cohérent)

        cas = self.classifier_rigoureux(mu_ed_a, sollicitation_elu.N)
        notes: list[str] = []

        if cas is CasSection.ENTIEREMENT_TENDUE:
            armatures, notes_cas = self._cas_entierement_tendue(sollicitation_elu, effets)
            moment_reduit = None
        elif cas is CasSection.ENTIEREMENT_COMPRIMEE:
            armatures, notes_cas = self._cas_entierement_comprimee(sollicitation_elu)
            moment_reduit = mu_ed_a
        else:
            armatures, notes_cas = self._cas_partiellement_comprimee(
                sollicitation_elu, M_Ed_A, mu_ed_a
            )
            moment_reduit = mu_ed_a
        notes.extend(notes_cas)

        return ResultatPoteau(
            sollicitation_elu=sollicitation_elu,
            effets_2nd_ordre=effets,
            cas=cas,
            moment_reduit=moment_reduit,
            armatures=armatures,
            notes=tuple(notes),
        )

    # -- Cas 1 : section partiellement comprimée --------------------------
    def _cas_partiellement_comprimee(
        self, sollicitation: Sollicitation, M_Ed_A: float, mu_ed_a: float
    ) -> tuple[ArmaturesSection, list[str]]:
        d, d_prime, b = self.section.d, self.section.d_prime, self.section.b
        mu_lu = moment_reduit_limite(self.beton, self.acier)

        resultat_fs = calcul_flexion_simple(mu_ed_a, b, d, d_prime, self.beton, self.acier, mu_lu)
        As1, As2 = corriger_flexion_composee(
            resultat_fs.As1_flexion_simple, resultat_fs.As2_flexion_simple,
            sollicitation.N, self.acier,
        )

        as_min = as_min_poteau(sollicitation.N, self.section.aire_beton, self.acier)
        as_max = as_max_poteau(self.section.aire_beton)

        notes = []
        if resultat_fs.armature_double:
            notes.append("Armature comprimée As2 nécessaire (mu_Ed,A > mu_lu).")

        armatures = ArmaturesSection(
            As1=max(As1, 0.0), As2=max(As2, 0.0),
            As_min=as_min, As_max=as_max,
            cas=CasSection.PARTIELLEMENT_COMPRIMEE,
            commentaire="Assimilation à la flexion simple.",
        )
        return armatures, notes

    # -- Cas 2 : section entièrement tendue --------------------------------
    def _cas_entierement_tendue(
        self, sollicitation: Sollicitation, effets: EffetsSecondOrdre
    ) -> tuple[ArmaturesSection, list[str]]:
        d, d_prime, h = self.section.d, self.section.d_prime, self.section.h
        N_Ed = sollicitation.N  # négatif (traction)
        e0 = effets.excentricite_1er_ordre  # signé, = M/N (N<0)

        e_A1 = d - h / 2 + e0
        e_A2 = h / 2 - d_prime - e0

        N_abs = abs(N_Ed) * 1000.0  # kN -> N
        denom = (e_A1 + e_A2) * self.acier.fyd
        As1 = N_abs * e_A2 / denom
        As2 = N_abs * e_A1 / denom

        # Section entièrement tendue : minimum de flexion (EC2 §9.2.1.1), et
        # non le minimum de poteau comprimé (rapport PFA §2.6) :
        as_min = as_min_flexion(self.section.b, d, self.beton, self.acier)
        as_max = as_max_poteau(self.section.aire_beton)

        notes = []
        if As1 < as_min:
            notes.append("As1 gouvernée par le minimum réglementaire (par nappe).")
        if As2 < as_min:
            notes.append("As2 gouvernée par le minimum réglementaire (par nappe).")

        armatures = ArmaturesSection(
            As1=max(As1, as_min), As2=max(As2, as_min),
            As_min=as_min, As_max=as_max,
            cas=CasSection.ENTIEREMENT_TENDUE,
            commentaire="Équilibre des moments par rapport à chaque nappe, sans le béton.",
        )
        return armatures, notes

    # -- Cas 3 : section entièrement comprimée -----------------------------
    def _cas_entierement_comprimee(
        self, sollicitation: Sollicitation
    ) -> tuple[ArmaturesSection, list[str]]:
        sigma_s = self.acier.contrainte_pivot_c(self.beton.eps_c2)
        N_Ed = sollicitation.N * 1000.0  # kN -> N
        Ac = self.section.aire_beton * 1e6  # m² -> mm²

        # Bilan des forces (pivot C, ferraillage symétrique As1 = As2 = A) :
        # N_Ed = Ac.fcd + (sigma_s - fcd).(2A)
        numerateur = N_Ed - Ac * self.beton.fcd
        denominateur = sigma_s - self.beton.fcd
        A = numerateur / (2 * denominateur) if denominateur != 0 else float("inf")

        as_min = as_min_poteau(sollicitation.N, self.section.aire_beton, self.acier)
        as_max = as_max_poteau(self.section.aire_beton)

        notes = []
        if A < 0:
            notes.append(
                "Bilan des forces négatif (béton seul suffit) : "
                "les armatures minimales gouvernent la section."
            )
            A = as_min / 2  # réparti sur les deux nappes

        armatures = ArmaturesSection(
            As1=max(A, as_min / 2), As2=max(A, as_min / 2),
            As_min=as_min, As_max=as_max,
            cas=CasSection.ENTIEREMENT_COMPRIMEE,
            commentaire="Bilan des forces au pivot C, ferraillage symétrique.",
        )
        return armatures, notes

    # ------------------------------------------------------------------
    # Étape 5 — vérification à l'ELS (section homogénéisée)
    # ------------------------------------------------------------------
    def verifier_els(
        self, sollicitation_els: Sollicitation, armatures: ArmaturesSection
    ) -> VerificationELS:
        """Contrainte de compression du béton en section homogénéisée
        (rapport PFA §1.6.1-1.6.2), valable pour N > 0 (compression)."""
        b, h, d, d_prime = (
            self.section.b, self.section.h, self.section.d, self.section.d_prime,
        )
        n_ratio = self.acier.Es / 30000.0  # module de Young béton usuel ~30000 MPa (Ecm)
        As1, As2 = armatures.As1 * 1e-6, armatures.As2 * 1e-6  # mm² -> m²

        A_hom = b * h + (n_ratio - 1) * (As1 + As2)
        y_g = (
            b * h * h / 2 + (n_ratio - 1) * As2 * d_prime + (n_ratio - 1) * As1 * d
        ) / A_hom
        I_hom = (
            b * h**3 / 12
            + b * h * (h / 2 - y_g) ** 2
            + (n_ratio - 1) * (As2 * (y_g - d_prime) ** 2 + As1 * (d - y_g) ** 2)
        )

        N_ser = sollicitation_els.N * 1000.0  # kN -> N (compression positive)
        sigma_s_lim = 0.8 * self.acier.fyk      # rapport PFA : 0,8.fyk

        if N_ser < 0:
            # Section entièrement tendue (rapport Cas 2 §2.8) : équilibre des moments
            e0 = abs(sollicitation_els.M / sollicitation_els.N)  # m
            eA1 = d - h / 2 + e0
            eA2 = h / 2 - d_prime - e0
            N_abs = abs(N_ser)
            s1 = N_abs * eA2 / ((eA1 + eA2) * armatures.As1) if armatures.As1 > 0 else float("inf")
            s2 = N_abs * eA1 / ((eA1 + eA2) * armatures.As2) if armatures.As2 > 0 else float("inf")
            return VerificationELS(
                sigma_beton=0.0,
                sigma_beton_limite=self.beton.sigma_c_lim_els,
                sigma_acier=max(s1, s2),
                sigma_acier_limite=sigma_s_lim,
            )

        e_ser = sollicitation_els.M * 1000.0 / sollicitation_els.N if sollicitation_els.N else 0.0
        # N_ser en N, A_hom en m² -> mm² (x1e6) ; e_ser en mm ; y, I convertis en mm, mm^4
        s_N = N_ser / (A_hom * 1e6)                  # part due à N (MPa)
        k_M = N_ser * e_ser / (I_hom * 1e12)         # gradient dû au moment (MPa/mm)
        sigma_c = s_N + k_M * y_g * 1e3
        # Acier = n x contrainte du béton homogène au niveau de chaque nappe
        sigma_s1 = n_ratio * (s_N - k_M * (d - y_g) * 1e3)
        sigma_s2 = n_ratio * (s_N + k_M * (y_g - d_prime) * 1e3)

        return VerificationELS(
            sigma_beton=sigma_c,
            sigma_beton_limite=self.beton.sigma_c_lim_els,
            sigma_acier=max(abs(sigma_s1), abs(sigma_s2)),
            sigma_acier_limite=sigma_s_lim,
        )
