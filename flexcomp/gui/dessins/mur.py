"""Figures du voile, style plan type AutoCAD.

- Élévation dans le plan : encastrement en pied, chaînages d'about en trait
  interrompu, N et V en tête, cotes b et lw.
- Coupe horizontale : épaisseur hw hachurée, aciers d'about choisis sur
  deux rangs (une rangée par face), point d'application de N.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter

from flexcomp.core.barres import section_barres
from flexcomp.gui.dessins.canevas import CanevasTechnique
from flexcomp.gui.dessins.poteau import PAS_COTE, _ecrire, _Repere
from flexcomp.gui.dessins.primitives import (
    COULEUR_BETON,
    COULEUR_TRAIT,
    TRAIT_FIN,
    TRAIT_FORT,
    TRAIT_MOYEN,
    appui_encastrement,
    barre_acier,
    cote_horizontale,
    cote_verticale,
    fleche,
    hachurer,
    ligne_axe,
    stylo,
    titre_figure,
)


def _legende(peintre: QPainter, zone: QRectF, lignes: list[str]) -> None:
    for rang, ligne in enumerate(reversed(lignes)):
        _ecrire(peintre, QPointF(zone.center().x(), zone.bottom() - 10 - 24 * rang),
                ligne, "centre")


class _AvecChoix(CanevasTechnique):
    """Figure qui suit le choix d'armatures « nHAφ » saisi dans les résultats."""

    choix: dict[str, tuple[int, int]] | None = None

    def definir_choix(self, choix: dict[str, tuple[int, int]] | None) -> None:
        self.choix = choix
        self.update()

    def _about(self) -> tuple[int, int] | None:
        return self.choix.get("As1") if self.choix else None


class ElevationMur(_AvecChoix):
    """Élévation du voile dans son plan."""

    def __init__(self, mur, resultat, sollicitation=None, parent=None) -> None:
        super().__init__(parent)
        self.mur = mur
        self.resultat = resultat
        self.sollicitation = sollicitation

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        m = self.mur
        b, lw, c = m.longueur_calcul, m.hauteur_libre, m.enrobage_nominal
        titre_figure(peintre, zone, "Élévation du voile")
        utile = zone.adjusted(190, 110, -(PAS_COTE + 30), -120)
        r = _Repere(b, lw, utile)
        rect = QRectF(r.p(0, lw), r.p(b, 0))

        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRect(rect)
        appui_encastrement(peintre, r.p(b / 2, 0), rect.width() * 1.15)

        # Chaînages verticaux d'about (cachés dans le béton -> trait interrompu)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN, Qt.PenStyle.DashLine))
        for x in (c + 0.02, c + 0.10, b - c - 0.10, b - c - 0.02):
            peintre.drawLine(r.p(x, 0.02), r.p(x, lw - 0.02))

        # Effort normal en tête
        tete = QPointF(rect.center().x(), rect.top())
        fleche(peintre, QPointF(tete.x(), tete.y() - 70), QPointF(tete.x(), tete.y() - 4),
               COULEUR_TRAIT, TRAIT_FORT, 9.0)
        _ecrire(peintre, QPointF(tete.x() + 10, tete.y() - 62),
                f"N_Ed = {self.resultat.verif_forces_axiales.N_Ed:.1f} kN", "gauche", gras=True)

        # Effort tranchant en tête, dans le plan
        tau = self.resultat.verif_effort_tranchant.tau_cp
        v_ed = tau * b * m.epaisseur * 1e6 / 1.5 / 1000
        y_v = rect.top() + 16
        fleche(peintre, QPointF(rect.left() - 90, y_v), QPointF(rect.left() - 4, y_v),
               COULEUR_TRAIT, TRAIT_MOYEN, 8.0)
        _ecrire(peintre, QPointF(rect.left() - 8, y_v - 16), f"V_Ed = {v_ed:.0f} kN",
                "droite", gras=True)

        # Cotes : b en bas (sous l'encastrement), lw à droite
        cote_horizontale(peintre, r.p(0, 0), r.p(b, 0), rect.bottom() + 42, f"b = {b:.2f} m")
        cote_verticale(peintre, r.p(b, lw), r.p(b, 0), rect.right() + PAS_COTE,
                       f"lw = {lw:.2f} m")

        about = self._about()
        lignes = [f"l₀ = β·lw = {m.l0:.2f} m   ·   λ = {m.elancement:.1f}"]
        lignes.append(
            f"Chaînages d'about : {about[0]} HA {about[1]} à chaque extrémité" if about
            else "- - - chaînages verticaux d'about"
        )
        _legende(peintre, zone, lignes)


