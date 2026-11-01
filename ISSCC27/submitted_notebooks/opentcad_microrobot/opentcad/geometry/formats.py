"""
opentcad/geometry/formats.py — Central MeshField data format.
Units: spatial=um, concentration=cm^-3, temperature=K, energy=eV
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional
import numpy as np
import pyvista as pv


class Material(IntEnum):
    VACUUM=0; SI=1; SIO2=2; SI3N4=3; POLY_SI=4; AL=5
    PHOTORESIST=6; SIGE=7; GAN=8; SIC=9; SUBSTRATE=10

MATERIAL_NAMES = {
    Material.SI:"Silicon", Material.SIO2:"SiO2", Material.SI3N4:"Si3N4",
    Material.POLY_SI:"PolySi", Material.AL:"Aluminum",
    Material.PHOTORESIST:"Photoresist", Material.SIGE:"SiGe",
    Material.GAN:"GaN", Material.SIC:"SiC", Material.SUBSTRATE:"Substrate",
}

@dataclass
class ContactTag:
    name: str
    boundary_nodes: np.ndarray
    contact_type: str = "ohmic"
    work_function_eV: Optional[float] = None
    #: Metal-on-insulator flat-band shift [V] — used to encode fixed oxide
    #: charge Qf, midgap Dit-driven Vfb offset, and metal-semi work-function
    #: differences on a gate contact in one compact-model number:
    #:     Vfb_eff = -Qf/Cox - q*Dit*(Emidgap-Ef_ref)/Cox + phi_MS.
    #: When set, the metal-on-insulator BC is Potential = bias - flat_band_shift_V.
    flat_band_shift_V: float = 0.0

@dataclass
class ProcessStep:
    step_type: str
    species: Optional[str] = None
    parameters: dict = field(default_factory=dict)

@dataclass
class MeshField:
    """Central interchange object. Wraps pyvista UnstructuredGrid + semiconductor fields.
    
    grid cell_data must have 'material_id' (int32, Material enum values).
    grid point_data may have 'Nd', 'Na' (float64, cm^-3).
    """
    grid: pv.UnstructuredGrid
    contacts: list[ContactTag] = field(default_factory=list)
    process_history: list[ProcessStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if "material_id" not in self.grid.cell_data:
            raise ValueError("MeshField grid must have 'material_id' cell data.")

    @property
    def n_points(self): return self.grid.n_points
    @property
    def n_cells(self): return self.grid.n_cells
    @property
    def points(self): return self.grid.points
    @property
    def bounds(self): return self.grid.bounds
    @property
    def material_ids(self): return self.grid.cell_data["material_id"]

    def get_cells_for_material(self, material: Material) -> np.ndarray:
        return np.where(self.material_ids == int(material))[0]

    @property
    def has_doping(self):
        return "Nd" in self.grid.point_data and "Na" in self.grid.point_data

    @property
    def Nd(self) -> np.ndarray:
        """Donor concentration [cm^-3], shape (n_points,)."""
        return self.grid.point_data.get("Nd", np.zeros(self.n_points))

    @Nd.setter
    def Nd(self, values: np.ndarray):
        assert values.shape == (self.n_points,), f"Shape mismatch: {values.shape} vs ({self.n_points},)"
        assert np.all(values >= 0), "Donor concentration must be non-negative"
        self.grid.point_data["Nd"] = values.astype(np.float64)

    @property
    def Na(self) -> np.ndarray:
        """Acceptor concentration [cm^-3], shape (n_points,)."""
        return self.grid.point_data.get("Na", np.zeros(self.n_points))

    @Na.setter
    def Na(self, values: np.ndarray):
        assert values.shape == (self.n_points,), f"Shape mismatch: {values.shape} vs ({self.n_points},)"
        assert np.all(values >= 0), "Acceptor concentration must be non-negative"
        self.grid.point_data["Na"] = values.astype(np.float64)

    @property
    def net_doping(self): return self.Nd - self.Na

    def get_contact(self, name: str) -> ContactTag:
        for c in self.contacts:
            if c.name == name: return c
        raise KeyError(f"Contact '{name}' not found. Available: {[c.name for c in self.contacts]}")

    def add_contact(self, contact: ContactTag):
        self.contacts = [c for c in self.contacts if c.name != contact.name]
        self.contacts.append(contact)

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.grid.save(str(path.with_suffix(".vtu")))
        meta = {
            "contacts": [{"name": c.name, "boundary_nodes": c.boundary_nodes.tolist(),
                          "contact_type": c.contact_type, "work_function_eV": c.work_function_eV}
                         for c in self.contacts],
            "process_history": [{"step_type": s.step_type, "species": s.species,
                                  "parameters": s.parameters} for s in self.process_history],
            "metadata": self.metadata,
        }
        path.with_suffix(".json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "MeshField":
        path = Path(path)
        grid = pv.read(str(path.with_suffix(".vtu")))
        meta = json.loads(path.with_suffix(".json").read_text())
        contacts = [ContactTag(name=c["name"], boundary_nodes=np.array(c["boundary_nodes"], dtype=int),
                               contact_type=c["contact_type"], work_function_eV=c["work_function_eV"])
                    for c in meta["contacts"]]
        history = [ProcessStep(step_type=s["step_type"], species=s.get("species"),
                               parameters=s.get("parameters", {})) for s in meta["process_history"]]
        return cls(grid=grid, contacts=contacts, process_history=history,
                   metadata=meta.get("metadata", {}))

    def summary(self) -> str:
        lines = [f"MeshField: {self.n_points} points, {self.n_cells} cells",
                 f"  Bounds [um]: x=[{self.bounds[0]:.3f},{self.bounds[1]:.3f}] "
                 f"y=[{self.bounds[2]:.3f},{self.bounds[3]:.3f}]"]
        mat_counts = {}
        for mid in self.material_ids:
            mat_counts[mid] = mat_counts.get(mid, 0) + 1
        lines.append("  Materials:")
        for mid, count in sorted(mat_counts.items()):
            try: name = MATERIAL_NAMES.get(Material(mid), Material(mid).name)
            except ValueError: name = f"UNKNOWN({mid})"
            lines.append(f"    {name}: {count} cells")
        if self.has_doping:
            lines.append(f"  Doping: Nd_max={self.Nd.max():.2e}, Na_max={self.Na.max():.2e} [cm^-3]")
        if self.contacts:
            lines.append(f"  Contacts: {[c.name for c in self.contacts]}")
        return "\n".join(lines)

    def __repr__(self):
        return f"MeshField(n_points={self.n_points}, n_cells={self.n_cells}, contacts={[c.name for c in self.contacts]})"
