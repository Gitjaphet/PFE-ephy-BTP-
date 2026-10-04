"""Poteau de section circulaire en flexion composée.

Même démarche que le poteau rectangulaire (rapport PFA, Partie 2) :
élancement -> effets du 2nd ordre -> e_tot, M*_Ed -> cas de section ->
armatures ELU -> As,min / As,max -> choix des barres -> ELS.

Différence de méthode : les barres étant réparties sur le pourtour, la
méthode du moment réduit (deux nappes) ne s'applique pas. Les armatures sont
obtenues par l'équilibre direct de la section (diagramme d'interaction) :
- béton : bloc rectangulaire de hauteur a = 0,8.x sur un segment circulaire ;
- pivot B (eps_cu2 = 3,5 ‰) si x <= D, pivot C au-delà ;
- acier élasto-plastique à palier horizontal.
Unités d'entrée : m, kN, kN.m (comme le poteau rectangulaire).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from flexcomp.core.armatures_reglementaires import as_max_poteau, as_min_poteau
from flexcomp.core.elancement import (
    ConditionAppui, elancement_limite, longueur_flambement, longueur_flambement_portique,
)
from flexcomp.core.materials import Acier, Beton
from flexcomp.results.dataclasses import (
    ArmaturesSection, CasSection, EffetsSecondOrdre, Sollicitation, VerificationELS,
)

EPS_CU2 = 3.5e-3
EPS_C2 = 2.0e-3
E_CM = 30000.0          # MPa, comme le poteau rectangulaire


@dataclass(frozen=True)
class ResultatPoteauCirculaire:
    sollicitation_elu: Sollicitation
    effets_2nd_ordre: EffetsSecondOrdre | None   # None en traction
    cas: CasSection
    x: float                    # profondeur de l'axe neutre à l'ELU (mm)
    M_Rd_beton: float           # moment résistant du béton seul sous N_Ed (kN.m)
    armatures: ArmaturesSection  # As1 = section TOTALE (répartie sur n barres), As2 = 0
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PoteauCirculaire:
    diametre: float             # D (m)
    longueur_libre: float       # l (m)
    condition_appui: ConditionAppui
    beton: Beton
    acier: Acier
    enrobage_nominal: float = 0.03
    diametre_barre: float = 0.020   # pour d' = c + phi/2
    nombre_barres: int = 8          # >= 6 (EC2 §9.5.2(4))
    k1: float = 0.1
    k2: float = 0.1

    # ------------------------------------------------------------------
    # Géométrie (mm)
    # ------------------------------------------------------------------
    @property
    def D(self) -> float:
        return self.diametre * 1000

    @property
    def d_prime(self) -> float:
        return (self.enrobage_nominal + self.diametre_barre / 2) * 1000

    @property
    def rs(self) -> float:
        """Rayon du cercle des armatures (mm)."""
        return self.D / 2 - self.d_prime

    @property
    def aire_beton(self) -> float:
        """Ac en m² (comme SectionRectangulaire.aire_beton)."""
        return math.pi * self.diametre**2 / 4

    @property
    def Ac(self) -> float:
        return self.aire_beton * 1e6

    @property
    def rayon_giration(self) -> float:
        return self.diametre / 4      # m

    @property
    def d_courbure(self) -> float:
        """d = D/2 + is, is = rs/sqrt(2) (EC2 §5.8.8.3(2)), en mm."""
        return self.D / 2 + self.rs / math.sqrt(2)

    @property
    def fyd(self) -> float:
        return getattr(self.acier, "fyd", self.acier.fyk / 1.15)

    @property
    def l0(self) -> float:
        if self.condition_appui in (ConditionAppui.PORTIQUE_NON_INTEGRE, ConditionAppui.PORTIQUE_INTEGRE):
            return longueur_flambement_portique(
                self.longueur_libre, self.k1, self.k2,
                contrevente=self.condition_appui is ConditionAppui.PORTIQUE_NON_INTEGRE,
            )
        return longueur_flambement(self.longueur_libre, self.condition_appui)

    @property
    def elancement(self) -> float:
        return self.l0 / self.rayon_giration

    def positions_barres(self) -> list[float]:
        """y_k (mm) depuis le centre, + vers la fibre la plus comprimée ; barre 1 en haut."""
        n = self.nombre_barres
        return [self.rs * math.cos(2 * math.pi * k / n) for k in range(n)]

    # ------------------------------------------------------------------
    # Excentricités et second ordre (même formules que le rectangle)
    # ------------------------------------------------------------------
    def effets_second_ordre(self, s: Sollicitation) -> EffetsSecondOrdre:
        lam = self.elancement
        n = s.N * 1e3 / (self.Ac * self.beton.fcd)
        lam_lim = elancement_limite(n)
        e1 = abs(s.M / s.N)
        ei = self.l0 / 400
        e2 = 0.0
        if lam > lam_lim:
            k_phi = max(1.0, 1 + 0.35 * self.beton.fck / 200 + lam / 150)
            inv_r = k_phi * (self.fyd / self.acier.Es) / (0.45 * self.d_courbure / 1000)
            e2 = inv_r * self.l0**2 / math.pi**2
        e_min = max(0.020, self.diametre / 30)
        e_tot = max(e1 + ei + e2, e_min)
        return EffetsSecondOrdre(
            lambda_calcule=lam, lambda_limite=lam_lim, second_ordre_necessaire=lam > lam_lim,
            excentricite_1er_ordre=e1, excentricite_imperfection=ei, excentricite_2nd_ordre=e2,
            excentricite_totale=e_tot, excentricite_min=e_min, moment_calcul=s.N * e_tot,
        )

    # ------------------------------------------------------------------
    # Équilibre de la section à l'ELU (N en N, M en N.mm)
    # ------------------------------------------------------------------
    def _segment(self, a: float) -> tuple[float, float]:
        """Aire (mm²) et distance au centre (mm) du segment comprimé de hauteur a."""
        D = self.D
        if a <= 0:
            return 0.0, 0.0
        if a >= D:
            return self.Ac, 0.0
        al = math.acos(1 - 2 * a / D)
        A = D**2 / 8 * (2 * al - math.sin(2 * al))
        return A, D**3 * math.sin(al) ** 3 / (12 * A)

    def _deformation(self, x: float, z: float) -> float:
        """Raccourcissement (+) à la profondeur z ; pivot B si x <= D, C sinon."""
        if x <= self.D:
            return EPS_CU2 * (x - z) / x
        return EPS_C2 * (x - z) / (x - 3 * self.D / 7)

    def resistance(self, x: float, As: float) -> tuple[float, float]:
        """(N_Rd, M_Rd) en N et N.mm pour un axe neutre x (mm) et une section totale As (mm²)."""
        A, yc = self._segment(0.8 * x)
        Fc = A * self.beton.fcd
        N, M = Fc, Fc * yc
        ab = As / self.nombre_barres
        for y in self.positions_barres():
            s = max(-self.fyd, min(self.fyd, self.acier.Es * self._deformation(x, self.D / 2 - y)))
            N += ab * s
            M += ab * s * y
        return N, M

    def axe_neutre(self, As: float, N_Ed: float) -> float:
        """x (mm) tel que N_Rd = N_Ed (N_Rd croît avec x)."""
        lo, hi = 1e-3, 3 * self.D
        for _ in range(100):
            m = (lo + hi) / 2
            if self.resistance(m, As)[0] < N_Ed:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2

    def moment_resistant(self, As: float, N_kN: float) -> tuple[float, float]:
        """(x en mm, M_Rd en kN.m) de la section As (mm²) sous N (kN)."""
        x = self.axe_neutre(As, N_kN * 1e3)
        return x, self.resistance(x, As)[1] / 1e6

    # ------------------------------------------------------------------
    # Dimensionnement ELU
    # ------------------------------------------------------------------
    def dimensionner(self, s: Sollicitation) -> ResultatPoteauCirculaire:
        notes: list[str] = []
        if s.N < 0:
            effets = None
            M_star = abs(s.M)
            As_traction = abs(s.N) * 1e3 / self.fyd
            notes.append(f"Traction : As >= |N_Ed|/f_yd = {As_traction:.0f} mm².")
            As_lo = As_traction * 1.0001
        else:
            effets = self.effets_second_ordre(s)
            M_star = effets.moment_calcul
            As_lo = 0.0

        x0, M0 = self.moment_resistant(As_lo, s.N) if s.N >= 0 else (0.0, 0.0)
        if s.N >= 0 and M0 >= M_star:
            As = 0.0
            notes.append("Le béton seul équilibre les sollicitations : les armatures minimales gouvernent.")
        else:
            lo, hi = As_lo, 0.08 * self.Ac
            for _ in range(80):
                m = (lo + hi) / 2
                if self.moment_resistant(m, s.N)[1] < M_star:
                    lo = m
                else:
                    hi = m
            As = (lo + hi) / 2
        x = self.axe_neutre(As, s.N * 1e3)
        cas = CasSection.ENTIEREMENT_COMPRIMEE if x >= self.D else CasSection.PARTIELLEMENT_COMPRIMEE
        if s.N < 0 and x <= 1e-2:
            cas = CasSection.ENTIEREMENT_TENDUE

        as_min = as_min_poteau(abs(s.N), self.aire_beton, self.acier)
        armatures = ArmaturesSection(
            As1=max(As, as_min), As2=0.0, As_min=as_min, As_max=as_max_poteau(self.aire_beton),
            cas=cas, commentaire=f"Section totale répartie sur {self.nombre_barres} barres (équilibre direct).",
        )
        return ResultatPoteauCirculaire(
            sollicitation_elu=s, effets_2nd_ordre=effets, cas=cas, x=x,
            M_Rd_beton=M0, armatures=armatures, notes=tuple(notes),
        )

    def verifier_resistance(self, s: Sollicitation, As_choisie: float,
                            resultat: ResultatPoteauCirculaire) -> tuple[float, float, bool]:
        """(x, M_Rd, vérifié) avec la section réellement choisie (mm²)."""
        M_star = abs(s.M) if resultat.effets_2nd_ordre is None else resultat.effets_2nd_ordre.moment_calcul
        x, M_Rd = self.moment_resistant(As_choisie, s.N)
        return x, M_Rd, M_Rd >= M_star - 1e-6

    # ------------------------------------------------------------------
    # ELS : section homogène si N_ser > 0 (comme le rectangle), fissurée sinon
    # ------------------------------------------------------------------
    def verifier_els(self, s_ser: Sollicitation, As_choisie: float) -> VerificationELS:
        n_mod = self.acier.Es / E_CM
        ys = self.positions_barres()
        ab = As_choisie / self.nombre_barres
        N, M = s_ser.N * 1e3, abs(s_ser.M) * 1e6
        lim_s = 0.8 * self.acier.fyk
        if N > 0:
            A_hom = self.Ac + (n_mod - 1) * As_choisie
            I_hom = math.pi * self.D**4 / 64 + (n_mod - 1) * sum(ab * y * y for y in ys)
            s_c = N / A_hom + M * (self.D / 2) / I_hom
            s_s = max(abs(n_mod * (N / A_hom + M * y / I_hom)) for y in ys)
            return VerificationELS(s_c, self.beton.sigma_c_lim_els, s_s, lim_s)
        x, s_top = self._els_fissure(N, M, As_choisie, n_mod)
        s_s = max(abs(n_mod * s_top * (x - (self.D / 2 - y)) / x) for y in ys)
        return VerificationELS(s_top, self.beton.sigma_c_lim_els, s_s, lim_s)

    def _els_fissure(self, N: float, M: float, As: float, n_mod: float, nb: int = 600):
        """Béton tendu négligé : axe neutre x et contrainte béton en fibre supérieure."""
        D, ys, ab = self.D, self.positions_barres(), As / self.nombre_barres

        def efforts(x):          # efforts pour une contrainte unité en fibre supérieure
            Nx = Mx = 0.0
            dz = min(x, D) / nb
            for j in range(nb):
                z = (j + 0.5) * dz
                y = D / 2 - z
                w = 2 * math.sqrt(max(0.0, (D / 2) ** 2 - y * y))
                sg = (x - z) / x
                Nx += sg * w * dz
                Mx += sg * w * dz * y
            for y in ys:
                z = D / 2 - y
                sg = n_mod * (x - z) / x - ((x - z) / x if z < x else 0.0)
                Nx += ab * sg
                Mx += ab * sg * y
            return Nx, Mx

        def ecart(x):
            Nx, Mx = efforts(x)
            st = N / Nx if Nx else -1
            return (Mx * st - M) if st > 0 else None

        prec = None
        for k in range(2, 1200):
            x = D * k / 400
            g = ecart(x)
            if g is not None and prec is not None and prec[1] * g <= 0:
                lo, hi = prec[0], x
                for _ in range(50):
                    m = (lo + hi) / 2
                    if ecart(lo) * ecart(m) <= 0:
                        hi = m
                    else:
                        lo = m
                x = (lo + hi) / 2
                return x, N / efforts(x)[0]
            prec = (x, g) if g is not None else None
        raise ValueError("Position de l'axe neutre à l'ELS introuvable.")
