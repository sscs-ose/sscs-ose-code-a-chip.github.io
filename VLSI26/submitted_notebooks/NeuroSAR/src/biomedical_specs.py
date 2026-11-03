"""
Biomedical implantable-telemetry ADC specifications.

Curated from published implantable-ADC and neural-recorder papers to
define realistic target specs that NeuroSAR can optimise toward. These
are the specs the biomedical case-study notebook sweeps against.

References
----------
- Harpe et al., "A 26 uW 8 bit 10 MS/s Asynchronous SAR ADC for Low
  Energy Radios," IEEE JSSC, vol.46, no.7, 2011.
- Harpe, "A Compact 10-b SAR ADC With Unit-Length Capacitors and a
  Passive FIR Filter," IEEE JSSC, vol.54, no.3, 2019.
- Muller et al., "A Minimally Invasive 64-Channel Wireless uECoG
  Implant," IEEE JSSC, 2015.
- Nurmi et al., "An 11-bit 0.4-V 10-kS/s SAR ADC for Biomedical
  Applications," IEEE TBioCAS, 2020.
- Zhang & Chen, "A 13b-ENOB Noise-Shaping SAR ADC With an Optimised
  Error-Feedback Filter for Biomedical Applications," IEEE TCAS-I, 2022.

License: Apache-2.0.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class BiomedicalSARTarget:
    """Target spec for a biomedical SAR ADC."""

    name: str
    application: str
    n_bits: int
    fs_MHz: float
    energy_per_conv_pJ_max: float
    enob_min: float
    metastability_p_max: float    # P(dwell_time > 1 bit period)
    supply_V: float
    temperature_K: float = 310.15

    def asdict(self) -> Dict:
        return asdict(self)


# Curated targets pulled from the references above.
BIOMEDICAL_TARGETS: List[BiomedicalSARTarget] = [
    BiomedicalSARTarget(
        name="Neural-recorder front-end",
        application="Cortical neural recording (uECoG / intracortical)",
        n_bits=10,
        fs_MHz=1.0,
        energy_per_conv_pJ_max=10.0,
        enob_min=9.0,
        metastability_p_max=1e-9,
        supply_V=1.0,
    ),
    BiomedicalSARTarget(
        name="Pacemaker telemetry AFE",
        application="Implantable pacemaker IEGM digitisation + HBC uplink",
        n_bits=10,
        fs_MHz=0.2,
        energy_per_conv_pJ_max=5.0,
        enob_min=9.2,
        metastability_p_max=1e-10,
        supply_V=1.2,
    ),
    BiomedicalSARTarget(
        name="Wearable ECG / PPG",
        application="Low-power wearable biopotential monitoring",
        n_bits=12,
        fs_MHz=0.01,
        energy_per_conv_pJ_max=50.0,
        enob_min=11.0,
        metastability_p_max=1e-8,
        supply_V=1.8,
    ),
    BiomedicalSARTarget(
        name="Cochlear implant stimulator ADC",
        application="Audio-band feedback digitisation in cochlear implants",
        n_bits=8,
        fs_MHz=0.025,
        energy_per_conv_pJ_max=2.0,
        enob_min=7.5,
        metastability_p_max=1e-7,
        supply_V=1.2,
    ),
]


def target_by_name(name: str) -> BiomedicalSARTarget:
    for t in BIOMEDICAL_TARGETS:
        if t.name == name:
            return t
    raise KeyError(name)


def walden_fom_fJ_per_step(energy_per_conv_pJ: float, enob: float) -> float:
    """Walden FoM = Energy / (2^ENOB * fs), reported per conversion step (fJ/step)."""
    return (energy_per_conv_pJ * 1e3) / (2.0 ** enob)


def meets_spec(target: BiomedicalSARTarget,
               energy_pJ: float,
               enob: float,
               p_meta: float) -> Dict[str, bool]:
    return {
        "energy_ok": energy_pJ <= target.energy_per_conv_pJ_max,
        "enob_ok": enob >= target.enob_min,
        "meta_ok": p_meta <= target.metastability_p_max,
    }
