"""
opentcad.process.topography — Level-set topography simulation.

Public surface:
    Recipe, Deposit, Etch, Oxidize     — recipe DSL (pure data)
    TopographyState, Layer             — simulation state (viennals-backed)
    simulate                           — run a Recipe on a Structure
    initial_state_from_structure       — get the starting stack
    extract_surface_polyline           — level-set → (nodes, lines)
    topography_to_meshfield            — final state → MeshField for the
                                          device solver
"""
from .recipe import Recipe, Deposit, Etch, Oxidize
from .simulator import (
    Layer,
    TopographyState,
    extract_surface_polyline,
    initial_state_from_structure,
    simulate,
)
from .mesh_bridge import topography_to_meshfield

__all__ = [
    "Recipe", "Deposit", "Etch", "Oxidize",
    "Layer", "TopographyState",
    "extract_surface_polyline",
    "initial_state_from_structure",
    "simulate",
    "topography_to_meshfield",
]
