"""Figures de la voûte à trois articulations (style plan type AutoCAD).

- Géométrie : extrados / intrados, ligne moyenne, funiculaire, rotules,
  ligne de charge, repère de la coupe A–A à la section critique.
- Diagramme M(x) hachuré, avec la section critique.
- Coupe A–A : bande de calcul, barres choisies au diamètre réel.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath

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
    appui_rotule,
    barre_acier,
    cote_horizontale,
    cote_verticale,
    fleche,
    hachurer,
    stylo,
    titre_figure,
)

NOMBRE_POINTS = 160


def _chemin(points: list[QPointF]) -> QPainterPath:
    chemin = QPainterPath()
    for i, point in enumerate(points):
        if i == 0:
            chemin.moveTo(point)
        else:
            chemin.lineTo(point)
    return chemin


def _legende(peintre: QPainter, zone: QRectF, lignes: list[str]) -> None:
    """Lignes de légende centrées en bas de la zone (la dernière tout en bas)."""
    for rang, ligne in enumerate(reversed(lignes)):
        _ecrire(peintre, QPointF(zone.center().x(), zone.bottom() - 10 - 24 * rang),
                ligne, "centre")


class GeometrieVoute(CanevasTechnique):
    """Arc (extrados, intrados, ligne moyenne), funiculaire, rotules, charge."""

    def __init__(self, voute, resultat, parent=None) -> None:
        super().__init__(parent)
        self.voute = voute
        self.resultat = resultat

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        v = self.voute
        l, f, e = v.portee, v.fleche, v.epaisseur
        titre_figure(peintre, zone, "Géométrie de l'arc")
        utile = zone.adjusted(30, 110, -(PAS_COTE + 80), -165)
        r = _Repere(l, f + e, utile)

        def P(x: float, y: float) -> QPointF:
            return r.p(x, y + e / 2)

        xs = [l * i / NOMBRE_POINTS for i in range(NOMBRE_POINTS + 1)]
        peintre.setBrush(Qt.BrushStyle.NoBrush)

        # Ligne des naissances, funiculaire (tirets), ligne moyenne (mixte)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        peintre.drawLine(P(-0.03 * l, 0), P(1.03 * l, 0))
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN, Qt.PenStyle.DashLine))
        peintre.drawPath(_chemin([P(x, v.y_funiculaire(x)) for x in xs]))
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN, Qt.PenStyle.DashDotLine))
        peintre.drawPath(_chemin([P(x, v.y_arc(x)) for x in xs]))

        # Extrados / intrados (trait fort) et fermeture aux naissances
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        for sens in (1, -1):
            peintre.drawPath(_chemin([P(x, v.y_arc(x) + sens * e / 2) for x in xs]))
        for x in (0.0, l):
            peintre.drawLine(P(x, v.y_arc(x) - e / 2), P(x, v.y_arc(x) + e / 2))

        # Appuis et rotules
        for x in (0.0, l):
            appui_encastrement(peintre, P(x, 0), 36.0)
        for x in (0.0, l / 2, l):
            appui_rotule(peintre, P(x, v.y_arc(x)), 5.0)

        # Ligne de charge p
        y_charge = P(0, f + e / 2).y() - 55
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        peintre.drawLine(QPointF(P(0, 0).x(), y_charge), QPointF(P(l, 0).x(), y_charge))
        for i in range(9):
            x = l * (i + 0.5) / 9
            fleche(peintre, QPointF(P(x, 0).x(), y_charge),
                   QPointF(P(x, 0).x(), P(x, v.y_arc(x) + e / 2).y() - 3),
                   COULEUR_TRAIT, TRAIT_FIN, 6.0)
        _ecrire(peintre, QPointF(zone.center().x(), y_charge - 14),
                f"p = {v.charge_uniforme:.0f} kN/m", "centre", gras=True)

        # Repère de coupe A–A à la section critique
        x_c = self.resultat.section_critique.x
        haut, bas = P(x_c, v.y_arc(x_c) + e / 2), P(x_c, v.y_arc(x_c) - e / 2)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.drawLine(QPointF(haut.x(), haut.y() - 18), QPointF(haut.x(), haut.y() - 4))
        peintre.drawLine(QPointF(bas.x(), bas.y() + 4), QPointF(bas.x(), bas.y() + 18))
        _ecrire(peintre, QPointF(bas.x() + 4, bas.y() + 26), "A", "gauche", gras=True)

        # Cotes : portée en bas, flèche à droite (texte horizontal : cote courte)
        cote_horizontale(peintre, P(0, 0), P(l, 0), P(0, -e / 2).y() + 50, f"l = {l:.2f} m")
        x_f = P(l, 0).x() + PAS_COTE
        cote_verticale(peintre, P(l / 2, f), P(l, 0), x_f, "")
        _ecrire(peintre, QPointF(x_f + 6, (P(l / 2, f).y() + P(l, 0).y()) / 2),
                f"f = {f:.2f} m", "gauche")

        _legende(peintre, zone, [
            f"H = {self.resultat.poussee_horizontale:.1f} kN/m   ·   R = {self.resultat.rayon_arc:.2f} m",
            f"Section critique A–A : x* = {x_c:.2f} m",
            "- - - funiculaire   ·   —·— ligne moyenne",
        ])


class DiagrammeMomentVoute(CanevasTechnique):
    """Diagramme M(x) hachuré le long de la portée, section critique repérée."""

    def __init__(self, voute, resultat, parent=None) -> None:
        super().__init__(parent)
        self.voute = voute
        self.resultat = resultat

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        v = self.voute
        l = v.portee
        titre_figure(peintre, zone, "Moment fléchissant M(x)")
        xs = [l * i / NOMBRE_POINTS for i in range(NOMBRE_POINTS + 1)]
        moments = [v.moment(x) for x in xs]
        bas_m, haut_m = min(0.0, min(moments)), max(0.0, max(moments))
        etendue = max(haut_m - bas_m, 1e-6)
        utile = zone.adjusted(45, 80, -45, -130)

        def P(x: float, m: float) -> QPointF:
            return QPointF(utile.left() + x / l * utile.width(),
                           utile.bottom() - (m - bas_m) / etendue * utile.height())

        # Hachures à 45° à l'intérieur du diagramme
        aire = _chemin([P(0, 0)] + [P(x, m) for x, m in zip(xs, moments)] + [P(l, 0)])
        aire.closeSubpath()
        peintre.save()
        peintre.setClipPath(aire)
        peintre.setPen(stylo(COULEUR_BETON, TRAIT_FIN))
        cadre = aire.boundingRect()
        k = cadre.left() - cadre.height()
        while k < cadre.right():
            peintre.drawLine(QPointF(k, cadre.bottom()), QPointF(k + cadre.height(), cadre.top()))
            k += 7.0
        peintre.restore()

        # Courbe et axe M = 0
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.drawPath(_chemin([P(x, m) for x, m in zip(xs, moments)]))
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_MOYEN))
        peintre.drawLine(P(0, 0), P(l, 0))

        # Rotules (M = 0) et repères
        negatif = abs(bas_m) >= haut_m
        decalage = -16.0 if negatif else 16.0
        for x, texte in ((0.0, "naissance"), (l / 2, "clef"), (l, "naissance")):
            appui_rotule(peintre, P(x, 0), 4.0)
            _ecrire(peintre, P(x, 0) + QPointF(0, decalage), texte, "centre")

        # Section critique
        sc = self.resultat.section_critique
        pied, pointe = P(sc.x, 0), P(sc.x, sc.moment)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN, Qt.PenStyle.DashLine))
        peintre.drawLine(pied, pointe)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QBrush(QColor("#000000")))
        peintre.drawEllipse(pointe, 3.5, 3.5)
        _ecrire(peintre, QPointF(pointe.x() + 10, pointe.y() + (14 if negatif else -14)),
                f"M = {sc.moment:.2f} kN·m", "gauche", gras=True)

        cote_horizontale(peintre, P(0, 0), P(l, 0), max(P(0, bas_m).y(), P(0, 0).y()) + 40,
                         f"l = {l:.2f} m")
        _legende(peintre, zone, [
            f"Section critique A–A : x* = {sc.x:.2f} m",
            "M = 0 aux trois rotules (structure isostatique)",
        ])


class CoupeSectionVoute(CanevasTechnique):
    """Coupe A–A à la section critique : bande b x e, nappes choisies."""

    def __init__(self, voute, resultat, parent=None) -> None:
        super().__init__(parent)
        self.voute = voute
        self.resultat = resultat
        self.choix: dict[str, tuple[int, int]] | None = None

    def definir_choix(self, choix: dict[str, tuple[int, int]] | None) -> None:
        self.choix = choix
        self.update()

    def dessiner(self, peintre: QPainter, zone: QRectF) -> None:
        v = self.voute
        b, e, c = v.largeur_calcul, v.epaisseur, v.enrobage_nominal
        titre_figure(peintre, zone, "Coupe A–A (section critique)")
        utile = zone.adjusted(165, 70, -(PAS_COTE + 55), -110)
        r = _Repere(b, e, utile)
        rect = QRectF(r.p(0, e), r.p(b, 0))

        hachurer(peintre, rect, pas=9.0, couleur=COULEUR_BETON)
        peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
        peintre.setBrush(Qt.BrushStyle.NoBrush)
        peintre.drawRect(rect)

        armatures = self.resultat.armatures
        espacements = []
        for cle, role, en_haut in (("As1", "extrados", True), ("As2", "intrados", False)):
            if self.choix and cle in self.choix:
                n, phi = self.choix[cle]
            else:
                n, phi = 5, round(v.diametre_barre * 1000)
            y = e - (c + phi / 2000) if en_haut else c + phi / 2000
            abscisses = [(i + 0.5) * b / n for i in range(n)]
            rayon = max(r.s * phi / 2000, 2.5)
            for x in abscisses:
                barre_acier(peintre, r.p(x, y), rayon)
            espacements.append(f"{cle} : s = {b / n * 100:.0f} cm")
            texte = f"{cle} ({role}) : {n} HA {phi}" if self.choix else \
                f"{cle} = {getattr(armatures, cle):.0f} mm²/m"
            depart = r.p(abscisses[0], y)
            coude = QPointF(rect.left() - 22, depart.y() + (-18 if en_haut else 18))
            largeur = _ecrire(peintre, QPointF(coude.x(), coude.y() - 11), texte, "droite")
            peintre.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
            peintre.drawLine(depart, coude)
            peintre.drawLine(coude, QPointF(coude.x() - largeur, coude.y()))

        cote_horizontale(peintre, r.p(0, 0), r.p(b, 0), rect.bottom() + 32,
                         f"b = {b:.2f} m")
        x_e = rect.right() + PAS_COTE
        cote_verticale(peintre, r.p(b, e), r.p(b, 0), x_e, "")
        _ecrire(peintre, QPointF(x_e + 6, rect.center().y()), f"e = {e * 100:.0f} cm", "gauche")

        lignes = ["As1 extrados   ·   As2 intrados   (bande de calcul)"]
        if self.choix:
            lignes.append("   ·   ".join(espacements))
        _legende(peintre, zone, lignes)


# Le calcul par bande reste lisible avec la section réelle en légende
__all__ = ["GeometrieVoute", "DiagrammeMomentVoute", "CoupeSectionVoute", "section_barres"]
