"""
opentcad.process.doping — Dopant simulation (Phase 2).

Phase 2.1 ships the implant pieces: a Pearson-IV moment table lookup
and a Gaussian-shape implant kernel that writes Nd / Na onto a
MeshField. Diffusion / anneal (Phase 2.3) is the next piece.

Public surface:
    apply_implant                  — kernel, in-place on a MeshField
    ImplantResult                   — diagnostic record from apply_implant
    moments_for                    — Pearson-IV table lookup
    canonicalize_species           — normalise 'B'/'boron'/'Boron' → 'boron'
    available_species              — species we ship data for
    PearsonMoments                 — the four-moment record returned by moments_for
"""
from .anneal import AnnealResult, apply_anneal, diffusivity_intrinsic
from .dispatch import DopingRecipeResult, apply_doping_recipe
from .implant import ImplantResult, apply_implant
from .pearson_iv import (
    PearsonMoments,
    available_species,
    canonicalize_species,
    moments_for,
)

__all__ = [
    "apply_implant",
    "apply_anneal",
    "apply_doping_recipe",
    "ImplantResult",
    "AnnealResult",
    "DopingRecipeResult",
    "moments_for",
    "diffusivity_intrinsic",
    "PearsonMoments",
    "canonicalize_species",
    "available_species",
]
