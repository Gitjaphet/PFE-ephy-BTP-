"""Tests de l'interface graphique.

Ils vérifient le *comportement* (navigation, validation, conversion
d'unités), pas l'apparence : un test qui compare des pixels casse au moindre
changement de thème et n'apporte rien. Ce qui compte ici, c'est que
l'interface ne puisse pas envoyer de données incohérentes au moteur.

Exécution sans écran : QT_QPA_PLATFORM=offscreen pytest tests/
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6", reason="PyQt6 n'est pas installé")

from flexcomp.gui.adaptateur import calculer
from flexcomp.gui.app import creer_application
from flexcomp.gui.main_window import FenetrePrincipale
from flexcomp.gui.pages.schemas_saisie import SCHEMAS
from flexcomp.results import CasSection


@pytest.fixture(scope="module")
def application():
    """Une seule QApplication pour tout le module (Qt n'en tolère qu'une)."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or creer_application([])
    yield app


@pytest.fixture
def fenetre(application):
    fen = FenetrePrincipale()
    yield fen
    fen.close()


class TestNavigation:
    def test_demarre_sur_accueil(self, fenetre):
        assert fenetre.pages.currentWidget() is fenetre.page_accueil

    def test_bouton_continuer_desactive_sans_selection(self, fenetre):
        assert fenetre.page_accueil.bouton.isEnabled() is False

    def test_selection_active_le_bouton(self, fenetre):
        fenetre.page_accueil._selectionner("poteau")
        assert fenetre.page_accueil.bouton.isEnabled() is True

    @pytest.mark.parametrize("element", ["poteau", "voute", "mur"])
    def test_ouverture_saisie_pour_chaque_element(self, fenetre, element):
        fenetre._ouvrir_saisie(element)
        assert fenetre.pages.currentWidget() is fenetre._page_saisie
        assert fenetre._page_saisie.identifiant == element

    def test_retour_depuis_saisie(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        fenetre._revenir_accueil()
        assert fenetre.pages.currentWidget() is fenetre.page_accueil


class TestValidationSaisie:
    def test_champ_vide_bloque_le_calcul(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["b"].saisie.setText("")

        recu = []
        page.calcul_demande.connect(recu.append)
        page._valider_et_calculer()

        assert recu == []  # aucun calcul lancé
        # isVisibleTo plutôt que isVisible : la fenêtre n'est pas affichée
        # à l'écran pendant les tests, mais l'état du widget est bien mis à jour.
        assert page._champs["b"].erreur.isVisibleTo(page)
        assert page._champs["b"].erreur.text() == "Champ requis"

    def test_valeur_negative_refusee_sur_geometrie(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["h"].saisie.setText("-40")

        recu = []
        page.calcul_demande.connect(recu.append)
        page._valider_et_calculer()

        assert recu == []
        assert page._champs["h"].erreur.isVisibleTo(page)
        assert page._champs["h"].saisie.property("invalide") == "true"

    def test_effort_normal_negatif_accepte(self, fenetre):
        """Un N négatif est une traction, pas une erreur de saisie."""
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["N_elu"].saisie.setText("-350")
        page._champs["M_elu"].saisie.setText("40")
        page._champs["N_els"].saisie.setText("")
        page._champs["M_els"].saisie.setText("")

        recu = []
        page.calcul_demande.connect(recu.append)
        page._valider_et_calculer()

        assert len(recu) == 1
        assert recu[0]["N_elu"] == -350.0

    def test_virgule_decimale_acceptee(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["longueur"].saisie.setText("3,5")
        assert page._champs["longueur"].valeur() == pytest.approx(3.5)

    def test_reinitialiser_restaure_les_defauts(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["b"].saisie.setText("99")
        page._reinitialiser()
        assert page._champs["b"].saisie.text() == "30"

    def test_champs_facultatifs_peuvent_rester_vides(self, fenetre):
        fenetre._ouvrir_saisie("poteau")
        page = fenetre._page_saisie
        page._champs["N_els"].saisie.setText("")
        page._champs["M_els"].saisie.setText("")

        recu = []
        page.calcul_demande.connect(recu.append)
        page._valider_et_calculer()

        assert len(recu) == 1
        assert recu[0]["N_els"] is None


class TestAdaptateurUnites:
    """L'adaptateur est la seule frontière de conversion d'unités : s'il se
    trompe, tout le reste est faux en silence."""

    def test_conversion_cm_vers_metres_poteau(self):
        sortie = calculer("poteau", {
            "b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
            "fck": 25, "fyk": 500, "N_elu": 800, "M_elu": 120,
            "N_els": None, "M_els": None, "condition_appui": 0,
        })
        section = sortie["modele"].section
        assert section.b == pytest.approx(0.30)
        assert section.h == pytest.approx(0.40)
        assert section.d == pytest.approx(0.360)

    def test_resultat_poteau_cas1_conforme_au_rapport(self):
        sortie = calculer("poteau", {
            "b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
            "fck": 25, "fyk": 500, "N_elu": 800, "M_elu": 120,
            "N_els": 580, "M_els": 85, "condition_appui": 0,
        })
        resultat = sortie["resultat"]
        assert resultat.cas is CasSection.PARTIELLEMENT_COMPRIMEE
        assert resultat.armatures.As1 == pytest.approx(345.1, abs=0.5)
        assert resultat.armatures.As2 == pytest.approx(142.0, abs=0.5)
        assert sortie["verification_els"] is not None

    def test_els_ignore_si_champs_vides(self):
        sortie = calculer("poteau", {
            "b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
            "fck": 25, "fyk": 500, "N_elu": 800, "M_elu": 120,
            "N_els": None, "M_els": None, "condition_appui": 0,
        })
        assert sortie["verification_els"] is None

    def test_resultat_voute_conforme_au_rapport(self):
        sortie = calculer("voute", {
            "portee": 12, "fleche": 1.2, "epaisseur": 30, "largeur": 1,
            "charge": 45, "fck": 25, "fyk": 500, "enrobage": 3, "diametre": 12,
        })
        resultat = sortie["resultat"]
        assert resultat.poussee_horizontale == pytest.approx(675.0, abs=0.1)
        assert resultat.section_critique.x == pytest.approx(1.72, abs=0.01)

    def test_resultat_mur_conforme_au_rapport(self):
        sortie = calculer("mur", {
            "hauteur": 4, "longueur": 2.5, "epaisseur": 30, "enrobage": 3,
            "fck": 40, "fyk": 500, "N_elu": 712.5, "M_elu": 142.5,
            "V_elu": 171, "excentricite": 0, "beta": 0,
        })
        resultat = sortie["resultat"]
        assert resultat.verif_forces_axiales.N_Rd1 == pytest.approx(16000.0, rel=0.01)
        assert resultat.calculable_non_arme is True


class TestPagesResultats:
    @pytest.mark.parametrize("element,donnees", [
        ("poteau", {"b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
                     "fck": 25, "fyk": 500, "N_elu": 800, "M_elu": 120,
                     "N_els": 580, "M_els": 85, "condition_appui": 0}),
        ("poteau", {"b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
                     "fck": 25, "fyk": 500, "N_elu": -350, "M_elu": 40,
                     "N_els": None, "M_els": None, "condition_appui": 0}),
        ("poteau", {"b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
                     "fck": 25, "fyk": 500, "N_elu": 1800, "M_elu": 60,
                     "N_els": 1300, "M_els": 42, "condition_appui": 0}),
        ("voute", {"portee": 12, "fleche": 1.2, "epaisseur": 30, "largeur": 1,
                    "charge": 45, "fck": 25, "fyk": 500, "enrobage": 3, "diametre": 12}),
        ("mur", {"hauteur": 4, "longueur": 2.5, "epaisseur": 30, "enrobage": 3,
                  "fck": 40, "fyk": 500, "N_elu": 712.5, "M_elu": 142.5,
                  "V_elu": 171, "excentricite": 0, "beta": 0}),
    ])
    def test_page_resultats_se_construit(self, fenetre, element, donnees):
        """Les trois cas du poteau + voûte + mur doivent tous s'afficher sans
        exception : c'est la garantie que l'affichage conditionnel couvre
        bien toutes les branches du moteur."""
        fenetre._ouvrir_saisie(element)
        fenetre._lancer_calcul(donnees)
        assert fenetre._page_resultats is not None
        assert fenetre.pages.currentWidget() is fenetre._page_resultats


class TestSchemasFormulaires:
    @pytest.mark.parametrize("element", ["poteau", "voute", "mur"])
    def test_toutes_les_cles_sont_uniques(self, element):
        cles = [c.cle for g in SCHEMAS[element].groupes for c in g.champs]
        assert len(cles) == len(set(cles))

    @pytest.mark.parametrize("element", ["poteau", "voute", "mur"])
    def test_tous_les_champs_ont_un_defaut(self, element):
        for groupe in SCHEMAS[element].groupes:
            for champ in groupe.champs:
                assert champ.defaut != "", f"{element}.{champ.cle} sans valeur par défaut"
