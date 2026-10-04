"""Description déclarative des formulaires de saisie, par type d'élément.

Un formulaire est de la *donnée*, pas du code : chaque élément déclare ses
groupes de champs (libellé, unité, valeur par défaut, aide, validation).
La page de saisie lit cette description et se construit toute seule.

Conséquence : ajouter un élément au logiciel (section en T, poutre-voile...)
ne demande pas d'écrire du code d'interface, seulement une entrée dans
`SCHEMAS`. C'est ce qui rend l'interface évolutive sans dette.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Champ:
    """Un champ de saisie d'une grandeur physique."""

    cle: str                      # identifiant utilisé par l'adaptateur de calcul
    libelle: str
    unite: str = ""
    defaut: str = ""
    info: str = ""
    validateur: Callable[[float], bool] = lambda v: v > 0
    message_erreur: str = "Valeur strictement positive attendue"


@dataclass(frozen=True)
class GroupeChamps:
    """Un bloc thématique de champs (géométrie, matériaux, sollicitations)."""

    titre: str
    champs: tuple[Champ, ...]
    colonnes: int = 2


@dataclass(frozen=True)
class SchemaFormulaire:
    """Le formulaire complet d'un élément."""

    titre: str
    description: str
    groupes: tuple[GroupeChamps, ...]
    options: dict[str, tuple[str, ...]] = field(default_factory=dict)


# Validateurs partagés
_positif = lambda v: v > 0
_reel = lambda v: True  # accepte le négatif (effort normal de traction)


SCHEMAS: dict[str, SchemaFormulaire] = {
    "poteau": SchemaFormulaire(
        titre="Poteau rectangulaire",
        description="Section rectangulaire soumise à un effort normal excentré",
        groupes=(
            GroupeChamps(
                titre="Géométrie de la section",
                champs=(
                    Champ("b", "Largeur b", "cm", "30", "Plus petite dimension de la section"),
                    Champ("h", "Hauteur h", "cm", "40", "Dimension dans le plan de flexion étudié"),
                    Champ("enrobage", "Enrobage c", "cm", "3", "Enrobage nominal des armatures"),
                    Champ("diametre", "Diamètre Φ", "mm", "20", "Diamètre des barres longitudinales"),
                ),
            ),
            GroupeChamps(
                titre="Élancement",
                champs=(
                    Champ("longueur", "Hauteur libre l", "m", "3.5", "Hauteur libre du poteau entre appuis"),
                    Champ("hauteur_poutre", "Hauteur de poutre en tête", "cm", "35", "Pour la planche de ferraillage"),
                ),
                colonnes=2,
            ),
            GroupeChamps(
                titre="Matériaux",
                champs=(
                    Champ("fck", "Béton fck", "MPa", "25", "Résistance caractéristique à 28 jours"),
                    Champ("fyk", "Acier fyk", "MPa", "500", "Limite d'élasticité caractéristique"),
                ),
            ),
            GroupeChamps(
                titre="Sollicitations ELU",
                champs=(
                    Champ("N_elu", "Effort normal N", "kN", "800",
                          "Positif en compression, négatif en traction", _reel,
                          "Valeur numérique attendue"),
                    Champ("M_elu", "Moment M", "kN·m", "120",
                          "Moment par rapport au centre de gravité du béton seul", _reel,
                          "Valeur numérique attendue"),
                ),
            ),
            GroupeChamps(
                titre="Sollicitations ELS (facultatif)",
                champs=(
                    Champ("N_els", "Effort normal N", "kN", "580", "Laisser vide pour ignorer l'ELS", _reel, ""),
                    Champ("M_els", "Moment M", "kN·m", "85", "Laisser vide pour ignorer l'ELS", _reel, ""),
                ),
            ),
        ),
        options={
            "condition_appui": (
                "Encastrement + rotule (l₀ = 0,7·l)",
                "Deux encastrements (l₀ = 0,5·l)",
                "Deux rotules (l₀ = l)",
                "Encastrement + libre (l₀ = 2·l)",
                "Portique non intégré au contreventement (l₀ fonction de k₁, k₂)",
                "Portique intégré au contreventement (l₀ fonction de k₁, k₂)",
            )
        },
    ),
    "voute": SchemaFormulaire(
        titre="Voûte à trois articulations",
        description="Arc de cercle surbaissé, rotules à la clef et aux naissances",
        groupes=(
            GroupeChamps(
                titre="Géométrie de l'arc",
                champs=(
                    Champ("portee", "Portée l", "m", "12", "Distance entre naissances"),
                    Champ("fleche", "Flèche f", "m", "1.2", "Hauteur de l'arc à la clef (l/10 usuel)"),
                    Champ("epaisseur", "Épaisseur hw", "cm", "30", "Épaisseur de la voûte"),
                    Champ("largeur", "Bande de calcul b", "m", "1", "Largeur de la bande étudiée"),
                ),
            ),
            GroupeChamps(
                titre="Chargement",
                champs=(
                    Champ("charge", "Charge répartie p", "kN/m", "45", "Charge verticale uniformément répartie"),
                ),
            ),
            GroupeChamps(
                titre="Matériaux et enrobage",
                champs=(
                    Champ("fck", "Béton fck", "MPa", "25"),
                    Champ("fyk", "Acier fyk", "MPa", "500"),
                    Champ("enrobage", "Enrobage c", "cm", "3"),
                    Champ("diametre", "Diamètre Φ", "mm", "12"),
                ),
            ),
        ),
    ),
    "mur": SchemaFormulaire(
        titre="Mur porteur (voile)",
        description="Console verticale encastrée en pied, vérifications du béton non armé",
        groupes=(
            GroupeChamps(
                titre="Géométrie du voile",
                champs=(
                    Champ("hauteur", "Hauteur libre lw", "m", "4", "Hauteur libre entre planchers"),
                    Champ("longueur", "Longueur de calcul b", "m", "2.5", "Longueur de la bande de voile"),
                    Champ("epaisseur", "Épaisseur hw", "cm", "30"),
                    Champ("enrobage", "Enrobage c", "cm", "3"),
                ),
            ),
            GroupeChamps(
                titre="Matériaux",
                champs=(
                    Champ("fck", "Béton fck", "MPa", "40"),
                    Champ("fyk", "Acier fyk", "MPa", "500"),
                ),
            ),
            GroupeChamps(
                titre="Sollicitations ELU",
                champs=(
                    Champ("N_elu", "Effort normal N", "kN", "712.5", "", _reel, "Valeur numérique attendue"),
                    Champ("M_elu", "Moment M (plan)", "kN·m", "142.5",
                          "Moment agissant dans le plan du voile", _reel, "Valeur numérique attendue"),
                    Champ("V_elu", "Effort tranchant V", "kN", "171", "", _reel, "Valeur numérique attendue"),
                    Champ("excentricite", "Excentricité e (épaisseur)", "cm", "0",
                          "Excentricité dans l'ÉPAISSEUR du voile — à ne pas confondre "
                          "avec e₁=M/N dans le plan", lambda v: v >= 0,
                          "Valeur positive ou nulle attendue"),
                ),
            ),
        ),
        options={
            "beta": (
                "Encastré tête et pied, bords libres (β = 1,0)",
                "Encastré en pied seulement (β = 2,0)",
                "Trois bords maintenus (β = 0,8)",
            )
        },
    ),
}


