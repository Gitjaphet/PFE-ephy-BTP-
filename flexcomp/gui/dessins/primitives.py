"""Boîte à outils de dessin technique (cotes, hachures, flèches, axes).

Ce module ne connaît ni le béton armé ni l'Eurocode : il fournit le
vocabulaire graphique d'un plan d'exécution. Les modules de dessin des
éléments (`poteau.py`, `voute.py`, `voile.py`) l'utilisent pour composer
leurs figures.

Deux choix structurants :

1. **Tout est dessiné en coordonnées réelles** (mètres), converties en
   pixels par une `Echelle`. Le code de dessin parle donc de « un trait de
   0,30 m à 0,40 m », jamais de pixels — c'est ce qui rend les figures
   justes à n'importe quelle taille de fenêtre.

2. **Le rendu passe par QPainter**, pas par une bibliothèque de tracé
   externe. QPainter sait peindre indifféremment sur un widget, une image
   ou un `QPdfWriter` : la même fonction de dessin servira à l'affichage
   écran et à l'export PDF vectoriel de la planche de calcul, sans être
   réécrite ni dupliquée.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from flexcomp.gui.theme import PALETTE, POLICE_MONO

# Épaisseurs normalisées, inspirées des conventions du dessin technique :
# trait fort pour les contours, trait fin pour les cotes et les hachures.
TRAIT_FORT = 1.8
TRAIT_MOYEN = 1.2
TRAIT_FIN = 0.7

COULEUR_TRAIT = QColor("#000000")
COULEUR_COTE = QColor("#000000")
COULEUR_AXE = QColor("#000000")
COULEUR_BETON = QColor("#000000")
COULEUR_ACIER = QColor("#000000")
COULEUR_EFFORT = QColor("#000000")
COULEUR_MOMENT = QColor("#000000")


@dataclass
class Echelle:
    """Conversion entre coordonnées réelles (mètres) et pixels.

    L'échelle est uniforme sur les deux axes — indispensable en dessin
    technique : un carré doit rester carré. L'axe Y est inversé, car en
    dessin l'ordonnée croît vers le haut alors qu'en pixels elle croît vers
    le bas.
    """

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    zone: QRectF
    marge: float = 0.0

    def __post_init__(self) -> None:
        largeur_reelle = max(self.x_max - self.x_min, 1e-9)
        hauteur_reelle = max(self.y_max - self.y_min, 1e-9)
        zone_utile = self.zone.adjusted(
            self.marge, self.marge, -self.marge, -self.marge
        )
        self.facteur = min(
            zone_utile.width() / largeur_reelle,
            zone_utile.height() / hauteur_reelle,
        )
        largeur_dessin = largeur_reelle * self.facteur
        hauteur_dessin = hauteur_reelle * self.facteur
        self.origine_x = zone_utile.left() + (zone_utile.width() - largeur_dessin) / 2
        self.origine_y = zone_utile.top() + (zone_utile.height() + hauteur_dessin) / 2

    def point(self, x: float, y: float) -> QPointF:
        """Convertit un point réel (m) en point écran (px)."""
        return QPointF(
            self.origine_x + (x - self.x_min) * self.facteur,
            self.origine_y - (y - self.y_min) * self.facteur,
        )

    def longueur(self, valeur: float) -> float:
        """Convertit une longueur réelle (m) en longueur écran (px)."""
        return valeur * self.facteur


def stylo(couleur: QColor, epaisseur: float = TRAIT_MOYEN,
          style: Qt.PenStyle = Qt.PenStyle.SolidLine) -> QPen:
    """Crée un stylo aux extrémités arrondies (rendu plus propre aux angles)."""
    crayon = QPen(couleur, epaisseur, style)
    crayon.setCapStyle(Qt.PenCapStyle.RoundCap)
    crayon.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return crayon


def police(taille: float, gras: bool = False, mono: bool = True) -> QFont:
    """Police de dessin unique : Times New Roman, 12 pt minimum."""
    fonte = QFont()
    fonte.setFamilies(["Times New Roman", "Liberation Serif"])
    fonte.setStyleHint(QFont.StyleHint.Serif)
    fonte.setPointSizeF(max(float(taille), 12.0))
    fonte.setBold(gras)
    return fonte


# ----------------------------------------------------------------------
# Primitives de dessin technique
# ----------------------------------------------------------------------
def hachurer(
    peintre: QPainter,
    rectangle: QRectF,
    pas: float = 7.0,
    couleur: QColor = COULEUR_BETON,
    epaisseur: float = TRAIT_FIN,
) -> None:
    """Remplit un rectangle de hachures à 45° — convention « coupe de
    matériau » du dessin technique."""
    peintre.save()
    peintre.setClipRect(rectangle)
    peintre.setPen(stylo(couleur, epaisseur))
    depart = rectangle.left() - rectangle.height()
    x = depart
    while x < rectangle.right() + rectangle.height():
        peintre.drawLine(
            QPointF(x, rectangle.bottom()),
            QPointF(x + rectangle.height(), rectangle.top()),
        )
        x += pas
    peintre.restore()


def pointe_de_fleche(
    peintre: QPainter, sommet: QPointF, angle: float,
    taille: float = 7.0, couleur: QColor = COULEUR_TRAIT
) -> None:
    """Dessine une pointe de flèche pleine, orientée selon `angle` (radians)."""
    ouverture = math.radians(20)
    p1 = QPointF(
        sommet.x() - taille * math.cos(angle - ouverture),
        sommet.y() - taille * math.sin(angle - ouverture),
    )
    p2 = QPointF(
        sommet.x() - taille * math.cos(angle + ouverture),
        sommet.y() - taille * math.sin(angle + ouverture),
    )
    peintre.save()
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QBrush(couleur))
    peintre.drawPolygon(QPolygonF([sommet, p1, p2]))
    peintre.restore()


def fleche(
    peintre: QPainter, depart: QPointF, arrivee: QPointF,
    couleur: QColor = COULEUR_TRAIT, epaisseur: float = TRAIT_MOYEN,
    taille_pointe: float = 7.0,
) -> None:
    """Flèche simple, pointe à l'arrivée."""
    peintre.setPen(stylo(couleur, epaisseur))
    peintre.drawLine(depart, arrivee)
    angle = math.atan2(arrivee.y() - depart.y(), arrivee.x() - depart.x())
    pointe_de_fleche(peintre, arrivee, angle, taille_pointe, couleur)


