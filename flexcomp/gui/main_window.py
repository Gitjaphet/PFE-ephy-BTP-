"""Fenêtre principale : assemblage des pages et navigation.

La navigation suit un parcours linéaire en trois étapes (choix → saisie →
résultats), matérialisé par le bandeau latéral. Les pages ne se connaissent
pas entre elles : elles émettent des signaux, la fenêtre décide de la suite.
Ce découplage permet d'insérer une étape (par exemple « choix des barres »)
sans toucher aux pages existantes.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from flexcomp.core.exceptions import FlexcompError
from flexcomp.gui.adaptateur import calculer
from flexcomp.gui.assets import visuels
from flexcomp.gui.pages.accueil import ELEMENTS, PageAccueil
from flexcomp.gui.pages.resultats import PageResultats
from flexcomp.gui.pages.saisie import PageSaisie
from flexcomp.gui.theme import METRIQUES, PALETTE, feuille_de_style

ETAPES = ("Choix de l'élément", "Données d'entrée", "Résultats")


class BandeauLateral(QFrame):
    """Colonne sombre affichant l'identité du logiciel et l'étape courante."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Bandeau")
        self.setFixedWidth(METRIQUES.largeur_bandeau)

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(
            METRIQUES.pad_lg, METRIQUES.pad_lg, METRIQUES.pad_lg, METRIQUES.pad_lg
        )
        disposition.setSpacing(METRIQUES.pad_md)

        image = QLabel()
        image.setPixmap(visuels.logo(44, sur_fond_sombre=True))
        disposition.addWidget(image)

        nom = QLabel("flexcomp")
        nom.setStyleSheet(
            f"color: {PALETTE.texte_inverse}; font-size: 14pt; font-weight: 600;"
        )
        disposition.addWidget(nom)


        disposition.addSpacing(METRIQUES.pad_xl)

        self._labels_etapes: list[QLabel] = []
        for index, etape in enumerate(ETAPES):
            label = QLabel(f"{index + 1}.  {etape}")
            label.setObjectName("BandeauEtape")
            self._labels_etapes.append(label)
            disposition.addWidget(label)

        disposition.addStretch()

        credit = QLabel("JEPHY Marinho\nESP Antsiranana\nPromotion Mahery")
        credit.setStyleSheet(
            f"color: {PALETTE.texte_tertiaire}; font-size: 12pt; line-height: 1.5;"
        )
        disposition.addWidget(credit)

    def definir_etape(self, index: int) -> None:
        """Met en évidence l'étape courante."""
        for position, label in enumerate(self._labels_etapes):
            label.setObjectName(
                "BandeauEtapeActive" if position == index else "BandeauEtape"
            )
            label.style().unpolish(label)
            label.style().polish(label)


class FenetrePrincipale(QMainWindow):
    """Fenêtre unique de l'application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("flexcomp — Calcul en flexion composée")
        self.resize(METRIQUES.largeur_fenetre, METRIQUES.hauteur_fenetre)
        self.setMinimumSize(980, 640)

        self._element_courant: Optional[str] = None
        self._page_saisie: Optional[PageSaisie] = None
        self._page_resultats: Optional[PageResultats] = None

        racine = QWidget()
        disposition = QHBoxLayout(racine)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)

        self.bandeau = BandeauLateral()
        disposition.addWidget(self.bandeau)

        self.pages = QStackedWidget()
        disposition.addWidget(self.pages, stretch=1)

        self.page_accueil = PageAccueil()
        self.page_accueil.element_choisi.connect(self._ouvrir_saisie)
        self.pages.addWidget(self.page_accueil)

        self.setCentralWidget(racine)
        self.bandeau.definir_etape(0)

    # ------------------------------------------------------------------
    def _ouvrir_saisie(self, identifiant: str) -> None:
        self._element_courant = identifiant
        if self._page_saisie is not None:
            self.pages.removeWidget(self._page_saisie)
            self._page_saisie.deleteLater()

        self._page_saisie = PageSaisie(identifiant)
        self._page_saisie.calcul_demande.connect(self._lancer_calcul)
        self._page_saisie.retour_demande.connect(self._revenir_accueil)
        self.pages.addWidget(self._page_saisie)
        self.pages.setCurrentWidget(self._page_saisie)
        self.bandeau.definir_etape(1)

        titre = next(e["titre"] for e in ELEMENTS if e["id"] == identifiant)
        self.setWindowTitle(f"flexcomp — {titre}")

    def _lancer_calcul(self, donnees: dict) -> None:
        """Exécute le calcul et bascule vers les résultats.

        Les erreurs métier (`FlexcompError`) sont présentées à l'utilisateur
        en langage clair ; toute autre exception remonte, car elle signale un
        défaut du logiciel qu'il ne faut pas masquer.
        """
        try:
            sortie = calculer(self._element_courant, donnees)
        except FlexcompError as erreur:
            QMessageBox.warning(
                self,
                "Données incompatibles",
                f"Le calcul n'a pas pu aboutir :\n\n{erreur}\n\n"
                "Vérifiez les valeurs saisies.",
            )
            return

        if self._page_resultats is not None:
            self.pages.removeWidget(self._page_resultats)
            self._page_resultats.deleteLater()

        self._page_resultats = PageResultats(self._element_courant, sortie)
        self._page_resultats.retour_demande.connect(self._revenir_saisie)
        self._page_resultats.nouveau_calcul_demande.connect(self._revenir_accueil)
        self.pages.addWidget(self._page_resultats)
        self.pages.setCurrentWidget(self._page_resultats)
        self.bandeau.definir_etape(2)

    def _revenir_saisie(self) -> None:
        if self._page_saisie is not None:
            self.pages.setCurrentWidget(self._page_saisie)
            self.bandeau.definir_etape(1)

    def _revenir_accueil(self) -> None:
        self.pages.setCurrentWidget(self.page_accueil)
        self.bandeau.definir_etape(0)
        self.setWindowTitle("flexcomp — Calcul en flexion composée")
