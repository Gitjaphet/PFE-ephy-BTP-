# flexcomp — Calcul des éléments en flexion composée selon l'Eurocode 2

Logiciel de dimensionnement et de vérification des éléments en béton armé soumis à la **flexion composée** (effort normal N + moment fléchissant M), conforme à l'**Eurocode 2 (NF EN 1992-1-1)**.

Développé dans le cadre du **Projet de Fin d'Année (PFA – S8)**, Master I Génie Civil, parcours BAT 4, École Supérieure Polytechnique d'Antsiranana (Université d'Antsiranana), Promotion Mahery, année universitaire 2025-2026.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Éléments calculés](#éléments-calculés)
- [Captures du déroulement](#déroulement-dun-calcul)
- [Installation](#installation)
- [Lancement](#lancement)
- [Structure du projet](#structure-du-projet)
- [Méthodes de calcul](#méthodes-de-calcul)
- [Validation](#validation)
- [Références](#références)
- [Auteurs](#auteurs)

---

## Fonctionnalités

- **Quatre éléments de structure** : poteau rectangulaire, poteau circulaire, voûte à trois articulations, voile.
- **Interface graphique** en trois étapes : choix de l'élément → données d'entrée → résultats.
- **Version console** : le même calcul, étape par étape, dans le terminal (`python run_console.py`).
- **Calcul ELU** complet, avec identification automatique du cas de section (partiellement comprimée, entièrement tendue, entièrement comprimée).
- **Effets du second ordre** (méthode de la courbure nominale) et imperfections géométriques.
- **Choix des armatures par l'utilisateur**, saisi au format `4HA12`, avec la section réelle affichée en direct et le contrôle As,min / As,max.
- **Vérification à l'ELS** calculée à partir des barres réellement choisies : contrainte du béton σc et contrainte de l'acier σs.
- **Conditions aux appuis** : six cas, dont les portiques intégrés ou non au contreventement (coefficients k₁, k₂).
- **Figures techniques** de style plan (type AutoCAD) : coupes, élévations, diagramme des moments. Elles sont mises à jour en direct selon les barres choisies et exportables en **PNG** ou **PDF**.
- **Planche de ferraillage A4** du poteau, avec :
  - nomenclature des armatures ;
  - élévation cotée avec la répartition des cadres ;
  - coupe A-A ;
  - cartouche avec logos.

---

## Éléments calculés

### Poteau rectangulaire

| Étape | Contenu |
|---|---|
| Élancement | l₀ selon les conditions aux appuis, λ = l₀/i, λlim = 20·A·B·C/√n |
| Second ordre | Courbure nominale : e₂ = (1/r)·l₀²/π² ; e_tot = e₁ + eᵢ + e₂ |
| Cas 1 | Section partiellement comprimée : assimilation à la flexion simple (simple ou double armature) |
| Cas 2 | Section entièrement tendue : équilibre des moments par rapport à chaque nappe |
| Cas 3 | Section entièrement comprimée : bilan des forces au pivot C |
| ELS | Section homogénéisée : σc ≤ 0,6·fck et σs ≤ 0,8·fyk |
| Cadres | EC2 §9.5.3 : Φt, espacement courant et espacement réduit aux extrémités |

### Poteau circulaire

| Étape | Contenu |
|---|---|
| Section | d' = c + Φ/2 ; rₛ = D/2 − d' (cercle des armatures) ; A_c = π·D²/4 ; i = D/4 |
| Élancement | l₀ selon les conditions aux appuis, λ = l₀/i, λlim = 20·A·B·C/√n |
| Second ordre | Courbure nominale avec d = D/2 + rₛ/√2 (EC2 §5.8.8.3) ; e_tot = e₁ + eᵢ + e₂ |
| Équilibre de la section | Béton : segment circulaire de profondeur 0,8·x ; n barres réparties (n ≥ 6), y_k = rₛ·cos(2πk/n) ; pivot B ou C |
| Armatures | x tel que N_Rd = N_Ed, puis A_s total tel que M_Rd ≥ M*_Ed |
| Vérification | Résistance recalculée avec les barres choisies : M_Rd ≥ M*_Ed |
| ELS | Section homogénéisée (N_ser > 0) ou fissurée (N_ser < 0) : σc et σs |

### Voûte à trois articulations

- Poussée horizontale H = p·l²/(8f) et rayon de l'arc (Mesnager).
- Moment le long de l'arc M(x) = H·[y_f(x) − y_arc(x)], nul aux trois rotules.
- Recherche de la section critique, excentricités additionnelles.
- Vérification du béton non armé (EC2 §12.6).
- Armatures en flexion composée à la section critique, par bande de calcul.
- ELS à la section critique.

### Voile

- Les trois vérifications du béton non armé (EC2 §12.6) : forces axiales, effort tranchant, flambement, avec λ ≤ 86.
- Conclusion : voile calculable comme non armé, ou à armer.
- Flexion composée dans le plan : aciers d'about (chaînages verticaux).

---

## Déroulement d'un calcul

1. **Choix de l'élément** sur l'écran d'accueil.
2. **Données d'entrée** : géométrie, élancement, matériaux, sollicitations ELU et ELS, conditions aux appuis.
3. **Résultats** :
   - excentricités, second ordre, cas de section ;
   - armatures calculées à l'ELU ;
   - **choix des armatures** (par exemple `4HA12` et `4HA8`) ;
   - **Vérifier à l'ELS** : σc et σs ;
   - **Exporter la planche de ferraillage** (poteau) ;
   - figures exportables en PNG ou PDF.

---

## Installation

Prérequis : **Python 3.11 ou plus récent** et **PyQt6**.

```bash
git clone https://github.com/Gitjaphet/PFE-ephy-BTP-.git
cd PFE-ephy-BTP-
python -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install PyQt6
pip install -e .
```

---

## Lancement

```bash
python run_gui.py
```

L'application peut aussi être lancée comme module :

```bash
python -m flexcomp.gui
```

Version console (demandée pour la présentation) :

```bash
python run_console.py
```

---

## Structure du projet

```
flexcomp_project/
├── run_gui.py                  # Point d'entrée de l'interface graphique
├── run_console.py              # Point d'entrée de la version console
├── pyproject.toml
├── examples/                   # Exemples de calcul
├── tests/                      # Tests
└── flexcomp/
    ├── core/                   # Noyau de calcul (indépendant de l'interface)
    │   ├── materials.py        # Béton, acier
    │   ├── elancement.py       # Longueur de flambement, élancement, portiques
    │   ├── flexion_simple.py   # Flexion simple (moment réduit, armatures)
    │   ├── armatures_reglementaires.py   # As,min, As,max
    │   ├── barres.py           # Table des aciers HA, lecture « 4HA12 »
    │   ├── cadres.py           # Cadres EC2 §9.5.3, longueurs des barres
    │   └── exceptions.py
    ├── sections/
    │   └── rectangular.py      # Section rectangulaire (d, d', aire)
    ├── elements/
    │   ├── poteau.py           # Poteau rectangulaire : 3 cas de flexion composée + ELS
    │   ├── poteau_circulaire.py  # Poteau circulaire : équilibre de la section + ELS
    │   ├── voute.py            # Voûte à trois articulations (Mesnager) + ELS
    │   └── mur_porteur.py      # Voile : EC2 §12.6 + flexion composée dans le plan
    ├── results/
    │   └── dataclasses.py      # Structures de résultats
    ├── reporting/
    │   └── console.py          # Sortie texte
    └── gui/                    # Interface PyQt6
        ├── app.py, main_window.py, theme.py, adaptateur.py
        ├── pages/              # Accueil, saisie, résultats
        ├── widgets/            # Composants réutilisables, panneau de figures
        ├── dessins/            # Figures techniques + planche de ferraillage
        └── assets/             # Pictogrammes et logos du cartouche
```

Le **noyau de calcul** (`core`, `sections`, `elements`, `results`) ne dépend pas de l'interface. Il peut être utilisé seul, depuis un script Python :

```python
from flexcomp.gui.adaptateur import calculer_poteau

sortie = calculer_poteau(dict(
    b=30, h=40, enrobage=3, diametre=20, longueur=3.5,
    fck=25, fyk=500, N_elu=800, M_elu=120, N_els=580, M_els=85,
))
print(sortie["resultat"].armatures)
```

---

## Méthodes de calcul

| Grandeur | Formule | Référence |
|---|---|---|
| Résistances de calcul | fcd = fck/1,5 ; fyd = fyk/1,15 | EC2 §3.1.6, §3.2.7 |
| Imperfections | eᵢ = l₀/400 | EC2 §5.2(7) |
| Excentricité minimale | e₀ = max(20 mm ; h/30) | EC2 §6.1(4) |
| Élancement limite | λlim = 20·A·B·C/√n | EC2 §5.8.3.1 |
| Courbure nominale | 1/r = Kr·Kφ·εyd/(0,45·d) | EC2 §5.8.8.3 |
| Longueur de flambement (portiques) | formules en k₁, k₂ | EC2 §5.8.3.2 |
| Armatures minimales du poteau | As,min = max(0,10·NEd/fyd ; 0,002·Ac) | EC2 §9.5.2 |
| Armatures maximales du poteau | As,max = 0,04·Ac | EC2 §9.5.2 |
| Cadres | Φt ≥ max(6 ; Φl/4) ; s ≤ min(20·Φl,min ; b ; 400 mm) ; 0,6·s aux extrémités | EC2 §9.5.3 |
| Béton non armé | NRd1, fcvd, NRd,12, Φ | EC2 §12.6 |
| Voûte | H = p·l²/(8f) ; M(x) = H·[y_f − y_arc] | Mesnager |

---

## Validation

Les résultats sont comparés au calcul manuel de la Partie 2 du rapport. Pour le poteau 30 × 40 cm, cas 1 (NEd = 800 kN, MEd = 120 kN·m) :

| Grandeur | Calcul manuel | flexcomp |
|---|---|---|
| e_tot | 16,58 cm | 16,58 cm |
| M*Ed | 132,64 kN·m | 132,64 kN·m |
| μEd,A | 0,402 | 0,402 |
| As1 / As2 | 345,1 / 142,0 mm² | 345,1 / 142,0 mm² |
| σc (4HA12 + 4HA8) | 14,81 MPa | 14,81 MPa |

Poteau circulaire D = 45 cm, mêmes sollicitations (NEd = 800 kN, MEd = 120 kN·m) :

| Grandeur | Valeur |
|---|---|
| M*Ed | 132,75 kN·m |
| A_s total calculé | 502,3 mm² |
| Barres choisies | 8HA10 → M_Rd = 138,93 kN·m ≥ 132,75 |
| ELS (Nser = 580 kN, Mser = 85 kN·m) | σc = 12,79 MPa ; σs = 74,33 MPa |

---

## Références

1. NGUYEN Quang Huy, *Béton Armé III — Calcul des voiles en béton selon l'EC2*, chapitre 16, INSA Rennes.
2. NGUYEN Quang Huy, *Cours de Béton Armé — Chapitre 11 : Flexion composée*, INSA Rennes.
3. AFNOR, *NF EN 1992-1-1 — Eurocode 2 : Calcul des structures en béton*, 2005 (Annexe nationale 2007).
4. ROUX Jean, *Pratique de l'Eurocode 2 — Guide d'application*, Eyrolles / AFNOR Éditions, 2009.
5. MESNAGER Augustin, *Cours de béton armé*, École nationale des ponts et chaussées, 1921.

---

## Auteurs

- **Étudiante** : JEPHY Marinho
- **Développement du code** : Japhet
- **Encadreurs** :
  - Mr RAZAFINDRAMARO Borgeot Augustin
  - Mr RANDRIAMARSON Julas Fridolès

École Supérieure Polytechnique d'Antsiranana — Mention Génie Civil, parcours BAT 4 — Promotion Mahery, 2025-2026.
