"""Tests de non-régression : reproduisent les 3 exemples numériques chiffrés
du rapport PFA (Partie 2) et figent les résultats attendus.

Toute modification future du moteur de calcul (matériaux, formules, second
ordre...) doit continuer à faire passer ces tests, sauf correction volontaire
et documentée d'une erreur du rapport lui-même.
"""

import math

import pytest

from flexcomp.core import Acier, Beton, ConditionAppui
from flexcomp.elements import MurPorteur, PoteauRectangulaire, VouteTroisArticulations
from flexcomp.results import CasSection, Sollicitation
from flexcomp.sections import SectionRectangulaire


@pytest.fixture
def poteau() -> PoteauRectangulaire:
    beton = Beton(fck=25.0)
    acier = Acier(fyk=500.0)
    section = SectionRectangulaire(b=0.30, h=0.40, enrobage_nominal=0.03, diametre_barre=0.020)
    return PoteauRectangulaire(
        section=section, longueur_libre=3.5,
        condition_appui=ConditionAppui.ENCASTREMENT_ROTULE,
        beton=beton, acier=acier,
    )


class TestPoteauCas1PartiellementComprimee:
    def test_geometrie(self, poteau):
        assert poteau.section.d == pytest.approx(0.360, abs=1e-6)
        assert poteau.section.d_prime == pytest.approx(0.040, abs=1e-6)
        assert poteau.l0 == pytest.approx(2.45, abs=1e-6)

    def test_second_ordre(self, poteau):
        effets = poteau.effets_second_ordre(Sollicitation(N=800.0, M=120.0))
        assert effets.lambda_calcule == pytest.approx(21.22, abs=0.01)
        assert effets.lambda_limite == pytest.approx(17.04, abs=0.01)
        assert effets.second_ordre_necessaire is True
        assert effets.excentricite_totale * 100 == pytest.approx(16.58, abs=0.02)
        assert effets.moment_calcul == pytest.approx(132.64, abs=0.05)

    def test_armatures(self, poteau):
        resultat = poteau.dimensionner(Sollicitation(N=800.0, M=120.0))
        assert resultat.cas is CasSection.PARTIELLEMENT_COMPRIMEE
        assert resultat.armatures.As1 == pytest.approx(345.1, abs=0.5)
        assert resultat.armatures.As2 == pytest.approx(142.0, abs=0.5)


class TestPoteauCas2EntierementTendue:
    def test_armatures(self, poteau):
        resultat = poteau.dimensionner(Sollicitation(N=-350.0, M=40.0))
        assert resultat.cas is CasSection.ENTIEREMENT_TENDUE
        assert resultat.armatures.As1 == pytest.approx(144.0, abs=0.5)  # min gouverne
        assert resultat.armatures.As2 == pytest.approx(690.0, abs=1.0)


class TestPoteauCas3EntierementComprimee:
    def test_armatures(self, poteau):
        resultat = poteau.dimensionner(Sollicitation(N=1800.0, M=60.0))
        assert resultat.cas is CasSection.ENTIEREMENT_COMPRIMEE
        assert resultat.armatures.As1 == pytest.approx(207.0, abs=0.5)
        assert resultat.armatures.As2 == pytest.approx(207.0, abs=0.5)


@pytest.fixture
def voute() -> VouteTroisArticulations:
    return VouteTroisArticulations(
        portee=12.0, fleche=1.2, charge_uniforme=45.0, epaisseur=0.30,
        beton=Beton(fck=25.0), acier=Acier(fyk=500.0),
        largeur_calcul=1.0, enrobage_nominal=0.03, diametre_barre=0.012,
    )


class TestVouteTroisArticulations:
    def test_statique(self, voute):
        assert voute.poussee_horizontale == pytest.approx(675.0, abs=0.1)
        assert voute.rayon_arc == pytest.approx(15.60, abs=0.01)

    def test_moments_nuls_aux_rotules(self, voute):
        m0, m_clef, m_l = voute.moments_aux_rotules(tolerance=1e-6)
        assert m0 == pytest.approx(0.0, abs=1e-6)
        assert m_clef == pytest.approx(0.0, abs=1e-6)
        assert m_l == pytest.approx(0.0, abs=1e-6)

    def test_section_critique(self, voute):
        sc = voute.section_critique()
        assert sc.x == pytest.approx(1.72, abs=0.01)
        assert sc.moment == pytest.approx(-8.10, abs=0.05)
        assert sc.effort_normal == pytest.approx(596.46, rel=0.01)

    def test_dimensionnement_complet(self, voute):
        resultat = voute.dimensionner()
        assert resultat.verification_12_6.verifie is True
        assert resultat.armatures.As1 == pytest.approx(352.1, abs=1.0)


@pytest.fixture
def mur() -> MurPorteur:
    return MurPorteur(
        hauteur_libre=4.0, longueur_calcul=2.5, epaisseur=0.30, beta=1.0,
        beton=Beton(fck=40.0), acier=Acier(fyk=500.0), enrobage_nominal=0.03,
    )


class TestMurPorteur:
    def test_elancement(self, mur):
        assert mur.l0 == pytest.approx(4.0, abs=1e-6)
        assert mur.elancement == pytest.approx(46.2, abs=0.1)

    def test_trois_verifications(self, mur):
        resultat = mur.verifier_non_arme(N_Ed=712.5, V_Ed=171.0, e=0.0)
        assert resultat.verif_forces_axiales.N_Rd1 == pytest.approx(16000.0, rel=0.01)
        assert resultat.verif_effort_tranchant.f_cvd == pytest.approx(1.72, abs=0.02)
        assert resultat.verif_flambement.N_Rd12 == pytest.approx(11541.33, rel=0.01)
        assert resultat.calculable_non_arme is True


class TestMaterialsProperties:
    def test_beton_c25(self):
        b = Beton(fck=25.0)
        assert b.fcd == pytest.approx(16.67, abs=0.01)
        assert b.fcd_pl == pytest.approx(13.33, abs=0.01)
        assert b.sigma_c_lim_els == pytest.approx(15.0, abs=1e-6)

    def test_acier_b500(self):
        a = Acier(fyk=500.0)
        assert a.fyd == pytest.approx(434.78, abs=0.01)
        assert a.eps_yd == pytest.approx(2.174e-3, rel=0.01)
        assert a.sigma_s_lim_els == pytest.approx(400.0, abs=1e-6)

    def test_donnees_invalides_leve_exception(self):
        from flexcomp.core.exceptions import DonneesInvalidesError
        with pytest.raises(DonneesInvalidesError):
            Beton(fck=-25.0)
