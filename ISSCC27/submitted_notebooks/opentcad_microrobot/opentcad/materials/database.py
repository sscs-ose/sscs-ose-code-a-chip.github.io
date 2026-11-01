"""
opentcad/materials/database.py — Material parameter loader.

Loads YAML parameter files from opentcad/materials/params/.
Returns pydantic-validated parameter objects for use in device simulation.

Usage:
    from opentcad.materials.database import load_material
    si = load_material("Si")
    print(si.mobility_constant.electron_cm2_Vs)   # 1350.0
    print(si.recombination.tau_n_s)                # 1e-5
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel

PARAMS_DIR = Path(__file__).parent / "params"


class MobilityConstant(BaseModel):
    electron_cm2_Vs: float = 1350.0
    hole_cm2_Vs: float = 480.0
    uncertainty_percent: float = 5.0


class MobilityKlaassen(BaseModel):
    """Klaassen unified low-field bulk mobility coefficients.

    Reference: Klaassen, Solid-State Electron. 35, 953 (1992).
    Default values are the published Si fit. If the YAML omits this
    block, these defaults are used."""
    mu_min_e: float = 52.2
    mu_max_e: float = 1417.0
    theta1_e: float = 2.285
    m_e: float = 1.0
    Nref_1_e: float = 9.68e16
    alpha_1_e: float = 0.68

    mu_min_h: float = 44.9
    mu_max_h: float = 470.5
    theta1_h: float = 2.247
    m_h: float = 1.258
    Nref_1_h: float = 2.2e17
    alpha_1_h: float = 0.719

    f_BH: float = 3.828
    f_CW: float = 2.459
    c_D: float = 0.21
    c_A: float = 0.50
    Nref_D: float = 4.0e20
    Nref_A: float = 7.2e20

    r1: float = 0.7643; r2: float = 2.2999; r3: float = 6.5502
    r4: float = 2.3670; r5: float = -0.01552; r6: float = 0.6478

    s1: float = 0.892333; s2: float = 0.41372; s3: float = 0.19778
    s4: float = 0.28227;  s5: float = 0.005978; s6: float = 1.80618
    s7: float = 0.72169


class Recombination(BaseModel):
    tau_n_s: float = 1e-5       # [s] electron SRH lifetime
    tau_p_s: float = 1e-5       # [s] hole SRH lifetime
    Et_eV: float = 0.0          # trap energy re mid-gap [eV]
    Cn_cm6_per_s: float = 2.8e-31  # Auger electron
    Cp_cm6_per_s: float = 9.9e-32  # Auger hole
    B_rad_cm3_per_s: float = 9.5e-15  # Radiative


class BandStructure(BaseModel):
    Eg_eV_300K: float = 1.124
    electron_affinity_eV: float = 4.05
    Nc_cm3_300K: float = 2.86e19
    Nv_cm3_300K: float = 3.10e19
    ni_cm3_300K: float = 9.65e9
    permittivity_relative: float = 11.7


class VelocitySaturation(BaseModel):
    vsat_e_cm_s: float = 1.02e7
    vsat_h_cm_s: float = 0.72e7
    beta_e: float = 2.0
    beta_h: float = 1.0


class MaterialParams(BaseModel):
    """Validated material parameter set for one material."""
    material: str
    symbol: str
    is_insulator: bool = False   # True for SiO2/Si3N4 (Poisson only, no carriers)
    band_structure: BandStructure = BandStructure()
    mobility_constant: MobilityConstant = MobilityConstant()
    mobility_klaassen: MobilityKlaassen = MobilityKlaassen()
    recombination: Recombination = Recombination()
    velocity_saturation: VelocitySaturation = VelocitySaturation()
    raw: dict = {}   # full YAML dict for advanced access


def load_material(symbol: str, process: Optional[str] = None) -> MaterialParams:
    """Load material parameters by symbol.

    Args:
        symbol: Material symbol, e.g. "Si", "SiO2", "GaN".
        process: Optional process variant, e.g. "hackerfab". If given, loads
                 from params/{process}/{symbol}.yaml with fallback to params/{symbol}.yaml.

    Returns:
        MaterialParams pydantic object.

    Raises:
        FileNotFoundError: If no YAML file found for the given symbol.
    """
    candidates = []
    if process:
        candidates.append(PARAMS_DIR / process / f"{symbol}.yaml")
    candidates.append(PARAMS_DIR / f"{symbol}.yaml")

    yaml_path = None
    for p in candidates:
        if p.exists():
            yaml_path = p
            break

    if yaml_path is None:
        available = [f.stem for f in PARAMS_DIR.glob("*.yaml")]
        raise FileNotFoundError(
            f"No parameter file found for '{symbol}'. "
            f"Available: {available}. "
            f"Searched: {[str(c) for c in candidates]}"
        )

    raw = yaml.safe_load(yaml_path.read_text())

    # Parse into typed sub-objects
    bs_raw = raw.get("bandgap", {})
    band = BandStructure(
        Eg_eV_300K=bs_raw.get("Eg_eV_300K", 1.124),
        electron_affinity_eV=raw.get("electron_affinity_eV", 4.05),
        Nc_cm3_300K=raw.get("Nc_cm3_300K", 2.86e19),
        Nv_cm3_300K=raw.get("Nv_cm3_300K", 3.10e19),
        ni_cm3_300K=raw.get("ni_cm3_300K", 9.65e9),
        permittivity_relative=raw.get("permittivity_relative", 11.7),
    )

    mob_raw = raw.get("mobility_constant", {})
    mob = MobilityConstant(
        electron_cm2_Vs=mob_raw.get("electron_cm2_Vs", 1350.0),
        hole_cm2_Vs=mob_raw.get("hole_cm2_Vs", 480.0),
    )

    # Klaassen block is optional; if missing the pydantic defaults apply.
    klaassen_raw = raw.get("mobility_klaassen", {})
    klaassen = MobilityKlaassen(**klaassen_raw)

    rec_raw = raw.get("recombination", {})
    rec = Recombination(
        tau_n_s=rec_raw.get("tau_n_s", 1e-5),
        tau_p_s=rec_raw.get("tau_p_s", 1e-5),
        Et_eV=rec_raw.get("Et_eV", 0.0),
        Cn_cm6_per_s=rec_raw.get("Cn_cm6_per_s", 2.8e-31),
        Cp_cm6_per_s=rec_raw.get("Cp_cm6_per_s", 9.9e-32),
    )

    vs_raw = raw.get("velocity_saturation", {})
    vs = VelocitySaturation(
        vsat_e_cm_s=vs_raw.get("vsat_e_cm_s", 1.02e7),
        vsat_h_cm_s=vs_raw.get("vsat_h_cm_s", 0.72e7),
        beta_e=vs_raw.get("beta_e", 2.0),
        beta_h=vs_raw.get("beta_h", 1.0),
    )

    return MaterialParams(
        material=raw.get("material", symbol),
        symbol=raw.get("symbol", symbol),
        is_insulator=bool(raw.get("is_insulator", False)),
        band_structure=band,
        mobility_constant=mob,
        mobility_klaassen=klaassen,
        recombination=rec,
        velocity_saturation=vs,
        raw=raw,
    )
