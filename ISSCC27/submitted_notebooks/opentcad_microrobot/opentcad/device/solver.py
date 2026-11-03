"""
opentcad/device/solver.py — DEVSIM device simulation wrapper.

Phase 0: 2D drift-diffusion with constant mobility and SRH recombination.
Takes a MeshField (triangular mesh, cell material_id, point Nd/Na, ContactTag
list) and exposes iv_sweep() for ohmic-contact IV curves.

Units: MeshField is um. DEVSIM coordinates are converted to cm on entry.
Doping stays in cm^-3 throughout.

Equations follow the edge-based Scharfetter-Gummel formulation from DEVSIM's
diode_2d reference example (devsim_data/testing/dio2_element_2d.py); the
element-based flux detour is not needed for Phase 0.
"""
from __future__ import annotations
import warnings
import numpy as np
from scipy.spatial import cKDTree
from ..geometry.formats import MATERIAL_NAMES, Material, MeshField
from ..materials.database import MaterialParams
from .physics import PhysicsConfig

Q_C = 1.602176634e-19   # elementary charge [C]
KB_J = 1.380649e-23     # Boltzmann [J/K]
EPS0_F_CM = 8.8541878128e-14   # vacuum permittivity [F/cm]
T_K_DEFAULT = 300.0


class DeviceSolver:
    """DEVSIM drift-diffusion solver wrapping a MeshField.

    Args:
        meshfield: 2D triangle MeshField with material_id cell data, Nd/Na
                   point data, and ContactTag boundary nodes.
        material_params: Mapping from material display name (e.g. "Silicon")
                         or enum short name (e.g. "SI") to MaterialParams.
        temperature_K: Lattice temperature [K].

    Example:
        solver = DeviceSolver(mf, {"Silicon": load_material("Si")})
        V, I = solver.iv_sweep("anode", "cathode", 0.0, 0.7, 0.05)
    """

    _instance_counter = 0

    def __init__(self, meshfield: MeshField,
                 material_params: dict[str, MaterialParams],
                 temperature_K: float = T_K_DEFAULT,
                 physics: PhysicsConfig | None = None):
        self.mf = meshfield
        self.mat_params = material_params
        self.T = float(temperature_K)
        self.physics = physics if physics is not None else PhysicsConfig()
        base = meshfield.metadata.get("structure_name", "device")
        # DEVSIM keeps global mesh/device state — disambiguate per instance.
        DeviceSolver._instance_counter += 1
        suffix = DeviceSolver._instance_counter
        self._device_name = f"{base}_{suffix}"
        self._mesh_name = f"{base}_{suffix}_mesh"
        self._initialized = False
        self._contact_regions: dict[str, str] = {}     # contact name -> region name
        self._region_materials: dict[str, Material] = {}   # region name -> Material
        self._region_is_insulator: dict[str, bool] = {}    # region name -> insulator?
        self._interfaces: list[tuple[str, str, str]] = []  # (if_name, r0, r1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Build the DEVSIM device + equations. Idempotent per instance."""
        if self._initialized:
            return
        try:
            import devsim as ds
        except ImportError as e:
            raise ImportError(
                "DEVSIM is not installed. Install with: pip install devsim"
            ) from e
        self._ds = ds
        self._convert_meshfield()
        self._setup_equations()
        self._initialized = True

    def solve_equilibrium(self) -> None:
        """Warm-start with Poisson-only then switch to coupled DD solve.

        With a prescribed optical generation field this returns an illuminated
        steady state at the current contact biases, NOT thermal equilibrium.
        """
        if not self._initialized:
            self.initialize()
        ds = self._ds
        # Initialise Electrons/Holes from the intrinsic guess (populated by
        # the Poisson-only solve below) before switching to the coupled system.
        # First: solve Poisson only. The IntrinsicCharge node_model is the
        # residual; PotentialEquation in "potential-only" mode uses it.
        # Insulator regions already have a Poisson-only equation set in
        # _build_insulator_potential — leave them alone.
        for region in self._region_materials:
            if self._region_is_insulator.get(region, False):
                continue
            ds.equation(device=self._device_name, region=region,
                        name="PotentialEquation", variable_name="Potential",
                        node_model="PotentialIntrinsicNodeCharge",
                        edge_model="PotentialEdgeFlux",
                        variable_update="log_damp")
        ds.solve(type="dc", absolute_error=1.0, relative_error=1e-12,
                 maximum_iterations=30)

        # Seed carrier densities from the equilibrium potential, then rebuild
        # PotentialEquation with the full DD node charge and couple in the
        # continuity equations. Insulator regions stay Poisson-only.
        for region in self._region_materials:
            if self._region_is_insulator.get(region, False):
                continue
            ds.set_node_values(device=self._device_name, region=region,
                               name="Electrons", init_from="IntrinsicElectrons")
            ds.set_node_values(device=self._device_name, region=region,
                               name="Holes", init_from="IntrinsicHoles")
        # Attach mobility AFTER carriers are seeded — Klaassen needs sane
        # Electrons/Holes values when its node models are first evaluated.
        self._attach_mobility_models()
        for region in self._region_materials:
            if self._region_is_insulator.get(region, False):
                continue
            ds.equation(device=self._device_name, region=region,
                        name="PotentialEquation", variable_name="Potential",
                        node_model="PotentialNodeCharge",
                        edge_model="PotentialEdgeFlux",
                        variable_update="log_damp")
            self._build_continuity_equations(region)
        for contact in self._contact_regions:
            r = self._contact_regions[contact]
            if self._region_is_insulator.get(r, False):
                continue
            self._build_contact_dd_equations(contact)

        # Unstructured triangle meshes can't reach 1e-10 relative; UMFPACK
        # precision saturates around 1e-9. 1e-7 gives 7-digit residual which
        # is far below any current magnitude of physical interest.
        ds.solve(type="dc", absolute_error=1e10, relative_error=1e-7,
                 maximum_iterations=50)

    def cv_sweep(self, terminal: str, reference: str,
                 v_start: float, v_end: float, v_step: float
                 ) -> tuple[list[float], list[float]]:
        """Quasi-static CV sweep on `terminal` vs `reference` (held at 0V).

        For each Vg in [v_start, v_end], solve DC and query the total
        charge stored at `terminal` via DEVSIM's get_contact_charge.
        Capacitance C(V) is then dQ/dV computed by central differences:
            C(V_i) = (Q(V_{i+1}) - Q(V_{i-1})) / (V_{i+1} - V_{i-1}).

        Returns (voltages, C_values). Units of C follow DEVSIM's 2-D
        integration: F/cm of out-of-plane depth.

        Notes:
        - Requires `terminal` to be a metal-on-insulator (gate) contact,
          on which we register PotentialEdgeFlux as the edge_charge_model.
        - The result is quasi-static (the DC-diff limit) — equivalent to
          measured LF CV. For HF CV where minority carriers can't follow,
          a small-signal AC solve is a follow-up.
        """
        if not self._initialized:
            self.initialize()
        self.solve_equilibrium()
        self._set_contact_voltage(reference, 0.0)

        voltages = np.arange(v_start, v_end + v_step / 2, v_step)

        # Ramp from equilibrium (V=0) to voltages[0] in small steps so
        # Newton doesn't have to swallow a large first jump (crucial in
        # MOS-cap accumulation/inversion where a sudden 1-2V step blows
        # convergence). 50 mV steps are conservative but robust.
        ramp_step = min(0.05, abs(v_step))
        if abs(voltages[0]) > 1e-9:
            pre_ramp = np.sign(voltages[0]) * np.arange(
                ramp_step, abs(voltages[0]) + ramp_step / 2, ramp_step)
            for v in pre_ramp:
                self._set_contact_voltage(terminal, float(v))
                self._solve_dc()

        charges: list[float] = []
        for v in voltages:
            self._set_contact_voltage(terminal, float(v))
            self._solve_dc()
            charges.append(self._integrated_semiconductor_charge())

        # Q_gate = -Q_semi (charge conservation on the isolated device).
        Q = -np.asarray(charges)
        C = np.gradient(Q, voltages)     # central diff, edge-safe
        return voltages.tolist(), C.tolist()

    def _integrated_semiconductor_charge(self) -> float:
        """Return sum over every semi region of q * integral((p - n +
        N_d - N_a) dV). By charge conservation on an isolated device
        this equals -Q_stored_on_the_biasing_contacts."""
        ds = self._ds
        Q_total = 0.0
        for region, is_ins in self._region_is_insulator.items():
            if is_ins:
                continue
            vol = np.asarray(ds.get_node_model_values(
                device=self._device_name, region=region, name="NodeVolume"))
            n  = np.asarray(ds.get_node_model_values(
                device=self._device_name, region=region, name="Electrons"))
            p  = np.asarray(ds.get_node_model_values(
                device=self._device_name, region=region, name="Holes"))
            Nd = np.asarray(ds.get_node_model_values(
                device=self._device_name, region=region, name="Donors"))
            Na = np.asarray(ds.get_node_model_values(
                device=self._device_name, region=region, name="Acceptors"))
            rho = p - n + Nd - Na
            Q_total += Q_C * float((rho * vol).sum())
        return Q_total

    def iv_sweep(self, anode_contact: str, cathode_contact: str,
                 v_start: float, v_end: float, v_step: float,
                 hold_contacts: dict[str, float] | None = None,
                 measure_contact: str | None = None,
                 ) -> tuple[list[float], list[float]]:
        """Ramp `anode_contact` from v_start to v_end, holding cathode at 0V.

        Returns (voltages, currents). Current is total (electron+hole) at
        `measure_contact` in A/cm of out-of-plane length. Use
        ``opentcad.device.optical.current_from_2d`` for physical Amps.

        Args:
            anode_contact: contact whose voltage is ramped.
            cathode_contact: reference contact, held at 0 V.
            hold_contacts: {name: voltage} of other contacts to hold at a
                nonzero DC bias — e.g. `{"drain": 0.05}` for a MOSFET
                Id-Vgs sweep at Vds = 50 mV. Each is ramped from 0 up to
                its target in ~50 mV steps before the main sweep begins.
            measure_contact: contact to read current from. Defaults to
                `anode_contact` (the classic diode / two-terminal case).
                For an NMOS Id-Vgs sweep, set to the drain.
        """
        if not self._initialized:
            self.initialize()
        self.solve_equilibrium()
        self._set_contact_voltage(cathode_contact, 0.0)

        # Ramp any pre-held contacts to their target bias smoothly so
        # Newton doesn't get a step change on top of equilibrium.
        holds = dict(hold_contacts or {})
        for name, target in holds.items():
            if target == 0.0:
                self._set_contact_voltage(name, 0.0)
                continue
            n_steps = max(1, int(abs(target) / 0.05))
            for step_v in np.linspace(0.0, float(target), n_steps + 1)[1:]:
                self._set_contact_voltage(name, float(step_v))
                self._solve_dc()

        measure = measure_contact or anode_contact
        voltages = np.arange(v_start, v_end + v_step / 2, v_step)
        currents: list[float] = []
        for v in voltages:
            self._set_contact_voltage(anode_contact, float(v))
            self._solve_dc()
            currents.append(self._get_contact_current(measure))
        return voltages.tolist(), currents

    def contact_current_A_per_cm(self, contact: str) -> float:
        """Read conventional current entering a contact at the last DD solution.

        Requires a successful ``solve_equilibrium`` or ``iv_sweep`` first.
        Photovoltaic power delivery has negative current at its positive terminal.
        """
        if not self._initialized:
            raise RuntimeError("Solve the device before reading contact current")
        if contact not in self._contact_regions:
            raise KeyError(f"Unknown contact: {contact}")
        return self._get_contact_current(contact)

    # ------------------------------------------------------------------
    # Mesh conversion
    # ------------------------------------------------------------------
    def _convert_meshfield(self) -> None:
        ds = self._ds
        mf = self.mf
        from .optical import GENERATION_FIELD
        generation = np.asarray(mf.grid.point_data.get(
            GENERATION_FIELD, np.zeros(mf.n_points)), dtype=float)
        if (generation.shape != (mf.n_points,) or np.any(~np.isfinite(generation))
                or np.any(generation < 0)):
            raise ValueError(f"{GENERATION_FIELD} must be finite, non-negative and nodal")

        import pyvista as pv
        if not np.all(np.asarray(mf.grid.celltypes) == pv.CellType.TRIANGLE):
            raise NotImplementedError(
                "DeviceSolver currently supports only 2D triangle meshes. "
                f"Found cell types: {set(mf.grid.celltypes.tolist())}"
            )

        pts_cm = np.asarray(mf.points, dtype=float) * 1e-4
        coords_flat = pts_cm.flatten().tolist()

        cells = mf.grid.cells.reshape(-1, 4)[:, 1:].astype(int)   # (n_cells, 3)
        mat_ids = np.asarray(mf.material_ids, dtype=np.int32)
        unique_mats = sorted({int(m) for m in mat_ids})

        region_names = {m: Material(m).name for m in unique_mats}
        contact_names = [c.name for c in mf.contacts]

        # Identify edges shared by two cells of *different* materials —
        # these are interior interfaces (Si/SiO2, SiO2/PolySi, ...).
        # Boundary edges (count == 1) are candidates for contacts.
        edge_count: dict[tuple[int, int], int] = {}
        edge_region: dict[tuple[int, int], int] = {}
        edge_other_region: dict[tuple[int, int], int] = {}
        for tri, mid in zip(cells, mat_ids):
            t0, t1, t2 = int(tri[0]), int(tri[1]), int(tri[2])
            mid_i = int(mid)
            for a, b in ((t0, t1), (t1, t2), (t2, t0)):
                e = (a, b) if a < b else (b, a)
                edge_count[e] = edge_count.get(e, 0) + 1
                if e not in edge_region:
                    edge_region[e] = mid_i
                elif edge_region[e] != mid_i:
                    edge_other_region[e] = mid_i
        boundary_edges = {e for e, c in edge_count.items() if c == 1}
        interface_edges_by_pair: dict[tuple[int, int], list] = {}
        for e in edge_other_region:
            a_mat, b_mat = sorted((edge_region[e], edge_other_region[e]))
            interface_edges_by_pair.setdefault((a_mat, b_mat), []).append(e)

        interface_phys_names = {
            pair: f"if_{Material(pair[0]).name}_{Material(pair[1]).name}"
            for pair in interface_edges_by_pair
        }

        # In-memory create_gmsh_mesh expects alphabetically-sorted physical
        # names (pythonmesh.read_gmsh_file sorts by name before indexing).
        physical_names = sorted(list(region_names.values()) + contact_names
                                + list(interface_phys_names.values()))
        name_to_idx = {n: i for i, n in enumerate(physical_names)}

        elements: list[int] = []
        for tri, mid in zip(cells, mat_ids):
            pn = name_to_idx[Material(int(mid)).name]
            elements.extend([2, pn, int(tri[0]), int(tri[1]), int(tri[2])])

        # Emit interface line elements. Each interface edge appears in two
        # triangles (different materials); emit it once under its interface
        # physical name. The "owning" region for the line element is one of
        # the two — pythonmesh sorts physical names so either is fine; pick
        # the alphabetically-lower material name to be deterministic.
        for pair, edges in interface_edges_by_pair.items():
            pn = name_to_idx[interface_phys_names[pair]]
            for e in edges:
                elements.extend([1, pn, e[0], e[1]])

        contact_region: dict[str, str] = {}
        for contact in mf.contacts:
            node_set = {int(n) for n in contact.boundary_nodes}
            pn = name_to_idx[contact.name]
            matched = 0
            for e in boundary_edges:
                if e[0] in node_set and e[1] in node_set:
                    elements.extend([1, pn, e[0], e[1]])
                    contact_region.setdefault(
                        contact.name, Material(edge_region[e]).name)
                    matched += 1
            if matched == 0:
                warnings.warn(
                    f"Contact '{contact.name}': no mesh boundary edges span "
                    f"its {len(node_set)} node(s); contact will be skipped.")

        ds.create_gmsh_mesh(mesh=self._mesh_name,
                            coordinates=coords_flat,
                            physical_names=physical_names,
                            elements=elements)
        for m in unique_mats:
            rname = Material(m).name
            display = MATERIAL_NAMES.get(Material(m), rname)
            ds.add_gmsh_region(mesh=self._mesh_name, gmsh_name=rname,
                               region=rname, material=display)
            self._region_materials[rname] = Material(m)
            try:
                p = self._params_for_region(Material(m))
                self._region_is_insulator[rname] = p.is_insulator
            except KeyError:
                self._region_is_insulator[rname] = False
        for cname, rname in contact_region.items():
            ds.add_gmsh_contact(mesh=self._mesh_name, gmsh_name=cname,
                                region=rname, name=cname, material="metal")
            self._contact_regions[cname] = rname
        for pair, _ in interface_edges_by_pair.items():
            if_name = interface_phys_names[pair]
            r0, r1 = Material(pair[0]).name, Material(pair[1]).name
            ds.add_gmsh_interface(mesh=self._mesh_name, gmsh_name=if_name,
                                  region0=r0, region1=r1, name=if_name)
            self._interfaces.append((if_name, r0, r1))

        ds.finalize_mesh(mesh=self._mesh_name)
        ds.create_device(mesh=self._mesh_name, device=self._device_name)

        # Populate Nd/Na/NetDoping per region. DEVSIM may re-order nodes per
        # region, so match region coordinates to MeshField nodes via KD-tree.
        # Insulator regions still get NetDoping (= 0) so Poisson can reference
        # it without a missing-model error.
        mf_pts_um = np.asarray(mf.points, dtype=float)[:, :2]
        tree = cKDTree(mf_pts_um)
        for region in self._region_materials:
            x_cm = np.asarray(
                ds.get_node_model_values(device=self._device_name,
                                         region=region, name="x"))
            y_cm = np.asarray(
                ds.get_node_model_values(device=self._device_name,
                                         region=region, name="y"))
            pts_um = np.column_stack([x_cm, y_cm]) * 1e4
            _, idx = tree.query(pts_um)
            if self._region_is_insulator.get(region, False):
                nd = np.zeros(len(idx))
                na = np.zeros(len(idx))
            else:
                nd = mf.Nd[idx]
                na = mf.Na[idx]
            for name, vals in (("Donors", nd), ("Acceptors", na),
                               ("NetDoping", nd - na),
                               ("OpticalGeneration", np.zeros(len(idx))
                                if self._region_is_insulator.get(region, False)
                                else generation[idx])):
                ds.node_solution(device=self._device_name, region=region,
                                 name=name)
                ds.set_node_values(device=self._device_name, region=region,
                                   name=name,
                                   values=np.asarray(vals, dtype=float).tolist())

    # ------------------------------------------------------------------
    # Equation setup
    # ------------------------------------------------------------------
    def _setup_equations(self) -> None:
        for region, mat in self._region_materials.items():
            params = self._params_for_region(mat)
            self._set_region_parameters(region, params)
            if self._region_is_insulator.get(region, False):
                self._build_insulator_potential(region)
            else:
                # BGN and statistics both need to be attached before
                # _build_potential_only: BGN so IntrinsicElectrons/Holes
                # / PotentialIntrinsicNodeCharge can refer to n_i_eff;
                # statistics so those same expressions can reference
                # N_c/N_v (Blakemore/FD) as needed. Their defaults
                # (NoBGN, Boltzmann) are no-ops.
                self.physics.bgn.attach(
                    self._ds, self._device_name, region, params, self.T)
                self.physics.statistics.attach(
                    self._ds, self._device_name, region, params, self.T)
                self._build_potential_only(region, params)
        for contact in self._contact_regions:
            self._build_contact_potential_equation(contact)
        for if_name, r0, r1 in self._interfaces:
            self._build_interface_continuity(if_name, "Potential")

    def _attach_mobility_models(self) -> None:
        """Register the configured mobility model on every semiconductor
        region. Called after the equilibrium Poisson-only solve so the
        Klaassen-style models (which reference Electrons/Holes seeded from
        the equilibrium) see sane values."""
        for region, mat in self._region_materials.items():
            if self._region_is_insulator.get(region, False):
                continue
            params = self._params_for_region(mat)
            self.physics.mobility.attach(
                self._ds, self._device_name, region, params, self.T)

    def _attach_recombination_models(self, region: str,
                                     params: MaterialParams) -> str:
        """Attach every configured recombination model on `region` and
        return the symbolic sum of their term_names (so the continuity
        equation can use it as its node_model). Empty list ⇒ '0'."""
        n_i_expr = self.physics.bgn.n_i_expr()
        for model in self.physics.recombination:
            model.attach(self._ds, self._device_name, region, params, self.T,
                         n_i_expr=n_i_expr)
        names = [m.term_name for m in self.physics.recombination]
        return " + ".join(names) if names else "0"

    def _params_for_region(self, mat: Material) -> MaterialParams:
        display = MATERIAL_NAMES.get(mat, mat.name)
        for key in (display, mat.name):
            if key in self.mat_params:
                return self.mat_params[key]
        raise KeyError(
            f"No MaterialParams provided for {mat.name} / {display}. "
            f"Available keys: {list(self.mat_params)}")

    def _set_region_parameters(self, region: str, p: MaterialParams) -> None:
        ds = self._ds
        V_t = KB_J * self.T / Q_C
        pairs = {
            "Permittivity": p.band_structure.permittivity_relative * EPS0_F_CM,
            "ElectronCharge": Q_C,
            "n_i": p.band_structure.ni_cm3_300K,
            "V_t": V_t,
        }
        for name, value in pairs.items():
            ds.set_parameter(device=self._device_name, region=region,
                             name=name, value=float(value))

    def _build_potential_only(self, region: str,
                              params: MaterialParams) -> None:
        """Create Potential solution + Poisson equation (intrinsic charge).

        After solve_equilibrium() switches to DD, PotentialEquation is rebuilt
        against PotentialNodeCharge (which uses Electrons/Holes as unknowns).
        """
        ds = self._ds
        device = self._device_name

        ds.node_solution(device=device, region=region, name="Potential")
        ds.edge_from_node_model(device=device, region=region,
                                node_model="Potential")

        for name, eq in (
            ("EField", "(Potential@n0 - Potential@n1)*EdgeInverseLength"),
            ("EField:Potential@n0", "EdgeInverseLength"),
            ("EField:Potential@n1", "-EdgeInverseLength"),
            ("PotentialEdgeFlux", "Permittivity*EField"),
            ("PotentialEdgeFlux:Potential@n0",
             "Permittivity*EdgeInverseLength"),
            ("PotentialEdgeFlux:Potential@n1",
             "-Permittivity*EdgeInverseLength"),
        ):
            ds.edge_model(device=device, region=region, name=name, equation=eq)

        # Intrinsic carrier node models (used as initial guess + Poisson source).
        # Use DEVSIM's symbolic diff() to avoid hand-derivative bugs.
        # `ni` is either "n_i" (parameter, no BGN) or "n_i_eff" (node
        # model registered by the BGN model, doping-dependent).
        # The statistics model wraps the Boltzmann-form n_boltz / p_boltz
        # with FD corrections when active — a no-op for Boltzmann.
        ni = self.physics.bgn.n_i_expr()
        stats = self.physics.statistics
        n_boltz = f"{ni}*exp(Potential/V_t)"
        p_boltz = f"({ni})^2/IntrinsicElectrons"
        n_expr = stats.wrap_electron_density(n_boltz, params)
        p_expr = stats.wrap_hole_density(p_boltz, params)
        for name, eq in (
            ("IntrinsicElectrons", n_expr),
            ("IntrinsicElectrons:Potential",
             f"simplify(diff({n_expr}, Potential))"),
            ("IntrinsicHoles", p_expr),
            ("IntrinsicHoles:Potential",
             f"simplify(diff({p_expr}, Potential))"),
            ("IntrinsicCharge",
             "IntrinsicHoles - IntrinsicElectrons + NetDoping"),
            ("IntrinsicCharge:Potential",
             "diff(IntrinsicHoles - IntrinsicElectrons, Potential)"),
            ("PotentialIntrinsicNodeCharge",
             "-ElectronCharge*IntrinsicCharge"),
            ("PotentialIntrinsicNodeCharge:Potential",
             "diff(-ElectronCharge*IntrinsicCharge, Potential)"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        # DD-mode node charge (active once Electrons/Holes are solutions)
        ds.node_solution(device=device, region=region, name="Electrons")
        ds.edge_from_node_model(device=device, region=region,
                                node_model="Electrons")
        ds.node_solution(device=device, region=region, name="Holes")
        ds.edge_from_node_model(device=device, region=region,
                                node_model="Holes")
        for name, eq in (
            ("PotentialNodeCharge",
             "-ElectronCharge*(Holes - Electrons + NetDoping)"),
            ("PotentialNodeCharge:Electrons", "ElectronCharge"),
            ("PotentialNodeCharge:Holes", "-ElectronCharge"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        # Poisson only (replaced later)
        ds.equation(device=device, region=region, name="PotentialEquation",
                    variable_name="Potential",
                    node_model="PotentialIntrinsicNodeCharge",
                    edge_model="PotentialEdgeFlux",
                    variable_update="log_damp")

    def _build_insulator_potential(self, region: str) -> None:
        """Poisson-only region (SiO2, Si3N4). No carriers — fixed-charge
        equation uses NetDoping (typically 0 in oxide)."""
        ds = self._ds
        device = self._device_name

        ds.node_solution(device=device, region=region, name="Potential")
        ds.edge_from_node_model(device=device, region=region,
                                node_model="Potential")

        for name, eq in (
            ("EField", "(Potential@n0 - Potential@n1)*EdgeInverseLength"),
            ("EField:Potential@n0", "EdgeInverseLength"),
            ("EField:Potential@n1", "-EdgeInverseLength"),
            ("PotentialEdgeFlux", "Permittivity*EField"),
            ("PotentialEdgeFlux:Potential@n0",
             "Permittivity*EdgeInverseLength"),
            ("PotentialEdgeFlux:Potential@n1",
             "-Permittivity*EdgeInverseLength"),
        ):
            ds.edge_model(device=device, region=region, name=name, equation=eq)

        for name, eq in (
            ("PotentialNodeCharge", "-ElectronCharge*NetDoping"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        ds.equation(device=device, region=region, name="PotentialEquation",
                    variable_name="Potential",
                    node_model="PotentialNodeCharge",
                    edge_model="PotentialEdgeFlux",
                    variable_update="log_damp")

    def _build_interface_continuity(self, if_name: str, variable: str) -> None:
        """Enforce `variable@r0 == variable@r1` across the interface."""
        ds = self._ds
        device = self._device_name
        mname = f"continuous{variable}"
        ds.interface_model(device=device, interface=if_name, name=mname,
                           equation=f"{variable}@r0 - {variable}@r1")
        ds.interface_model(device=device, interface=if_name,
                           name=f"{mname}:{variable}@r0", equation="1")
        ds.interface_model(device=device, interface=if_name,
                           name=f"{mname}:{variable}@r1", equation="-1")
        # Map "PotentialEquation" → "PotentialEquation", etc.
        eq_name = f"{variable}Equation" if variable == "Potential" \
            else f"{variable}ContinuityEquation"
        ds.interface_equation(device=device, interface=if_name, name=eq_name,
                              interface_model=mname, type="continuous")

    def _build_continuity_equations(self, region: str) -> None:
        ds = self._ds
        device = self._device_name

        # Scharfetter-Gummel current densities on edges.
        for name, eq in (
            ("vdiff", "(Potential@n0 - Potential@n1)/V_t"),
            ("vdiff:Potential@n0", "1/V_t"),
            ("vdiff:Potential@n1", "-1/V_t"),
            ("Bern01", "B(vdiff)"),
            ("Bern01:Potential@n0", "dBdx(vdiff)*vdiff:Potential@n0"),
            ("Bern01:Potential@n1", "dBdx(vdiff)*vdiff:Potential@n1"),
            ("Bern10", "Bern01 + vdiff"),
            ("Bern10:Potential@n0",
             "Bern01:Potential@n0 + vdiff:Potential@n0"),
            ("Bern10:Potential@n1",
             "Bern01:Potential@n1 + vdiff:Potential@n1"),
        ):
            ds.edge_model(device=device, region=region, name=name, equation=eq)

        # Mobility expressions come from self.physics.mobility — inlined
        # into the current density (rather than wrapped in an edge_model)
        # so the constant case reduces to the original solver expression
        # exactly. Carrier-dependent models (Klaassen) need cross
        # derivatives (J_n vs Holes, J_p vs Electrons); the constant case
        # doesn't, and adding 0-valued cross terms perturbs the Jacobian.
        mu_n_e = self.physics.mobility.mu_n_expr()
        mu_p_e = self.physics.mobility.mu_p_expr()
        coupled = self.physics.mobility.requires_carriers

        Jn = (f"ElectronCharge*{mu_n_e}*EdgeInverseLength*V_t*"
              "(Electrons@n1*Bern10 - Electrons@n0*Bern01)")
        jn_models = [
            ("ElectronCurrent", Jn),
            ("ElectronCurrent:Electrons@n0",
             f"simplify(diff({Jn}, Electrons@n0))"),
            ("ElectronCurrent:Electrons@n1",
             f"simplify(diff({Jn}, Electrons@n1))"),
            ("ElectronCurrent:Potential@n0",
             f"simplify(diff({Jn}, Potential@n0))"),
            ("ElectronCurrent:Potential@n1",
             f"simplify(diff({Jn}, Potential@n1))"),
        ]
        if coupled:
            jn_models += [
                ("ElectronCurrent:Holes@n0",
                 f"simplify(diff({Jn}, Holes@n0))"),
                ("ElectronCurrent:Holes@n1",
                 f"simplify(diff({Jn}, Holes@n1))"),
            ]
        for name, eq in jn_models:
            ds.edge_model(device=device, region=region, name=name, equation=eq)

        Jp = (f"-ElectronCharge*{mu_p_e}*EdgeInverseLength*V_t*"
              "(Holes@n1*Bern01 - Holes@n0*Bern10)")
        jp_models = [
            ("HoleCurrent", Jp),
            ("HoleCurrent:Holes@n0", f"simplify(diff({Jp}, Holes@n0))"),
            ("HoleCurrent:Holes@n1", f"simplify(diff({Jp}, Holes@n1))"),
            ("HoleCurrent:Potential@n0", f"simplify(diff({Jp}, Potential@n0))"),
            ("HoleCurrent:Potential@n1", f"simplify(diff({Jp}, Potential@n1))"),
        ]
        if coupled:
            jp_models += [
                ("HoleCurrent:Electrons@n0",
                 f"simplify(diff({Jp}, Electrons@n0))"),
                ("HoleCurrent:Electrons@n1",
                 f"simplify(diff({Jp}, Electrons@n1))"),
            ]
        for name, eq in jp_models:
            ds.edge_model(device=device, region=region, name=name, equation=eq)

        # Time-node models (zero for DC, but equation() requires them)
        for name, eq in (
            ("NCharge", "-ElectronCharge*Electrons"),
            ("NCharge:Electrons", "-ElectronCharge"),
            ("PCharge", "ElectronCharge*Holes"),
            ("PCharge:Holes", "ElectronCharge"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        # Recombination — sum every model registered in
        # self.physics.recombination. Each model's term_name node_model
        # holds its contribution (with carrier derivatives). The composite
        # `URec` node_model is what the continuity equation actually sees.
        params = self._params_for_region(self._region_materials[region])
        rec_sum = self._attach_recombination_models(region, params)
        for name, eq in (
            ("URec", rec_sum),
            ("URec:Electrons",
             " + ".join(f"{m.term_name}:Electrons"
                        for m in self.physics.recombination) or "0"),
            ("URec:Holes",
             " + ".join(f"{m.term_name}:Holes"
                        for m in self.physics.recombination) or "0"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        # URec is -qR by the RecombinationModel contract. Electron and
        # hole sources MUST have opposite signs so pair creation/destruction
        # conserves charge. G is prescribed and has no carrier derivatives.
        for name, eq in (
            ("ElectronSource", "URec + ElectronCharge*OpticalGeneration"),
            ("HoleSource", "-URec - ElectronCharge*OpticalGeneration"),
            ("ElectronSource:Electrons", "URec:Electrons"),
            ("ElectronSource:Holes", "URec:Holes"),
            ("HoleSource:Electrons", "-URec:Electrons"),
            ("HoleSource:Holes", "-URec:Holes"),
        ):
            ds.node_model(device=device, region=region, name=name, equation=eq)

        ds.equation(device=device, region=region,
                    name="ElectronContinuityEquation",
                    variable_name="Electrons", edge_model="ElectronCurrent",
                    variable_update="positive",
                    time_node_model="NCharge", node_model="ElectronSource")
        ds.equation(device=device, region=region,
                    name="HoleContinuityEquation",
                    variable_name="Holes", edge_model="HoleCurrent",
                    variable_update="positive",
                    time_node_model="PCharge", node_model="HoleSource")

    # ------------------------------------------------------------------
    # Contact BCs
    # ------------------------------------------------------------------
    def _contact_tag(self, contact_name: str):
        """Look up the ContactTag object by name so we can read
        contact_type and work_function_eV."""
        for c in self.mf.contacts:
            if c.name == contact_name:
                return c
        return None

    def _build_contact_potential_equation(self, contact: str) -> None:
        ds = self._ds
        device = self._device_name
        region = self._contact_regions[contact]
        biasname = f"{contact}bias"
        ds.set_parameter(device=device, region=region, name=biasname,
                         value=0.0)

        pot_name = f"{contact}nodemodel"
        if self._region_is_insulator.get(region, False):
            # Metal-on-insulator: Potential pinned to bias, minus a
            # flat-band shift that encodes fixed oxide charge Qf, midgap
            # Dit-driven Vfb offset, and phi_MS in one compact-model
            # number. Follow-up: implement proper interface-Poisson
            # surface-charge for a physically-located Qf.
            tag = self._contact_tag(contact)
            vfb = 0.0 if tag is None else float(tag.flat_band_shift_V)
            vfb_name = f"{contact}_vfb"
            ds.set_parameter(device=device, region=region,
                             name=vfb_name, value=vfb)
            ds.contact_node_model(device=device, contact=contact,
                                  name=pot_name,
                                  equation=f"Potential-{biasname}+{vfb_name}")
            ds.contact_node_model(device=device, contact=contact,
                                  name=f"{pot_name}:Potential", equation="1")
            ds.contact_equation(device=device, contact=contact,
                                name="PotentialEquation",
                                node_model=pot_name)
            return

        tag = self._contact_tag(contact)
        if tag is not None and tag.contact_type == "schottky":
            self._build_schottky_potential(contact, region, biasname,
                                           pot_name, tag)
            return

        cemod = f"celec_{contact}"
        chmod = f"chole_{contact}"
        # Equilibrium carrier densities at the contact (ohmic assumption).
        # `ni` is n_i (parameter) or n_i_eff (BGN node model on the region).
        # The built-in potential offset V_t*log(n/n_i) is statistics-aware
        # (Boltzmann is a pass-through; FermiDirac adds the Blakemore
        # correction so the equilibrium Vbi is consistent with the
        # wrapped IntrinsicElectrons/Holes in the bulk).
        ni = self.physics.bgn.n_i_expr()
        stats = self.physics.statistics
        params = self._params_for_region(self._region_materials[region])
        ds.contact_node_model(
            device=device, contact=contact, name=cemod,
            equation=f"1e-10 + 0.5*(NetDoping + (NetDoping^2 + 4*({ni})^2)^(0.5))")
        ds.contact_node_model(
            device=device, contact=contact, name=chmod,
            equation=f"1e-10 + 0.5*(-NetDoping + (NetDoping^2 + 4*({ni})^2)^(0.5))")

        n_offset = stats.electron_potential_offset(cemod, ni, params)
        p_offset = stats.hole_potential_offset(chmod, ni, params)
        ds.contact_node_model(
            device=device, contact=contact, name=pot_name,
            equation=(f"ifelse(NetDoping > 0,"
                      f" Potential-{biasname}-({n_offset}),"
                      f" Potential-{biasname}+({p_offset}))"))
        ds.contact_node_model(device=device, contact=contact,
                              name=f"{pot_name}:Potential", equation="1")

        ds.contact_equation(device=device, contact=contact,
                            name="PotentialEquation",
                            node_model=pot_name)

    def _build_schottky_potential(self, contact: str, region: str,
                                  biasname: str, pot_name: str, tag) -> None:
        """Schottky metal-semiconductor barrier.

        Barrier for electrons: phi_Bn = phi_M - chi
        Pinned electron density: n_sc = Nc * exp(-phi_Bn / V_t)
        Pinned hole density: p_sc = n_i^2 / n_sc  (mass-action, consistent
            because phi_Bn + phi_Bp = Eg and Nc*Nv*exp(-Eg/V_t) = n_i^2)

        Potential BC: Potential = V_applied - V_t*log(n_sc / n_i) — same
        form as ohmic n-side but with n_sc replacing the equilibrium
        electron density from doping.
        """
        ds = self._ds
        device = self._device_name

        if tag.work_function_eV is None:
            raise ValueError(
                f"Schottky contact '{contact}' needs work_function_eV set.")

        mat = self._region_materials[region]
        params = self._params_for_region(mat)
        chi = params.band_structure.electron_affinity_eV
        Nc = params.band_structure.Nc_cm3_300K
        phi_Bn = tag.work_function_eV - chi
        if phi_Bn <= 0:
            warnings.warn(
                f"Schottky contact '{contact}': phi_Bn = {phi_Bn:.3f} eV <= 0. "
                f"phi_M ({tag.work_function_eV} eV) - chi ({chi} eV) gives "
                f"no barrier; behaves as ohmic.")

        # Register as contact-scoped parameters so we can inspect them.
        ds.set_parameter(device=device, region=region,
                         name=f"{contact}_phiBn", value=float(phi_Bn))
        ds.set_parameter(device=device, region=region,
                         name=f"{contact}_Nc", value=float(Nc))

        ni = self.physics.bgn.n_i_expr()
        n_sc_expr = f"{contact}_Nc * exp(-{contact}_phiBn/V_t)"

        ds.contact_node_model(
            device=device, contact=contact,
            name=f"n_schottky_{contact}", equation=n_sc_expr)
        ds.contact_node_model(
            device=device, contact=contact,
            name=f"p_schottky_{contact}",
            equation=f"({ni})^2 / n_schottky_{contact}")

        ds.contact_node_model(
            device=device, contact=contact, name=pot_name,
            equation=(f"Potential-{biasname}"
                      f" - V_t*log(n_schottky_{contact}/({ni}))"))
        ds.contact_node_model(device=device, contact=contact,
                              name=f"{pot_name}:Potential", equation="1")

        ds.contact_equation(device=device, contact=contact,
                            name="PotentialEquation",
                            node_model=pot_name)

    def _build_contact_dd_equations(self, contact: str) -> None:
        ds = self._ds
        device = self._device_name
        ni = self.physics.bgn.n_i_expr()

        tag = self._contact_tag(contact)
        e_name = f"{contact}nodeelectrons"
        h_name = f"{contact}nodeholes"

        if tag is not None and tag.contact_type == "schottky":
            # Carriers pinned to the barrier-set concentrations, independent
            # of doping (metal is the reservoir).
            ds.contact_node_model(
                device=device, contact=contact, name=e_name,
                equation=f"Electrons - n_schottky_{contact}")
            ds.contact_node_model(
                device=device, contact=contact, name=h_name,
                equation=f"Holes - p_schottky_{contact}")
        else:
            cemod = f"celec_{contact}"
            chmod = f"chole_{contact}"
            ds.contact_node_model(
                device=device, contact=contact, name=e_name,
                equation=(f"ifelse(NetDoping > 0,"
                          f" Electrons - {cemod},"
                          f" Electrons - ({ni})^2/{chmod})"))
            ds.contact_node_model(
                device=device, contact=contact, name=h_name,
                equation=(f"ifelse(NetDoping < 0,"
                          f" Holes - {chmod},"
                          f" Holes - ({ni})^2/{cemod})"))

        ds.contact_node_model(device=device, contact=contact,
                              name=f"{e_name}:Electrons", equation="1.0")
        ds.contact_node_model(device=device, contact=contact,
                              name=f"{h_name}:Holes", equation="1.0")

        ds.contact_equation(device=device, contact=contact,
                            name="ElectronContinuityEquation",
                            node_model=e_name,
                            edge_current_model="ElectronCurrent")
        ds.contact_equation(device=device, contact=contact,
                            name="HoleContinuityEquation",
                            node_model=h_name,
                            edge_current_model="HoleCurrent")

    # ------------------------------------------------------------------
    # Solve helpers
    # ------------------------------------------------------------------
    def _set_contact_voltage(self, contact: str, voltage: float) -> None:
        region = self._contact_regions[contact]
        self._ds.set_parameter(device=self._device_name, region=region,
                               name=f"{contact}bias", value=float(voltage))

    def _solve_dc(self) -> None:
        self._ds.solve(type="dc", absolute_error=1e10, relative_error=1e-7,
                       maximum_iterations=50)

    def _get_contact_current(self, contact: str) -> float:
        ecurr = self._ds.get_contact_current(
            contact=contact, equation="ElectronContinuityEquation",
            device=self._device_name)
        hcurr = self._ds.get_contact_current(
            contact=contact, equation="HoleContinuityEquation",
            device=self._device_name)
        return float(ecurr + hcurr)
