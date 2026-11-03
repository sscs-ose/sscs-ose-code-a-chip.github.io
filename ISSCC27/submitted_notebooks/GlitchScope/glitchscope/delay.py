from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DelayResult:
    delay_fs: int
    output_slew_fs: int
    model: str

class ConstantDelayProvider:
    def delay(self, cell, new_output, input_slew_fs=0, load_ff=0.0, related_pin=None, pin_values=None, input_transition=None):
        d = cell.rise_fs if new_output == 1 else cell.fall_fs
        return DelayResult(int(d), int(input_slew_fs), "CONSTANT")
