"""Page de saisie des données d'entrée.

Se construit entièrement à partir du `SchemaFormulaire` de l'élément choisi
(`pages/schemas_saisie.py`) : aucune disposition n'est codée en dur par
élément, donc un nouvel élément hérite gratuitement de la même ergonomie.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from flexcomp.gui.pages.schemas_saisie import SCHEMAS, SchemaFormulaire
from flexcomp.gui.theme import METRIQUES, PALETTE
from flexcomp.gui.widgets.composants import (
    ChampNumerique,
    carte,
    separateur,
    titre_section,
)


class PageSaisie(QWidget):
    """Formulaire de saisie. Émet `calcul_demande(dict)` une fois validé."""

    calcul_demande = pyqtSignal(dict)
    retour_demande = pyqtSignal()

    def __init__(self, identifiant_element: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.identifiant = identifiant_element
        self.schema: SchemaFormulaire = SCHEMAS[identifiant_element]
        self._champs: dict[str, ChampNumerique] = {}
        self._options: dict[str, QComboBox] = {}
        self._construire()

    def _construire(self) -> None:
        exterieur = QVBoxLayout(self)
        exterieur.setContentsMargins(
            METRIQUES.pad_xl, METRIQUES.pad_lg, METRIQUES.pad_xl, METRIQUES.pad_lg
        )
        exterieur.setSpacing(METRIQUES.pad_md)

        exterieur.addLayout(self._en_tete())
        exterieur.addWidget(separateur())

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        contenu = QWidget()
        self._corps = QVBoxLayout(contenu)
        self._corps.setContentsMargins(0, METRIQUES.pad_md, 0, METRIQUES.pad_md)
        self._corps.setSpacing(METRIQUES.pad_md)

        for groupe in self.schema.groupes:
            self._corps.addWidget(self._construire_groupe(groupe))
        if self.schema.options:
            self._corps.addWidget(self._construire_options())
        self._corps.addStretch()

        defilement.setWidget(contenu)
        exterieur.addWidget(defilement, stretch=1)

        exterieur.addWidget(separateur())
        exterieur.addLayout(self._barre_actions())

    def _en_tete(self) -> QVBoxLayout:
        colonne = QVBoxLayout()
        colonne.setSpacing(METRIQUES.pad_xs)
        titre = QLabel(self.schema.titre)
        titre.setObjectName("TitrePage")
        colonne.addWidget(titre)
        description = QLabel(self.schema.description)
        description.setObjectName("Legende")
        colonne.addWidget(description)
        return colonne

    def _construire_groupe(self, groupe) -> QWidget:
        cadre, disposition = carte()
        disposition.addWidget(titre_section(groupe.titre))

        grille = QGridLayout()
        grille.setHorizontalSpacing(METRIQUES.pad_lg)
        grille.setVerticalSpacing(METRIQUES.pad_md)
        for index, champ in enumerate(groupe.champs):
            widget = ChampNumerique(
                libelle=champ.libelle,
                unite=champ.unite,
                valeur_defaut=champ.defaut,
                info=champ.info,
                validateur=champ.validateur,
            )
            self._champs[champ.cle] = widget
            ligne, colonne = divmod(index, groupe.colonnes)
            grille.addWidget(widget, ligne, colonne)
        for colonne in range(groupe.colonnes):
            grille.setColumnStretch(colonne, 1)
        disposition.addLayout(grille)
        return cadre

    def _construire_options(self) -> QWidget:
        cadre, disposition = carte()
        disposition.addWidget(titre_section("Conditions aux appuis"))
        for cle, choix in self.schema.options.items():
            liste = QComboBox()
            liste.addItems(choix)
            self._options[cle] = liste
            disposition.addWidget(liste)
            if cle == "condition_appui":
                self._ajouter_k_portique(disposition, liste)
        return cadre

    def _ajouter_k_portique(self, disposition, liste: QComboBox) -> None:
        """Champs k1/k2, visibles seulement pour les deux cas de portique."""
        zone = QWidget()
        grille = QGridLayout(zone)
        grille.setContentsMargins(0, METRIQUES.pad_sm, 0, 0)
        grille.setHorizontalSpacing(METRIQUES.pad_lg)
        for colonne, (cle, libelle) in enumerate(
            (("k1", "Souplesse en pied k₁"), ("k2", "Souplesse en tête k₂"))
        ):
            champ = ChampNumerique(libelle=libelle, valeur_defaut="0.1")
            self._champs[cle] = champ
            grille.addWidget(champ, 0, colonne)
            grille.setColumnStretch(colonne, 1)
        disposition.addWidget(zone)
        maj = lambda index: zone.setVisible(index >= 4)
        liste.currentIndexChanged.connect(maj)
        maj(liste.currentIndex())

    def _barre_actions(self) -> QHBoxLayout:
        ligne = QHBoxLayout()
        retour = QPushButton("← Retour")
        retour.setObjectName("Discret")
        retour.clicked.connect(self.retour_demande.emit)
        ligne.addWidget(retour)

        self.message = QLabel("")
        self.message.setStyleSheet(f"color: {PALETTE.danger}; font-size: 12pt;")
        ligne.addWidget(self.message)
        ligne.addStretch()

        reinitialiser = QPushButton("Réinitialiser")
        reinitialiser.clicked.connect(self._reinitialiser)
        ligne.addWidget(reinitialiser)

        calculer = QPushButton("Lancer le calcul")
        calculer.setObjectName("Principal")
        calculer.setMinimumWidth(170)
        calculer.clicked.connect(self._valider_et_calculer)
        ligne.addWidget(calculer)
        return ligne

    def _reinitialiser(self) -> None:
        for groupe in self.schema.groupes:
            for champ in groupe.champs:
                self._champs[champ.cle].saisie.setText(champ.defaut)
                self._champs[champ.cle].masquer_erreur()
        for cle in ("k1", "k2"):
            if cle in self._champs:
                self._champs[cle].saisie.setText("0.1")
                self._champs[cle].masquer_erreur()
        self.message.setText("")

    def _valider_et_calculer(self) -> None:
        """Valide tous les champs obligatoires, puis émet les données."""
        self.message.setText("")
        donnees: dict[str, Any] = {}
        tout_valide = True

        for groupe in self.schema.groupes:
            facultatif = "facultatif" in groupe.titre.lower()
            for champ in groupe.champs:
                widget = self._champs[champ.cle]
                valeur = widget.valeur()
                if valeur is None:
                    if facultatif:
                        donnees[champ.cle] = None
                        widget.masquer_erreur()
                        continue
                    widget.afficher_erreur("Champ requis")
                    tout_valide = False
                    continue
                if not widget.valider(champ.message_erreur or "Valeur invalide"):
                    tout_valide = False
                    continue
                donnees[champ.cle] = valeur

        for cle, liste in self._options.items():
            donnees[cle] = liste.currentIndex()

        if donnees.get("condition_appui", 0) >= 4:
            for cle in ("k1", "k2"):
                widget = self._champs[cle]
                if not widget.valider("k doit être strictement positif"):
                    tout_valide = False
                    continue
                donnees[cle] = widget.valeur()

        if not tout_valide:
            self.message.setText("Corrigez les champs signalés avant de lancer le calcul.")
            return

        self.calcul_demande.emit(donnees)