SCHEMAS["poteau_circ"] = SchemaFormulaire(
    titre="Poteau circulaire",
    description="Section circulaire, armatures réparties sur le pourtour, effort normal excentré",
    groupes=(
        GroupeChamps(
            titre="Géométrie de la section",
            champs=(
                Champ("D", "Diamètre D", "cm", "45", "Diamètre de la section"),
                Champ("enrobage", "Enrobage c", "cm", "3", "Enrobage nominal"),
                Champ("diametre", "Diamètre Φ", "mm", "20", "Diamètre de calcul pour d'"),
                Champ("nb_barres", "Nombre de barres", "", "8", "Barres réparties sur le pourtour",
                      lambda v: v >= 6 and float(v).is_integer(), "Nombre entier, au moins 6 barres"),
            ),
        ),
        GroupeChamps(
            titre="Élancement",
            champs=(Champ("longueur", "Hauteur libre l", "m", "3.5", "Hauteur libre du poteau entre appuis"),),
        ),
        GroupeChamps(
            titre="Matériaux",
            champs=(
                Champ("fck", "Béton fck", "MPa", "25", "Résistance caractéristique à 28 jours"),
                Champ("fyk", "Acier fyk", "MPa", "500", "Limite d'élasticité caractéristique"),
            ),
        ),
        GroupeChamps(
            titre="Sollicitations ELU",
            champs=(
                Champ("N_elu", "Effort normal N", "kN", "800", "Positif en compression, négatif en traction",
                      _reel, "Valeur numérique attendue"),
                Champ("M_elu", "Moment M", "kN·m", "120", "Moment par rapport au centre de la section",
                      _reel, "Valeur numérique attendue"),
            ),
        ),
        GroupeChamps(
            titre="Sollicitations ELS (facultatif)",
            champs=(
                Champ("N_els", "Effort normal N", "kN", "580", "Laisser vide pour ignorer l'ELS", _reel, ""),
                Champ("M_els", "Moment M", "kN·m", "85", "Laisser vide pour ignorer l'ELS", _reel, ""),
            ),
        ),
    ),
    options=dict(SCHEMAS["poteau"].options),
)