def _texte_centre(
    peintre: QPainter, centre: QPointF, texte: str,
    taille: float = 8.0, couleur: QColor = COULEUR_COTE,
    fond: QColor | None = None, gras: bool = False,
) -> None:
    """Écrit un texte centré sur un point, avec un fond optionnel qui
    « mange » le trait de cote pour rester lisible."""
    peintre.save()
    peintre.setFont(police(taille, gras))
    metrique = QFontMetrics(peintre.font())
    largeur = metrique.horizontalAdvance(texte)
    hauteur = metrique.height()
    boite = QRectF(
        centre.x() - largeur / 2 - 3, centre.y() - hauteur / 2,
        largeur + 6, hauteur,
    )
    if fond is not None:
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QBrush(fond))
        peintre.drawRect(boite)
    peintre.setPen(stylo(couleur, TRAIT_FIN))
    peintre.drawText(boite, Qt.AlignmentFlag.AlignCenter, texte)
    peintre.restore()


def _tiret_cote(peintre: QPainter, point: QPointF, taille: float = 4.0) -> None:
    """Extrémité de cote style AutoCAD « Architectural tick » : tiret à 45°."""
    peintre.save()
    peintre.setPen(stylo(COULEUR_COTE, TRAIT_MOYEN))
    peintre.drawLine(
        QPointF(point.x() - taille, point.y() + taille),
        QPointF(point.x() + taille, point.y() - taille),
    )
    peintre.restore()


def _texte_sur_ligne(peintre: QPainter, centre: QPointF, texte: str, taille: float = 12.0) -> None:
    """Texte de cote posé au-dessus de la ligne (repère courant), sans fond."""
    peintre.save()
    peintre.setFont(police(taille))
    hauteur = QFontMetrics(peintre.font()).height()
    _texte_centre(peintre, QPointF(centre.x(), centre.y() - hauteur / 2 - 1), texte, taille=taille)
    peintre.restore()


def cote_horizontale(
    peintre: QPainter, gauche: QPointF, droite: QPointF, y: float,
    texte: str, depassement: float = 5.0, fond: QColor | None = None,
) -> None:
    """Cote horizontale style AutoCAD : lignes d'attache décollées de l'objet,
    tirets à 45° aux extrémités, texte au-dessus de la ligne de cote."""
    ecart = 2.0
    peintre.save()
    peintre.setPen(stylo(COULEUR_COTE, TRAIT_FIN))
    for p in (gauche, droite):
        sens = 1.0 if y >= p.y() else -1.0
        peintre.drawLine(QPointF(p.x(), p.y() + sens * ecart), QPointF(p.x(), y + sens * depassement))
    peintre.drawLine(QPointF(gauche.x() - 3, y), QPointF(droite.x() + 3, y))
    peintre.restore()
    _tiret_cote(peintre, QPointF(gauche.x(), y))
    _tiret_cote(peintre, QPointF(droite.x(), y))
    _texte_sur_ligne(peintre, QPointF((gauche.x() + droite.x()) / 2, y), texte)


