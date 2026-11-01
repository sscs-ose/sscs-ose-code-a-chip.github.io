"""
opentcad/geometry/structure.py — Semiconductor geometry DSL.

The Structure class defines a device cross-section as an ordered layer stack
with optional rectangular region overrides and named contacts.
Produces a MeshField via to_meshfield().

Example:
    s = Structure(width_um=2.0, name="nmos")
    s.add_substrate("body", 1.0, Material.SI, doping_Na=1e15)
    s.add_layer("gate_oxide", 0.005, Material.SIO2)
    s.add_layer("poly", 0.15, Material.POLY_SI, doping_Nd=1e20)
    s.add_contact("gate", 0.0, 2.0, "poly", surface="top")
    s.add_contact("body", 0.0, 2.0, "body", surface="bottom")
    mf = s.to_meshfield(mesh_size_um=0.02)
"""
from __future__ import annotations
import warnings
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from .formats import ContactTag, Material, MeshField, ProcessStep


@dataclass
class LayerSpec:
    name: str
    thickness_um: float
    material: Material
    doping_Na: float = 0.0   # [cm^-3]
    doping_Nd: float = 0.0   # [cm^-3]
    y_bottom: float = 0.0    # set during build


@dataclass
class RegionSpec:
    """Rectangular sub-region overriding layer material/doping."""
    name: str
    x_start: float; x_end: float
    y_start: float; y_end: float
    material: Material
    doping_Na: float = 0.0
    doping_Nd: float = 0.0


@dataclass
class ContactSpec:
    name: str
    x_start: float; x_end: float
    layer_name: str
    surface: str = "top"   # "top" or "bottom"
    contact_type: str = "ohmic"
    work_function_eV: Optional[float] = None
    flat_band_shift_V: float = 0.0   # metal-on-insulator Vfb shift


