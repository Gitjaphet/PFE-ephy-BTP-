"""Programme console de flexcomp : saisie au clavier et calcul déroulé étape par
étape (poteau, voûte, mur), avec le même moteur de calcul que l'interface.

Lancement : python run_console.py
"""

from __future__ import annotations

from dataclasses import replace

from flexcomp.core.barres import format_choix, lire_choix, section_barres
from flexcomp.gui.adaptateur import calculer_mur, calculer_poteau, calculer_voute
from flexcomp.results import CasSection, Sollicitation

LIGNE = "=" * 64
CAS = {
    CasSection.PARTIELLEMENT_COMPRIMEE: "Cas 1 : section partiellement comprimée",
    CasSection.ENTIEREMENT_TENDUE: "Cas 2 : section entièrement tendue",
    CasSection.ENTIEREMENT_COMPRIMEE: "Cas 3 : section entièrement comprimée",
}
APPUIS = (
    "Encastrement + rotule (l0 = 0,7.l)",
    "Deux encastrements (l0 = 0,5.l)",
    "Deux rotules (l0 = l)",
    "Encastrement + libre (l0 = 2.l)",
    "Portique non intégré au contreventement (k1, k2)",
    "Portique intégré au contreventement (k1, k2)",
)
BETA = ("beta = 1,0", "beta = 2,0", "beta = 0,8")


# ----------------------------------------------------------------------
# Saisie
# ----------------------------------------------------------------------
def lire(texte: str, defaut: float) -> float:
    """Lit un nombre ; Entrée = valeur par défaut (celle du rapport)."""
    while True:
        saisie = input(f"   {texte} [{defaut:g}] : ").strip().replace(",", ".")
        if not saisie:
            return defaut
        try:
            return float(saisie)
        except ValueError:
            print("   -> valeur numérique attendue.")


def lire_option(titre: str, options: tuple[str, ...]) -> int:
    print(f"   {titre} :")
    for i, texte in enumerate(options, 1):
        print(f"     {i}. {texte}")
    while True:
        saisie = input("   Choix [1] : ").strip()
        if not saisie:
            return 0
        if saisie.isdigit() and 1 <= int(saisie) <= len(options):
            return int(saisie) - 1
        print(f"   -> entrez un numéro entre 1 et {len(options)}.")


def lire_armature(nom: str, requis: float, unite: str, largeur: float = 1.0) -> tuple[int, int]:
    """Choix « nHAφ » ; refusé tant que la section réelle est insuffisante."""
    while True:
        texte = input(f"   Choix arm. {nom} (ex : 4HA12) : ").strip()
        choix = lire_choix(texte)
        if choix is None:
            print("   -> format attendu : 4HA12 (diamètre HA de la table).")
            continue
        reel = section_barres(*choix) / largeur
        if reel < requis - 0.5:
            print(f"   -> Ast réel = {reel:.0f} {unite} < requis {requis:.1f} {unite} : insuffisant.")
            continue
        print(f"      Ast réel = {reel:.0f} {unite} >= requis {requis:.1f} {unite}  OK")
        return choix


def titre(texte: str) -> None:
    print(f"\n{LIGNE}\n  {texte}\n{LIGNE}")


def etape(texte: str) -> None:
    print(f"\n{texte}")


def verdict(ok: bool) -> str:
    return "vérifié" if ok else "NON VÉRIFIÉ"


