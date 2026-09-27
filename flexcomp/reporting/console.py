"""Mise en forme des résultats pour la console.

Utilise `rich` si le paquet est installé (rendu soigné : tableaux, couleurs,
panneaux), et se replie silencieusement sur un affichage texte simple sinon
— aucune dépendance obligatoire pour que le moteur de calcul reste utilisable
partout (scripts, futurs tests CI, etc.).
"""

from __future__ import annotations

from flexcomp.results.dataclasses import (
    ArmaturesSection,
    CasSection,
    ResultatMurPorteur,
    ResultatPoteau,
    ResultatVoute,
)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    _RICH_DISPONIBLE = True
    _console = Console()
except ImportError:  # pragma: no cover - repli sans dépendance
    _RICH_DISPONIBLE = False
    _console = None


_LIBELLES_CAS = {
    CasSection.PARTIELLEMENT_COMPRIMEE: "Section partiellement comprimée",
    CasSection.ENTIEREMENT_TENDUE: "Section entièrement tendue",
    CasSection.ENTIEREMENT_COMPRIMEE: "Section entièrement comprimée",
}


def _imprimer_titre(titre: str) -> None:
    if _RICH_DISPONIBLE:
        _console.print(Panel(titre, style="bold cyan"))
    else:
        print("=" * len(titre))
        print(titre)
        print("=" * len(titre))


def _imprimer_lignes(lignes: list[tuple[str, str]]) -> None:
    if _RICH_DISPONIBLE:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold")
        table.add_column()
        for cle, valeur in lignes:
            table.add_row(cle, valeur)
        _console.print(table)
    else:
        largeur = max(len(cle) for cle, _ in lignes)
        for cle, valeur in lignes:
            print(f"  {cle.ljust(largeur)} : {valeur}")


def rapport_poteau(resultat: ResultatPoteau) -> None:
    """Affiche un rapport lisible pour un ResultatPoteau."""
    _imprimer_titre("POTEAU RECTANGULAIRE — Résultat du dimensionnement ELU")

    effets = resultat.effets_2nd_ordre
    _imprimer_lignes([
        ("Sollicitation ELU", f"N = {resultat.sollicitation_elu.N:.1f} kN   "
                               f"M = {resultat.sollicitation_elu.M:.2f} kN.m"),
        ("Élancement", f"λ = {effets.lambda_calcule:.2f}   λ_lim = {effets.lambda_limite:.2f}   "
                        f"second ordre : {'OUI' if effets.second_ordre_necessaire else 'non'}"),
        ("Excentricité totale", f"e_tot = {effets.excentricite_totale * 100:.2f} cm"),
        ("Moment de calcul", f"M*_Ed = {effets.moment_calcul:.2f} kN.m"),
        ("Cas de section", _LIBELLES_CAS[resultat.cas]),
    ])
    if resultat.moment_reduit is not None:
        _imprimer_lignes([("Moment réduit", f"μ_Ed,A = {resultat.moment_reduit:.3f}")])

    _imprimer_lignes([
        ("As1", f"{resultat.armatures.As1:.1f} mm²"),
        ("As2", f"{resultat.armatures.As2:.1f} mm²"),
        ("As,min (par nappe)", f"{resultat.armatures.As_min:.1f} mm²"),
    ])
    for note in resultat.notes:
        print(f"  · {note}")


def rapport_voute(resultat: ResultatVoute) -> None:
    _imprimer_titre("VOÛTE À TROIS ARTICULATIONS — Résultat du calcul")
    sc = resultat.section_critique
    _imprimer_lignes([
        ("Poussée horizontale H", f"{resultat.poussee_horizontale:.2f} kN/m"),
        ("Rayon de l'arc R", f"{resultat.rayon_arc:.2f} m"),
        ("Moments aux 3 rotules", f"{tuple(round(m, 4) for m in resultat.moments_aux_rotules)}"),
        ("Section critique", f"x* = {sc.x:.2f} m   M(x*) = {sc.moment:.2f} kN.m   "
                               f"N = {sc.effort_normal:.2f} kN"),
        ("Excentricité totale", f"{resultat.effets_2nd_ordre.excentricite_totale * 100:.2f} cm"),
        ("EC2 §12.6 (flambement)", "OK" if resultat.verification_12_6.verifie else "NON VÉRIFIÉ"),
        ("As1 / m", f"{resultat.armatures.As1:.1f} mm²/m"),
        ("As2 / m", f"{resultat.armatures.As2:.1f} mm²/m"),
    ])


def rapport_mur_porteur(resultat: ResultatMurPorteur) -> None:
    _imprimer_titre("MUR PORTEUR — Vérifications EC2 §12.6")
    _imprimer_lignes([
        ("Vérif. 1 — forces axiales", f"N_Rd1 = {resultat.verif_forces_axiales.N_Rd1:.0f} kN "
                                        f"({'OK' if resultat.verif_forces_axiales.verifie else 'KO'})"),
        ("Vérif. 2 — effort tranchant", f"τ_cp = {resultat.verif_effort_tranchant.tau_cp:.3f} MPa "
                                          f"<= f_cvd = {resultat.verif_effort_tranchant.f_cvd:.3f} MPa "
                                          f"({'OK' if resultat.verif_effort_tranchant.verifie else 'KO'})"),
        ("Vérif. 3 — flambement", f"N_Rd12 = {resultat.verif_flambement.N_Rd12:.0f} kN "
                                    f"({'OK' if resultat.verif_flambement.verifie else 'KO'})"),
        ("Conclusion", "NON ARMÉ possible" if resultat.calculable_non_arme else "Mur À ARMER"),
    ])
    for note in resultat.notes:
        print(f"  · {note}")
