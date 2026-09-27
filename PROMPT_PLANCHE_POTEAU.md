# PROMPT — Planche de calcul « Poteau rectangulaire » (mise en page façon AutoCAD)

> À copier-coller tel quel dans une session Claude Code (ou toute IA de code)
> ayant accès au dépôt `flexcomp_project/`. Le prompt référence directement
> les classes déjà codées (`ResultatPoteau`, `ArmaturesSection`, `CasSection`,
> `SectionRectangulaire`) pour être exécutable sans réinterprétation.

---

## Contexte

Le package `flexcomp` calcule déjà un poteau rectangulaire en flexion
composée et retourne un objet `ResultatPoteau` (voir
`flexcomp/results/dataclasses.py`) contenant : la sollicitation ELU, les
effets du second ordre, le cas de section identifié (`CasSection`), le
moment réduit, les armatures (`ArmaturesSection`) et des notes.

## Objectif

Créer une fonction `generer_planche_poteau(poteau: PoteauRectangulaire, resultat: ResultatPoteau, armatures_choisies: list[ChoixBarre]) -> matplotlib.figure.Figure`
dans un nouveau module `flexcomp/reporting/planche_poteau.py`, qui produit
**une planche A3 paysage** reproduisant l'esprit des figures du rapport PFA
(élévation + coupe transversale), mais **remplie avec les valeurs numériques
réelles du calcul**, pas un organigramme générique. Pas de diagramme
d'interaction M-N sur cette planche (il fait l'objet d'une planche séparée).

## Mise en page générale

Grille 2 colonnes sur toute la hauteur de la page :

```
┌─────────────────────────┬──────────────────────────────────┐
│                          │  SCHÉMA DE CALCUL (haut)          │
│   COLONNE GAUCHE          │  élévation + coupe transversale,  │
│   données + calcul        │  cotée, style trait technique     │
│   (texte/tableaux)        │  noir sur fond blanc               │
│   largeur ≈ 38%           ├──────────────────────────────────┤
│                          │  FERRAILLAGE + TABLEAU (bas droite)│
│                          │  coupe avec barres réelles          │
│                          │  + tableau de choix des barres      │
└─────────────────────────┴──────────────────────────────────┘
```

- Utiliser `matplotlib.gridspec.GridSpec` : 1 ligne × 2 colonnes principales
  (largeurs relatives `[0.38, 0.62]`), puis dans la colonne droite un
  `GridSpecFromSubplotSpec` de 2 lignes (`[0.55, 0.45]`) pour schéma /
  ferraillage+tableau.
- Format de sortie : PDF vectoriel ET PNG haute résolution (300 dpi),
  export via `fig.savefig(...)`.
- Cartouche en en-tête de page (nom du projet, élément, date, auteur) —
  reprendre le style des en-têtes « Nom : JEPHY / Filière : Génie Civil »
  du rapport PFA.

## Colonne gauche — contenu, dans cet ordre

Chaque bloc est un petit tableau ou une liste `clé : valeur`, police
monospace 8-9 pt, aligné à gauche. Tirer toutes les valeurs des objets
Python — ne rien recalculer dans le module de rendu.

1. **Données d'entrée**
   `b, h` (`poteau.section.b/.h`), `c` = enrobage nominal, `Φ` = diamètre
   barre, `l0` (`poteau.l0`), `fck`, `fyk`, et les grandeurs dérivées
   `d, d'` (`poteau.section.d/.d_prime`), `fcd`, `fyd`.

2. **Excentricités**
   `e1` (`effets.excentricite_1er_ordre`), `ei`
   (`.excentricite_imperfection`), `e2` (`.excentricite_2nd_ordre`, afficher
   "—" si `second_ordre_necessaire` est `False`), `e_tot`
   (`.excentricite_totale`).

3. **Élancement et second ordre**
   `λ` (`.lambda_calcule`), `λ_lim` (`.lambda_limite`), verdict "second
   ordre pris en compte : OUI/NON".

4. **Moment réduit et cas de section**
   `M*_Ed` (`.moment_calcul`), `M_Ed,A`, `μ_Ed,A` (`resultat.moment_reduit`,
   "—" si cas 2), **encadré avec fond gris clair** annonçant le cas
   retenu : "CAS 1 — Section partiellement comprimée" (ou 2, ou 3), à
   partir de `resultat.cas` (`CasSection`).

5. **Bloc conditionnel — un seul des trois est affiché**, sélectionné sur
   `resultat.cas` :
   - **Si `PARTIELLEMENT_COMPRIMEE`** : `μ_lu`, armature double oui/non
     (lire dans `resultat.notes`), `α_u`, `z_c`, puis `As1`/`As2` avant et
     après correction flexion composée.
   - **Si `ENTIEREMENT_TENDUE`** : `e_A1`, `e_A2`, puis `As1`/`As2` bruts
     et après application du minimum réglementaire.
   - **Si `ENTIEREMENT_COMPRIMEE`** : `σs` (contrainte pivot C), bilan des
     forces (`N_Ed = Ac.fcd + (σs-fcd).Asc,tot`), `A` obtenu, note si le
     bilan est négatif (minimum gouverne).

   → Concrètement : une fonction `_bloc_cas(ax, resultat)` avec un
   `if/elif/elif` sur `resultat.cas`, qui n'écrit QUE le bloc pertinent
   (ne pas laisser de blocs vides ou grisés des deux autres cas).