# ----------------------------------------------------------------------
# Poteau
# ----------------------------------------------------------------------
def poteau() -> None:
    titre("POTEAU RECTANGULAIRE — FLEXION COMPOSÉE (EUROCODE 2)")
    etape("1. Données (Entrée = valeur du rapport)")
    d = dict(
        b=lire("Largeur b (cm)", 30), h=lire("Hauteur h (cm)", 40),
        enrobage=lire("Enrobage c (cm)", 3), diametre=lire("Diamètre Φ (mm)", 20),
        longueur=lire("Hauteur libre l (m)", 3.5),
        fck=lire("Béton fck (MPa)", 25), fyk=lire("Acier fyk (MPa)", 500),
        N_elu=lire("ELU : effort normal NEd (kN)", 800), M_elu=lire("ELU : moment MEd (kN.m)", 120),
        N_els=lire("ELS : effort normal Nser (kN)", 580), M_els=lire("ELS : moment Mser (kN.m)", 85),
    )
    d["condition_appui"] = lire_option("Conditions aux appuis", APPUIS)
    if d["condition_appui"] >= 4:
        d["k1"], d["k2"] = lire("Souplesse en pied k1", 0.1), lire("Souplesse en tête k2", 0.1)

    s = calculer_poteau(d)
    p, r = s["modele"], s["resultat"]
    e, a, sec = r.effets_2nd_ordre, r.armatures, p.section

    etape("2. Caractéristiques des matériaux et de la section")
    print(f"   fcd = fck/1,5  = {p.beton.fcd:.2f} MPa")
    print(f"   fyd = fyk/1,15 = {d['fyk'] / 1.15:.2f} MPa")
    print(f"   d  = h - c - Φ/2 = {sec.d * 100:.1f} cm      d' = c + Φ/2 = {sec.d_prime * 100:.1f} cm")
    print(f"   l0 = {p.l0:.3f} m  ({APPUIS[d['condition_appui']]})")

    etape("3. Élancement et effets du second ordre")
    print(f"   λ = l0/i = {e.lambda_calcule:.2f}      λlim = 20.A.B.C/√n = {e.lambda_limite:.2f}")
    print("   -> second ordre " + ("PRIS EN COMPTE (λ > λlim)" if e.second_ordre_necessaire
                                     else "négligeable (λ <= λlim)"))
    print(f"   e1 = MEd/NEd = {e.excentricite_1er_ordre * 100:.2f} cm")
    print(f"   ei = l0/400  = {e.excentricite_imperfection * 100:.3f} cm")
    print(f"   e2           = {e.excentricite_2nd_ordre * 100:.3f} cm")
    print(f"   etot = e1 + ei + e2 = {e.excentricite_totale * 100:.2f} cm   (e0,min = {e.excentricite_min * 100:.2f} cm)")
    print(f"   M*Ed = NEd.etot = {e.moment_calcul:.2f} kN.m")

    etape("4. Identification du cas de section")
    print(f"   {CAS[r.cas]}")
    if r.moment_reduit is not None:
        print(f"   μEd,A = {r.moment_reduit:.3f}")

    etape("5. Armatures à l'ELU")
    print(f"   As1 = {a.As1:.1f} mm²      As2 = {a.As2:.1f} mm²")
    print(f"   As,min = {a.As_min:.1f} mm²" + (f"      As,max = {a.As_max:.0f} mm²" if a.As_max else ""))
    for note in r.notes:
        print(f"   · {note}")

    etape("6. Choix des armatures")
    c1 = lire_armature("As1", a.As1, "mm²")
    c2 = lire_armature("As2", a.As2, "mm²")
    choisies = replace(a, As1=section_barres(*c1), As2=section_barres(*c2))
    total = choisies.As1 + choisies.As2
    print(f"   Retenu : As1 = {format_choix(*c1)}, As2 = {format_choix(*c2)}  (total {total:.0f} mm²)")

    etape("7. Vérification à l'ELS (armatures choisies)")
    v = p.verifier_els(Sollicitation(N=d["N_els"], M=d["M_els"]), choisies)
    if d["N_els"] >= 0:
        print(f"   σc = {v.sigma_beton:.2f} MPa <= {v.sigma_beton_limite:.2f} MPa  -> {verdict(v.beton_verifie)}")
    print(f"   σs = {v.sigma_acier:.2f} MPa <= {v.sigma_acier_limite:.2f} MPa  -> {verdict(v.acier_verifie)}")