class Structure:
    """Semiconductor device structure builder (DSL).

    Coordinate system: x=horizontal [0..width_um], y=vertical [0..total_height].
    All coordinates in micrometers.
    """

    def __init__(self, width_um: float, name: str = "structure"):
        self.width_um = width_um
        self.name = name
        self._layers: list[LayerSpec] = []
        self._regions: list[RegionSpec] = []
        self._contacts: list[ContactSpec] = []

    def add_substrate(self, name: str, thickness_um: float,
                      material: Material = Material.SI,
                      doping_Na: float = 0.0, doping_Nd: float = 0.0) -> "Structure":
        """Add the bottommost substrate layer. Must be called before add_layer()."""
        if self._layers:
            raise ValueError("add_substrate() must be first. Use add_layer() after.")
        return self._add(name, thickness_um, material, doping_Na, doping_Nd)

    def add_layer(self, name: str, thickness_um: float, material: Material,
                  doping_Na: float = 0.0, doping_Nd: float = 0.0) -> "Structure":
        """Add a layer on top of the stack."""
        if not self._layers:
            raise ValueError("Call add_substrate() before add_layer().")
        return self._add(name, thickness_um, material, doping_Na, doping_Nd)

    def _add(self, name, thickness_um, material, doping_Na, doping_Nd):
        if thickness_um <= 0:
            raise ValueError(f"Layer '{name}' thickness must be > 0, got {thickness_um}")
        if any(l.name == name for l in self._layers):
            raise ValueError(f"Duplicate layer name '{name}'")
        self._layers.append(LayerSpec(name, thickness_um, material, doping_Na, doping_Nd))
        return self

    def add_region(self, name: str, x_start: float, x_end: float,
                   y_start: float, y_end: float, material: Material,
                   doping_Na: float = 0.0, doping_Nd: float = 0.0) -> "Structure":
        """Override material in a rectangular region. Later calls take precedence."""
        if x_start >= x_end or y_start >= y_end:
            raise ValueError(f"Region '{name}': start must be < end on both axes")
        self._regions.append(RegionSpec(name, x_start, x_end, y_start, y_end,
                                         material, doping_Na, doping_Nd))
        return self

    def add_contact(self, name: str, x_start: float, x_end: float,
                    layer_name: str, surface: str = "top",
                    contact_type: str = "ohmic",
                    work_function_eV: Optional[float] = None,
                    flat_band_shift_V: float = 0.0) -> "Structure":
        """Define a named electrical contact on a layer surface.

        `flat_band_shift_V` applies only to metal-on-insulator contacts
        (typically the gate on an oxide). It packs fixed oxide charge Qf,
        midgap Dit-driven Vfb offset, and metal-semi work-function
        differences into a single compact-model number so a MOS-cap or
        MOSFET can hit a target Vth without invoking the full interface-
        Poisson surface-charge machinery."""
        self._contacts.append(ContactSpec(name, x_start, x_end, layer_name,
                                           surface, contact_type,
                                           work_function_eV,
                                           flat_band_shift_V))
        return self

    @property
    def total_height_um(self) -> float:
        return sum(l.thickness_um for l in self._layers)

    def to_meshfield(self, mesh_size_um: float = 0.05) -> MeshField:
        """Generate mesh and return a MeshField. This is the DSL exit point.

        Args:
            mesh_size_um: Default element size [um]. Automatically refined at
                          material interfaces to mesh_size_um / 2.

        Returns:
            MeshField with material tags, doping from layer/region specs, and contacts.
        """
        if not self._layers:
            raise ValueError("No layers defined. Call add_substrate() first.")

        # Assign y_bottom to each layer
        y = 0.0
        for layer in self._layers:
            layer.y_bottom = y
            y += layer.thickness_um

        from .mesh import build_2d_mesh   # imported here to isolate gmsh dependency
        grid = build_2d_mesh(self, mesh_size_um=mesh_size_um)

        # Assign doping from layer specs, then region overrides
        pts = grid.points   # [um], shape (N, 3)
        nd = np.zeros(grid.n_points)
        na = np.zeros(grid.n_points)

        # First match wins. Layers iterate bottom-up, so a point exactly on
        # an internal interface is claimed by the lower layer. The top-of-
        # device boundary (y == total_height) needs <= on the upper bound,
        # otherwise the top-contact nodes get zero doping and ohmic BCs fail.
        for i, pt in enumerate(pts):
            x, y_pt = pt[0], pt[1]
            for layer in self._layers:
                if layer.y_bottom <= y_pt <= layer.y_bottom + layer.thickness_um:
                    nd[i] = layer.doping_Nd
                    na[i] = layer.doping_Na
                    break
            # Region overrides (last match wins)
            for reg in self._regions:
                if reg.x_start <= x <= reg.x_end and reg.y_start <= y_pt <= reg.y_end:
                    nd[i] = reg.doping_Nd
                    na[i] = reg.doping_Na

        grid.point_data["Nd"] = nd
        grid.point_data["Na"] = na

        contacts = self._resolve_contacts(grid)

        return MeshField(
            grid=grid,
            contacts=contacts,
            process_history=[ProcessStep("structure_definition",
                                          parameters={"name": self.name})],
            metadata={"structure_name": self.name,
                      "width_um": self.width_um,
                      "total_height_um": self.total_height_um},
        )

    def _resolve_contacts(self, grid) -> list[ContactTag]:
        pts = grid.points
        tol = 0.001   # 1 nm
        contacts = []
        for cs in self._contacts:
            layer = next((l for l in self._layers if l.name == cs.layer_name), None)
            if layer is None:
                warnings.warn(f"Contact '{cs.name}': unknown layer '{cs.layer_name}'")
                continue
            y_c = layer.y_bottom + layer.thickness_um if cs.surface == "top" else layer.y_bottom
            mask = ((np.abs(pts[:, 1] - y_c) < tol) &
                    (pts[:, 0] >= cs.x_start - tol) &
                    (pts[:, 0] <= cs.x_end + tol))
            node_ids = np.where(mask)[0]
            if len(node_ids) == 0:
                warnings.warn(f"Contact '{cs.name}': no nodes matched at y={y_c:.4f} um")
                continue
            contacts.append(ContactTag(cs.name, node_ids, cs.contact_type,
                                       cs.work_function_eV,
                                       cs.flat_band_shift_V))
        return contacts

    def __repr__(self):
        layers = ", ".join(f"{l.name}({l.thickness_um}um)" for l in self._layers)
        return f"Structure('{self.name}', w={self.width_um}um, [{layers}])"
