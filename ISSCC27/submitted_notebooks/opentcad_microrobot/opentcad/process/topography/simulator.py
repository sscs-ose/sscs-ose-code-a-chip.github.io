"""
opentcad/process/topography/simulator.py — Level-set topography engine.

Plays a Recipe against an initial substrate and produces a stack of
material level-sets. Uses ViennaLS (viennals) as the low-level level-set
library.

Why viennals directly and not viennaps?
  On macOS the current viennaps 4.6 wheel statically links VTK and
  registers duplicate Objective-C classes (vtkCocoa*) that collide with
  viennals's copy, causing SIGSEGV in `MakePlane.apply()` and
  `getMaterialsInDomain()`. viennals alone is stable and gives us
  everything Milestone 1.1a needs:

    * Domain construction with bounds + boundary conditions
    * Plane / Sphere / Box primitives via MakeGeometry
    * GeometricAdvect with SphereDistribution for Minkowski
      dilation/erosion (isotropic deposit/etch)
    * BooleanOperation for stack maintenance
    * ToSurfaceMesh to extract polylines for the mesh bridge

    We wrap process-model semantics ourselves (deposit vs. etch, mask
    handling); ViennaPS's PlasmaEtchingParameters and friends will slot
    in when the macOS wheel is fixed.

State representation:
  A `TopographyState` holds an ordered list of level-sets, bottom-first.
  Convention: each level-set's implicit surface is the *top* of that
  material. The material fills the region between its top and the top of
  the material below (or the domain floor for the bottom material). This
  matches how viennals's ToVoxelMesh / disk-mesh multi-LS conventions
  work and how ViennaPS labels materials in a stacked domain.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

import numpy as np
import viennals

from opentcad.geometry.formats import Material

from .oxidation import (
    ALPHA_SI_CONSUMED_PER_OXIDE,
    oxide_thickness,
    temperature_celsius_to_kelvin,
)
from .recipe import Anneal, Deposit, Etch, Implant, Oxidize, Recipe


@dataclass
class Layer:
    """One material layer in the topography stack.

    Attributes:
        material: opentcad Material enum for the layer.
        level_set: viennals 2D Domain whose implicit surface marks the
            *top* of this material.
    """
    material: Material
    level_set: "viennals.d2.Domain"


@dataclass
class TopographyState:
    """Full topography stack — bottom material first.

    Attributes:
        bounds_um: (xmin, xmax, ymin, ymax) simulation window in um.
        grid_delta_um: level-set grid spacing in um.
        layers: material layers, bottom-to-top.
    """
    bounds_um: tuple  # (xmin, xmax, ymin, ymax)
    grid_delta_um: float
    layers: List[Layer] = field(default_factory=list)

    @property
    def top(self) -> Layer:
        if not self.layers:
            raise RuntimeError("TopographyState has no layers yet.")
        return self.layers[-1]


def _boundary_conditions() -> Sequence:
    """Reflective x, infinite y — the standard 2D wafer-column convention."""
    bc = viennals._core.BoundaryConditionEnum
    return [bc.REFLECTIVE_BOUNDARY, bc.INFINITE_BOUNDARY]


def _empty_domain(bounds_um: tuple, grid_delta_um: float) -> "viennals.d2.Domain":
    xmin, xmax, ymin, ymax = bounds_um
    return viennals.d2.Domain(
        [float(xmin), float(xmax), float(ymin), float(ymax)],
        _boundary_conditions(),
        float(grid_delta_um),
    )


def _plane_at(bounds_um: tuple, grid_delta_um: float, y_um: float,
              normal_up: bool = True) -> "viennals.d2.Domain":
    """Build a level-set whose surface is the horizontal plane y = y_um.

    normal_up=True → material occupies y < y_um (surface faces up).
    """
    ls = _empty_domain(bounds_um, grid_delta_um)
    origin = [0.0, float(y_um)]
    normal = [0.0, 1.0 if normal_up else -1.0]
    plane = viennals.d2.Plane(origin, normal)
    viennals.d2.MakeGeometry(ls, plane).apply()
    return ls


def _dilate(level_set: "viennals.d2.Domain", radius_um: float) -> None:
    """Minkowski-dilate the surface by radius_um (positive grows out,
    negative erodes inward). In-place.

    Uses viennals GeometricAdvect + SphereDistribution — the standard
    "isotropic advance for time T with unit velocity" primitive. In 2D
    the SphereDistribution is really a disk of the given radius.
    """
    dist = viennals.d2.SphereDistribution(float(radius_um))
    advector = viennals.d2.GeometricAdvect()
    advector.setLevelSet(level_set)
    advector.setAdvectionDistribution(dist)
    advector.apply()


def initial_state_from_structure(structure, grid_delta_um: float = 0.01
                                 ) -> TopographyState:
    """Build the starting TopographyState from an opentcad Structure.

    Supports both single-substrate (add_substrate) and stacked initial
    conditions (add_substrate + add_layer). Layers are iterated in
    bottom-to-top order — matching Structure's storage — so state.layers
    ends up bottom-first, which is also the order ViennaLS expects when
    the stack is handed to Advect for multi-material simulation.
    """
    if len(structure._layers) < 1:
        raise ValueError(
            "Structure has no layers to serve as initial substrate.")

    xmin, xmax = 0.0, float(structure.width_um)

    y_bottom = 0.0
    y_top_total = sum(l.thickness_um for l in structure._layers)
    # Domain top gets some headroom so subsequent deposits don't run into
    # the boundary. The bottom stays at the substrate floor — the mesh
    # bridge uses ymin as the physical wafer floor, and going below it
    # would silently thicken the substrate.
    ymin = y_bottom
    ymax = y_top_total + max(0.5, 0.5 * y_top_total)

    state = TopographyState(bounds_um=(xmin, xmax, ymin, ymax),
                            grid_delta_um=float(grid_delta_um))

    y = y_bottom
    for layer in structure._layers:
        y += layer.thickness_um
        ls = _plane_at(state.bounds_um, state.grid_delta_um, y_um=y)
        state.layers.append(Layer(material=layer.material, level_set=ls))
    return state


def _apply_deposit(state: TopographyState, step: Deposit) -> None:
    """Add a new layer on top: duplicate the current top surface, dilate
    it by thickness. The old top marks the bottom of the new material;
    the dilated LS marks its new top."""
    if not state.layers:
        raise RuntimeError("Cannot deposit onto an empty stack.")

    top_ls = state.top.level_set
    # Deep-copy the top surface to become the new material's top LS.
    new_ls = viennals.d2.Domain(top_ls)
    _dilate(new_ls, +step.thickness_um)
    state.layers.append(Layer(material=step.material, level_set=new_ls))


def _exposed(coord, mask_y, x0, x1, tol):
    """Common mask gate: True if the surface point at *coord* is
    reachable by etchant given a rigid mask that covers the surface
    everywhere except x ∈ [x0, x1] and initially sits at y = mask_y.

    Either the point is inside the window, or the point has already
    dropped below the initial mask height (sidewall of the trench once
    it starts advancing under the mask edge).
    """
    x, y = coord[0], coord[1]
    if x0 <= x <= x1:
        return True
    return y < mask_y - tol


def _rate_scale(material_idx: int,
                materials_in_order,
                rate_map,
                default_rate: float) -> float:
    """Look up the per-material rate scale for a surface point.

    `material_idx` is the integer ViennaLS passes to the VelocityField
    callback — it's the index of the stacked LS the surface point sits
    on, matching the order we handed to `Advect.insertNextLevelSet`.
    We map it back to an `opentcad.Material` enum via
    `materials_in_order[material_idx]`, then look up `rate_map` for the
    scale (or fall back to `default_rate` for an unlisted material).

    When `rate_map is None` the behaviour is "etch everything at full
    rate" — preserves Phase 1 scripts that pre-date Unit D selectivity.
    """
    if rate_map is None:
        return 1.0
    if 0 <= material_idx < len(materials_in_order):
        mat = materials_in_order[material_idx]
        return rate_map.get(mat, default_rate)
    return default_rate


class _MaskedIsotropicVelocity(viennals.VelocityField):
    """Isotropic etch through a photolith-style mask window.

    Rate is uniform (-rate along the normal) wherever the surface is
    exposed; the level-set produces the textbook quarter-circle
    undercut at the mask edges because every exposed point advances
    simultaneously along its own normal.

    Per-material selectivity (`rate_map`): scales the uniform rate by
    `rate_map[Material.<name>]` based on which stacked LS the point
    sits on. Unlisted materials get `default_rate`. See `_rate_scale`.
    """
    def __init__(self, rate: float, x0: float, x1: float, mask_y: float,
                 materials_in_order=None,
                 rate_map=None,
                 default_rate: float = 0.0,
                 tol: float = 1e-4):
        super().__init__()
        self.rate = float(rate)
        self.x0 = float(x0)
        self.x1 = float(x1)
        self.mask_y = float(mask_y)
        self.tol = float(tol)
        self.materials_in_order = list(materials_in_order or [])
        self.rate_map = dict(rate_map) if rate_map is not None else None
        self.default_rate = float(default_rate)

    def getScalarVelocity(self, coord, material, normal, pointID):
        if not _exposed(coord, self.mask_y, self.x0, self.x1, self.tol):
            return 0.0
        scale = _rate_scale(material, self.materials_in_order,
                             self.rate_map, self.default_rate)
        return -self.rate * scale

    def getVectorVelocity(self, coord, material, normal, pointID):
        return [0.0, 0.0, 0.0]

    def getDissipationAlpha(self, direction, material, coord):
        return abs(self.rate)


class _MaskedDirectionalVelocity(viennals.VelocityField):
    """RIE-style directional etch through a photolith-style mask window.

    The etchant is a collimated ion beam travelling along `direction`.
    A surface facet's etch rate scales with how strongly it faces INTO
    the beam:

        v = -rate * material_scale *
            (sidewall_ratio + (1 - sidewall_ratio) * max(0, -direction · normal))

    So the horizontal trench floor (normal = (0, 1)) sees the full ion
    flux and etches at -rate · material_scale, whereas a vertical
    sidewall (normal = ±x) etches at -rate · material_scale · sidewall_ratio.
    With sidewall_ratio = 0 the sidewalls freeze and the trench walls
    stay vertical — the RIE limit. The mask gate is the same as for the
    isotropic case, and the per-material rate scale is the same as
    `_MaskedIsotropicVelocity`.
    """
    def __init__(self, rate: float, x0: float, x1: float, mask_y: float,
                 direction: Tuple[float, float], sidewall_ratio: float,
                 materials_in_order=None,
                 rate_map=None,
                 default_rate: float = 0.0,
                 tol: float = 1e-4):
        super().__init__()
        self.rate = float(rate)
        self.x0 = float(x0)
        self.x1 = float(x1)
        self.mask_y = float(mask_y)
        # Normalize the 2D beam direction to unit length so
        # dot(direction, normal) is a real cosine.
        dx, dy = float(direction[0]), float(direction[1])
        norm = math.sqrt(dx * dx + dy * dy)
        self.dx, self.dy = dx / norm, dy / norm
        self.iso = float(sidewall_ratio)
        self.tol = float(tol)
        self.materials_in_order = list(materials_in_order or [])
        self.rate_map = dict(rate_map) if rate_map is not None else None
        self.default_rate = float(default_rate)

    def getScalarVelocity(self, coord, material, normal, pointID):
        if not _exposed(coord, self.mask_y, self.x0, self.x1, self.tol):
            return 0.0
        scale = _rate_scale(material, self.materials_in_order,
                             self.rate_map, self.default_rate)
        if scale == 0.0:
            return 0.0
        nx, ny = normal[0], normal[1]
        flux = max(0.0, -(self.dx * nx + self.dy * ny))
        return -self.rate * scale * (self.iso + (1.0 - self.iso) * flux)

    def getVectorVelocity(self, coord, material, normal, pointID):
        return [0.0, 0.0, 0.0]

    def getDissipationAlpha(self, direction, material, coord):
        return abs(self.rate)


def _current_top_y(level_set: "viennals.d2.Domain",
                   xmin: float, xmax: float) -> float:
    """Return the max y of the current top surface — used as the mask
    level for a windowed etch. Assumes a single-valued top surface."""
    mesh = viennals.Mesh()
    to_mesh = viennals.d2.ToSurfaceMesh()
    to_mesh.setLevelSet(level_set)
    to_mesh.setMesh(mesh)
    to_mesh.apply()
    nodes = mesh.getNodes()
    if not nodes:
        raise RuntimeError("Cannot sample top-y: level-set surface is empty.")
    return max(n[1] for n in nodes if xmin - 1e-6 <= n[0] <= xmax + 1e-6)


def _apply_etch(state: TopographyState, step: Etch) -> None:
    """Erode the top layer by depth.

    Backends:
      * unmasked isotropic — uniform Minkowski erosion via GeometricAdvect
        with a SphereDistribution of radius -depth. Fast, closed-form.
      * masked isotropic  — Advect + `_MaskedIsotropicVelocity`.
        Lax-Friedrichs step; textbook quarter-circle undercut.
      * unmasked directional / masked directional — Advect + the
        `_MaskedDirectionalVelocity` field. Ions travel along
        `step.direction`; surface recedes at full rate where it faces
        into the beam, at `sidewall_ratio · rate` where it doesn't. The
        RIE trench falls out of the same advection loop as the isotropic
        one.
    """
    if not state.layers:
        raise RuntimeError("Cannot etch an empty stack.")

    # Fast path: unmasked isotropic, no selectivity → closed-form
    # Minkowski erosion on the top LS. Selectivity (rates=…) needs the
    # Advect path so each LS sees its own per-material rate scale.
    if (step.model == "isotropic"
            and step.window_x_um is None
            and step.rates is None):
        _dilate(state.top.level_set, -step.depth_um)
        return

    xmin, xmax, _, _ = state.bounds_um
    if step.window_x_um is None:
        # A directional etch without a window still needs an ion-beam
        # gate so the horizontal top recedes at the right rate: model
        # the "no mask" case as a window spanning the whole domain.
        x0, x1 = xmin, xmax
    else:
        x0, x1 = step.window_x_um
        if x0 < xmin - 1e-6 or x1 > xmax + 1e-6:
            raise ValueError(
                f"Etch window [{x0:.3f}, {x1:.3f}] um extends outside "
                f"the simulation domain [{xmin:.3f}, {xmax:.3f}] um.")

    mask_y = _current_top_y(state.top.level_set, xmin, xmax)

    # Bottom-first list of Material enums — matches the order we hand
    # the LSs to Advect.insertNextLevelSet, so a `material` index from
    # the VF callback indexes directly into this list.
    materials_in_order = [L.material for L in state.layers]
    rate_map = step.rates
    default_rate = step.default_rate

    if step.model == "isotropic":
        vf = _MaskedIsotropicVelocity(
            rate=1.0, x0=x0, x1=x1, mask_y=mask_y,
            materials_in_order=materials_in_order,
            rate_map=rate_map, default_rate=default_rate)
    elif step.model == "directional":
        vf = _MaskedDirectionalVelocity(
            rate=1.0, x0=x0, x1=x1, mask_y=mask_y,
            direction=step.direction, sidewall_ratio=step.sidewall_ratio,
            materials_in_order=materials_in_order,
            rate_map=rate_map, default_rate=default_rate)
    else:
        raise ValueError(f"Unknown etch model {step.model!r}")

    # Multi-material advection: hand ViennaLS every layer's LS bottom-
    # first. It advects all of them under the shared VelocityField and
    # enforces the stack invariant (upper LS ≥ lower LS everywhere) —
    # so a deep etch that would push the top layer through the layer
    # below is resolved by pinning the top LS to the lower LS at those
    # columns and continuing to advect the exposed lower material.
    adv = viennals.d2.Advect()
    adv.setVelocityField(vf)
    for layer in state.layers:
        adv.insertNextLevelSet(layer.level_set)
    adv.setAdvectionTime(float(step.depth_um))
    adv.apply()


class _PerXScalarVelocity(viennals.VelocityField):
    """Scalar velocity field with per-x profile.

    For each surface point queried by the Advect kernel, look up the
    velocity by 1D linear interpolation over a supplied (xs, dys) table.
    Used to advect a horizontal-ish top surface by a per-column vertical
    displacement — the natural discretization of Deal-Grove oxidation,
    where the local oxide growth depends on the local existing thickness
    and on a mask function.

    We set the advection time to 1.0 and let `dys` carry the total
    signed displacement in μm. Scalar velocity is applied along the
    local normal, so a horizontal surface with normal = +y translates
    scalar v → vertical dy directly; a small curvature (e.g. near a
    bird's-beak feathering) introduces second-order deviation only.
    """

    def __init__(self, xs: np.ndarray, dys: np.ndarray):
        super().__init__()
        self.xs = np.asarray(xs, dtype=float)
        self.dys = np.asarray(dys, dtype=float)
        max_abs = float(np.max(np.abs(self.dys))) if self.dys.size else 0.0
        # Guard against Lax-Friedrichs dissipation-alpha under-estimate
        # for near-zero fields; 1e-9 μm is smaller than any physical
        # oxide growth.
        self._max_v = max(max_abs, 1e-9)

    def getScalarVelocity(self, coord, material, normal, pointID):
        return float(np.interp(coord[0], self.xs, self.dys))

    def getVectorVelocity(self, coord, material, normal, pointID):
        return [0.0, 0.0, 0.0]

    def getDissipationAlpha(self, direction, material, coord):
        return self._max_v


def _advect_by_per_x_dy(level_set: "viennals.d2.Domain",
                        xs: np.ndarray, dys: np.ndarray) -> None:
    """Displace a nearly-horizontal top-surface LS by dy(x). In-place."""
    if not np.any(np.abs(dys) > 1e-9):
        return  # nothing to do
    vf = _PerXScalarVelocity(xs, dys)
    adv = viennals.d2.Advect(level_set, vf)
    adv.setAdvectionTime(1.0)
    adv.apply()


def _sample_ls_y_at_xs(level_set: "viennals.d2.Domain",
                       xs_master: np.ndarray) -> np.ndarray:
    """Return y(x) for a single-valued top level-set at the master xs.

    Handles the ToSurfaceMesh multi-node-per-x case by keeping the
    lower y at duplicates (same policy as mesh_bridge)."""
    nodes, _ = extract_surface_polyline(level_set)
    if not nodes:
        raise RuntimeError("Cannot sample y(x): level-set surface is empty.")
    pts = np.asarray(nodes, dtype=float)
    xs = pts[:, 0]
    ys = pts[:, 1]
    order = np.argsort(xs, kind="stable")
    xs, ys = xs[order], ys[order]
    return np.interp(xs_master, xs, ys)


def _mask_factor(xs: np.ndarray, window: Tuple[float, float],
                 bird_beak_length_um: float) -> np.ndarray:
    """Growth-rate multiplier vs x: 1 inside the window, 0 far outside,
    exponentially feathered over `bird_beak_length_um` past each edge.

    The heuristic feathering stands in for lateral O2 diffusion under a
    LOCOS nitride edge — a proper 2D coupled diffusion PDE would give
    the exact bird's-beak shape, but at MVP scale the exponential tail
    reproduces the characteristic feature qualitatively."""
    x0, x1 = window
    factor = np.zeros_like(xs, dtype=float)
    inside = (xs >= x0) & (xs <= x1)
    factor[inside] = 1.0
    if bird_beak_length_um > 0.0:
        left = xs < x0
        right = xs > x1
        factor[left] = np.exp(-(x0 - xs[left]) / bird_beak_length_um)
        factor[right] = np.exp(-(xs[right] - x1) / bird_beak_length_um)
    return factor


def _apply_oxidize(state: TopographyState, step: Oxidize) -> None:
    """Grow SiO2 on top of exposed Si per Deal-Grove.

    Finds the top-most Si layer, spawns a SiO2 layer immediately above
    if one isn't already present, and advects both level-sets:
      * Si top drops by 0.44 · dx_ox
      * SiO2 top rises by 0.56 · dx_ox
    where dx_ox is the per-column Deal-Grove growth given the current
    local oxide thickness. Outside the optional window, dx_ox is
    masked to 0 (with an exponential bird's-beak tail if requested).
    """
    if not state.layers:
        raise RuntimeError("Cannot oxidize an empty stack.")

    # Locate the top-most Si layer and the layer directly above it (if
    # any). If that layer is already SiO2 we grow it; otherwise we
    # spawn a fresh SiO2 layer from a copy of Si-top, effectively
    # starting with zero oxide thickness at every column.
    si_idx = None
    for i in range(len(state.layers) - 1, -1, -1):
        if state.layers[i].material == Material.SI:
            si_idx = i
            break
    if si_idx is None:
        raise ValueError(
            "Oxidize step needs a Si layer in the stack; none found.")

    if si_idx + 1 < len(state.layers) and \
       state.layers[si_idx + 1].material == Material.SIO2:
        ox_layer = state.layers[si_idx + 1]
    else:
        new_ls = viennals.d2.Domain(state.layers[si_idx].level_set)
        ox_layer = Layer(material=Material.SIO2, level_set=new_ls)
        state.layers.insert(si_idx + 1, ox_layer)
    si_layer = state.layers[si_idx]

    xmin, xmax, _, _ = state.bounds_um
    grid = state.grid_delta_um
    # One xs sample per grid cell keeps interpolation consistent with
    # the level-set resolution.
    n_samples = max(64, int((xmax - xmin) / grid) + 1)
    xs_master = np.linspace(xmin, xmax, n_samples)

    ys_si = _sample_ls_y_at_xs(si_layer.level_set, xs_master)
    ys_ox = _sample_ls_y_at_xs(ox_layer.level_set, xs_master)
    x0 = np.maximum(0.0, ys_ox - ys_si)

    T_K = temperature_celsius_to_kelvin(step.temperature_C)
    x1 = np.array([oxide_thickness(float(x0i), step.time_s, T_K, step.ambient)
                   for x0i in x0])

    if step.window_x_um is None:
        mask = np.ones_like(x1)
    else:
        mask = _mask_factor(xs_master, step.window_x_um,
                            step.bird_beak_length_um)
    dx_grown = mask * (x1 - x0)

    _advect_by_per_x_dy(si_layer.level_set, xs_master,
                        -ALPHA_SI_CONSUMED_PER_OXIDE * dx_grown)
    _advect_by_per_x_dy(ox_layer.level_set, xs_master,
                        +(1.0 - ALPHA_SI_CONSUMED_PER_OXIDE) * dx_grown)


def simulate(structure, recipe: Recipe, grid_delta_um: float = 0.01
             ) -> TopographyState:
    """Run *recipe* on *structure*, returning the final TopographyState.

    Args:
        structure: opentcad Structure — provides the substrate + width.
        recipe: opentcad Recipe — ordered process steps.
        grid_delta_um: level-set grid spacing.
    """
    state = initial_state_from_structure(structure, grid_delta_um)
    for step in recipe:
        if isinstance(step, Deposit):
            _apply_deposit(state, step)
        elif isinstance(step, Etch):
            _apply_etch(state, step)
        elif isinstance(step, Oxidize):
            _apply_oxidize(state, step)
        elif isinstance(step, (Implant, Anneal)):
            # Doping — a MeshField concern, not a level-set concern.
            # Carried through to the doping dispatcher after meshing;
            # ignored by the topography simulator.
            continue
        else:
            raise TypeError(f"Unknown recipe step type: {type(step).__name__}")
    return state


def extract_surface_polyline(level_set: "viennals.d2.Domain"
                             ) -> "tuple[list, list]":
    """Extract the (nodes, lines) representation of a 2D level-set's
    surface. Returns the raw viennals Mesh contents:
      nodes: list of [x, y, z] (z always 0 in 2D)
      lines: list of [i, j] node indices forming the polyline segments.
    """
    mesh = viennals.Mesh()
    to_mesh = viennals.d2.ToSurfaceMesh()
    to_mesh.setLevelSet(level_set)
    to_mesh.setMesh(mesh)
    to_mesh.apply()
    return mesh.getNodes(), mesh.getLines()