# ----------------------------------------------------------------------
# Voûte
# ----------------------------------------------------------------------
def voute() -> None:
    titre("VOÛTE À TROIS ARTICULATIONS — FLEXION COMPOSÉE")
    etape("1. Données (Entrée = valeur du rapport)")
    d = dict(
        portee=lire("Portée l (m)", 12), fleche=lire("Flèche f (m)", 1.2),
        charge=lire("Charge p (kN/m)", 45), epaisseur=lire("Épaisseur hw (cm)", 30),
        largeur=lire("Bande de calcul b (m)", 1), enrobage=lire("Enrobage c (cm)", 3),
        diametre=lire("Diamètre Φ (mm)", 12),
        fck=lire("Béton fck (MPa)", 25), fyk=lire("Acier fyk (MPa)", 500),
    )
    s = calculer_voute(d)
    v, r = s["modele"], s["resultat"]
    sc, e, w, a = r.section_critique, r.effets_2nd_ordre, r.verification_12_6, r.armatures

    etape("2. Statique de l'arc (Mesnager)")
    print(f"   H = p.l²/(8f) = {r.poussee_horizontale:.2f} kN/m")
    print(f"   R = l²/(8f) + f/2 = {r.rayon_arc:.2f} m")
    m0, m1, m2 = r.moments_aux_rotules
    print(f"   Moments aux 3 rotules : {m0:.4f} ; {m1:.4f} ; {m2:.4f} kN.m  -> isostatique")

    etape("3. Section critique")
    print(f"   x* = {sc.x:.2f} m      M(x*) = {sc.moment:.2f} kN.m      N = {sc.effort_normal:.2f} kN")
    print(f"   e_géo = |M|/N = {sc.excentricite_geo * 100:.2f} cm      etot = {e.excentricite_totale * 100:.2f} cm")
    print(f"   Mdesign = {e.moment_calcul:.2f} kN.m")

    etape("4. Vérification du béton non armé (EC2 §12.6)")
    print(f"   λ = {w.lambda_calcule:.2f} (<= 86 : {'oui' if w.elancement_ok else 'NON'})      Φ = {w.phi:.3f}")
    print(f"   NEd = {w.N_Ed:.1f} kN <= NRd,12 = {w.N_Rd12:.1f} kN  -> {verdict(w.verifie)}")

    etape("5. Armatures à la section critique (par mètre)")
    print(f"   As1 = {a.As1:.1f} mm²/m      As2 = {a.As2:.1f} mm²/m      As,min = {a.As_min:.1f} mm²/m")

    etape(f"6. Choix des armatures (par bande de {d['largeur']:.2f} m)")
    c1 = lire_armature("As1 (extrados)", a.As1, "mm²/m", d["largeur"])
    c2 = lire_armature("As2 (intrados)", a.As2, "mm²/m", d["largeur"])
    choisies = replace(a, As1=section_barres(*c1) / d["largeur"], As2=section_barres(*c2) / d["largeur"])
    print(f"   Retenu : As1 = {format_choix(*c1)} (s = {d['largeur'] * 100 / c1[0]:.0f} cm), "
          f"As2 = {format_choix(*c2)} (s = {d['largeur'] * 100 / c2[0]:.0f} cm)")

    etape("7. Vérification à l'ELS (Nser = N/1,35 ; Mser = M/1,35)")
    els = v.verifier_els(r, choisies)
    print(f"   σc = {els.sigma_beton:.2f} MPa <= {els.sigma_beton_limite:.2f} MPa  -> {verdict(els.beton_verifie)}")
    print(f"   σs = {els.sigma_acier:.2f} MPa <= {els.sigma_acier_limite:.2f} MPa  -> {verdict(els.acier_verifie)}")


