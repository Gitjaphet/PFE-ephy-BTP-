"""Valide le moteur de calcul flexcomp contre les valeurs numériques du
rapport PFA (Partie 2 — Exemple de calcul), pour les 3 éléments.

Ce script n'est pas une suite de tests formelle (voir tests/ pour cela) : il
sert de démonstration exécutable et de première preuve de correction, en
affichant côte à côte les valeurs obtenues et les valeurs de référence.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flexcomp.core import Acier, Beton, ConditionAppui
from flexcomp.elements import MurPorteur, PoteauRectangulaire, VouteTroisArticulations
from flexcomp.reporting import rapport_mur_porteur, rapport_poteau, rapport_voute
from flexcomp.results import Sollicitation
from flexcomp.sections import SectionRectangulaire


def ecart(valeur: float, reference: float) -> str:
    if reference == 0:
        return "n/a"
    return f"{100 * (valeur - reference) / reference:+.1f}%"


print("\n" + "#" * 70)
print("# 1. POTEAU RECTANGULAIRE (rapport PFA, Partie 2, Chapitre 1)")
print("#" * 70)

beton = Beton(fck=25.0)
acier = Acier(fyk=500.0)
section = SectionRectangulaire(b=0.30, h=0.40, enrobage_nominal=0.03, diametre_barre=0.020)
poteau = PoteauRectangulaire(
    section=section, longueur_libre=3.5,
    condition_appui=ConditionAppui.ENCASTREMENT_ROTULE,
    beton=beton, acier=acier,
)

print(f"\nd = {section.d*1000:.1f} mm (réf. 360 mm)   d' = {section.d_prime*1000:.1f} mm (réf. 40 mm)")
print(f"l0 = {poteau.l0:.3f} m (réf. 2,45 m)")

# --- Cas 1 : section partiellement comprimée ---
sollicitation_1 = Sollicitation(N=800.0, M=120.0)
resultat_1 = poteau.dimensionner(sollicitation_1)
rapport_poteau(resultat_1)
print(f"  >> Référence rapport : As1=345,1 mm² (écart {ecart(resultat_1.armatures.As1, 345.1)}), "
      f"As2=142,0 mm² (écart {ecart(resultat_1.armatures.As2, 142.0)})")

# --- Cas 2 : section entièrement tendue ---
sollicitation_2 = Sollicitation(N=-350.0, M=40.0)
resultat_2 = poteau.dimensionner(sollicitation_2)
rapport_poteau(resultat_2)
print(f"  >> Référence rapport : As1=115 mm² avant min (écart {ecart(resultat_2.armatures.As1, 144.0)} vs min 144), "
      f"As2=690 mm² (écart {ecart(resultat_2.armatures.As2, 690.0)})")

# --- Cas 3 : section entièrement comprimée ---
sollicitation_3 = Sollicitation(N=1800.0, M=60.0)
resultat_3 = poteau.dimensionner(sollicitation_3)
rapport_poteau(resultat_3)
print(f"  >> Référence rapport : As1=As2=207 mm² par nappe (bilan négatif -> minimum, "
      f"ici As={resultat_3.armatures.As1:.1f} mm²)")


print("\n" + "#" * 70)
print("# 2. VOÛTE À TROIS ARTICULATIONS (rapport PFA, Partie 2, Chapitre 2)")
print("#" * 70)

voute = VouteTroisArticulations(
    portee=12.0, fleche=1.2, charge_uniforme=45.0, epaisseur=0.30,
    beton=beton, acier=Acier(fyk=500.0), largeur_calcul=1.0,
    enrobage_nominal=0.03, diametre_barre=0.012,
)
print(f"\nH = {voute.poussee_horizontale:.1f} kN/m (réf. 675 kN/m)")
print(f"R = {voute.rayon_arc:.2f} m (réf. 15,60 m)")

sc = voute.section_critique()
print(f"Section critique : x* = {sc.x:.2f} m (réf. 1,72 m), "
      f"M(x*) = {sc.moment:.2f} kN.m (réf. -8,10 kN.m), "
      f"N = {sc.effort_normal:.2f} kN (réf. 596,46 kN)")

resultat_voute = voute.dimensionner()
rapport_voute(resultat_voute)


print("\n" + "#" * 70)
print("# 3. MUR PORTEUR (rapport PFA, Partie 2, Chapitre 3)")
print("#" * 70)

mur = MurPorteur(
    hauteur_libre=4.0, longueur_calcul=2.5, epaisseur=0.30, beta=1.0,
    beton=Beton(fck=40.0), acier=Acier(fyk=500.0), enrobage_nominal=0.03,
)
print(f"\nl0 = {mur.l0:.2f} m (réf. 4 m)   lambda = {mur.elancement:.1f} (réf. 46,2)")

resultat_mur = mur.verifier_non_arme(N_Ed=712.5, V_Ed=171.0, e=0.0)
rapport_mur_porteur(resultat_mur)
print(f"  >> Référence rapport : N_Rd1=16000 kN, f_cvd=1,72 MPa, N_Rd12=11541,33 kN")

print("\nValidation terminée.\n")
