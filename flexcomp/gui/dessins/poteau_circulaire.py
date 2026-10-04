"""Coupe transversale du poteau circulaire (style plan, comme le poteau rectangulaire) :
béton hachuré, cadre circulaire, barres choisies au diamètre réel, axe neutre ELU."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath

from flexcomp.core.barres import section_barres
from flexcomp.gui.dessins.canevas import CanevasTechnique
from flexcomp.gui.dessins.poteau import _ecrire
from flexcomp.gui.dessins.primitives import (
    COULEUR_BETON, COULEUR_TRAIT, TRAIT_FIN, TRAIT_FORT, TRAIT_MOYEN,
    barre_acier, cote_horizontale, hachurer, ligne_axe, stylo, titre_figure,
)


class CoupePoteauCirculaire(CanevasTechnique):
    """Coupe du poteau circulaire ; suit en direct le choix « nHAφ » saisi."""

    def __init__(self, poteau, resultat, parent=None) -> None:
        super().__init__(parent)
        self.poteau = poteau
        self.resultat = resultat
        self.choix: dict[str, tuple[int, int]] | None = None

    def definir_choix(self, choix) -> None:
        self.choix = choix
        self.update()

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        p = self.poteau
        D = p.D                                         # mm
        titre_figure(peintre, zone, "Coupe transversale")
        utile = zone.adjusted(150, 80, -60, -120)
        s = min(utile.width(), utile.height()) / D      # px par mm
        c = QPointF(utile.center().x(), utile.center().y())
        R = D / 2 * s

        def P(x_mm: float, y_mm: float) -> QPointF:     # y vers le haut
            return QPointF(c.x() + x_mm * s, c.y() - y_mm * s)

        # Béton hachuré dans le cercle
        cercle = QPainterPath()
        cercle.addEllipse(c, R, R)
        peintre.save()
        peintre.setClipPath(cercle)
        peintre.setPen(stylo(COULEUR_BETON, TRAIT_FIN))
        k = c.x() - 3 * R
        while k < c.x() + R:                       # hachures à 45° limitées au cercle
            peintre.drawLine(QPointF(k, c.y() + R), QPointF(k + 2 * R, c.y() - R))
            k += 9.0
        peintre.restore()
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawEllipse(c, R, R)

        # Barres (choix saisi, sinon nombre de barres du calcul)
        n, phi = self.choix["As1"] if self.choix and self.choix.get("As1") else (p.nombre_barres, round(p.diametre_barre * 1000))
        r_cadre = (p.rs + phi / 2 + 4) * s
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN))
        peintre.drawEllipse(c, r_cadre, r_cadre)
        for k in range(n):
            u = math.pi / 2 + 2 * math.pi * k / n
            barre_acier(peintre, P(p.rs * math.cos(u), p.rs * math.sin(u)), max(phi / 2 * s, 2.5))

        # Axe de symétrie et axe neutre à l'ELU
        ligne_axe(peintre, QPointF(c.x() - R - 15, c.y()), QPointF(c.x() + R + 15, c.y()))
        x = self.resultat.x
        if 0 < x < D:        # axe neutre dans la section (cas 1)
            yn = c.y() - (D / 2 - x) * s
            peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN, Qt.PenStyle.DashLine))
            largeur_txt = _ecrire(peintre, QPointF(c.x() - R - 8, yn - 12), "axe neutre (ELU)", "droite")
            peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN, Qt.PenStyle.DashLine))
            peintre.drawLine(QPointF(c.x() - R - 8 - largeur_txt, yn), QPointF(c.x() + R + 25, yn))

        # Ligne de rappel vers la barre du haut
        haut = P(0, p.rs)
        coude = QPointF(c.x() - R * 0.75, c.y() - R - 28)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        peintre.drawLine(haut, coude)
        largeur = _ecrire(peintre, QPointF(coude.x(), coude.y() - 11), f"{n} HA {phi}", "droite")
        peintre.drawLine(coude, QPointF(coude.x() - largeur, coude.y()))

        # Cote D et légende
        cote_horizontale(peintre, QPointF(c.x() - R, c.y()), QPointF(c.x() + R, c.y()),
                         c.y() + R + 32, f"D = {D / 10:.0f} cm")
        As = section_barres(n, phi)
        etat = ("Cas 2 : entièrement tendue" if x <= 0 else "Cas 3 : entièrement comprimée"
                if x >= p.D else "Cas 1 : partiellement comprimée")
        lignes = [f"{etat}   ·   x = {x / 10:.1f} cm   ·   rₛ = {p.rs / 10:.1f} cm",
                  f"{n} HA {phi} = {As:.0f} mm²"]
        for rang, ligne in enumerate(reversed(lignes)):
            _ecrire(peintre, QPointF(zone.center().x(), zone.bottom() - 10 - 24 * rang), ligne, "centre")
