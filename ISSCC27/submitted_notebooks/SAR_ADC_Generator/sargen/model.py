"""Behavioral (Python) model of the charge-redistribution SAR ADC.

Used for the animated explanation and for fast Monte-Carlo runs whose
non-idealities (unit-cap mismatch, top-plate parasitic, comparator offset and
noise) come from SPICE characterization of the real SKY130 blocks.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SarModel:
    bits: int
    vref: float = 1.8
    cu_sigma: float = 0.0       # relative std of one unit capacitor
    cp_ratio: float = 0.0       # top-plate parasitic / total array capacitance
    offset: float = 0.0         # comparator input offset [V]
    noise_rms: float = 0.0      # comparator input-referred rms noise [V]
    seed: int | None = None
    caps: np.ndarray = field(init=False)     # caps[i] = bit-i capacitance (unit = 1), LSB first
    c_dummy: float = field(init=False)
    c_sum: float = field(init=False)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        units = 1 + self.cu_sigma * self.rng.standard_normal(2**self.bits)
        # bit i uses 2**i unit caps; the last unit is the termination (dummy) cap
        idx = np.cumsum([0] + [2**i for i in range(self.bits)])
        self.caps = np.array([units[idx[i]:idx[i + 1]].sum() for i in range(self.bits)])
        self.c_dummy = units[-1]
        self.c_sum = self.caps.sum() + self.c_dummy

    @property
    def vcm(self) -> float:
        return self.vref / 2

    def vx_minus_vcm(self, vin, ctrl):
        """Top-plate voltage relative to vcm for bottom-plate controls `ctrl` (LSB-first 0/1)."""
        q_dac = np.tensordot(ctrl, self.caps, axes=([-1], [0])) * self.vref
        return (q_dac - vin * self.c_sum) / (self.c_sum * (1 + self.cp_ratio))

    def convert(self, vin):
        """Convert a scalar or array of inputs; returns integer codes."""
        vin = np.atleast_1d(np.asarray(vin, dtype=float))
        ctrl = np.zeros(vin.shape + (self.bits,))
        for i in reversed(range(self.bits)):
            ctrl[..., i] = 1
            v = self.vx_minus_vcm(vin, ctrl) + self.offset
            v = v + self.noise_rms * self.rng.standard_normal(vin.shape)
            ctrl[..., i] = (v < 0).astype(float)    # keep the bit if DAC still below vin
        return (ctrl * 2**np.arange(self.bits)).sum(-1).astype(int)

    def trace(self, vin: float):
        """Step-by-step record of one conversion, for teaching and animation."""
        steps = [dict(phase="sample", bit=None, ctrl=np.zeros(self.bits), vdac=0.0, decision=None)]
        ctrl = np.zeros(self.bits)
        for i in reversed(range(self.bits)):
            ctrl[i] = 1
            vdac = float(ctrl @ self.caps / self.c_sum * self.vref)
            keep = bool(self.vx_minus_vcm(vin, ctrl) + self.offset < 0)
            steps.append(dict(phase="trial", bit=i, ctrl=ctrl.copy(), vdac=vdac, decision=keep))
            ctrl[i] = float(keep)
        code = int(ctrl @ 2**np.arange(self.bits))
        steps.append(dict(phase="done", bit=None, ctrl=ctrl.copy(),
                          vdac=float(ctrl @ self.caps / self.c_sum * self.vref), decision=None, code=code))
        return steps
