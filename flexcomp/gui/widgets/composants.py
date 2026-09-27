"""Widgets réutilisables de l'interface flexcomp.

Chaque widget est autonome et sans dépendance au moteur de calcul : ils ne
connaissent que des nombres et des chaînes. Cela permet de les tester, de
les recomposer, et de les réutiliser dans de futures pages sans rien casser.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from flexcomp.gui.theme import METRIQUES, PALETTE, POLICE_MONO


class ChampNumerique(QWidget):
    """Champ de saisie d'une grandeur physique : libellé, valeur, unité,
    et validation immédiate.

    La validation est déclarée à la construction (`validateur`), pas codée
    dans la page : une page de saisie décrit *quoi* saisir, le widget se
    charge du *comment*.
    """

    valeur_modifiee = pyqtSignal()

    def __init__(
        self,
        libelle: str,
        unite: str = "",
        valeur_defaut: str = "",
        info: str = "",
        validateur: Optional[Callable[[float], bool]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._validateur = validateur or (lambda v: v > 0)
        self._message_erreur = ""

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(5)

        ligne_libelle = QHBoxLayout()
        ligne_libelle.setSpacing(6)
        self.label = QLabel(libelle)
        self.label.setStyleSheet(
            f"font-size: 12pt; color: {PALETTE.texte_secondaire}; "
            "background: transparent; border: none;"
        )
        ligne_libelle.addWidget(self.label)
        ligne_libelle.addStretch()
        disposition.addLayout(ligne_libelle)

        ligne_saisie = QHBoxLayout()
        ligne_saisie.setSpacing(8)
        self.saisie = QLineEdit(valeur_defaut)
        self.saisie.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.saisie.setMaximumWidth(190)
        self.saisie.textChanged.connect(self._au_changement)
        ligne_saisie.addWidget(self.saisie)
        if unite:
            label_unite = QLabel(unite)
            label_unite.setStyleSheet(
                f"color: {PALETTE.texte_tertiaire}; font-family: {POLICE_MONO}; "
                f"font-size: 12pt; background: transparent; border: none;"
            )
            label_unite.setMinimumWidth(38)
            ligne_saisie.addWidget(label_unite)
        ligne_saisie.addStretch()
        disposition.addLayout(ligne_saisie)

        self.erreur = QLabel("")
        self.erreur.setStyleSheet(
            f"color: {PALETTE.danger}; font-size: 12pt; background: transparent; border: none;"
        )
        self.erreur.setVisible(False)
        disposition.addWidget(self.erreur)

    def _au_changement(self) -> None:
        self.masquer_erreur()
        self.valeur_modifiee.emit()

    def valeur(self) -> Optional[float]:
        """Valeur saisie convertie en float, ou None si la saisie est vide
        ou non numérique (la virgule décimale est acceptée)."""
        texte = self.saisie.text().strip().replace(",", ".")
        if not texte:
            return None
        try:
            return float(texte)
        except ValueError:
            return None

    def est_valide(self) -> bool:
        valeur = self.valeur()
        return valeur is not None and self._validateur(valeur)

    def valider(self, message: str = "Valeur invalide") -> bool:
        """Valide le champ et affiche l'erreur en place si besoin."""
        if self.est_valide():
            self.masquer_erreur()
            return True
        self.afficher_erreur(message)
        return False

    def afficher_erreur(self, message: str) -> None:
        self.erreur.setText(message)
        self.erreur.setVisible(True)
        self.saisie.setProperty("invalide", "true")
        self.saisie.style().unpolish(self.saisie)
        self.saisie.style().polish(self.saisie)

    def masquer_erreur(self) -> None:
        self.erreur.setVisible(False)
        self.saisie.setProperty("invalide", "false")
        self.saisie.style().unpolish(self.saisie)
        self.saisie.style().polish(self.saisie)


