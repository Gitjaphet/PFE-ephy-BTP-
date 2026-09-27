"""Logo de l'application et pictogrammes des trois éléments.

Les visuels sont produits en SVG par le code plutôt que chargés depuis des
fichiers binaires : le dépôt reste léger, les couleurs suivent
automatiquement le thème (`flexcomp.gui.theme`), et le rendu reste net à
toutes les résolutions.
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from flexcomp.gui.theme import PALETTE


def _svg_vers_pixmap(svg: str, largeur: int, hauteur: int) -> QPixmap:
    """Rend une chaîne SVG en QPixmap à la taille demandée."""
    rendu = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(largeur, hauteur)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    rendu.render(peintre)
    peintre.end()
    return pixmap


def logo(taille: int = 88, sur_fond_sombre: bool = False) -> QPixmap:
    """Logo de l'application : une section de poteau vue en coupe, avec ses
    quatre barres d'angle et l'axe neutre — l'objet même du logiciel."""
    trait = PALETTE.texte_inverse if sur_fond_sombre else PALETTE.texte
    accent = PALETTE.accent_clair if sur_fond_sombre else PALETTE.accent
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <rect x="18" y="10" width="64" height="80" rx="3"
            fill="none" stroke="{trait}" stroke-width="3.5"/>
      <line x1="18" y1="50" x2="82" y2="50"
            stroke="{accent}" stroke-width="2.5" stroke-dasharray="6 4"/>
      <circle cx="31" cy="23" r="6" fill="{accent}"/>
      <circle cx="69" cy="23" r="6" fill="{accent}"/>
      <circle cx="31" cy="77" r="6" fill="{accent}"/>
      <circle cx="69" cy="77" r="6" fill="{accent}"/>
    </svg>"""
    return _svg_vers_pixmap(svg, taille, taille)


def pictogramme_poteau(largeur: int = 132, hauteur: int = 96) -> QPixmap:
    """Élévation schématique d'un poteau : encastrement en pied, rotule en
    tête, effort normal N et moment M."""
    t, n, m = PALETTE.texte_secondaire, PALETTE.effort_normal, PALETTE.moment
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 132 96">
      <rect x="56" y="22" width="20" height="58" fill="none"
            stroke="{t}" stroke-width="2"/>
      <line x1="40" y1="80" x2="92" y2="80" stroke="{t}" stroke-width="2"/>
      <line x1="44" y1="80" x2="38" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="55" y1="80" x2="49" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="66" y1="80" x2="60" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="77" y1="80" x2="71" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="88" y1="80" x2="82" y2="88" stroke="{t}" stroke-width="1.4"/>
      <circle cx="66" cy="22" r="4.5" fill="none" stroke="{t}" stroke-width="2"/>
      <line x1="66" y1="4" x2="66" y2="16" stroke="{n}" stroke-width="2.4"/>
      <path d="M62 13 L66 18 L70 13 Z" fill="{n}"/>
      <path d="M84 40 A 16 16 0 0 1 84 56" fill="none" stroke="{m}" stroke-width="2.2"/>
      <path d="M81 53 L85 58 L89 53 Z" fill="{m}"/>
    </svg>"""
    return _svg_vers_pixmap(svg, largeur, hauteur)


def pictogramme_voute(largeur: int = 132, hauteur: int = 96) -> QPixmap:
    """Voûte surbaissée à trois articulations : rotules à la clef et aux
    naissances, charge répartie."""
    t, n = PALETTE.texte_secondaire, PALETTE.effort_normal
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 132 96">
      <path d="M22 70 Q 66 26 110 70" fill="none" stroke="{t}" stroke-width="2.6"/>
      <circle cx="22" cy="70" r="4.5" fill="#FFFFFF" stroke="{t}" stroke-width="2"/>
      <circle cx="110" cy="70" r="4.5" fill="#FFFFFF" stroke="{t}" stroke-width="2"/>
      <circle cx="66" cy="48" r="4.5" fill="#FFFFFF" stroke="{t}" stroke-width="2"/>
      <line x1="14" y1="78" x2="118" y2="78" stroke="{t}" stroke-width="1.8"/>
      <line x1="30" y1="14" x2="30" y2="26" stroke="{n}" stroke-width="1.8"/>
      <path d="M27 23 L30 28 L33 23 Z" fill="{n}"/>
      <line x1="66" y1="10" x2="66" y2="22" stroke="{n}" stroke-width="1.8"/>
      <path d="M63 19 L66 24 L69 19 Z" fill="{n}"/>
      <line x1="102" y1="14" x2="102" y2="26" stroke="{n}" stroke-width="1.8"/>
      <path d="M99 23 L102 28 L105 23 Z" fill="{n}"/>
    </svg>"""
    return _svg_vers_pixmap(svg, largeur, hauteur)


def pictogramme_mur(largeur: int = 132, hauteur: int = 96) -> QPixmap:
    """Élévation d'un mur porteur : console verticale encastrée en pied,
    effort normal et effort tranchant dans le plan."""
    t, n, m = PALETTE.texte_secondaire, PALETTE.effort_normal, PALETTE.moment
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 132 96">
      <rect x="38" y="24" width="56" height="56" fill="none"
            stroke="{t}" stroke-width="2"/>
      <line x1="30" y1="80" x2="102" y2="80" stroke="{t}" stroke-width="2"/>
      <line x1="36" y1="80" x2="30" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="50" y1="80" x2="44" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="64" y1="80" x2="58" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="78" y1="80" x2="72" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="92" y1="80" x2="86" y2="88" stroke="{t}" stroke-width="1.4"/>
      <line x1="66" y1="6" x2="66" y2="18" stroke="{n}" stroke-width="2.4"/>
      <path d="M62 15 L66 20 L70 15 Z" fill="{n}"/>
      <line x1="18" y1="34" x2="32" y2="34" stroke="{m}" stroke-width="2.2"/>
      <path d="M29 31 L34 34 L29 37 Z" fill="{m}"/>
      <line x1="46" y1="36" x2="86" y2="36" stroke="{t}" stroke-width="0.9" stroke-dasharray="3 3"/>
      <line x1="46" y1="52" x2="86" y2="52" stroke="{t}" stroke-width="0.9" stroke-dasharray="3 3"/>
      <line x1="46" y1="68" x2="86" y2="68" stroke="{t}" stroke-width="0.9" stroke-dasharray="3 3"/>
    </svg>"""
    return _svg_vers_pixmap(svg, largeur, hauteur)
