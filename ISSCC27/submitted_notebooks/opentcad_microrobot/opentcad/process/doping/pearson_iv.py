"""
opentcad.process.doping.pearson_iv — Pearson-IV moment lookup.

Loads the per-species YAML tables under `data/` at import time and
returns the four moments (Rp, ΔRp, γ, β) for a given (species, energy).
Log-interpolates in energy — implant range vs energy follows a nuclear-
stopping-power law that is very close to a power law across the ranges
we tabulate, so log-linear is accurate to well under 5 % between
tabulated points.

The evaluator itself (Pearson-IV analytic profile) is *not* here yet —
the current implant kernel uses only Rp and ΔRp as a Gaussian
approximation. γ and β are surfaced for a later upgrade; see the
'implant is Gaussian' entry in KNOWN_ISSUES.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from opentcad.geometry.formats import Material


_DATA_DIR = Path(__file__).parent / "data"


# Species names OpenTCAD recognises. Uses lowercase full name as canonical.
# Add symbol aliases as we ship more species.
_ALIASES = {
    "boron":      "boron",
    "b":          "boron",
    "phosphorus": "phosphorus",
    "p":          "phosphorus",
    "arsenic":    "arsenic",
    "as":         "arsenic",
}


@dataclass(frozen=True)
class PearsonMoments:
    """The four moments of an implant depth distribution.

    Rp and dRp are in µm; γ and β are dimensionless. `dopant_kind` is
    'donor' or 'acceptor' — set from the YAML per species."""
    Rp_um: float
    dRp_um: float
    gamma: float
    beta: float
    dopant_kind: str      # 'donor' | 'acceptor'


@lru_cache(maxsize=None)
def _load_species(canonical_name: str) -> Dict:
    """Read a species YAML once, cache forever."""
    path = _DATA_DIR / f"{_symbol_for(canonical_name)}_in_Si.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No implant table for species {canonical_name!r}: "
            f"looked at {path}. Ship a YAML there to add one.")
    with path.open("r") as fh:
        return yaml.safe_load(fh)


_SYMBOLS = {"boron": "B", "phosphorus": "P", "arsenic": "As"}


def _symbol_for(canonical_name: str) -> str:
    return _SYMBOLS[canonical_name]


def canonicalize_species(name: str) -> str:
    """Normalize a species name to the canonical lowercase form. Raises
    ValueError with a clear message if we don't ship data for it."""
    key = name.strip().lower()
    if key not in _ALIASES:
        raise ValueError(
            f"Unknown implant species {name!r}. Known: "
            f"{sorted(set(_ALIASES.values()))}")
    return _ALIASES[key]


def available_species() -> List[str]:
    return sorted(set(_ALIASES.values()))


def moments_for(species: str, energy_keV: float,
                target: Material = Material.SI) -> PearsonMoments:
    """Interpolate Pearson-IV moments for the given species and energy.

    Uses log-linear interpolation on energy (implant range vs. energy is
    close to a power law across our tabulated range, so log-interp is
    accurate to well under 5% between points).

    Extrapolation is refused — raise ValueError if energy falls outside
    the tabulated range for that species. We'd rather force the caller
    to add a data point than silently return nonsense.
    """
    if target != Material.SI:
        raise NotImplementedError(
            f"Only Si target supported today; asked for {target}. "
            "Ship additional YAMLs to extend.")
    canonical = canonicalize_species(species)
    table = _load_species(canonical)
    rows = sorted(table["moments"], key=lambda r: r["energy_keV"])
    energies = [r["energy_keV"] for r in rows]

    if not (energies[0] <= energy_keV <= energies[-1]):
        raise ValueError(
            f"Energy {energy_keV} keV outside tabulated range for "
            f"{canonical} in Si [{energies[0]} … {energies[-1]}] keV.")

    # find bracketing rows
    for i in range(len(rows) - 1):
        if energies[i] <= energy_keV <= energies[i + 1]:
            lo, hi = rows[i], rows[i + 1]
            break
    else:
        # exact endpoint match
        row = rows[-1] if energy_keV == energies[-1] else rows[0]
        return PearsonMoments(
            Rp_um=row["Rp_um"], dRp_um=row["dRp_um"],
            gamma=row["gamma"], beta=row["beta"],
            dopant_kind=table["dopant_kind"],
        )

    # log-linear interpolation
    import math
    t = ((math.log(energy_keV) - math.log(lo["energy_keV"])) /
         (math.log(hi["energy_keV"]) - math.log(lo["energy_keV"])))

    def _interp_log(key):
        return math.exp(math.log(lo[key]) + t * (math.log(hi[key]) - math.log(lo[key])))

    def _interp_lin(key):
        return lo[key] + t * (hi[key] - lo[key])

    return PearsonMoments(
        Rp_um=_interp_log("Rp_um"),
        dRp_um=_interp_log("dRp_um"),
        gamma=_interp_lin("gamma"),
        beta=_interp_lin("beta"),
        dopant_kind=table["dopant_kind"],
    )
