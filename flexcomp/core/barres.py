"""Table des aciers HA : section totale selon le nombre et le diamètre des barres."""

from __future__ import annotations

import math
import re

DIAMETRES_HA: tuple[int, ...] = (6, 8, 10, 12, 14, 16, 20, 25, 28, 32, 40, 50)
NOMBRES_BARRES: tuple[int, ...] = tuple(range(1, 11))


def section_barres(nombre: int, diametre_mm: float) -> float:
    """Section totale (mm²) de `nombre` barres HA de diamètre `diametre_mm`."""
    return nombre * math.pi * diametre_mm**2 / 4


_MOTIF_CHOIX = re.compile(r"^\s*(\d{1,3})\s*HA\s*(\d{1,2})\s*$", re.IGNORECASE)


def lire_choix(texte: str) -> tuple[int, int] | None:
    """Lit un choix d'armatures écrit « 35HA12 » -> (35, 12), ou None si invalide."""
    correspondance = _MOTIF_CHOIX.match(texte or "")
    if correspondance is None:
        return None
    nombre, diametre = int(correspondance.group(1)), int(correspondance.group(2))
    if nombre < 1 or diametre not in DIAMETRES_HA:
        return None
    return nombre, diametre


def format_choix(nombre: int, diametre: int) -> str:
    """(4, 12) -> « 4HA12 »."""
    return f"{nombre}HA{diametre}"
