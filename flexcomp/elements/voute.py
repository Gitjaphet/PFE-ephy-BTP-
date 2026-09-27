"""Voûte à trois articulations, théorie de Mesnager + formalisme EC2 moderne.

Suit le rapport PFA (Partie 1 Chapitre 3, Partie 2 Chapitre 2) :
    1. poussée horizontale H et rayon de l'arc R (Mesnager)
    2. vérification M = 0 aux trois rotules
    3. recherche de la section courante la plus sollicitée (balayage de x)
    4. effets du second ordre / excentricités additionnelles (comme un poteau)
    5. vérification EC2 §12.6 (comme un mur non armé)
    6. dimensionnement des armatures à la section critique (flexion simple
       assimilée, identique au poteau/mur porteur)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from flexcomp.core.armatures_reglementaires import as_min_voile_flexion
from flexcomp.core.exceptions import ConvergenceError, DonneesInvalidesError
from flexcomp.core.flexion_simple import calcul_flexion_simple, corriger_flexion_composee
from flexcomp.core.materials import Acier, Beton
from flexcomp.results.dataclasses import (
    ArmaturesSection,
    EffetsSecondOrdre,
    ResultatVoute,
    SectionCritiqueVoute,
    VerificationFlambementVoile,
)
from flexcomp.sections.rectangular import SectionRectangulaire


@dataclass(frozen=True)
class VouteTroisArticulations:
    """Voûte en arc de cercle surbaissé, à trois articulations
    (rotules à la clef et aux naissances -> structure isostatique).

    Attributes:
        portee: portée l (m).
        fleche: flèche f (m), typiquement l/10 pour une voûte surbaissée.
        charge_uniforme: charge verticale uniformément répartie p (kN/m).
        epaisseur: épaisseur de la voûte hw (m).
        largeur_calcul: largeur de la bande de calcul b (m), 1 m par défaut.
        enrobage_nominal, diametre_barre: pour le calcul de d, d'.
        beton, acier: matériaux.
    """

    portee: float
    fleche: float
    charge_uniforme: float
    epaisseur: float
    beton: Beton
    acier: Acier
    largeur_calcul: float = 1.0
    enrobage_nominal: float = 0.03
    diametre_barre: float = 0.012

    def __post_init__(self) -> None:
        for nom, val in (
            ("portee", self.portee), ("fleche", self.fleche),
            ("charge_uniforme", self.charge_uniforme), ("epaisseur", self.epaisseur),
        ):
            if val <= 0:
                raise DonneesInvalidesError(f"'{nom}' doit être strictement positif.")

    # ------------------------------------------------------------------
    # Statique (Mesnager)
    # ------------------------------------------------------------------
    @property
    def poussee_horizontale(self) -> float:
        """H = p.l²/(8f), kN (par mètre de largeur si p est en kN/m/m)."""
        return self.charge_uniforme * self.portee**2 / (8 * self.fleche)

    @property
    def rayon_arc(self) -> float:
        """R = l²/(8f) + f/2, m."""
        return self.portee**2 / (8 * self.fleche) + self.fleche / 2

    def y_funiculaire(self, x: float) -> float:
        """Courbe funiculaire de la charge uniforme : yf(x) = 4.f.x.(l-x)/l²."""
        return 4 * self.fleche * x * (self.portee - x) / self.portee**2

    def y_arc(self, x: float) -> float:
        """Géométrie réelle de l'arc circulaire : yarc(x) = f - R + sqrt(R² - (x-l/2)²)."""
        R = self.rayon_arc
        terme = R**2 - (x - self.portee / 2) ** 2
        return self.fleche - R + math.sqrt(max(terme, 0.0))

    def moment(self, x: float) -> float:
        """Moment fléchissant le long de l'arc : M(x) = H.[yf(x) - yarc(x)] (Mesnager)."""
        H = self.poussee_horizontale
        return H * (self.y_funiculaire(x) - self.y_arc(x))

    def moments_aux_rotules(self, tolerance: float = 1e-6) -> tuple[float, float, float]:
        """Vérifie M = 0 aux naissances (x=0, x=l) et à la clef (x=l/2)."""
        m0 = self.moment(0.0)
        m_clef = self.moment(self.portee / 2)
        m_l = self.moment(self.portee)
        for nom, m in (("naissance gauche", m0), ("clef", m_clef), ("naissance droite", m_l)):
            if abs(m) > tolerance:
                raise ConvergenceError(
                    f"Moment non nul à la rotule '{nom}' (M={m:.4g} kN.m) : "
                    "géométrie de l'arc à revoir."
                )
        return (m0, m_clef, m_l)

    # ------------------------------------------------------------------
    # Recherche de la section critique
    # ------------------------------------------------------------------
    def section_critique(self, n_points: int = 2001) -> SectionCritiqueVoute:
        """Balaye x dans [0 ; l/2] et retient l'abscisse de |M(x)| maximal
        (par symétrie de charge, l'autre moitié est identique).

        Args:
            n_points: résolution du balayage. 2001 points sur l/2 donne une
                précision largement suffisante (< 1 mm) pour une portée de
                quelques dizaines de mètres.
        """
        meilleur_x = 0.0
        meilleur_m = 0.0
        for i in range(n_points):
            x = (self.portee / 2) * i / (n_points - 1)
            m = self.moment(x)
            if abs(m) > abs(meilleur_m):
                meilleur_m = m
                meilleur_x = x

        H = self.poussee_horizontale
        V0 = self.charge_uniforme * self.portee / 2 - self.charge_uniforme * meilleur_x
        R = self.rayon_arc
        dx = meilleur_x - self.portee / 2
        terme = R**2 - dx**2
        angle = math.atan2(-dx, math.sqrt(max(terme, 0.0)))
        # tan(phi) = (x - l/2) / sqrt(R² - (x-l/2)²) ; angle orienté comme au rapport.
        angle = math.atan(dx / math.sqrt(max(terme, 1e-12)))

        N = H * math.cos(angle) + V0 * math.sin(angle)
        e_geo = abs(meilleur_m) / N if N != 0 else float("inf")

        return SectionCritiqueVoute(
            x=meilleur_x, moment=meilleur_m, effort_normal=N,
            angle_rad=angle, excentricite_geo=e_geo,
        )

    # ------------------------------------------------------------------
    # Excentricités additionnelles + second ordre (comme un poteau/mur)
    # ------------------------------------------------------------------
    def effets_additionnels(
        self, section_crit: SectionCritiqueVoute, longueur_flambement_l0: float
    ) -> EffetsSecondOrdre:
        """e0 = max(20mm ; hw/30) ; ei = max(l0/400 ; hw/30 ; 20mm) (rapport PFA §4.5)."""
        e0 = max(0.020, self.epaisseur / 30)
        ei = max(longueur_flambement_l0 / 400, self.epaisseur / 30, 0.020)
        e_tot = section_crit.excentricite_geo + e0 + ei
        moment_design = abs(section_crit.moment) + section_crit.effort_normal * (e0 + ei)

        return EffetsSecondOrdre(
            lambda_calcule=float("nan"),
            lambda_limite=float("nan"),
            second_ordre_necessaire=False,
            excentricite_1er_ordre=section_crit.excentricite_geo,
            excentricite_imperfection=ei,
            excentricite_2nd_ordre=0.0,
            excentricite_totale=e_tot,
            excentricite_min=e0,
            moment_calcul=moment_design,
        )

    # ------------------------------------------------------------------
    # Vérification EC2 §12.6 (comme un mur non armé)
    # ------------------------------------------------------------------
    def verifier_ec2_12_6(
        self, N: float, e_tot: float, longueur_flambement_l0: float
    ) -> VerificationFlambementVoile:
        """Vérifie N <= N_Rd,12 (flambement, EC2 §12.6.5) à la section critique."""
        i = self.epaisseur / math.sqrt(12)
        lam = longueur_flambement_l0 / i
        phi = min(
            1.14 * (1 - 2 * e_tot / self.epaisseur) - 0.02 * longueur_flambement_l0 / self.epaisseur,
            1 - 2 * e_tot / self.epaisseur,
        )
        N_Rd12 = (
            self.largeur_calcul * self.epaisseur * self.beton.fcd_pl * phi * 1000.0
        )  # MN -> kN (b, hw en m ; fcd_pl en MPa=MN/m²)

        return VerificationFlambementVoile(
            lambda_calcule=lam, lambda_limite=86.0, phi=phi,
            N_Ed=N, N_Rd12=N_Rd12,
        )

    def verifier_forces_axiales(self, N: float, e_tot: float) -> float:
        """N_Rd1 = fcd,pl.b.hw.(1 - 2.e_tot/hw), en kN."""
        return (
            self.beton.fcd_pl * self.largeur_calcul * self.epaisseur
            * (1 - 2 * e_tot / self.epaisseur) * 1000.0
        )

    # ------------------------------------------------------------------
    # Dimensionnement des armatures à la section critique
    # ------------------------------------------------------------------
    def dimensionner(self, longueur_flambement_l0: float | None = None) -> ResultatVoute:
        """Enchaîne l'ensemble du calcul et renvoie un ResultatVoute complet.

        Args:
            longueur_flambement_l0: longueur de flambement à utiliser pour
                l'excentricité additionnelle et EC2 §12.6 ; si None, on
                utilise la demi-portée l/2 (distance naissance-clef), valeur
                cohérente avec le calcul numérique du rapport PFA §4.6
                (lambda = 69,29 pour l=12m, hw=30cm) — à ajuster selon les
                conditions d'appui réelles de l'ouvrage si nécessaire.
        """
        self.moments_aux_rotules()
        section_crit = self.section_critique()

        if longueur_flambement_l0 is None:
            longueur_flambement_l0 = self.portee / 2

        effets = self.effets_additionnels(section_crit, longueur_flambement_l0)
        verif_126 = self.verifier_ec2_12_6(
            section_crit.effort_normal, effets.excentricite_totale, longueur_flambement_l0
        )

        d = self.epaisseur - self.enrobage_nominal - self.diametre_barre / 2
        d_prime = self.enrobage_nominal + self.diametre_barre / 2
        M_Ed_A = effets.moment_calcul + section_crit.effort_normal * (d - self.epaisseur / 2)

        mu_ed_a = (
            M_Ed_A * 1e-3 / (self.largeur_calcul * d**2 * self.beton.fcd)
            if d > 0 else 0.0
        )
        resultat_fs = calcul_flexion_simple(
            mu_ed_a, self.largeur_calcul, d, d_prime, self.beton, self.acier
        )
        As1, As2 = corriger_flexion_composee(
            resultat_fs.As1_flexion_simple, resultat_fs.As2_flexion_simple,
            section_crit.effort_normal, self.acier,
        )
        as_min = as_min_voile_flexion(self.largeur_calcul, d, self.beton, self.acier)

        armatures = ArmaturesSection(
            As1=max(As1, as_min), As2=max(As2, 0.0), As_min=as_min,
            commentaire="Flexion composée à la section critique, méthode identique au poteau.",
        )

        return ResultatVoute(
            poussee_horizontale=self.poussee_horizontale,
            rayon_arc=self.rayon_arc,
            moments_aux_rotules=self.moments_aux_rotules(),
            section_critique=section_crit,
            effets_2nd_ordre=effets,
            verification_12_6=verif_126,
            armatures=armatures,
        )

    # ------------------------------------------------------------------
    # Vérification à l'ELS à la section critique (rapport PFA §4.9)
    # ------------------------------------------------------------------
    def verifier_els(self, resultat: ResultatVoute, armatures: ArmaturesSection):
        """N_ser = N_Ed/1,35 ; M_ser = M_Ed/1,35 (section critique) ;
        sigma_c = N/(b.e) + 6.M/(b.e²) ; sigma_s = M/(As.z) - N/As, z = 0,9.d.
        `armatures.As1` est la section CHOISIE, en mm² par mètre."""
        from flexcomp.results.dataclasses import VerificationELS

        b, e = self.largeur_calcul, self.epaisseur                  # m
        d = e - self.enrobage_nominal - self.diametre_barre / 2     # m
        N_ser = resultat.section_critique.effort_normal / 1.35      # kN
        M_ser = resultat.effets_2nd_ordre.moment_calcul / 1.35      # kN.m
        sigma_c = (N_ser / (b * e) + 6 * M_ser / (b * e**2)) / 1000.0  # kN/m² -> MPa
        As = armatures.As1 * b                                      # mm² sur la bande
        z = 0.9 * d * 1000.0                                        # mm
        sigma_s = M_ser * 1e6 / (As * z) - N_ser * 1e3 / As if As > 0 else float("inf")
        if sigma_s < 0:
            # Acier non tendu : section (quasi) entièrement comprimée, la formule
            # fissurée ne s'applique pas -> section non fissurée : sigma_s = n.sigma_béton
            n = self.acier.Es / 30000.0
            y = d - e / 2                                           # m (sous le c.d.g.)
            inertie = b * e**3 / 12                                 # m^4
            sigma_b_acier = (N_ser / (b * e) - M_ser * y / inertie) / 1000.0  # MPa
            sigma_s = abs(n * sigma_b_acier)
        return VerificationELS(
            sigma_beton=sigma_c,
            sigma_beton_limite=self.beton.sigma_c_lim_els,
            sigma_acier=sigma_s,
            sigma_acier_limite=0.8 * self.acier.fyk,
        )