6. **Vérification armatures min/max**
   `As,min`, `As,max` (`resultat.armatures.As_min/.As_max`), comparaison
   avec `As1`/`As2` retenus, verdict OK/KO par une pastille colorée
   (vert `#1D9E75` / rouge `#E24B4A`, cohérent avec le reste du document).

7. **Choix des barres (tableau à saisir)**
   Tableau 2 lignes (nappe 1 / nappe 2) × colonnes
   [As requis (mm²) | choix (n × HA∅) | As fourni (mm²) | écart (%)].
   Les valeurs de la colonne "choix" viennent du paramètre
   `armatures_choisies` (liste de `ChoixBarre(nombre: int, diametre: int)`
   à définir) — **ne pas générer ce choix automatiquement dans cette
   fonction**, il est fourni par l'appelant (l'utilisateur, ou une future
   fonction `choisir_barres_standard()` séparée).

8. **Vérification à l'ELS**
   `σc`, `σc,lim`, verdict OK/KO (si `resultat.verification_els` est
   renseigné ; sinon, indiquer "non demandée").

## Colonne droite, en haut — schéma de calcul (style AutoCAD)

Dessiner en `matplotlib.patches` (pas d'image importée) :

- **Élévation** (à gauche du sous-panneau) : rectangle vertical de hauteur
  proportionnelle à `poteau.l0`, hachures diagonales fines en pied
  (encastrement) et symbole de rotule (petit cercle) en tête si
  `condition_appui == ENCASTREMENT_ROTULE`. Flèche verticale rouge en tête
  annotée `N_Ed = {N} kN`, flèche horizontale bleue annotée
  `M_Ed = {M} kN.m`. Coter `l0` sur le côté avec une ligne de cote fléchée
  (style `matplotlib.patches.FancyArrowPatch` double flèche + texte).
- **Coupe transversale** (à droite du sous-panneau) : rectangle `b × h`,
  4 pastilles pour les positions de nappes (2 en haut à `d'`, 2 en bas à
  `d`, ou l'inverse selon le cas — reprendre la convention des figures du
  rapport : nappe tendue en bas si `N > 0`). Coter `b`, `h`, `d`, `d'` avec
  des lignes de cote fines et flèches, dans le style trait-fin noir sur
  fond blanc des figures du rapport PFA (pas de remplissage coloré, juste
  des hachures croisées légères pour le béton).
- Trait `linewidth=0.6`, couleur `#2C2C2A` (gris CDS foncé), police des
  cotes 7 pt.

## Colonne droite, en bas — ferraillage + tableau (SANS diagramme)

- **Dessin de ferraillage** (sous-panneau gauche) : reprendre la coupe
  transversale, mais avec les **barres réellement choisies** (cercles à
  l'échelle du diamètre réel, nombre exact par nappe tiré de
  `armatures_choisies`), plus un cadre (étrier) en trait fin autour, et les
  aciers de peau si applicable. Coter l'enrobage `c`.
- **Tableau de choix des barres** (sous-panneau droit, à côté du dessin) :
  tableau `matplotlib.table` reprenant EXACTEMENT les mêmes lignes que le
  tableau du bloc 7 de la colonne gauche (nappe, As requis, choix, As
  fourni, écart, OK/KO) — c'est la version « propre », en grand, destinée à
  être lue depuis le dessin de ferraillage juste à côté. Ne pas ajouter de
  diagramme d'interaction M-N ici (il appartient à une planche séparée).

## Style graphique commun

- Fond blanc, traits noirs/gris foncé, aucune couleur vive sauf :
  rouge pour les efforts normaux (`N`), bleu pour les moments (`M`),
  vert/rouge uniquement pour les pastilles de vérification OK/KO.
- Police technique (`monospace` ou `DejaVu Sans Mono`) pour toutes les
  valeurs numériques ; `sans-serif` pour les titres de bloc.
- Cadre fin (`linewidth=0.5`) autour de chaque bloc de la colonne gauche et
  de chaque sous-panneau de la colonne droite, pour un rendu "planche
  technique" plutôt que "rapport bureautique".

## Livrable attendu du prompt

1. `flexcomp/reporting/planche_poteau.py` avec `generer_planche_poteau(...)`.
2. Une dataclass `ChoixBarre(nombre: int, diametre_mm: int)` avec une
   propriété `aire_mm2`.
3. Un exemple `examples/generer_planche_poteau_exemple.py` qui instancie le
   Cas 1 du rapport PFA (`N=800kN, M=120kN.m`), choisit `4HA12` / `4HA8`
   comme dans le rapport, et exporte `planche_poteau_cas1.pdf`.
4. Un test visuel simple (`tests/test_planche_poteau.py`) qui vérifie
   seulement que la figure se génère sans exception et contient le bon
   nombre d'`Axes` (pas de comparaison pixel par pixel).
