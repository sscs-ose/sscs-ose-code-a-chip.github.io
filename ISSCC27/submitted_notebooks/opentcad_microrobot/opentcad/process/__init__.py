"""
opentcad.process — Process simulation orchestrator.

Top-level entry point for the Phase 1 + Phase 2 pipeline. Takes a
Structure (initial substrate geometry + contacts) and a Recipe
(ordered process-flow DSL), runs the topography half, meshes the
result, applies the doping half, and hands back a MeshField ready for
the device solver.

The orchestrator is a thin stitch over three stages that live in their
own subpackages:

    opentcad.process.topography.simulate         — level-set evolution
    opentcad.process.topography_to_meshfield     — Gmsh triangulation
    opentcad.process.doping.apply_doping_recipe  — implant / anneal

Clients that only need one of those three can import them directly;
`run_recipe` is the "give me the whole thing, in one call" API that
closes the process → device loop end-to-end.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from opentcad.geometry.formats import MeshField

from .doping import DopingRecipeResult, apply_doping_recipe
from .topography import (
    Recipe, TopographyState, simulate, topography_to_meshfield,
)
from .topography.recipe import Anneal, Implant


@dataclass
class RecipeRunResult:
    """Everything the orchestrator produced, in one object. The
    MeshField is the main artefact; the rest is diagnostic.

    `topography_state` is None when the recipe is doping-only (in
    which case the MeshField came straight from Structure.to_meshfield
    instead of from the level-set stack)."""
    meshfield: MeshField
    topography_state: Optional[TopographyState] = None
    doping_result: DopingRecipeResult = field(default_factory=DopingRecipeResult)


def _recipe_has_topography_steps(recipe: Recipe) -> bool:
    """A recipe is topography-free if every step is a doping step
    (Implant or Anneal)."""
    return any(not isinstance(step, (Implant, Anneal)) for step in recipe)


def run_recipe(structure,
               recipe: Recipe,
               *,
               grid_delta_um: float = 0.005,
               mesh_size_um: float = 0.03,
               ) -> RecipeRunResult:
    """Run *recipe* against *structure*, end to end. Returns a
    MeshField with material_id, Nd, Na, and contacts all populated.

    Args:
        structure: initial geometry (substrate + layers + regions +
            contacts). Any `doping_Na` / `doping_Nd` on substrates
            or regions is honoured as the starting doping; implants
            in the recipe add on top.
        recipe: ordered process-flow DSL. Topography steps are played
            through ViennaLS; doping steps are deferred to the meshed
            device.
        grid_delta_um: level-set grid spacing for topography steps.
            Default 5 nm — fine enough for Phase 1 LOCOS, cheap enough
            for interactive use.
        mesh_size_um: Gmsh characteristic element size for the device
            mesh. Default 30 nm — matches Phase 0 exit-criterion MOSFET.

    Returns:
        `RecipeRunResult` carrying the finished MeshField plus the
        intermediate TopographyState (if any) and the DopingRecipeResult.
    """
    # Topography half. If the recipe has no topography steps we can
    # skip the level-set round-trip entirely and mesh the Structure
    # directly — faster, and keeps hand-drawn devices identical to
    # their pre-Recipe form.
    if _recipe_has_topography_steps(recipe):
        topo = simulate(structure, recipe, grid_delta_um=grid_delta_um)
        mf = topography_to_meshfield(topo, mesh_size_um=mesh_size_um)
    else:
        topo = None
        mf = structure.to_meshfield(mesh_size_um=mesh_size_um)

    # Doping half.
    dop = apply_doping_recipe(mf, recipe)

    return RecipeRunResult(meshfield=mf,
                            topography_state=topo,
                            doping_result=dop)


__all__ = [
    "run_recipe",
    "RecipeRunResult",
    "apply_doping_recipe",
    "DopingRecipeResult",
    "simulate",
    "topography_to_meshfield",
    "Recipe",
    "TopographyState",
]
