"""
Circuit modeling, gm/ID sizing, chopper stabilization, and SPICE netlist generation.
"""
from .gmid_engine import GMIDSizingEngine, SKY130DeviceModel
from .chopper_rrl import ChopperRRLSimulator
from .spice_generator import SpiceNetlistGenerator, SimulationManager, parse_ngspice_ac_raw
from .fom_analyzer import FoMAnalyzer
from .sky130_setup import Sky130ModelSetup, discover_sky130_models
from .eeg_dataset import ClinicalEEGGenerator
from .cace_verifier import CACESpecificationVerifier

__all__ = [
    "GMIDSizingEngine",
    "SKY130DeviceModel",
    "ChopperRRLSimulator",
    "SpiceNetlistGenerator",
    "SimulationManager",
    "parse_ngspice_ac_raw",
    "FoMAnalyzer",
    "Sky130ModelSetup",
    "discover_sky130_models",
    "ClinicalEEGGenerator",
    "CACESpecificationVerifier",
]
