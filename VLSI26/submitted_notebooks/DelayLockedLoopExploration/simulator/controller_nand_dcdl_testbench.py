"""Standalone testbench for SaturateController + NandDCDL.

This drives explicit up/down requests into the controller and prints the
resulting NAND DCDL control word and total delay after each update.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import NandDCDL, SaturateController
else:
    from . import NandDCDL, SaturateController


@dataclass(frozen=True)
class Stimulus:
    label: str
    up: int
    down: int


STIMULUS = [
    Stimulus("idle", 0, 0),
    Stimulus("up_1", 1, 0),
    Stimulus("up_2", 1, 0),
    Stimulus("up_3", 1, 0),
    Stimulus("hold", 0, 0),
    Stimulus("down_1", 0, 1),
    Stimulus("down_2", 0, 1),
    Stimulus("hold", 0, 0),
    Stimulus("up_4", 1, 0),
    Stimulus("up_5", 1, 0),
]


class IndexedNandDCDL:
    """Map scalar controller output to prefix-clear NAND DCDL words."""

    def __init__(self, inner: NandDCDL):
        self.inner = inner
        self.num_cells = inner.num_cells
        self.full_mask = (1 << self.num_cells) - 1

    def ctrl_word(self, ctrl_index: int) -> int:
        active_stages = max(0, min(ctrl_index, self.num_cells))
        if active_stages == 0:
            return self.full_mask
        return self.full_mask ^ ((1 << active_stages) - 1)

    def delay(self, ctrl_index: int) -> float:
        return self.inner.delay(self.ctrl_word(ctrl_index))


def expected_delay_for_index(
    ctrl_index: int,
    first_cell_delay_ps: float,
    remaining_cell_delay_ps: float,
) -> float:
    if ctrl_index <= 0:
        return 0.0
    return first_cell_delay_ps + (ctrl_index - 1) * remaining_cell_delay_ps


def run_testbench() -> int:
    controller = SaturateController(ctrl_bits=6, init_ctrl=0)
    dcdl = IndexedNandDCDL(
        NandDCDL(num_cells=64, first_cell_delay_ps=106.67, remaining_cell_delay_ps=72.68)
    )

    controller.reset()

    print("SaturateController + NandDCDL testbench")
    print("NAND encoding: 0 bit adds stage delay, 1 bit bypasses stage")
    print()
    print("step   stim    up  down  ctrl_idx  ctrl_word            delay_ps   expected   result")

    failures = 0

    for step, stimulus in enumerate(STIMULUS):
        controller.update(stimulus.up, stimulus.down)
        ctrl_idx = controller.ctrl
        ctrl_word = dcdl.ctrl_word(ctrl_idx)
        observed_delay = dcdl.delay(ctrl_idx)
        expected_delay = expected_delay_for_index(
            ctrl_idx,
            first_cell_delay_ps=dcdl.inner.first_cell_delay_ps,
            remaining_cell_delay_ps=dcdl.inner.remaining_cell_delay_ps,
        )
        passed = abs(observed_delay - expected_delay) < 1e-9
        if not passed:
            failures += 1

        print(
            f"{step:4d}  {stimulus.label:<6}  {stimulus.up:2d}  {stimulus.down:4d}  "
            f"{ctrl_idx:8d}  0x{ctrl_word:016x}  {observed_delay:9.2f}  "
            f"{expected_delay:9.2f}  {'PASS' if passed else 'FAIL'}"
        )

    print()
    if failures:
        print(f"FAILED: {failures} controller/NAND checks failed.")
        return 1

    print("PASSED: controller output produces the expected NAND DCDL delays.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_testbench())
