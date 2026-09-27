"""Système de design de l'application flexcomp.

Un seul endroit définit les couleurs, les espacements, la typographie et la
feuille de style Qt (QSS). Aucun autre fichier de `flexcomp.gui` ne doit
contenir de couleur en dur : si une teinte doit changer, elle change ici et
l'application entière suit.

Palette : neutres chauds + un seul accent (bleu ardoise). Un logiciel de
calcul technique doit rester sobre — la couleur est réservée au sens
(vérification OK / KO, effort normal, moment), jamais à la décoration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """Couleurs de l'application, en hexadécimal."""

    # Surfaces (du plus sombre au plus clair)
    fond_app: str = "#F4F3F0"        # canvas de la fenêtre
    surface: str = "#FFFFFF"          # cartes, panneaux
    surface_alt: str = "#FAF9F7"      # lignes alternées, zones secondaires
    surface_sombre: str = "#23262B"   # bandeau latéral / en-tête

    # Texte
    texte: str = "#1C1F24"
    texte_secondaire: str = "#5F6670"
    texte_tertiaire: str = "#8B929C"
    texte_inverse: str = "#F4F3F0"

    # Bordures
    bordure: str = "#E2E0DB"
    bordure_forte: str = "#C9C6C0"

    # Accent unique
    accent: str = "#2F5D8A"
    accent_clair: str = "#E8EEF5"
    accent_sombre: str = "#234668"

    # Sémantique (réservée aux verdicts de vérification)
    succes: str = "#1D7A56"
    succes_clair: str = "#E3F2EC"
    danger: str = "#B23B32"
    danger_clair: str = "#FBEAE8"
    alerte: str = "#9A6B12"
    alerte_clair: str = "#FBF1DE"

    # Sémantique structurelle (schémas : effort normal / moment)
    effort_normal: str = "#B23B32"    # rouge — N
    moment: str = "#2F5D8A"           # bleu — M


@dataclass(frozen=True)
class Metriques:
    """Espacements et rayons, en pixels. Échelle 4 px."""

    pad_xs: int = 4
    pad_sm: int = 8
    pad_md: int = 16
    pad_lg: int = 24
    pad_xl: int = 32
    pad_xxl: int = 48

    rayon: int = 6
    rayon_carte: int = 10

    largeur_fenetre: int = 1180
    hauteur_fenetre: int = 760
    largeur_bandeau: int = 232


PALETTE = Palette()
METRIQUES = Metriques()

# Familles de police : une sans-serif pour l'interface, une monospace pour
# toutes les valeurs numériques (alignement des chiffres en colonne).
POLICE_UI = "Times New Roman, Liberation Serif, serif"
POLICE_MONO = "Times New Roman, Liberation Serif, serif"


