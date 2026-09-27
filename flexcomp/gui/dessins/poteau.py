"""Figures du poteau rectangulaire : coupe transversale et élévation.

Style plan (type AutoCAD) : traits noirs, béton hachuré à 45°, cotes à
tirets obliques, barres dessinées à leur diamètre réel. Les marges sont
exprimées en pixels d'après la taille des textes (12 pt), pour qu'aucun
texte ne se chevauche, à l'écran comme en PNG ou en PDF.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QFontMetrics, QPainter, QPainterPath

from flexcomp.core.barres import section_barres
from flexcomp.core.elancement import ConditionAppui
from flexcomp.gui.dessins.canevas import CanevasTechnique
from flexcomp.gui.dessins.primitives import (
    COULEUR_BETON,
    COULEUR_TRAIT,
    TRAIT_FIN,
    TRAIT_FORT,
    TRAIT_MOYEN,
    appui_encastrement,
    appui_rotule,
    barre_acier,
    cote_horizontale,
    cote_verticale,
    fleche,
    hachurer,
    ligne_axe,
    pointe_de_fleche,
    police,
    stylo,
    titre_figure,
)
from flexcomp.results import CasSection

PAS_COTE = 34.0  # écart entre deux lignes de cote parallèles (px)


def _ecrire(peintre: QPainter, point: QPointF, texte: str, alignement: str,
            gras: bool = False) -> float:
    """Écrit un texte 12 pt ancré sur `point` ; renvoie sa largeur (px)."""
    peintre.save()
    peintre.setFont(police(12, gras))
    metrique = QFontMetrics(peintre.font())
    largeur, hauteur = metrique.horizontalAdvance(texte) + 4, metrique.height()
    if alignement == "droite":
        boite = QRectF(point.x() - largeur, point.y() - hauteur / 2, largeur, hauteur)
    elif alignement == "gauche":
        boite = QRectF(point.x(), point.y() - hauteur / 2, largeur, hauteur)
    else:
        boite = QRectF(point.x() - largeur / 2, point.y() - hauteur / 2, largeur, hauteur)
    peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
    peintre.drawText(boite, Qt.AlignmentFlag.AlignCenter, texte)
    peintre.restore()
    return largeur


class _Repere:
    """Échelle unique en x et y (m -> px), dessin centré dans la zone utile."""

    def __init__(self, largeur: float, hauteur: float, zone: QRectF) -> None:
        self.s = max(min(zone.width() / largeur, zone.height() / hauteur), 1.0)
        self.x0 = zone.center().x() - largeur * self.s / 2
        self.y0 = zone.center().y() + hauteur * self.s / 2  # y réel = 0 en bas

    def p(self, x: float, y: float) -> QPointF:
        return QPointF(self.x0 + x * self.s, self.y0 - y * self.s)


class CoupeTransversalePoteau(CanevasTechnique):
    """Coupe transversale cotée avec les deux nappes d'armatures."""

    def __init__(self, poteau, resultat, nombre_barres: int = 3, parent=None) -> None:
        super().__init__(parent)
        self.poteau = poteau
        self.resultat = resultat
        self.nombre_barres = max(2, nombre_barres)
        self.choix: dict[str, tuple[int, int]] | None = None

    def definir_choix(self, choix: dict[str, tuple[int, int]] | None) -> None:
        """choix = {"As1": (nombre, diametre_mm), "As2": (...)}, ou None."""
        self.choix = choix
        self.update()

    def _nappe(self, cle: str) -> tuple[int, int]:
        if self.choix and cle in self.choix:
            return self.choix[cle]
        return self.nombre_barres, round(self.poteau.section.diametre_barre * 1000)

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        section = self.poteau.section
        b, h, c = section.b, section.h, section.enrobage_nominal
        d, d_prime = section.d, section.d_prime
        armatures = self.resultat.armatures

        titre_figure(peintre, zone, "Coupe transversale")
        utile = zone.adjusted(130, 55, -(3 * PAS_COTE + 15), -115)
        r = _Repere(b, h, utile)
        rect = QRectF(r.p(0, h), r.p(b, 0))

        # Béton : hachures 45° + contour fort, axe de symétrie
        hachurer(peintre, rect, pas=9.0, couleur=COULEUR_BETON)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRect(rect)
        ligne_axe(peintre, r.p(-0.06 * b, h / 2), r.p(1.06 * b, h / 2))

        # Cadre (étrier) à l'intérieur de l'enrobage
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN))
        peintre.drawRoundedRect(QRectF(r.p(c, h - c), r.p(b - c, c)), 4, 4)

        # Nappes : As2 à d' de la fibre comprimée (haut), As1 à d (bas)
        premieres: dict[str, QPointF] = {}
        for cle, y in (("As2", h - d_prime), ("As1", h - d)):
            n, phi = self._nappe(cle)
            rayon = max(r.s * phi / 2000, 2.5)
            marge = c + 0.008 + phi / 2000  # enrobage + étrier + demi-barre
            if n == 1:
                abscisses = [b / 2]
            else:
                abscisses = [marge + i * (b - 2 * marge) / (n - 1) for i in range(n)]
            for x in abscisses:
                barre_acier(peintre, r.p(x, y), rayon)
            premieres[cle] = r.p(abscisses[0], y)

        # Lignes de rappel des nappes, tirées vers la gauche
        x_texte = rect.left() - 25
        for cle, decalage in (("As2", -18.0), ("As1", 18.0)):
            n, phi = self._nappe(cle)
            texte = f"{cle} : {n} HA {phi}" if self.choix else \
                f"{cle} = {getattr(armatures, cle):.0f} mm²"
            depart = premieres[cle]
            coude = QPointF(x_texte, depart.y() + decalage)
            largeur = _ecrire(peintre, QPointF(x_texte, coude.y() - 11), texte, "droite")
            peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
            peintre.drawLine(depart, coude)
            peintre.drawLine(coude, QPointF(x_texte - largeur, coude.y()))

        # Cotes à droite (cotation de base depuis la fibre supérieure)
        droite = rect.right()
        x_dp = droite + PAS_COTE
        cote_verticale(peintre, r.p(b, h), r.p(b, h - d_prime), x_dp, "")
        _ecrire(peintre, QPointF(x_dp - 6, rect.top() - 20),
                f"d' = {d_prime * 100:.1f} cm", "gauche")
        cote_verticale(peintre, r.p(b, h), r.p(b, h - d), droite + 2 * PAS_COTE,
                       f"d = {d * 100:.1f} cm")
        cote_verticale(peintre, r.p(b, h), r.p(b, 0), droite + 3 * PAS_COTE,
                       f"h = {h * 100:.0f} cm")
        # Cote b en bas
        cote_horizontale(peintre, r.p(0, 0), r.p(b, 0), rect.bottom() + 32,
                         f"b = {b * 100:.0f} cm")

        # Légende : rôle des nappes (+ sections choisies)
        if self.resultat.cas is CasSection.PARTIELLEMENT_COMPRIMEE:
            roles = ("tendue", "comprimée")
        elif self.resultat.cas is CasSection.ENTIEREMENT_TENDUE:
            roles = ("tendue", "tendue")
        else:
            roles = ("comprimée", "comprimée")
        lignes = [f"As1 {roles[0]}   ·   As2 {roles[1]}"]
        if self.choix:
            a1 = section_barres(*self._nappe("As1"))
            a2 = section_barres(*self._nappe("As2"))
            lignes.append(f"As1 = {a1:.0f} mm²   ·   As2 = {a2:.0f} mm²")
        for rang, ligne in enumerate(reversed(lignes)):
            _ecrire(peintre, QPointF(zone.center().x(), zone.bottom() - 10 - 24 * rang),
                    ligne, "centre")