# ----------------------------------------------------------------------
# Mur porteur
# ----------------------------------------------------------------------
def mur() -> None:
    titre("MUR PORTEUR (VOILE) — EC2 §12.6 ET FLEXION COMPOSÉE")
    etape("1. Données (Entrée = valeur du rapport)")
    d = dict(
        hauteur=lire("Hauteur libre lw (m)", 4), longueur=lire("Longueur de calcul b (m)", 2.5),
        epaisseur=lire("Épaisseur hw (cm)", 30), enrobage=lire("Enrobage c (cm)", 3),
        fck=lire("Béton fck (MPa)", 40), fyk=lire("Acier fyk (MPa)", 500),
        N_elu=lire("NEd (kN)", 712.5), M_elu=lire("MEd dans le plan (kN.m)", 142.5),
        V_elu=lire("VEd (kN)", 171), excentricite=lire("Excentricité e dans l'épaisseur (cm)", 0),
    )
    d["beta"] = lire_option("Coefficient de longueur efficace", BETA)
    s = calculer_mur(d)
    m, r, a = s["modele"], s["resultat"], s["armatures_si_arme"]
    f1, f2, f3 = r.verif_forces_axiales, r.verif_effort_tranchant, r.verif_flambement

    etape("2. Longueur efficace et élancement")
    print(f"   l0 = β.lw = {m.l0:.2f} m      λ = l0/i = {m.elancement:.2f}  (limite 86)")

    etape("3. Vérifications du béton non armé (EC2 §12.6)")
    print(f"   1 — Forces axiales   : NEd = {f1.N_Ed:.1f} kN <= NRd1 = {f1.N_Rd1:.1f} kN  -> {verdict(f1.verifie)}")
    print(f"   2 — Effort tranchant : τcp = {f2.tau_cp:.3f} MPa <= fcvd = {f2.f_cvd:.3f} MPa  -> {verdict(f2.verifie)}")
    print(f"   3 — Flambement       : NEd = {f3.N_Ed:.1f} kN <= NRd,12 = {f3.N_Rd12:.1f} kN  -> {verdict(f3.verifie)}")
    print("   Conclusion : " + ("mur calculable comme NON ARMÉ" if r.calculable_non_arme
                               else "le mur DOIT être armé"))

    if a is not None:
        etape("4. Flexion composée dans le plan : aciers d'about")
        print(f"   As1 = {a.As1:.1f} mm² par about      As,min = {a.As_min:.1f} mm²")
        etape("5. Choix des armatures d'about")
        c1 = lire_armature("As1 (about)", a.As1, "mm²")
        print(f"   Retenu : {format_choix(*c1)} à chaque extrémité du voile")