class CarteSelection(QFrame):
    """Carte cliquable représentant un type d'élément à calculer.

    Préférée à une liste déroulante : avec seulement trois éléments, montrer
    le schéma de chacun est plus parlant qu'un texte dans un menu, et
    l'utilisateur voit tout le domaine couvert par le logiciel d'un coup
    d'œil.
    """

    clique = pyqtSignal(str)

    def __init__(
        self,
        identifiant: str,
        titre: str,
        description: str,
        pictogramme: QPixmap,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.identifiant = identifiant
        self.setObjectName("CarteSelection")
        self.setProperty("selectionnee", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(
            METRIQUES.pad_md, METRIQUES.pad_md, METRIQUES.pad_md, METRIQUES.pad_md
        )
        disposition.setSpacing(METRIQUES.pad_sm)

        image = QLabel()
        image.setPixmap(pictogramme)
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setStyleSheet("background: transparent; border: none;")
        disposition.addWidget(image)

        label_titre = QLabel(titre)
        label_titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_titre.setStyleSheet(
            f"font-size: 12pt; font-weight: 600; color: {PALETTE.texte}; "
            "background: transparent; border: none;"
        )
        disposition.addWidget(label_titre)

        label_desc = QLabel(description)
        label_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_desc.setWordWrap(True)
        label_desc.setStyleSheet(
            f"font-size: 12pt; color: {PALETTE.texte_secondaire}; "
            "background: transparent; border: none;"
        )
        disposition.addWidget(label_desc)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self.clique.emit(self.identifiant)
        super().mousePressEvent(event)

    def definir_selection(self, selectionnee: bool) -> None:
        self.setProperty("selectionnee", "true" if selectionnee else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class BadgeVerdict(QLabel):
    """Pastille colorée indiquant le résultat d'une vérification."""

    def __init__(self, texte: str, etat: str = "succes", parent: Optional[QWidget] = None) -> None:
        super().__init__(texte, parent)
        couleurs = {
            "succes": (PALETTE.succes, PALETTE.succes_clair),
            "danger": (PALETTE.danger, PALETTE.danger_clair),
            "alerte": (PALETTE.alerte, PALETTE.alerte_clair),
            "neutre": (PALETTE.texte_secondaire, PALETTE.surface_alt),
        }
        avant_plan, fond = couleurs.get(etat, couleurs["neutre"])
        self.setStyleSheet(
            f"color: {avant_plan}; background-color: {fond}; "
            f"border-radius: 4px; padding: 3px 10px; font-size: 12pt; font-weight: 600;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)


class LigneResultat(QWidget):
    """Une ligne « grandeur — valeur — verdict optionnel » d'un tableau de
    résultats. La valeur est en police monospace pour aligner les chiffres."""

    def __init__(
        self,
        libelle: str,
        valeur: str,
        verdict: Optional[BadgeVerdict] = None,
        en_evidence: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        disposition = QHBoxLayout(self)
        disposition.setContentsMargins(0, 3, 0, 3)
        disposition.setSpacing(METRIQUES.pad_md)

        label = QLabel(libelle)
        label.setStyleSheet(
            f"color: {PALETTE.texte_secondaire}; font-size: 12pt; background: transparent;"
        )
        label.setMinimumWidth(190)
        disposition.addWidget(label)

        poids = "600" if en_evidence else "400"
        label_valeur = QLabel(valeur)
        label_valeur.setStyleSheet(
            f"font-family: {POLICE_MONO}; font-size: 12pt; font-weight: {poids}; "
            f"color: {PALETTE.texte}; background: transparent;"
        )
        label_valeur.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        disposition.addWidget(label_valeur)
        disposition.addStretch()
        if verdict is not None:
            disposition.addWidget(verdict)


def separateur() -> QFrame:
    """Filet horizontal de séparation."""
    ligne = QFrame()
    ligne.setObjectName("Separateur")
    ligne.setFrameShape(QFrame.Shape.HLine)
    return ligne


def carte(espacement: int = METRIQUES.pad_md) -> tuple[QFrame, QVBoxLayout]:
    """Crée une carte blanche et retourne (cadre, disposition verticale)."""
    cadre = QFrame()
    cadre.setObjectName("Carte")
    disposition = QVBoxLayout(cadre)
    disposition.setContentsMargins(
        METRIQUES.pad_lg, METRIQUES.pad_lg, METRIQUES.pad_lg, METRIQUES.pad_lg
    )
    disposition.setSpacing(espacement)
    return cadre, disposition


def titre_section(texte: str) -> QLabel:
    """Petit intitulé de section, en majuscules espacées."""
    label = QLabel(texte.upper())
    label.setObjectName("TitreSection")
    return label