def cote_verticale(
    peintre: QPainter, haut: QPointF, bas: QPointF, x: float,
    texte: str, depassement: float = 5.0, fond: QColor | None = None,
) -> None:
    """Cote verticale style AutoCAD, texte tourné de 90° à gauche de la ligne."""
    ecart = 2.0
    peintre.save()
    peintre.setPen(stylo(COULEUR_COTE, TRAIT_FIN))
    for p in (haut, bas):
        sens = 1.0 if x >= p.x() else -1.0
        peintre.drawLine(QPointF(p.x() + sens * ecart, p.y()), QPointF(x + sens * depassement, p.y()))
    peintre.drawLine(QPointF(x, haut.y() - 3), QPointF(x, bas.y() + 3))
    peintre.restore()
    _tiret_cote(peintre, QPointF(x, haut.y()))
    _tiret_cote(peintre, QPointF(x, bas.y()))

    milieu = QPointF(x, (haut.y() + bas.y()) / 2)
    peintre.save()
    peintre.translate(milieu)
    peintre.rotate(-90)
    _texte_sur_ligne(peintre, QPointF(0, 0), texte)
    peintre.restore()


def ligne_axe(
    peintre: QPainter, depart: QPointF, arrivee: QPointF,
    couleur: QColor = COULEUR_AXE,
) -> None:
    """Trait d'axe (mixte fin), convention pour les axes de symétrie."""
    crayon = stylo(couleur, TRAIT_FIN, Qt.PenStyle.DashDotLine)
    peintre.setPen(crayon)
    peintre.drawLine(depart, arrivee)


def appui_encastrement(
    peintre: QPainter, centre: QPointF, largeur: float,
    couleur: QColor = COULEUR_TRAIT,
) -> None:
    """Symbole d'encastrement : ligne d'appui + hachures inclinées."""
    peintre.save()
    peintre.setPen(stylo(couleur, TRAIT_MOYEN))
    gauche = centre.x() - largeur / 2
    droite = centre.x() + largeur / 2
    peintre.drawLine(QPointF(gauche, centre.y()), QPointF(droite, centre.y()))
    peintre.setPen(stylo(couleur, TRAIT_FIN))
    pas = max(largeur / 7, 6.0)
    x = gauche
    while x <= droite:
        peintre.drawLine(QPointF(x, centre.y()), QPointF(x - 7, centre.y() + 9))
        x += pas
    peintre.restore()


def appui_rotule(
    peintre: QPainter, centre: QPointF, rayon: float = 5.0,
    couleur: QColor = COULEUR_TRAIT, fond: QColor | None = None,
) -> None:
    """Symbole de rotule : petit cercle évidé."""
    peintre.save()
    peintre.setPen(stylo(couleur, TRAIT_MOYEN))
    peintre.setBrush(QBrush(fond if fond else QColor(PALETTE.surface)))
    peintre.drawEllipse(centre, rayon, rayon)
    peintre.restore()


def barre_acier(
    peintre: QPainter, centre: QPointF, rayon: float,
    couleur: QColor = COULEUR_ACIER,
) -> None:
    """Barre d'acier vue en coupe : disque plein."""
    peintre.save()
    peintre.setPen(Qt.PenStyle.NoPen)
    peintre.setBrush(QBrush(couleur))
    peintre.drawEllipse(centre, rayon, rayon)
    peintre.restore()


def etiquette(
    peintre: QPainter, ancre: QPointF, decalage: QPointF, texte: str,
    couleur: QColor = COULEUR_TRAIT, taille: float = 8.0,
    aligner_a_droite: bool = False,
) -> None:
    """Étiquette reliée à un point par une ligne de rappel coudée —
    convention d'annotation des plans d'armatures."""
    fin = QPointF(ancre.x() + decalage.x(), ancre.y() + decalage.y())
    peintre.save()
    peintre.setPen(stylo(COULEUR_COTE, TRAIT_FIN))
    peintre.drawLine(ancre, fin)
    longueur_trait = 12 if not aligner_a_droite else -12
    bout = QPointF(fin.x() + longueur_trait, fin.y())
    peintre.drawLine(fin, bout)

    peintre.setFont(police(taille))
    metrique = QFontMetrics(peintre.font())
    largeur = metrique.horizontalAdvance(texte)
    x_texte = bout.x() + 4 if not aligner_a_droite else bout.x() - largeur - 4
    peintre.setPen(stylo(couleur, TRAIT_FIN))
    peintre.drawText(
        QRectF(x_texte, bout.y() - metrique.height() / 2, largeur + 2, metrique.height()),
        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        texte,
    )
    peintre.restore()


def titre_figure(peintre: QPainter, zone: QRectF, texte: str) -> None:
    """Titre discret en haut de la figure."""
    peintre.save()
    peintre.setFont(police(9, gras=True, mono=False))
    peintre.setPen(stylo(QColor("#000000"), TRAIT_FIN))
    peintre.drawText(
        QRectF(zone.left(), zone.top() + 2, zone.width(), 20),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        texte,
    )
    peintre.restore()