def feuille_de_style() -> str:
    """Retourne la feuille de style QSS globale de l'application."""
    p, m = PALETTE, METRIQUES
    return f"""
    QWidget {{
        background-color: {p.fond_app};
        color: {p.texte};
        font-family: {POLICE_UI};
        font-size: 12pt;
    }}

    QLabel#Titre {{
        font-size: 20pt;
        font-weight: 600;
        color: {p.texte};
    }}
    QLabel#SousTitre {{
        font-size: 12pt;
        color: {p.texte_secondaire};
    }}
    QLabel#TitreSection {{
        font-size: 12pt;
        font-weight: 600;
        color: {p.texte_tertiaire};
        letter-spacing: 1px;
    }}
    QLabel#TitrePage {{
        font-size: 16pt;
        font-weight: 600;
    }}
    QLabel#Legende {{
        font-size: 12pt;
        color: {p.texte_tertiaire};
    }}
    QLabel#Mono {{
        font-family: {POLICE_MONO};
        font-size: 12pt;
    }}

    /* ----- Cartes ----- */
    QFrame#Carte {{
        background-color: {p.surface};
        border: 1px solid {p.bordure};
        border-radius: {m.rayon_carte}px;
    }}
    QFrame#Carte QLabel {{
        background-color: transparent;
        border: none;
    }}
    QFrame#CarteSelection {{
        background-color: {p.surface};
        border: 1px solid {p.bordure};
        border-radius: {m.rayon_carte}px;
    }}
    QFrame#CarteSelection QLabel {{
        background-color: transparent;
        border: none;
    }}
    QFrame#CarteSelection[selectionnee="true"] {{
        border: 2px solid {p.accent};
        background-color: {p.accent_clair};
    }}
    QFrame#Separateur {{
        background-color: {p.bordure};
        max-height: 1px;
        border: none;
    }}

    /* ----- Bandeau latéral ----- */
    QFrame#Bandeau {{
        background-color: {p.surface_sombre};
        border: none;
    }}
    QFrame#Bandeau QLabel {{
        background-color: transparent;
        color: {p.texte_inverse};
    }}
    QLabel#BandeauEtape {{
        color: {p.texte_tertiaire};
        font-size: 12pt;
        padding: 6px 0px;
    }}
    QLabel#BandeauEtapeActive {{
        color: {p.texte_inverse};
        font-size: 12pt;
        font-weight: 600;
        padding: 6px 0px;
    }}

    /* ----- Boutons ----- */
    QPushButton {{
        background-color: {p.surface};
        border: 1px solid {p.bordure_forte};
        border-radius: {m.rayon}px;
        padding: 9px 20px;
        font-size: 12pt;
        color: {p.texte};
    }}
    QPushButton:hover {{
        background-color: {p.surface_alt};
        border-color: {p.texte_tertiaire};
    }}
    QPushButton:disabled {{
        color: {p.texte_tertiaire};
        background-color: {p.surface_alt};
        border-color: {p.bordure};
    }}
    QPushButton#Principal {{
        background-color: {p.accent};
        color: #FFFFFF;
        border: 1px solid {p.accent};
        font-weight: 600;
    }}
    QPushButton#Principal:hover {{
        background-color: {p.accent_sombre};
        border-color: {p.accent_sombre};
    }}
    QPushButton#Principal:disabled {{
        background-color: {p.bordure_forte};
        border-color: {p.bordure_forte};
        color: {p.surface};
    }}
    QPushButton#Discret {{
        background-color: transparent;
        border: none;
        color: {p.texte_secondaire};
        padding: 9px 12px;
    }}
    QPushButton#Discret:hover {{
        color: {p.accent};
        background-color: transparent;
    }}

    /* ----- Champs de saisie ----- */
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
        background-color: {p.surface};
        border: 1px solid {p.bordure_forte};
        border-radius: {m.rayon}px;
        padding: 7px 10px;
        font-family: {POLICE_MONO};
        font-size: 12pt;
        selection-background-color: {p.accent_clair};
        selection-color: {p.texte};
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
        border: 2px solid {p.accent};
        padding: 6px 9px;
    }}
    QLineEdit[invalide="true"] {{
        border: 2px solid {p.danger};
        padding: 6px 9px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface};
        border: 1px solid {p.bordure_forte};
        selection-background-color: {p.accent_clair};
        selection-color: {p.texte};
        outline: none;
    }}

    /* ----- Tableaux de résultats ----- */
    QTableWidget {{
        background-color: {p.surface};
        border: 1px solid {p.bordure};
        border-radius: {m.rayon}px;
        gridline-color: {p.bordure};
        font-family: {POLICE_MONO};
        font-size: 12pt;
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.texte_secondaire};
        border: none;
        border-bottom: 1px solid {p.bordure};
        padding: 8px 10px;
        font-family: {POLICE_UI};
        font-size: 12pt;
        font-weight: 600;
    }}
    QTableWidget::item {{
        padding: 6px 10px;
    }}

    /* ----- Divers ----- */
    QScrollArea {{ border: none; background-color: transparent; }}
    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.bordure_forte}; border-radius: 5px; min-height: 30px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}
    QGroupBox {{
        border: none;
        margin-top: 4px;
    }}
    QToolTip {{
        background-color: {p.surface_sombre};
        color: {p.texte_inverse};
        border: none;
        padding: 6px 9px;
        border-radius: 4px;
    }}
    """
