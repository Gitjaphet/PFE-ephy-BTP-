"""Adaptateur entre l'interface et le moteur de calcul.

Rôle unique : convertir un dictionnaire de valeurs saisies (en unités
« chantier » : cm, mm, m, kN) en objets du moteur (`PoteauRectangulaire`,
`VouteTroisArticulations`, `MurPorteur`, qui travaillent en mètres), lancer
le calcul, et rendre le résultat.

C'est la seule frontière où les unités sont converties. Le moteur ne connaît
que le mètre et le kN ; l'interface ne connaît que ce que l'ingénieur écrit
sur un plan. Aucune de ces deux couches n'a besoin de connaître l'autre.
"""

from __future__ import annotations

from typing import Any

from flexcomp.core import Acier, Beton, ConditionAppui
from flexcomp.elements import MurPorteur, PoteauRectangulaire, VouteTroisArticulations
from flexcomp.results import Sollicitation
from flexcomp.sections import SectionRectangulaire

_CONDITIONS_APPUI = {
    0: ConditionAppui.ENCASTREMENT_ROTULE,
    1: ConditionAppui.DEUX_ENCASTREMENTS,
    2: ConditionAppui.DEUX_ROTULES,
    3: ConditionAppui.ENCASTREMENT_LIBRE,
    4: ConditionAppui.PORTIQUE_NON_INTEGRE,
    5: ConditionAppui.PORTIQUE_INTEGRE,
}

_BETA_VOILE = {0: 1.0, 1: 2.0, 2: 0.8}


def calculer_poteau(donnees: dict[str, Any]) -> dict[str, Any]:
    """Construit le poteau, le dimensionne, et retourne le modèle + résultat."""
    section = SectionRectangulaire(
        b=donnees["b"] / 100.0,                 # cm -> m
        h=donnees["h"] / 100.0,
        enrobage_nominal=donnees["enrobage"] / 100.0,
        diametre_barre=donnees["diametre"] / 1000.0,  # mm -> m
    )
    poteau = PoteauRectangulaire(
        section=section,
        longueur_libre=donnees["longueur"],
        condition_appui=_CONDITIONS_APPUI[donnees.get("condition_appui", 0)],
        k1=donnees.get("k1") or 0.1,
        k2=donnees.get("k2") or 0.1,
        beton=Beton(fck=donnees["fck"]),
        acier=Acier(fyk=donnees["fyk"]),
    )
    sollicitation = Sollicitation(N=donnees["N_elu"], M=donnees["M_elu"])
    resultat = poteau.dimensionner(sollicitation)

    sollicitation_els = None
    if donnees.get("N_els") is not None and donnees.get("M_els") is not None:
        sollicitation_els = Sollicitation(N=donnees["N_els"], M=donnees["M_els"])

    return {
        "modele": poteau,
        "resultat": resultat,
        "sollicitation_els": sollicitation_els,
    }


def calculer_voute(donnees: dict[str, Any]) -> dict[str, Any]:
    voute = VouteTroisArticulations(
        portee=donnees["portee"],
        fleche=donnees["fleche"],
        charge_uniforme=donnees["charge"],
        epaisseur=donnees["epaisseur"] / 100.0,     # cm -> m
        beton=Beton(fck=donnees["fck"]),
        acier=Acier(fyk=donnees["fyk"]),
        largeur_calcul=donnees["largeur"],
        enrobage_nominal=donnees["enrobage"] / 100.0,
        diametre_barre=donnees["diametre"] / 1000.0,
    )
    return {"modele": voute, "resultat": voute.dimensionner()}


def calculer_mur(donnees: dict[str, Any]) -> dict[str, Any]:
    mur = MurPorteur(
        hauteur_libre=donnees["hauteur"],
        longueur_calcul=donnees["longueur"],
        epaisseur=donnees["epaisseur"] / 100.0,
        beta=_BETA_VOILE[donnees.get("beta", 0)],
        beton=Beton(fck=donnees["fck"]),
        acier=Acier(fyk=donnees["fyk"]),
        enrobage_nominal=donnees["enrobage"] / 100.0,
    )
    resultat = mur.verifier_non_arme(
        N_Ed=donnees["N_elu"],
        V_Ed=donnees["V_elu"],
        e=donnees["excentricite"] / 100.0,
    )
    armatures = mur.dimensionner_arme(
        Sollicitation(N=donnees["N_elu"], M=donnees["M_elu"])
    )
    return {"modele": mur, "resultat": resultat, "armatures_si_arme": armatures}


CALCULATEURS = {
    "poteau": calculer_poteau,
    "voute": calculer_voute,
    "mur": calculer_mur,
}


def calculer(identifiant_element: str, donnees: dict[str, Any]) -> dict[str, Any]:
    """Point d'entrée unique appelé par l'interface."""
    return CALCULATEURS[identifiant_element](donnees)