class ElevationPoteau(CanevasTechnique):
    """Élévation du poteau : appuis, sollicitations, hauteur libre."""

    def __init__(self, poteau, resultat, parent=None) -> None:
        super().__init__(parent)
        self.poteau = poteau
        self.resultat = resultat

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        poteau = self.poteau
        longueur = poteau.longueur_libre
        epaisseur = poteau.section.h  # vue de face : dimension fléchie

        titre_figure(peintre, zone, "Élévation")
        utile = zone.adjusted(90, 110, -170, -95)
        r = _Repere(epaisseur, longueur, utile)
        rect = QRectF(r.p(0, longueur), r.p(epaisseur, 0))

        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRect(rect)
        pied, tete = r.p(epaisseur / 2, 0), r.p(epaisseur / 2, longueur)
        ligne_axe(peintre, QPointF(tete.x(), tete.y() - 12), QPointF(pied.x(), pied.y() + 12))

        # Appuis selon la condition retenue
        condition = poteau.condition_appui
        largeur_appui = max(rect.width() * 2.2, 40.0)
        portiques = (ConditionAppui.PORTIQUE_NON_INTEGRE, ConditionAppui.PORTIQUE_INTEGRE)
        if condition is ConditionAppui.DEUX_ROTULES:
            appui_rotule(peintre, pied, 6.0)
        else:
            appui_encastrement(peintre, pied, largeur_appui)
        if condition in (ConditionAppui.ENCASTREMENT_ROTULE, ConditionAppui.DEUX_ROTULES):
            appui_rotule(peintre, tete, 6.0)
        elif condition is ConditionAppui.DEUX_ENCASTREMENTS or condition in portiques:
            appui_encastrement(peintre, tete, largeur_appui)

        # Effort normal en tête
        sollicitation = self.resultat.sollicitation_elu
        haut_n = QPointF(tete.x(), tete.y() - 70)
        bas_n = QPointF(tete.x(), tete.y() - 8)
        if sollicitation.N > 0:
            fleche(peintre, haut_n, bas_n, COULEUR_TRAIT, TRAIT_FORT, 9.0)
        else:
            fleche(peintre, bas_n, haut_n, COULEUR_TRAIT, TRAIT_FORT, 9.0)
        _ecrire(peintre, QPointF(tete.x() + 10, tete.y() - 62),
                f"N = {sollicitation.N:.0f} kN", "gauche", gras=True)

        # Moment en tête : flèche courbe (sens horaire)
        if abs(sollicitation.M) > 1e-9:
            rm = 28.0
            cadre = QRectF(tete.x() - rm, tete.y() - rm, 2 * rm, 2 * rm)
            chemin = QPainterPath()
            chemin.arcMoveTo(cadre, 60)
            chemin.arcTo(cadre, 60, -120)
            peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN))
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            peintre.drawPath(chemin)
            theta = math.radians(-60)
            bout = QPointF(tete.x() + rm * math.cos(theta), tete.y() - rm * math.sin(theta))
            pointe_de_fleche(peintre, bout, math.atan2(math.cos(theta), math.sin(theta)),
                             8.0, COULEUR_TRAIT)
            _ecrire(peintre, QPointF(tete.x() + rm + 10, tete.y() + 4),
                    f"M = {sollicitation.M:.0f} kN·m", "gauche", gras=True)

        # Cote de la hauteur libre à gauche
        cote_verticale(peintre, r.p(0, longueur), r.p(0, 0), rect.left() - 45,
                       f"l = {longueur:.2f} m")

        # Légende : longueur de flambement et grandeurs clés
        effets = self.resultat.effets_2nd_ordre
        centre_x = zone.center().x()
        _ecrire(peintre, QPointF(centre_x, zone.bottom() - 34),
                f"l₀ = {poteau.l0:.2f} m   ·   λ = {effets.lambda_calcule:.1f}", "centre")
        _ecrire(peintre, QPointF(centre_x, zone.bottom() - 10),
                f"e_tot = {effets.excentricite_totale * 100:.2f} cm   ·   "
                f"M*_Ed = {effets.moment_calcul:.2f} kN·m", "centre")