# ----------------------------------------------------------------------
# Poteau circulaire
# ----------------------------------------------------------------------
def poteau_circulaire() -> None:
    from dataclasses import replace as remplacer
    from flexcomp.core.materials import Acier, Beton
    from flexcomp.elements.poteau_circulaire import PoteauCirculaire
    from flexcomp.gui.adaptateur import _CONDITIONS_APPUI

    titre("POTEAU CIRCULAIRE — FLEXION COMPOSÉE (EUROCODE 2)")
    etape("1. Données (Entrée = valeur par défaut)")
    D = lire("Diamètre D (cm)", 45)
    l = lire("Hauteur libre l (m)", 3.5)
    c = lire("Enrobage c (cm)", 3)
    phi = lire("Diamètre Φ pour d' (mm)", 20)
    fck, fyk = lire("Béton fck (MPa)", 25), lire("Acier fyk (MPa)", 500)
    N, M = lire("ELU : effort normal NEd (kN)", 800), lire("ELU : moment MEd (kN.m)", 120)
    Ns, Ms = lire("ELS : effort normal Nser (kN)", 580), lire("ELS : moment Mser (kN.m)", 85)
    nb = 0
    while nb < 6:
        nb = int(lire("Nombre de barres réparties (>= 6)", 8))
        if nb < 6:
            print("   -> au moins 6 barres pour une section circulaire (EC2 §9.5.2(4)).")
    appui = lire_option("Conditions aux appuis", APPUIS)
    k1 = k2 = 0.1
    if appui >= 4:
        k1, k2 = lire("Souplesse en pied k1", 0.1), lire("Souplesse en tête k2", 0.1)

    p = PoteauCirculaire(diametre=D / 100, longueur_libre=l, condition_appui=_CONDITIONS_APPUI[appui],
                         beton=Beton(fck=fck), acier=Acier(fyk=fyk), enrobage_nominal=c / 100,
                         diametre_barre=phi / 1000, nombre_barres=nb, k1=k1, k2=k2)
    s = Sollicitation(N=N, M=M)

    etape("2. Caractéristiques des matériaux et de la section")
    print(f"   fcd = fck/1,5  = {p.beton.fcd:.2f} MPa      fyd = fyk/1,15 = {p.fyd:.2f} MPa")
    print(f"   d' = c + Φ/2 = {p.d_prime/10:.1f} cm      rs = D/2 − d' = {p.rs/10:.1f} cm (cercle des armatures)")
    print(f"   Ac = π.D²/4 = {p.Ac:.0f} mm²      i = D/4 = {p.rayon_giration*100:.2f} cm")
    print(f"   d (courbure) = D/2 + rs/√2 = {p.d_courbure/10:.2f} cm")
    print(f"   l0 = {p.l0:.3f} m  ({APPUIS[appui]})")

    r = p.dimensionner(s)
    e = r.effets_2nd_ordre
    if e is not None:
        etape("3. Élancement et effets du second ordre")
        print(f"   λ = l0/i = {e.lambda_calcule:.2f}      λlim = 20.A.B.C/√n = {e.lambda_limite:.2f}")
        print("   -> second ordre " + ("PRIS EN COMPTE (λ > λlim)" if e.second_ordre_necessaire
                                         else "négligeable (λ <= λlim)"))
        print(f"   e1 = {e.excentricite_1er_ordre*100:.2f} cm   ei = {e.excentricite_imperfection*100:.3f} cm"
              f"   e2 = {e.excentricite_2nd_ordre*100:.3f} cm")
        print(f"   etot = {e.excentricite_totale*100:.2f} cm   (e0,min = {e.excentricite_min*100:.2f} cm)")
        print(f"   M*Ed = NEd.etot = {e.moment_calcul:.2f} kN.m")
    else:
        etape("3. Traction : pas d'effet du second ordre")
        print(f"   e0 = |MEd/NEd| = {abs(M / N)*100:.2f} cm")

    etape("4. Identification du cas de section (équilibre de la section)")
    print(f"   Axe neutre à l'ELU : x = {r.x/10:.2f} cm  (D = {D:.0f} cm)")
    print("   " + CAS[r.cas].split(" : ")[1].capitalize())
    if N > 0:
        print(f"   Béton seul : M_Rd,c = {r.M_Rd_beton:.2f} kN.m")

    etape("5. Armatures à l'ELU (section totale répartie sur les barres)")
    a = r.armatures
    print(f"   As = {a.As1:.1f} mm²      As,min = {a.As_min:.1f} mm²      As,max = {a.As_max:.0f} mm²")
    for note in r.notes:
        print(f"   · {note}")

    etape("6. Choix des armatures")
    while True:
        n_ch, phi_ch = lire_armature("As (total)", a.As1, "mm²")
        if n_ch >= 6:
            break
        print("   -> au moins 6 barres pour une section circulaire.")
    As_ch = section_barres(n_ch, phi_ch)
    p_ch = remplacer(p, nombre_barres=n_ch)
    if As_ch > a.As_max:
        print(f"   ATTENTION : {As_ch:.0f} mm² > As,max = {a.As_max:.0f} mm².")

    etape("7. Vérification de la résistance avec les barres choisies")
    x, MRd, ok = p_ch.verifier_resistance(s, As_ch, r)
    M_star = e.moment_calcul if e is not None else abs(M)
    print(f"   {format_choix(n_ch, phi_ch)} = {As_ch:.0f} mm² : x = {x/10:.2f} cm pour N_Rd = N_Ed")
    print(f"   M_Rd = {MRd:.2f} kN.m >= M*Ed = {M_star:.2f} kN.m  -> {verdict(ok)}")

    etape("8. Vérification à l'ELS (barres choisies)")
    v = p_ch.verifier_els(Sollicitation(N=Ns, M=Ms), As_ch)
    print("   " + ("Section homogène (N_ser > 0)" if Ns > 0 else "Section fissurée (N_ser < 0, béton tendu négligé)"))
    print(f"   σc = {v.sigma_beton:.2f} MPa <= {v.sigma_beton_limite:.2f} MPa  -> {verdict(v.beton_verifie)}")
    print(f"   σs = {v.sigma_acier:.2f} MPa <= {v.sigma_acier_limite:.2f} MPa  -> {verdict(v.acier_verifie)}")


# ----------------------------------------------------------------------
def main() -> None:
    menus = {"1": poteau, "2": voute, "3": mur, "4": poteau_circulaire}
    while True:
        titre("flexcomp — Calcul des éléments en flexion composée (EC2)")
        print("   1. Poteau rectangulaire\n   2. Voûte à trois articulations\n"
              "   3. Mur porteur (voile)\n   4. Poteau circulaire\n   0. Quitter")
        choix = input("   Votre choix : ").strip()
        if choix == "0":
            print("Au revoir.")
            return
        if choix not in menus:
            print("   -> choix invalide.")
            continue
        try:
            menus[choix]()
        except Exception as erreur:          # données incohérentes : on reste dans le menu
            print(f"\n   ERREUR : {erreur}")
        input("\n   Appuyez sur Entrée pour revenir au menu...")


if __name__ == "__main__":
    main()
