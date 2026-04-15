"""Zero-delay buffer demo using the DLL simulator.

Architecture:
    PFDPhaseDetector -> SaturateController -> NandDCDL -> feedback to PFD

The current NAND DCDL model interprets control bits as stage bypass
enables: a 0 bit adds that stage's delay and a 1 bit bypasses it.
This demo maps the controller's scalar output to a prefix-clear mask so
higher controller values correspond to more accumulated delay.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import NandDCDL, PFDPhaseDetector, SaturateController
else:
    from . import NandDCDL, PFDPhaseDetector, SaturateController


@dataclass
class ZDBTraceEntry:
    cycle: int
    action: str
    ctrl_index: int
    ctrl_word: int
    delay_ps: float
    phase_error_ps: float
    up: int
    down: int


class IndexedNandDCDL:
    """Map a scalar control index to a prefix-clear NAND DCDL control word."""

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


def run_zdb_demo(
    target_tap: int = 41,
    init_ctrl: int = 0,
    num_cycles: int = 120,
    settle_cycles: int = 3,
) -> tuple[list[ZDBTraceEntry], float]:
    """Simulate the ZDB loop until convergence or until num_cycles elapse."""
    pd = PFDPhaseDetector()
    controller = SaturateController(ctrl_bits=6, init_ctrl=init_ctrl)
    dcdl = IndexedNandDCDL(NandDCDL())

    clk_period_ps = dcdl.delay(target_tap)
    controller.reset()
    controller.configure_pipeline(pd.prop_delay_ps, clk_period_ps)

    trace: list[ZDBTraceEntry] = []
    prev_delay_ps = dcdl.delay(controller.ctrl)
    stable_cycles = 0

    for cycle in range(num_cycles):
        phase_error_ps = prev_delay_ps - clk_period_ps
        up, down, _ = pd.detect(prev_delay_ps, clk_period_ps)
        prev_ctrl = controller.ctrl
        controller.update(up, down)
        current_delay_ps = dcdl.delay(controller.ctrl)

        if controller.ctrl > prev_ctrl:
            action = "ADD"
        elif controller.ctrl < prev_ctrl:
            action = "SUB"
        else:
            action = "HOLD"

        entry = ZDBTraceEntry(
            cycle=cycle,
            action=action,
            ctrl_index=controller.ctrl,
            ctrl_word=dcdl.ctrl_word(controller.ctrl),
            delay_ps=current_delay_ps,
            phase_error_ps=phase_error_ps,
            up=up,
            down=down,
        )
        trace.append(entry)

        if phase_error_ps == 0.0 and up == 0 and down == 0:
            stable_cycles += 1
            if stable_cycles >= settle_cycles:
                break
        else:
            stable_cycles = 0

        prev_delay_ps = current_delay_ps

    return trace, clk_period_ps


def print_zdb_trace(trace: list[ZDBTraceEntry], clk_period_ps: float) -> None:
    print(f"ZDB target clock period: {clk_period_ps:.2f} ps")
    print("cycle  action  ctrl_idx  ctrl_word      delay_ps   phase_err   up  down")
    for entry in trace:
        if entry.action == "HOLD" and entry.phase_error_ps != 0.0:
            continue
        width = max(1, (entry.ctrl_word.bit_length() + 3) // 4)
        print(
            f"{entry.cycle:5d}  {entry.action:>4}  {entry.ctrl_index:8d}  "
            f"0x{entry.ctrl_word:0{width}x}  {entry.delay_ps:9.2f}  "
            f"{entry.phase_error_ps:10.2f}  {entry.up:2d}  {entry.down:4d}"
        )

    last = trace[-1]
    converged = last.phase_error_ps == 0.0 and last.up == 0 and last.down == 0
    status = "CONVERGED" if converged else "STOPPED WITHOUT FULL CONVERGENCE"
    width = max(1, (last.ctrl_word.bit_length() + 3) // 4)
    print()
    print(
        f"{status}: cycle={last.cycle}, ctrl_idx={last.ctrl_index}, "
        f"ctrl_word=0x{last.ctrl_word:0{width}x}, delay={last.delay_ps:.2f} ps"
    )


if __name__ == "__main__":
    trace, clk_period_ps = run_zdb_demo()
    print_zdb_trace(trace, clk_period_ps)
