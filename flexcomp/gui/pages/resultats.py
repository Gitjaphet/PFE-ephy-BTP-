"""Page de résultats.

L'affichage s'adapte à ce qui a été calculé : pour un poteau, seul le bloc
du cas réellement identifié (partiellement comprimée / entièrement tendue /
entièrement comprimée) est présenté — comme dans l'organigramme du rapport,
on ne montre pas les branches non empruntées.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from dataclasses import replace

from flexcomp.core.barres import (
    DIAMETRES_HA, NOMBRES_BARRES, format_choix, lire_choix, section_barres,
)
from flexcomp.results import CasSection
from flexcomp.gui.dessins.voute import CoupeSectionVoute
from flexcomp.gui.dessins.poteau_circulaire import CoupePoteauCirculaire
from flexcomp.gui.dessins import (
    CoupeHorizontaleMur,
    CoupeTransversalePoteau,
    DiagrammeMomentVoute,
    ElevationMur,
    ElevationPoteau,
    GeometrieVoute,
)
from flexcomp.gui.theme import METRIQUES, PALETTE, POLICE_MONO
from flexcomp.gui.widgets.composants import (
    BadgeVerdict,
    LigneResultat,
    carte,
    separateur,
    titre_section,
)
from flexcomp.gui.widgets.panneau_figures import PanneauFigures

_LIBELLE_CAS = {
    CasSection.PARTIELLEMENT_COMPRIMEE: ("Cas 1", "Section partiellement comprimée"),
    CasSection.ENTIEREMENT_TENDUE: ("Cas 2", "Section entièrement tendue"),
    CasSection.ENTIEREMENT_COMPRIMEE: ("Cas 3", "Section entièrement comprimée"),
}


def _nombre(valeur: float, decimales: int = 2, unite: str = "") -> str:
    """Formate un nombre, en gérant proprement les valeurs non définies."""
    if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)):
        return "—"
    texte = f"{valeur:,.{decimales}f}".replace(",", " ")
    return f"{texte} {unite}".strip()


class PageResultats(QWidget):
    """Présente le résultat d'un calcul et propose les actions suivantes."""

    retour_demande = pyqtSignal()
    nouveau_calcul_demande = pyqtSignal()

    def __init__(
        self,
        identifiant_element: str,
        sortie: dict[str, Any],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.identifiant = identifiant_element
        self.sortie = sortie
        self._construire()

    def _construire(self) -> None:
        exterieur = QVBoxLayout(self)
        exterieur.setContentsMargins(
            METRIQUES.pad_xl, METRIQUES.pad_lg, METRIQUES.pad_xl, METRIQUES.pad_lg
        )
        exterieur.setSpacing(METRIQUES.pad_md)

        exterieur.addLayout(self._en_tete())
        exterieur.addWidget(separateur())

        # Deux colonnes : les valeurs à gauche, les figures à droite.
        # Le QSplitter laisse l'utilisateur arbitrer entre lire les chiffres
        # et regarder le schéma, selon ce qu'il est en train de vérifier.
        separation = QSplitter(Qt.Orientation.Horizontal)
        separation.setChildrenCollapsible(False)
        separation.setHandleWidth(METRIQUES.pad_md)

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        contenu = QWidget()
        self._corps = QVBoxLayout(contenu)
        self._corps.setContentsMargins(0, METRIQUES.pad_md, METRIQUES.pad_sm, METRIQUES.pad_md)
        self._corps.setSpacing(METRIQUES.pad_md)

        constructeurs = {
            "poteau": self._corps_poteau,
            "poteau_circ": self._corps_poteau_circ,
            "voute": self._corps_voute,
            "mur": self._corps_mur,
        }
        constructeurs[self.identifiant]()
        self._corps.addStretch()

        defilement.setWidget(contenu)
        separation.addWidget(defilement)

        panneau = self._construire_figures()
        if panneau is not None:
            separation.addWidget(panneau)
            separation.setStretchFactor(0, 1)
            separation.setStretchFactor(1, 1)
            separation.setSizes([1000, 1000])  # moitié / moitié dès l'ouverture

        exterieur.addWidget(separation, stretch=1)

        exterieur.addWidget(separateur())
        exterieur.addLayout(self._barre_actions())

    def _construire_figures(self) -> QWidget | None:
        """Compose les figures propres à l'élément calculé."""
        modele = self.sortie.get("modele")
        resultat = self.sortie["resultat"]
        if modele is None:
            return None

        if self.identifiant == "poteau":
            figures = [
                ("Coupe transversale", CoupeTransversalePoteau(modele, resultat)),
                ("Élévation", ElevationPoteau(modele, resultat)),
            ]
        elif self.identifiant == "poteau_circ":
            figures = [("Coupe transversale", CoupePoteauCirculaire(modele, resultat))]
        elif self.identifiant == "voute":
            figures = [
                ("Géométrie", GeometrieVoute(modele, resultat)),
                ("Moment M(x)", DiagrammeMomentVoute(modele, resultat)),
                ("Coupe A–A", CoupeSectionVoute(modele, resultat)),
            ]
        else:
            figures = [
                ("Élévation", ElevationMur(modele, resultat)),
                ("Coupe horizontale", CoupeHorizontaleMur(modele, resultat)),
            ]
        self._figures_choix = [fig for _, fig in figures if hasattr(fig, 'definir_choix')]
        self._synchroniser_coupe()
        return PanneauFigures(figures)

    def _en_tete(self) -> QVBoxLayout:
        colonne = QVBoxLayout()
        colonne.setSpacing(METRIQUES.pad_xs)
        titre = QLabel("Résultats du calcul")
        titre.setObjectName("TitrePage")
        colonne.addWidget(titre)
        return colonne

    def _bandeau_cas(self, code: str, libelle: str) -> QWidget:
        """Bandeau accentué annonçant le cas de section identifié."""
        cadre = QWidget()
        disposition = QHBoxLayout(cadre)
        disposition.setContentsMargins(
            METRIQUES.pad_md, METRIQUES.pad_sm, METRIQUES.pad_md, METRIQUES.pad_sm
        )
        cadre.setStyleSheet(
            f"background-color: {PALETTE.accent_clair}; "
            f"border-left: 3px solid {PALETTE.accent}; border-radius: 0px;"
        )
        label_code = QLabel(code)
        label_code.setStyleSheet(
            f"color: {PALETTE.accent}; font-weight: 600; font-size: 12pt; "
            "background: transparent;"
        )
        disposition.addWidget(label_code)
        label_libelle = QLabel(libelle)
        label_libelle.setStyleSheet(
            f"color: {PALETTE.texte}; font-size: 12pt; font-weight: 600; "
            "background: transparent;"
        )
        disposition.addWidget(label_libelle)
        disposition.addStretch()
        return cadre

    # ------------------------------------------------------------------
    # Poteau
    # ------------------------------------------------------------------
    def _corps_poteau(self) -> None:
        resultat = self.sortie["resultat"]
        effets = resultat.effets_2nd_ordre
        armatures = resultat.armatures

        cadre, disposition = carte()
        disposition.addWidget(titre_section("Excentricités et second ordre"))
        disposition.addWidget(
            LigneResultat("Excentricité 1er ordre e₁", _nombre(effets.excentricite_1er_ordre * 100, 2, "cm"))
        )
        disposition.addWidget(
            LigneResultat("Imperfections eᵢ", _nombre(effets.excentricite_imperfection * 100, 3, "cm"))
        )
        disposition.addWidget(
            LigneResultat("Second ordre e₂", _nombre(effets.excentricite_2nd_ordre * 100, 3, "cm"))
        )
        disposition.addWidget(
            LigneResultat("Excentricité totale e_tot", _nombre(effets.excentricite_totale * 100, 2, "cm"), en_evidence=True)
        )
        disposition.addWidget(
            LigneResultat(
                "Élancement λ / λ_lim",
                f"{_nombre(effets.lambda_calcule, 2)} / {_nombre(effets.lambda_limite, 2)}",
                BadgeVerdict(
                    "2nd ordre pris en compte" if effets.second_ordre_necessaire else "2nd ordre négligeable",
                    "alerte" if effets.second_ordre_necessaire else "succes",
                ),
            )
        )
        disposition.addWidget(
            LigneResultat("Moment de calcul M*_Ed", _nombre(effets.moment_calcul, 2, "kN·m"), en_evidence=True)
        )
        self._corps.addWidget(cadre)

        code, libelle = _LIBELLE_CAS[resultat.cas]
        self._corps.addWidget(self._bandeau_cas(code, libelle))

        cadre_cas, disposition_cas = carte()
        disposition_cas.addWidget(titre_section("Armatures à l'ELU"))
        if resultat.moment_reduit is not None:
            disposition_cas.addWidget(
                LigneResultat("Moment réduit μ_Ed,A", _nombre(resultat.moment_reduit, 3))
            )
        verdict_1 = BadgeVerdict(
            "minimum gouverne" if armatures.As1 <= armatures.As_min + 0.5 else "calcul gouverne",
            "alerte" if armatures.As1 <= armatures.As_min + 0.5 else "succes",
        )
        disposition_cas.addWidget(
            LigneResultat("Nappe As1", _nombre(armatures.As1, 1, "mm²"), verdict_1, en_evidence=True)
        )
        disposition_cas.addWidget(
            LigneResultat("Nappe As2", _nombre(armatures.As2, 1, "mm²"), en_evidence=True)
        )
        disposition_cas.addWidget(
            LigneResultat("As,min réglementaire", _nombre(armatures.As_min, 1, "mm²"))
        )
        if armatures.As_max is not None:
            disposition_cas.addWidget(
                LigneResultat("As,max réglementaire", _nombre(armatures.As_max, 0, "mm²"))
            )
        if armatures.commentaire:
            note = QLabel(armatures.commentaire)
            note.setObjectName("Legende")
            note.setWordWrap(True)
            disposition_cas.addWidget(note)
        self._corps.addWidget(cadre_cas)

        self._zone_els = QVBoxLayout()
        self._corps.addWidget(self._carte_choix_armatures(armatures))
        self._corps.addLayout(self._zone_els)

    # ------------------------------------------------------------------
    # Choix des armatures, puis ELS (organigramme : choix des barres -> ELS)
    # ------------------------------------------------------------------
    def _carte_choix_armatures(self, armatures, nappes=("As1", "As2"),
                               largeur: float | None = None, avec_els: bool = True) -> QWidget:
        """Choix « nHAφ » pour chaque nappe ; `largeur` (m) = bande de calcul
        pour les éléments calculés par mètre (voûte)."""
        cadre, disposition = carte()
        titre = "Choix des armatures"
        if largeur:
            titre += f" (par bande de {largeur:.2f} m)"
        disposition.addWidget(titre_section(titre))
        self._armatures_elu = armatures
        self._largeur = largeur
        self._avec_els = avec_els
        self._unite = "mm²/m" if largeur else "mm²"
        self._choix: dict[str, tuple[QLineEdit, QLabel]] = {}
        for cle in nappes:
            requis = getattr(armatures, cle) * (largeur or 1.0)
            ligne = QHBoxLayout()
            ligne.setSpacing(METRIQUES.pad_sm)
            etiquette = QLabel(f"Choix arm. {cle} =")
            etiquette.setMinimumWidth(140)
            ligne.addWidget(etiquette)
            saisie = QLineEdit(format_choix(*self._proposition(requis)))
            saisie.setPlaceholderText("ex : 12HA20")
            saisie.setMaximumWidth(130)
            ligne.addWidget(saisie)
            resume = QLabel()
            ligne.addWidget(resume)
            ligne.addStretch()
            disposition.addLayout(ligne)
            self._choix[cle] = (saisie, resume)
            saisie.textChanged.connect(self._maj_choix)

        self._bilan_choix = QLabel()
        self._bilan_choix.setWordWrap(True)
        disposition.addWidget(self._bilan_choix)

        self._bouton_els = None
        if avec_els:
            self._bouton_els = QPushButton("Vérifier à l'ELS")
            self._bouton_els.setObjectName("Principal")
            self._bouton_els.clicked.connect(self._verifier_els)
            disposition.addWidget(self._bouton_els, alignment=Qt.AlignmentFlag.AlignRight)
        self._bouton_planche = None
        if self.identifiant == "poteau":
            self._bouton_planche = QPushButton("Exporter la planche de ferraillage")
            self._bouton_planche.clicked.connect(self._exporter_planche)
            disposition.addWidget(self._bouton_planche, alignment=Qt.AlignmentFlag.AlignRight)
        self._maj_choix()
        return cadre

    def _proposition(self, requis: float) -> tuple[int, int]:
        """Proposition initiale. Poteau : 4 barres du plus petit Φ suffisant.
        Voûte / voile : plus petit Φ (>= 8 mm) demandant au plus 6 barres."""
        if self.identifiant == "poteau_circ":
            nb = self.sortie["modele"].nombre_barres
            for d in DIAMETRES_HA:
                if d >= 8 and section_barres(nb, d) >= requis:
                    return nb, d
            return nb, DIAMETRES_HA[-1]
        if self.identifiant == "poteau":
            for d in DIAMETRES_HA:
                if d >= 8 and section_barres(4, d) >= requis:
                    return 4, d
            return NOMBRES_BARRES[-1], DIAMETRES_HA[-1]
        for d in DIAMETRES_HA:
            if d >= 8:
                n = max(2, math.ceil(requis / section_barres(1, d) - 1e-9))
                if n <= 6:
                    return n, d
        return 10, DIAMETRES_HA[-1]

    def _choix_lus(self) -> dict[str, tuple[int, int] | None]:
        return {cle: lire_choix(saisie.text()) for cle, (saisie, _) in self._choix.items()}

    def _sections_choisies(self) -> dict[str, float]:
        facteur = 1.0 / self._largeur if self._largeur else 1.0
        return {cle: section_barres(*c) * facteur
                for cle, c in self._choix_lus().items() if c is not None}

    def _synchroniser_coupe(self) -> None:
        """Les figures qui montrent des barres suivent en direct le choix saisi."""
        figures = getattr(self, "_figures_choix", None)
        if not figures or not hasattr(self, "_choix"):
            return
        choix = self._choix_lus()
        valeur = choix if all(c is not None for c in choix.values()) else None
        for figure in figures:
            figure.definir_choix(valeur)

    def _maj_choix(self) -> None:
        armatures = self._armatures_elu
        choix = self._choix_lus()
        sections = self._sections_choisies()
        valide = True
        for cle, (_, resume) in self._choix.items():
            if choix[cle] is None:
                valide = False
                resume.setText("format attendu : 4HA12")
                resume.setStyleSheet(f"color: {PALETTE.danger}; font-weight: 600;")
                continue
            requis = getattr(armatures, cle)
            suffisant = sections[cle] >= requis - 0.5
            valide = valide and suffisant
            couleur = PALETTE.succes if suffisant else PALETTE.danger
            resume.setText(
                f"Ast réel = {_nombre(sections[cle], 0, self._unite)}   (requis {_nombre(requis, 1, self._unite)})"
            )
            resume.setStyleSheet(f"color: {couleur}; font-weight: 600;")

        if self.identifiant == "poteau_circ" and choix.get("As1") and choix["As1"][0] < 6:
            valide = False
            self._choix["As1"][1].setText("au moins 6 barres (section circulaire)")
            self._choix["As1"][1].setStyleSheet(f"color: {PALETTE.danger}; font-weight: 600;")
        total = sum(sections.values())
        messages = [f"Section totale choisie : {_nombre(total, 0, 'mm²')}."] if valide or sections else []
        if sections and total < armatures.As_min - 0.5:
            valide = False
            messages.append(f"Inférieure à As,min = {_nombre(armatures.As_min, 0, 'mm²')}.")
        if armatures.As_max is not None and total > armatures.As_max:
            valide = False
            messages.append(f"Supérieure à As,max = {_nombre(armatures.As_max, 0, 'mm²')}.")
        els_possible = self._avec_els and (
            self.identifiant == "voute" or self.sortie.get("sollicitation_els") is not None
        )
        if self._avec_els and not els_possible:
            messages.append("Renseignez les sollicitations ELS pour lancer la vérification.")
        self._bilan_choix.setText(" ".join(messages))
        if self._bouton_els is not None:
            self._bouton_els.setEnabled(valide and els_possible)
        if getattr(self, "_bouton_planche", None) is not None:
            self._bouton_planche.setEnabled(valide)
        self._vider_els()
        self._synchroniser_coupe()

    def _exporter_planche(self) -> None:
        """Planche de ferraillage A4 avec les barres saisies dans « Choix des armatures »."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from flexcomp.gui.dessins.planche_poteau import exporter_planche_poteau
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter la planche de ferraillage",
            "planche_ferraillage_poteau.pdf", "Fichier PDF (*.pdf)",
        )
        if not chemin:
            return
        if not chemin.lower().endswith(".pdf"):
            chemin += ".pdf"
        try:
            exporter_planche_poteau(
                chemin, self.sortie["modele"], self._choix_lus(),
                hauteur_poutre_cm=self.sortie.get("hauteur_poutre", 35.0),
            )
        except OSError as erreur:
            QMessageBox.warning(self, "Export impossible",
                                f"Le fichier n'a pas pu être écrit :\n\n{erreur}")
            return
        QMessageBox.information(self, "Export réussi", f"Planche enregistrée :\n{chemin}")

    def _vider_els(self) -> None:
        while self._zone_els.count():
            widget = self._zone_els.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self.sortie.pop("verification_els", None)
        self.sortie.pop("armatures_choisies", None)

    def _verifier_els(self) -> None:
        sections = self._sections_choisies()
        choisies = replace(self._armatures_elu, **sections)
        if self.identifiant == "poteau_circ":
            n_ch = self._choix_lus()["As1"][0]
            modele = replace(self.sortie["modele"], nombre_barres=n_ch)
            sollicitation = self.sortie["sollicitation_els"]
            verification = modele.verifier_els(sollicitation, sections["As1"])
            res = self.sortie["resultat"]
            _x, M_Rd, ok = modele.verifier_resistance(res.sollicitation_elu, sections["As1"], res)
            M_et = res.effets_2nd_ordre.moment_calcul if res.effets_2nd_ordre else abs(res.sollicitation_elu.M)
            self._resistance_circ = (M_Rd, M_et, ok)
        elif self.identifiant == "voute":
            sollicitation = None
            verification = self.sortie["modele"].verifier_els(self.sortie["resultat"], choisies)
        else:
            sollicitation = self.sortie["sollicitation_els"]
            verification = self.sortie["modele"].verifier_els(sollicitation, choisies)
        self._vider_els()
        self.sortie["armatures_choisies"] = choisies
        self.sortie["verification_els"] = verification

        cadre, disposition = carte()
        disposition.addWidget(titre_section("Vérification à l'ELS"))
        if self.identifiant == "poteau_circ":
            M_Rd, M_et, ok = self._resistance_circ
            disposition.addWidget(LigneResultat(
                "Résistance ELU M_Rd / M*_Ed",
                f"{_nombre(M_Rd, 2)} / {_nombre(M_et, 2, 'kN·m')}",
                BadgeVerdict("vérifié" if ok else "non vérifié", "succes" if ok else "danger"),
                en_evidence=True,
            ))
        if sollicitation is not None and sollicitation.N < 0 and self.identifiant == "poteau":
            disposition.addWidget(
                LigneResultat("Contrainte béton σc", "section entièrement tendue")
            )
        else:
            disposition.addWidget(
                LigneResultat(
                    "Contrainte béton σc",
                    f"{_nombre(verification.sigma_beton, 2)} / {_nombre(verification.sigma_beton_limite, 2, 'MPa')}",
                    BadgeVerdict(
                        "vérifié" if verification.beton_verifie else "non vérifié",
                        "succes" if verification.beton_verifie else "danger",
                    ),
                    en_evidence=True,
                )
            )
        disposition.addWidget(
            LigneResultat(
                "Contrainte acier σs",
                f"{_nombre(verification.sigma_acier, 2)} / {_nombre(verification.sigma_acier_limite, 2, 'MPa')}",
                BadgeVerdict(
                    "vérifié" if verification.acier_verifie else "non vérifié",
                    "succes" if verification.acier_verifie else "danger",
                ),
                en_evidence=True,
            )
        )
        if not verification.verifie:
            conseil = QLabel(
                "Contrainte limite dépassée : augmentez la section d'armatures "
                "choisie ou les dimensions de la section."
            )
            conseil.setObjectName("Legende")
            conseil.setWordWrap(True)
            disposition.addWidget(conseil)
        self._zone_els.addWidget(cadre)

    # ------------------------------------------------------------------
    # Voûte
    # ------------------------------------------------------------------
    def _corps_poteau_circ(self) -> None:
        resultat = self.sortie["resultat"]
        modele = self.sortie["modele"]
        effets = resultat.effets_2nd_ordre
        s = resultat.sollicitation_elu

        cadre, disposition = carte()
        disposition.addWidget(titre_section("Excentricités et second ordre"))
        if effets is not None:
            disposition.addWidget(LigneResultat("Excentricité 1er ordre e₁", _nombre(effets.excentricite_1er_ordre * 100, 2, "cm")))
            disposition.addWidget(LigneResultat("Imperfections eᵢ", _nombre(effets.excentricite_imperfection * 100, 3, "cm")))
            disposition.addWidget(LigneResultat("Second ordre e₂", _nombre(effets.excentricite_2nd_ordre * 100, 3, "cm")))
            disposition.addWidget(LigneResultat("Excentricité totale e_tot", _nombre(effets.excentricite_totale * 100, 2, "cm"), en_evidence=True))
            disposition.addWidget(LigneResultat(
                "Élancement λ / λ_lim",
                f"{_nombre(effets.lambda_calcule, 2)} / {_nombre(effets.lambda_limite, 2)}",
                BadgeVerdict("2nd ordre pris en compte" if effets.second_ordre_necessaire else "2nd ordre négligeable",
                             "alerte" if effets.second_ordre_necessaire else "succes"),
            ))
            disposition.addWidget(LigneResultat("Moment de calcul M*_Ed", _nombre(effets.moment_calcul, 2, "kN·m"), en_evidence=True))
        else:
            disposition.addWidget(LigneResultat("Excentricité e₀ (traction)", _nombre(abs(s.M / s.N) * 100, 2, "cm"), en_evidence=True))
            note = QLabel("Effort de traction : pas d'effet du second ordre.")
            note.setObjectName("Legende")
            disposition.addWidget(note)
        self._corps.addWidget(cadre)

        libelles = {
            CasSection.PARTIELLEMENT_COMPRIMEE: "Section partiellement comprimée",
            CasSection.ENTIEREMENT_TENDUE: "Section entièrement tendue",
            CasSection.ENTIEREMENT_COMPRIMEE: "Section entièrement comprimée",
        }
        self._corps.addWidget(self._bandeau_cas("Équilibre", libelles[resultat.cas]))

        cadre_a, disposition_a = carte()
        disposition_a.addWidget(titre_section("Armatures à l'ELU"))
        a = resultat.armatures
        disposition_a.addWidget(LigneResultat("Axe neutre x", _nombre(resultat.x / 10, 2, "cm")))
        if s.N > 0:
            disposition_a.addWidget(LigneResultat("M_Rd du béton seul", _nombre(resultat.M_Rd_beton, 2, "kN·m")))
        disposition_a.addWidget(LigneResultat("Section totale As", _nombre(a.As1, 1, "mm²"), en_evidence=True))
        disposition_a.addWidget(LigneResultat("As,min réglementaire", _nombre(a.As_min, 1, "mm²")))
        disposition_a.addWidget(LigneResultat("As,max réglementaire", _nombre(a.As_max, 0, "mm²")))
        disposition_a.addWidget(LigneResultat("Barres réparties (calcul)", str(modele.nombre_barres)))
        for texte in (a.commentaire, *resultat.notes):
            note = QLabel(texte)
            note.setObjectName("Legende")
            note.setWordWrap(True)
            disposition_a.addWidget(note)
        self._corps.addWidget(cadre_a)

        self._zone_els = QVBoxLayout()
        self._corps.addWidget(self._carte_choix_armatures(a, nappes=("As1",)))
        self._corps.addLayout(self._zone_els)

    def _corps_voute(self) -> None:
        resultat = self.sortie["resultat"]
        section = resultat.section_critique
        verification = resultat.verification_12_6

        cadre, disposition = carte()
        disposition.addWidget(titre_section("Statique de l'arc (Mesnager)"))
        disposition.addWidget(
            LigneResultat("Poussée horizontale H", _nombre(resultat.poussee_horizontale, 2, "kN/m"), en_evidence=True)
        )
        disposition.addWidget(LigneResultat("Rayon de l'arc R", _nombre(resultat.rayon_arc, 2, "m")))
        moments = resultat.moments_aux_rotules
        tous_nuls = all(abs(m) < 1e-6 for m in moments)
        disposition.addWidget(
            LigneResultat(
                "Moments aux 3 rotules",
                f"{_nombre(moments[0], 3)} · {_nombre(moments[1], 3)} · {_nombre(moments[2], 3)} kN·m",
                BadgeVerdict("isostatique confirmé" if tous_nuls else "à revoir",
                             "succes" if tous_nuls else "danger"),
            )
        )
        self._corps.addWidget(cadre)

        cadre_sc, disposition_sc = carte()
        disposition_sc.addWidget(titre_section("Section courante la plus sollicitée"))
        disposition_sc.addWidget(LigneResultat("Abscisse x*", _nombre(section.x, 2, "m"), en_evidence=True))
        disposition_sc.addWidget(LigneResultat("Moment M(x*)", _nombre(section.moment, 2, "kN·m")))
        disposition_sc.addWidget(LigneResultat("Effort normal N", _nombre(section.effort_normal, 2, "kN")))
        disposition_sc.addWidget(
            LigneResultat("Pente de l'arc φ", _nombre(math.degrees(section.angle_rad), 2, "°"))
        )
        disposition_sc.addWidget(
            LigneResultat("Excentricité géométrique", _nombre(section.excentricite_geo * 100, 2, "cm"))
        )
        disposition_sc.addWidget(
            LigneResultat(
                "Excentricité totale",
                _nombre(resultat.effets_2nd_ordre.excentricite_totale * 100, 2, "cm"),
                en_evidence=True,
            )
        )
        self._corps.addWidget(cadre_sc)

        cadre_v, disposition_v = carte()
        disposition_v.addWidget(titre_section("Vérifications du béton non armé"))
        disposition_v.addWidget(LigneResultat("Coefficient Φ", _nombre(verification.phi, 3)))
        disposition_v.addWidget(
            LigneResultat("Élancement λ", _nombre(verification.lambda_calcule, 2),
                          BadgeVerdict("λ ≤ 86" if verification.elancement_ok else "λ > 86",
                                       "succes" if verification.elancement_ok else "danger"))
        )
        disposition_v.addWidget(
            LigneResultat(
                "N_Ed / N_Rd,12",
                f"{_nombre(verification.N_Ed, 1)} / {_nombre(verification.N_Rd12, 1, 'kN')}",
                BadgeVerdict("vérifié" if verification.verifie else "non vérifié",
                             "succes" if verification.verifie else "danger"),
                en_evidence=True,
            )
        )
        self._corps.addWidget(cadre_v)

        cadre_a, disposition_a = carte()
        disposition_a.addWidget(titre_section("Armatures à la section critique"))
        disposition_a.addWidget(
            LigneResultat("Nappe As1", _nombre(resultat.armatures.As1, 1, "mm²/m"), en_evidence=True)
        )
        disposition_a.addWidget(LigneResultat("Nappe As2", _nombre(resultat.armatures.As2, 1, "mm²/m")))
        disposition_a.addWidget(LigneResultat("As,min réglementaire", _nombre(resultat.armatures.As_min, 1, "mm²/m")))
        self._corps.addWidget(cadre_a)

        self._zone_els = QVBoxLayout()
        self._corps.addWidget(self._carte_choix_armatures(
            resultat.armatures, largeur=self.sortie["modele"].largeur_calcul))
        self._corps.addLayout(self._zone_els)

    # ------------------------------------------------------------------
    # Mur porteur
    # ------------------------------------------------------------------
    def _corps_mur(self) -> None:
        resultat = self.sortie["resultat"]
        v1, v2, v3 = (
            resultat.verif_forces_axiales,
            resultat.verif_effort_tranchant,
            resultat.verif_flambement,
        )

        cadre, disposition = carte()
        disposition.addWidget(titre_section("Les trois vérifications du béton non armé"))
        disposition.addWidget(
            LigneResultat(
                "1 — Forces axiales",
                f"{_nombre(v1.N_Ed, 1)} / {_nombre(v1.N_Rd1, 1, 'kN')}",
                BadgeVerdict("vérifié" if v1.verifie else "non vérifié",
                             "succes" if v1.verifie else "danger"),
            )
        )
        disposition.addWidget(
            LigneResultat(
                "2 — Effort tranchant",
                f"{_nombre(v2.tau_cp, 3)} / {_nombre(v2.f_cvd, 3, 'MPa')}",
                BadgeVerdict("vérifié" if v2.verifie else "non vérifié",
                             "succes" if v2.verifie else "danger"),
            )
        )
        disposition.addWidget(
            LigneResultat(
                "3 — Flambement",
                f"{_nombre(v3.N_Ed, 1)} / {_nombre(v3.N_Rd12, 1, 'kN')}",
                BadgeVerdict("vérifié" if v3.verifie else "non vérifié",
                             "succes" if v3.verifie else "danger"),
            )
        )
        disposition.addWidget(
            LigneResultat("Élancement λ", _nombre(v3.lambda_calcule, 2),
                          BadgeVerdict("λ ≤ 86" if v3.elancement_ok else "λ > 86",
                                       "succes" if v3.elancement_ok else "danger"))
        )
        self._corps.addWidget(cadre)

        etat = "succes" if resultat.calculable_non_arme else "alerte"
        texte = (
            "Voile calculable comme NON ARMÉ"
            if resultat.calculable_non_arme
            else "Le voile DOIT être armé"
        )
        cadre_c, disposition_c = carte()
        ligne = QHBoxLayout()
        label = QLabel("Conclusion")
        label.setStyleSheet(f"color: {PALETTE.texte_secondaire}; font-size: 12pt;")
        ligne.addWidget(label)
        ligne.addWidget(BadgeVerdict(texte, etat))
        ligne.addStretch()
        disposition_c.addLayout(ligne)
        for note in resultat.notes:
            label_note = QLabel(note)
            label_note.setObjectName("Legende")
            label_note.setWordWrap(True)
            disposition_c.addWidget(label_note)
        self._corps.addWidget(cadre_c)

        armatures = self.sortie.get("armatures_si_arme")
        if armatures is not None:
            cadre_a, disposition_a = carte()
            disposition_a.addWidget(
                titre_section("Armatures si le voile est calculé comme armé")
            )
            disposition_a.addWidget(
                LigneResultat("Aciers d'about As1", _nombre(armatures.As1, 1, "mm²"), en_evidence=True)
            )
            disposition_a.addWidget(LigneResultat("Nappe As2", _nombre(armatures.As2, 1, "mm²")))
            disposition_a.addWidget(LigneResultat("As,min réglementaire", _nombre(armatures.As_min, 1, "mm²")))
            note = QLabel(armatures.commentaire)
            note.setObjectName("Legende")
            note.setWordWrap(True)
            disposition_a.addWidget(note)
            self._corps.addWidget(cadre_a)
            self._zone_els = QVBoxLayout()
            self._corps.addWidget(self._carte_choix_armatures(
                armatures, nappes=("As1",), avec_els=False))
            self._corps.addLayout(self._zone_els)

    # ------------------------------------------------------------------
    def _carte_notes(self, notes: tuple[str, ...]) -> QWidget:
        cadre, disposition = carte(espacement=METRIQUES.pad_sm)
        disposition.addWidget(titre_section("Observations"))
        for note in notes:
            ligne = QHBoxLayout()
            puce = QLabel("•")
            puce.setStyleSheet(f"color: {PALETTE.texte_tertiaire};")
            puce.setFixedWidth(12)
            ligne.addWidget(puce, alignment=Qt.AlignmentFlag.AlignTop)
            texte = QLabel(note)
            texte.setWordWrap(True)
            texte.setStyleSheet(f"color: {PALETTE.texte_secondaire}; font-size: 12pt;")
            ligne.addWidget(texte, stretch=1)
            disposition.addLayout(ligne)
        return cadre

    def _barre_actions(self) -> QHBoxLayout:
        ligne = QHBoxLayout()
        retour = QPushButton("← Modifier les données")
        retour.setObjectName("Discret")
        retour.clicked.connect(self.retour_demande.emit)
        ligne.addWidget(retour)
        ligne.addStretch()

        nouveau = QPushButton("Nouveau calcul")
        nouveau.clicked.connect(self.nouveau_calcul_demande.emit)
        ligne.addWidget(nouveau)
        return ligne
