"""Widget de base accueillant une figure technique.

Les classes filles n'implémentent que `dessiner(peintre, zone)` en
coordonnées réelles : le widget s'occupe du fond, de l'antialiasing, des
marges et du redimensionnement.

La méthode `exporter_png` / `exporter_pdf` réutilise exactement la même
fonction `dessiner` : c'est tout l'intérêt de passer par QPainter plutôt
que par un moteur de tracé lié à l'écran. La planche de calcul imprimable
n'aura pas à redessiner quoi que ce soit.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPageLayout, QPainter, QPdfWriter, QPageSize
from PyQt6.QtWidgets import QSizePolicy, QWidget

from flexcomp.gui.theme import PALETTE


class CanevasTechnique(QWidget):
    """Surface de dessin d'une figure technique."""

    marge = 18.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(260, 240)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    # À implémenter par les classes filles -----------------------------
    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        """Trace la figure dans `zone` (en pixels)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        peintre.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        peintre.fillRect(self.rect(), QColor(PALETTE.surface))
        zone = QRectF(self.rect()).adjusted(
            self.marge, self.marge, -self.marge, -self.marge
        )
        self.dessiner(peintre, zone)
        peintre.end()

    def sizeHint(self) -> QSize:  # noqa: N802 (API Qt)
        return QSize(420, 380)

    # ------------------------------------------------------------------
    # Exports — même code de dessin que l'affichage écran
    # ------------------------------------------------------------------
    def exporter_png(self, chemin: str, largeur: int = 1600, hauteur: int = 1200) -> None:
        """Exporte la figure en PNG haute résolution."""
        image = QImage(largeur, hauteur, QImage.Format.Format_ARGB32)
        image.fill(QColor(PALETTE.surface))
        peintre = QPainter(image)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        zone = QRectF(0, 0, largeur, hauteur).adjusted(
            self.marge * 3, self.marge * 3, -self.marge * 3, -self.marge * 3
        )
        self.dessiner(peintre, zone)
        peintre.end()
        image.save(chemin)

    def exporter_pdf(self, chemin: str) -> None:
        """Exporte la figure en PDF vectoriel (A4 paysage)."""
        ecrivain = QPdfWriter(chemin)
        ecrivain.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        ecrivain.setPageOrientation(QPageLayout.Orientation.Landscape)
        # 96 dpi = même échelle que l'écran : textes et cotes gardent leurs
        # proportions (le PDF reste vectoriel, seule l'unité change).
        ecrivain.setResolution(96)
        peintre = QPainter(ecrivain)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        zone = QRectF(
            0, 0, ecrivain.width(), ecrivain.height()
        ).adjusted(40, 40, -40, -40)
        self.dessiner(peintre, zone)
        peintre.end()
