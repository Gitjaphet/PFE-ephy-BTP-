"""Tests des figures techniques.

Comme pour l'interface, on teste le comportement et non les pixels : qu'une
figure se construise et se peigne sans lever d'exception pour chacune des
branches du moteur, et que les exports produisent un fichier non vide.

C'est suffisant pour attraper les régressions qui comptent vraiment ici :
un `QPainter.save()` sans `restore()`, une division par zéro sur une
géométrie limite, ou une classe de résultat dont un attribut a changé de
nom sans que le dessin suive.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6", reason="PyQt6 n'est pas installé")

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage, QPainter

from flexcomp.gui.adaptateur import calculer
from flexcomp.gui.app import creer_application
from flexcomp.gui.dessins import (
    CoupeHorizontaleMur,
    CoupeTransversalePoteau,
    DiagrammeMomentVoute,
    ElevationMur,
    ElevationPoteau,
    GeometrieVoute,
)

DONNEES_POTEAU_BASE = {
    "b": 30, "h": 40, "enrobage": 3, "diametre": 20, "longueur": 3.5,
    "fck": 25, "fyk": 500, "condition_appui": 0,
}
DONNEES_VOUTE = {
    "portee": 12, "fleche": 1.2, "epaisseur": 30, "largeur": 1,
    "charge": 45, "fck": 25, "fyk": 500, "enrobage": 3, "diametre": 12,
}
DONNEES_MUR = {
    "hauteur": 4, "longueur": 2.5, "epaisseur": 30, "enrobage": 3,
    "fck": 40, "fyk": 500, "N_elu": 712.5, "M_elu": 142.5,
    "V_elu": 171, "excentricite": 0, "beta": 0,
}


@pytest.fixture(scope="module")
def application():
    from PyQt6.QtWidgets import QApplication

    yield QApplication.instance() or creer_application([])


def peindre(figure, largeur: int = 600, hauteur: int = 500) -> QImage:
    """Peint la figure dans une image mémoire et la retourne."""
    image = QImage(largeur, hauteur, QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    peintre = QPainter(image)
    figure.dessiner(peintre, QRectF(20, 20, largeur - 40, hauteur - 40))
    peintre.end()
    return image


class TestFiguresPoteau:
    @pytest.mark.parametrize("N,M,libelle", [
        (800, 120, "cas 1 — partiellement comprimée"),
        (-350, 40, "cas 2 — entièrement tendue"),
        (1800, 60, "cas 3 — entièrement comprimée"),
    ])
    def test_figures_pour_les_trois_cas(self, application, N, M, libelle):
        """Chaque cas de section a son libellé de nappes : les trois doivent
        se dessiner, y compris la traction où il n'y a pas de flambement."""
        donnees = dict(DONNEES_POTEAU_BASE, N_elu=N, M_elu=M, N_els=None, M_els=None)
        sortie = calculer("poteau", donnees)
        for classe in (CoupeTransversalePoteau, ElevationPoteau):
            figure = classe(sortie["modele"], sortie["resultat"])
            image = peindre(figure)
            assert not image.isNull(), f"{classe.__name__} vide pour {libelle}"

    def test_toutes_conditions_appui(self, application):
        """Chaque condition d'appui dessine ses propres symboles."""
        for index in range(4):
            donnees = dict(
                DONNEES_POTEAU_BASE, N_elu=800, M_elu=120,
                N_els=None, M_els=None, condition_appui=index,
            )
            sortie = calculer("poteau", donnees)
            figure = ElevationPoteau(sortie["modele"], sortie["resultat"])
            assert not peindre(figure).isNull()

    def test_section_tres_elancee(self, application):
        """Géométrie extrême : le dessin ne doit pas diviser par zéro ni
        produire une échelle infinie."""
        donnees = dict(
            DONNEES_POTEAU_BASE, b=20, h=80, longueur=12,
            N_elu=400, M_elu=200, N_els=None, M_els=None,
        )
        sortie = calculer("poteau", donnees)
        figure = CoupeTransversalePoteau(sortie["modele"], sortie["resultat"])
        assert not peindre(figure).isNull()


class TestFiguresVoute:
    def test_geometrie_et_moment(self, application):
        sortie = calculer("voute", DONNEES_VOUTE)
        for classe in (GeometrieVoute, DiagrammeMomentVoute):
            figure = classe(sortie["modele"], sortie["resultat"])
            assert not peindre(figure).isNull()

    def test_voute_tres_surbaissee(self, application):
        """Flèche faible : le rayon devient grand, l'arc quasi plat."""
        sortie = calculer("voute", dict(DONNEES_VOUTE, fleche=0.4))
        figure = GeometrieVoute(sortie["modele"], sortie["resultat"])
        assert not peindre(figure).isNull()


class TestFiguresMur:
    def test_elevation_et_coupe(self, application):
        sortie = calculer("mur", DONNEES_MUR)
        for classe in (ElevationMur, CoupeHorizontaleMur):
            figure = classe(sortie["modele"], sortie["resultat"])
            assert not peindre(figure).isNull()

    def test_coupe_avec_excentricite_non_nulle(self, application):
        sortie = calculer("mur", dict(DONNEES_MUR, excentricite=5))
        figure = CoupeHorizontaleMur(
            sortie["modele"], sortie["resultat"], excentricite=0.05
        )
        assert not peindre(figure).isNull()


class TestExports:
    def test_export_png(self, application, tmp_path):
        sortie = calculer("poteau", dict(
            DONNEES_POTEAU_BASE, N_elu=800, M_elu=120, N_els=None, M_els=None
        ))
        figure = CoupeTransversalePoteau(sortie["modele"], sortie["resultat"])
        chemin = tmp_path / "coupe.png"
        figure.exporter_png(str(chemin), 800, 600)
        assert chemin.exists() and chemin.stat().st_size > 1000

    def test_export_pdf_vectoriel(self, application, tmp_path):
        """L'export PDF réutilise le même code de dessin que l'écran."""
        sortie = calculer("voute", DONNEES_VOUTE)
        figure = GeometrieVoute(sortie["modele"], sortie["resultat"])
        chemin = tmp_path / "voute.pdf"
        figure.exporter_pdf(str(chemin))
        assert chemin.exists() and chemin.stat().st_size > 1000
        assert chemin.read_bytes().startswith(b"%PDF")


class TestPanneauFigures:
    def test_panneau_dans_la_page_resultats(self, application):
        """La page de résultats doit embarquer son panneau de figures pour
        les trois éléments."""
        from flexcomp.gui.pages.resultats import PageResultats
        from flexcomp.gui.widgets.panneau_figures import PanneauFigures

        cas = [
            ("poteau", dict(DONNEES_POTEAU_BASE, N_elu=800, M_elu=120,
                            N_els=580, M_els=85)),
            ("voute", DONNEES_VOUTE),
            ("mur", DONNEES_MUR),
        ]
        for element, donnees in cas:
            page = PageResultats(element, calculer(element, donnees))
            panneau = page.findChild(PanneauFigures)
            assert panneau is not None, f"pas de figures pour {element}"
            assert panneau.onglets.count() == 2
