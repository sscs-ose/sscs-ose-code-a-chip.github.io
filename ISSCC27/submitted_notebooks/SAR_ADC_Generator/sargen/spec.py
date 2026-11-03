"""User-facing specification of the SAR ADC."""

from dataclasses import dataclass, asdict


@dataclass
class SarSpec:
    """Top-level SAR ADC specification.

    Architecture (fixed for now): single-ended, binary-weighted charge-redistribution
    CDAC with bottom-plate sampling, conventional (set-and-down) switching,
    StrongARM comparator, synchronous SAR logic. Input range is 0 .. vref.
    """

    bits: int = 4                 # resolution N (4..8)
    fs: float = 10e6              # sample rate [S/s]
    vdd: float = 1.8              # supply [V]
    vref: float = 1.8             # DAC reference [V] (CDAC drivers run from vref)
    temp: float = 27.0            # temperature [degC]
    corner: str = "tt"            # process corner of the SKY130 models

    # Design targets, all in LSB. The sizing step turns these into device sizes.
    dnl_3sigma_lsb: float = 0.5       # 3-sigma mid-code DNL from capacitor mismatch
    offset_3sigma_lsb: float = 1.0    # 3-sigma comparator offset; it only causes offset error here
    noise_lsb: float = 0.1            # rms comparator + kT/C noise
    settle_lsb: float = 0.25          # settling error allowed at end of each phase

    def __post_init__(self):
        if not 4 <= self.bits <= 8:
            raise ValueError("bits must be between 4 and 8")
        if self.vref > self.vdd:
            raise ValueError("vref must not exceed vdd (CDAC drivers are powered from vref)")

    @property
    def lsb(self) -> float:
        return self.vref / 2**self.bits

    @property
    def vcm(self) -> float:
        return self.vref / 2

    @property
    def cycles(self) -> int:
        """Clock cycles per conversion: 1 sample + N bit trials + 1 output/reset."""
        return self.bits + 2

    @property
    def fclk(self) -> float:
        return self.fs * self.cycles

    @property
    def tclk(self) -> float:
        return 1 / self.fclk

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(lsb=self.lsb, vcm=self.vcm, cycles=self.cycles, fclk=self.fclk)
        return d