class CoupeHorizontaleMur(_AvecChoix):
    """Coupe horizontale : épaisseur hw, aciers d'about, point d'application de N."""

    def __init__(self, mur, resultat, excentricite: float = 0.0, parent=None) -> None:
        super().__init__(parent)
        self.mur = mur
        self.resultat = resultat
        self.excentricite = excentricite

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        m = self.mur
        b, hw, c = m.longueur_calcul, m.epaisseur, m.enrobage_nominal
        titre_figure(peintre, zone, "Coupe horizontale du voile")
        utile = zone.adjusted(30, 110, -(PAS_COTE + 70), -140)
        r = _Repere(b, hw, utile)
        rect = QRectF(r.p(0, hw), r.p(b, 0))

        hachurer(peintre, rect, pas=8.0, couleur=COULEUR_BETON)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRect(rect)
        ligne_axe(peintre, r.p(-0.04 * b, hw / 2), r.p(1.04 * b, hw / 2))

        # Aciers d'about : n barres par about, sur deux rangs (une par face)
        about = self._about()
        if about:
            n, phi = about
            colonnes = math.ceil(n / 2)
            pas = max(3 * phi / 1000, 0.05)
            bord = c + 0.008 + phi / 2000
            rayon = max(r.s * phi / 2000, 2.5)
            for cote_gauche in (True, False):
                xs = []
                for i in range(n):
                    dx = bord + (i // 2) * pas
                    x = dx if cote_gauche else b - dx
                    y = hw - bord if i % 2 == 0 else bord
                    barre_acier(peintre, r.p(x, y), rayon)
                    xs.append(x)
                # Cadre d'about autour des barres
                x_int = bord + (colonnes - 1) * pas + phi / 2000 + 0.008
                x1, x2 = (c, x_int) if cote_gauche else (b - x_int, b - c)
                peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN))
                peintre.setBrush(Qt.BrushStyle.NoBrush)
                peintre.drawRoundedRect(QRectF(r.p(x1, hw - c), r.p(x2, c)), 3, 3)
                # Ligne de rappel vers le haut
                depart = r.p(xs[0], hw - bord)
                coude = QPointF(depart.x() + (18 if cote_gauche else -18), rect.top() - 28)
                texte = f"{n} HA {phi}"
                peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
                peintre.drawLine(depart, coude)
                largeur = _ecrire(peintre, QPointF(coude.x(), coude.y() - 11), texte,
                                  "gauche" if cote_gauche else "droite")
                fin = coude.x() + largeur if cote_gauche else coude.x() - largeur
                peintre.drawLine(coude, QPointF(fin, coude.y()))

        # Point d'application de N (décalé de e dans l'épaisseur)
        point = r.p(b / 2, hw / 2 + self.excentricite)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QBrush(QColor("#000000")))
        peintre.drawEllipse(point, 3.5, 3.5)

        cote_horizontale(peintre, r.p(0, 0), r.p(b, 0), rect.bottom() + 32, f"b = {b:.2f} m")
        x_hw = rect.right() + PAS_COTE
        cote_verticale(peintre, r.p(b, hw), r.p(b, 0), x_hw, "")
        _ecrire(peintre, QPointF(x_hw + 6, rect.center().y()), f"hw = {hw * 100:.0f} cm", "gauche")

        lignes = [
            "e = 0 : effort normal centré dans l'épaisseur" if abs(self.excentricite) < 1e-9
            else f"e = {self.excentricite * 100:.1f} cm dans l'épaisseur",
            "M_Ed agit dans le plan du voile (e1 = M/N sur la longueur b)",
        ]
        if about:
            lignes.append(f"Aciers d'about : {about[0]} HA {about[1]} = "
                          f"{section_barres(*about):.0f} mm² à chaque extrémité")
        _legende(peintre, zone, lignes)
