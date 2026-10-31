"""Explicit process mapping and sizing assumptions for the portable hierarchy."""
from dataclasses import dataclass
from functools import lru_cache
from silk import load_pdk

@lru_cache(maxsize=None)
def _catalog(name):
    # Silk API: load the device catalog; reuse it for the blocks in this process.
    return load_pdk(name)

@dataclass(frozen=True)
class Technology:
    """Demo mapping of device names, supply, corner, and geometry scales.

    Widths and lengths are in micrometres. Scaling them is a starting
    assumption for the port, not a guarantee of matched performance.
    """
    name: str
    label: str
    nmos: str
    pmos: str
    corner: str
    nominal_v: float
    width_scale: float = 1.0
    length_scale: float = 1.0

    def load(self):
        return _catalog(self.name)

    def width(self, value):
        return value * self.width_scale

    def length(self, value):
        return value * self.length_scale

SKY130 = Technology('sky130','PDK_skywater130','nmos1p8','pmos1p8','tt',1.8)
# Illustrative port: double W/L and use 3.3 V devices, then recharacterize.
# This scaling does not establish equivalent performance between processes.
GF180 = Technology('gf180mcu','PDK_gf180mcu','nmos3p3','pmos3p3','typical',3.3,2.0,2.0)
TECHNOLOGIES = {t.name:t for t in (SKY130,GF180)}
