"""Planche de ferraillage du poteau (A4 portrait), mise en page identique aux
planches du département : nomenclature, élévation avec la répartition des
cadres, coupes A-A et B-B, cartouche avec logos.
Police Times New Roman, 7 pt comme la planche de référence (mesures en mm).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PyQt6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QImage, QPageLayout, QPageSize,
    QPainter, QPdfWriter, QPolygonF,
)

from flexcomp.core.cadres import (
    COEF_RECOUVREMENT, RepartitionCadres, calculer_cadres, longueur_barre_longitudinale,
)
from flexcomp.gui.dessins.primitives import COULEUR_TRAIT, TRAIT_FIN, TRAIT_FORT, TRAIT_MOYEN, stylo

DOSSIER_LOGOS = Path(__file__).resolve().parent.parent / "assets" / "logos"

# Textes du cartouche : à modifier ici si besoin
INFOS_PLANCHE = {
    "titre": "PROJET DE FIN D'ANNÉE - S8",
    "projet": "CALCUL DES ÉLÉMENTS TRAVAILLANT EN FLEXION COMPOSÉE SELON EUROCODES 2",
    "encadreurs": ("Mr RAZAFINDRAMARO Borgeot Augustin", "Mr RANDRIAMARSON Julas Fridolès", ""),
    "etudiant": "JEPHY Marinho",
    "designation": "FERRAILLAGE POTEAU RECTANGULAIRE",
    "stade": "A",
    "planche": "1",
    "planches": "1",
    "mention": "MENTION GÉNIE CIVIL\nPARCOURS BAT 4",
}
TAILLE = 7.0
ECHELLES_ELEVATION = (20, 25, 30, 40, 50, 75, 100)
ECHELLES_COUPE = (10, 20, 25, 50)
GRIS = QColor("#C0C0C0")
NOIR = QColor("#000000")


def _police(taille: float = TAILLE, gras: bool = False) -> QFont:
    fonte = QFont()
    fonte.setFamilies(["Times New Roman", "Liberation Serif"])
    fonte.setStyleHint(QFont.StyleHint.Serif)
    fonte.setPointSizeF(taille)
    fonte.setBold(gras)
    return fonte


class _Page:
    """Dessin en millimètres (k = pixels par mm)."""

    def __init__(self, peintre: QPainter, k: float) -> None:
        self.p, self.k = peintre, k

    def pt(self, x: float, y: float) -> QPointF:
        return QPointF(x * self.k, y * self.k)

    def rect(self, x, y, w, h) -> QRectF:
        return QRectF(x * self.k, y * self.k, w * self.k, h * self.k)

    def ligne(self, x1, y1, x2, y2, ep=TRAIT_FIN) -> None:
        self.p.setPen(stylo(COULEUR_TRAIT, ep))
        self.p.drawLine(self.pt(x1, y1), self.pt(x2, y2))

    def cadre(self, x, y, w, h, ep=TRAIT_FIN) -> None:
        self.p.setPen(stylo(COULEUR_TRAIT, ep))
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawRect(self.rect(x, y, w, h))

    def texte(self, x, y, w, h, texte, taille=TAILLE, gras=False,
              align=Qt.AlignmentFlag.AlignCenter) -> None:
        self.p.save()
        self.p.setFont(_police(taille, gras))
        self.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        self.p.drawText(self.rect(x, y, w, h),
                        int(align.value) | int(Qt.TextFlag.TextWordWrap.value), texte)
        self.p.restore()

    def morceaux(self, x, y, w, h, morceaux) -> None:
        """Une ligne centrée faite de morceaux (texte, taille, gras)."""
        largeurs = [QFontMetricsF(_police(t, g)).horizontalAdvance(s) for s, t, g in morceaux]
        dispo = (w - 1.5) * self.k
        if sum(largeurs) > dispo:
            facteur = dispo / sum(largeurs)
            morceaux = [(s, t * facteur, g) for s, t, g in morceaux]
            largeurs = [QFontMetricsF(_police(t, g)).horizontalAdvance(s) for s, t, g in morceaux]
        xc = x * self.k + (w * self.k - sum(largeurs)) / 2
        for (s, t, g), lw in zip(morceaux, largeurs):
            self.p.save()
            self.p.setFont(_police(t, g))
            self.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
            self.p.drawText(QRectF(xc, y * self.k, lw + 1, h * self.k),
                            int((Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter).value), s)
            self.p.restore()
            xc += lw

    def texte_vertical(self, xc, yc, texte, taille=TAILLE) -> None:
        self.p.save()
        self.p.translate(self.pt(xc, yc))
        self.p.rotate(-90)
        self.p.setFont(_police(taille))
        self.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        k = self.k
        self.p.drawText(QRectF(-40 * k, -2.5 * k, 80 * k, 5 * k),
                        int(Qt.AlignmentFlag.AlignCenter.value), texte)
        self.p.restore()

    def tiret(self, x, y) -> None:
        self.ligne(x - 0.9, y + 0.9, x + 0.9, y - 0.9, TRAIT_MOYEN)

    def cote_v(self, x, y1, y2, texte, depuis_x=None) -> None:
        haut, bas = min(y1, y2), max(y1, y2)
        if depuis_x is not None:
            s = 1.0 if x > depuis_x else -1.0
            for y in (haut, bas):
                self.ligne(depuis_x + s * 0.8, y, x + s * 1.0, y)
        self.ligne(x, haut - 1, x, bas + 1)
        self.tiret(x, haut)
        self.tiret(x, bas)
        self.texte_vertical(x - 2.0, (haut + bas) / 2, texte)

    def cote_h(self, y, x1, x2, texte, depuis_y=None) -> None:
        g, d = min(x1, x2), max(x1, x2)
        if depuis_y is not None:
            s = 1.0 if y > depuis_y else -1.0
            for x in (g, d):
                self.ligne(x, depuis_y + s * 0.8, x, y + s * 1.0)
        self.ligne(g - 1, y, d + 1, y)
        self.tiret(g, y)
        self.tiret(d, y)
        self.texte(g, y - 4.2, d - g, 4, texte)

    def disque(self, x, y, r) -> None:
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(QBrush(NOIR))
        self.p.drawEllipse(self.pt(x, y), r * self.k, r * self.k)

    def bulle(self, x, y, numero: int) -> None:
        self.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
        self.p.setBrush(QBrush(QColor("#FFFFFF")))
        self.p.drawEllipse(self.pt(x, y), 2.1 * self.k, 2.1 * self.k)
        self.texte(x - 2.1, y - 2.1, 4.2, 4.2, str(numero))

    def fleche_bas(self, x, y) -> None:
        self.ligne(x, y, x, y + 2.0, TRAIT_MOYEN)
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(QBrush(NOIR))
        self.p.drawPolygon(QPolygonF([self.pt(x, y + 3.0), self.pt(x - 0.7, y + 1.7),
                                      self.pt(x + 0.7, y + 1.7)]))

    def image(self, chemin, x, y, w, h) -> None:
        if chemin is None:
            return
        img = QImage(str(chemin))
        if img.isNull():
            return
        s = min(w * self.k / img.width(), h * self.k / img.height())
        dw, dh = img.width() * s, img.height() * s
        self.p.drawImage(QRectF(x * self.k + (w * self.k - dw) / 2,
                                y * self.k + (h * self.k - dh) / 2, dw, dh), img)


def _logo(nom: str):
    for ext in ("png", "jpg", "jpeg"):
        chemin = DOSSIER_LOGOS / f"logo_{nom}.{ext}"
        if chemin.exists():
            return chemin
    return None


def _nom_mixte(nom: str) -> list[tuple[str, float, bool]]:
    """« Mr RAZAFINDRAMARO Borgeot » : nom de famille (majuscules) en gras."""
    mots = nom.split()
    return [(m + (" " if i < len(mots) - 1 else ""), TAILLE, m.isupper() and len(m) > 1)
            for i, m in enumerate(mots)]


# ----------------------------------------------------------------------
# Nomenclature (en haut à droite)
# ----------------------------------------------------------------------
def _nomenclature(pg: _Page, lignes) -> None:
    x0, y0, h_tete, h_ligne = 122.0, 10.0, 4.2, 7.0
    largeurs = (9.5, 35.5, 33.0)
    xs = [x0, x0 + largeurs[0], x0 + largeurs[0] + largeurs[1], 200.0]
    total = h_tete + h_ligne * len(lignes)
    pg.cadre(x0, y0, 78, total, TRAIT_MOYEN)
    pg.ligne(x0, y0 + h_tete, 200, y0 + h_tete)
    for x in xs[1:-1]:
        pg.ligne(x, y0, x, y0 + total)
    for i, t in enumerate(("Pos.", "Armature", "Forme")):
        pg.texte(xs[i], y0, largeurs[i], h_tete, t)
    gauche = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    droite = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    for r, (pos, armature, longueur, forme) in enumerate(lignes):
        y = y0 + h_tete + h_ligne * r
        if r:
            pg.ligne(x0, y, 200, y)
        pg.texte(xs[0], y, largeurs[0], h_ligne, str(pos))
        pg.texte(xs[1] + 2, y, largeurs[1] / 2, h_ligne, armature, align=gauche)
        pg.texte(xs[1] + largeurs[1] / 2, y, largeurs[1] / 2 - 2, h_ligne, longueur, align=droite)
        forme(pg, xs[2], y, largeurs[2], h_ligne)


def _forme_droite(longueur_m: float):
    def dessiner(pg: _Page, x, y, w, h) -> None:
        pg.ligne(x + 4, y + h * 0.68, x + w - 4, y + h * 0.68)
        pg.texte(x, y + 0.6, w, h * 0.5, f"{longueur_m:.2f}")
    return dessiner


def _forme_cadre(cadres: RepartitionCadres):
    """Croquis du cadre à sa vraie proportion (sens de la coupe : a en largeur, b en hauteur)."""
    def dessiner(pg: _Page, x, y, w, h) -> None:
        rh = 3.6
        rw = rh * cadres.cote_a / cadres.cote_b
        rx, ry = x + w / 2 - rw / 2, y + 2.8
        pg.cadre(rx, ry, rw, rh)
        pg.ligne(rx + 0.2, ry + 0.9, rx + 0.9, ry + 0.2)                   # crochet
        pg.texte(rx - 3, y + 0.2, rw + 6, 2.6, f"{cadres.cote_a:.0f}")     # largeur, en haut
        pg.texte(rx + rw + 0.6, ry, 6, rh, f"{cadres.cote_b:.0f}",
                 align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pg.texte(rx - 6.6, ry - 0.8, 6, 3, f"{cadres.crochet:.0f}",
                 align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return dessiner


# ----------------------------------------------------------------------
# Élévation avec répartition des cadres
# ----------------------------------------------------------------------
def _elevation(pg: _Page, b, c, l, hp, recouv, cad: RepartitionCadres, phi_barre, echelle) -> None:
    f = 10.0 / echelle                         # mm de planche par cm réel
    w = b * f
    xl = 49.0 - w / 2
    xr = xl + w
    y_bas = 213.0
    y_pb = y_bas - l * f                       # sous-face de la poutre
    y_ph = y_pb - hp * f                       # dessus de la poutre
    y_sup = y_ph - recouv * f                  # bout des attentes

    # Coffrage : poteau, poutre en tête, amorce du poteau supérieur, plancher bas
    for x in (xl, xr):
        pg.ligne(x, y_bas, x, y_pb)
        pg.ligne(x, y_ph, x, y_sup)
    for y in (y_pb, y_ph):
        pg.ligne(xl - 7, y, xl, y)
        pg.ligne(xr, y, xr + 7, y)
    pg.ligne(xl - 5, y_bas, xl, y_bas)
    pg.ligne(xr, y_bas, xr + 5, y_bas)

    # Barres longitudinales (trait fort) et cadres
    d = (c + cad.phi_t / 10 + phi_barre / 20) * f
    xb1, xb2 = xl + d, xr - d
    for x in (xb1, xb2):
        pg.ligne(x, y_bas, x, y_sup, TRAIT_FORT)
    positions, cumul = [y_bas - cad.depart * f], cad.depart
    for n, s in cad.zones:
        for _ in range(n):
            cumul += s
            positions.append(y_bas - cumul * f)
    positions = [max(y, y_pb) for y in positions]
    for y in positions:
        pg.ligne(xb1 - 0.4, y, xb2 + 0.4, y, TRAIT_MOYEN)

    # Repères de coupe : B dans la zone basse, A dans la zone courante
    hz = [n * s for n, s in cad.zones]
    y_b = y_bas - hz[0] / 2 * f
    y_a = y_bas - (hz[0] + (hz[1] / 2 if len(hz) > 1 else 0)) * f
    for lettre, y in (("A", y_a),):
        for x1, x2, gauche in ((xl - 8.5, xl - 5, True), (xr + 5, xr + 8.5, False)):
            pg.ligne(x1, y, x2, y, TRAIT_MOYEN)
            pg.fleche_bas((x1 + x2) / 2, y)
            pg.texte(x1 - 2.4 if gauche else x2 - 0.6, y - 3.6, 3, 3, lettre)

    # Chaîne 1 : un tiret à chaque cadre + libellés « n x s »
    x1 = xr + 21
    pg.ligne(x1, y_bas + 1, x1, positions[-1] - 1)
    for y in positions:
        pg.ligne(x1 - 1, y, x1 + 1, y)
    if cad.depart > 0:                                   # cote plancher -> 1er cadre
        pg.ligne(x1 - 1, y_bas, x1 + 1, y_bas)
        pg.texte(x1 + 1.2, y_bas - 3, 6, 3, f"{cad.depart:.0f}",
                 align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    y_c = y_bas - cad.depart * f
    for (n, s), libelle in zip(cad.zones, cad.libelles()):
        y_n = max(y_c - n * s * f, y_pb)
        pg.texte_vertical(x1 - 2.2, (y_c + y_n) / 2, libelle)
        y_c = y_n
    # Chaîne 2 : hauteur libre + poutre ; chaîne 3 : total + recouvrement
    x2, x3 = x1 + 8, x1 + 16
    pg.cote_v(x2, y_bas, y_pb, f"{l / 100:.2f}")
    pg.cote_v(x2, y_pb, y_ph, f"{hp:.0f}")
    pg.cote_v(x3, y_bas, y_ph, f"{(l + hp) / 100:.2f}")
    pg.cote_v(x3, y_ph, y_sup, f"{recouv:.0f}")


# ----------------------------------------------------------------------
# Coupes A-A et B-B
# ----------------------------------------------------------------------
def _coupe(pg: _Page, xc, y_titre, b, h, c, nappes, cad: RepartitionCadres,
           lettre: str, ech: int) -> float:
    pg.morceaux(xc - 40, y_titre - 2.5, 80, 5,
                [(f"COUPE {lettre}-{lettre}", 8.5, True), (f" (Ech:1/{ech}è)", 8.5, False)])
    f = 10.0 / ech
    bw, bh = b * f, h * f
    xl, yt = xc - bw / 2, y_titre + 21.5
    xr, yb = xl + bw, yt + bh

    pg.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FIN))
    pg.p.setBrush(QBrush(GRIS))
    pg.p.drawRect(pg.rect(xl, yt, bw, bh))
    ci = c * f
    pg.p.setPen(stylo(COULEUR_TRAIT, TRAIT_FORT))
    pg.p.setBrush(Qt.BrushStyle.NoBrush)
    pg.p.drawRoundedRect(pg.rect(xl + ci, yt + ci, bw - 2 * ci, bh - 2 * ci), 1.0 * pg.k, 1.0 * pg.k)
    for dx in (0.0, 0.9):                                     # crochet à 135°
        pg.ligne(xr - ci - 0.7 - dx, yt + ci + 0.7, xr - ci - 3.7 - dx, yt + ci + 3.7, TRAIT_FORT)

    for numero, n, phi, en_haut in nappes:
        d = ci + (cad.phi_t / 10 + phi / 20) * f
        y = yt + d if en_haut else yb - d
        xa, xb = xl + d, xr - d
        xs = [(xa + xb) / 2] if n == 1 else [xa + i * (xb - xa) / (n - 1) for i in range(n)]
        for x in xs:
            pg.disque(x, y, max(phi / 20 * f, 0.45))
        pg.ligne(xs[0], y, xl - 7.9 + 2.1, y)                 # rappel horizontal
        pg.bulle(xl - 7.9, y, numero)
    pg.ligne(xc, yt + ci, xc, yt - 8.5 + 2.1)                 # rappel vertical du cadre
    pg.bulle(xc, yt - 8.5, 3)

    pg.cote_v(xr + 6.5, yt, yb, f"{h:.0f}", depuis_x=xr)
    pg.cote_h(yb + 6.5, xl, xr, f"{b:.0f}", depuis_y=yb)
    return yb


# ----------------------------------------------------------------------
# Cartouche (2 bandes, comme la planche de référence)
# ----------------------------------------------------------------------
def _cartouche(pg: _Page, infos: dict, echelle: int) -> None:
    y0, y1, y2 = 247.0, 261.0, 287.0
    # Bande 1 : logos encadrés | titre
    largeur_logo = 79.0 / 3
    for i, nom in enumerate(("una", "esp", "mention")):
        x = 15 + i * largeur_logo
        pg.image(_logo(nom), x + 2, y0 + 1.5, largeur_logo - 4, 11)
        pg.cadre(x + 2, y0 + 1.5, largeur_logo - 4, 11)
    pg.ligne(94, y0, 94, y1)
    pg.texte(94, y0, 106, 14, infos["titre"], 10, True)
    pg.ligne(15, y1, 200, y1)

    # Bande 2 gauche : intervenants
    colonnes = (15.0, 30.0, 72.0, 82.0, 94.0)
    h_tete = 5.4
    h_rang = (y2 - y1 - h_tete) / 4
    for x in colonnes[1:-1]:
        pg.ligne(x, y1, x, y2)
    for (xa, xb), t in zip(zip(colonnes, colonnes[1:]), ("Profession", "Nom et Prénom", "Date", "Signature")):
        pg.texte(xa, y1, xb - xa, h_tete, t)
    rangs = [("Encadreur", nom, "") for nom in infos["encadreurs"]]
    rangs.append(("Étudiante", infos["etudiant"], date.today().strftime("%m/%Y")))
    for r, (profession, nom, jour) in enumerate(rangs):
        y = y1 + h_tete + h_rang * r
        pg.ligne(15, y, 94, y)
        pg.texte(15, y, 15, h_rang, profession)
        if nom:
            pg.morceaux(30, y, 42, h_rang, _nom_mixte(nom))
        pg.texte(72, y, 10, h_rang, jour)

    # Bande 2 milieu : projet + désignation
    pg.ligne(94, y1, 94, y2)
    pg.texte(95, y1 + 0.5, 64, 13, infos["projet"], 7.5, True)
    pg.ligne(94, y1 + 14, 160, y1 + 14)
    pg.texte(94, y1 + 14.5, 66, 5.5, infos["designation"])
    pg.texte(94, y1 + 19.5, 66, 5, f"(Echelle : 1/{echelle})", 6)

    # Bande 2 droite : stade / planche N° / planches + mention
    pg.ligne(160, y1, 160, y2)
    for xa, xb, libelle, valeur in ((160, 169.5, "Stade", infos["stade"]),
                                    (169.5, 185, "Planche N°", infos["planche"]),
                                    (185, 200, "Planches", infos["planches"])):
        pg.texte(xa, y1, xb - xa, h_tete, libelle)
        pg.texte(xa, y1 + h_tete, xb - xa, 14 - h_tete, valeur, 14)
        if xa > 160:
            pg.ligne(xa, y1, xa, y1 + 14)
    pg.ligne(160, y1 + h_tete, 200, y1 + h_tete)
    pg.ligne(160, y1 + 14, 200, y1 + 14)
    pg.texte(160, y1 + 14, 40, 12, infos["mention"])

    pg.cadre(15, y0, 185, y2 - y0, TRAIT_MOYEN)


# ----------------------------------------------------------------------
def exporter_planche_poteau(chemin: str, poteau, choix: dict[str, tuple[int, int]],
                            hauteur_poutre_cm: float = 35.0, infos: dict | None = None) -> None:
    """Écrit la planche de ferraillage A4 du poteau dans `chemin` (PDF)."""
    infos = {**INFOS_PLANCHE, **(infos or {})}
    section = poteau.section
    b, h, c = section.b * 100, section.h * 100, section.enrobage_nominal * 100
    l = poteau.longueur_libre * 100
    hp = hauteur_poutre_cm
    (n1, phi1), (n2, phi2) = choix["As1"], choix["As2"]
    phi_max = max(phi1, phi2)
    cadres = calculer_cadres(b, h, c, l, phi_max, min(phi1, phi2))
    recouv = COEF_RECOUVREMENT * phi_max / 10
    echelle = next((e for e in ECHELLES_ELEVATION if (l + hp + recouv) * 10 / e <= 190), 100)
    ech_coupe = next((e for e in ECHELLES_COUPE if max(b, h) * 10 / e <= 45), 50)

    ecrivain = QPdfWriter(str(chemin))
    ecrivain.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    ecrivain.setPageOrientation(QPageLayout.Orientation.Portrait)
    ecrivain.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    ecrivain.setResolution(96)
    peintre = QPainter(ecrivain)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pg = _Page(peintre, ecrivain.width() / 210.0)

    pg.cadre(15, 10, 185, 277, TRAIT_MOYEN)
    # Longueur dessinée et cotée : hauteur totale + recouvrement 40.Φmax
    l1 = l2 = longueur_barre_longitudinale(l + hp, phi_max) / 100
    _nomenclature(pg, [
        (1, f"{n1}HA{phi1}", f"l={l1:.2f}", _forme_droite(l1)),
        (2, f"{n2}HA{phi2}", f"l={l2:.2f}", _forme_droite(l2)),
        (3, f"{cadres.nombre}HA{cadres.phi_t}", f"l={cadres.longueur / 100:.2f}", _forme_cadre(cadres)),
    ])
    _elevation(pg, b, c, l, hp, recouv, cadres, phi_max, echelle)
    nappes = ((1, n1, phi1, False), (2, n2, phi2, True))
    _coupe(pg, 157, 70, b, h, c, nappes, cadres, "A", ech_coupe)
    _cartouche(pg, infos, echelle)
    peintre.end()
