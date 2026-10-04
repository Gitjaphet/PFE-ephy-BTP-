"""Page d'accueil : identité du projet et choix de l'élément à calculer."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flexcomp.gui.assets import visuels
from flexcomp.gui.theme import METRIQUES, PALETTE
from flexcomp.gui.widgets.composants import CarteSelection, separateur

# Catalogue des éléments calculables. Ajouter un élément au logiciel se
# réduit à ajouter une entrée ici + un formulaire dans `pages/saisie.py`.
ELEMENTS = [
    {
        "id": "poteau",
        "titre": "Poteau rectangulaire",
        "description": "Section b×h, trois cas de flexion composée, effets du second ordre",
        "pictogramme": visuels.pictogramme_poteau,
    },
    {
        "id": "poteau_circ",
        "titre": "Poteau circulaire",
        "description": "Section circulaire, armatures réparties, effets du second ordre",
        "pictogramme": visuels.pictogramme_poteau_circ,
    },
    {
        "id": "voute",
        "titre": "Voûte à trois articulations",
        "description": "Arc surbaissé, poussée de Mesnager, section critique",
        "pictogramme": visuels.pictogramme_voute,
    },
    {
        "id": "mur",
        "titre": "Voile",
        "description": "Vérifications du béton non armé, flexion composée dans le plan",
        "pictogramme": visuels.pictogramme_mur,
    },
]


class PageAccueil(QWidget):
    """Écran d'ouverture. Émet `element_choisi` quand l'utilisateur valide."""

    element_choisi = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selection: Optional[str] = None
        self._cartes: dict[str, CarteSelection] = {}
        self._construire()

    def _construire(self) -> None:
        exterieur = QVBoxLayout(self)
        exterieur.setContentsMargins(
            METRIQUES.pad_xxl, METRIQUES.pad_xl, METRIQUES.pad_xxl, METRIQUES.pad_xl
        )
        exterieur.setSpacing(METRIQUES.pad_lg)

        exterieur.addStretch(1)
        exterieur.addLayout(self._en_tete())
        exterieur.addSpacing(METRIQUES.pad_sm)
        exterieur.addWidget(separateur())
        exterieur.addSpacing(METRIQUES.pad_sm)
        exterieur.addLayout(self._zone_selection())
        exterieur.addSpacing(METRIQUES.pad_md)
        exterieur.addLayout(self._pied_de_page())
        exterieur.addStretch(1)

    def _en_tete(self) -> QHBoxLayout:
        ligne = QHBoxLayout()
        ligne.setSpacing(METRIQUES.pad_lg)

        image = QLabel()
        image.setPixmap(visuels.logo(76))
        image.setAlignment(Qt.AlignmentFlag.AlignTop)
        ligne.addWidget(image)

        textes = QVBoxLayout()
        textes.setSpacing(METRIQUES.pad_xs)

        titre = QLabel("Calcul des éléments en flexion composée")
        titre.setObjectName("Titre")
        textes.addWidget(titre)


        ligne.addLayout(textes)
        ligne.addStretch()
        return ligne

    def _zone_selection(self) -> QVBoxLayout:
        zone = QVBoxLayout()
        zone.setSpacing(METRIQUES.pad_md)

        consigne = QLabel("Sélectionnez l'élément à calculer")
        consigne.setStyleSheet(
            f"font-size: 12pt; font-weight: 600; color: {PALETTE.texte};"
        )
        zone.addWidget(consigne)

        grille = QHBoxLayout()
        grille.setSpacing(METRIQUES.pad_md)
        for element in ELEMENTS:
            carte = CarteSelection(
                identifiant=element["id"],
                titre=element["titre"],
                description=element["description"],
                pictogramme=element["pictogramme"](),
            )
            carte.clique.connect(self._selectionner)
            self._cartes[element["id"]] = carte
            grille.addWidget(carte)
        zone.addLayout(grille)
        return zone

    def _pied_de_page(self) -> QHBoxLayout:
        ligne = QHBoxLayout()

        self.legende = QLabel("Aucun élément sélectionné")
        self.legende.setObjectName("Legende")
        ligne.addWidget(self.legende)
        ligne.addStretch()

        self.bouton = QPushButton("Continuer")
        self.bouton.setObjectName("Principal")
        self.bouton.setEnabled(False)
        self.bouton.setMinimumWidth(150)
        self.bouton.clicked.connect(self._continuer)
        ligne.addWidget(self.bouton)
        return ligne

    def _selectionner(self, identifiant: str) -> None:
        self._selection = identifiant
        for cle, carte in self._cartes.items():
            carte.definir_selection(cle == identifiant)
        element = next(e for e in ELEMENTS if e["id"] == identifiant)
        self.legende.setText(element['titre'])
        self.bouton.setEnabled(True)

    def _continuer(self) -> None:
        if self._selection:
            self.element_choisi.emit(self._selection)
