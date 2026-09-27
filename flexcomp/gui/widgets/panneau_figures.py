"""Panneau de figures affiché à droite des résultats.

Regroupe les vues d'un élément dans des onglets et offre l'export de la
figure courante. Le panneau ne sait rien du calcul : il reçoit des canevas
déjà construits, ce qui permet d'ajouter une vue (diagramme d'interaction,
plan de ferraillage) sans toucher à ce fichier.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from flexcomp.gui.dessins.canevas import CanevasTechnique
from flexcomp.gui.theme import METRIQUES, PALETTE


class PanneauFigures(QWidget):
    """Onglets de figures + barre d'export."""

    def __init__(self, figures: list[tuple[str, CanevasTechnique]], parent=None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(METRIQUES.pad_sm)

        self.onglets = QTabWidget()
        self.onglets.setDocumentMode(True)
        self.onglets.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {PALETTE.bordure};
                border-radius: {METRIQUES.rayon_carte}px;
                background-color: {PALETTE.surface};
                top: -1px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {PALETTE.texte_secondaire};
                padding: 7px 16px;
                margin-right: 2px;
                border: none;
                font-size: 12pt;
            }}
            QTabBar::tab:selected {{
                color: {PALETTE.accent};
                font-weight: 600;
                border-bottom: 2px solid {PALETTE.accent};
            }}
            """
        )
        for titre, figure in figures:
            self.onglets.addTab(figure, titre)
        disposition.addWidget(self.onglets, stretch=1)

        barre = QHBoxLayout()
        barre.addStretch()
        bouton_png = QPushButton("Exporter en PNG")
        bouton_png.clicked.connect(lambda: self._exporter("png"))
        barre.addWidget(bouton_png)
        bouton_pdf = QPushButton("Exporter en PDF")
        bouton_pdf.clicked.connect(lambda: self._exporter("pdf"))
        barre.addWidget(bouton_pdf)
        disposition.addLayout(barre)

    def figure_courante(self) -> CanevasTechnique:
        return self.onglets.currentWidget()

    def _exporter(self, format_fichier: str) -> None:
        titre = self.onglets.tabText(self.onglets.currentIndex())
        nom_defaut = titre.lower().replace(" ", "_").replace("'", "")
        chemin, _ = QFileDialog.getSaveFileName(
            self, f"Exporter la figure en {format_fichier.upper()}",
            f"{nom_defaut}.{format_fichier}",
            f"Fichier {format_fichier.upper()} (*.{format_fichier})",
        )
        if not chemin:
            return
        figure = self.figure_courante()
        try:
            if format_fichier == "png":
                figure.exporter_png(chemin)
            else:
                figure.exporter_pdf(chemin)
        except OSError as erreur:
            QMessageBox.warning(
                self, "Export impossible",
                f"Le fichier n'a pas pu être écrit :\n\n{erreur}",
            )
            return
        QMessageBox.information(
            self, "Export réussi", f"Figure enregistrée :\n{chemin}"
        )
